"""Grouped two-axis payload v1: the committed adapter must use the declared axes.

This is a synthetic offline page: the server model renders the same shell the templates use, the
committed bundle is served same-origin under a production-shaped CSP, and no application route
or second data request is involved. Values are chosen so a series drawn on the wrong axis falls
outside its fixed min/max and is clipped: the painted colours then prove the adapter consumed
`series[].axis` instead of inferring a scale from the series position.
"""
import json
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.chart_model import group_model
from app.charts import chart_legend, chart_plot
from app.interactive import build_payload
from tests.app.test_chart_layout import _chromium

ROOT = Path(__file__).parents[2]
BUNDLE = ROOT / "static" / "js" / "prumo-charts.min.js"
CSP = ("default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; "
       "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
LABELS = ("Nível", "Taxa A", "Taxa B")
UNITS = ("milhões de euros", "%", "%")
AXES = (0, 1, 1)
ROWS = [{"period": "2024-S1", "values": ["100000", "1.0", "2.0"]},
        {"period": "2024-S2", "values": ["101000", "1.5", "3.0"]},
        {"period": "2025-S1", "values": ["102500", "2.0", "2.5"]},
        {"period": "2025-S2", "values": ["103000", "2.5", "3.5"]},
        {"period": "2026-S1", "values": ["104000", "3.0", "4.0"]},
        {"period": "2026-S2", "values": ["105000", "3.5", "4.5"]}]


def grouped_model():
    return group_model(ROWS, frequency="S", title="Prova agrupada", labels=LABELS,
                       units=UNITS, axes=AXES)


def page_html(model, payload):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    plot = str(chart_plot(model))
    legend = str(chart_legend(model))
    last = len(payload["periods"]) - 1
    return f"""<!doctype html>
<html lang="pt-PT"><head><meta charset="utf-8">
<link rel="icon" href="data:,">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prova agrupada</title>
<style>
:root {{
  --ink: #1a1a1a; --red: #c0392b; --muted: #524d48; --rule: #e2ded9;
  --sans: "Lato", system-ui, sans-serif; --accent: #9b1c2e;
  --chart-series-2: #2f5d8a; --chart-series-3: #8a5a00; --chart-series-4: #2e7d32;
  --chart-series-5: #6b3fa0; --chart-series-6: #0b6b6b;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: var(--sans); background: #faf8f5; color: var(--ink); }}
.chart-shell {{ width: min(880px, 100%); }}
.chart-wrap {{ position: relative; width: 100%; height: 340px; }}
.chart-wrap .chart {{ width: 100%; height: 100%; }}
.chart-canvas {{ position: absolute; inset: 0; opacity: 0; pointer-events: none; }}
.chart-enhanced .chart-canvas {{ opacity: 1; pointer-events: auto; }}
.chart-enhanced .chart {{ opacity: 0; pointer-events: none; }}
.chart-controls {{ width: 100%; }}
.chart-range {{ width: 100%; }}
.chart-tooltip {{ font-size: 19.8px; line-height: 29.7px; }}
.sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }}
</style></head><body>
<div class="chart-shell" data-chart>
  <div class="chart-scroll"><div class="chart-wrap">
    {plot}
    <div class="chart-canvas" aria-hidden="true"></div>
  </div></div>{legend}
  <div class="chart-controls">
    <label class="sr-only" for="chart-range-probe">Período no gráfico</label>
    <input class="chart-range" id="chart-range-probe" type="range" min="0" max="{last}"
      step="1" value="{last}" aria-valuetext="{payload['periods'][-1]}" hidden>
    <output class="chart-readout" for="chart-range-probe"></output>
    <span class="sr-only chart-live" aria-live="polite"></span>
  </div>
  <p class="chart-hint" hidden>Use as setas, Início e Fim.</p>
  <script type="application/json" class="chart-data">{data}</script>
</div>
<script src="/static/js/prumo-charts.min.js"></script>
</body></html>"""


class _Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        super().end_headers()

    def log_message(self, format, *args):  # keep the test quiet
        pass


@pytest.fixture(scope="module")
def grouped_site(tmp_path_factory):
    root = tmp_path_factory.mktemp("group-probe")
    (root / "static" / "js").mkdir(parents=True)
    shutil.copy2(BUNDLE, root / "static" / "js" / "prumo-charts.min.js")
    model = grouped_model()
    assert model is not None
    payload = build_payload(model)
    assert payload is not None
    (root / "valid.html").write_text(page_html(model, payload), encoding="utf-8")

    def invalid(name, mutate):
        copy = json.loads(json.dumps(payload))
        mutate(copy)
        (root / f"{name}.html").write_text(page_html(model, copy), encoding="utf-8")

    invalid("empty-axis", lambda data: [entry.__setitem__("axis", 0)
                                        for entry in data["series"]])
    invalid("missing-axis", lambda data: data["series"][1].pop("axis"))
    invalid("bad-axis", lambda data: data["series"][2].__setitem__("axis", 2))

    handler = partial(_Handler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    executable = _chromium()
    options = {"headless": True, "args": ["--no-sandbox"]}
    if executable:
        options["executable_path"] = executable
    try:
        playwright = sync_api.sync_playwright().start()
        engine = playwright.chromium.launch(**options)
    except Exception as exc:  # Playwright installed without a usable browser
        pytest.skip(f"Chromium unavailable: {exc}")
    try:
        yield engine
    finally:
        engine.close()
        playwright.stop()


SCAN = """() => {
  const stage = document.querySelector('.chart-canvas');
  const canvas = stage.querySelector('canvas');
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  function count(test) {
    let total = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (test(data[i], data[i + 1], data[i + 2], data[i + 3])) total += 1;
    }
    return total;
  }
  return {
    dpr: window.devicePixelRatio,
    accent: count((r, g, b, a) => a > 128 && r >= 130 && r <= 180 && g < 60 && b < 75),
    blue: count((r, g, b, a) => a > 128 && r < 80 && g > 70 && g < 120 && b > 110),
    brown: count((r, g, b, a) => a > 128 && r > 110 && r < 165 && g > 65 && g < 115 && b < 45),
  };
}"""


def _payload(page):
    return json.loads(page.evaluate(
        "() => document.querySelector('script.chart-data').textContent"))


# The core interaction tests locate the drawn series by saturated pixels: axis text, grid rules
# and the background stay low-saturation, so this span is the first and last plotted symbol.
INK = """() => {
  const stage = document.querySelector('.chart-canvas');
  const canvas = stage.querySelector('canvas');
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let min = null, max = null;
  for (let x = 0; x < canvas.width; x += 1) {
    for (let y = 0; y < canvas.height; y += 1) {
      const i = (y * canvas.width + x) * 4;
      const r = data[i], g = data[i + 1], b = data[i + 2];
      if (data[i + 3] > 128 && Math.max(r, g, b) - Math.min(r, g, b) > 30) {
        if (min === null) min = x;
        max = x;
        break;
      }
    }
  }
  const rect = stage.getBoundingClientRect();
  return {dpr: window.devicePixelRatio, min: min, max: max,
          box: {left: rect.left, top: rect.top,
                width: rect.width, height: rect.height}};
}"""


def _tip_lines(page):
    return page.eval_on_selector_all(
        ".chart-tip-line", "els => els.map(el => el.textContent)")


def _tip_rows(payload, index):
    return [payload["periods"][index]] + [
        payload["series"][side]["title"] + ": " + payload["display"][index][side]
        for side in range(len(payload["series"]))]


@pytest.mark.parametrize("width", [390, 1440])
def test_pointer_tooltip_matches_the_selected_row_at_first_mid_and_last(
        grouped_site, browser, width):
    context = browser.new_context(viewport={"width": width, "height": 900},
                                  device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        page.goto(grouped_site + "/valid.html", wait_until="networkidle")
        page.wait_for_selector(".chart-enhanced canvas", timeout=10000)
        page.wait_for_timeout(120)
        payload = _payload(page)
        ink = page.evaluate(INK)
        assert ink["dpr"] == 1
        assert ink["min"] is not None and ink["max"] - ink["min"] > 100, ink
        box = ink["box"]
        last = len(payload["periods"]) - 1
        moves = [("first", ink["min"] + 1, 0),
                 ("mid", (ink["min"] + ink["max"]) / 2, None),
                 ("last", ink["max"] - 1, last)]
        for name, x, expected in moves:
            page.mouse.move(box["left"] + x, box["top"] + box["height"] / 2)
            page.locator(".chart-tooltip .chart-tip-line").first.wait_for(
                state="visible", timeout=5000)
            page.wait_for_timeout(240)
            index = int(page.locator(".chart-range").input_value())
            if expected is None:
                assert abs(index - last / 2) <= 1, (width, name, index)
            else:
                assert index == expected, (width, name, index)
            rows = _tip_rows(payload, index)
            assert _tip_lines(page) == rows, (width, name, index, rows)
        assert not errors
    finally:
        context.close()


def test_grouped_payload_carries_explicit_axes_and_names_every_side(grouped_site, browser):
    context = browser.new_context(viewport={"width": 900, "height": 700},
                                  device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        page.goto(grouped_site + "/valid.html", wait_until="networkidle")
        page.wait_for_selector(".chart-enhanced canvas", timeout=10000)
        page.wait_for_timeout(120)
        payload = _payload(page)
        assert payload["kind"] == "group"
        assert [axis["unit"] for axis in payload["axes"]] == list(UNITS[:2])
        assert [entry["axis"] for entry in payload["series"]] == list(AXES)

        # Both later series are painted only if they use the right axis: their 1-3% values are
        # far outside the left axis' 99 750-101 250 domain and would be clipped there.
        scan = page.evaluate(SCAN)
        assert scan["dpr"] == 1
        assert scan["accent"] > 0 and scan["blue"] > 0 and scan["brown"] > 0, scan

        labels = page.locator("svg.chart").get_attribute("aria-label")
        for label, unit in zip(LABELS, UNITS):
            assert label in labels and unit in labels
        legend = page.locator(".legend li").all_text_contents()
        assert len(legend) == 3
        assert "Eixo esquerdo" in legend[0]
        assert "Eixo direito" in legend[1] and "Eixo direito" in legend[2]

        from playwright.sync_api import expect

        page.locator(".chart-range").focus()
        page.keyboard.press("End")
        last_rows = [payload["periods"][-1]] + [
            payload["series"][index]["title"] + ": " + payload["display"][-1][index]
            for index in range(3)]
        expect(page.locator(".chart-readout")).to_have_text(
            last_rows[0] + " - " + "; ".join(last_rows[1:]), timeout=3000)

        # The tooltip lists every series of the union row with its exact prepared value.
        box = page.locator(".chart-canvas").bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.locator(".chart-tooltip .chart-tip-line").first.wait_for(state="visible",
                                                                      timeout=5000)
        index = page.evaluate("() => Number(document.querySelector('.chart-range').value)")
        expected_rows = [payload["periods"][index]] + [
            payload["series"][side]["title"] + ": " + payload["display"][index][side]
            for side in range(3)]
        expect(page.locator(".chart-tip-line")).to_have_count(4, timeout=3000)
        for row, line in enumerate(expected_rows):
            expect(page.locator(".chart-tip-line").nth(row)).to_have_text(line, timeout=3000)
        assert not errors
    finally:
        context.close()


@pytest.mark.parametrize("name", ["empty-axis", "missing-axis", "bad-axis"])
def test_grouped_payload_without_a_valid_axis_membership_keeps_the_svg(grouped_site, browser,
                                                                      name):
    context = browser.new_context(viewport={"width": 900, "height": 700},
                                  device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        page.goto(grouped_site + f"/{name}.html", wait_until="networkidle")
        page.wait_for_timeout(120)
        assert page.evaluate("() => document.querySelectorAll('canvas').length") == 0
        assert page.evaluate(
            "() => document.querySelector('.chart-shell').classList.contains('chart-enhanced')"
        ) is False
        assert page.locator("svg.chart").is_visible()
        assert page.locator(".chart-readout").text_content() == ""
        assert not errors
    finally:
        context.close()
