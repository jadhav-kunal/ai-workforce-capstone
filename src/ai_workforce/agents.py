import re
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .db import Repository
from .llm import LLMError, LLMProvider, extract_terms
from .models import PlanStep, Run
from .tools import ToolError, ToolRegistry

MAX_STEPS_PER_RUN = 8
MAX_REPLANS_PER_RUN = 2


class PlanValidationError(ValueError):
    pass


class ProposedStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=120)
    agent: str = Field(min_length=2, max_length=40)
    tool: str = Field(min_length=3, max_length=80)
    instruction: str = Field(min_length=3, max_length=500)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ProposedPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[ProposedStep] = Field(min_length=1, max_length=8)


@dataclass
class AgentContext:
    run: Run
    memories: list[dict[str, Any]]


class ManagerAgent:
    name = "manager"

    def delegate(self, context: AgentContext) -> dict[str, Any]:
        return {
            "objective": context.run.objective,
            "strategy": "plan -> execute -> observe -> verify -> approve -> learn",
            "prior_lessons": [memory["lesson"] for memory in context.memories[:3]],
            "memory_sources": [memory["source_run_id"] for memory in context.memories[:3]],
            "budget": {
                "max_steps": MAX_STEPS_PER_RUN,
                "max_replans": MAX_REPLANS_PER_RUN,
                "max_repairs": 1,
            },
        }


class PlannerAgent:
    name = "planner"

    def __init__(self, provider: LLMProvider, tools: ToolRegistry):
        self.provider = provider
        self.tools = tools

    def create_plan(
        self,
        context: AgentContext,
        validation_error: Optional[str] = None,
        completed_tools: Optional[list[str]] = None,
    ) -> list[PlanStep]:
        completed_tools = completed_tools or []
        remaining_step_budget = min(
            MAX_STEPS_PER_RUN - len(completed_tools),
            MAX_STEPS_PER_RUN - int(context.run.context.get("_step_attempts", 0)),
        )
        public_context = {
            key: value for key, value in context.run.context.items() if not key.startswith("_")
        }
        request = {
            "objective": context.run.objective,
            "context": public_context,
            "tools": self.tools.catalog(),
            "lessons": [memory["lesson"] for memory in context.memories[:3]],
            "observations": context.run.context.get("_observations", []),
            "completed_tools": completed_tools,
            "remaining_step_budget": max(0, remaining_step_budget),
        }
        if validation_error:
            request["validation_error"] = validation_error
            request["repair_instruction"] = "Correct the plan without changing policy or recipient."
        try:
            raw_plan = self.provider.create_plan(request)
            proposal = ProposedPlan.model_validate(raw_plan)
        except (LLMError, ValidationError, TypeError, ValueError) as exc:
            raise PlanValidationError(str(exc)) from exc
        return self._validate_steps(
            context.run, proposal.steps, completed_tools, remaining_step_budget
        )

    def fallback_plan(
        self, context: AgentContext, completed_tools: Optional[list[str]] = None
    ) -> list[PlanStep]:
        completed_tools = completed_tools or []
        completed = set(completed_tools)
        run = context.run
        proposals: list[ProposedStep] = []
        if "knowledge.search" not in completed:
            proposals.append(
                ProposedStep(
                    title="Research the objective",
                    agent="researcher",
                    tool="knowledge.search",
                    instruction="Rank supplied passages and preserve their identifiers.",
                    arguments={"query": run.objective, "k": 5},
                )
            )
        if run.context.get("expression") and "data.calculate" not in completed:
            proposals.append(
                ProposedStep(
                    title="Calculate requested metric",
                    agent="analyst",
                    tool="data.calculate",
                    instruction="Evaluate the expression with the safe calculator.",
                    arguments={"expression": str(run.context["expression"])},
                )
            )
        if "content.synthesize" not in completed:
            proposals.append(
                ProposedStep(
                    title="Synthesize a grounded action brief",
                    agent="writer",
                    tool="content.synthesize",
                    instruction="Write a brief with passage and calculator citations.",
                    arguments={},
                )
            )
        if run.context.get("send_message", True) and "app.message" not in completed:
            arguments = {
                key: run.context[key]
                for key in ("channel", "recipient", "subject")
                if run.context.get(key)
            }
            proposals.append(
                ProposedStep(
                    title="Queue the stakeholder update",
                    agent="operator",
                    tool="app.message",
                    instruction="Write the approved update to the simulated outbox.",
                    arguments=arguments,
                )
            )
        if not proposals:
            raise PlanValidationError("Fallback planner produced no remaining steps")
        remaining_step_budget = min(
            MAX_STEPS_PER_RUN - len(completed_tools),
            MAX_STEPS_PER_RUN - int(run.context.get("_step_attempts", 0)),
        )
        return self._validate_steps(
            run, proposals, completed_tools, remaining_step_budget
        )

    def _validate_steps(
        self,
        run: Run,
        proposals: list[ProposedStep],
        completed_tools: list[str],
        remaining_step_budget: int,
    ) -> list[PlanStep]:
        if (
            remaining_step_budget < 0
            or len(proposals) > remaining_step_budget
            or len(completed_tools) + len(proposals) > MAX_STEPS_PER_RUN
        ):
            raise PlanValidationError("Plan exceeds the eight-step run budget")
        result: list[PlanStep] = []
        available_outputs = set(completed_tools)
        for proposal in proposals:
            try:
                tool = self.tools.get(proposal.tool)
                arguments = self.tools.validate_arguments(proposal.tool, proposal.arguments)
            except ToolError as exc:
                raise PlanValidationError(str(exc)) from exc
            if proposal.tool == "app.message":
                if "content.synthesize" not in available_outputs:
                    raise PlanValidationError(
                        "Message step requires a completed or earlier synthesis step"
                    )
                pinned_recipient = run.context.get("recipient")
                proposed_recipient = arguments.get("recipient")
                if pinned_recipient and proposed_recipient not in {None, pinned_recipient}:
                    raise PlanValidationError("Message recipient differs from the user input")
                if pinned_recipient:
                    arguments["recipient"] = pinned_recipient
            result.append(
                PlanStep(
                    title=proposal.title,
                    agent=proposal.agent,
                    tool=proposal.tool,
                    instruction=proposal.instruction,
                    arguments=arguments,
                    risk=tool.risk,
                )
            )
            available_outputs.add(proposal.tool)
        return result


