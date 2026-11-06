# GitHub Issue Drafts

These issues are intentionally small and independently testable.

## 1. Add bounded replanning after a recoverable tool error

**Label:** `enhancement`

When a registered tool returns a recoverable error, let the planner create a revised remainder of
the plan instead of immediately failing the run.

Acceptance criteria:

- Store the failed observation in the audit trace.
- Allow at most two replans and preserve the global step budget.
- Add a deterministic test that injects one timeout and then completes.

## 2. Add claim-level grounding checks to the critic

**Label:** `enhancement`

Have the critic report whether each factual claim and numeric result is supported by a supplied
source passage or calculator output.

Acceptance criteria:

- Return a structured verdict for every checked claim.
- Permit at most one writer revision when grounding fails.
- Add tests for one supported and one unsupported claim.

## 3. Add a reproducible two-dataset evaluation runner

**Label:** `evaluation`

Create a command that evaluates the fixed pipeline and improved system on two versioned datasets
and writes machine-readable results.

Acceptance criteria:

- Record dataset origin, license, split, and case count.
- Report task success, citation precision, recovery, latency, and token use.
- Save run IDs and raw JSON results for every reported score.

## 4. Test approval idempotency through the REST API

**Label:** `testing`

Add an API regression test proving that repeated start or approval requests cannot create duplicate
simulated messages.

Acceptance criteria:

- Exercise the same run and step IDs more than once.
- Assert that only one outbox artifact exists.
- Assert that the event history preserves the original approval decision.
