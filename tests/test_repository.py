from pathlib import Path

from ai_workforce.db import Repository
from ai_workforce.models import PlanStep, Run, RunStatus, StepStatus


def test_repository_round_trip_and_metrics(tmp_path: Path) -> None:
    repository = Repository(str(tmp_path / "runs.db"))
    run = Run(objective="Test durable state")
    run.plan = [
        PlanStep(
            title="Research",
            agent="researcher",
            tool="knowledge.search",
            instruction="go",
        )
    ]
    run.plan[0].status = StepStatus.COMPLETED
    run.plan[0].output = {"findings": [{"title": "Evidence"}]}
    run.status = RunStatus.COMPLETED
    run.result = {"ok": True}
    repository.save_run(run)
    repository.add_event(run.id, "run.completed", "manager", {"ok": True})
    repository.add_memory("durable state", "Persist before execution.", 0.8, run.id)

    restored = repository.get_run(run.id)
    assert restored is not None
    assert restored.status == RunStatus.COMPLETED
    assert restored.plan[0].output["findings"][0]["title"] == "Evidence"
    assert repository.get_events(run.id)[0]["actor"] == "manager"
    assert repository.search_memories(["durable"])[0]["source_run_id"] == run.id
    assert repository.metrics()["success_rate"] == 1
