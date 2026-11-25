# Milestone 2 template contract

## Reference

- Retained source: `/Users/manastole/Downloads/CSE598_AI_Workforce_Milestone_2_Draft.docx`
- SHA-256: `b341e84504a08a5705f6cda1a1e32d3485219c2c6e3105c47eea24528a7e99bf`
- Baseline render: `tmp/milestone2/template-reference-render/` (7 pages, inspected page by page)
- Structure: 1 section, 73 body paragraphs, 7 tables, no drawings, no fields, no content controls.

## Page system

- US Letter portrait, one continuous section.
- Margins: 0.90 in left/right, 0.78 in top, 0.72 in bottom.
- Footer is independent and centered; no visible header.
- Footer text: `CSE 598 · AI Workforce · Milestone 2 evidence-grounded draft`.
- Page breaks are automatic; no first/odd/even page variants.

## Typography and components

- Normal: Aptos 10 pt, 6 pt after.
- Title: Aptos Display 19 pt bold, `#183151`, 15 pt after, single spacing.
- Heading 1: Aptos Display 14 pt bold, `#183151`, 24 pt before, keep-with-next.
- Heading 2: Aptos Display 11.5 pt bold, `#224A75`, 10 pt before, keep-with-next.
- Top title line is a Title paragraph followed by two Normal subtitle/status paragraphs.
- Tables use built-in `Light Shading Accent 1`, blue banding/rules, and equal-width source grids:
  - T1: 4x2, grid 4824/4824 DXA.
  - T2/T3/T7: 3 columns, each 3216 DXA.
  - T4/T5/T6: 4 columns, each 2412 DXA.
- Code/setup block uses direct Consolas formatting already present in the template.
- No generic design preset, cover redesign, new header pattern, or alternate color palette is permitted.

## Content flow and editable slots

1. Title/status and T1 metadata: update the report basis, main commit, and verification status.
2. Executive Summary: replace draft caveats with verified implementation/test/evaluation evidence.
3. Section 1 stakeholder follow-up: preserve the documented September 28 meeting; do not invent a later meeting. Mark the required post-implementation review and exact feedback as team input still required. Update T2 responses using implemented evidence.
4. Section 1.2 scope: distinguish retained scope, implemented additions, and remaining boundaries.
5. Section 2 system: update the baseline/extension narrative, T3 status, architecture flow, implementation decisions, budgets, state, and recovery.
6. Section 3 evaluation: replace planned-dataset prose, T4 dataset facts, comparison conditions, metric definitions, and T5 with the newly generated offline results. Preserve the template's B0/B1/P columns; discuss P-M in prose.
7. Section 4 demo: replace baseline-only description and figure placeholders with the current S2 run, two current dashboard screenshots, exact run ID, calculation, approval transition, and outbox result.
8. Section 5 failure analysis: report observed failures from the current evaluation, including recovery, FinQA, and injected-text relay limits.
9. Section 6 remaining work: replace T6 with evidence-backed priorities and no inferred owners.
10. Section 7 repository/contributions: update branch/SHA/setup and T7 from Git author/commit evidence; non-code work remains team-confirmed.
11. Conclusion/references: update to current findings and add the versioned datasets/evaluation artifact.

Stable edit locators are paragraph style plus exact source prefix/heading, and table ordinal plus row/column. All replacements are allowed to reflow, but the section, named styles, table styles, footer, theme, numbering, and package relationships are preserve-only.

## Package preservation

- Preserve: `word/styles.xml`, `word/stylesWithEffects.xml`, `word/theme/theme1.xml`, `word/numbering.xml`, all `customXml/*`, relationship parts, content types, and document properties unless an output-title metadata update is required. Preserve the footer's structure and formatting while changing its status text from draft to the verified main commit.
- Editable: `word/document.xml`; media and document relationships may be extended only for the two requested current-system screenshots.
- The reference must remain byte-for-byte unchanged at its recorded path and hash.

## Fidelity gates

- Final length must be 5-10 pages.
- Render and inspect every page at 100% zoom.
- Section count, page size, margins, named styles, footer, table style, blue palette, and heading hierarchy must remain source-derived.
- No `[TO VERIFY]`, `[TO PROVIDE]`, `[INSERT]`, `[ASSIGN]`, `[ADD]`, or tool citation tokens may remain, except a plain-language stakeholder-review warning that clearly states the missing evidence.
- No invented stakeholder meeting, human ratings, live-model score, token count, or cost result.
- Tables must remain readable without clipping; screenshots and captions must stay paired.
