# Capstone Submission Checklist

## Artifact

- [x] Source package has a version and console entry point.
- [x] Project runs without external accounts in deterministic mode.
- [x] Dashboard, REST API, CLI, and Python SDK share one backend.
- [x] Database and generated outbox artifacts are excluded from version control.
- [x] Docker and local Python setup paths are documented.
- [x] License and contribution rules are included.

## Requirements evidence

| Claim | Evidence |
|---|---|
| Specialized agent organization | `agents.py`, step actor fields, architecture diagram |
| Research-plan-execute loop | Workflow test and `workforce demo` trace |
| Human-controlled side effects | Approval/rejection tests and policy events |
| Self-improvement | Critic memory plus related-run reuse test |
| Observability | SQLite tables, run detail API, dashboard timeline |
| Five-line embedding | `examples/five_lines.py` |
| Reproducibility | Demo provider, dependency locks by version range, Docker |

## Final verification

Run from a clean virtual environment and paste results into the final report appendix or submission notes:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
ruff check src tests
pytest --cov=ai_workforce
workforce demo
```

- [ ] Record operating system and Python version.
- [ ] Record commit SHA or zip timestamp.
- [ ] Capture test count and coverage.
- [ ] Capture dashboard screenshots before and after approval.
- [ ] Confirm no `.env`, database, or outbox artifact is in the submission.
- [ ] Export architecture/report to the format required by the course.
- [ ] Rehearse the backup demo path.

## Presentation package

Recommended ten-slide sequence:

1. Title and one-sentence contribution.
2. Problem: text generation is not governed execution.
3. Research question and hypothesis.
4. Architecture and trust boundaries.
5. Run state machine and approval semantics.
6. Live demonstration.
7. Bounded self-improvement loop.
8. Evaluation design and results.
9. Safety, limitations, and production gap.
10. Conclusion and next work.

## Final honesty check

- [ ] Do not call the simulated outbox “email delivery.”
- [ ] Do not label the structural quality score “accuracy.”
- [ ] Do not claim production readiness or validated high-impact use.
- [ ] Report failed scenarios and human-evaluation sample size.
- [ ] Distinguish implemented behavior from proposed future work.

