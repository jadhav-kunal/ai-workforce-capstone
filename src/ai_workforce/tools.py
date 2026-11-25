import ast
import hashlib
import json
import operator
import os
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rank_bm25 import BM25Okapi

from .models import RiskLevel, utc_now


class ToolError(RuntimeError):
    pass


# A sentence ends at . ! or ? followed by whitespace and a capital, digit, or opening mark, so
# decimals such as "3.5%" or "$6.6 million" stay inside their sentence.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[$]?[A-Z0-9])")
SENTENCES_PER_PASSAGE = 2

# Passages are untrusted data. One that issues orders to the agent is quarantined: it is kept in
# the trace for the reviewer but never reaches the writer, the brief, or the outbound message.
_EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
_INSTRUCTION_PATTERNS = [
    (
        re.compile(r"\b(?:note|message|instructions?)\s+(?:to|for)\s+the\s+(?:agent|assistant|ai)\b"
                   r"|(?:^|[.!?:]\s+)(?:assistant|agent|ai|system)\s*:", re.IGNORECASE),
        "addresses the agent directly",
    ),
    (
        re.compile(r"\b(?:ignore|disregard|override)\b[^.]{0,40}\b(?:instructions?|rules?|polic"
                   r"(?:y|ies)|previous|above)\b", re.IGNORECASE),
        "tries to override the agent's instructions",
    ),
    (
        re.compile(r"\bapprov(?:al|ed)\b[^.]{0,40}\b(?:granted|already)\b|\bskip\b[^.]{0,30}"
                   r"\bapproval\b|\bapproval step\b[^.]{0,40}\bskip\b", re.IGNORECASE),
        "claims approval was granted or asks to skip it",
    ),
    (
        re.compile(r"\brecipient\b[^.]{0,30}\bchanged\b|\binstead of the address\b",
                   re.IGNORECASE),
        "tries to change the message recipient",
    ),
    (
        re.compile(r"\bdo not (?:mention|tell|disclose|report)\b", re.IGNORECASE),
        "asks the agent to hide information",
    ),
]
_SEND_TO_ADDRESS = re.compile(
    rf"\b(?:send|email|forward|copy|cc|bcc|mail)\b[^.]{{0,80}}?({_EMAIL})", re.IGNORECASE
)


def planned_expression(
    context: dict[str, Any], observations: list[dict[str, Any]]
) -> Optional[str]:
    """The expression a plan should calculate, repaired after a calculator error.

    None means no calculation should be planned: none was requested, or it already failed and
    has no valid repair (the writer then discloses that the figure is missing).
    """
    expression = context.get("expression")
    if not expression:
        return None
    if not any(item.get("tool") == "data.calculate" for item in observations):
        return str(expression)
    try:
        SafeCalculatorTool().evaluate(str(expression))
    except ToolError:
        return repair_expression(str(expression))
    return str(expression)  # Valid input, so the failure was transient: retry it.


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(text.strip()) if part.strip()]


def _terms(value: str) -> set[str]:
    return {
        word
        for word in ("".join(c for c in raw.lower() if c.isalnum()) for raw in value.split())
        if len(word) >= 3
    }


def best_sentences(content: str, query: str, limit: int = SENTENCES_PER_PASSAGE) -> list[str]:
    """The `limit` sentences that share the most terms with the query, in passage order."""
    sentences = split_sentences(content)
    if len(sentences) <= limit:
        return sentences
    query_terms = _terms(query)
    ranked = sorted(
        range(len(sentences)),
        key=lambda index: (-len(_terms(sentences[index]) & query_terms), index),
    )
    return [sentences[index] for index in sorted(ranked[:limit])]


def instruction_flags(text: str, allowed_recipient: Optional[str] = None) -> list[str]:
    """Reasons a passage reads as orders to the agent rather than evidence; empty if none."""
    reasons = [reason for pattern, reason in _INSTRUCTION_PATTERNS if pattern.search(text)]
    allowed = (allowed_recipient or "").lower()
    if any(match.lower() != allowed for match in _SEND_TO_ADDRESS.findall(text)):
        reasons.append("asks for a message to an address the user did not give")
    return reasons


