# Dashboard accessibility

The operations console (`src/ai_workforce/static/`) targets WCAG 2.2 AA.

## What is implemented

| Area | Behaviour |
|---|---|
| Keyboard | Every control is a native `<button>`, `<input>`, `<textarea>`, `<summary>` or link. Run-log entries are buttons in a list (not clickable `<article>`s). A **Skip to main content** link is the first tab stop. |
| Focus | One global `:focus-visible` style: a 3px outline with offset plus a 6px halo. It is visible on the light page and the dark panel, and conveys focus by shape/thickness, not colour alone. The custom toggle switch shows focus on its track. The selected run also has a 4px left border, so it does not rely on background colour. |
| Focus management | Selecting a run, deploying, or approving/rejecting moves focus to the run detail heading. Re-rendering the run list keeps focus on the same run. |
| Labels | Decorative glyphs (`→`, `⌁`, noise layer, step dots) are `aria-hidden`. The metrics group, plan list, approval group and detail panel have accessible names. Times use `<time datetime>`. |
| Status text | Run status badges, step statuses (e.g. "waiting approval", "completed") and the approval prompt are written as text; colour is only an extra cue. Badges also have a border. |
| Live regions | `#toast` (`role=status`, polite) for confirmations; `#toast-error` (`role=alert`, assertive) for errors; `#sr-status` (polite, visually hidden) for loading ("Loading run details…", "Refreshing run log…", "Deploying workforce…") and run status changes. Containers set `aria-busy` while loading. |
| Contrast | Muted text darkened to `#5a5a53` (≈6:1 on the page background) and dim text on the dark panel lightened. Text below 11px was raised to 11px. |
| Motion / contrast modes | `prefers-reduced-motion` disables transitions; `forced-colors` keeps badges and the active run distinguishable. |

## How to check it (browser tooling)

1. `workforce serve` and open <http://127.0.0.1:8000>.
2. **Lighthouse**: Chrome DevTools → Lighthouse → *Accessibility* → Analyze. Target: no failing audits.
3. **axe**: install the axe DevTools extension (or run `npx @axe-core/cli http://127.0.0.1:8000`). Run it once on the empty page and again after creating a run with *Include stakeholder update* on (to cover the approval state). Target: 0 violations.
4. **Keyboard walk-through** (no mouse): press Tab from the top. Confirm the skip link appears, every control is reachable in a logical order, the focus ring is always visible, Enter/Space activates run entries and Approve/Reject, and the "Evidence and calculation inputs" and audit sections toggle with Enter/Space.
5. **Screen reader**: with VoiceOver (macOS: Cmd+F5) deploy a run and confirm you hear "Deploying workforce…", then the run status, and "Human approval is required." when a step waits. Trigger an error (e.g. clear the objective via DevTools) and confirm it is announced immediately.
6. **DevTools → Accessibility tab**: inspect a run entry, a status badge and the approval group; check names/roles. Use *Rendering → Emulate vision deficiencies* (achromatopsia) to confirm statuses and focus remain distinguishable.

Record results (tool, date, violations found/fixed) in the pull request when changing the UI.
