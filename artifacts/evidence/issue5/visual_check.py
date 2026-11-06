"""Compare dashboard variants: pixels and every computed style, in every state and viewport."""
import json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

BASE = sys.argv[1]; A = Path(sys.argv[2]); B = Path(sys.argv[3]); OUT = Path(sys.argv[4]); OUT.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(1440, 1000), (801, 900), (800, 900), (375, 800)]
PORT = 8765

def seed(db, outbox):
    from ai_workforce.db import Repository
    from ai_workforce.llm import DemoProvider
    from ai_workforce.orchestrator import WorkforceOrchestrator
    from ai_workforce.tools import ToolRegistry
    o = WorkforceOrchestrator(Repository(db), DemoProvider(), ToolRegistry.defaults(outbox))
    src = [{"title": "Support baseline", "content": "The team receives 1,200 tickets per month; 42% are repetitive tier-one requests."},
           {"title": "Pilot constraint", "content": "Any customer-facing output must be reviewed by a support lead."}]
    ids = {}
    r = o.execute(o.create_run("Evaluate the AI support assistant pilot, calculate impact, and notify the sponsor.", {"sources": src, "expression": "1200 * 0.42", "send_message": True, "recipient": "project-sponsor@example.com", "channel": "email"}).id)
    s = next(x for x in r.plan if x.status.value == "waiting_approval"); o.resolve_approval(r.id, s.id, True); ids["completed"] = r.id
    r = o.execute(o.create_run("Prepare a pilot memo and notify the sponsor.", {"sources": src, "send_message": True, "recipient": "a@example.com"}).id)
    ids["waiting"] = r.id
    r = o.execute(o.create_run("Prepare a rejected memo and notify the sponsor.", {"sources": src, "send_message": True}).id)
    s = next(x for x in r.plan if x.status.value == "waiting_approval"); o.resolve_approval(r.id, s.id, False); ids["rejected"] = r.id
    r = o.execute(o.create_run("Calculate an untrusted expression safely.", {"expression": "__import__('os').system('false')", "send_message": False}).id)
    ids["failed"] = r.id
    r = o.create_run("A queued run with a very long objective that must be truncated by the run card rather than wrapping across the whole log column of the dashboard", {"send_message": False}); ids["queued"] = r.id
    return ids

DUMP = """() => {
  const read = (el, pseudo) => { const cs = getComputedStyle(el, pseudo); const o = {}; for (const p of cs) { if (!p.startsWith('--')) o[p] = cs.getPropertyValue(p); } return o; };
  return [...document.querySelectorAll('html, html *')].filter(e => !['SCRIPT','STYLE','LINK','META','TITLE','HEAD'].includes(e.tagName)).map(e => ({
    tag: e.tagName, id: e.id, cls: e.className && e.className.baseVal === undefined ? e.className : '',
    self: read(e, null), before: read(e, '::before'), after: read(e, '::after'), rect: JSON.stringify(e.getBoundingClientRect()) }));
}"""

def scenarios(ids):
    def go(q=""): return lambda p: (p.goto(f"http://127.0.0.1:{PORT}/{q}"), p.wait_for_load_state("networkidle"), p.wait_for_timeout(120))
    def open_all(q):
        def f(p):
            go(q)(p); p.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)"); p.wait_for_timeout(50)
        return f
    def hover(sel, q=""):
        def f(p):
            go(q)(p); loc = p.locator(sel).first
            if loc.is_visible(): loc.hover(); p.wait_for_timeout(300)
        return f
    def focus(sel):
        def f(p):
            go()(p); p.locator(sel).first.focus(); p.wait_for_timeout(100)
        return f
    def toast(p):
        go()(p); p.evaluate("const t=document.querySelector('#toast');t.textContent='Workforce deployed';t.classList.add('show')"); p.wait_for_timeout(450)
    def switch_off(p):
        go()(p); p.evaluate("document.querySelector('#send-message').checked=false"); p.wait_for_timeout(350)
    def closed_inputs(p):
        go()(p); p.evaluate("document.querySelector('.demo-inputs').open=false"); p.wait_for_timeout(50)
    return {
      "home": go(), "home_inputs_closed": closed_inputs, "completed": go(f"?run={ids['completed']}"), "completed_expanded": open_all(f"?run={ids['completed']}"),
      "waiting_approval": go(f"?run={ids['waiting']}"), "rejected": go(f"?run={ids['rejected']}"), "failed": go(f"?run={ids['failed']}"), "failed_expanded": open_all(f"?run={ids['failed']}"),
      "hover_run_card": hover(".run-card"), "hover_submit": hover("#run-form button"), "hover_refresh": hover("#refresh"), "hover_approve": hover("[data-approve='true']", f"?run={ids['waiting']}"), "hover_reject": hover("[data-approve='false']", f"?run={ids['waiting']}"),
      "focus_objective": focus("#objective"), "focus_sources": focus("#sources"), "focus_expression": focus("#expression"), "focus_recipient": focus("#recipient"), "toast": toast, "switch_off": switch_off,
    }

