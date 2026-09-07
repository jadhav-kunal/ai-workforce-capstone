# Product Requirements Document

## Product statement

AI Workforce lets a user delegate a business outcome to a governed team of software agents. The system decomposes the outcome, invokes bounded tools, exposes its work, requests approval for consequential actions, and learns a reusable lesson from the result.

## Problem

Most agent demos optimize for an impressive single response. Teams adopting agents instead need repeatability, inspectability, safe access to tools, and a way to improve future runs. The capstone tests whether these controls can coexist in a small system that a reviewer can run locally.

## Users

- **Operator:** delegates work and resolves approvals.
- **Team lead:** examines outcomes, failure rate, and saved lessons.
- **Developer:** adds tools/providers and uses the SDK or API.
- **Auditor/evaluator:** reconstructs who did what and why.

## Jobs to be done

1. When I have a research-and-action task, I want to describe the outcome once and receive an execution plan.
2. When an agent attempts an external action, I want it to stop until I approve or reject the exact step.
3. When a run finishes or fails, I want enough evidence to reconstruct the sequence.
4. When I repeat related work, I want the system to reuse lessons without silently changing its authority.

## Functional requirements

| ID | Requirement | Acceptance criterion | Priority |
|---|---|---|---|
| FR-01 | Accept a natural-language objective through UI, CLI, SDK, and API | A valid objective creates a durable run ID | Must |
| FR-02 | Produce a role- and tool-specific plan | Every step records agent, tool, instruction, risk, and status | Must |
| FR-03 | Execute bounded tools | Evidence, arithmetic, synthesis, and messaging tools return structured output | Must |
| FR-04 | Gate high-risk actions | Default runs pause before `app.message` and emit `approval.requested` | Must |
| FR-05 | Resume or reject safely | Approval completes once; rejection executes no message | Must |
| FR-06 | Store a complete event trace | Run, plan, step, approval, completion/failure events are queryable | Must |
| FR-07 | Learn from a run | Critic writes one scored lesson after successful completion | Must |
| FR-08 | Retrieve relevant lessons | Planner context includes memories matched to objective terms | Should |
| FR-09 | Work without a model key | Demo provider passes all acceptance tests offline | Must |
| FR-10 | Support a live compatible model | Environment configuration selects an OpenAI-compatible endpoint | Should |
| FR-11 | Report operations metrics | UI/API show total, completed, waiting, failed, success rate, and lessons | Should |

## Non-functional requirements

- **Safety:** external writes are denied by default until an explicit decision.
- **Reliability:** state persists across process restarts; repeated execution skips completed steps.
- **Performance:** a demo-mode, no-message run completes locally in under two seconds on a typical laptop.
- **Accessibility:** dashboard uses semantic controls, keyboard-compatible actions, visible focus, and text status labels.
- **Maintainability:** agents, tools, persistence, provider, interface, and UI are separate modules.
- **Portability:** Python 3.9+; Docker image available.
- **Privacy:** no hidden telemetry and no secrets stored in run context by design.

## MVP user journey

1. User enters an objective and optional evidence.
2. Manager retrieves related lessons and asks planner for a workflow.
3. Researcher/analyst/writer execute low-risk steps.
4. Operator step pauses at the policy gate.
5. User approves; simulated connector writes an outbox artifact.
6. Critic scores the run and stores a lesson.
7. Dashboard shows result, trace, and updated metrics.

## Out of scope

- Real email/Slack credentials or delivery.
- Unrestricted shell/browser access.
- Multi-tenant identity and billing.
- Unattended recursive goal creation.
- Online reinforcement learning or automatic code mutation.
- Claims of full production readiness.

## Success criteria

The capstone is successful when a fresh clone can complete the scripted demo, the high-risk action cannot execute before approval, the trace survives a restart, the second related run receives prior lesson context, and all automated tests pass.

