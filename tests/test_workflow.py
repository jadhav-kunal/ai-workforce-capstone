from pathlib import Path

from ai_workforce.models import RunStatus
from ai_workforce.orchestrator import WorkforceOrchestrator


def test_no_message_run_completes_and_learns(workforce: tuple[WorkforceOrchestrator, Path]) -> None:
    orchestrator, outbox = workforce
    run = orchestrator.create_run(
        "Analyze support pilot evidence",
        {"sources": [{"title": "Pilot", "content": "91% passed"}], "send_message": False},
    )
    run = orchestrator.execute(run.id)

    assert run.status == RunStatus.COMPLETED
    assert run.result["review"]["checks"]["all_steps_completed"] is True
    assert not outbox.exists()
    assert orchestrator.repository.metrics()["lessons_learned"] == 1


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
