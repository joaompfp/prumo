"""Additional read-only asset and native-day control checks on the isolated candidate."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "browser")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "static/js/prumo-charts.manifest.json").read_text())
    checks = []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        assert condition, name

    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            executable_path="/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",
            args=["--no-sandbox"])
        for javascript in (False, True):
            context = browser.new_context(java_script_enabled=javascript, viewport={"width": 390, "height": 844})
            page = context.new_page()
            for prefix in ("", "/dados"):
                label = f"{prefix}-js{javascript}"
                response = page.goto(args.origin + prefix + "/series/eredes.production_total.PT")
                check(label + "-200", response.status == 200)
                page.get_by_role("link", name="Intervalo e ações", exact=True).click()
                select = page.locator("select[name=dia]")
                check(label + "-day-visible", select.is_visible())
                check(label + "-native-get", page.locator(".chart-day-form").get_attribute("method") == "get")
                days = select.locator("option").evaluate_all("items => items.map(el => el.value)")
                chosen = days[-1]
                select.select_option(chosen)
                page.locator(".chart-day-form button").click()
                check(label + "-selected-day-address", parse_qs(urlparse(page.url).query)["dia"] == [chosen])
                check(label + "-prefix-preserved", urlparse(page.url).path == prefix + "/series/eredes.production_total.PT")
                if javascript:
                    page.wait_for_selector(".chart-enhanced")
                    asset = page.locator("script[src]").get_attribute("src")
                    body = context.request.get(args.origin + asset).body()
                    check(label + "-exact-served-asset", hashlib.sha256(body).hexdigest() == manifest["sha256"])
            context.close()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.goto(args.origin + "/dados/comparar/taxas-juro-credito-depositos")
        page.wait_for_selector(".chart-enhanced")
        page.locator(".chart-range").focus()
        page.keyboard.press("End")
        page.locator(".chart-controls").screenshot(path=str(args.output / "structured-inspector-1440.png"))
        browser.close()
    (args.output / "native-controls.json").write_text(json.dumps({"checks": checks}, indent=2) + "\n")
    print(json.dumps({"passed": len(checks)}))


if __name__ == "__main__":
    main()
