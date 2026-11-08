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


def test_dashboard_exposes_evidence_and_calculation_inputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI_WORKFORCE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("AI_WORKFORCE_OUTBOX", str(tmp_path / "outbox"))
    get_orchestrator.cache_clear()
    client = TestClient(create_app())

    dashboard = client.get("/")

    assert dashboard.status_code == 200
    assert 'id="sources"' in dashboard.text
    assert 'id="expression"' in dashboard.text
    assert 'id="recipient"' in dashboard.text
    get_orchestrator.cache_clear()


def test_dashboard_accessibility_markup() -> None:
    static = Path(__file__).resolve().parents[1] / "src" / "ai_workforce" / "static"
    html = (static / "index.html").read_text()
    css = (static / "styles.css").read_text()
    js = (static / "app.js").read_text()

    assert 'class="skip-link"' in html and 'id="main"' in html
    assert 'id="toast"' in html and 'role="status"' in html
    assert 'id="toast-error"' in html and 'role="alert"' in html
    assert 'id="sr-status"' in html
    assert ":focus-visible" in css and "prefers-reduced-motion" in css
    # Run entries must be real buttons, and status must be rendered as text.
    assert 'class="btn run-card' in js
    assert "step-status" in js and "label(run.status)" in js
