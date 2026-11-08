"""Build the AI Workforce final capstone report as a polished DOCX."""

# The report's prose and Graphviz source intentionally remain on long lines so
# the generated document text is easy to audit against the final evidence.
# ruff: noqa: E501, I001

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "artifacts" / "final-report"
TMP_DIR = ROOT / "tmp" / "final-report"
EVIDENCE_DIR = ROOT / "artifacts" / "evidence"
OUTPUT_DOCX = OUTPUT_DIR / "AI_Workforce_Final_Report.docx"
ARCHITECTURE_PNG = TMP_DIR / "architecture.png"

DOCS_SKILL = Path(
    "/Users/manastole/.codex/plugins/cache/openai-primary-runtime/documents/"
    "26.826.12353/skills/documents"
)
sys.path.insert(0, str(DOCS_SKILL / "scripts"))
from table_geometry import apply_table_geometry  # noqa: E402


NAVY = "17365D"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
ACCENT = "8FCE00"
MUTED = "5B6573"
LIGHT = "F2F4F7"
PALE_BLUE = "E8EEF5"
PALE_GREEN = "EAF5E3"
PALE_GOLD = "FFF4CE"
WHITE = "FFFFFF"
BLACK = "111111"
RED = "9B1C1C"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_border(cell, color: str = "D5DAE2", size: str = "4") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def set_run_font(
    run,
    *,
    name: str = "Calibri",
    size: float | None = None,
    color: str | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_field(paragraph, instruction: str, display: str = "1") -> None:
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = display
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run = paragraph.add_run()
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, size=9, color=MUTED)


def add_hyperlink(paragraph, text: str, url: str) -> None:
    relationship = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.extend([color, underline])
    run.append(properties)
    value = OxmlElement("w:t")
    value.text = text
    run.append(value)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    table_header = OxmlElement("w:tblHeader")
    table_header.set(qn("w:val"), "true")
    tr_pr.append(table_header)


def set_image_alt(paragraph, description: str) -> None:
    for element in paragraph._p.xpath(".//wp:docPr"):
        element.set("descr", description)


def set_keep_with_next(paragraph, value: bool = True) -> None:
    paragraph.paragraph_format.keep_with_next = value


def configure_styles(document: Document) -> None:
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.10

    heading_specs = {
        "Heading 1": (16, BLUE, 16, 8),
        "Heading 2": (13, BLUE, 12, 6),
        "Heading 3": (12, DARK_BLUE, 8, 4),
    }
    for name, (size, color, before, after) in heading_specs.items():
        style = styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for list_name in ("List Bullet", "List Number"):
        style = styles[list_name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.5)
        style.paragraph_format.first_line_indent = Inches(-0.25)
        style.paragraph_format.space_after = Pt(8)
        style.paragraph_format.line_spacing = 1.167

    caption = styles["Caption"]
    caption.font.name = "Calibri"
    caption.font.size = Pt(9)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(10)
    caption.paragraph_format.keep_with_next = False


def configure_section(section, first_page: bool = False) -> None:
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    section.different_first_page_header_footer = first_page


def add_running_furniture(section) -> None:
    _fill_running_header(section.header)
    _fill_running_footer(section.footer)


def _fill_running_header(header) -> None:
    paragraph = header.paragraphs[0]
    paragraph.clear()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run("AI WORKFORCE  |  CSE 598 CAPSTONE FINAL REPORT")
    set_run_font(run, size=8, color=MUTED, bold=True)
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "D5DAE2")
    border.append(bottom)
    paragraph._p.get_or_add_pPr().append(border)


def _fill_running_footer(footer) -> None:
    paragraph = footer.paragraphs[0]
    paragraph.clear()
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        Inches(6.5), WD_ALIGN_PARAGRAPH.RIGHT
    )
    run = paragraph.add_run("Group 3  |  Final verified build: 65034a8")
    set_run_font(run, size=8, color=MUTED)
    run = paragraph.add_run("\tPage ")
    set_run_font(run, size=9, color=MUTED)
    add_field(paragraph, "PAGE")


def add_heading(document: Document, text: str, level: int = 1) -> None:
    paragraph = document.add_paragraph(text, style=f"Heading {level}")
    set_keep_with_next(paragraph)


def add_body(document: Document, text: str, *, bold_lead: str | None = None) -> None:
    paragraph = document.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        set_run_font(lead, bold=True)
        text = text[len(bold_lead) :]
    run = paragraph.add_run(text)
    set_run_font(run)


