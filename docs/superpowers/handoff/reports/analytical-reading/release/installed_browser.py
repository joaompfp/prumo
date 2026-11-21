"""Read-only phase B acceptance on the actual public addresses."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.sync_api import expect, sync_playwright

SLUGS = {
    "inflacao-e-desemprego": 2, "euribor-e-inflacao": 2, "credito-e-taxa": 2,
    "taxas-juro-credito-depositos": 4, "divida-saldo-pib-per-capita": 3,
    "comercio-externo-pib-per-capita": 3, "eletricidade-domestica": 5,
    "pib-por-habitante": 5, "divida-publica": 5,
}
ROUTES = {
    "series": "/series/ine.hicp_yoy.PT",
    "interval": "/series/eredes.production_total.PT",
    "derived": "/calculadas/derived.credit_housing.PT.yoy_change_pct",
    "notebook": "/caderno?s=ine.hicp_yoy.PT&s=worldbank.gdp_per_capita.PT&escala=dupla",
    **{slug: "/comparar/" + slug for slug in SLUGS},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks, errors, warnings, requests, measurements = [], [], [], [], []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        assert condition, name

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(
                executable_path="/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",
                args=["--no-sandbox"])
            for origin in ("https://cae.joao.date", "https://joao.date/dados"):
                for width, height in ((320, 844), (390, 844), (1440, 1000), (1920, 1080)):
                    context = browser.new_context(viewport={"width": width, "height": height})
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("console", lambda message: warnings.append(message.text)
                            if message.type in ("warning", "error") else None)
                    page.on("request", lambda request: requests.append(request.url))
                    response = page.goto(origin + "/comparar")
                    label = f"{origin}-{width}"
                    check(label + "-directory-200", response.status == 200)
                    check(label + "-nine-real-documents", page.locator(".compare-link").count() == len(SLUGS))
                    check(label + "-directory-script-free", page.locator("script").count() == 0)
                    for name, route in ROUTES.items():
                        label = f"{origin}-{width}-{name}"
                        response = page.goto(origin + route)
                        check(label + "-200", response.status == 200)
                        page.evaluate("document.fonts.ready")
                        page.wait_for_selector(".chart-enhanced canvas")
                        data = json.loads(page.locator(".chart-data").first.text_content())
                        check(label + "-no-overflow", page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"))
                        check(label + "-structured-rows", page.locator(".chart-readout-row").count() == len(data["series"]))
                        check(label + "-preserved-reading-scale", page.locator(".chart-readout").first.evaluate(
                            "el => parseFloat(getComputedStyle(el).fontSize)") >= 25)
                        check(label + "-silent-pointer-region", page.locator(".chart-readout").first.get_attribute("aria-live") == "off")
                        slider = page.locator(".chart-range").first
                        if len(data["periods"]) > 1:
                            check(label + "-48px-target", slider.bounding_box()["height"] >= 48)
                            for key, index in (("Home", 0), ("End", -1)):
                                slider.focus()
                                slider.press(key)
                                expect(page.locator(".chart-readout-period").first).to_have_text(data["periods"][index])
                                values = [value if value is not None else data["missing"] for value in data["display"][index]]
                                expect(page.locator(".chart-readout-value")).to_have_text(values)
                                check(label + "-" + key + "-exact-point", True)
                        if name != "notebook":
                            check(label + "-no-public-composition", page.locator(
                                "main select[name^=series_], main select[name^=axis_], main select[name=escala], main .notebook-chart-form").count() == 0)
                        if name in SLUGS:
                            check(label + "-all-authored-series", len(data["series"]) == SLUGS[name])
                            check(label + "-complete-table", page.locator(".notebook-table-scroll tbody tr").count() == len(data["x"]))
                        if name in ("series", "interval"):
                            check(label + "-nearby-interval-shortcut", page.locator('a[href="#opcoes-serie"]').count() == 1)
                        page.locator("h1").click()
                        page.locator(".chart-canvas").first.scroll_into_view_if_needed()
                        canvas = page.locator(".chart-canvas").first.bounding_box()
                        page.mouse.move(canvas["x"] + 2, canvas["y"] + 2)
                        page.mouse.move(0, 0)
                        expect(page.locator(".chart-tip-line").first).to_be_hidden()
                        page.evaluate("window.scrollTo(0,0)")
                        check(label + "-neutral-top", page.evaluate("scrollY") == 0)
                        plot = page.locator(".chart-wrap").first.bounding_box()
                        check(label + "-useful-plot-height", plot["height"] >= 250)
                        measurements.append({"origin": origin, "width": width, "route": name, "plot": plot})
                        if width >= 1440 and name in ("series", "interval", "derived", "taxas-juro-credito-depositos", "eletricidade-domestica"):
                            check(label + "-whole-plot-first-view", plot["y"] + plot["height"] <= height)
                        if origin.endswith("/dados") and width in (390, 1440) and name in ("series", "taxas-juro-credito-depositos"):
                            page.screenshot(path=str(args.output / f"{name}-{width}.png"))
                        if width == 390 and name in ("series", "derived", "taxas-juro-credito-depositos"):
                            page.emulate_media(media="print")
                            check(label + "-print-svg", page.locator("svg.chart").first.evaluate(
                                "el => getComputedStyle(el).opacity") == "1")
                            check(label + "-print-table", page.locator(".table-details tbody").first.bounding_box()["height"] > 0)
                            check(label + "-print-no-controls", page.locator(".chart-controls").first.evaluate(
                                "el => getComputedStyle(el).display") == "none")
                            page.emulate_media(media="screen")
                    context.close()
                nojs = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
                plain = nojs.new_page()
                for name in ("series", "derived", "taxas-juro-credito-depositos"):
                    plain.goto(origin + ROUTES[name])
                    check(origin + name + "-nojs-svg", plain.locator("svg.chart").first.is_visible())
                    check(origin + name + "-nojs-no-canvas", plain.locator("canvas").count() == 0)
                nojs.close()
                blocked = browser.new_context()
                blocked.route("**/static/js/prumo-charts*", lambda route: route.abort())
                plain = blocked.new_page()
                plain.goto(origin + ROUTES["taxas-juro-credito-depositos"])
                check(origin + "-blocked-bundle-svg", plain.locator("svg.chart").first.evaluate(
                    "el => getComputedStyle(el).opacity") == "1")
                blocked.close()
            browser.close()
        check("no-application-errors", not errors)
        check("no-new-console-errors", not [warning for warning in warnings if "vr" not in warning])
        check("no-off-origin-requests", all(urlparse(url).netloc in {"cae.joao.date", "joao.date"}
              for url in requests if url.startswith("http")))
        with httpx.Client(follow_redirects=False, timeout=40) as client:
            response = client.get("https://joao.date/dados/admin/cms")
            check("anonymous-admin-authelia", response.status_code in (301, 302, 303, 307)
                  and "authelia.joao.date" in response.headers.get("location", ""))
            for origin in ("https://cae.joao.date", "https://joao.date/dados"):
                response = client.get(origin + "/series/ine.hicp_yoy.PT")
                from html.parser import HTMLParser

                class Scripts(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.srcs = []
                    def handle_starttag(self, tag, attrs):
                        attrs = dict(attrs)
                        if tag == "script" and attrs.get("src"):
                            self.srcs.append(attrs["src"])

                doc = Scripts()
                doc.feed(response.text)
                check(origin + "-one-local-engine", len(doc.srcs) == 1)
                src = doc.srcs[0]
                asset = client.get("https://" + urlparse(origin).netloc + src)
                local = (args.source / "static/js/prumo-charts.min.js").read_bytes()
                check(origin + "-installed-exact-bundle", asset.status_code == 200 and asset.content == local)
                css = client.get(origin + "/static/css/chart-inspector.css")
                check(origin + "-installed-inspector-css", css.status_code == 200
                      and css.content == (args.source / "static/css/chart-inspector.css").read_bytes())
                check(origin + "-strict-csp", "script-src 'self'" in response.headers.get("content-security-policy", ""))
                for route in ("/series/ine.hicp_yoy.PT.csv", "/calculadas/derived.credit_housing.PT.yoy_change_pct.csv"):
                    result = client.get(origin + route)
                    check(origin + route + "-csv", result.status_code == 200 and "text/csv" in result.headers.get("content-type", ""))
                check(origin + "-health", client.get(origin + "/healthz").status_code == 200)
                check(origin + "-unknown-404", client.get(origin + "/comparar/unknown-phase-b-document").status_code == 404)
    finally:
        result = {"passed": sum(item["passed"] for item in checks), "checks": checks,
                  "errors": errors, "warnings": warnings, "measurements": measurements,
                  "bundle_sha256": hashlib.sha256((args.source / "static/js/prumo-charts.min.js").read_bytes()).hexdigest()}
        (args.output / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"passed": result["passed"], "checks": len(checks), "cases": len(measurements),
                          "application_errors": errors, "shared_edge_vr_warnings": len(warnings),
                          "receipt": str(args.output / "browser.json")}))


if __name__ == "__main__":
    main()
