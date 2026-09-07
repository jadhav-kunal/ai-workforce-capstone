from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PlanStep:
    title: str
    agent: str
    tool: str
    instruction: str
    risk: RiskLevel = RiskLevel.LOW
    id: str = field(default_factory=lambda: new_id("step"))
    status: StepStatus = StepStatus.PENDING
    output: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["risk"] = self.risk.value
        value["status"] = self.status.value
        return value


@dataclass
class Run:
    objective: str
    id: str = field(default_factory=lambda: new_id("run"))
    status: RunStatus = RunStatus.QUEUED
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    context: dict[str, Any] = field(default_factory=dict)
    plan: list[PlanStep] = field(default_factory=list)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context": self.context,
            "plan": [step.to_dict() for step in self.plan],
            "result": self.result,
            "error": self.error,
        }
