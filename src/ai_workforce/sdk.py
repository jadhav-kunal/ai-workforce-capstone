from typing import Any, Optional

from .config import Settings, get_settings
from .db import Repository
from .llm import create_provider
from .models import Run
from .orchestrator import WorkforceOrchestrator
from .tools import ToolRegistry


class Workforce:
    """Five-line-friendly SDK facade around the full orchestration service."""

    def __init__(self, settings: Optional[Settings] = None):
        configured = settings or get_settings()
        self.orchestrator = WorkforceOrchestrator(
            Repository(configured.database_path),
            create_provider(
                configured.provider,
                configured.api_key,
                configured.model,
                configured.base_url,
            ),
            ToolRegistry.defaults(configured.outbox_path),
            configured.auto_approve,
        )

    def delegate(self, objective: str, **context: Any) -> Run:
        run = self.orchestrator.create_run(objective, context)
        return self.orchestrator.execute(run.id)

    def approve(self, run_id: str, step_id: str) -> Run:
        return self.orchestrator.resolve_approval(run_id, step_id, True)

    def reject(self, run_id: str, step_id: str) -> Run:
        return self.orchestrator.resolve_approval(run_id, step_id, False)

    def inspect(self, run_id: str) -> dict[str, Any]:
        return self.orchestrator.detail(run_id)
