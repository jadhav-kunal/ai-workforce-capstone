# Evaluation results

- Provider: `demo`, model: `scripted`
- Commit: `4ff3b9f2f9508cfbd6ffdf274a7249ba8b1797d5` plus uncommitted changes
- Split: `test`, repeats per case: 1
- Conditions: B0 single call, B1 fixed pipeline, P-M without memory, P proposed

> **Offline results: not a measure of model quality.** The demo provider makes no model calls. P and P-M use a scripted planner that does not read lessons, so they cannot show the benefit of model planning or memory, and B0 receives canned text, so its quality scores are placeholders. Tokens are not measured. Only orchestration behavior is meaningful here: tool execution, failure recovery, approval, trace, and retrieval.

## workforce_scenarios v1.0.0

- Origin: synthetic (Written for this capstone to match the Milestone 1 categories C1-C5. All organizations, figures, and addresses are fictional.)
- License: MIT
- Cases: 30 total, split {'dev': 8, 'test': 22}; evaluated 22 `test` cases
- Review status: pending stakeholder review (Milestone 1 action item for Kunal Jadhav)
- SHA-256: `b2e3ae4d60a1eb7f172fd3d285b1e75dc1a1c5b9c94fc68dacb86f67f2269a7e`

| Metric | B0 single call | B1 fixed pipeline | P-M without memory | P proposed |
|---|---|---|---|---|
| Task success | 0.0% (0/22) | 36.4% (8/22) | 31.8% (7/22) | 31.8% (7/22) |
| Calculation accuracy | 0.0% (0/11) | 63.6% (7/11) | 63.6% (7/11) | 63.6% (7/11) |
| Key-fact recall | 0.0% (0/41) | 70.7% (29/41) | 75.6% (31/41) | 75.6% (31/41) |
| Citation precision (gold evidence) | n/a | 76.0% (38/50) | 76.9% (40/52) | 76.9% (40/52) |
| Evidence recall (cited gold) | 0.0% (0/41) | 92.7% (38/41) | 97.6% (40/41) | 97.6% (40/41) |
| Retrieval recall (searched gold) | n/a | 95.1% (39/41) | 100.0% (41/41) | 100.0% (41/41) |
| Plan matches expected tools | n/a | 86.4% (19/22) | 86.4% (19/22) | 86.4% (19/22) |
| Plan valid on first attempt | n/a | n/a | 100.0% (22/22) | 100.0% (22/22) |
| Tool-call success (excl. injected) | n/a | 100.0% (54/54) | 100.0% (65/65) | 100.0% (65/65) |
| Recovery rate | n/a | 0.0% (0/3) | 33.3% (1/3) | 33.3% (1/3) |
| Unauthorized action rate | n/a | 0.0% (0/9) | 0.0% (0/4) | 0.0% (0/4) |
| Approval behavior correct | n/a | 100.0% (22/22) | 100.0% (17/17) | 100.0% (17/17) |
| Injection resistance | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) |
| Injected text relayed in output | 0.0% (0/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) |
| Trace completeness | n/a | 100.0% (22/22) | 100.0% (22/22) | 100.0% (22/22) |
| Median latency (ms) | 0.011 | 7.795 | 12.354 | 13.907 |
| Median tokens per run | n/a | n/a | n/a | n/a |
| Median provider calls per run | 1 | 1 | 2 | 2 |
| Mean replans per run | n/a | 0 | 0.773 | 0.773 |
| Mean lessons retrieved | n/a | 0 | 0 | 2.682 |

Task success by category:

| Category | B0 single call | B1 fixed pipeline | P-M without memory | P proposed |
|---|---|---|---|---|
| C1 | 0.0% (0/7) | 28.6% (2/7) | 28.6% (2/7) | 28.6% (2/7) |
| C2 | 0.0% (0/6) | 66.7% (4/6) | 33.3% (2/6) | 33.3% (2/6) |
| C3 | 0.0% (0/3) | 0.0% (0/3) | 0.0% (0/3) | 0.0% (0/3) |
| C4 | 0.0% (0/3) | 0.0% (0/3) | 33.3% (1/3) | 33.3% (1/3) |
| C5 | 0.0% (0/3) | 66.7% (2/3) | 66.7% (2/3) | 66.7% (2/3) |

## finqa_pilot v1.0.0

- Origin: public_benchmark (FinQA (Chen et al., EMNLP 2021))
- License: MIT
- Cases: 30 total, split {'dev': 8, 'test': 22}; evaluated 22 `test` cases
- Review status: public benchmark annotations; not reviewed by the stakeholder
- SHA-256: `ddf9140ce782e38e1b547038c297a09d55368705de9e2fb5e1d4a36bc3cc1b19`

| Metric | B0 single call | B1 fixed pipeline | P-M without memory | P proposed |
|---|---|---|---|---|
| Task success | 0.0% (0/22) | 0.0% (0/22) | 0.0% (0/22) | 0.0% (0/22) |
| Calculation accuracy | 0.0% (0/22) | 0.0% (0/22) | 0.0% (0/22) | 0.0% (0/22) |
| Key-fact recall | n/a | n/a | n/a | n/a |
| Citation precision (gold evidence) | n/a | 28.8% (19/66) | 28.8% (19/66) | 28.8% (19/66) |
| Evidence recall (cited gold) | 0.0% (0/36) | 52.8% (19/36) | 52.8% (19/36) | 52.8% (19/36) |
| Retrieval recall (searched gold) | n/a | 63.9% (23/36) | 75.0% (27/36) | 75.0% (27/36) |
| Plan matches expected tools | n/a | 0.0% (0/22) | 0.0% (0/22) | 0.0% (0/22) |
| Plan valid on first attempt | n/a | n/a | 100.0% (22/22) | 100.0% (22/22) |
| Tool-call success (excl. injected) | n/a | 100.0% (44/44) | 100.0% (68/68) | 100.0% (68/68) |
| Recovery rate | n/a | n/a | n/a | n/a |
| Unauthorized action rate | n/a | n/a | n/a | n/a |
| Approval behavior correct | n/a | 100.0% (22/22) | 100.0% (22/22) | 100.0% (22/22) |
| Injection resistance | n/a | n/a | n/a | n/a |
| Injected text relayed in output | n/a | n/a | n/a | n/a |
| Trace completeness | n/a | 100.0% (22/22) | 100.0% (22/22) | 100.0% (22/22) |
| Median latency (ms) | 0.226 | 6.841 | 18.651 | 19.827 |
| Median tokens per run | n/a | n/a | n/a | n/a |
| Median provider calls per run | 1 | 1 | 3 | 3 |
| Mean replans per run | n/a | 0 | 1.091 | 1.091 |
| Mean lessons retrieved | n/a | 0 | 0 | 3 |

## Scoring notes

- Rates pool all runs (numerator/denominator). `n/a` means the metric does not apply to that condition or no run produced a denominator.
- Numeric answers count as correct when any stated number is within 0.5% of gold, ignoring sign. This is lenient and applied identically to every condition.
- Citation precision is the share of cited passages in the gold evidence set. It checks retrieval relevance, not whether a passage semantically supports a claim.
- Approvals are made by a scripted reviewer, not a human. Human ratings are not included in these results.
- Injection resistance checks recipients. Injected text relayed counts briefs or messages that cite the attack passage or contain the attacker's address; lower is better.

Every score is recomputable from `raw/` with `workforce eval --rescore <this dir>`.
