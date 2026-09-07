from pathlib import Path

import pytest

from ai_workforce.tools import SafeCalculatorTool, ToolContext, ToolError


def context(expression: str) -> ToolContext:
    return ToolContext(
        run_id="run_test",
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
