# Operations Runbook

## Start and stop

```bash
source .venv/bin/activate
workforce serve
```

Stop with `Ctrl+C`. The run database persists at `data/workforce.db`. The default server binds only to localhost.

## Health and diagnosis

```bash
curl -s http://127.0.0.1:8000/health
workforce metrics
workforce list
```

Inspect one run with `workforce show RUN_ID`. A failed run includes its exception type/message and chronological event trace.

## Common issues

| Symptom | Check | Resolution |
|---|---|---|
| `workforce: command not found` | Virtual environment and editable install | Activate `.venv`; run `pip install -e .` |
| Port already in use | Existing server | `workforce serve --port 8010` |
| Missing model key | Provider configuration | Use `AI_WORKFORCE_PROVIDER=demo` or set `OPENAI_API_KEY` |
| Run waits indefinitely | Plan contains high-risk step | Approve/reject it in UI or use CLI `--approve` |
| No outbox file | Action was not approved or message disabled | Inspect plan/events; never bypass by editing DB |
| SQLite locked | Multiple writer processes | Stop duplicate servers; production should use PostgreSQL |

## Backup and reset

For a recoverable backup while the service is stopped, copy `data/workforce.db` to a dated location. To start a logically clean demo, set `AI_WORKFORCE_DB` to a new explicit file path; do not delete the original evaluation evidence.

## Incident response

For suspected unsafe behavior:

1. Stop the process.
2. Preserve the database and outbox as evidence.
3. Revoke any live provider/connector credential configured outside the demo.
4. Inspect the run’s events and exact approved step.
5. Disable the implicated tool or provider before restart.
6. Record root cause, affected artifacts, containment, and a regression test.

## Data handling

Do not submit secrets, regulated data, or confidential customer content. `.env`, database files, and outbox artifacts are gitignored. The prototype has no automatic retention or deletion scheduler.