def add_bullets(document: Document, items: list[str]) -> None:
    for item in items:
        paragraph = document.add_paragraph(style="List Bullet")
        run = paragraph.add_run(item)
        set_run_font(run)


def _new_decimal_numbering(document: Document) -> int:
    numbering = document.part.numbering_part.element
    abstract_ids = [
        int(element.get(qn("w:abstractNumId")))
        for element in numbering.findall(qn("w:abstractNum"))
    ]
    num_ids = [
        int(element.get(qn("w:numId"))) for element in numbering.findall(qn("w:num"))
    ]
    abstract_id = max(abstract_ids, default=0) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    num_format = OxmlElement("w:numFmt")
    num_format.set(qn("w:val"), "decimal")
    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), "%1.")
    justification = OxmlElement("w:lvlJc")
    justification.set(qn("w:val"), "left")
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "720")
    tabs.append(tab)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "720")
    indent.set(qn("w:hanging"), "360")
    p_pr.extend([tabs, indent])
    level.extend([start, num_format, level_text, justification, p_pr])
    abstract.append(level)
    numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(num)
    return num_id


def add_numbered(document: Document, items: list[str]) -> None:
    num_id = _new_decimal_numbering(document)
    for item in items:
        paragraph = document.add_paragraph(style="List Number")
        p_pr = paragraph._p.get_or_add_pPr()
        num_pr = p_pr.get_or_add_numPr()
        ilvl = OxmlElement("w:ilvl")
        ilvl.set(qn("w:val"), "0")
        num_id_element = OxmlElement("w:numId")
        num_id_element.set(qn("w:val"), str(num_id))
        num_pr.extend([ilvl, num_id_element])
        run = paragraph.add_run(item)
        set_run_font(run)


def add_callout(document: Document, label: str, text: str, fill: str = PALE_GREEN) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(10)
    paragraph.paragraph_format.left_indent = Inches(0.12)
    paragraph.paragraph_format.right_indent = Inches(0.12)
    p_pr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    p_pr.append(shading)
    border = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), ACCENT if fill == PALE_GREEN else BLUE)
    border.append(left)
    p_pr.append(border)
    lead = paragraph.add_run(f"{label}: ")
    set_run_font(lead, bold=True, color=NAVY)
    run = paragraph.add_run(text)
    set_run_font(run, color=BLACK)


def add_table(
    document: Document,
    headers: list[str],
    rows: list[list[str]],
    widths_dxa: list[int],
    *,
    font_size: float = 9.2,
    status_column: int | None = None,
) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    header_row = table.rows[0]
    set_repeat_table_header(header_row)
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.text = header
        set_cell_shading(cell, NAVY)
        set_cell_border(cell, NAVY)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        for run in paragraph.runs:
            set_run_font(run, size=9, color=WHITE, bold=True)
    for row_values in rows:
        row = table.add_row()
        for index, value in enumerate(row_values):
            cell = row.cells[index]
            cell.text = str(value)
            set_cell_border(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if status_column is not None and index == status_column:
                if str(value).upper() in {"PASS", "IMPLEMENTED", "COMPLETE"}:
                    set_cell_shading(cell, PALE_GREEN)
                elif str(value).upper() in {"NOT RUN", "PLANNED", "PARTIAL"}:
                    set_cell_shading(cell, PALE_GOLD)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(1)
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
                if index == status_column or len(str(value)) < 12
                else WD_ALIGN_PARAGRAPH.LEFT
            )
            for run in paragraph.runs:
                set_run_font(run, size=font_size, color=BLACK)
                if status_column is not None and index == status_column:
                    run.bold = True
    apply_table_geometry(
        table,
        widths_dxa,
        table_width_dxa=sum(widths_dxa),
        indent_dxa=120,
        cell_margins_dxa={"top": 90, "bottom": 90, "start": 120, "end": 120},
    )
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)


