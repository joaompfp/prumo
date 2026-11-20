"""Installed public-prefix browser smoke; no database or CMS writes."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from tests.app.test_chart_layout import _chromium  # noqa: E402

CASES = {
    "native": "/caderno?s=ine.hicp_yoy.PT&s=worldbank.gdp_per_capita.PT&escala=dupla",
    "annual": "/caderno?s=ine.hicp_yoy.PT&s=eurostat.gdp_per_capita_eur.PT&escala=dupla&frequencia=anual",
    "base100": "/caderno?s=eurostat.gdp_per_capita_eur.PT&s=eurostat.gdp_per_capita_eur.ES&frequencia=anual&transformacao=base100&base=2015",
    "pp": "/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT&frequencia=anual&transformacao=pp&base=2015",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", action="append")
    args = parser.parse_args()
    bases = args.base or ["https://cae.joao.date", "https://joao.date/dados"]
    manifest = json.loads(Path("static/js/prumo-charts.manifest.json").read_text())
    checks, pages, warnings = [], [], []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        assert condition, name

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=_chromium(), headless=True,
                                             args=["--no-sandbox"])
        try:
            for base in bases:
                origin = urlsplit(base).netloc
                health = requests.get(base + "/healthz", timeout=30)
                check(base + " health", health.status_code == 200 and health.json()["status"] == "ok")
                asset = requests.get(base + "/static/" + manifest["asset"],
                                     headers={"Accept-Encoding": "gzip"}, stream=True, timeout=30)
                wire = asset.raw.read(decode_content=False)
                decoded = gzip.decompress(wire) if asset.headers.get("content-encoding") == "gzip" else wire
                check(base + " compiled bytes", asset.status_code == 200
                      and hashlib.sha256(decoded).hexdigest() == manifest["sha256"])
                pages.append({"base": base, "asset_wire_bytes": len(wire),
                              "asset_decoded_bytes": len(decoded),
                              "encoding": asset.headers.get("content-encoding")})
                for width in (390, 1440):
                    context = browser.new_context(viewport={"width": width, "height": 1000},
                                                  has_touch=width == 390)
                    page = context.new_page()
                    errors, outside = [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("console", lambda msg: (errors.append(msg.text) if msg.type == "error"
                                                     else warnings.append(msg.text) if msg.type == "warning" else None))
                    page.on("request", lambda req: outside.append(req.url)
                            if urlsplit(req.url).netloc not in (origin, "") else None)
                    for name, path in CASES.items():
                        response = page.goto(base + path, wait_until="networkidle", timeout=45000)
                        check(f"{base} {width} {name} status", response is not None and response.status == 200)
                        page.evaluate("document.fonts.ready")
                        expect(page.locator(".chart-shell")).to_have_class(__import__("re").compile("chart-enhanced"))
                        payload_text = page.locator("script.chart-data").text_content()
                        assert payload_text is not None
                        payload = json.loads(payload_text)
                        check(name + " version", payload["version"] == (2 if name == "native" else 1))
                        check(name + " full table", page.locator(".notebook-table-scroll > table > tbody > tr").count() == len(payload["x"]))
                        for key, index in (("Home", 0), ("End", len(payload["x"]) - 1)):
                            page.locator(".chart-range").focus()
                            page.keyboard.press(key)
                            expect(page.locator(".chart-readout")).to_contain_text(payload["periods"][index])
                            lines = ([payload["series"][0]["badge"]] if payload["series"][0]["badge"] else [])
                            lines.append(payload["periods"][index])
                            for side, entry in enumerate(payload["series"]):
                                value = payload["display"][index][side]
                                if payload["version"] == 2:
                                    cell = (payload["cell_periods"][index][side] + ": " + value
                                            if value is not None else payload["missing"])
                                    lines.append(entry["title"] + " - " + cell)
                                else:
                                    lines.append(entry["title"] + ": " + value)
                            expect(page.locator(".chart-tip-line")).to_have_text(lines, timeout=5000)
                            check(name + " " + key + " exact tooltip", True)
                        check(name + " overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                        if name == "base100":
                            expect(page.locator(".notebook-chart-sources")).to_contain_text("Unidade do gráfico: índice (base 2015=100)")
                            expect(page.locator(".notebook-chart-sources")).to_contain_text("Unidade da fonte: euros por habitante")
                        if name == "annual":
                            expect(page.locator(".notebook-analysis-note")).to_contain_text("não é a taxa de inflação anual oficial")
                        pages.append({"base": base, "width": width, "case": name,
                                      "rows": len(payload["x"]), "version": payload["version"]})
                        if name == "native":
                            page.mouse.move(1, 1)
                            page.evaluate("scrollTo(0,0)")
                            args.output.parent.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(args.output.parent / f"installed-{origin.split('.')[0]}-{width}.png"))
                    check("browser errors absent", not errors)
                    check("no external requests", not outside)
                    context.close()
                method = requests.get(base + "/metodologia", timeout=30)
                check(base + " methodology", method.status_code == 200 and "Comparação temporal no Caderno" in method.text)
                check(base + " no em dashes", chr(0x2014) not in method.text)
                check(base + " unknown series", requests.get(base + "/series/does-not-exist", timeout=30).status_code == 404)
            admin = requests.get("https://joao.date/dados/admin/cms", allow_redirects=False, timeout=30)
            check("Admin challenges through Authelia", admin.status_code in (301, 302, 303, 307, 308)
                  and "authelia.joao.date" in admin.headers.get("location", ""))
        finally:
            browser.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"checks": checks, "pages": pages, "warnings": warnings,
                                      "bundle_sha256": manifest["sha256"]}, ensure_ascii=False, indent=2))
    print(json.dumps({"passed": len(checks), "pages": len(pages), "warnings": len(warnings)}))


if __name__ == "__main__":
    main()
