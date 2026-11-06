"""Issue #5: keep the dashboard stylesheet organized around tokens and component classes."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "src" / "ai_workforce" / "static"
STYLES = (STATIC / "styles.css").read_text(encoding="utf-8")
SECTIONS = ["Tokens", "Base", "Layout", "Components", "States", "Responsive"]
# Structural hook with no styling of its own.
UNSTYLED_CLASSES = {"run-list"}


def without_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def section_bodies() -> dict[str, str]:
    parts = re.split(r"/\* \d\. (\w+)\n\s+=+ \*/", STYLES)
    return dict(zip(parts[1::2], parts[2::2]))


def test_stylesheet_is_organized_into_ordered_sections() -> None:
    assert list(section_bodies()) == SECTIONS


def test_raw_colors_and_font_families_exist_only_in_tokens() -> None:
    sections = section_bodies()
    outside_tokens = without_comments(
        "".join(body for name, body in sections.items() if name != "Tokens")
    )
    without_data_uri = re.sub(r'url\("[^"]*"\)', "", outside_tokens)

    assert re.findall(r"#[0-9a-fA-F]{3,8}\b", without_data_uri) == []
    assert re.findall(r"\b(?:rgba?|hsla?)\(", without_data_uri) == []
    assert re.findall(r":\s*white\b", without_data_uri) == []
    assert "ui-monospace" not in without_data_uri
    assert "Inter" not in without_data_uri


def test_every_token_is_defined_once_and_every_reference_resolves() -> None:
    css = without_comments(STYLES)
    root = css[css.index(":root") : css.index("}", css.index(":root"))]
    defined = re.findall(r"(--[\w-]+)\s*:", root)
    # Component tokens are set by a variant and always read with a fallback.
    component_tokens = set(re.findall(r"var\((--[\w-]+),", css))
    referenced = set(re.findall(r"var\((--[\w-]+)", css))

    assert len(defined) == len(set(defined))
    assert referenced - set(defined) == component_tokens
    assert set(defined) - referenced == set()


def test_every_class_used_by_the_dashboard_is_styled() -> None:
    markup = (STATIC / "index.html").read_text(encoding="utf-8")
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    used: set[str] = set()
    for value in re.findall(r'class="([^"]*)"', markup + script):
        used.update(token for token in value.split() if re.fullmatch(r"[\w-]+", token))
    styled = set(re.findall(r"\.([A-Za-z_][\w-]*)", without_comments(STYLES)))

    assert used - styled - UNSTYLED_CLASSES == set()


def test_every_run_status_has_a_badge_style() -> None:
    states = section_bodies()["States"]

    for status in ("completed", "waiting_approval", "failed", "rejected", "running"):
        assert f".badge.{status}" in states


def test_buttons_use_component_classes() -> None:
    markup = (STATIC / "index.html").read_text(encoding="utf-8")
    script = (STATIC / "app.js").read_text(encoding="utf-8")

    for button in re.findall(r"<button[^>]*>", markup + script):
        assert 'class="btn ' in button, button
    assert not re.search(r"^button\b", without_comments(STYLES), flags=re.MULTILINE)
