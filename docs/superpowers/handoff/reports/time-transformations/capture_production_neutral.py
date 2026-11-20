"""Capture the installed chart with transient hover UI dismissed, without writes."""
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from production_browser import CASES, _chromium


def main():
    output = Path(__file__).resolve().parent / "production"
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=_chromium(), headless=True, args=["--no-sandbox"]
        )
        try:
            for width in (390, 1440):
                context = browser.new_context(viewport={"width": width, "height": 1000})
                page = context.new_page()
                response = page.goto(
                    "https://joao.date/dados" + CASES["native"],
                    wait_until="networkidle", timeout=45000,
                )
                assert response is not None and response.status == 200
                page.evaluate("document.fonts.ready")
                payload_text = page.locator("script.chart-data").text_content()
                assert payload_text is not None
                payload = json.loads(payload_text)
                assert payload["version"] == 2
                page.locator(".chart-canvas").hover()
                page.mouse.move(1, 1)
                expect(page.locator(".chart-tooltip")).not_to_be_visible()
                page.evaluate("scrollTo(0,0)")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                path = output / f"installed-joao-{width}-neutral.png"
                page.screenshot(path=str(path))
                results.append({
                    "width": width,
                    "tooltip_hidden": True,
                    "no_horizontal_overflow": True,
                    "series_titles": [side["title"] for side in payload["series"]],
                    "screenshot": path.name,
                })
                context.close()
        finally:
            browser.close()
    (output / "neutral-capture.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2)
    )
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
