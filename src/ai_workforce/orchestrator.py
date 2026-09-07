import threading
from typing import Any, Optional

from .agents import AgentContext, CriticAgent, ManagerAgent, PlannerAgent
from .db import Repository
from .llm import LLMProvider, extract_terms
from .models import Run, RunStatus, StepStatus, utc_now
from .tools import ToolContext, ToolRegistry


class RunNotFound(KeyError):
    pass


class InvalidTransition(ValueError):
    pass


class WorkforceOrchestrator:
    def __init__(
        self,
        repository: Repository,
        provider: LLMProvider,
        tools: ToolRegistry,
        auto_approve: bool = False,
    ):
        self.repository = repository
        self.provider = provider
        self.tools = tools
        self.auto_approve = auto_approve
        self.manager = ManagerAgent()
        self.planner = PlannerAgent()
        self.critic = CriticAgent(provider, repository)
        self._run_locks: dict[str, threading.Lock] = {}
        self._lock_guard = threading.Lock()

    def create_run(self, objective: str, context: Optional[dict[str, Any]] = None) -> Run:
        if not objective.strip():
            raise ValueError("Objective cannot be empty")
        run = Run(objective=objective.strip(), context=context or {})
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
        if run.status in {RunStatus.COMPLETED, RunStatus.REJECTED}:
            return run
        run.status = RunStatus.RUNNING
        run.updated_at = utc_now()
        self.repository.save_run(run)
        self.repository.add_event(run.id, "run.started", "manager", {})
        try:
            if not run.plan:
                memories = self.repository.search_memories(extract_terms(run.objective))
                agent_context = AgentContext(run=run, memories=memories)
                delegation = self.manager.delegate(agent_context)
                run.plan = self.planner.create_plan(agent_context)
                run.context["delegation"] = delegation
                self.repository.save_run(run)
                self.repository.add_event(
                    run.id,
                    "plan.created",
                    "planner",
                    {"steps": [step.to_dict() for step in run.plan]},
                )

            approved = set(run.context.get("_approved_steps", []))
            prior_outputs = [step.output for step in run.plan if step.output]
            for step in run.plan:
                if step.status == StepStatus.COMPLETED:
                    continue
                if step.risk.value == "high" and not self.auto_approve and step.id not in approved:
                    step.status = StepStatus.WAITING_APPROVAL
                    run.status = RunStatus.WAITING_APPROVAL
                    run.updated_at = utc_now()
                    self.repository.save_run(run)
                    self.repository.add_event(
                        run.id,
                        "approval.requested",
                        "policy",
                        {"step_id": step.id, "title": step.title, "risk": step.risk.value},
                    )
                    return run
                step.status = StepStatus.RUNNING
                self.repository.save_run(run)
                self.repository.add_event(
                    run.id, "step.started", step.agent, {"step_id": step.id, "tool": step.tool}
                )
                tool = self.tools.get(step.tool)
                step.output = tool.execute(
                    ToolContext(
                        run_id=run.id,
                        objective=run.objective,
                        instruction=step.instruction,
                        prior_outputs=prior_outputs,
                        inputs=run.context,
                    )
                )
                prior_outputs.append(step.output)
                step.status = StepStatus.COMPLETED
                self.repository.save_run(run)
                self.repository.add_event(
                    run.id,
                    "step.completed",
                    step.agent,
                    {"step_id": step.id, "output": step.output},
                )

            review = self.critic.evaluate(run)
            run.result = {
                "summary": "All delegated tasks completed successfully.",
                "artifacts": prior_outputs,
                "review": review,
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
            self.repository.save_run(run)
            self.repository.add_event(run.id, "approval.rejected", "human", {"step_id": step.id})
            return run
        approved_steps = set(run.context.get("_approved_steps", []))
        approved_steps.add(step.id)
        run.context["_approved_steps"] = sorted(approved_steps)
        step.status = StepStatus.PENDING
        run.status = RunStatus.QUEUED
        run.updated_at = utc_now()
        self.repository.save_run(run)
        self.repository.add_event(run.id, "approval.granted", "human", {"step_id": step.id})
        return self.execute(run.id)

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
