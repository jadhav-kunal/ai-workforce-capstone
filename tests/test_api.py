from pathlib import Path

from fastapi.testclient import TestClient

from ai_workforce.app import create_app, get_orchestrator


def test_api_lifecycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI_WORKFORCE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("AI_WORKFORCE_OUTBOX", str(tmp_path / "outbox"))
    monkeypatch.setenv("AI_WORKFORCE_PROVIDER", "demo")
    get_orchestrator.cache_clear()
    client = TestClient(create_app())

    assert client.get("/health").json()["status"] == "ok"
    response = client.post(
        "/api/runs",
        json={"objective": "Research and send a launch brief", "context": {"send_message": True}},
    )
    assert response.status_code == 202
    run_id = response.json()["id"]
    detail = client.get(f"/api/runs/{run_id}").json()
    assert detail["status"] == "waiting_approval"
    waiting = next(step for step in detail["plan"] if step["status"] == "waiting_approval")

    approved = client.post(
        f"/api/runs/{run_id}/approval",
        json={"step_id": waiting["id"], "approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert client.get("/api/metrics").json()["completed_runs"] == 1
    get_orchestrator.cache_clear()


def test_api_validates_empty_objective(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI_WORKFORCE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("AI_WORKFORCE_OUTBOX", str(tmp_path / "outbox"))
    get_orchestrator.cache_clear()
    client = TestClient(create_app())
    assert client.post("/api/runs", json={"objective": ""}).status_code == 422
    get_orchestrator.cache_clear()
