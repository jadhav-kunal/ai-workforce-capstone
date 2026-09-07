# Capstone Project Plan

## Objective

Design, implement, and evaluate a production-shaped AI workforce prototype that safely completes a multi-step research-to-action workflow and demonstrates observable learning across runs.

## Research question

Can a small multi-agent architecture improve task decomposition and reuse prior lessons while preserving human control over consequential actions?

## Deliverables

1. Runnable Python package, CLI, REST API, and operations dashboard.
2. Specialized agent workflow and bounded tool registry.
3. SQLite trace, approval state machine, and lesson memory.
4. Offline deterministic provider and optional live model provider.
5. Automated unit/integration tests and evaluation protocol.
6. Capstone report, product requirements, architecture, safety analysis, API guide, and demonstration script.

## Eight-week schedule

| Week | Focus | Exit evidence |
|---:|---|---|
| 1 | Problem framing and literature review | Research question, stakeholder map, PRD |
| 2 | Architecture and threat modeling | Component/state diagrams, misuse cases |
| 3 | Persistence and orchestration | Runs, steps, events, deterministic state transitions |
| 4 | Agents and tools | Research, calculation, synthesis, simulated connector |
| 5 | Governance and learning | Approval/rejection flow, critic, cross-run memory |
| 6 | Interfaces | API, CLI/SDK, responsive dashboard |
| 7 | Evaluation and hardening | Test suite, scenario benchmark, failure analysis |
| 8 | Presentation and handoff | Final report, demo rehearsal, tagged release |

## Work breakdown structure

- Product: personas, scope, acceptance criteria, demo scenario.
- Platform: configuration, data model, repository, state machine.
- Intelligence: provider abstraction, agent roles, planning and critique.
- Execution: tool API, safe calculator, knowledge adapter, outbox connector.
- Governance: policy classification, approvals, event trace, threat model.
- Experience: API schema, CLI, SDK, operations console, accessibility.
- Quality: unit, integration, API, security-negative, and usability tests.
- Communication: architecture, report, poster/slides, demo, runbook.

## Milestones and gates

| Milestone | Gate |
|---|---|
| M1 — Design approved | PRD and architecture trace to acceptance criteria |
| M2 — Vertical slice | Objective reaches a completed no-message run |
| M3 — Governed action | Message cannot execute before approval; rejection is safe |
| M4 — Learning evidence | Related second run retrieves first-run lesson |
| M5 — Candidate release | Clean setup, tests pass, scripted demo completes |

## RACI

For a solo capstone, the student owns Responsible and Accountable roles; faculty/evaluator acts as Consulted and Informed.

| Workstream | Student | Faculty/evaluator | Test users |
|---|---|---|---|
| Scope and requirements | R/A | C | C |
| Architecture and implementation | R/A | I | I |
| Safety policy | R | C/A | C |
| Evaluation | R | A | C |
| Final demonstration | R/A | I | I |

## Risk register

| Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|
| Live model unavailable/costly | Medium | High | Deterministic offline provider | API error or missing key |
| Agent takes unauthorized action | Medium | Critical | Default-deny high-risk policy and approval | Tool has external side effect |
| Hallucinated evidence | Medium | High | Supplied-source provenance and evidence checks | No sources supplied |
| Demo setup fails | Low | High | Editable install, Docker, scripted demo, CI | Clean-environment failure |
| Scope expands beyond semester | High | Medium | Simulated connectors; explicit out-of-scope list | New integration request |
| Memory reinforces poor lesson | Medium | Medium | Store source/score; retrieve only, never mutate policy | Low review score or conflict |
| Sensitive data enters trace | Medium | High | Document no-secret policy; production redaction path | Token/key patterns in context |

## Effort estimate

| Area | Hours |
|---|---:|
| Research and requirements | 18 |
| Architecture and threat model | 18 |
| Backend and persistence | 34 |
| Agents, providers, and tools | 34 |
| UI and developer experience | 24 |
| Tests and evaluation | 28 |
| Report and presentation | 24 |
| Contingency | 20 |
| **Total** | **200** |

## Definition of done

- Fresh install instructions work on Python 3.9+ and Docker.
- Demo succeeds without network access.
- No high-risk tool runs without policy approval.
- Each state transition and tool output is traceable.
- Quality/learning behavior is measurable and documented.
- Unit/integration/API tests pass.
- Limitations and production gaps are disclosed.

