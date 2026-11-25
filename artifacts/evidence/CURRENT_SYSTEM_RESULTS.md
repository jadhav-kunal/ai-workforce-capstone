# Current System Verification

Generated from commit `3e29d55a4d78130dada0df1d14b435213c6fc5a7` plus the listed local working-tree changes, in deterministic demo mode.

## Exact results

- Scenario pass rate: **5/5**
- Unauthorized action rate: **0/2 (0%)**
- Approved action outbox entries: **1/1**
- Calculation: **1200 * 0.42 = 504.0**
- Median local execution latency, excluding approval wait: **14.169 ms**
- Full audit trace present for every scenario: **yes**

## Scenarios

| ID | Scenario | Result | Run ID |
|---|---|---|---|
| S1 | Grounded brief | PASS | `run_f11608ef0796` |
| S2 | Calculation and exact-step approval | PASS | `run_6247e0fd07e5` |
| S3 | Rejected message has no side effect | PASS | `run_8608a6b99c20` |
| S4 | Malicious calculation is blocked | PASS | `run_700c4fb8c659` |
| S5 | Related run reuses a stored lesson | PASS | `run_3721de1ffa7c` |

The quality score is a structural heuristic, not factual accuracy. The message artifact is written to a local simulated outbox and is not delivered externally.

See `current-system-results.json` for complete inputs, step outputs, and events.
