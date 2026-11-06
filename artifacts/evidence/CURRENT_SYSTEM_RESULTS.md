# Current System Verification

Generated from commit `2147a90d7a5a85001c53460e4e90551718355b0a` plus the listed local working-tree changes, in deterministic demo mode.

## Exact results

- Scenario pass rate: **5/5**
- Unauthorized action rate: **0/2 (0%)**
- Approved action outbox entries: **1/1**
- Calculation: **1200 * 0.42 = 504.0**
- Median local execution latency, excluding approval wait: **18.169 ms**
- Full audit trace present for every scenario: **yes**

## Scenarios

| ID | Scenario | Result | Run ID |
|---|---|---|---|
| S1 | Grounded brief | PASS | `run_41bf2b5fe420` |
| S2 | Calculation and exact-step approval | PASS | `run_d88113aef0ae` |
| S3 | Rejected message has no side effect | PASS | `run_17504c1e0922` |
| S4 | Malicious calculation is blocked | PASS | `run_a05c9b000f74` |
| S5 | Related run reuses a stored lesson | PASS | `run_2da96924445a` |

The quality score is a structural heuristic, not factual accuracy. The message artifact is written to a local simulated outbox and is not delivered externally.

See `current-system-results.json` for complete inputs, step outputs, and events.
