import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("AI_WORKFORCE_PROVIDER", "demo"))
    model: str = field(default_factory=lambda: os.getenv("AI_WORKFORCE_MODEL", "gpt-4o-mini"))
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    database_path: str = field(
        default_factory=lambda: os.getenv("AI_WORKFORCE_DB", "data/workforce.db")
    )
    outbox_path: str = field(
        default_factory=lambda: os.getenv("AI_WORKFORCE_OUTBOX", "data/outbox")
    )
    auto_approve: bool = field(
        default_factory=lambda: _as_bool(os.getenv("AI_WORKFORCE_AUTO_APPROVE", "false"))
    )
    host: str = field(default_factory=lambda: os.getenv("AI_WORKFORCE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("AI_WORKFORCE_PORT", "8000")))

    def ensure_directories(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.outbox_path).mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    if settings.provider == "openai" and not settings.api_key:
        raise ValueError("OPENAI_API_KEY is required when AI_WORKFORCE_PROVIDER=openai")
    return settings