def add_figure(document: Document, image_path: Path, caption: str, width: float, alt: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Inches(width))
    set_image_alt(paragraph, alt)
    caption_paragraph = document.add_paragraph(caption, style="Caption")
    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def create_architecture_diagram() -> None:
    dot = r'''
digraph G {
  graph [rankdir=TB, bgcolor="white", pad="0.20", nodesep="0.28", ranksep="0.45", splines=ortho];
  node [shape=box, style="rounded,filled", fontname="Arial", fontsize=12, color="#9CA8B6", fillcolor="#F5F7FA", margin="0.18,0.12"];
  edge [color="#687487", penwidth=1.2, arrowsize=0.7];
  intake [label="Interfaces\nUI | API | CLI | SDK", fillcolor="#E8EEF5", color="#2E74B5"];
  plan [label="Plan and govern\nmanager | planner | validator", fillcolor="#E8EEF5", color="#2E74B5"];
  tools [label="Execute\nsearch | calculate | synthesize", fillcolor="#F2F4F7"];
  critic [label="Verify\ngrounding critic | one revision", fillcolor="#EAF5E3", color="#5A9A2C"];
  action [label="Act\nexact-step approval | idempotent outbox", fillcolor="#FFF4CE", color="#B58B00"];
  state [label="SQLite\nruns | steps | events | memory", shape=cylinder, fillcolor="#F2F4F7"];
  {rank=same; intake; plan; tools; critic; action}
  intake -> plan -> tools -> critic -> action;
  tools -> plan [label="error / weak grounding", fontname="Arial", fontsize=9, color="#9B1C1C", constraint=false];
  plan -> state [dir=both];
  tools -> state;
  critic -> state;
  action -> state;
}
'''
    ARCHITECTURE_PNG.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["dot", "-Tpng", "-Gdpi=180", "-o", str(ARCHITECTURE_PNG)],
        input=dot,
        text=True,
        check=True,
    )


def add_cover(document: Document) -> None:
    section = document.sections[0]
    configure_section(section, first_page=False)

    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(58)

    kicker = document.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = kicker.add_run("CSE 598  |  CAPSTONE PROJECT  |  FINAL REPORT")
    set_run_font(run, size=10, color=BLUE, bold=True)
    kicker.paragraph_format.space_after = Pt(18)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(8)
    run = title.add_run("AI Workforce")
    set_run_font(run, size=31, color=NAVY, bold=True)

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(28)
    run = subtitle.add_run("A Governed, Self-Correcting Multi-Agent Execution Platform")
    set_run_font(run, size=16, color=DARK_BLUE)

    rule = document.add_paragraph()
    rule.paragraph_format.space_after = Pt(24)
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:color"), ACCENT)
    border.append(bottom)
    rule._p.get_or_add_pPr().append(border)

    metadata = [
        "Group 3",
        "Manas Tole  |  Asmi Phulgam  |  Shreya Kale  |  Pratik Chaudhari",
        "Stakeholder: Kunal Ramesh Jadhav",
        "Final build: v2.0.0  |  Commit 65034a8",
        "November 7, 2026",
    ]
    for index, value in enumerate(metadata):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(5 if index < 2 else 3)
        run = paragraph.add_run(value)
        set_run_font(
            run,
            size=12 if index == 0 else 10.5,
            color=NAVY if index == 0 else MUTED,
            bold=index in {0, 3},
        )

    document.add_paragraph().paragraph_format.space_after = Pt(44)
    repo = document.add_paragraph()
    repo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = repo.add_run("Repository: ")
    set_run_font(run, size=9.5, color=MUTED, bold=True)
    add_hyperlink(repo, "github.com/jadhav-kunal/ai-workforce-capstone", "https://github.com/jadhav-kunal/ai-workforce-capstone")

    document.add_section(WD_SECTION.NEW_PAGE)


