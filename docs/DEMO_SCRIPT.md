# Demonstration Script

Target length: 7–9 minutes.

## 1. Frame the problem — 45 seconds

“Agent demos often stop at generated text. This capstone asks what is needed for an AI team to execute a business workflow without surrendering human control. The answer combines specialized roles, bounded tools, durable state, approvals, and a conservative learning loop.”

## 2. Show architecture — 60 seconds

Open `docs/ARCHITECTURE.md`. Point out the interface layer, stateful orchestrator, role-specific agents, policy gate, tools, audit database, and outbox. Emphasize that models never call tools directly.

## 3. Run automated proof — 45 seconds

```bash
pytest
workforce demo
```

Highlight the calculated 504 repetitive tickets, the approval pause, completed state, quality review, saved lesson, and local outbox path.

## 4. Use the console — 3 minutes

```bash
workforce serve
```

Open <http://127.0.0.1:8000>.

1. Submit the prefilled objective.
2. Open the run and show the specialized plan.
3. At `waiting approval`, note that no message file exists yet.
4. Approve the step.
5. Show completed status, structured outputs, review score, and lesson count.
6. Submit a second related no-message objective and show the run’s `context.delegation.prior_lessons` through the API or `workforce show`.

## 5. Show rejection/safety — 60 seconds

Create another message run and click Reject. Show terminal `rejected` status and explain why the manager does not route around the user’s refusal. Mention the calculator’s AST allowlist and simulated connector.

## 6. Discuss evaluation — 60 seconds

Open `docs/EVALUATION.md`. Separate automated structural correctness from human semantic evaluation. State the target of zero unauthorized actions and describe the baseline-versus-workforce study.

## 7. Close — 30 seconds

“The contribution is not another chatbot. It is a compact control plane for agents: delegation, execution, evidence, approval, and learning are visible and testable. The prototype is honest about its boundary, and the architecture provides a clear route to authenticated production connectors and distributed workers.”

## Backup plan

- If the network is unavailable, use demo mode; it requires no network.
- If a port is occupied, run `workforce serve --port 8010`.
- If the browser cannot be shown, run `workforce demo` and `workforce show RUN_ID`.
- If dependencies cannot be installed locally, use `docker compose up --build`.

## Likely questions

**Why multiple agents?** Roles make ownership, permissions, evaluation, and failure location explicit. The prototype does not claim multiple agents always outperform one model.

**Is it really self-improving?** It learns episodic lessons from completed runs and retrieves relevant ones later. It does not rewrite its code or safety policy.

**Why simulate email?** Real delivery would make a grading demo unsafe and credential-dependent. The outbox preserves the side-effect and approval semantics while remaining inspectable.

**What would you build next?** Authentication, tenant isolation, durable workers, connector idempotency, semantic memory, real provider evaluations, and policy-as-code.

