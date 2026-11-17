"""Read-only browser smoke of the installed carmim/Tabler presentation release."""
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / "carmim-production"
OUT.mkdir(exist_ok=True)
BASES = ("https://cae.joao.date", "https://joao.date/dados")
report = {"checks": [], "errors": [], "warnings": [], "external": [], "assets": {}}


def check(name, condition):
    report["checks"].append({"check": name, "passed": bool(condition)})
    if not condition:
        (OUT / "failure.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        raise AssertionError(name)


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",
        args=["--no-sandbox"],
    )
    for base in BASES:
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        origin = base.split("/dados")[0]
        context.on("request", lambda request, allowed=origin: report["external"].append(request.url)
                   if not request.url.startswith(allowed + "/") else None)
        page = context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        page.on("console", lambda message: report["errors"].append(message.text)
                if message.type == "error" else report["warnings"].append(message.text)
                if message.type == "warning" else None)
        for width in (320, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            response = page.goto(base + "/")
            check(f"{base} home HTTP200 {width}", response is not None and response.status == 200)
            check(f"{base} carmim highlight {width}", page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()") == "#9b1c2e")
            check(f"{base} warm paper {width}", page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(246, 244, 241)")
            check(f"{base} no overflow {width}", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            check(f"{base} populated homepage {width}", page.locator(".card-value").count() == 12 and page.locator("h1").count() == 1)
            check(f"{base} summaries lightweight {width}", page.locator("script").count() == 0 and "vendor/tabler" not in page.content())
            check(f"{base} authored punctuation {width}", chr(0x2014) not in page.locator("body").inner_text())
            if width in (390, 1440):
                page.screenshot(path=str(OUT / ("home-" + ("mounted" if "/dados" in base else "direct") + f"-{width}.png")))
        for route in ("/healthz", "/comparar", "/fontes", "/metodologia", "/paginas", "/series/ine.hicp_yoy.PT", "/series/ine.hicp_yoy.PT.csv"):
            response = context.request.get(base + route)
            check(base + route + " HTTP200", response.status == 200)
        for asset in ("static/css/prumo.css", "static/images/prumo/favicon.svg", "static/js/prumo-charts.min.js"):
            response = context.request.get(base + "/" + asset)
            data = response.body()
            check(base + "/" + asset + " exact installed bytes", response.status == 200 and data == (ROOT / asset).read_bytes())
            report["assets"][base + "/" + asset] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        page.goto(base + "/comparar/credito-e-taxa")
        page.locator(".chart-enhanced").wait_for()
        payload = json.loads(page.locator('script[type="application/json"]').inner_text())
        check(base + " two-axis interactive chart", len(payload["axes"]) == 2 and page.locator("canvas").count() > 0)
        check(base + " SVG fallback", page.locator("svg.chart").count() == 1)
        slider = page.locator('input[type="range"]')
        slider.focus()
        slider.press("Home")
        check(base + " exact first keyboard values", all(value in page.locator(".chart-readout").inner_text() for value in payload["display"][0]))
        slider.press("End")
        check(base + " exact last keyboard values", all(value in page.locator(".chart-readout").inner_text() for value in payload["display"][-1]))
        page.screenshot(path=str(OUT / ("comparison-" + ("mounted" if "/dados" in base else "direct") + ".png")))
        check(base + " unknown series404", context.request.get(base + "/series/not-a-series").status == 404)
        context.close()
    context = browser.new_context()
    response = context.request.get("https://joao.date/dados/admin/cms/page/inicio", max_redirects=0)
    check("real public Admin Authelia challenge", response.status in (302, 303, 307) and response.headers.get("location", "").startswith("https://authelia.joao.date/"))
    context.close()
    browser.close()
check("no external public asset requests", not report["external"])
check("no page/CSP errors", not report["errors"])
known = [warning for warning in report["warnings"] if "Permissions-Policy" in warning and "vr" in warning]
check("no unexpected console warnings", len(known) == len(report["warnings"]))
report["known_shared_edge_vr_warnings"] = len(known)
(OUT / "public-smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({"checks": len(report["checks"]), "errors": report["errors"], "known_edge_warnings": len(known)}))
