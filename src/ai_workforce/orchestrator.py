import threading
from dataclasses import dataclass
from typing import Any, Optional

from .agents import (
    MAX_REPLANS_PER_RUN,
    MAX_STEPS_PER_RUN,
    AgentContext,
    CriticAgent,
    ManagerAgent,
    PlannerAgent,
    PlanValidationError,
)
from .db import Repository
from .llm import LLMProvider, extract_terms
from .models import RiskLevel, Run, RunStatus, StepStatus, utc_now
from .tools import ToolContext, ToolRegistry


class RunNotFound(KeyError):
    pass


class InvalidTransition(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionConfig:
    """Agentic capabilities a run may use. Evaluation baselines switch these off."""

    model_planning: bool = True
    max_replans: int = 2
    verify_grounding: bool = True
    use_memory: bool = True


class WorkforceOrchestrator:
    def __init__(
        self,
        repository: Repository,
        provider: LLMProvider,
        tools: ToolRegistry,
        auto_approve: bool = False,
        config: Optional[ExecutionConfig] = None,
    ):
        self.repository = repository
        self.provider = provider
        self.tools = tools
        self.auto_approve = auto_approve
        self.config = config or ExecutionConfig()
        self.manager = ManagerAgent()
        self.planner = PlannerAgent(provider, tools)
        self.critic = CriticAgent(provider, repository)
        self._run_locks: dict[str, threading.Lock] = {}
        self._lock_guard = threading.Lock()

    def create_run(self, objective: str, context: Optional[dict[str, Any]] = None) -> Run:
        if not objective.strip():
            raise ValueError("Objective cannot be empty")
        run = Run(objective=objective.strip(), context=context or {})
        run.context.setdefault("_replans", 0)
        run.context.setdefault("_repairs", 0)
        run.context.setdefault("_revisions", 0)
        run.context.setdefault("_step_attempts", 0)
        run.context.setdefault("_observations", [])
        self.repository.save_run(run)
        self.repository.add_event(run.id, "run.created", "user", {"objective": run.objective})
        return run

    def execute(self, run_id: str) -> Run:
        lock = self._get_lock(run_id)
        if not lock.acquire(blocking=False):
            run = self.repository.get_run(run_id)
            if run is None:
                raise RunNotFound(run_id)
            return run
        try:
            return self._execute_locked(run_id)
        finally:
            lock.release()

    def _execute_locked(self, run_id: str) -> Run:
        run = self._require_run(run_id)
        # A paused run resumes only through resolve_approval, which moves it to QUEUED first.
        if run.status in {
            RunStatus.COMPLETED,
            RunStatus.REJECTED,
            RunStatus.FAILED,
            RunStatus.WAITING_APPROVAL,
        }:
            return run
        was_resuming = bool(run.plan)
        claimed_status = run.status
        run.status = RunStatus.RUNNING
        run.error = None
        run.updated_at = utc_now()
        if not self.repository.save_run_if_status(run, claimed_status):
            return self._require_run(run_id)
        self.repository.add_event(
            run.id, "run.resumed" if was_resuming else "run.started", "manager", {}
        )
        try:
            if not run.plan:
                self._create_initial_plan(run)

            while True:
                replanned = False
                approved = set(run.context.get("_approved_steps", []))
                prior_outputs = [step.output for step in run.plan if step.output]
                for step in run.plan:
                    if step.status == StepStatus.COMPLETED:
                        continue
                    if step.risk == RiskLevel.HIGH and step.id not in approved:
                        if self.auto_approve:
                            approved.add(step.id)
                            run.context["_approved_steps"] = sorted(approved)
                            self.repository.add_event(
                                run.id, "approval.auto_granted", "policy", {"step_id": step.id}
                            )
                        else:
                            step.status = StepStatus.WAITING_APPROVAL
                            run.status = RunStatus.WAITING_APPROVAL
                            run.updated_at = utc_now()
                            self.repository.save_run(run)
                            self.repository.add_event(
                                run.id,
                                "approval.requested",
                                "policy",
                                {
                                    "step_id": step.id,
                                    "title": step.title,
                                    "risk": step.risk.value,
                                    "grounding_passed": run.context.get("_draft_review", {}).get(
                                        "passed"
                                    ),
                                },
                            )
                            return run
                    if int(run.context.get("_step_attempts", 0)) >= MAX_STEPS_PER_RUN:
                        raise RuntimeError("Global eight-step execution budget exhausted")
                    run.context["_step_attempts"] = int(
                        run.context.get("_step_attempts", 0)
                    ) + 1
                    step.status = StepStatus.RUNNING
                    self.repository.save_run(run)
                    self.repository.add_event(
                        run.id,
                        "step.started",
                        step.agent,
                        {
                            "step_id": step.id,
                            "tool": step.tool,
                            "arguments": step.arguments,
                        },
                    )
                    try:
                        step.output = self._execute_step(run, step, prior_outputs)
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        step.status = StepStatus.FAILED
                        step.output = {"error": error}
                        self.repository.save_run(run)
                        self.repository.add_event(
                            run.id,
                            "step.failed",
                            step.agent,
                            {"step_id": step.id, "tool": step.tool, "error": error},
                        )
                        if self._replan(run, step, error):
                            replanned = True
                            break
                        raise
                    prior_outputs.append(step.output)
                    step.status = StepStatus.COMPLETED
                    self.repository.save_run(run)
                    self.repository.add_event(
                        run.id,
                        "step.completed",
                        step.agent,
                        {"step_id": step.id, "output": step.output},
                    )
                    if step.tool == "content.synthesize" and self.config.verify_grounding:
                        grounding = self._verify_and_revise(run, step, prior_outputs)
                        if not grounding["passed"]:
                            error = "Grounding review failed after the allowed writer revision"
                            step.status = StepStatus.FAILED
                            self.repository.save_run(run)
                            self.repository.add_event(
                                run.id,
                                "step.failed",
                                step.agent,
                                {"step_id": step.id, "tool": step.tool, "error": error},
                            )
                            if self._replan(run, step, error):
                                replanned = True
                                break
                            raise RuntimeError(error)
                if replanned:
                    continue
                break

            review = self.critic.evaluate(run)
            run.result = {
                "summary": "All delegated tasks completed successfully.",
                "artifacts": [step.output for step in run.plan if step.output],
                "review": review,
                "execution": {
                    "planner": run.context.get("_plan_source"),
                    "repairs": run.context.get("_repairs", 0),
                    "replans": run.context.get("_replans", 0),
                    "draft_revisions": run.context.get("_revisions", 0),
                    "step_attempts": run.context.get("_step_attempts", 0),
                },
            }
            run.status = RunStatus.COMPLETED
            run.updated_at = utc_now()
            self.repository.save_run(run)
            self.repository.add_event(run.id, "run.completed", "manager", {"review": review})
            return run
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.error = f"{type(exc).__name__}: {exc}"
            run.updated_at = utc_now()
            self.repository.save_run(run)
            self.repository.add_event(run.id, "run.failed", "manager", {"error": run.error})
            return run

    def _create_initial_plan(self, run: Run) -> None:
        agent_context = AgentContext(run=run, memories=self._retrieve_lessons(run))
        run.context["delegation"] = self.manager.delegate(agent_context)
        run.context["delegation"]["budget"]["max_replans"] = self._max_replans
        if self.config.model_planning:
            source = self._plan_with_model(run, agent_context)
        else:
            run.plan = self.planner.fallback_plan(agent_context)
            source = "fixed_pipeline"
        run.context["_plan_source"] = source
        self.repository.save_run(run)
        self.repository.add_event(
            run.id,
            "plan.created",
            "planner",
            {"source": source, "steps": [step.to_dict() for step in run.plan]},
        )

    def _plan_with_model(self, run: Run, agent_context: AgentContext) -> str:
        try:
            run.plan = self.planner.create_plan(agent_context)
            return "model"
        except PlanValidationError as first_error:
            run.context["_repairs"] = 1
            self.repository.add_event(
                run.id, "plan.invalid", "validator", {"error": str(first_error), "attempt": 1}
            )
            try:
                run.plan = self.planner.create_plan(
                    agent_context, validation_error=str(first_error)
                )
                self.repository.add_event(
                    run.id, "plan.repaired", "planner", {"error": str(first_error)}
                )
                return "model_repair"
            except PlanValidationError as second_error:
                run.plan = self.planner.fallback_plan(agent_context)
                self.repository.add_event(
                    run.id,
                    "plan.fallback",
                    "planner",
                    {"errors": [str(first_error), str(second_error)]},
                )
                return "deterministic_fallback"

    def _retrieve_lessons(self, run: Run) -> list[dict[str, Any]]:
        if not self.config.use_memory:
            return []
        return self.repository.search_memories(extract_terms(run.objective), limit=3)

    def _execute_step(
        self, run: Run, step: Any, prior_outputs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        tool = self.tools.get(step.tool)
        inputs = dict(run.context)
        inputs.update(step.arguments)
        return tool.execute(
            ToolContext(
                run_id=run.id,
                step_id=step.id,
                objective=run.objective,
                instruction=step.instruction,
                prior_outputs=prior_outputs,
                inputs=inputs,
            )
        )

    def _replan(self, run: Run, failed_step: Any, error: str) -> bool:
        replans = int(run.context.get("_replans", 0))
        observation = {"tool": failed_step.tool, "step_id": failed_step.id, "error": error}
        run.context.setdefault("_observations", []).append(observation)
        self.repository.save_run(run)
        self.repository.add_event(run.id, "step.observed", "manager", observation)
        if (
            replans >= self._max_replans
            or int(run.context.get("_step_attempts", 0)) >= MAX_STEPS_PER_RUN
        ):
            return False
        run.context["_replans"] = replans + 1
        completed_steps = [
            step
            for step in run.plan
            if step.status == StepStatus.COMPLETED and step.id != failed_step.id
        ]
        completed_tools = [step.tool for step in completed_steps]
        context = AgentContext(run=run, memories=self._retrieve_lessons(run))
        try:
            remaining = self.planner.create_plan(
                context, validation_error=error, completed_tools=completed_tools
            )
            source = "model_replan"
        except PlanValidationError as plan_error:
            remaining = self.planner.fallback_plan(context, completed_tools=completed_tools)
            source = "fallback_replan"
            self.repository.add_event(
                run.id, "replan.invalid", "validator", {"error": str(plan_error)}
            )
        run.plan = completed_steps + remaining
        run.context["_plan_source"] = source
        self.repository.save_run(run)
        self.repository.add_event(
            run.id,
            "plan.replanned",
            "planner",
            {
                "attempt": run.context["_replans"],
                "failed_tool": failed_step.tool,
                "error": error,
                "source": source,
                "remaining_steps": [step.to_dict() for step in remaining],
            },
        )
        return True

    @property
    def _max_replans(self) -> int:
        return min(max(self.config.max_replans, 0), MAX_REPLANS_PER_RUN)

    def _verify_and_revise(
        self, run: Run, step: Any, prior_outputs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        review = self.critic.evaluate_draft(run)
        self.repository.add_event(run.id, "critic.checked", "critic", review)
        if not review["passed"] and int(run.context.get("_revisions", 0)) < 1:
            run.context["_revisions"] = 1
            inputs = dict(run.context)
            inputs.update(step.arguments)
            inputs["_critic_notes"] = review["notes"]
            step.output = self.tools.get(step.tool).execute(
                ToolContext(
                    run_id=run.id,
                    step_id=step.id,
                    objective=run.objective,
                    instruction=step.instruction,
                    prior_outputs=prior_outputs[:-1],
                    inputs=inputs,
                )
            )
            prior_outputs[-1] = step.output
            self.repository.save_run(run)
            self.repository.add_event(
                run.id,
                "draft.revised",
                "writer",
                {"step_id": step.id, "critic_notes": review["notes"], "output": step.output},
            )
            review = self.critic.evaluate_draft(run)
            self.repository.add_event(run.id, "critic.rechecked", "critic", review)
        if not review["passed"]:
            self.repository.add_event(run.id, "critic.flagged", "critic", review)
        run.context["_draft_review"] = review
        self.repository.save_run(run)
        return review

    def resolve_approval(self, run_id: str, step_id: str, approved: bool) -> Run:
        run = self._require_run(run_id)
        if run.status != RunStatus.WAITING_APPROVAL:
            raise InvalidTransition("Run is not waiting for approval")
        step = next((candidate for candidate in run.plan if candidate.id == step_id), None)
        if step is None or step.status != StepStatus.WAITING_APPROVAL:
            raise InvalidTransition("Step is not waiting for approval")
        if not approved:
            step.status = StepStatus.REJECTED
            run.status = RunStatus.REJECTED
            run.updated_at = utc_now()
            self._record_decision(run)
            self.repository.add_event(run.id, "approval.rejected", "human", {"step_id": step.id})
            return run
        approved_steps = set(run.context.get("_approved_steps", []))
        approved_steps.add(step.id)
        run.context["_approved_steps"] = sorted(approved_steps)
        step.status = StepStatus.PENDING
        run.status = RunStatus.QUEUED
        run.updated_at = utc_now()
        self._record_decision(run)
        self.repository.add_event(run.id, "approval.granted", "human", {"step_id": step.id})
        return self.execute(run.id)

    def _record_decision(self, run: Run) -> None:
        if not self.repository.save_run_if_status(run, RunStatus.WAITING_APPROVAL):
            raise InvalidTransition("Approval was already resolved by another request")

    def detail(self, run_id: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        result = run.to_dict()
        result["events"] = self.repository.get_events(run_id)
        return result

    def _require_run(self, run_id: str) -> Run:
        run = self.repository.get_run(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return run

    def _get_lock(self, run_id: str) -> threading.Lock:
        with self._lock_guard:
            return self._run_locks.setdefault(run_id, threading.Lock())
