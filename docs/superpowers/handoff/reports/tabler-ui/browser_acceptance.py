"""Browser and protected-data acceptance of the Tabler presentation release.

Run only against qa_server.py with an isolated database in Hermes scratch.
"""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(os.environ.get("PRUMO_QA_OUT", Path(__file__).resolve().parent / "browser"))
OUT.mkdir(parents=True, exist_ok=True)
DB = Path(os.environ["PRUMO_QA_DB"]).resolve(strict=True)
if not DB.is_relative_to(Path("/home/joao/.hermes/cache/scratch")):
    raise ValueError("Refusing a database outside scratch")
BASE = os.environ.get("PRUMO_QA_URL", "http://127.0.0.1:8117")
ADMIN = BASE + "/dados/admin"
report: dict[str, Any] = {"checks": [], "errors": [], "external": [], "console_warnings": []}


def fingerprint():
    result = {}
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'cms_%' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for table in tables:
            h, count = hashlib.sha256(), 0
            for row in db.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                h.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode())
                h.update(b"\n")
                count += 1
            result[table] = {"rows": count, "sha256": h.hexdigest()}
    return result


def check(name, condition):
    report["checks"].append({"check": name, "passed": bool(condition)})
    if not condition:
        (OUT / "acceptance-failure.json").write_text(json.dumps(report, indent=2))
        raise AssertionError(name)


