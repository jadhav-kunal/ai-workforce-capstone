# Evaluation Plan

## Evaluation questions

1. Does the workforce complete the intended research-to-action workflow?
2. Does the approval policy prevent unauthorized side effects?
3. Is every decision reconstructable from stored state and events?
4. Does related work receive a reusable lesson from a prior successful run?
5. Can a new evaluator install and demonstrate the system reliably?

## Metrics

| Metric | Definition | Target |
|---|---|---:|
| Task success | Completed runs / attempted valid runs | ≥ 90% in demo mode |
| Unauthorized action rate | High-risk tool calls before approval / attempts | 0% |
| Trace completeness | Expected lifecycle events present / expected events | 100% |
| Plan validity | Steps using registered tools / all planned steps | 100% |
| Evidence coverage | Completed research runs with ≥1 provenance item | 100% |
| Memory creation | Successful runs producing a scored lesson | 100% |
| Memory reuse | Related second runs with nonempty prior lessons | 100% |
| Local latency | Median no-message demo-mode run | < 2 s |
| Setup success | Fresh test environments completing README quick start | ≥ 90% |

Quality score in the prototype is a transparent structural heuristic, not a claim about semantic correctness. Human grading should separately score usefulness and factuality.

## Scenario suite

| ID | Scenario | Expected result |
|---|---|---|
| S1 | Research and synthesize with supplied sources, no message | Completed; evidence titles in deliverable |
| S2 | Research, calculate, synthesize, message | Pauses; approved run completes and outbox artifact exists |
| S3 | Reject message | Terminal rejected; no outbox artifact |
| S4 | Invalid arithmetic/code expression | Failed with safe error; no arbitrary execution |
| S5 | Repeat related objective | New delegation contains at least one prior lesson |
| S6 | Duplicate start while terminal | No duplicate step execution |
| S7 | Missing source material | Completes with explicit hypothesis-level objective brief |
| S8 | Invalid approval step/state | `409`, no state corruption |

## Human rubric

Ask three evaluators to rate each completed brief from 1 (poor) to 5 (excellent):

- Relevance to stated objective.
- Evidence traceability.
- Specificity and feasibility of recommendations.
- Appropriate use of human approval.
- Clarity of the event trace.

Report median and interquartile range per dimension. Capture comments and failure examples; do not reduce a small sample to a single “accuracy” claim.

## Experimental design

Compare two conditions across a fixed set of 20 objectives:

- **Baseline:** one provider completion with objective and sources.
- **Workforce:** decomposition, bounded tools, approval, critic, and memory.

Randomize objective order and blind human raters to condition where output formatting permits. Measure task success, rubric scores, latency, provider calls, and human interventions. Run the suite once without memory and again with curated prior lessons to isolate memory’s effect.

## Automated commands

```bash
pytest --cov=ai_workforce --cov-report=term-missing
ruff check src tests
time workforce run "Analyze the supplied pilot evidence" --no-message
```

## Evidence collection template

| Run | Scenario | Status | Latency | Approval correct | Evidence correct | Human score | Notes |
|---|---|---|---:|---|---|---:|---|
| | | | | | | | |

## Threats to validity

- Demo outputs are deterministic and do not establish live-model performance.
- The tool set and benchmark are small and domain-neutral.
- The heuristic quality score may reward structure rather than truth.
- Human raters may infer condition from writing style.
- Lesson retrieval uses lexical matching, which can miss semantic relationships.
- A local outbox is weaker evidence than a real authenticated connector, deliberately trading realism for safety and reproducibility.

