from pathlib import Path

import pytest

from ai_workforce.db import Repository
from ai_workforce.llm import DemoProvider
from ai_workforce.orchestrator import WorkforceOrchestrator
from ai_workforce.tools import (
    AppMessageTool,
    KnowledgeSearchTool,
    SafeCalculatorTool,
    SynthesisTool,
    ToolRegistry,
)


@pytest.fixture
def workforce(tmp_path: Path) -> tuple[WorkforceOrchestrator, Path]:
    outbox = tmp_path / "outbox"
    registry = ToolRegistry(
        [
            KnowledgeSearchTool(),
            SafeCalculatorTool(),
            SynthesisTool(),
            AppMessageTool(str(outbox)),
        ]
    )
    orchestrator = WorkforceOrchestrator(
        Repository(str(tmp_path / "test.db")), DemoProvider(), registry
    )
    return orchestrator, outbox
