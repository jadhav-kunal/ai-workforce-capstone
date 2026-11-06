# Changelog

## Unreleased

- Added `workforce eval`: a reproducible comparison of B0, B1, P-M, and P on two versioned datasets,
  with raw traces for every run and rescoring without model calls.
- Added the scenario and FinQA pilot datasets and token accounting for OpenAI-compatible providers.
- Added `ExecutionConfig` so baselines can switch off agentic capabilities.
- Revised drafts are now stored in the trace event.

## 2.0.0 — 2026-11-06

- Added provider-generated typed plans with strict schema and tool-argument validation.
- Added one plan-repair attempt followed by a deterministic fallback.
- Added bounded replanning with an eight-step attempt cap and two-replan cap.
- Added stable passage IDs, BM25 evidence ranking, and claim-level grounding checks.
- Added one writer revision before high-risk approval when grounding fails.
- Added BM25 top-three lesson retrieval and source-run provenance.
- Added deterministic run-and-step idempotency for simulated messages.
- Added three-attempt exponential backoff for OpenAI-compatible requests.
- Expanded verification to 19 passing tests with 82% total coverage.

## 1.0.0 — 2026-09-04

- Added durable manager/planner/executor/critic orchestration.
- Added bounded research, calculation, synthesis, and simulated message tools.
- Added human approval and rejection state transitions.
- Added cross-run lesson memory and operational metrics.
- Added REST API, Python SDK, CLI, and responsive operations console.
- Added deterministic offline and OpenAI-compatible providers.
- Added tests, Docker support, capstone documentation, and demonstration script.