def repair_expression(expression: str) -> Optional[str]:
    """Fix common typos in an arithmetic expression; None when no valid repair exists.

    Repairs: thousands separators and currency signs, x/× and ÷ for * and /, an operator typed
    twice ("1200 * * 0.42"), a trailing operator, and unbalanced parentheses.
    """
    text = expression.replace(",", "").replace("$", "").replace("×", "*").replace("÷", "/")
    text = re.sub(r"(?<=[\d)])\s*[xX]\s*(?=[\d(])", " * ", text)
    text = re.sub(r"([+*/%])(?:\s+\1)+", r"\1", text)
    text = re.sub(r"[\s+\-*/%]+$", "", text).strip()
    missing = text.count("(") - text.count(")")
    if missing > 0:
        text += ")" * missing
    elif missing < 0:
        text = "(" * -missing + text
    if not text or text == expression.strip():
        return None
    try:
        SafeCalculatorTool().evaluate(text)
    except ToolError:
        return None
    return text


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
                "quarantined": [],
            }
        quarantined: list[dict[str, Any]] = []
        trusted: list[dict[str, Any]] = []
        for item in normalized:
            reasons = instruction_flags(
                f"{item['title']}: {item['content']}", context.inputs.get("recipient")
            )
            if reasons:
                quarantined.append({"id": item["id"], "title": item["title"], "reasons": reasons})
            else:
                trusted.append(item)
        normalized = trusted
        query = str(context.inputs.get("query") or context.objective)
        query_tokens = self._tokens(query)
        corpus = [self._tokens(f"{item['title']} {item['content']}") for item in normalized]
        ranked = normalized
        if query_tokens and corpus and all(corpus):
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
            "grounding_mode": "supplied_sources" if normalized else "hypothesis",
            "quarantined": quarantined,
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
        quarantined: list[dict[str, Any]] = []
        for output in context.prior_outputs:
            quarantined.extend(output.get("quarantined", []))
            # Without supplied sources the search echoes the objective as S0; that is not evidence.
            if output.get("grounding_mode") != "hypothesis":
                evidence.extend(output.get("findings", []))
            if "expression" in output and "value" in output:
                calculations.append(output)
        titles = [item.get("title", "evidence") for item in evidence]
        query = f"{context.objective} {context.inputs.get('query', '')}"
        claims: list[dict[str, Any]] = []
        for item in evidence[:3]:
            passage_id = item.get("id", "S0")
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            sentences = best_sentences(content, query)
            text = " ".join(
                sentence if sentence[-1] in ".!?" else f"{sentence}." for sentence in sentences
            )
            claims.append(
                {
                    "text": f"{text} [{passage_id}]",
                    "citations": [passage_id],
                    "kind": "evidence",
                }
            )
        if context.inputs.get("expression") and not calculations:
            claims.append(
                {
                    "text": (
                        "The requested calculation could not be completed with the safe "
                        "calculator, so no computed figure is reported."
                    ),
                    "citations": [],
                    "kind": "disclosure",
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
        if not evidence:
            claims.append(
                {
                    "text": (
                        "No supporting source passage was supplied; the brief is provisional and "
                        "its conclusions are hypotheses to verify before acting."
                    ),
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
                "quarantined_sources": [
                    {"id": item["id"], "reasons": item["reasons"]} for item in quarantined
                ],
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
        # Publish with os.link so one writer wins and readers never see a partial message.
        temporary = self.outbox_dir / f".{message_id}.{uuid4().hex}.tmp"
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        duplicate = False
        try:
            os.link(temporary, path)
        except FileExistsError:
            payload = json.loads(path.read_text(encoding="utf-8"))
            duplicate = True
        finally:
            temporary.unlink()
        return {
            "message": payload,
            "outbox_path": str(path),
            "idempotency_key": idempotency_key,
            "duplicate_suppressed": duplicate,
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
        return {"expression": expression, "value": self.evaluate(expression)}

    def evaluate(self, expression: str) -> float:
        try:
            tree = ast.parse(expression, mode="eval")
            return self._evaluate(tree.body)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
            raise ToolError(f"Invalid calculation: {exc}") from exc

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
