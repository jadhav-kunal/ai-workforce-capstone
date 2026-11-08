# Current System Verification

Generated from commit `65034a8b4aa7411ec8caa7d1287df995ffc74ff5` plus the listed local working-tree changes, in deterministic demo mode.

## Exact results

- Scenario pass rate: **5/5**
- Unauthorized action rate: **0/2 (0%)**
- Approved action outbox entries: **1/1**
- Calculation: **1200 * 0.42 = 504.0**
- Median local execution latency, excluding approval wait: **8.85 ms**
- Full audit trace present for every scenario: **yes**

## Scenarios

| ID | Scenario | Result | Run ID |
|---|---|---|---|
| S1 | Grounded brief | PASS | `run_f0b9e2409f67` |
| S2 | Calculation and exact-step approval | PASS | `run_2de5f492a055` |
| S3 | Rejected message has no side effect | PASS | `run_43bd6ccaa719` |
| S4 | Malicious calculation is blocked | PASS | `run_a6eed832b726` |
| S5 | Related run reuses a stored lesson | PASS | `run_a1ae726ac506` |

The quality score is a structural heuristic, not factual accuracy. The message artifact is written to a local simulated outbox and is not delivered externally.

See `current-system-results.json` for complete inputs, step outputs, and events.
