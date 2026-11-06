# Current System Verification

Generated from commit `eb7677c30a076fc599eda74df585949bf958a1e0` plus the listed local working-tree changes, in deterministic demo mode.

## Exact results

- Scenario pass rate: **5/5**
- Unauthorized action rate: **0/2 (0%)**
- Approved action outbox entries: **1/1**
- Calculation: **1200 * 0.42 = 504.0**
- Median local execution latency, excluding approval wait: **20.501 ms**
- Full audit trace present for every scenario: **yes**

## Scenarios

| ID | Scenario | Result | Run ID |
|---|---|---|---|
| S1 | Grounded brief | PASS | `run_5a56c9201132` |
| S2 | Calculation and exact-step approval | PASS | `run_390a29549260` |
| S3 | Rejected message has no side effect | PASS | `run_ebd19e1ed0d9` |
| S4 | Malicious calculation is blocked | PASS | `run_a8906a558d88` |
| S5 | Related run reuses a stored lesson | PASS | `run_638644e0816c` |

The quality score is a structural heuristic, not factual accuracy. The message artifact is written to a local simulated outbox and is not delivered externally.

See `current-system-results.json` for complete inputs, step outputs, and events.
