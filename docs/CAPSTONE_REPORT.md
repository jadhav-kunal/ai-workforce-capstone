# AI Workforce: A Governed Multi-Agent Execution Platform

## Abstract

This capstone presents AI Workforce, a local-first platform for delegating a business objective to multiple specialized software agents. The system converts an objective into a typed execution plan, invokes bounded tools, pauses before consequential actions, records an audit trail, and stores a reusable lesson after completion. The artifact includes a Python SDK, CLI, REST API, browser operations console, SQLite persistence, deterministic offline provider, and optional OpenAI-compatible provider. Its principal contribution is an integrated control plane: agent reasoning is separated from authority, tools declare risk, approval is a durable state transition, and “self-improvement” is constrained to sourced episodic memory. A scenario-based evaluation measures task completion, unauthorized actions, trace completeness, evidence coverage, memory reuse, latency, and human-rated usefulness. The result is a production-shaped educational prototype that demonstrates both the promise and necessary limitations of autonomous agent teams.

## 1. Introduction

Large language models can describe how to perform complex work, but useful automation must also maintain state, invoke software tools, survive interruptions, expose intermediate decisions, and respect organizational authority. A single prompt can generate a plan; it cannot by itself guarantee that a sensitive action was approved, that a retry is safe, or that an evaluator can reconstruct what occurred.

AI Workforce investigates a narrow research question: **Can a small multi-agent architecture improve task decomposition and reuse prior lessons while preserving human control over consequential actions?** The project’s hypothesis is that explicit roles and workflow state make autonomy safer and easier to evaluate, provided that the system—not the model—owns tool access and policy enforcement.

The demonstration use case is a research-to-action workflow. A user asks the workforce to evaluate an AI support pilot, quantify an opportunity, write a brief, and notify a sponsor. The manager and planner delegate work to researcher, analyst, writer, and operator roles. Low-risk work proceeds automatically. The outbound action stops at a human approval gate. After approval, the system creates a simulated outbox artifact and a critic records a lesson for related future runs.

## 2. Background and related work

ReAct introduced an influential pattern in which language-model reasoning traces are interleaved with actions and observations, demonstrating that tool interaction can ground decisions and support multi-step tasks [1]. AI Workforce adopts the separation between reasoning and action but moves action authority into an explicit tool registry and state machine.

Reflexion explored verbal reinforcement in which an agent reflects on feedback and stores text that guides later attempts [2]. This capstone implements a deliberately constrained variation: only completed runs create a scored, source-linked lesson; retrieval may inform delegation but cannot modify code, policy, or tool permissions.

AutoGen demonstrated an architecture for applications built from conversations among multiple customizable agents [3]. AI Workforce similarly assigns distinct roles, while emphasizing durable workflow state, step-level risk, and human approval over open-ended agent conversation.

For governance, the NIST AI Risk Management Framework frames AI risk work through govern, map, measure, and manage functions [4]. The capstone reflects those concerns through explicit scope, threat modeling, structural and human evaluation, event logging, and a production-readiness checklist.

## 3. Requirements and design principles

Four principles guide the artifact:

1. **Authority is code, not prose.** A model cannot grant itself a tool or bypass the approval state.
2. **State is durable.** The current plan, outputs, decisions, errors, and lessons reside in SQLite rather than process memory.
3. **Learning is bounded and inspectable.** Improvement means retrieving a scored lesson, not autonomous prompt or code mutation.
4. **Evaluation is reproducible.** Offline demo mode produces a complete workflow without an account, key, cost, or network dependency.

The functional requirements include multi-interface delegation, specialized planning, structured tools, high-risk approval, rejection, a complete trace, lesson storage/retrieval, operational metrics, and provider abstraction. Production concerns such as authentication and real connectors are explicitly out of scope for the semester artifact.

## 4. System design

### 4.1 Layered architecture

The interface layer contains the dashboard, REST API, CLI, and Python facade. All call the same orchestration service. The control layer owns the run state machine and agent roles. The execution layer is a registry of bounded tools. The data layer persists normalized runs and steps plus append-only events and lesson memory. The intelligence layer can be deterministic or model-backed.

This separation makes key policies testable without a live model. A malformed or adversarial model output cannot directly invoke an application connector because provider objects only generate text; the orchestrator chooses registered steps and evaluates risk.

### 4.2 Agent roles

- Manager owns the objective and makes prior lessons visible.
- Planner emits an ordered workflow using the available capability set.
- Researcher collects supplied evidence with provenance.
- Analyst performs arithmetic through a restricted AST evaluator.
- Writer produces a structured action brief.
- Operator invokes the simulated messaging connector only after approval.
- Critic performs post-run checks, assigns a transparent score, and saves a lesson.

Specialization is used for observability and least privilege, not to claim that role count alone creates intelligence.

### 4.3 Execution and approval

A run begins queued, becomes running, and persists each plan step before invocation. On a high-risk step, the orchestrator saves `waiting_approval`, emits an approval event, and returns without calling the tool. Approval is bound to a run and exact step ID. Rejection is terminal. After approval, completed steps are skipped and the authorized step is invoked.

The included connector writes JSON to a local outbox. This simulates an external side effect while preventing accidental real communication during evaluation. It also leaves a concrete artifact that tests and reviewers can inspect.

### 4.4 Memory

