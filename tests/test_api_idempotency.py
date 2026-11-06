"""Regression tests for issue #4: repeated requests cannot duplicate or overturn a decision."""

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ai_workforce.app import create_app, get_orchestrator
from ai_workforce.db import Repository
from ai_workforce.llm import DemoProvider
from ai_workforce.models import RunStatus
from ai_workforce.orchestrator import InvalidTransition, WorkforceOrchestrator
from ai_workforce.tools import ToolRegistry


@dataclass
class Api:
    client: TestClient
    orchestrator: WorkforceOrchestrator
    outbox: Path

    def start_waiting_run(self) -> tuple[str, str]:
        response = self.client.post(
            "/api/runs",
            json={
                "objective": "Research and send a launch brief",
                "context": {"send_message": True, "recipient": "sponsor@example.com"},
            },
        )
        assert response.status_code == 202
        run_id = response.json()["id"]
        detail = self.detail(run_id)
        assert detail["status"] == "waiting_approval"
        step_id = next(s["id"] for s in detail["plan"] if s["status"] == "waiting_approval")
        return run_id, step_id

    def decide(self, run_id: str, step_id: str, approved: bool) -> int:
        return self.client.post(
            f"/api/runs/{run_id}/approval", json={"step_id": step_id, "approved": approved}
        ).status_code

    def detail(self, run_id: str) -> dict[str, Any]:
        return self.client.get(f"/api/runs/{run_id}").json()

    def event_types(self, run_id: str) -> list[str]:
        return [event["type"] for event in self.detail(run_id)["events"]]

    def outbox_count(self) -> int:
        return len(list(self.outbox.glob("*.json"))) if self.outbox.exists() else 0

    def message_executions(self, run_id: str) -> int:
        return sum(
            1
            for event in self.detail(run_id)["events"]
            if event["type"] == "step.started" and event["payload"]["tool"] == "app.message"
        )


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Api]:
    monkeypatch.setenv("AI_WORKFORCE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("AI_WORKFORCE_OUTBOX", str(tmp_path / "outbox"))
    monkeypatch.setenv("AI_WORKFORCE_PROVIDER", "demo")
    monkeypatch.setenv("AI_WORKFORCE_AUTO_APPROVE", "false")
    get_orchestrator.cache_clear()
    yield Api(TestClient(create_app()), get_orchestrator(), tmp_path / "outbox")
    get_orchestrator.cache_clear()


def force_stale_reads(
    monkeypatch: pytest.MonkeyPatch, repository: Repository, parties: int
) -> None:
    """Hold the next `parties` run reads until all have read, forcing the check-then-act race."""
    barrier = threading.Barrier(parties, timeout=10)
    remaining = [parties]
    guard = threading.Lock()
    original = repository.get_run

    def synchronized_get_run(run_id: str) -> Any:
        run = original(run_id)
        with guard:
            armed = remaining[0] > 0
            remaining[0] -= 1
        if armed:
            barrier.wait()
        return run

    monkeypatch.setattr(repository, "get_run", synchronized_get_run)


def test_repeated_start_while_waiting_changes_nothing(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()
    events_before = api.event_types(run_id)

    responses = [api.client.post(f"/api/runs/{run_id}/start").status_code for _ in range(3)]

    assert responses == [202, 202, 202]
    detail = api.detail(run_id)
    assert detail["status"] == "waiting_approval"
    assert next(s["id"] for s in detail["plan"] if s["status"] == "waiting_approval") == step_id
    assert api.event_types(run_id) == events_before
    assert api.event_types(run_id).count("approval.requested") == 1
    assert api.outbox_count() == 0


def test_repeated_approval_executes_the_message_once(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()

    assert [api.decide(run_id, step_id, True) for _ in range(3)] == [200, 409, 409]

    assert api.detail(run_id)["status"] == "completed"
    assert api.outbox_count() == 1
    assert api.message_executions(run_id) == 1
    assert api.event_types(run_id).count("approval.granted") == 1


def test_repeated_start_after_completion_changes_nothing(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()
    assert api.decide(run_id, step_id, True) == 200
    events_before = api.event_types(run_id)

    for _ in range(3):
        assert api.client.post(f"/api/runs/{run_id}/start").status_code == 202

    assert api.event_types(run_id) == events_before
    assert api.outbox_count() == 1
    assert api.message_executions(run_id) == 1


def test_approval_decision_survives_a_later_reversal(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()
    assert api.decide(run_id, step_id, True) == 200

    assert api.decide(run_id, step_id, False) == 409

    assert api.detail(run_id)["status"] == "completed"
    event_types = api.event_types(run_id)
    assert event_types.count("approval.granted") == 1
    assert "approval.rejected" not in event_types


def test_rejection_survives_a_later_approval(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()
    assert api.decide(run_id, step_id, False) == 200

    assert api.decide(run_id, step_id, True) == 409
    assert api.client.post(f"/api/runs/{run_id}/start").status_code == 202

    assert api.detail(run_id)["status"] == "rejected"
    assert api.outbox_count() == 0
    assert api.message_executions(run_id) == 0
    event_types = api.event_types(run_id)
    assert event_types.count("approval.rejected") == 1
    assert "approval.granted" not in event_types


def test_approval_is_bound_to_the_exact_step(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()
    other_run_id, _ = api.start_waiting_run()

    assert api.decide(run_id, "step_does_not_exist", True) == 409
    assert api.decide(other_run_id, step_id, True) == 409

    assert api.detail(run_id)["status"] == "waiting_approval"
    assert api.detail(other_run_id)["status"] == "waiting_approval"
    assert api.outbox_count() == 0


def test_concurrent_approve_and_reject_record_exactly_one_decision(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, step_id = api.start_waiting_run()
    force_stale_reads(monkeypatch, api.orchestrator.repository, parties=2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        approve = pool.submit(api.decide, run_id, step_id, True)
        reject = pool.submit(api.decide, run_id, step_id, False)
    codes = sorted([approve.result(), reject.result()])

    assert codes == [200, 409]
    event_types = api.event_types(run_id)
    granted = event_types.count("approval.granted")
    rejected = event_types.count("approval.rejected")
    assert granted + rejected == 1
    status = api.detail(run_id)["status"]
    if granted:
        assert (status, api.outbox_count()) == ("completed", 1)
    else:
        assert (status, api.outbox_count()) == ("rejected", 0)


def test_concurrent_approvals_record_one_grant_and_one_message(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, step_id = api.start_waiting_run()
    force_stale_reads(monkeypatch, api.orchestrator.repository, parties=2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(lambda _: api.decide(run_id, step_id, True), range(2)))

    assert codes == [200, 409]
    assert api.event_types(run_id).count("approval.granted") == 1
    assert api.outbox_count() == 1
    assert api.message_executions(run_id) == 1


def test_approval_racing_start_requests_sends_one_message(api: Api) -> None:
    run_id, step_id = api.start_waiting_run()

    with ThreadPoolExecutor(max_workers=6) as pool:
        starts = [
            pool.submit(api.client.post, f"/api/runs/{run_id}/start") for _ in range(5)
        ]
        decision = pool.submit(api.decide, run_id, step_id, True)
    assert [future.result().status_code for future in starts] == [202] * 5
    assert decision.result() == 200

    assert api.client.post(f"/api/runs/{run_id}/start").status_code == 202
    assert api.detail(run_id)["status"] == "completed"
    assert api.outbox_count() == 1
    assert api.message_executions(run_id) == 1
    assert api.event_types(run_id).count("approval.granted") == 1


def test_decision_is_enforced_across_orchestrator_instances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two API workers share a database but not in-process locks."""
    database = str(tmp_path / "shared.db")
    outbox = tmp_path / "outbox"
    first = WorkforceOrchestrator(
        Repository(database), DemoProvider(), ToolRegistry.defaults(str(outbox))
    )
    second = WorkforceOrchestrator(
        Repository(database), DemoProvider(), ToolRegistry.defaults(str(outbox))
    )
    run = first.execute(first.create_run("Draft and send a memo", {"send_message": True}).id)
    step = next(item for item in run.plan if item.status.value == "waiting_approval")

    barrier = threading.Barrier(2, timeout=10)
    for orchestrator in (first, second):
        original = orchestrator.repository.get_run
        calls = [0]

        def synchronized(run_id: str, original=original, calls=calls) -> Any:
            value = original(run_id)
            calls[0] += 1
            if calls[0] == 1:
                barrier.wait()
            return value

        monkeypatch.setattr(orchestrator.repository, "get_run", synchronized)

    def decide(orchestrator: WorkforceOrchestrator, approved: bool) -> str:
        try:
            return orchestrator.resolve_approval(run.id, step.id, approved).status.value
        except InvalidTransition:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        approve = pool.submit(decide, first, True)
        reject = pool.submit(decide, second, False)
    outcomes = [approve.result(), reject.result()]

    assert outcomes.count("conflict") == 1
    final = first.repository.get_run(run.id)
    events = [event["type"] for event in first.repository.get_events(run.id)]
    assert events.count("approval.granted") + events.count("approval.rejected") == 1
    delivered = len(list(outbox.glob("*.json"))) if outbox.exists() else 0
    assert delivered == (1 if final.status == RunStatus.COMPLETED else 0)
