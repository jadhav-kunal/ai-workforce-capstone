from pathlib import Path
from typing import Optional

from ai_workforce.db import Repository
from ai_workforce.llm import DemoProvider
from ai_workforce.models import RunStatus
from ai_workforce.orchestrator import ExecutionConfig, WorkforceOrchestrator
from ai_workforce.tools import (
    AppMessageTool,
    KnowledgeSearchTool,
    SafeCalculatorTool,
    SynthesisTool,
    ToolContext,
    ToolRegistry,
)


class RecordingDemoProvider(DemoProvider):
    def __init__(self) -> None:
        self.plan_requests: list[dict] = []

    def create_plan(self, request: dict) -> dict:
        self.plan_requests.append(request)
        return super().create_plan(request)


class RepairingProvider(DemoProvider):
    def __init__(self) -> None:
        self.plan_calls = 0

    def create_plan(self, request: dict) -> dict:
        self.plan_calls += 1
        if self.plan_calls == 1:
            return {
                "steps": [
                    {
                        "title": "Use an unavailable connector",
                        "agent": "researcher",
                        "tool": "unknown.connector",
                        "instruction": "Attempt an invalid action.",
                        "arguments": {},
                    }
                ]
            }
        return super().create_plan(request)


class WrongRecipientProvider(DemoProvider):
    def create_plan(self, request: dict) -> dict:
        plan = super().create_plan(request)
        for step in plan["steps"]:
            if step["tool"] == "app.message":
                step["arguments"]["recipient"] = "attacker@example.com"
        return plan


class DirectMessageProvider(DemoProvider):
    def create_plan(self, request: dict) -> dict:
        return {
            "steps": [
                {
                    "title": "Send without a grounded draft",
                    "agent": "operator",
                    "tool": "app.message",
                    "instruction": "Attempt to bypass the writer and critic.",
                    "arguments": {"recipient": request["context"].get("recipient")},
                }
            ]
        }


class TransientCalculatorTool(SafeCalculatorTool):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, context: ToolContext) -> dict:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("temporary calculator outage")
        return super().execute(context)


class UngroundedSynthesisTool(SynthesisTool):
    def execute(self, context: ToolContext) -> dict:
        return {
            "deliverable": {
                "title": "Unsupported brief",
                "executive_summary": "An unsupported number was introduced.",
                "claims": [
                    {
                        "text": "Performance improved by 99%.",
                        "citations": [],
                        "kind": "evidence",
                    }
                ],
                "recommendations": [],
            }
        }


def build_workforce(
    tmp_path: Path,
    provider: DemoProvider,
    calculator: Optional[SafeCalculatorTool] = None,
    synthesis: Optional[SynthesisTool] = None,
) -> WorkforceOrchestrator:
    registry = ToolRegistry(
        [
            KnowledgeSearchTool(),
            calculator or SafeCalculatorTool(),
            synthesis or SynthesisTool(),
            AppMessageTool(str(tmp_path / "outbox")),
        ]
    )
    return WorkforceOrchestrator(Repository(str(tmp_path / "test.db")), provider, registry)


def test_no_message_run_completes_and_learns(workforce: tuple[WorkforceOrchestrator, Path]) -> None:
    orchestrator, outbox = workforce
    run = orchestrator.create_run(
        "Analyze support pilot evidence",
        {"sources": [{"title": "Pilot", "content": "91% passed"}], "send_message": False},
    )
    run = orchestrator.execute(run.id)

    assert run.status == RunStatus.COMPLETED
    assert run.result["review"]["checks"]["all_steps_completed"] is True
    assert run.result["review"]["grounding"]["passed"] is True
    assert run.result["review"]["grounding"]["claim_verdicts"][0]["citations"] == ["S1"]
    assert not outbox.exists()
    assert orchestrator.repository.metrics()["lessons_learned"] == 1


def test_invalid_model_plan_is_repaired_once(tmp_path: Path) -> None:
    provider = RepairingProvider()
    orchestrator = build_workforce(tmp_path, provider)
    run = orchestrator.create_run("Analyze support evidence", {"send_message": False})
    completed = orchestrator.execute(run.id)

    assert completed.status == RunStatus.COMPLETED
    assert completed.result["execution"]["planner"] == "model_repair"
    assert completed.result["execution"]["repairs"] == 1
    event_types = [event["type"] for event in orchestrator.repository.get_events(run.id)]
    assert "plan.invalid" in event_types
    assert "plan.repaired" in event_types


def test_invalid_recipient_falls_back_to_user_pinned_value(tmp_path: Path) -> None:
    orchestrator = build_workforce(tmp_path, WrongRecipientProvider())
    run = orchestrator.create_run(
        "Draft and send a pilot update",
        {"send_message": True, "recipient": "sponsor@example.com"},
    )
    waiting = orchestrator.execute(run.id)

    assert waiting.status == RunStatus.WAITING_APPROVAL
    assert waiting.context["_plan_source"] == "deterministic_fallback"
    message_step = next(step for step in waiting.plan if step.tool == "app.message")
    assert message_step.arguments["recipient"] == "sponsor@example.com"


