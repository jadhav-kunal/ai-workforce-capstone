import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from .models import PlanStep, RiskLevel, Run, RunStatus, StepStatus, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    context_json TEXT NOT NULL,
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    agent TEXT NOT NULL,
    tool TEXT NOT NULL,
    instruction TEXT NOT NULL,
    risk TEXT NOT NULL,
    status TEXT NOT NULL,
    output_json TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objective_key TEXT NOT NULL,
    lesson TEXT NOT NULL,
    score REAL NOT NULL,
    source_run_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id, position);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, id);
CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(objective_key, score DESC);
"""


class Repository:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._lock, self.connection() as connection:
            connection.executescript(SCHEMA)

    def save_run(self, run: Run) -> None:
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO runs
                (id, objective, status, context_json, result_json, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status,
                context_json=excluded.context_json, result_json=excluded.result_json,
                error=excluded.error, updated_at=excluded.updated_at""",
                (
                    run.id,
                    run.objective,
                    run.status.value,
                    json.dumps(run.context),
                    json.dumps(run.result) if run.result is not None else None,
                    run.error,
                    run.created_at,
                    run.updated_at,
                ),
            )
            connection.execute("DELETE FROM steps WHERE run_id = ?", (run.id,))
            connection.executemany(
                """INSERT INTO steps
                (id, run_id, position, title, agent, tool, instruction, risk, status, output_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        step.id,
                        run.id,
                        index,
                        step.title,
                        step.agent,
                        step.tool,
                        step.instruction,
                        step.risk.value,
                        step.status.value,
                        json.dumps(step.output) if step.output is not None else None,
                    )
                    for index, step in enumerate(run.plan)
                ],
            )

    def get_run(self, run_id: str) -> Optional[Run]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            step_rows = connection.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY position", (run_id,)
            ).fetchall()
        run = Run(
            id=row["id"],
            objective=row["objective"],
            status=RunStatus(row["status"]),
            context=json.loads(row["context_json"]),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        run.plan = [
            PlanStep(
                id=step["id"],
                title=step["title"],
                agent=step["agent"],
                tool=step["tool"],
                instruction=step["instruction"],
                risk=RiskLevel(step["risk"]),
                status=StepStatus(step["status"]),
                output=json.loads(step["output_json"]) if step["output_json"] else None,
            )
            for step in step_rows
        ]
        return run

    def list_runs(self, limit: int = 50) -> list[Run]:
        with self.connection() as connection:
            ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            ]
        return [run for run_id in ids if (run := self.get_run(run_id)) is not None]

    def add_event(self, run_id: str, event_type: str, actor: str, payload: dict[str, Any]) -> None:
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO events
                (run_id, event_type, actor, payload_json, created_at) VALUES(?,?,?,?,?)""",
                (run_id, event_type, actor, json.dumps(payload), utc_now()),
            )

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "type": row["event_type"],
                "actor": row["actor"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def add_memory(self, objective_key: str, lesson: str, score: float, run_id: str) -> None:
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO memories
                (objective_key, lesson, score, source_run_id, created_at) VALUES(?,?,?,?,?)""",
                (objective_key, lesson, score, run_id, utc_now()),
            )

    def search_memories(self, terms: list[str], limit: int = 5) -> list[dict[str, Any]]:
        if not terms:
            return []
        patterns = [f"%{term.lower()}%" for term in terms[:8]]
        where = " OR ".join(["lower(objective_key) LIKE ?"] * len(patterns))
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM memories WHERE {where} ORDER BY score DESC, id DESC LIMIT ?",
                (*patterns, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def metrics(self) -> dict[str, Any]:
        with self.connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            completed = connection.execute(
                "SELECT COUNT(*) FROM runs WHERE status = 'completed'"
            ).fetchone()[0]
            waiting = connection.execute(
                "SELECT COUNT(*) FROM runs WHERE status = 'waiting_approval'"
            ).fetchone()[0]
            failed = connection.execute(
                "SELECT COUNT(*) FROM runs WHERE status IN ('failed','rejected')"
            ).fetchone()[0]
            memories = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        return {
            "total_runs": total,
            "completed_runs": completed,
            "waiting_approval": waiting,
            "failed_runs": failed,
            "success_rate": round(completed / total, 3) if total else 0,
            "lessons_learned": memories,
        }