def build_report() -> None:
    results = json.loads((EVIDENCE_DIR / "current-system-results.json").read_text())
    create_architecture_diagram()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    document = Document()
    configure_styles(document)
    add_cover(document)

    add_heading(document, "Executive Summary", 1)
    add_body(
        document,
        "AI Workforce is a local-first, governed multi-agent platform for converting a natural-language objective into a typed plan, bounded tool calls, a sourced action brief, an exact-step approval decision, and a reusable lesson. The final v2 implementation replaces the baseline's fixed planner with provider-generated plans that are validated before execution, repaired once when invalid, and replaced by a deterministic fallback when repair fails.",
    )
    add_callout(
        document,
        "Final outcome",
        "The committed system passed 19 of 19 automated tests, achieved 82% statement coverage, passed all 5 deterministic evaluation scenarios, produced zero unauthorized actions in 2 approval-sensitive scenarios, and preserved a complete trace for every scenario.",
    )
    add_body(
        document,
        "The implementation adds bounded replanning, BM25 evidence and memory retrieval, claim-level citation and numeric checks, one writer revision, recipient pinning, provider retry with exponential backoff, and deterministic run-and-step idempotency. The project remains an educational prototype: real application delivery, production authentication, open-web retrieval, and completed live-model/human-rating experiments remain out of scope or future work.",
    )

    add_heading(document, "Document Map", 2)
    add_numbered(
        document,
        [
            "Problem definition and final scope",
            "Implemented architecture and system behavior",
            "Technical implementation and safety controls",
            "Evaluation method and exact results",
            "Requirement traceability, limitations, and future work",
            "Reproduction commands and references",
        ],
    )

    add_heading(document, "1. Problem Definition and Final Scope", 1)
    add_heading(document, "1.1 Problem", 2)
    add_body(
        document,
        "Teams increasingly use language models for multi-step research-to-action work, but a single completion cannot reliably preserve durable state, coordinate tools, recover from failure, connect claims to source passages, or wait safely for human approval. The capstone addresses this gap by separating model reasoning from code-owned authority. The provider may propose a plan; the runtime owns schemas, risk levels, budgets, approvals, state transitions, and side effects.",
    )
    add_heading(document, "1.2 Intended user and demonstration scenario", 2)
    add_body(
        document,
        "The primary user is a project or operations lead who needs to analyze supplied evidence, calculate a metric, prepare an action brief, and optionally notify a stakeholder. The demonstration scenario evaluates an AI-support pilot, calculates the repetitive-ticket opportunity, produces a cited brief, and pauses before writing a simulated stakeholder message.",
    )
    add_heading(document, "1.3 Final scope", 2)
    add_table(
        document,
        ["Area", "Final scope"],
        [
            ["Inputs", "Natural-language objective, supplied source passages, optional arithmetic expression, and optional message request."],
            ["Outputs", "Validated typed plan, observations, sourced brief, grounding verdict, approval state, audit trace, and scored lesson."],
            ["In scope", "Provider planning, validation, repair/fallback, bounded replanning, grounding, memory, BM25 retrieval, SQLite, UI/API/CLI/SDK, and offline demo mode."],
            ["Out of scope", "Real email or Slack delivery, open web or shell access, production authentication, fine-tuning, and high-impact decisions."],
        ],
        [1800, 7560],
        font_size=9.3,
    )

    add_heading(document, "2. Implemented Architecture", 1)
    add_body(
        document,
        "The final architecture uses plan-then-execute with observation-driven replanning. A complete plan is inspectable before action, while recoverable failures or failed grounding can revise only the remaining work. Every run, plan step, output, approval, failure, and lesson is persisted in SQLite.",
    )
    add_figure(
        document,
        ARCHITECTURE_PNG,
        "Figure 1. Final v2 architecture and code-owned governance boundaries.",
        6.35,
        "Flow diagram of the AI Workforce v2 architecture from interfaces through manager, planner, validator, registered tools, grounding critic, approval gate, simulated outbox, and SQLite state.",
    )
    add_heading(document, "2.1 End-to-end workflow", 2)
    add_numbered(
        document,
        [
            "Intake: save the objective and context as a queued run.",
            "Delegate: retrieve up to three qualifying prior lessons with BM25 and establish the execution budget.",
            "Plan: request typed steps from the configured provider and validate every tool and argument.",
            "Repair or fall back: allow one repair for an invalid plan, then use the deterministic safe plan.",
            "Execute and observe: persist outputs and errors after every bounded tool call.",
            "Verify: check citation identifiers and numeric consistency; permit one writer revision.",
            "Replan: rebuild remaining work after a recoverable tool or grounding failure, up to two times and within eight total attempts.",
            "Approve: pause at the exact high-risk message step; rejection is terminal.",
            "Learn: save a scored, source-run-linked lesson after successful completion.",
        ],
    )

    add_heading(document, "2.2 Agent and tool responsibilities", 2)
    add_table(
        document,
        ["Component", "Implemented responsibility", "Authority"],
        [
            ["Manager", "Packages objective, budgets, and top-3 prior lessons.", "No tool calls"],
            ["Planner", "Proposes ordered typed tool steps and replans remaining work.", "Proposal only"],
            ["Validator", "Checks schema, registered tool, arguments, budget, order, and recipient pinning.", "Code-owned"],
            ["Researcher", "Ranks supplied passages with BM25 and assigns stable S# identifiers.", "Low risk"],
            ["Analyst", "Evaluates arithmetic through a restricted AST subset.", "Low risk"],
            ["Writer", "Builds a structured brief with passage and calculator citations.", "Low risk"],
            ["Critic", "Checks citation IDs and numeric support before messaging and records lessons.", "No external action"],
            ["Operator", "Writes the approved message to a deterministic simulated outbox artifact.", "High risk; approval required"],
        ],
        [1600, 5540, 2220],
        font_size=8.7,
    )

    add_heading(document, "3. Technical Implementation", 1)
    add_heading(document, "3.1 Validated dynamic planning", 2)
    add_body(
        document,
        "The provider receives the objective, public context, tool catalog with JSON schemas, prior lessons, observations, completed tools, and remaining budget. Pydantic models enforce a 1-to-8 step plan. Each step is revalidated against its registered tool's argument model. Risk is copied from the registry rather than trusted from model output. Message plans must follow synthesis, and a user-supplied recipient cannot be replaced by the provider.",
    )
    add_heading(document, "3.2 Recovery and provider resilience", 2)
    add_body(
        document,
        "A tool exception becomes a durable observation and step.failed event. The planner may regenerate only the unfinished portion of the plan. The runtime enforces at most two replans and eight attempted steps. OpenAI-compatible HTTP calls use three attempts with exponential backoff. Completed steps are preserved on resume.",
    )
    add_heading(document, "3.3 Retrieval, grounding, and synthesis", 2)
    add_body(
        document,
        "knowledge.search applies BM25 to supplied passages and returns stable S1, S2, and related identifiers. The synthesis tool carries those identifiers into structured claims and adds a CALC citation for numeric outputs. Before messaging, the critic verifies that every cited passage exists and that every claimed number appears in its supporting observation. A source-free run is allowed only when the brief explicitly discloses hypothesis-level evidence. Failed grounding permits one writer revision and then enters the bounded replan path.",
    )
    add_heading(document, "3.4 Memory and learning", 2)
    add_body(
        document,
        "Completed runs store an episodic lesson with objective keywords, quality score, source run ID, and timestamp. Future runs retrieve at most three memories above the quality threshold, rank them with BM25, and expose both the lesson and its provenance to the manager. Memory is advisory and cannot alter tools, risk levels, recipients, or policy.",
    )
    add_heading(document, "3.5 Persistence and interfaces", 2)
    add_bullets(
        document,
        [
            "SQLite persists runs, step arguments and outputs, append-only events, approvals, errors, and lessons.",
            "FastAPI exposes run creation, inspection, approval, tool catalog, health, and metrics endpoints.",
            "The same orchestration service is available through the dashboard, CLI, and Python SDK.",
            "The v2 dashboard displays plan source, validated arguments, attempts, replans, revisions, evidence IDs, calculation output, policy outcome, and audit history.",
        ],
    )

    add_heading(document, "4. Governance, Safety, and Failure Controls", 1)
    add_table(
        document,
        ["Risk", "Implemented control", "Observed evidence"],
        [
            ["Unknown or malformed plan", "Strict Pydantic plan and tool-argument validation; one repair, then fallback.", "Invalid-plan repair and fallback tests pass."],
            ["Prompt-driven recipient change", "Recipient pinned to user input; model output cannot replace it.", "Wrong-recipient test falls back safely."],
            ["Message before evidence review", "Message step requires earlier synthesis; grounding must complete first.", "Direct-to-message plan is rejected."],
            ["Unauthorized side effect", "Exact run-and-step approval gate; rejection is terminal.", "0/2 unauthorized actions."],
            ["Duplicate message", "Stable SHA-256-derived run-and-step idempotency key.", "Repeated invocation returns duplicate_suppressed=true."],
            ["Arbitrary calculation code", "Restricted arithmetic AST; imports, file reads, and containers rejected.", "Malicious expression scenario passes."],
            ["Runaway recovery", "Eight-attempt global cap and two-replan cap.", "Grounding failure stops after two replans."],
            ["Memory policy drift", "Retrieved lessons are advisory data and cannot change authority.", "Tool risk and policy remain code-owned."],
        ],
        [1850, 4210, 3300],
        font_size=8.4,
    )

    add_heading(document, "5. Evaluation Method", 1)
    add_heading(document, "5.1 Environment", 2)
    add_table(
        document,
        ["Item", "Value"],
        [
            ["Commit", results["environment"]["commit"]],
            ["Provider", results["environment"]["provider"]],
            ["Python", results["environment"]["python"]],
            ["Platform", results["environment"]["platform"]],
            ["Test command", "pytest --cov=ai_workforce --cov-report=term-missing"],
            ["Evidence command", "python scripts/collect_evidence.py"],
        ],
        [2050, 7310],
        font_size=9.2,
    )
    add_heading(document, "5.2 Evaluation scenarios", 2)
    add_body(
        document,
        "The deterministic evidence suite executes five end-to-end scenarios without an API key. It measures workflow correctness, authorization, idempotent side effects, safe arithmetic, memory reuse, local latency, and trace availability. The built-in quality score is a grounding/workflow heuristic, not factual accuracy or a substitute for human evaluation.",
    )

    add_heading(document, "6. Results", 1)
    add_heading(document, "6.1 Headline results", 2)
    add_table(
        document,
        ["Metric", "Result", "Interpretation"],
        [
            ["Automated tests", "19/19 PASS", "All current unit, workflow, API, persistence, recovery, and security tests passed."],
            ["Statement coverage", "82%", "975 statements; 179 not covered in the measured run."],
            ["Scenario pass rate", results["metrics"]["scenario_pass_rate"], "All deterministic evidence scenarios met their assertions."],
            ["Unauthorized actions", results["metrics"]["unauthorized_action_rate"], "No message artifact was created before approval or after rejection."],
            ["Approved message", results["metrics"]["approved_action_outbox_entries"], "The approved path wrote exactly one simulated artifact."],
            ["Trace completeness", "100%", "Every scenario exposed a stored event history."],
            ["Median local latency", f"{results['metrics']['median_local_latency_ms']} ms", "Deterministic local execution; excludes human approval wait."],
            ["Calculation", results["metrics"]["calculation_result"], "Restricted calculator returned the expected value."],
        ],
        [2100, 1700, 5560],
        font_size=8.8,
    )

    add_heading(document, "6.2 Scenario-level results", 2)
    scenario_rows = []
    for scenario in results["scenarios"]:
        latency = scenario.get("latency_ms")
        if latency is None:
            latency = scenario.get("latency_ms_excluding_human_wait")
        run = scenario.get("run") or scenario.get("after_approval") or {}
        scenario_rows.append(
            [
                scenario["id"],
                scenario["name"],
                "PASS" if scenario["passed"] else "FAIL",
                f"{latency:.3f} ms",
                run.get("id", ""),
            ]
        )
    add_table(
        document,
        ["ID", "Scenario", "Result", "Latency", "Run ID"],
        scenario_rows,
        [600, 3420, 1050, 1500, 2790],
        font_size=8.5,
        status_column=2,
    )

    add_heading(document, "6.3 Module coverage", 2)
    add_table(
        document,
        ["Module", "Statements", "Coverage"],
        [
            ["models.py", "56", "100%"],
            ["config.py", "27", "96%"],
            ["tools.py", "165", "95%"],
            ["agents.py", "151", "94%"],
            ["db.py", "84", "93%"],
            ["orchestrator.py", "227", "93%"],
            ["app.py", "71", "83%"],
            ["sdk.py", "20", "65%"],
            ["llm.py", "91", "57%"],
            ["cli.py", "80", "0%"],
            ["Total", "975", "82%"],
        ],
        [4770, 2100, 2490],
        font_size=9,
    )
    add_body(
        document,
        "Coverage is strongest in the core tools, agents, repository, and orchestrator. The primary remaining gaps are the command-line entry path and live-provider network branches; these are visible rather than hidden by the aggregate score.",
    )

    add_heading(document, "6.4 Approval and completion evidence", 2)
    add_body(
        document,
        "The dashboard evidence below shows the same governed workflow at its two decision points. These screenshots were captured during development; the machine-readable scenario results and timing tables above were regenerated against final commit 65034a8.",
    )
    add_figure(
        document,
        EVIDENCE_DIR / "current-waiting-approval.png",
        "Figure 2. The run pauses before the high-risk message step; no outbox artifact exists yet.",
        5.45,
        "AI Workforce dashboard showing completed research, calculation, and synthesis steps and a waiting-approval message step with Approve and Reject controls.",
    )
    add_figure(
        document,
        EVIDENCE_DIR / "current-completed-result.png",
        "Figure 3. After exact-step approval, the run completes with evidence, calculation, and simulated-only policy outcome.",
        5.15,
        "AI Workforce dashboard showing a completed run, two supplied passages, the 1200 times 0.42 calculation equal to 504, and an approved simulated-only message outcome.",
    )

    document.add_page_break()
    add_heading(document, "6.5 Results not yet collected", 2)
    add_callout(
        document,
        "Evidence boundary",
        "No final live-model benchmark, token/cost comparison, blinded human-rating study, or semantic-memory ablation was present in the repository. This report therefore does not invent those results.",
        fill=PALE_GOLD,
    )
    add_table(
        document,
        ["Planned evaluation", "Final status", "Needed evidence"],
        [
            ["Single-call vs. multi-agent quality comparison", "NOT RUN", "Versioned objective set and equal-model-budget results."],
            ["Three-rater relevance/factuality/actionability study", "NOT RUN", "Blinded rubric scores and inter-rater summary."],
            ["Live-provider token, cost, and latency comparison", "NOT RUN", "Provider usage records under the same model and prompts."],
            ["Memory ablation", "NOT RUN", "Paired runs with and without retrieved lessons."],
        ],
        [3400, 1450, 4510],
        font_size=8.8,
        status_column=1,
    )

    add_heading(document, "7. Final Requirement Traceability", 1)
    add_table(
        document,
        ["Requirement", "Status", "Implementation evidence"],
        [
            ["Typed provider-generated plans", "IMPLEMENTED", "Planner request, Pydantic schema, registered-tool validation."],
            ["One repair then deterministic fallback", "IMPLEMENTED", "plan.invalid, plan.repaired, and plan.fallback events plus tests."],
            ["At most 8 attempts and 2 replans", "IMPLEMENTED", "Run counters and bounded recovery tests."],
            ["BM25 source retrieval with passage IDs", "IMPLEMENTED", "knowledge.search returns ranked S# findings."],
            ["Grounding critic before messaging", "IMPLEMENTED", "Citation and numeric checks, one revision, direct-message rejection."],
            ["Exact-step approval", "IMPLEMENTED", "waiting_approval state and run/step-bound approval records."],
            ["Idempotent simulated message", "IMPLEMENTED", "Stable run+step key and duplicate suppression test."],
            ["Top-3 lesson retrieval", "IMPLEMENTED", "BM25 memory ranking and source-run provenance."],
            ["Three provider retries", "IMPLEMENTED", "Exponential backoff in OpenAI-compatible provider."],
            ["Offline reproducibility", "IMPLEMENTED", "DemoProvider; 5/5 evidence suite without an API key."],
            ["Real Slack/email integration", "PLANNED", "Explicitly outside final prototype scope."],
            ["Production identity and tenant controls", "PLANNED", "Required before remote deployment."],
        ],
        [3120, 1620, 4620],
        font_size=8.4,
        status_column=1,
    )

    add_heading(document, "8. Discussion", 1)
    add_heading(document, "8.1 What the results demonstrate", 2)
    add_bullets(
        document,
        [
            "The orchestration contract is reproducible offline and does not depend on a paid model for grading.",
            "The planner can be dynamic without granting the provider direct tool or policy authority.",
            "Tool errors and unsupported drafts follow a bounded, observable recovery path instead of silently looping.",
            "Human approval is a durable state transition tied to one exact consequential step.",
            "Cross-run memory is retrieved and attributed without allowing memories to rewrite safety policy.",
        ],
    )
    add_heading(document, "8.2 Limitations", 2)
    add_bullets(
        document,
        [
            "Demo-mode plans and synthesis are deterministic and do not prove live-model reasoning quality.",
            "Grounding checks validate citation existence and numeric consistency, not full semantic entailment or factual truth.",
            "BM25 retrieval is lexical and can miss semantically related evidence or lessons.",
            "SQLite and in-process execution are single-node choices without production concurrency guarantees.",
            "The local API has no authentication and should not be exposed to the public internet.",
            "The simulated outbox proves governance and idempotency, not connector authentication or delivery behavior.",
            "CLI and live-provider branches have the lowest automated coverage and should be prioritized next.",
        ],
    )

    add_heading(document, "9. Recommended Next Work", 1)
    add_numbered(
        document,
        [
            "Run the fixed live-model objective set against both the single-call baseline and v2 under equal model, token, and time budgets.",
            "Complete the three-rater blinded evaluation and report medians, variability, disagreements, and failure cases.",
            "Add explicit token/cost accounting and test provider retry behavior with controlled network failures.",
            "Add semantic retrieval with provenance, review, expiration, conflict handling, and deletion controls.",
            "Add authentication, tenant isolation, durable queued workers, transactional outbox semantics, rate limits, and tamper-evident audit storage before any production deployment.",
            "Increase CLI and live-provider test coverage and add a CI matrix across supported Python versions.",
        ],
    )

    add_heading(document, "10. Conclusion", 1)
    add_body(
        document,
        "AI Workforce v2 completes the core semester development objective: it evolves the fixed baseline into a governed, observable, and self-correcting agent workflow while preserving human authority over consequential actions. The final committed build validates provider plans, ranks evidence and lessons, verifies claims before messaging, recovers within explicit budgets, suppresses duplicate side effects, and records an inspectable trace. The measured results establish strong workflow correctness and safety in deterministic mode. They do not yet establish superiority on live-model answer quality, cost, or human usefulness; those remain the necessary final empirical extension.",
    )

    add_heading(document, "Appendix A. Reproduction Commands", 1)
    commands = [
        "python3 -m venv .venv",
        "source .venv/bin/activate",
        "pip install -e '.[dev]'",
        "ruff check src tests",
        "pytest --cov=ai_workforce --cov-report=term-missing",
        "python scripts/collect_evidence.py",
        "workforce serve",
    ]
    for command in commands:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.25)
        paragraph.paragraph_format.space_after = Pt(3)
        p_pr = paragraph._p.get_or_add_pPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), LIGHT)
        p_pr.append(shading)
        run = paragraph.add_run(command)
        set_run_font(run, name="Menlo", size=9, color=BLACK)

    add_heading(document, "Appendix B. References", 1)
    references = [
        ("Group 3 Milestone 1 Report", None, "CSE 598 Capstone Project, September 2026."),
        ("AI Workforce repository", "https://github.com/jadhav-kunal/ai-workforce-capstone", "Final build and reproducible evidence."),
        ("NIST AI Risk Management Framework 1.0", "https://www.nist.gov/itl/ai-risk-management-framework", "Governance and risk-management context."),
        ("ReAct: Synergizing Reasoning and Acting in Language Models", "https://arxiv.org/abs/2210.03629", "Reasoning and action pattern."),
        ("Reflexion: Language Agents with Verbal Reinforcement Learning", "https://arxiv.org/abs/2303.11366", "Episodic verbal learning context."),
        ("AutoGen: Enabling Next-Gen LLM Applications", "https://arxiv.org/abs/2308.08155", "Multi-agent application architecture context."),
    ]
    for index, (title, url, note) in enumerate(references, start=1):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.32)
        paragraph.paragraph_format.first_line_indent = Inches(-0.32)
        paragraph.paragraph_format.space_after = Pt(5)
        paragraph.paragraph_format.keep_together = True
        run = paragraph.add_run(f"{index}. ")
        set_run_font(run, bold=True)
        if url:
            add_hyperlink(paragraph, title, url)
        else:
            run = paragraph.add_run(title)
            set_run_font(run, color=BLUE)
        run = paragraph.add_run(f". {note}")
        set_run_font(run)

    # Isolate the cover in its own section and use one body page style. This
    # keeps the cover clean while rendering the same furniture on every body
    # page in both Word and LibreOffice.
    document.settings.odd_and_even_pages_header_footer = False
    for index, section in enumerate(document.sections):
        configure_section(section, first_page=False)
        if index == 0:
            continue
        for part in (section.header, section.footer):
            part.is_linked_to_previous = False
        add_running_furniture(section)

    document.core_properties.title = "AI Workforce - Final Capstone Report"
    document.core_properties.subject = "Governed multi-agent execution platform final results"
    document.core_properties.author = "CSE 598 Group 3"
    document.core_properties.keywords = "AI agents, governance, planning, grounding, evaluation"
    document.core_properties.comments = "Generated from verified commit 65034a8."
    document.save(OUTPUT_DOCX)
    print(OUTPUT_DOCX)


if __name__ == "__main__":
    build_report()
