from dataclasses import dataclass
from typing import Any

from .db import Repository
from .llm import LLMProvider, extract_terms
from .models import PlanStep, RiskLevel, Run


@dataclass
class AgentContext:
    run: Run
    memories: list[dict[str, Any]]


class ManagerAgent:
    name = "manager"

    def delegate(self, context: AgentContext) -> dict[str, Any]:
        return {
            "objective": context.run.objective,
            "strategy": "research -> synthesize -> act -> reflect",
            "prior_lessons": [memory["lesson"] for memory in context.memories],
        }


class PlannerAgent:
    name = "planner"

    def create_plan(self, context: AgentContext) -> list[PlanStep]:
        run = context.run
        plan = [
            PlanStep(
                title="Research the objective",
                agent="researcher",
                tool="knowledge.search",
                instruction="Collect the relevant evidence supplied with the objective.",
            )
        ]
        if run.context.get("expression"):
            plan.append(
                PlanStep(
                    title="Calculate requested metric",
                    agent="analyst",
                    tool="data.calculate",
                    instruction="Calculate the numeric input using the sandboxed arithmetic tool.",
                )
            )
        plan.append(
            PlanStep(
                title="Synthesize an action brief",
                agent="writer",
                tool="content.synthesize",
                instruction="Create an evidence-linked executive brief with recommendations.",
            )
        )
        if run.context.get("send_message", True):
            plan.append(
                PlanStep(
                    title="Queue the stakeholder update",
                    agent="operator",
                    tool="app.message",
                    instruction=(
                        "Prepare the stakeholder message and place it in the simulated outbox."
                    ),
                    risk=RiskLevel.HIGH,
                )
            )
        return plan


class CriticAgent:
    name = "critic"

    def __init__(self, provider: LLMProvider, repository: Repository):
        self.provider = provider
        self.repository = repository

    def evaluate(self, run: Run) -> dict[str, Any]:
        completed = [step for step in run.plan if step.output]
        evidence_count = sum(
            int(step.output.get("source_count", 0)) for step in completed if step.output
        )
        score = min(1.0, 0.55 + 0.1 * len(completed) + (0.1 if evidence_count else 0))
        reflection = self.provider.complete(
            "You are a concise quality critic for an autonomous agent system.",
            "Review this objective and execution trace: {}; completed steps: {}".format(
                run.objective, ", ".join(step.title for step in completed)
            ),
        )
        focus = ", ".join(extract_terms(run.objective)[:3]) or "general work"
        lesson = (
            f"For objectives involving {focus}, preserve evidence provenance and require "
            "approval before outbound communication."
        )
        self.repository.add_memory(" ".join(extract_terms(run.objective)), lesson, score, run.id)
        return {
            "quality_score": round(score, 2),
            "reflection": reflection,
            "lesson_saved": lesson,
            "checks": {
                "has_evidence": evidence_count > 0,
                "all_steps_completed": len(completed) == len(run.plan),
                "external_action_guarded": all(
                    step.risk != RiskLevel.HIGH or step.output is not None for step in run.plan
                ),
            },
        }