def test_message_cannot_bypass_synthesis_and_grounding(tmp_path: Path) -> None:
    orchestrator = build_workforce(tmp_path, DirectMessageProvider())
    run = orchestrator.create_run(
        "Send a grounded pilot update",
        {"send_message": True, "recipient": "sponsor@example.com"},
    )
    waiting = orchestrator.execute(run.id)

    assert waiting.status == RunStatus.WAITING_APPROVAL
    assert waiting.context["_plan_source"] == "deterministic_fallback"
    assert [step.tool for step in waiting.plan][-2:] == ["content.synthesize", "app.message"]
    assert waiting.context["_draft_review"]["passed"] is True


def test_recoverable_tool_error_triggers_bounded_replan(tmp_path: Path) -> None:
    calculator = TransientCalculatorTool()
    provider = RecordingDemoProvider()
    orchestrator = build_workforce(tmp_path, provider, calculator)
    run = orchestrator.create_run(
        "Calculate the support pilot result",
        {"expression": "1200 * 0.42", "send_message": False},
    )
    completed = orchestrator.execute(run.id)

    assert completed.status == RunStatus.COMPLETED
    assert completed.result["execution"]["replans"] == 1
    assert completed.result["execution"]["step_attempts"] == 4
    observation = {
        "tool": "data.calculate",
        "step_id": next(
            event["payload"]["step_id"]
            for event in orchestrator.repository.get_events(run.id)
            if event["type"] == "step.failed"
        ),
        "error": "TimeoutError: temporary calculator outage",
    }
    assert completed.context["_observations"] == [observation]
    assert provider.plan_requests[1]["observations"] == [observation]
    assert provider.plan_requests[1]["remaining_step_budget"] == 6
    event_types = [event["type"] for event in orchestrator.repository.get_events(run.id)]
    assert "step.failed" in event_types
    assert "step.observed" in event_types
    assert "plan.replanned" in event_types


def test_failed_grounding_uses_two_replans_then_stops(tmp_path: Path) -> None:
    orchestrator = build_workforce(tmp_path, DemoProvider(), synthesis=UngroundedSynthesisTool())
    orchestrator.config = ExecutionConfig(max_replans=5)
    run = orchestrator.create_run(
        "Analyze grounded pilot evidence",
        {
            "sources": [{"title": "Pilot", "content": "The pilot passed 91% of tests."}],
            "send_message": False,
        },
    )
    failed = orchestrator.execute(run.id)

    assert failed.status == RunStatus.FAILED
    assert failed.context["_replans"] == 2
    assert failed.context["delegation"]["budget"]["max_replans"] == 2
    assert len(failed.context["_observations"]) == 3
    assert "Grounding review failed" in failed.error
    event_types = [event["type"] for event in orchestrator.repository.get_events(run.id)]
    assert event_types.count("plan.replanned") == 2
    assert event_types.count("step.observed") == 3
    assert "critic.flagged" in event_types


def test_high_risk_action_waits_then_executes_once(
    workforce: tuple[WorkforceOrchestrator, Path],
) -> None:
    orchestrator, outbox = workforce
    run = orchestrator.create_run("Research a pilot and notify the sponsor", {"send_message": True})
    waiting = orchestrator.execute(run.id)

    assert waiting.status == RunStatus.WAITING_APPROVAL
    assert not list(outbox.glob("*.json")) if outbox.exists() else True
    step = next(item for item in waiting.plan if item.status.value == "waiting_approval")
    completed = orchestrator.resolve_approval(waiting.id, step.id, True)

    assert completed.status == RunStatus.COMPLETED
    assert len(list(outbox.glob("*.json"))) == 1
    orchestrator.execute(completed.id)
    assert len(list(outbox.glob("*.json"))) == 1
    event_types = [event["type"] for event in orchestrator.repository.get_events(completed.id)]
    assert "approval.requested" in event_types
    assert "approval.granted" in event_types


def test_rejection_is_terminal_and_has_no_side_effect(
    workforce: tuple[WorkforceOrchestrator, Path],
) -> None:
    orchestrator, outbox = workforce
    run = orchestrator.create_run("Draft and send a memo")
    waiting = orchestrator.execute(run.id)
    step = next(item for item in waiting.plan if item.status.value == "waiting_approval")
    rejected = orchestrator.resolve_approval(waiting.id, step.id, False)

    assert rejected.status == RunStatus.REJECTED
    assert orchestrator.execute(rejected.id).status == RunStatus.REJECTED
    assert not outbox.exists()


def test_related_run_receives_prior_lesson(workforce: tuple[WorkforceOrchestrator, Path]) -> None:
    orchestrator, _ = workforce
    first = orchestrator.create_run("Analyze support pilot evidence", {"send_message": False})
    assert orchestrator.execute(first.id).status == RunStatus.COMPLETED

    second = orchestrator.create_run("Review support pilot risks", {"send_message": False})
    second = orchestrator.execute(second.id)
    assert second.context["delegation"]["prior_lessons"]


def test_malicious_expression_fails_without_execution(
    workforce: tuple[WorkforceOrchestrator, Path],
) -> None:
    orchestrator, _ = workforce
    run = orchestrator.create_run(
        "Calculate unsafe input",
        {"expression": "__import__('os').system('false')", "send_message": False},
    )
    failed = orchestrator.execute(run.id)
    assert failed.status == RunStatus.FAILED
    assert "Invalid calculation" in failed.error
