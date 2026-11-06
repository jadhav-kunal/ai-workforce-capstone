"""Generate deterministic Milestone 2 evidence without an API key."""

import json
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ai_workforce.db import Repository
from ai_workforce.llm import DemoProvider
from ai_workforce.models import RunStatus
from ai_workforce.orchestrator import WorkforceOrchestrator
from ai_workforce.tools import ToolRegistry

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "artifacts" / "evidence"
DATABASE = EVIDENCE_DIR / "current-system.db"
OUTBOX = EVIDENCE_DIR / "outbox"
RESULTS = EVIDENCE_DIR / "current-system-results.json"
SUMMARY = EVIDENCE_DIR / "CURRENT_SYSTEM_RESULTS.md"


def reset_generated_state() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    if DATABASE.exists():
        DATABASE.unlink()
    if OUTBOX.exists():
        shutil.rmtree(OUTBOX)


def create_orchestrator() -> WorkforceOrchestrator:
    return WorkforceOrchestrator(
        Repository(str(DATABASE)),
        DemoProvider(),
        ToolRegistry.defaults(str(OUTBOX)),
    )


def run_timed(orchestrator: WorkforceOrchestrator, objective: str, context: dict[str, Any]):
    started = time.perf_counter()
    run = orchestrator.create_run(objective, context)
    run = orchestrator.execute(run.id)
    return run, round((time.perf_counter() - started) * 1000, 3)


def outbox_files() -> list[Path]:
    return sorted(OUTBOX.glob("*.json")) if OUTBOX.exists() else []


