"""Exercise real CMS publications and analytical pages on a disposable production copy."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from backoffice.cms import Cms  # noqa: E402
from ingest.db import read_db_readonly  # noqa: E402


def fingerprint(path):
    def read(db):
        tables = {}
        for (name,) in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            if name.startswith("cms_") or name == "sqlite_sequence":
                continue
            digest = hashlib.sha256()
            count = 0
            for row in db.conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
                digest.update(json.dumps(tuple(row), ensure_ascii=False, default=repr).encode())
                digest.update(b"\n")
                count += 1
            tables[name] = {"rows": count, "sha256": digest.hexdigest()}
        schema = [tuple(row) for row in db.conn.execute(
            "SELECT type,name,sql FROM sqlite_master ORDER BY type,name")]
        home = [tuple(row) for row in db.conn.execute(
            "SELECT * FROM cms_document WHERE kind='page' AND slug='inicio'")]
        return {"tables": tables, "schema": hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
                "home": home, "integrity": [tuple(row) for row in db.conn.execute("PRAGMA quick_check")],
                "foreign_keys": [tuple(row) for row in db.conn.execute("PRAGMA foreign_key_check")]}
    return read_db_readonly(path, read)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "browser")
    args = parser.parse_args()
    args.db = args.db.resolve(strict=True)
    if not args.db.is_relative_to(Path("/home/joao/.hermes/cache/scratch")):
        raise ValueError("Only a disposable scratch copy is allowed")
    args.output.mkdir(parents=True, exist_ok=True)
    checks, measurements, errors, requests = [], [], [], []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        assert condition, name

    before = fingerprint(args.db)
    cms = Cms(args.db, args.db)
    # A reusable calculated chart exercises the legacy, non-comparison branch too.
    library_slug = "leitura-calculada-ensaio"
    if cms.get("chart", library_slug) is None:
        body = {"title": "Variação do crédito à habitação em Portugal",
                "note": "Ensaio isolado da apresentação analítica.",
                "series_a": "bportugal.credit_housing.PT",
                "derived_key": "derived.credit_housing.PT.yoy_change_pct",
                "window": "max", "scale": "single"}
        created = cms.create("chart", library_slug, body, actor="acceptance", note="Criar apenas na cópia")
        cms.publish("chart", library_slug, created["version"], actor="acceptance", note="Publicar apenas na cópia")
    slug = "taxas-juro-credito-depositos"
    original = cms.get("chart", slug)
    original_revision = original["meta"]["draft_revision_id"]
    paths = {
        "series": "/series/ine.hicp_yoy.PT",
        "interval": "/series/eredes.production_total.PT",
        "derived": "/calculadas/derived.credit_housing.PT.yoy_change_pct",
        "library": "/graficos/leitura-calculada-ensaio",
        "pair": "/comparar/inflacao-e-desemprego",
        "dual": f"/comparar/{slug}",
        "countries": "/comparar/eletricidade-domestica",
        "notebook": "/caderno?s=ine.hicp_yoy.PT&s=worldbank.gdp_per_capita.PT&escala=dupla",
    }
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(
                executable_path="/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",
                args=["--no-sandbox"])
            context = browser.new_context()
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: requests.append(request.url))
            for prefix in ("", "/dados"):
                for width, height in ((320, 844), (390, 844), (760, 1000), (761, 1000),
                                      (900, 1000), (901, 1000), (1440, 1000), (1920, 1080)):
                    page.set_viewport_size({"width": width, "height": height})
                    for name, path in paths.items():
                        label = f"{prefix}-{width}-{name}"
                        response = page.goto(args.origin + prefix + path)
                        check(label + "-200", response.status == 200)
                        page.evaluate("document.fonts.ready")
                        page.wait_for_selector(".chart-enhanced canvas")
                        check(label + "-no-overflow", page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"))
                        data = json.loads(page.locator(".chart-data").first.text_content())
                        check(label + "-structured-series", page.locator(".chart-readout-row").count() == len(data["series"]))
                        check(label + "-functional-type", page.locator(".chart-readout").first.evaluate(
                            "el => parseFloat(getComputedStyle(el).fontSize)") >= 25)
                        if name != "notebook":
                            check(label + "-no-editorial-controls", page.locator(
                                "main select[name=escala], main select[name=scale], main select[name^=series_], main .notebook-chart-form").count() == 0)
                        slider = page.locator(".chart-range").first
                        if len(data["periods"]) > 1:
                            check(label + "-range-target", slider.bounding_box()["height"] >= 48)
                            for key, point in (("Home", 0), ("End", len(data["periods"]) - 1)):
                                slider.focus()
                                slider.press(key)
                                expect(page.locator(".chart-readout-period").first).to_have_text(data["periods"][point])
                                expected = [value if value is not None else data["missing"] for value in data["display"][point]]
                                expect(page.locator(".chart-readout-value")).to_have_text(expected)
                                check(label + "-" + key + "-exact", True)
                        page.locator("h1").click()
                        page.locator(".chart-canvas").first.scroll_into_view_if_needed()
                        canvas = page.locator(".chart-canvas").first.bounding_box()
                        page.mouse.move(canvas["x"] + 2, canvas["y"] + 2)
                        page.mouse.move(0, 0)
                        expect(page.locator(".chart-tip-line").first).to_be_hidden()
                        page.evaluate("window.scrollTo(0,0)")
                        check(label + "-at-top", page.evaluate("scrollY") == 0)
                        plot = page.locator(".chart-wrap").first.bounding_box()
                        measurements.append({"route": name, "prefix": prefix, "width": width,
                                             "height": height, "plot": plot})
                        if width >= 1440:
                            check(label + "-whole-plot-in-first-view", plot["y"] + plot["height"] <= height)
                        if prefix == "/dados" and width in (390, 1440) and name in ("series", "dual", "countries"):
                            page.screenshot(path=str(args.output / f"{name}-{width}.png"))
            page.set_viewport_size({"width": 1440, "height": 1000})
            editor = args.origin + "/dados/admin/cms/chart/" + slug
            response = page.goto(editor)
            check("admin-real-editor", response.status == 200)
            check("admin-six-slots", page.locator("select[name^=series_]").count() == 6)
            page.on("dialog", lambda dialog: dialog.accept())
            page.locator("input[name=title]").fill("Juros e crédito em Portugal: leitura revista no CMS")
            page.locator("#draft-note").fill("Verificação isolada da autoria CMS após mudança de apresentação")
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/save")) as saved:
                page.get_by_role("button", name="Guardar rascunho", exact=False).click()
            check("admin-save-303", saved.value.status == 303)
            reader = context.new_page()
            reader.goto(args.origin + paths["dual"])
            check("draft-private", reader.locator("h1").inner_text() == original["published"].title)
            preview = context.new_page()
            preview_response = preview.goto(editor + "/preview")
            check("preview-200", preview_response.status == 200)
            check("preview-no-executable-script", preview.locator("script[src]").count() == 0)
            check("preview-svg", preview.locator("svg.chart").count() == 1)
            preview_css = preview.locator('link[href$="chart-inspector.css"]').get_attribute("href")
            check("preview-css-admin-base", preview_css == "/dados/admin/static/css/chart-inspector.css")
            check("preview-css-served", context.request.get(args.origin + preview_css).status == 200)
            script_policy = preview_response.headers.get("content-security-policy", "")
            check("preview-script-refused", "script-src 'none'" in script_policy or
                  ("default-src 'none'" in script_policy and "script-src" not in script_policy))
            page.locator("#publish-note").fill("Publicação de ensaio apenas na cópia isolada")
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/publish")) as published:
                page.get_by_role("button", name="Publicar este rascunho", exact=False).click()
            check("admin-publish-303", published.value.status == 303)
            reader.reload()
            check("published-title-readback", "leitura revista no CMS" in reader.locator("h1").inner_text())
            check("public-remains-unconfigurable", reader.locator("main form").count() == 0)
            for name in ("series", "derived", "library", "dual", "countries"):
                reader.goto(args.origin + "/dados" + paths[name])
                reader.wait_for_selector(".chart-enhanced")
                reader.emulate_media(media="print")
                check(name + "-print-svg", reader.locator("svg.chart").first.evaluate(
                    "el => getComputedStyle(el).opacity") == "1")
                check(name + "-print-no-controls", reader.locator(".chart-controls").evaluate(
                    "el => getComputedStyle(el).display") == "none")
                check(name + "-print-table", reader.locator(".table-details tbody").first.bounding_box()["height"] > 0)
                if name in ("library", "dual", "countries"):
                    check(name + "-print-notes", reader.locator(".authored-note").is_visible())
                reader.emulate_media(media="screen")
            nojs = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
            plain = nojs.new_page()
            for name, path in paths.items():
                plain.goto(args.origin + "/dados" + path)
                check(name + "-nojs-svg", plain.locator("svg.chart").first.is_visible())
                check(name + "-nojs-no-canvas", plain.locator(".chart-canvas canvas").count() == 0)
            blocked_context = browser.new_context()
            blocked_context.route("**/static/js/prumo-charts*", lambda route: route.abort())
            blocked = blocked_context.new_page()
            blocked.goto(args.origin + paths["dual"])
            check("blocked-bundle-svg", blocked.locator("svg.chart").first.evaluate(
                "el => getComputedStyle(el).opacity") == "1")
            check("no-application-errors", not errors)
            check("no-external-requests", all(url.startswith(args.origin + "/") or url.startswith("data:") for url in requests))
            browser.close()
    finally:
        current = cms.get("chart", slug)
        if current["draft"].title != original["draft"].title:
            restored = cms.restore("chart", slug, current["meta"]["version"], original_revision,
                                   actor="acceptance", note="Restaurar rascunho na cópia isolada")
            cms.publish("chart", slug, restored["version"], actor="acceptance", note="Repor publicação original na cópia")
        after = fingerprint(args.db)
        unchanged = before == after
        check("protected-schema-home-unchanged", unchanged)
        result = {"checks": checks, "measurements": measurements, "errors": errors,
                  "before": before, "after": after, "protected_unchanged": unchanged}
        (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": len(checks), "receipt": str(args.output / "result.json")}))


if __name__ == "__main__":
    main()
