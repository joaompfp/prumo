"""Real-browser regression for chart point selection, tooltip completeness and mobile width.

Ground truth is the painted chart, not a guessed canvas fraction: the leftmost and rightmost
dark pixels of the first series are the drawn first and last periods. A pointer or a touch on
those pixels must read those periods, the padding around the plot must clamp to the same two
ends, and the keyboard must reach the same values. The tooltip is a DOM node whose rows must
carry the exact prepared strings and whose box must stay inside the canvas. Nothing here reads
ECharts internals or patches the DOM/library.

Skipped when Playwright or a cached Chromium is absent; the rest of the suite is unaffected.
"""
import json
import threading
import time

import pytest

from app.main import create_app
from ingest.db import open_db
from tests.app.conftest import T2, build, fetch
from tests.app.test_chart_layout import _chromium

BP = "bportugal"
EUR12 = "bportugal.euribor_12m.EA"
CREDIT = "bportugal.credit_housing.PT"
PAIR = "/comparar/credito-e-taxa"
SINGLE = "/calculadas/derived.unemployment_monthly.PT.yoy_change"


def _months(count=120):
    year, month = 2016, 10
    out = []
    for _ in range(count):
        out.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            month, year = 1, year + 1
    return out


def _add_market_pair(path):
    """A dual-axis pair with 120 common months, so a middle period exists and values are long."""
    db = open_db(path)
    try:
        db.conn.execute(
            "INSERT INTO source(id, name, licence, licence_url, attribution, redistribution_ok) "
            "VALUES (6, ?, 'CC BY 4.0', 'https://www.bportugal.pt/terms', "
            "'Banco de Portugal', 1)", (BP,))
        for sid, key, geography, unit in ((EUR12, "euribor_12m.EA.M", "EA", "%"),
                                          (CREDIT, "credit_housing.PT.M", "PT", "MEUR")):
            db.conn.execute(
                "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
                "frequency, unit, active) VALUES (?, 6, ?, 'primary', 'economy', ?, 'M', ?, 1)",
                (sid, key, geography, unit))
        db.conn.commit()
    finally:
        db.close()
    periods = _months()
    db = open_db(path)
    try:
        fetch(db, EUR12, {p: f"{-0.0688 + i * 0.02786:.4f}" for i, p in enumerate(periods)},
              T2, source=BP, sha="a" * 64)
        fetch(db, CREDIT, {p: f"{94907.3 + i * 212.4:.1f}" for i, p in enumerate(periods)},
              T2, source=BP, sha="c" * 64)
    finally:
        db.close()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory):
    import uvicorn

    path = tmp_path_factory.mktemp("chart-browser") / "site.db"
    build(path)
    _add_market_pair(path)
    config = uvicorn.Config(create_app(str(path)), host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    if not server.started:
        pytest.skip("uvicorn did not start the chart site")
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
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


# The canvas is read at devicePixelRatio 1, so canvas pixels are CSS pixels. The muted axis
# labels are #524d48 (r=82); the series ink is #1a1a1a, so r,g,b < 70 selects the drawn line.
SCAN = """() => {
  const stage = document.querySelector('.chart-canvas');
  const canvas = stage.querySelector('canvas');
  const box = stage.getBoundingClientRect();
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let min = null, max = null;
  for (let x = 0; x < canvas.width; x += 1) {
    for (let y = 0; y < canvas.height; y += 1) {
      const i = (y * canvas.width + x) * 4;
      if (data[i] < 70 && data[i + 1] < 70 && data[i + 2] < 70 && data[i + 3] > 128) {
        if (min === null) min = x;
        max = x;
        break;
      }
    }
  }
  return {min: min, max: max, dpr: window.devicePixelRatio,
          box: {left: box.left, top: box.top, width: box.width, height: box.height}};
}"""

READ = """() => ({
  value: Number(document.querySelector('.chart-range').value),
  vt: document.querySelector('.chart-range').getAttribute('aria-valuetext'),
  readout: document.querySelector('.chart-readout').textContent,
  scrollW: document.documentElement.scrollWidth,
  innerW: window.innerWidth,
  rangeW: document.querySelector('.chart-range').getBoundingClientRect().width,
  controlsW: document.querySelector('.chart-controls').getBoundingClientRect().width
})"""

TOOLTIP = """() => {
  const tip = document.querySelector('.chart-tooltip');
  if (!tip || getComputedStyle(tip).display === 'none') return null;
  const box = tip.getBoundingClientRect();
  const canvas = document.querySelector('.chart-canvas').getBoundingClientRect();
  return {rows: [...tip.querySelectorAll('.chart-tip-line')].map(el => el.textContent),
          left: box.left - canvas.left, right: box.right - canvas.left,
          top: box.top - canvas.top, bottom: box.bottom - canvas.top,
          width: canvas.width, height: canvas.height};
}"""


def readout_text(payload, index):
    period = payload["periods"][index]
    if len(payload["series"]) == 1:
        return period + ": " + payload["display"][index][0]
    parts = [payload["series"][i]["title"] + ": " + payload["display"][index][i]
             for i in range(len(payload["series"]))]
    return period + " - " + "; ".join(parts)


def tooltip_rows(payload, index):
    rows = [payload["periods"][index]]
    rows += [payload["series"][i]["title"] + ": " + payload["display"][index][i]
             for i in range(len(payload["series"]))]
    return rows


def _payload(page):
    return json.loads(page.evaluate(
        "() => document.querySelector('script.chart-data').textContent"))


def _open(browser, url, width, *, touch=False):
    context = browser.new_context(viewport={"width": width, "height": 900},
                                  device_scale_factor=1, has_touch=touch, is_mobile=touch)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(url, wait_until="networkidle")
    page.wait_for_selector(".chart-enhanced canvas", timeout=10000)
    page.locator(".chart-wrap").scroll_into_view_if_needed()
    page.wait_for_timeout(120)
    return context, page, errors


def _move(page, box, x, y=None):
    page.mouse.move(box["left"] + x, box["top"] + (box["height"] / 2 if y is None else y))
    page.wait_for_timeout(90)


@pytest.mark.parametrize("width", [320, 390, 768, 1440])
def test_pointer_reads_the_period_painted_under_it(browser, site_url, width):
    context, page, errors = _open(browser, site_url + PAIR, width)
    try:
        payload = _payload(page)
        ink = page.evaluate(SCAN)
        assert ink["dpr"] == 1
        assert ink["min"] is not None and ink["max"] - ink["min"] > 50
        box = ink["box"]
        last = len(payload["periods"]) - 1

        # Left and right drawn end symbols, the middle of the drawn span, and the canvas padding.
        checks = [(ink["min"] + 1, 0), ((ink["min"] + ink["max"]) / 2, None),
                  (ink["max"] - 1, last), (2, 0), (box["width"] - 2, last)]
        for x, expected in checks:
            _move(page, box, x)
            state = page.evaluate(READ)
            index = state["value"]
            if expected is None:
                assert abs(index - (last / 2)) <= 1, (width, x, index)
            else:
                assert index == expected, (width, x, index)
            assert state["vt"] == payload["periods"][index]
            assert state["readout"] == readout_text(payload, index)

        # The tooltip at the middle of the painted span carries the prepared strings whole.
        _move(page, box, (ink["min"] + ink["max"]) / 2)
        tip = page.evaluate(TOOLTIP)
        index = page.evaluate(READ)["value"]
        assert tip is not None
        assert tip["rows"] == tooltip_rows(payload, index)
        assert tip["left"] >= -1 and tip["right"] <= tip["width"] + 1
        assert tip["top"] >= -1 and tip["bottom"] <= tip["height"] + 1

        # The footer links wrap; the page never pans sideways.
        assert page.evaluate(READ)["scrollW"] <= page.evaluate(READ)["innerW"] + 1
        if width <= 600:
            state = page.evaluate(READ)
            assert state["rangeW"] >= state["controlsW"] * 0.9

        # Keyboard reaches exactly the same endpoints, and the readout stays exact.
        page.locator(".chart-range").focus()
        page.keyboard.press("Home")
        page.wait_for_timeout(80)
        assert page.evaluate(READ)["value"] == 0
        assert page.evaluate(READ)["readout"] == readout_text(payload, 0)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(80)
        assert page.evaluate(READ)["value"] == 1
        page.keyboard.press("End")
        page.wait_for_timeout(80)
        state = page.evaluate(READ)
        assert state["value"] == last and state["readout"] == readout_text(payload, last)
        assert state["scrollW"] <= state["innerW"] + 1
        assert not errors
    finally:
        context.close()


def test_touch_taps_select_the_visible_end_points(browser, site_url):
    context, page, errors = _open(browser, site_url + PAIR, 390, touch=True)
    try:
        payload = _payload(page)
        page.locator(".chart-wrap").scroll_into_view_if_needed()
        page.wait_for_timeout(120)
        ink = page.evaluate(SCAN)
        box = ink["box"]
        last = len(payload["periods"]) - 1
        scroll_before = page.evaluate("() => window.scrollY")

        page.touchscreen.tap(box["left"] + ink["min"] + 1, box["top"] + box["height"] / 2)
        page.wait_for_timeout(200)
        state = page.evaluate(READ)
        assert state["value"] == 0 and state["vt"] == payload["periods"][0]
        assert state["readout"] == readout_text(payload, 0)
        assert page.evaluate(TOOLTIP)["rows"] == tooltip_rows(payload, 0)

        page.touchscreen.tap(box["left"] + ink["max"] - 1, box["top"] + box["height"] / 2)
        page.wait_for_timeout(200)
        state = page.evaluate(READ)
        assert state["value"] == last and state["vt"] == payload["periods"][last]
        assert state["readout"] == readout_text(payload, last)
        assert page.evaluate(TOOLTIP)["rows"] == tooltip_rows(payload, last)
        assert page.evaluate("() => window.scrollY") == scroll_before
        assert not errors
    finally:
        context.close()


def test_single_point_keeps_its_readout_and_hides_the_stepping_hint(browser, site_url):
    context, page, errors = _open(browser, site_url + SINGLE, 390)
    try:
        payload = _payload(page)
        assert len(payload["periods"]) == 1
        state = page.evaluate(READ)
        assert page.evaluate("() => document.querySelector('.chart-range').hidden") is True
        assert page.evaluate("() => document.querySelector('.chart-hint').hidden") is True
        assert state["readout"] == readout_text(payload, 0)
        assert state["readout"] == "outubro de 2026: 0,3 p.p."
        assert not errors
    finally:
        context.close()


def test_no_javascript_still_gets_the_svg_and_a_contained_page(browser, site_url):
    context = browser.new_context(viewport={"width": 390, "height": 900}, java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(site_url + PAIR, wait_until="networkidle")
        assert page.locator("svg.chart[role=img]").is_visible()
        assert page.evaluate("() => document.querySelectorAll('canvas').length") == 0
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert page.locator(".chart-range").is_hidden()
    finally:
        context.close()
