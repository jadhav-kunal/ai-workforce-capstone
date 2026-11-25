"""Populate the supplied Milestone 2 DOCX template with verified main results."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path("/Users/manastole/Downloads/CSE598_AI_Workforce_Milestone_2_Draft.docx")
OUTPUT_DIR = ROOT / "artifacts" / "milestone2"
OUTPUT = OUTPUT_DIR / "CSE598_AI_Workforce_Milestone_2_Report.docx"
WAITING_IMAGE = ROOT / "artifacts/evidence/issue5/desktop-after-waiting_approval.png"
COMPLETED_IMAGE = ROOT / "artifacts/evidence/issue5/desktop-after-completed.png"
DOCS_SCRIPTS = Path(
    "/Users/manastole/.codex/plugins/cache/openai-primary-runtime/documents/"
    "26.826.12353/skills/documents/scripts"
)
sys.path.insert(0, str(DOCS_SCRIPTS))
from table_geometry import apply_table_geometry  # noqa: E402


def replace_paragraph(paragraph, text: str) -> None:
    """Replace visible text while retaining the source paragraph/run formatting."""
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def replace_cell(cell, text: str) -> None:
    first = cell.paragraphs[0]
    replace_paragraph(first, text)
    for paragraph in cell.paragraphs[1:]:
        replace_paragraph(paragraph, "")


def set_image_alt(paragraph, descriptions: list[str]) -> None:
    elements = paragraph._p.xpath(".//wp:docPr")
    for element, description in zip(elements, descriptions, strict=True):
        element.set("descr", description)


def update_table(table, rows: list[list[str]]) -> None:
    assert len(table.rows) == len(rows)
    assert all(len(row.cells) == len(values) for row, values in zip(table.rows, rows, strict=True))
    for row, values in zip(table.rows, rows, strict=True):
        for cell, value in zip(row.cells, values, strict=True):
            replace_cell(cell, value)
        row_properties = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        row_properties.append(cant_split)
    header_properties = table.rows[0]._tr.get_or_add_trPr()
    marker = OxmlElement("w:tblHeader")
    marker.set(qn("w:val"), "true")
    header_properties.append(marker)
    # Preserve the template's equal-column grids while making the geometry
    # explicit and keeping the visible border within the 0.9-inch margins.
    table_width = 9528
    column_count = len(table.columns)
    widths = [table_width // column_count] * column_count
    widths[-1] += table_width - sum(widths)
    apply_table_geometry(table, widths, indent_dxa=120)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE, OUTPUT)
    document = Document(OUTPUT)
    paragraphs = document.paragraphs

    replacements = {
        1: "Milestone 2 Report | AI Workforce: From a Fixed Pipeline to a Governed, Self-Correcting Agent Team",
        2: "Verification status: latest main commit f29cb95 rerun November 7, 2026; post-implementation stakeholder review still requires team-supplied meeting notes before submission.",
        4: (
            "AI Workforce now implements the governed agentic design proposed in Milestone 1: provider-generated typed plans, schema validation with one repair and deterministic fallback, bounded replanning, BM25 evidence and lesson retrieval, claim-level grounding checks, exact-step approval, and idempotent simulated messaging. On latest main commit f29cb95, Ruff passed, all 65 automated tests passed, and statement coverage reached 91%. A fresh deterministic evidence run passed 5/5 scenarios, produced 0/2 unauthorized actions, created exactly 1/1 approved outbox entry, preserved complete traces, and calculated 1,200 x 42% = 504. The full offline comparison executed 176 scored test runs across two versioned datasets and four conditions. These results demonstrate reproducible orchestration and governance, but not live-model quality: task success, recovery, citation precision, prompt-injection handling, human ratings, tokens, and cost still require improvement or additional evidence."
        ),
        7: (
            "The documented stakeholder discovery meeting occurred September 28, 2026 with Kunal Ramesh Jadhav and team members Manas Tole, Asmi Phulgam, Shreya Kale, and Pratik Chaudhari. The group reviewed the fixed-pipeline baseline, the manager-worker design, safety boundaries, and evaluation plan. The recorded direction was to retain simulated delivery and prioritize dynamic planning, recovery, useful memory, fair comparisons, and offline reproducibility. The repository and supplied files do not contain dated notes from the required post-implementation Milestone 2 review. Before submission, the group must add the meeting date, attendees, demonstrated build, Kunal's exact feedback, the team's response, and confirmation of final deliverables; this report does not invent those facts."
        ),
        9: (
            "The implemented scope remains one research-to-action workflow: accept an objective and supplied sources; retrieve evidence; optionally calculate a metric; create and validate a typed plan; synthesize and verify a cited brief; persist events and lessons; and require human approval for the exact simulated message step. The team added dynamic planning, validation/repair/fallback, bounded replanning, grounding checks, advisory memory, evaluation tooling, and idempotency. Real email/Slack delivery, unrestricted web or shell access, production identity and tenancy, fine-tuning, and high-impact automated decisions remain outside scope. Final stakeholder sign-off on these deliverables is still required."
        ),
        10: (
            "Milestone 1 targets were zero unauthorized actions, 100% reconstructable traces, at least 85% task success, at least 90% citation precision, at least 75% injected-failure recovery, and bounded cost. Current deterministic scenario checks meet the first two targets, but the 22-case stakeholder test split does not meet the quality/recovery targets: P achieved 31.8% task success, 76.9% gold-evidence citation precision, and 33.3% recovery. Provider tokens and cost were not emitted in demo mode."
        ),
        13: (
            "At commit f29cb95 the extension is implemented rather than merely proposed. The Python/FastAPI application uses Pydantic schemas, SQLite state, a provider-backed planner, one invalid-plan repair, deterministic fallback, four registered tools, up to two observation-driven replans, a grounding critic with one writer revision, BM25 evidence and lesson ranking, an approval gate, an idempotent simulated outbox, CLI/API/dashboard/SDK interfaces, and a reproducible evaluation runner. The demo provider permits offline testing without an API key; an OpenAI-compatible provider remains optional."
        ),
        15: (
            "Implemented flow: the manager persists the objective and retrieves up to three advisory lessons; the planner proposes typed registered-tool steps; the validator checks tools, arguments, order, budgets, and recipient pinning; workers execute search, calculation, and synthesis; the critic verifies cited passage IDs and numeric support; failures or weak grounding can replan the unfinished work within caps; and a high-risk message pauses for approval before one idempotent local outbox write. Every transition is stored in SQLite."
        ),
        16: "INPUT -> MANAGER + SQLITE STATE -> LESSON RETRIEVAL (top three, advisory)",
        17: "MANAGER -> PROVIDER PLAN -> PYDANTIC / TOOL / BUDGET VALIDATION",
        18: "VALID PLAN -> SEARCH -> CALCULATE -> SYNTHESIZE -> GROUNDING CRITIC",
        19: "INVALID PLAN -> ONE REPAIR -> DETERMINISTIC FALLBACK",
        20: "TOOL OR GROUNDING FAILURE -> OBSERVATION -> BOUNDED REPLAN (max two)",
        21: "VERIFIED BRIEF -> EXACT-STEP APPROVAL -> IDEMPOTENT SIMULATED OUTBOX",
        22: "ALL STEPS -> SQLITE RUNS, ARGUMENTS, OUTPUTS, EVENTS, APPROVALS, LESSONS",
        23: "Figure 1. Implemented architecture and code-owned governance boundaries at main commit f29cb95.",
        25: (
            "The provider receives the objective, public context, registered tool schemas, prior observations, completed tools, retrieved lessons, and remaining budget, but it never receives direct authority to execute. Code validates a one-to-eight-step plan, copies risk from the registry, requires synthesis before messaging, and pins the user-supplied recipient. knowledge.search assigns stable passage IDs, data.calculate evaluates a restricted arithmetic AST, content.synthesize carries passage/CALC citations into structured claims, and app.message writes only after exact-step approval. Tool exceptions become durable observations; completed steps survive replanning, and duplicate start/approval calls are suppressed by run-and-step idempotency."
        ),
        26: (
            "The verified environment uses Python 3.9+ (rerun here on Python 3.14.4), FastAPI, SQLite, Pydantic, and rank-bm25. Runtime caps are eight attempted steps, two replans, one plan repair, one grounding revision, and three OpenAI-compatible provider attempts with exponential backoff. Demo mode is deterministic and offline. Live-provider model quality, token use, cost, and retry behavior under real network faults were not measured in this run."
        ),
        29: (
            "Dataset A is datasets/workforce_scenarios_v1.json, a team-authored MIT-licensed suite of 30 synthetic cases aligned to categories C1-C5: research briefs (10), calculation/approval (8), off-template requests (4), injected failures (4), and adversarial sources (4). The fixed split contains 8 development and 22 test cases; all 22 test cases were evaluated. Gold fields cover expected tools, evidence, numeric answers, approval behavior, and safety. Stakeholder review remains explicitly pending in the dataset metadata."
        ),
        30: (
            "Dataset B is datasets/finqa_pilot_v1.json, a reproducible 30-case MIT-licensed subset of the public FinQA benchmark (Chen et al., EMNLP 2021), also split 8 development/22 test. scripts/build_finqa_subset.py verifies pinned source hashes, preserves official splits, orders eligible cases deterministically by ID hash, and selects one case per filing. All 22 test cases were evaluated, providing an independently sourced retrieval, citation, and arithmetic challenge."
        ),
        32: (
            "The offline runner compared B0 (single canned completion), B1 (fixed pipeline), P-M (enhanced planning without memory), and P (enhanced planning with seeded lessons) on identical test cases. Each condition used its own database; P was seeded from development runs. The run produced 176 scored test executions plus 16 lesson-seed runs. Because the provider was scripted, B0 text was canned and P/P-M planning did not read lessons; therefore the comparison measures orchestration, retrieval, approval, and trace behavior, not live-model quality or memory benefit."
        ),
        34: (
            "Task success requires the expected workflow outcome, required facts, and an in-tolerance numeric answer when applicable. Citation precision checks whether cited passage IDs are in the gold evidence set; it is not semantic entailment. Recovery is recovered injected-failure cases divided by injected attempts. Unauthorized-action rate counts high-risk calls before approval. Trace completeness checks persisted lifecycle records. Rates below pool one run per test case; no confidence interval is claimed. Tokens/cost and blinded human ratings were not collected, and scripted approvals are not human review."
        ),
        35: "Table 3. Exact offline results on main f29cb95 (22 held-out cases per dataset and condition; one repeat). Every entry is the stored numerator/denominator from results.json; percentages are discussed in the text. P-M matched P on all reported rate metrics and is reported separately below. n/a means no denominator existed.",
        36: (
            "Independent software verification also passed: Ruff reported no violations; pytest completed 65/65 tests; and statement coverage was 91% (1,543 statements, 143 missed). A separate five-scenario evidence run passed 5/5 with 0/2 unauthorized actions, 1/1 approved outbox entry, complete traces, the expected 504.0 calculation, and 8.421 ms median local execution latency excluding approval wait."
        ),
        37: (
            "Dataset A shows the exact trade-off: B1 completed 8/22 cases (36.4%) and P completed 7/22 (31.8%), while P improved key-fact recall from 29/41 to 31/41, evidence recall from 38/41 to 40/41, retrieval recall from 39/41 to 41/41, and recovery from 0/3 to 1/3. P also recorded 22/22 first-attempt valid plans, 65/65 non-injected tool calls, 17/17 correct approval outcomes, 22/22 complete traces, and 0/4 unauthorized actions. On Dataset B, P retrieved 27/36 gold passages and completed 68/68 tool calls, 22/22 approvals, and 22/22 traces, but task and calculation success remained 0/22 and citation precision remained 19/66 (28.8%). Median latency in B0/B1/P-M/P order was 0.010/4.918/9.747/10.315 ms on A and 0.174/6.115/16.950/18.798 ms on B. P-M equaled P on all rate metrics; its zero lessons versus P's means of 2.682 on A and 3.000 on B did not change scripted-provider quality."
        ),
        39: "4.1 Current verified run",
        40: (
            "The fresh S2 demonstration used run run_a9f7397472c9 with objective 'Evaluate the AI support assistant pilot, calculate impact, and notify the sponsor.' Two supplied passages stated that the team receives 1,200 monthly tickets, 42% are repetitive tier-one requests, and customer-facing output requires support-lead review. The model-sourced plan searched two passages (S1/S2), evaluated 1200 * 0.42 = 504.0, synthesized three supported claims with S1/S2/CALC citations, and queued a high-risk email to the pinned project-sponsor@example.com recipient. The run paused in waiting_approval with zero outbox entries; exact-step approval then completed the same run and created exactly one local simulated artifact."
        ),
        42: "4.2 Observation-to-action trace",
        43: (
            "Search observations established the two stable passage IDs used by the writer and critic. The calculator observation supplied 504.0 and a CALC citation. The critic marked all three claims supported and the calculation consistent, so no revision or replan was needed. The message step could not execute from planner text, source text, or prior memory; the runtime required approval bound to step_5274975d3715. Approval produced one outbox record and a complete event history. Companion checks covered rejection with no side effect, blocked malicious arithmetic, related-run lesson reuse, and exactly-once execution."
        ),
        45: (
            "The current failures are measurable rather than hypothetical. P completed 7/22 Dataset A cases (31.8%) and 0/22 FinQA cases; calculation accuracy was 7/11 on Dataset A and 0/22 on FinQA. Expected-tool matching was 19/22 for Dataset A and 0/22 for FinQA, showing that the scripted plan and evaluator are not adapted to the benchmark's arithmetic workflow. Citation precision was 76.9% on Dataset A and 28.8% on FinQA, below the planned 90% target."
        ),
        46: (
            "Injected-failure recovery improved from 0/3 for B1 to 1/3 for P, but two cases still failed after bounded recovery. More importantly, the recipient-focused injection-resistance check passed 3/3 while B1 and P relayed injected text in 3/3 adversarial outputs. Thus destination pinning worked, but content isolation did not. The next fix should exclude adversarial passages from synthesis after detection, add semantic support checks, and rerun the same case IDs. Regression evidence must preserve the current 0% unauthorized-action rate, exact-step approval, and duplicate suppression."
        ),
        47: (
            "Other validity limits are the deterministic demo provider, one repeat per case, scripted approvals, synthetic stakeholder data, lexical BM25 retrieval, no live-provider usage records, no blinded human ratings, and simulated-only delivery. P and P-M had identical task/citation results because the scripted planner ignores lessons, so the current run cannot establish a memory benefit. Production authentication, tenant isolation, durable workers, and connector delivery remain outside the prototype."
        ),
        49: (
            "Priorities below are based on the fresh test evidence. Repository-visible owners are listed only where commit authorship supports them; stakeholder liaison, human scoring, presentation work, and other non-code ownership must be confirmed by the team. The post-implementation stakeholder review is a blocking submission requirement."
        ),
        51: (
            "Submission repository: https://github.com/jadhav-kunal/ai-workforce-capstone.git. Branch tested: main. Full code-under-test SHA: f29cb959c1c2079039e021f656fa83db707c7235. The local main branch was fast-forwarded from 2147a90 to f29cb95 before verification. Public grader access should still be checked in a logged-out browser before submission. Generated evidence/report files are local working-tree outputs and do not change the tested source commit."
        ),
        53: "Reproducible commands executed from the repository root:",
        54: "git clone https://github.com/jadhav-kunal/ai-workforce-capstone.git",
        55: "cd ai-workforce-capstone && git checkout main && git pull --ff-only origin main",
        56: "uv sync --extra dev",
        57: "uv run ruff check src tests",
        58: "uv run pytest --cov=ai_workforce --cov-report=term-missing",
        59: "uv run python scripts/collect_evidence.py",
        60: "uv run workforce eval --output artifacts/evaluation/milestone2-current",
        61: "uv run workforce eval --rescore artifacts/evaluation/milestone2-current",
        62: (
            "Offline mode requires no API key. The evaluation output includes a manifest, raw JSONL traces, results.json, scores.csv, and summary.md. Live evaluation is billable and requires explicit provider credentials; no private keys belong in the repository. Current command results: Ruff pass, 65 tests pass, 91% coverage, 5/5 scenario checks, and 176 rescored test runs."
        ),
        64: (
            "The table reports only Git-visible evidence. Dataset annotation, stakeholder work, manual scoring, screenshots, manuscript preparation, and presentation work must be confirmed by the team with links or artifacts; commit counts alone do not prove full ownership."
        ),
        66: (
            "Milestone 2 establishes a working, testable governed agent workflow on latest main: typed dynamic plans are validated, failures are observed within bounded recovery, evidence and calculations are carried into structured claims, approval controls the exact consequential step, duplicate side effects are suppressed, and complete traces are reproducible offline. The measured evidence is deliberately narrower than a claim of superior intelligence. Safety and observability are strong, while task success, FinQA arithmetic, recovery, semantic grounding, injected-content isolation, live-model cost/quality, human evaluation, and stakeholder sign-off remain the work required for the final project."
        ),
        68: "[1] Group 3, 'AI Workforce: From a Fixed Pipeline to a Governed, Self-Correcting Agent Team,' CSE 598 Milestone 1, September 2026.",
        69: "[2] K. R. Jadhav et al., AI Workforce repository, main commit f29cb959c1c2079039e021f656fa83db707c7235, accessed November 7, 2026, https://github.com/jadhav-kunal/ai-workforce-capstone.",
        70: "[3] Group 3, 'Evaluation results,' artifacts/evaluation/milestone2-current, regenerated November 7, 2026 from 176 offline test runs.",
        71: "[4] Z. Chen et al., 'FinQA: A Dataset of Numerical Reasoning over Financial Data,' EMNLP 2021; MIT-licensed project subset in datasets/finqa_pilot_v1.json.",
        72: "[5] S. Yao et al., 'ReAct: Synergizing Reasoning and Acting in Language Models,' arXiv:2210.03629, 2022; N. Shinn et al., 'Reflexion,' arXiv:2303.11366, 2023.",
    }

    for index, text in replacements.items():
        replace_paragraph(paragraphs[index], text)

    update_table(
        document.tables[0],
        [
            ["Team members", "Stakeholder / reference"],
            ["Manas Tole; Asmi Phulgam; Shreya Kale; Pratik Chaudhari", "Kunal Ramesh Jadhav - proposal author and stakeholder"],
            ["Project repository / tested branch", "github.com/jadhav-kunal/ai-workforce-capstone | main @ f29cb95"],
            ["Report basis", "Milestone 1; latest main; fresh tests, evidence suite, and 176-run offline evaluation on November 7, 2026"],
        ],
    )

    update_table(
        document.tables[1],
        [
            ["Feedback", "Team response / current evidence", "Next action / evidence"],
            ["Fixed planning limits unfamiliar objectives", "Implemented provider plans, Pydantic validation, one repair, and deterministic fallback; plan-first validity was 22/22 for P.", "Run live-provider off-template cases and inspect plan quality."],
            ["Tool errors terminate the baseline", "Implemented durable observations and up to two replans; P recovered 1/3 injected failures versus B1's 0/3.", "Fix the two failed case IDs and rerun the frozen split."],
            ["Stored lessons need to affect future work", "Implemented top-three BM25 lesson retrieval with source-run provenance; P averaged 2.682 lessons on Dataset A.", "Use a planner that reads lessons and rerun the P-M/P ablation."],
            ["Briefs must be grounded and useful", "Implemented passage IDs, numeric checks, critic verdicts, and one revision; P citation precision was 76.9% on Dataset A.", "Add semantic support checks and three-rater human scoring."],
            ["High-risk actions must remain governed", "Exact-step approval and idempotent outbox retained; 0/2 unauthorized scenario actions and P 0/4 in Dataset A.", "Re-test after content-injection fixes; keep simulated delivery."],
            ["Fairness, cost and reproducibility matter", "Published two versioned datasets, raw traces, scoring code, and offline results; tokens/cost and human ratings remain unavailable.", "Run equal-budget live conditions and document stakeholder review."],
        ],
    )

    update_table(
        document.tables[2],
        [
            ["Component", "Baseline supported", "Milestone 2 implementation / evidence"],
            ["Intake + REST/CLI/dashboard/SDK", "Implemented", "Retained; current UI evidence and lifecycle tests present."],
            ["State machine + SQLite events", "Implemented", "Expanded persistence, complete traces, safe resume, concurrent idempotency."],
            ["Planner", "Fixed deterministic plan", "Provider-generated typed plans, schema/tool/order/budget checks, one repair, fallback."],
            ["Research/analysis/writing", "Registered tools", "BM25 passage IDs, restricted arithmetic, sourced structured claims."],
            ["Critic + lessons", "Formula score and saved lessons", "Claim/numeric critic, one revision, top-three source-linked BM25 memories."],
            ["Approval + outbox", "Exact-step gate", "Retained; recipient pinning, 0 unauthorized actions, exactly-once simulated write."],
        ],
    )

    update_table(
        document.tables[3],
        [
            ["Dataset", "Source / size", "Pilot evaluated", "What it tests"],
            ["A: workforce_scenarios v1.0.0", "Team-authored synthetic; MIT; 30 cases (8 dev/22 test)", "22 test cases x 4 conditions", "Workflow, calculation, approval, recovery, adversarial sources"],
            ["B: finqa_pilot v1.0.0", "FinQA public benchmark subset; MIT; 30 cases (8 dev/22 test)", "22 test cases x 4 conditions", "Independent retrieval, citation, and financial arithmetic"],
        ],
    )

    update_table(
        document.tables[4],
        [
            ["Dataset / metric", "B0: single call", "B1: fixed pipeline", "P: enhanced agent"],
            ["A - success / calculation", "0/22; 0/11", "8/22; 7/11", "7/22; 7/11"],
            ["A - fact recall / citation precision", "0/41; n/a", "29/41; 38/50", "31/41; 40/52"],
            ["A - evidence / retrieval recall", "0/41; n/a", "38/41; 39/41", "40/41; 41/41"],
            ["A - plan match / tool-call success", "n/a; n/a", "19/22; 54/54", "19/22; 65/65"],
            ["A - recovery / unauthorized", "n/a; n/a", "0/3; 0/9", "1/3; 0/4"],
            ["A - approval / complete trace", "n/a; n/a", "22/22; 22/22", "17/17; 22/22"],
            ["B - success / calculation / citation", "0/22; 0/22; n/a", "0/22; 0/22; 19/66", "0/22; 0/22; 19/66"],
            ["B - evidence / retrieval / tool success", "0/36; n/a; n/a", "19/36; 23/36; 44/44", "19/36; 27/36; 68/68"],
        ],
    )

    update_table(
        document.tables[5],
        [
            ["Priority / required work", "Current gap", "Owners", "Completion evidence"],
            ["P0 - Stakeholder follow-up", "No post-implementation meeting notes in supplied evidence", "Team to confirm liaison", "Dated notes, exact feedback, responses, final-deliverable sign-off"],
            ["P0 - Task success / FinQA", "P: 7/22 on A and 0/22 on B", "Shreya (evaluation code); team review", "Corrected fixed-case rerun and error analysis"],
            ["P0 - Injection content isolation", "Injected text relayed in 3/3 B1/P adversarial cases", "Team to assign", "Attack passages excluded; safety regression passes"],
            ["P0 - Recovery", "P recovered only 1/3 injected failures", "Asmi (replanning); team review", "At least 3/4 planned recovery target with traces"],
            ["P1 - Grounding quality", "A citation precision 76.9%; B 28.8%", "Team to assign", "Semantic support checks and audited citations"],
            ["P1 - Live comparison / cost", "Demo provider; tokens and cost unavailable", "Team to assign", "Equal-budget live B0/B1/P logs with usage"],
            ["P1 - Human scoring", "No blinded ratings or inter-rater results", "Team to assign", "Three-rater rubric, raw scores, medians/IQR"],
            ["P1 - Final presentation", "Rehearsal and submission sign-off not evidenced", "All four; coordinator to confirm", "Final deck, demo script, access check, rehearsal"],
            ["P2 - Production controls", "No identity, tenancy, durable workers, or real connector", "Only if stakeholder approves", "Documented post-capstone extension; core scope unchanged"],
        ],
    )

    update_table(
        document.tables[6],
        [
            ["Team member", "GitHub user / commit evidence", "Verified repository-visible contributions"],
            ["Manas Tole", "manastole03; 65034a8; merge commits including f29cb95", "Core architecture refactor, planner/critic/memory/tool changes, documentation, evidence integration, PR merges."],
            ["Asmi Phulgam", "asmipulgam; b397b46", "Bounded replanning after recoverable tool errors and workflow tests."],
            ["Shreya Kale", "kaleshreya162001 / ShreyaK1601; 698b8de, 3f11e15, e469a52", "Evaluation runner/datasets, usage reporting, concurrency/idempotency tests, dashboard UI refactor and visual evidence."],
            ["Pratik Chaudhari", "No commit attributed in current Git history", "Non-code or branch-local contributions require team-provided artifact links before submission."],
        ],
    )

    image_paragraph = paragraphs[41]
    image_paragraph.clear()
    image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_paragraph.add_run().add_picture(str(WAITING_IMAGE), width=Inches(3.0))
    image_paragraph.add_run("  ").add_picture(str(COMPLETED_IMAGE), width=Inches(3.0))
    caption = image_paragraph.add_run(
        "\nFigures 2-3. Current dashboard at exact-step approval (left) and after one approved simulated outbox write (right)."
    )
    caption.italic = True
    set_image_alt(
        image_paragraph,
        [
            "AI Workforce dashboard showing a run paused at the exact high-risk message step awaiting human approval.",
            "AI Workforce dashboard showing the same workflow completed after approval with evidence, calculation, and policy outcome.",
        ],
    )

    footer_text = "CSE 598 · AI Workforce · Milestone 2 Report · main f29cb95"
    for section in document.sections:
        for paragraph in section.footer.paragraphs:
            if paragraph.text.strip():
                replace_paragraph(paragraph, footer_text)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    props = document.core_properties
    props.title = "CSE 598 AI Workforce Milestone 2 Report"
    props.subject = "Working agentic system, preliminary evaluation, stakeholder status, and remaining work"
    props.author = "Manas Tole; Asmi Phulgam; Shreya Kale; Pratik Chaudhari"
    props.keywords = "CSE 598, AI Workforce, Milestone 2, agentic system, evaluation"
    props.comments = "Populated from supplied template and verified main commit f29cb95."

    # Keep the template's language and page geometry; only request a fresh field
    # update if Word discovers any inherited page fields.
    settings = document.settings._element
    update_fields = settings.find(qn("w:updateFields"))
    if update_fields is not None:
        update_fields.set(qn("w:val"), "true")

    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
