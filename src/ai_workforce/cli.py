import argparse
import json
import sys
from typing import Any

from .config import get_settings
from .models import RunStatus
from .sdk import Workforce


def print_run(run: Any) -> None:
    print(json.dumps(run.to_dict(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workforce", description="Operate the AI Workforce capstone"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Start the API and operations dashboard")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--reload", action="store_true")

    run = subparsers.add_parser("run", help="Delegate an objective from the command line")
    run.add_argument("objective")
    run.add_argument("--no-message", action="store_true")
    run.add_argument("--approve", action="store_true", help="Approve the first guarded action")
    run.add_argument("--source", action="append", default=[])
    run.add_argument("--expression")

    show = subparsers.add_parser("show", help="Show a run and its event trace")
    show.add_argument("run_id")

    subparsers.add_parser("list", help="List recent runs")
    subparsers.add_parser("metrics", help="Show aggregate run metrics")
    subparsers.add_parser("demo", help="Run the scripted end-to-end capstone demo")
    return parser


def command_run(workforce: Workforce, args: argparse.Namespace) -> int:
    context: dict[str, Any] = {
        "send_message": not args.no_message,
        "sources": args.source,
    }
    if args.expression:
        context["expression"] = args.expression
    run = workforce.delegate(args.objective, **context)
    if args.approve and run.status == RunStatus.WAITING_APPROVAL:
        waiting = next(step for step in run.plan if step.status.value == "waiting_approval")
        run = workforce.approve(run.id, waiting.id)
    print_run(run)
    return 0 if run.status != RunStatus.FAILED else 1


def command_demo(workforce: Workforce) -> int:
    print("1/4 Delegating objective to the manager agent...")
    run = workforce.delegate(
        "Evaluate an AI support assistant pilot, prepare a launch brief, and notify the sponsor",
        sources=[
            {
                "title": "Support baseline",
                "content": (
                    "The team receives 1,200 tickets/month; 42% are repetitive tier-one requests."
                ),
            },
            {
                "title": "Pilot constraint",
                "content": "Any customer-facing output must be reviewed by a support lead.",
            },
        ],
        expression="1200 * 0.42",
        channel="email",
        recipient="project-sponsor@example.com",
    )
    print("2/4 Agents researched, calculated, and drafted the action brief.")
    if run.status != RunStatus.WAITING_APPROVAL:
        print_run(run)
        return 1
    waiting = next(step for step in run.plan if step.status.value == "waiting_approval")
    print(f"3/4 Approval gate reached: {waiting.title}")
    run = workforce.approve(run.id, waiting.id)
    print("4/4 Approved, executed, reviewed, and saved a reusable lesson.")
    print_run(run)
    return 0 if run.status == RunStatus.COMPLETED else 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        settings = get_settings()
        uvicorn.run(
            "ai_workforce.app:app",
            host=args.host or settings.host,
            port=args.port or settings.port,
            reload=args.reload,
        )
        return
    try:
        workforce = Workforce()
        if args.command == "run":
            code = command_run(workforce, args)
        elif args.command == "show":
            print(json.dumps(workforce.inspect(args.run_id), indent=2))
            code = 0
        elif args.command == "list":
            recent = workforce.orchestrator.repository.list_runs()
            print(json.dumps([run.to_dict() for run in recent], indent=2))
            code = 0
        elif args.command == "metrics":
            print(json.dumps(workforce.orchestrator.repository.metrics(), indent=2))
            code = 0
        else:
            code = command_demo(workforce)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
        return
    sys.exit(code)


if __name__ == "__main__":
    main()
