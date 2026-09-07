from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import get_settings
from .db import Repository
from .llm import create_provider
from .orchestrator import InvalidTransition, RunNotFound, WorkforceOrchestrator
from .tools import ToolRegistry


class CreateRunRequest(BaseModel):
    objective: str = Field(min_length=3, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)
    start: bool = True


class ApprovalRequest(BaseModel):
    step_id: str
    approved: bool


@lru_cache(maxsize=1)
def get_orchestrator() -> WorkforceOrchestrator:
    settings = get_settings()
    return WorkforceOrchestrator(
        repository=Repository(settings.database_path),
        provider=create_provider(
            settings.provider, settings.api_key, settings.model, settings.base_url
        ),
        tools=ToolRegistry.defaults(settings.outbox_path),
        auto_approve=settings.auto_approve,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workforce API",
        version="1.0.0",
        description="Safe, observable multi-agent workflow orchestration.",
    )
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "ai-workforce", "version": "1.0.0"}

    @app.get("/api/tools")
    def tools() -> list[dict[str, str]]:
        return get_orchestrator().tools.catalog()

    @app.post("/api/runs", status_code=202)
    def create_run(request: CreateRunRequest, background: BackgroundTasks) -> dict[str, Any]:
        orchestrator = get_orchestrator()
        run = orchestrator.create_run(request.objective, request.context)
        if request.start:
            background.add_task(orchestrator.execute, run.id)
        return run.to_dict()

    @app.get("/api/runs")
    def list_runs(limit: int = Query(default=25, ge=1, le=100)) -> list[dict[str, Any]]:
        return [run.to_dict() for run in get_orchestrator().repository.list_runs(limit)]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return get_orchestrator().detail(run_id)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc

    @app.post("/api/runs/{run_id}/start", status_code=202)
    def start_run(run_id: str, background: BackgroundTasks) -> dict[str, str]:
        if get_orchestrator().repository.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        background.add_task(get_orchestrator().execute, run_id)
        return {"run_id": run_id, "status": "accepted"}

    @app.post("/api/runs/{run_id}/approval")
    def approval(run_id: str, request: ApprovalRequest) -> dict[str, Any]:
        try:
            return (
                get_orchestrator()
                .resolve_approval(run_id, request.step_id, request.approved)
                .to_dict()
            )
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/metrics")
    def metrics() -> dict[str, Any]:
        return get_orchestrator().repository.metrics()

    return app


app = create_app()
