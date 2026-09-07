# Requirements Traceability Matrix

| Requirement | Design component | Verification | User evidence |
|---|---|---|---|
| FR-01 objective intake | SDK, CLI, `POST /api/runs`, form | API validation test | New delegation panel |
| FR-02 typed plan | Planner and `PlanStep` | Workflow assertions | Run timeline |
| FR-03 bounded execution | Tool registry | Calculator/workflow tests | Structured artifacts |
| FR-04 approval gate | Orchestrator risk check | No-artifact-before-approval test | Yellow approval panel |
| FR-05 approve/reject | State transition methods | Approval and rejection tests | Approve/Reject controls |
| FR-06 event trace | Repository `events` table | Event assertions | Run detail API |
| FR-07 lesson creation | Critic and `memories` table | Completion test | Lessons metric |
| FR-08 lesson retrieval | Lexical memory search | Related-run test | Delegation context |
| FR-09 offline operation | Demo provider | Entire test suite and CLI demo | No key required |
| FR-10 live provider | Compatible HTTP provider | Provider boundary/unit path | Environment config |
| FR-11 metrics | Repository aggregates | Repository/API tests | Hero metrics |

## Safety-control traceability

| Control | Threat | Enforcement point | Negative test |
|---|---|---|---|
| Registered tool allowlist | Excessive agency | `ToolRegistry.get` | Unknown tool fails |
| Restricted AST | Arbitrary execution | `SafeCalculatorTool._evaluate` | Import/open/list expressions rejected |
| Step-bound approval | Unauthorized action/replay | `resolve_approval` | Wrong state/step returns conflict |
| Terminal rejection | Policy circumvention | `execute` terminal guard | Rejected run stays rejected |
| Completed-step skip | Duplicate side effects | execution loop | Re-execute creates no second file |
| Sourced/scored lessons | Memory opacity | `add_memory` fields | Repository round-trip |

