"""Sparse calendar payload v2: strict adapter contract and local browser probe.

This is deliberately a synthetic, offline page: the server-side model renders the same shell
the templates use, the committed bundle is served same-origin under a production-shaped CSP,
and no application route or second data request is involved. The probe proves the adapter's
v2 behaviour (null side cells, per-side native gaps, union-row readout, touch and keyboard)
before a page integration exists. Full-route acceptance remains the controller's browser gate.
"""
import json
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.calendar_model import calendar_model
from app.calendar_svg import calendar_legend, calendar_plot
from app.interactive import build_payload
from tests.app.test_chart_layout import _chromium

ROOT = Path(__file__).parents[2]
BUNDLE = ROOT / "static" / "js" / "prumo-charts.min.js"
CSP = ("default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; "
       "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

ANNUAL = [{"period": "2023", "value_text": "100"},
          {"period": "2025", "value_text": "110"}]
QUARTERLY = [{"period": "2023-Q1", "value_text": "1.0"},
             {"period": "2024-Q1", "value_text": "1.2"},
             {"period": "2025-Q1", "value_text": "1.4"}]
MONTHLY = [{"period": "2024-01", "value_text": "2.0"},
           {"period": "2024-02", "value_text": "2.1"}]
EXPECTED_ROWS = [
    ["01/01/2023", "Anual - 2023: 100 %", "Trimestral - 1.º trimestre de 2023: 1 %",
     "Mensal - sem observação nesta posição temporal"],
    ["01/01/2024", "Anual - sem observação nesta posição temporal",
     "Trimestral - 1.º trimestre de 2024: 1,2 %", "Mensal - janeiro de 2024: 2 %"],
    ["01/02/2024", "Anual - sem observação nesta posição temporal",
     "Trimestral - sem observação nesta posição temporal",
     "Mensal - fevereiro de 2024: 2,1 %"],
    ["01/01/2025", "Anual - 2025: 110 %", "Trimestral - 1.º trimestre de 2025: 1,4 %",
     "Mensal - sem observação nesta posição temporal"],
]


def expected_readout(row):
    return row[0] + " - " + "; ".join(row[1:])


def sparse_model():
    return calendar_model(
        (ANNUAL, QUARTERLY, MONTHLY),
        labels=("Anual", "Trimestral", "Mensal"),
        units=("%", "%", "%"),
        frequencies=("A", "Q", "M"),
        title="Prova esparsa",
    )


def page_html(model, payload):
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    plot = str(calendar_plot(model))
    legend = str(calendar_legend(model))
    last = len(payload["periods"]) - 1
    return f"""<!doctype html>
<html lang="pt-PT"><head><meta charset="utf-8">
<link rel="icon" href="data:,">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prova esparsa</title>
<style>
:root {{
  --ink: #1a1a1a; --red: #c0392b; --muted: #524d48; --rule: #e2ded9;
  --sans: "Lato", system-ui, sans-serif; --accent: #9b1c2e;
  --chart-series-2: #2f5d8a; --chart-series-3: #8a5a00; --chart-series-4: #2e7d32;
  --chart-series-5: #6b3fa0; --chart-series-6: #0b6b6b;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: var(--sans); background: #faf8f5; color: var(--ink); }}
.chart-shell {{ width: 880px; }}
.chart-wrap {{ position: relative; width: 880px; height: 340px; }}
.chart-wrap .chart {{ width: 100%; height: 100%; }}
.chart-canvas {{ position: absolute; inset: 0; opacity: 0; pointer-events: none; }}
.chart-enhanced .chart-canvas {{ opacity: 1; pointer-events: auto; }}
.chart-enhanced .chart {{ opacity: 0; pointer-events: none; }}
.chart-controls {{ width: 880px; }}
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


class _Site:
    def __init__(self, url, payload):
        self.url = url
        self.payload = payload


@pytest.fixture(scope="module")
def synthetic_site(tmp_path_factory):
    root = tmp_path_factory.mktemp("calendar-probe")
    (root / "static" / "js").mkdir(parents=True)
    shutil.copy2(BUNDLE, root / "static" / "js" / "prumo-charts.min.js")
    model = sparse_model()
    assert model is not None
    payload = build_payload(model)
    assert payload is not None
    (root / "valid.html").write_text(page_html(model, payload), encoding="utf-8")

    def invalid(name, mutate):
        copy = json.loads(json.dumps(payload))
        mutate(copy)
        (root / f"{name}.html").write_text(page_html(model, copy), encoding="utf-8")

    invalid("kind", lambda data: data.update(kind="comparison"))
    invalid("ordinals", lambda data: data["x"].__setitem__(1, data["x"][0]))
    invalid("half-null", lambda data: data["display"][2].__setitem__(0, "2,1 %"))
    invalid("breaks", lambda data: data["series"][0].__setitem__("breaks", [99]))
    invalid("missing", lambda data: data.pop("missing"))

    handler = partial(_Handler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield _Site(f"http://127.0.0.1:{port}", payload)
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


def _open(browser, url, *, touch=False):
    context = browser.new_context(viewport={"width": 900, "height": 700},
                                  device_scale_factor=1, has_touch=touch)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(url, wait_until="networkidle")
    page.wait_for_selector(".chart-enhanced canvas", timeout=10000)
    page.wait_for_timeout(100)
    return context, page, errors


def _payload(page):
    return json.loads(page.evaluate(
        "() => document.querySelector('script.chart-data').textContent"))


def _box(page):
    return page.evaluate("() => {const b = document.querySelector('.chart-canvas')"
                         ".getBoundingClientRect();"
                         "return {left: b.left, top: b.top, width: b.width, height: b.height};}")


def _move(page, box, x):
    page.mouse.move(box["left"] + x, box["top"] + box["height"] / 2)
    page.wait_for_timeout(50)


def _value(page):
    return page.evaluate("() => Number(document.querySelector('.chart-range').value)")


def _readout(page):
    return page.evaluate(
        "() => ({value: Number(document.querySelector('.chart-range').value),"
        " vt: document.querySelector('.chart-range').getAttribute('aria-valuetext'),"
        " readout: document.querySelector('.chart-readout').textContent,"
        " live: document.querySelector('.chart-live').textContent})")


def _structured(page):
    return page.evaluate("""() => ({
      period: (document.querySelector('.chart-readout-period') || {}).textContent || '',
      rows: [...document.querySelectorAll('.chart-readout-row')].map((row) => ({
        missing: row.getAttribute('data-missing'),
        title: (row.querySelector('.chart-readout-title') || {}).textContent || '',
        native: (row.querySelector('.chart-readout-native') || {}).textContent || '',
        value: (row.querySelector('.chart-readout-value') || {}).textContent || ''
      }))
    })""")


def _expect_rows(structured, payload, index):
    assert structured["period"] == payload["periods"][index]
    assert len(structured["rows"]) == len(payload["series"])
    for side, row in enumerate(structured["rows"]):
        native = payload["cell_periods"][index][side]
        assert row["title"] == payload["series"][side]["title"]
        assert row["native"] == ("" if native is None else native)
        if native is None:
            assert row["missing"] == "true"
            assert row["value"] == payload["missing"]
        else:
            assert row["missing"] is None
            assert row["value"] == payload["display"][index][side]


def _find_value(page, box, target):
    for x in range(2, int(box["width"]) - 1, 4):
        _move(page, box, x)
        if _value(page) == target:
            return x
    raise AssertionError(f"row {target} was not reachable by pointer")


def _show(page, box, x):
    page.mouse.move(0, 0)
    try:
        page.locator(".chart-tooltip").wait_for(state="hidden", timeout=2000)
    except Exception:
        pass
    _move(page, box, x)
    page.locator(".chart-tooltip .chart-tip-line").first.wait_for(state="visible", timeout=5000)
    page.wait_for_timeout(60)


def _tooltip_rows(page):
    return page.locator(".chart-tooltip .chart-tip-line").all_text_contents()


SCAN = """() => {
  const stage = document.querySelector('.chart-canvas');
  const canvas = stage.querySelector('canvas');
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  function columns(test) {
    const out = [];
    for (let x = 0; x < canvas.width; x += 1) {
      for (let y = 0; y < canvas.height; y += 1) {
        const i = (y * canvas.width + x) * 4;
        if (test(data[i], data[i + 1], data[i + 2], data[i + 3])) { out.push(x); break; }
      }
    }
    return out;
  }
  function clusters(cols) {
    const groups = [];
    let start = null, previous = null;
    for (const x of cols) {
      if (start === null) { start = previous = x; }
      else if (x - previous <= 2) { previous = x; }
      else { groups.push([start, previous]); start = previous = x; }
    }
    if (start !== null) groups.push([start, previous]);
    return groups;
  }
  const accent = columns((r, g, b, a) => a > 128 && r >= 130 && r <= 180 && g < 60 && b < 75);
  const quarterly = columns((r, g, b, a) => a > 128 && r < 80 && g > 70 && g < 120 && b > 110);
  const monthly = columns((r, g, b, a) => a > 128 && r > 110 && r < 165 && g > 65 && g < 115 && b < 45);
  return {dpr: window.devicePixelRatio, width: canvas.width, height: canvas.height,
          accent: clusters(accent), quarterly: clusters(quarterly), monthly: clusters(monthly)};
}"""


def test_adapter_source_keeps_the_v2_contract_explicit():
    source = (ROOT / "tools" / "charts" / "src" / "adapter.js").read_text(encoding="utf-8")
    assert "payload.version === 2" in source
    assert "payload.kind !== 'calendar'" in source
    assert "payload.y[i][seriesIndex] === null" in source
    assert "data.push(null)" in source
    assert "function indexMap(payload, seriesIndex)" in source
    assert "payload.series[seriesIndex].breaks" in source
    assert "payload.cell_periods[point][index]" in source
    assert "payload.missing" in source
    assert "a: { color: ink, type: 'solid' }" in source
    assert "b: { color: red, type: 'dashed' }" in source
    for forbidden in ("Number(payload.y", "Number(payload.display", "fetch(", "XMLHttpRequest",
                      "innerHTML", "eval(", "new Function", "document.write"):
        assert forbidden not in source
    for listener in ("addEventListener('pointermove'", "addEventListener('pointerdown'",
                     "addEventListener('pointerup'", "range.addEventListener('input'"):
        assert listener in source


def test_v2_pointer_tooltip_readout_and_native_gaps_are_exact(browser, synthetic_site):
    context, page, errors = _open(browser, synthetic_site.url + "/valid.html")
    try:
        payload = _payload(page)
        assert payload["version"] == 2 and payload["kind"] == "calendar"
        assert payload["x"] == sorted(set(payload["x"]))
        assert all(float(value).is_integer() for value in payload["x"])
        assert payload["series"][0]["breaks"] == [3]
        assert payload["series"][1]["breaks"] == [1, 3]
        assert payload["series"][2]["breaks"] == []
        assert payload["cell_periods"][2] == [None, None, "fevereiro de 2024"]
        assert "2024-02" not in json.dumps(payload, ensure_ascii=False)

        scan = page.evaluate(SCAN)
        assert scan["dpr"] == 1
        # The annual line has two painted symbols and no connecting segment through 2024.
        assert len(scan["accent"]) == 2, scan["accent"]
        centers = [(first + last) / 2 for first, last in scan["accent"]]
        assert centers[1] - centers[0] > 200
        assert scan["quarterly"] and scan["monthly"]

        box = _box(page)
        accent_centers = [(first + last) / 2 for first, last in scan["accent"]]
        monthly_centers = [(first + last) / 2 for first, last in scan["monthly"]]
        # The painted annual marks select their own union rows, not an invented monthly value.
        for center, expected in zip(accent_centers, (0, 3)):
            _move(page, box, center)
            assert _value(page) == expected

        # Monthly symbols exist at both observed rows and never on the annual or quarterly rows.
        monthly_values = set()
        for center in monthly_centers:
            _move(page, box, center)
            monthly_values.add(_value(page))
        assert {1, 2} <= monthly_values

        x2 = monthly_centers[-1]
        _show(page, box, x2)
        state = _readout(page)
        assert state["value"] == 2
        assert state["vt"] == payload["periods"][2]
        assert state["readout"] == expected_readout(EXPECTED_ROWS[2])
        rows = _tooltip_rows(page)
        assert rows == EXPECTED_ROWS[2]
        assert state["readout"] == rows[0] + " - " + "; ".join(rows[1:])
        assert state["live"] == ""
        _expect_rows(_structured(page), payload, 2)
        assert "null" not in state["readout"] and "undefined" not in state["readout"]

        # The annual value is absent at the intervening month, not carried forward.
        _show(page, box, monthly_centers[0])
        rows = _tooltip_rows(page)
        assert rows == EXPECTED_ROWS[1]
        assert "Anual - sem observação" in rows[1]
        assert "100 %" not in _readout(page)["readout"]
        assert "110 %" not in _readout(page)["readout"]

        # Nudge just inside the painted grid: a pointer exactly on the left edge does not open
        # an ECharts axis tooltip, though the readout already clamps to the first row.
        _show(page, box, accent_centers[0] + 8)
        assert _tooltip_rows(page) == EXPECTED_ROWS[0]
        assert not errors
    finally:
        context.close()


def test_v2_touch_and_keyboard_open_the_union_tooltip_when_most_sides_are_null(browser,
                                                                               synthetic_site):
    context, page, errors = _open(browser, synthetic_site.url + "/valid.html", touch=True)
    try:
        payload = _payload(page)
        box = _box(page)
        x2 = _find_value(page, box, 2)
        scroll_before = page.evaluate("() => window.scrollY")
        page.touchscreen.tap(box["left"] + x2, box["top"] + box["height"] / 2)
        page.wait_for_timeout(220)
        state = _readout(page)
        assert state["value"] == 2
        assert state["vt"] == payload["periods"][2]
        assert state["readout"] == expected_readout(EXPECTED_ROWS[2])
        assert _tooltip_rows(page) == EXPECTED_ROWS[2]
        assert page.evaluate("() => window.scrollY") == scroll_before
        assert "null" not in state["readout"] and "undefined" not in state["readout"]

        page.locator(".chart-range").focus()
        page.keyboard.press("Home")
        page.wait_for_timeout(80)
        assert _readout(page)["value"] == 0
        assert _readout(page)["readout"] == expected_readout(EXPECTED_ROWS[0])
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(80)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(120)
        state = _readout(page)
        assert state["value"] == 2
        assert state["readout"] == expected_readout(EXPECTED_ROWS[2])
        assert state["live"] == state["readout"]
        _expect_rows(_structured(page), payload, 2)
        assert _tooltip_rows(page) == EXPECTED_ROWS[2]
        assert not errors
    finally:
        context.close()


@pytest.mark.parametrize("name", ["kind", "ordinals", "half-null", "breaks", "missing"])
def test_malformed_v2_payload_leaves_the_svg_fallback(browser, synthetic_site, name):
    context = browser.new_context(viewport={"width": 900, "height": 700},
                                  device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        page.goto(synthetic_site.url + f"/{name}.html", wait_until="networkidle")
        page.wait_for_timeout(120)
        assert page.evaluate("() => document.querySelectorAll('canvas').length") == 0
        assert page.evaluate(
            "() => document.querySelector('.chart-shell').classList.contains('chart-enhanced')"
        ) is False
        assert page.locator("svg.chart").is_visible()
        assert page.locator(".chart-readout").text_content() == ""
        assert page.locator(".chart-live").text_content() == ""
        assert not errors
    finally:
        context.close()
