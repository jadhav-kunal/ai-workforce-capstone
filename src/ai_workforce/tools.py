import ast
import json
import operator
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import RiskLevel, new_id, utc_now


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolContext:
    run_id: str
    objective: str
    instruction: str
    prior_outputs: list[dict[str, Any]]
    inputs: dict[str, Any]


class Tool(ABC):
    name: str
    description: str
    risk: RiskLevel = RiskLevel.LOW

    @abstractmethod
    def execute(self, context: ToolContext) -> dict[str, Any]:
        raise NotImplementedError


class KnowledgeSearchTool(Tool):
    name = "knowledge.search"
    description = "Search supplied context and prior work for relevant evidence"

    def execute(self, context: ToolContext) -> dict[str, Any]:
        sources: Iterable[Any] = context.inputs.get("sources", [])
        normalized = []
        for index, source in enumerate(sources):
            if isinstance(source, str):
                normalized.append({"title": f"Source {index + 1}", "content": source})
            elif isinstance(source, dict):
                normalized.append(
                    {
                        "title": source.get("title", f"Source {index + 1}"),
                        "content": source.get("content", source.get("text", "")),
                        "url": source.get("url"),
                    }
                )
        if not normalized:
            normalized = [
                {
                    "title": "Objective brief",
                    "content": context.objective,
                    "note": "No external sources supplied; conclusion is hypothesis-level.",
                }
            ]
        return {"findings": normalized[:10], "source_count": len(normalized)}


class SynthesisTool(Tool):
    name = "content.synthesize"
    description = "Turn evidence and intermediate outputs into a concise deliverable"

    def execute(self, context: ToolContext) -> dict[str, Any]:
        evidence = []
        for output in context.prior_outputs:
            evidence.extend(output.get("findings", []))
        titles = [item.get("title", "evidence") for item in evidence if isinstance(item, dict)]
        return {
            "deliverable": {
                "title": f"Action brief: {context.objective[:72]}",
                "executive_summary": (
                    "The workforce analyzed the objective, converted available evidence into an "
                    "execution plan, and prepared the requested outbound action."
                ),
                "recommendations": [
                    "Start with a narrow, measurable pilot.",
                    "Keep a human approval checkpoint for external actions.",
                    "Review run metrics and captured lessons before scaling.",
                ],
                "evidence_used": titles or ["Objective brief"],
            }
        }


class AppMessageTool(Tool):
    name = "app.message"
    description = "Queue an email, Slack update, or task-system message in the local outbox"
    risk = RiskLevel.HIGH

    def __init__(self, outbox_dir: str = "data/outbox"):
        self.outbox_dir = Path(outbox_dir)

    def execute(self, context: ToolContext) -> dict[str, Any]:
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "id": new_id("msg"),
            "run_id": context.run_id,
            "channel": context.inputs.get("channel", "email"),
            "recipient": context.inputs.get("recipient", "capstone-reviewer@example.com"),
            "subject": context.inputs.get("subject", "AI Workforce action brief"),
            "body": self._body(context),
            "created_at": utc_now(),
            "delivery": "simulated",
        }
        path = self.outbox_dir / (payload["id"] + ".json")
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"message": payload, "outbox_path": str(path)}

    @staticmethod
    def _body(context: ToolContext) -> str:
        for output in reversed(context.prior_outputs):
            deliverable = output.get("deliverable")
            if deliverable:
                return "{}\n\n{}".format(
                    deliverable.get("executive_summary", ""),
                    "\n".join(f"- {item}" for item in deliverable.get("recommendations", [])),
                )
        return f"Completed objective: {context.objective}"


class SafeCalculatorTool(Tool):
    name = "data.calculate"
    description = "Evaluate a basic arithmetic expression without executing code"

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def execute(self, context: ToolContext) -> dict[str, Any]:
        expression = str(context.inputs.get("expression", "1 + 1"))
        try:
            tree = ast.parse(expression, mode="eval")
            result = self._evaluate(tree.body)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise ToolError(f"Invalid calculation: {exc}") from exc
        return {"expression": expression, "value": result}

    def _evaluate(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._operators:
            left = self._evaluate(node.left)
            right = self._evaluate(node.right)
            if abs(left) > 1e12 or abs(right) > 1e12:
                raise ValueError("operand exceeds safety limit")
            return self._operators[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._operators:
            return self._operators[type(node.op)](self._evaluate(node.operand))
        raise ValueError("only basic arithmetic is allowed")


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {tool.name: tool for tool in tools}

    @classmethod
    def defaults(cls, outbox_dir: str = "data/outbox") -> "ToolRegistry":
        return cls(
            [
                KnowledgeSearchTool(),
                SynthesisTool(),
                AppMessageTool(outbox_dir),
                SafeCalculatorTool(),
            ]
        )

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(f"Unknown tool: {name}") from exc

    def catalog(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description, "risk": tool.risk.value}
            for tool in self._tools.values()
        ]