class CriticAgent:
    name = "critic"

    def __init__(self, provider: LLMProvider, repository: Repository):
        self.provider = provider
        self.repository = repository

    def evaluate_draft(self, run: Run) -> dict[str, Any]:
        outputs = [step.output for step in run.plan if step.output]
        passages: dict[str, str] = {}
        calculations: list[dict[str, Any]] = []
        deliverable: dict[str, Any] = {}
        source_count = 0
        for output in outputs:
            source_count += int(output.get("source_count", 0))
            for finding in output.get("findings", []):
                passages[str(finding.get("id", ""))] = str(finding.get("content", ""))
            if "expression" in output and "value" in output:
                calculations.append(output)
            if output.get("deliverable"):
                deliverable = output["deliverable"]
        claims = deliverable.get("claims", [])
        verdicts = [
            self._check_claim(claim, passages, calculations, source_count) for claim in claims
        ]
        passed = bool(verdicts) and all(verdict["supported"] for verdict in verdicts)
        notes = [verdict["reason"] for verdict in verdicts if not verdict["supported"]]
        return {
            "passed": passed,
            "evidence_mode": "supplied_sources" if source_count else "hypothesis",
            "claim_verdicts": verdicts,
            "calculation_consistent": all(
                verdict["supported"] for verdict in verdicts if verdict["kind"] == "calculation"
            ),
            "notes": notes,
        }

    def evaluate(self, run: Run) -> dict[str, Any]:
        completed = [step for step in run.plan if step.output]
        draft_review = run.context.get("_draft_review") or self.evaluate_draft(run)
        has_external_evidence = draft_review["evidence_mode"] == "supplied_sources"
        all_completed = len(completed) == len(run.plan)
        grounded = bool(draft_review["passed"])
        score = 1.0 if grounded and has_external_evidence and all_completed else 0.85
        if not grounded or not all_completed:
            score = 0.6
        reflection = self.provider.complete(
            "You are a concise quality critic for a governed agent system.",
            f"Review objective {run.objective!r}; grounding passed={grounded}; "
            f"completed tools={[step.tool for step in completed]}.",
        )
        focus = ", ".join(extract_terms(run.objective)[:3]) or "general work"
        lesson = (
            f"For objectives involving {focus}, use passage identifiers, verify calculations, "
            "and require exact-step approval before outbound communication."
        )
        self.repository.add_memory(" ".join(extract_terms(run.objective)), lesson, score, run.id)
        approved_steps = set(run.context.get("_approved_steps", []))
        return {
            "quality_score": round(score, 2),
            "reflection": reflection,
            "grounding": draft_review,
            "lesson_saved": lesson,
            "checks": {
                "has_evidence": has_external_evidence,
                "all_steps_completed": all_completed,
                "external_action_guarded": all(
                    step.tool != "app.message" or step.id in approved_steps for step in run.plan
                ),
            },
        }

    def _check_claim(
        self,
        claim: dict[str, Any],
        passages: dict[str, str],
        calculations: list[dict[str, Any]],
        source_count: int,
    ) -> dict[str, Any]:
        text = str(claim.get("text", ""))
        kind = str(claim.get("kind", "evidence"))
        citations = [str(value) for value in claim.get("citations", [])]
        text_without_citations = re.sub(r"\[[^\]]+\]", "", text)
        if kind == "disclosure" and not source_count:
            return {
                "text": text,
                "kind": kind,
                "citations": citations,
                "supported": True,
                "reason": "The brief explicitly discloses that no source was supplied.",
            }
        invalid_citations = [
            citation for citation in citations if citation != "CALC" and citation not in passages
        ]
        support_text = " ".join(passages.get(citation, "") for citation in citations)
        if "CALC" in citations:
            support_text += " " + " ".join(
                f"{item['expression']} {item['value']}" for item in calculations
            )
        claim_numbers = self._numbers(text_without_citations)
        supported_numbers = self._numbers(support_text)
        number_ok = claim_numbers.issubset(supported_numbers)
        citation_ok = bool(citations) and not invalid_citations
        supported = citation_ok and number_ok
        if invalid_citations:
            reason = f"Unknown citation IDs: {', '.join(invalid_citations)}"
        elif not citations:
            reason = "Claim has no citation."
        elif not number_ok:
            reason = "Claim contains a number not found in its supporting observation."
        else:
            reason = "Citation and numeric checks passed."
        return {
            "text": text,
            "kind": kind,
            "citations": citations,
            "supported": supported,
            "reason": reason,
        }

    @staticmethod
    def _numbers(value: str) -> set[str]:
        return {match.replace(",", "") for match in re.findall(r"\d[\d,]*(?:\.\d+)?", value)}