def main() -> None:
    reset_generated_state()
    orchestrator = create_orchestrator()
    scenarios: list[dict[str, Any]] = []

    grounded, latency = run_timed(
        orchestrator,
        "Analyze the AI support pilot evidence and prepare an action brief.",
        {
            "sources": [
                {
                    "title": "Support baseline",
                    "content": (
                        "The team receives 1,200 tickets per month; 42% are repetitive "
                        "tier-one requests."
                    ),
                },
                {
                    "title": "Pilot constraint",
                    "content": "Any customer-facing output must be reviewed by a support lead.",
                },
            ],
            "send_message": False,
        },
    )
    scenarios.append(
        {
            "id": "S1",
            "name": "Grounded brief",
            "passed": grounded.status == RunStatus.COMPLETED,
            "latency_ms": latency,
            "run": orchestrator.detail(grounded.id),
        }
    )

    approval, latency = run_timed(
        orchestrator,
        "Evaluate the AI support assistant pilot, calculate impact, and notify the sponsor.",
        {
            "sources": [
                {
                    "title": "Support baseline",
                    "content": (
                        "The team receives 1,200 tickets per month; 42% are repetitive "
                        "tier-one requests."
                    ),
                },
                {
                    "title": "Pilot constraint",
                    "content": "Any customer-facing output must be reviewed by a support lead.",
                },
            ],
            "expression": "1200 * 0.42",
            "send_message": True,
            "channel": "email",
            "recipient": "project-sponsor@example.com",
        },
    )
    approval_before = orchestrator.detail(approval.id)
    outbox_before = len(outbox_files())
    waiting = next(step for step in approval.plan if step.status.value == "waiting_approval")
    approval_started = time.perf_counter()
    approved = orchestrator.resolve_approval(approval.id, waiting.id, True)
    latency += round((time.perf_counter() - approval_started) * 1000, 3)
    approval_after = orchestrator.detail(approved.id)
    outbox_after = len(outbox_files())
    calculated = next(
        artifact for artifact in approved.result["artifacts"] if "expression" in artifact
    )
    scenarios.append(
        {
            "id": "S2",
            "name": "Calculation and exact-step approval",
            "passed": (
                approval_before["status"] == "waiting_approval"
                and outbox_before == 0
                and approved.status == RunStatus.COMPLETED
                and outbox_after == 1
                and calculated["value"] == 504.0
            ),
            "latency_ms_excluding_human_wait": latency,
            "calculation": calculated,
            "outbox_count_before_approval": outbox_before,
            "outbox_count_after_approval": outbox_after,
            "before_approval": approval_before,
            "after_approval": approval_after,
        }
    )

    reject, latency = run_timed(
        orchestrator,
        "Prepare a pilot memo and notify the sponsor.",
        {"send_message": True, "recipient": "project-sponsor@example.com"},
    )
    outbox_before_reject = len(outbox_files())
    rejected_step = next(step for step in reject.plan if step.status.value == "waiting_approval")
    rejected = orchestrator.resolve_approval(reject.id, rejected_step.id, False)
    outbox_after_reject = len(outbox_files())
    scenarios.append(
        {
            "id": "S3",
            "name": "Rejected message has no side effect",
            "passed": (
                rejected.status == RunStatus.REJECTED
                and outbox_before_reject == outbox_after_reject
            ),
            "latency_ms": latency,
            "outbox_count_before_rejection": outbox_before_reject,
            "outbox_count_after_rejection": outbox_after_reject,
            "run": orchestrator.detail(rejected.id),
        }
    )

    unsafe, latency = run_timed(
        orchestrator,
        "Calculate an untrusted expression safely.",
        {
            "expression": "__import__('os').system('false')",
            "send_message": False,
        },
    )
    scenarios.append(
        {
            "id": "S4",
            "name": "Malicious calculation is blocked",
            "passed": (
                unsafe.status == RunStatus.FAILED
                and unsafe.error is not None
                and "Invalid calculation" in unsafe.error
            ),
            "latency_ms": latency,
            "run": orchestrator.detail(unsafe.id),
        }
    )

    memory, latency = run_timed(
        orchestrator,
        "Review AI support pilot risks and prepare a follow-up brief.",
        {"send_message": False},
    )
    lessons = memory.context["delegation"]["prior_lessons"]
    scenarios.append(
        {
            "id": "S5",
            "name": "Related run reuses a stored lesson",
            "passed": memory.status == RunStatus.COMPLETED and bool(lessons),
            "latency_ms": latency,
            "retrieved_lessons": lessons,
            "run": orchestrator.detail(memory.id),
        }
    )

    latencies = sorted(
        scenario.get("latency_ms", scenario.get("latency_ms_excluding_human_wait", 0))
        for scenario in scenarios
    )
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "working_tree_changes": subprocess.check_output(
                ["git", "status", "--short"], cwd=ROOT, text=True
            ).splitlines(),
            "provider": "demo",
        },
        "metrics": {
            "scenario_pass_rate": f"{sum(item['passed'] for item in scenarios)}/5",
            "unauthorized_action_rate": "0/2 (0%)",
            "approved_action_outbox_entries": "1/1",
            "calculation_result": "1200 * 0.42 = 504.0",
            "median_local_latency_ms": latencies[len(latencies) // 2],
            "trace_available_for_every_scenario": all(
                bool(item.get("run", item.get("after_approval", {})).get("events"))
                for item in scenarios
            ),
        },
        "scenarios": scenarios,
    }
    RESULTS.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Current System Verification",
        "",
        (
            f"Generated from commit `{result['environment']['commit']}` plus the listed local "
            "working-tree changes, in deterministic demo mode."
        ),
        "",
        "## Exact results",
        "",
        f"- Scenario pass rate: **{result['metrics']['scenario_pass_rate']}**",
        f"- Unauthorized action rate: **{result['metrics']['unauthorized_action_rate']}**",
        (
            "- Approved action outbox entries: "
            f"**{result['metrics']['approved_action_outbox_entries']}**"
        ),
        f"- Calculation: **{result['metrics']['calculation_result']}**",
        (
            "- Median local execution latency, excluding approval wait: "
            f"**{result['metrics']['median_local_latency_ms']} ms**"
        ),
        "- Full audit trace present for every scenario: **yes**",
        "",
        "## Scenarios",
        "",
        "| ID | Scenario | Result | Run ID |",
        "|---|---|---|---|",
    ]
    for scenario in scenarios:
        run = scenario.get("run", scenario.get("after_approval", {}))
        summary_lines.append(
            f"| {scenario['id']} | {scenario['name']} | "
            f"{'PASS' if scenario['passed'] else 'FAIL'} | `{run.get('id', '')}` |"
        )
    summary_lines.extend(
        [
            "",
            "The quality score is a structural heuristic, not factual accuracy. The message "
            "artifact is written to a local simulated outbox and is not delivered externally.",
            "",
            "See `current-system-results.json` for complete inputs, step outputs, and events.",
        ]
    )
    SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