Keywords from the objective form a simple retrieval key. The critic stores a lesson, quality score, source run, and timestamp. Related future objectives retrieve highest-scoring matches, and the manager records them in delegation context. Lexical retrieval is intentionally understandable; semantic embeddings are a documented extension.

## 5. Implementation

The backend uses Python and FastAPI. SQLite was selected because it is transactional, inspectable, and requires no service for a single-node capstone. The dashboard is dependency-light HTML, CSS, and JavaScript served by the API. A small SDK provides an embeddable facade. Environment variables select a deterministic provider or an OpenAI-compatible Chat Completions endpoint.

The tool registry currently contains knowledge search, safe arithmetic, content synthesis, and simulated application messaging. Tool outputs are dictionaries so they can be recorded, displayed, and evaluated consistently. Errors become terminal failed runs with events instead of disappearing in server logs.

The codebase includes unit tests for calculation safety and repositories, workflow tests for approval/rejection/memory, API tests for validation and transitions, Docker packaging, configuration examples, and a scripted demonstration.

## 6. Evaluation methodology

Structural evaluation uses eight scenarios: source-based synthesis, calculation and approval, rejection, malicious arithmetic, related-run memory, terminal-run idempotence, missing-source disclosure, and invalid approval. Primary targets are at least 90% task success in deterministic mode, zero unauthorized actions, and complete lifecycle traces.

Semantic evaluation compares a single-completion baseline with the workforce on 20 fixed objectives. Three blinded evaluators rate relevance, evidence traceability, recommendation feasibility, appropriate approval, and trace clarity on a five-point scale. Latency, provider calls, and human interventions are reported alongside median human scores. A second workforce pass with prior lessons estimates whether memory improves the relevant dimensions.

This methodology deliberately distinguishes workflow correctness from answer quality. The built-in score is a structural signal only and is not labeled accuracy.

## 7. Safety and ethical analysis

The most important risk is excessive agency: a system optimized to “finish” might treat review as friction. AI Workforce therefore makes rejection terminal and places policy outside agent text. Additional controls include a tool allowlist, risk declarations, restricted arithmetic evaluation, approval event binding, persisted outputs, and a simulated connector.

Remaining prototype risks include unauthenticated API access, locally mutable audit records, unsanitized sensitive context, lexical memory poisoning, denial of service, and lack of tenant isolation. The repository must not be exposed as an internet service. Real deployment requires identity, least-privilege connector credentials, encrypted secrets, redaction, durable workers, transactional outbox/idempotency, rate and cost limits, tamper-evident logs, monitoring, and an incident stop process.

The project also rejects the simplistic implication that “AI workforce” makes people unnecessary. The intended application is augmentation of repetitive research and drafting while humans retain objective setting, authority, exception handling, and accountability. The artifact is not evaluated or approved for high-impact decisions.

## 8. Results and expected evidence

In deterministic mode, the implemented vertical slice produces a plan, extracts supplied source records, calculates a requested metric, generates a brief, and pauses before messaging. Approval creates one outbox artifact, completes the run, records the critic review, and increments lesson metrics. Rejection creates no artifact. A related second objective receives the earlier lesson in its delegation context. Automated tests encode these claims and should be reported with the exact environment and commit used for the final submission.

The capstone avoids fabricating benchmark numbers in advance. The included evaluation sheet is the place to record final repeated-run latency, pass rate, and human scores during the study.

## 9. Limitations

- The deterministic provider proves orchestration, not open-ended reasoning quality.
- Planning is intentionally constrained to a known research-to-action workflow.
- The local outbox does not test real connector authentication or delivery failures.
- SQLite and in-process background tasks are single-node choices.
- Memory uses lexical matching and has no automated conflict resolution or deletion UI.
- The heuristic reviewer does not measure factual correctness.
- The API has no authentication and must remain local.

These limitations bound the claims and identify concrete future work rather than being hidden behind an “autonomous” label.

## 10. Future work

The next stage would add authenticated identities and per-agent tool scopes, durable queued workers, PostgreSQL concurrency controls, real connectors with transactional idempotency, semantic memory with lifecycle management, policy-as-code, provider/token budgets, OpenTelemetry traces, and representative live-model evaluations. A longer-term study could compare single-agent, manager-worker, and deliberative multi-agent topologies under equal token and time budgets.

## 11. Conclusion

AI Workforce demonstrates that a useful agent system is more than generated text. The capstone integrates delegation, bounded execution, human authority, observability, and conservative learning in a project that runs locally and exposes its assumptions. Its central design choice—keeping authority and durable state outside the model—makes autonomy measurable and governable. The project is small enough to understand end to end while providing a credible foundation for production-oriented research.

## References

1. Yao, S. et al. “ReAct: Synergizing Reasoning and Acting in Language Models.” arXiv:2210.03629, 2022. <https://arxiv.org/abs/2210.03629>
2. Shinn, N. et al. “Reflexion: Language Agents with Verbal Reinforcement Learning.” arXiv:2303.11366, 2023. <https://arxiv.org/abs/2303.11366>
3. Wu, Q. et al. “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation.” arXiv:2308.08155, 2023. <https://arxiv.org/abs/2308.08155>
4. National Institute of Standards and Technology. “Artificial Intelligence Risk Management Framework (AI RMF 1.0).” 2023. <https://www.nist.gov/itl/ai-risk-management-framework>