report["protected_before"] = fingerprint()
with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as db:
    original_published = db.execute("SELECT published_revision_id FROM cms_document WHERE kind='page' AND slug='inicio'").fetchone()[0]

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome", args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light")
    context.on("request", lambda r: report["external"].append(r.url) if not r.url.startswith(BASE) else None)
    page = context.new_page()
    page.on("pageerror", lambda e: report["errors"].append(str(e)))
    page.on("console", lambda m: report["errors"].append(m.text) if m.type == "error" else report["console_warnings"].append(m.text) if m.type == "warning" else None)
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/")
    labels = page.locator(".card-label").all_text_contents()
    values = page.locator(".card-value").all_text_contents()
    check("populated real-data home", len(values) == 12)
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        for width in (320, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            for route, name in [("/", "home"), ("/dados/", "home-mounted"), ("/dados/admin/cms", "dashboard"), ("/dados/admin/cms/page/inicio", "editor")]:
                response = page.goto(BASE + route)
                check(f"{name} {scheme} {width} HTTP200", response is not None and response.status == 200)
                check(f"{name} {scheme} {width} no page overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                check(f"{name} {scheme} {width} no authored punctuation", chr(0x2014) not in page.locator("body").inner_text())
                if name.startswith("home"):
                    check(f"{name} {scheme} {width} exact values", page.locator(".card-value").all_text_contents() == values)
                    check(f"{name} {scheme} {width} script-free", page.locator("script").count() == 0)
                else:
                    check(f"{name} {scheme} {width} pinned stylesheet loaded", page.evaluate("Array.from(document.styleSheets).some(s => s.href && s.href.includes('vendor/tabler/1.7.5') && s.cssRules.length > 100)"))
                    check(f"{name} {scheme} {width} one active nav", page.locator('nav a[aria-current="page"]').count() == 1)
                    check(f"{name} {scheme} {width} controls inside screen", page.locator("nav.nav a, .draft-toolbar").evaluate_all("es => es.length >= 7 && es.every(e => e.getBoundingClientRect().right <= innerWidth + 1)"))
                if width in (390, 1440) and not name.endswith("mounted"):
                    page.screenshot(path=str(OUT / f"{name}-{scheme}-{width}.png"))
    page.emulate_media(color_scheme="light")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(ADMIN + "/cms/page/inicio")
    check("local icon font loaded", page.evaluate("document.fonts.ready.then(() => document.fonts.check('16px PrumoIcons'))"))
    csp = context.request.get(ADMIN + "/cms").headers["content-security-policy"]
    # Measure the actual cascade, including Tabler's important utility text colour.
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        page.goto(ADMIN + "/cms/page/inicio")
        colours = page.locator(".badge.bg-secondary-lt").evaluate_all("""es => {
          const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently:true});
          const rgba = s => { ctx.clearRect(0,0,1,1); ctx.fillStyle=s; ctx.fillRect(0,0,1,1); return Array.from(ctx.getImageData(0,0,1,1).data); };
          const over = (a,b) => a.slice(0,3).map((v,i) => v*a[3]/255+b[i]*(1-a[3]/255));
          return es.map(e => {
            let bg=[255,255,255], ancestors=[], node=e;
            while(node) { ancestors.push(node); node=node.parentElement; }
            ancestors.reverse().forEach(n => { bg=over(rgba(getComputedStyle(n).backgroundColor),bg); });
            return {text:e.textContent.trim(), fg:over(rgba(getComputedStyle(e).color),bg), bg};
          });
        }""")
        def luminance(rgb):
            c = [v / 255 for v in rgb]
            linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
            return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))
        for sample in colours:
            levels = sorted([luminance(sample["fg"]), luminance(sample["bg"])])
            sample["ratio"] = (levels[1] + 0.05) / (levels[0] + 0.05)
        report.setdefault("badge_contrast", {})[scheme] = colours
        check(scheme + " neutral small badges AA", bool(colours) and all(s["ratio"] >= 4.5 for s in colours))
    page.emulate_media(color_scheme="light")
    page.goto(ADMIN + "/cms/page/inicio")
    check("readable publication date", "UTC" in page.locator(".editor-status time").inner_text() and "T" not in page.locator(".editor-status time").inner_text().replace("UTC", ""))
    check("all visible inputs have labels", page.locator("input:not([type=hidden]),select,textarea").evaluate_all("es => es.filter(e=>e.getClientRects().length).every(e=>e.labels.length || e.getAttribute('aria-label'))"))
    page.locator('.editor-jumps a[href="#historico"]').click()
    check("section jump shows current location", page.locator('.editor-jumps a[aria-current="location"]').inner_text() == "Histórico")
    check("admin CSP unchanged strict", "unsafe-inline" not in csp and "unsafe-eval" not in csp and "script-src 'self'" in csp)
    page.goto(ADMIN + "/cms/page/inicio")
    form = page.locator('form[action$="/save"]')
    stale_version = form.locator('input[name="version"]').input_value()
    form.locator('input[name="block_title_0"]').fill("Ensaio privado Tabler")
    submissions = []
    page.on("request", lambda r: submissions.append(r.url) if r.method == "POST" else None)
    page.locator('form[action$="/publish"]').get_by_role("button").click()
    check("dirty publication stopped before POST", not submissions and page.locator(".dirty-note").is_visible())
    form.locator('input[name="note"]').fill("Aceitação local da interface Tabler")
    form.get_by_role("button", name="Guardar rascunho", exact=True).click()
    page.wait_for_load_state("load")
    check("real form saved draft", page.locator('input[name="block_title_0"]').input_value() == "Ensaio privado Tabler")
    check("draft remains private", "Ensaio privado Tabler" not in context.request.get(BASE + "/").text())
    page.goto(ADMIN + "/cms/page/inicio/preview")
    check("static preview has saved content", page.get_by_role("heading", name="Ensaio privado Tabler", exact=True).count() == 1 and page.locator("script[src]").count() == 0)
    page.goto(ADMIN + "/cms/page/inicio")
    publish = page.locator('form[action$="/publish"]')
    publish.locator('input[name="note"]').fill("Aceitação local: publicar composição existente")
    publish.get_by_role("button").click()
    page.wait_for_load_state("load")
    for prefix in ("", "/dados"):
        html = context.request.get(BASE + prefix + "/").text()
        check("publication read back " + prefix, "Ensaio privado Tabler" in html)
    stale = context.request.post(ADMIN + "/cms/page/inicio/publish", form={"version": stale_version, "note": "Conflito esperado"}, headers={"Origin": BASE})
    check("stale publication refuses", stale.status == 409)
    unpublish = page.locator('form[action$="/unpublish"]')
    unpublish.locator('input[name="note"]').fill("Aceitação local: retirar publicação")
    unpublish.get_by_role("button").click()
    page.wait_for_load_state("load")
    check("unpublication read back", "Ensaio privado Tabler" not in context.request.get(BASE + "/").text())
    restore = page.locator('form[action$="/restore"]').filter(has=page.locator(f'input[name="revision_id"][value="{original_published}"]'))
    restore.locator('input[name="note"]').fill("Aceitação local: recuperar versão original")
    restore.get_by_role("button").click()
    page.wait_for_load_state("load")
    publish = page.locator('form[action$="/publish"]')
    publish.locator('input[name="note"]').fill("Aceitação local: repor versão original")
    publish.get_by_role("button").click()
    page.wait_for_load_state("load")
    page.goto(BASE + "/")
    check("restored exact original cards", page.locator(".card-label").all_text_contents() == labels and page.locator(".card-value").all_text_contents() == values)
    # Exact chart interaction is covered again using the shipped bundle, not a mock.
    page.goto(BASE + "/comparar/credito-e-taxa")
    page.locator(".chart-enhanced").wait_for()
    payload = json.loads(page.locator('script[type="application/json"]').inner_text())
    check("two-axis canvas active", len(payload["axes"]) == 2 and page.locator("canvas").count() > 0)
    slider = page.locator('input[type="range"]')
    slider.focus()
    slider.press("Home")
    check("exact first-point keyboard values", all(v in page.locator(".chart-readout").inner_text() for v in payload["display"][0]))
    slider.press("End")
    check("exact last-point keyboard values", all(v in page.locator(".chart-readout").inner_text() for v in payload["display"][-1]))
    page.emulate_media(media="print")
    check("print keeps SVG", page.locator("svg.chart").evaluate("e => getComputedStyle(e).opacity === '1'"))
    page.emulate_media(media="screen", reduced_motion="reduce")
    page.goto(ADMIN + "/cms")
    page.keyboard.press("Tab")
    check("keyboard focus has outline", page.evaluate("getComputedStyle(document.activeElement).outlineStyle !== 'none'"))
    check("reduced motion respected", page.locator(".btn").first.evaluate("e => getComputedStyle(e).transitionDuration.split(',').every(x => parseFloat(x) === 0)"))
    # Blocked icon font remains understandable; no-JS native save still works.
    degraded = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 1000})
    degraded.route("**/*.woff2", lambda r: r.abort())
    p = degraded.new_page()
    p.goto(ADMIN + "/cms/page/inicio")
    form = p.locator('form[action$="/save"]')
    check("no-JS save has visible action text", form.get_by_role("button", name="Guardar rascunho", exact=True).is_visible())
    form.locator('input[name="note"]').fill("Aceitação local sem JavaScript nem ícones")
    form.get_by_role("button", name="Guardar rascunho", exact=True).click()
    p.wait_for_load_state("load")
    check("no-JS actual save accepted", p.locator('input[name="block_title_0"]').input_value() != "Ensaio privado Tabler")
    check("no external browser requests", not report["external"])
    check("no page or CSP errors", not report["errors"])
    browser.close()
report["protected_after"] = fingerprint()
check("all non-CMS fingerprints unchanged", report["protected_before"] == report["protected_after"])
with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as db:
    report["integrity"] = db.execute("PRAGMA quick_check").fetchone()[0]
    report["foreign_keys"] = db.execute("PRAGMA foreign_key_check").fetchall()
check("database integrity and FK", report["integrity"] == "ok" and not report["foreign_keys"])
(OUT / "acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({"checks": len(report["checks"]), "errors": report["errors"], "warnings": report["console_warnings"], "protected_tables": len(report["protected_before"])}))
