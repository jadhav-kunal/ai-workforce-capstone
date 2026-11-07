# Contributing

1. Create a focused branch and keep changes scoped to one behavior.
2. Install development dependencies with `pip install -e '.[dev]'`.
3. Add or update tests for every state transition or tool behavior.
4. Run `ruff check src tests` and `pytest` before opening a change.
5. Never commit API keys, `.env`, the runtime database, or outbox artifacts.

Dashboard styles live in `src/ai_workforce/static/styles.css`. Add raw colors and font families only to the Tokens section, and put new rules in the matching section. `tests/test_dashboard_styles.py` enforces this.

New tools must declare a risk level, accept a `ToolContext`, return JSON-serializable data, and have tests for valid input, invalid input, and authorization behavior. External-write tools are high risk unless a documented policy says otherwise.

