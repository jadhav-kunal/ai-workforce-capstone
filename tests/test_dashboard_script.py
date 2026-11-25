"""Guard against merge leftovers: the dashboard script must parse and declare each name once.

Merge 187d11b kept both sides of a conflict, so `transient` was declared twice and the whole
dashboard stopped rendering while every Python test still passed.
"""

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "src" / "ai_workforce" / "static"
DECLARATION = re.compile(
    r"^(\s*)(?:const|let|var|class|(?:async\s+)?function)\s+([A-Za-z_$][\w$]*)"
)


def duplicate_declarations(script: str) -> list[str]:
    """Names declared twice at top level, or twice in one top-level function's own scope."""
    duplicates: list[str] = []
    top_level: Counter = Counter()
    scope: Counter = Counter()
    for line in script.splitlines():
        match = DECLARATION.match(line)
        if line[:1].strip():  # A column-0 line starts a new top-level statement.
            scope = Counter()
        if not match:
            continue
        indent, name = match.groups()
        counter = top_level if not indent else scope if len(indent) == 2 else None
        if counter is None:
            continue  # Nested blocks have their own scopes.
        counter[name] += 1
        if counter[name] == 2:
            duplicates.append(name)
    return duplicates


def duplicate_ids(markup: str) -> list[str]:
    counts = Counter(re.findall(r'\bid="([^"$]+)"', markup))
    return sorted(name for name, count in counts.items() if count > 1)


def test_dashboard_script_parses_without_duplicate_declarations_or_ids() -> None:
    script_path = STATIC / "app.js"
    script = script_path.read_text(encoding="utf-8")

    assert duplicate_declarations(script) == []
    assert duplicate_ids((STATIC / "index.html").read_text(encoding="utf-8")) == []
    # The broken merge is caught by the scan above even where Node is not installed.
    assert duplicate_declarations("function a() {\n  const t = 1;\n  const t = 2;\n}") == ["t"]
    node = shutil.which("node")
    if node:
        result = subprocess.run(
            [node, "--check", str(script_path)], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
