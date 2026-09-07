# API Guide

The server exposes OpenAPI at `/openapi.json`, interactive Swagger documentation at `/docs`, and ReDoc at `/redoc`.

## Create and start a run

```http
POST /api/runs
Content-Type: application/json

{
  "objective": "Research the pilot and notify the sponsor",
  "context": {
    "sources": [{"title": "Pilot", "content": "91% of test cases passed."}],
    "send_message": true,
    "recipient": "sponsor@example.com"
  },
  "start": true
}
```

Returns `202 Accepted` with a queued run. Execution occurs in a background task; poll the run resource.

## Inspect a run

```http
GET /api/runs/{run_id}
```

The representation contains the objective, status, context, ordered plan, outputs, final review, error, and event trace. Status is one of `queued`, `running`, `waiting_approval`, `completed`, `failed`, or `rejected`.

## Resolve an approval

Find the plan step with `status: "waiting_approval"`, then send:

```http
POST /api/runs/{run_id}/approval
Content-Type: application/json

{"step_id": "step_...", "approved": true}
```

Approval resumes synchronously and returns the resulting run. A rejection returns a terminal `rejected` run and does not invoke the tool. Invalid transitions return `409 Conflict`.

## Other endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness and version |
| `GET` | `/api/tools` | Tool catalog and risk levels |
| `GET` | `/api/runs?limit=25` | Recent runs |
| `POST` | `/api/runs/{id}/start` | Start a created run |
| `GET` | `/api/metrics` | Aggregate operational metrics |

## cURL walkthrough

```bash
curl -s http://127.0.0.1:8000/health

curl -s -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  --data @examples/sample_request.json

curl -s http://127.0.0.1:8000/api/runs
```

The UI is the easiest way to resolve the generated step ID during a live demo.

## Error model

Input validation returns FastAPI’s standard `422` response. Missing runs return `404`. An approval against the wrong run state/step returns `409`. Execution errors are persisted on the run with status `failed` rather than discarded as transient HTTP failures.

## Production additions

The educational API has no authentication. Before remote exposure, add TLS, OIDC/OAuth, per-tenant authorization, request and token budgets, rate limits, audit-log access controls, CORS restrictions, input size limits, and secret redaction.