def capture(ctx, variant, ids, shots):
    variant = Path(variant); page = ctx.new_page(); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    def handler(route):
        from urllib.parse import urlparse
        path = urlparse(route.request.url).path
        name = {"/": "index.html", "/static/styles.css": "styles.css", "/static/app.js": "app.js"}.get(path)
        if name:
            route.fulfill(body=(variant / name).read_text(), content_type={"html": "text/html", "css": "text/css", "js": "application/javascript"}[name.rsplit(".",1)[1]])
        else:
            route.continue_()
    page.route("**/*", handler)
    out = {}
    for name, action in scenarios(ids).items():
        action(page)
        path = shots / f"{name}.png"; page.screenshot(path=str(path), full_page=True)
        out[name] = page.evaluate(DUMP)
    page.close()
    return out, errors

def main():
    tmp = Path(tempfile.mkdtemp()); db = str(tmp / "v.db"); outbox = str(tmp / "o")
    ids = seed(db, outbox)
    env = dict(os.environ, AI_WORKFORCE_DB=db, AI_WORKFORCE_OUTBOX=outbox, AI_WORKFORCE_PROVIDER="demo")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "ai_workforce.app:app", "--port", str(PORT), "--log-level", "error"], env=env)
    report = {"scenarios": 0, "elements_compared": 0, "properties_compared": 0, "style_differences": 0, "pixel_differences": 0, "element_count_mismatches": 0, "console_errors": [], "details": []}
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health"); break
            except Exception: time.sleep(.2)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            report["browser"] = browser.version
            for w, h in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": h}, timezone_id="UTC", locale="en-US", reduced_motion="no-preference")
                sa = OUT / f"{w}" / "a"; sb = OUT / f"{w}" / "b"; sa.mkdir(parents=True, exist_ok=True); sb.mkdir(parents=True, exist_ok=True)
                ra, ea = capture(ctx, A, ids, sa); rb, eb = capture(ctx, B, ids, sb); ctx.close()
                report["console_errors"] += ea + eb
                for name in ra:
                    report["scenarios"] += 1
                    x, y = ra[name], rb[name]
                    if len(x) != len(y):
                        report["element_count_mismatches"] += 1; report["details"].append({"vw": w, "scenario": name, "elements": [len(x), len(y)]}); continue
                    for ex, ey in zip(x, y):
                        report["elements_compared"] += 1
                        if ex["rect"] != ey["rect"]:
                            report["style_differences"] += 1
                            if len(report["details"]) < 40: report["details"].append({"vw": w, "scenario": name, "el": ex["tag"]+"."+ex["cls"], "rect": [ex["rect"], ey["rect"]]})
                        for part in ("self", "before", "after"):
                            for prop in set(ex[part]) | set(ey[part]):
                                report["properties_compared"] += 1
                                if ex[part].get(prop) != ey[part].get(prop):
                                    report["style_differences"] += 1
                                    if len(report["details"]) < 40: report["details"].append({"vw": w, "scenario": name, "el": ex["tag"]+"."+str(ex["cls"]), "part": part, "prop": prop, "a": ex[part].get(prop), "b": ey[part].get(prop)})
                    ia = Image.open(sa / f"{name}.png").convert("RGB"); ib = Image.open(sb / f"{name}.png").convert("RGB")
                    if ia.size != ib.size or ImageChops.difference(ia, ib).getbbox():
                        report["pixel_differences"] += 1; report["details"].append({"vw": w, "scenario": name, "pixels": "differ", "bbox": None if ia.size != ib.size else ImageChops.difference(ia, ib).getbbox(), "sizes": [ia.size, ib.size]})
            browser.close()
    finally:
        server.terminate(); server.wait()
    report["console_errors"] = sorted(set(report["console_errors"]))
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, indent=1)); print("first details:", json.dumps(report["details"][:6], indent=0)[:1500])
main()
