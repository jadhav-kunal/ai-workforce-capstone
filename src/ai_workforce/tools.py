import ast
import hashlib
import json
import operator
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rank_bm25 import BM25Okapi

from .models import RiskLevel, utc_now


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolContext:
    run_id: str
    step_id: str
    objective: str
    instruction: str
    prior_outputs: list[dict[str, Any]]
    inputs: dict[str, Any]


class Tool(ABC):
    name: str
    description: str
    risk: RiskLevel = RiskLevel.LOW
    argument_model: type[BaseModel]

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.argument_model.model_validate(arguments).model_dump(exclude_none=True)
        except ValidationError as exc:
            raise ToolError(f"Invalid arguments for {self.name}: {exc}") from exc

    @abstractmethod
    def execute(self, context: ToolContext) -> dict[str, Any]:
        raise NotImplementedError


class StrictArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchArguments(StrictArguments):
    query: str = ""
    k: int = Field(default=5, ge=1, le=10)


class SynthesisArguments(StrictArguments):
    pass


class MessageArguments(StrictArguments):
    channel: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None


class CalculatorArguments(StrictArguments):
    expression: str


class KnowledgeSearchTool(Tool):
    name = "knowledge.search"
    description = "Search supplied context and prior work for relevant evidence"
    argument_model = SearchArguments

    def execute(self, context: ToolContext) -> dict[str, Any]:
        sources: Iterable[Any] = context.inputs.get("sources", [])
        normalized: list[dict[str, Any]] = []
        for index, source in enumerate(sources):
            if isinstance(source, str):
                normalized.append(
                    {"id": f"S{index + 1}", "title": f"Source {index + 1}", "content": source}
                )
            elif isinstance(source, dict):
                normalized.append(
                    {
                        "id": f"S{index + 1}",
                        "title": source.get("title", f"Source {index + 1}"),
                        "content": source.get("content", source.get("text", "")),
                        "url": source.get("url"),
                    }
                )
        if not normalized:
            return {
                "findings": [
                    {
                        "id": "S0",
                        "title": "Objective brief",
                        "content": context.objective,
                        "note": "No external sources supplied; conclusion is hypothesis-level.",
                    }
                ],
                "source_count": 0,
                "query": context.inputs.get("query", context.objective),
                "grounding_mode": "hypothesis",
            }
        query = str(context.inputs.get("query") or context.objective)
        query_tokens = self._tokens(query)
        corpus = [self._tokens(f"{item['title']} {item['content']}") for item in normalized]
        ranked = normalized
        if query_tokens and all(corpus):
            scores = BM25Okapi(corpus).get_scores(query_tokens)
            ranked = [
                item
                for item, _ in sorted(
                    zip(normalized, scores), key=lambda pair: float(pair[1]), reverse=True
                )
            ]
        k = int(context.inputs.get("k", 5))
        return {
            "findings": ranked[:k],
            "source_count": len(normalized),
            "query": query,
            "grounding_mode": "supplied_sources",
        }

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return [
            "".join(character for character in word.lower() if character.isalnum())
            for word in value.split()
            if any(character.isalnum() for character in word)
        ]


class SynthesisTool(Tool):
    name = "content.synthesize"
    description = "Turn evidence and intermediate outputs into a concise deliverable"
    argument_model = SynthesisArguments

    def execute(self, context: ToolContext) -> dict[str, Any]:
        evidence: list[dict[str, Any]] = []
        calculations: list[dict[str, Any]] = []
        for output in context.prior_outputs:
            evidence.extend(output.get("findings", []))
            if "expression" in output and "value" in output:
                calculations.append(output)
        titles = [item.get("title", "evidence") for item in evidence]
        claims: list[dict[str, Any]] = []
        for item in evidence[:3]:
            passage_id = item.get("id", "S0")
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            sentence = content.split(".")[0].strip()
            claims.append(
                {
                    "text": f"{sentence}. [{passage_id}]",
                    "citations": [passage_id],
                    "kind": "evidence",
                }
            )
        for calculation in calculations:
            claims.append(
                {
                    "text": (
                        f"The requested calculation {calculation['expression']} equals "
                        f"{calculation['value']}. [CALC]"
                    ),
                    "citations": ["CALC"],
                    "kind": "calculation",
                }
            )
        if not claims:
            claims.append(
                {
                    "text": "No supporting passage was supplied; recommendations are provisional.",
                    "citations": [],
                    "kind": "disclosure",
                }
            )
        critic_notes = context.inputs.get("_critic_notes", [])
        return {
            "deliverable": {
                "title": f"Action brief: {context.objective[:72]}",
                "executive_summary": " ".join(claim["text"] for claim in claims),
                "claims": claims,
                "recommendations": [
                    "Start with a narrow, measurable pilot.",
                    "Keep a human approval checkpoint for external actions.",
                    "Review run metrics and captured lessons before scaling.",
                ],
                "evidence_used": titles or ["Objective brief"],
                "revision_notes_applied": critic_notes,
            }
        }


class AppMessageTool(Tool):
    name = "app.message"
    description = "Queue an email, Slack update, or task-system message in the local outbox"
    risk = RiskLevel.HIGH
    argument_model = MessageArguments

    def __init__(self, outbox_dir: str = "data/outbox"):
        self.outbox_dir = Path(outbox_dir)

    def execute(self, context: ToolContext) -> dict[str, Any]:
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        idempotency_key = f"{context.run_id}:{context.step_id}"
        message_id = "msg_" + hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:16]
        path = self.outbox_dir / f"{message_id}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {
                "message": payload,
                "outbox_path": str(path),
                "idempotency_key": idempotency_key,
                "duplicate_suppressed": True,
            }
        payload = {
            "id": message_id,
            "run_id": context.run_id,
            "step_id": context.step_id,
            "channel": context.inputs.get("channel", "email"),
            "recipient": context.inputs.get("recipient", "capstone-reviewer@example.com"),
            "subject": context.inputs.get("subject", "AI Workforce action brief"),
            "body": self._body(context),
            "created_at": utc_now(),
            "delivery": "simulated",
            "idempotency_key": idempotency_key,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "message": payload,
            "outbox_path": str(path),
            "idempotency_key": idempotency_key,
            "duplicate_suppressed": False,
        }

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
    argument_model = CalculatorArguments

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

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.get(name).validate_arguments(arguments)

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "risk": tool.risk.value,
                "input_schema": tool.argument_model.model_json_schema(),
            }
            for tool in self._tools.values()
        ]
