from pathlib import Path

import pytest

from ai_workforce.tools import AppMessageTool, SafeCalculatorTool, ToolContext, ToolError


def context(expression: str) -> ToolContext:
    return ToolContext(
        run_id="run_test",
        step_id="step_test",
        objective="calculate",
        instruction="calculate",
        prior_outputs=[],
        inputs={"expression": expression},
    )


def test_calculator_supports_basic_arithmetic() -> None:
    result = SafeCalculatorTool().execute(context("1200 * 0.42"))
    assert result["value"] == 504


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('touch /tmp/owned')", "open('/etc/passwd').read()", "[1, 2]"],
)
def test_calculator_rejects_code(expression: str, tmp_path: Path) -> None:
    del tmp_path
    with pytest.raises(ToolError, match="Invalid calculation"):
        SafeCalculatorTool().execute(context(expression))


def test_message_tool_suppresses_duplicate_step_delivery(tmp_path: Path) -> None:
    tool = AppMessageTool(str(tmp_path / "outbox"))
    tool_context = context("1 + 1")

    first = tool.execute(tool_context)
    second = tool.execute(tool_context)

    assert first["message"]["id"] == second["message"]["id"]
    assert first["duplicate_suppressed"] is False
    assert second["duplicate_suppressed"] is True
    assert len(list((tmp_path / "outbox").glob("*.json"))) == 1
