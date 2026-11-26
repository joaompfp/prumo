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
GDP_PC = "worldbank.gdp_per_capita.PT"
CALENDAR = "/caderno?s=ine.hicp_yoy.PT&s=worldbank.gdp_per_capita.PT&escala=dupla"


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


def _add_calendar_pair(path):
    """A 121-row native calendar: monthly HICP against annual GDP per capita.

    The rows, units and axis ranges match the production mixed pair, so the last period sits
    on the same narrow-canvas plot edge the keyboard End key has to cross.
    """
    db = open_db(path)
    try:
        db.conn.execute(
            "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
            "frequency, unit, active) VALUES (?, 4, 'worldbank_gdp_per_capita.PT.A', "
            "'primary', 'economy', 'PT', 'A', 'USD', 1)", (GDP_PC,))
        db.conn.commit()
    finally:
        db.close()
    periods = _months(121)
    db = open_db(path)
    try:
        fetch(db, "ine.hicp_yoy.PT",
              {period: f"{-0.8 + (index % 12) * 1.036:.1f}"
               for index, period in enumerate(periods)}, T2, sha="a" * 64)
        fetch(db, GDP_PC,
              {str(year): f"{21442.3842768879 + (year - 2017) * 1300:.6f}"
               for year in range(2017, 2026)}, T2, source="worldbank", sha="e" * 64)
    finally:
        db.close()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory):
    import uvicorn

    path = tmp_path_factory.mktemp("chart-browser") / "site.db"
    build(path)
    _add_market_pair(path)
    _add_calendar_pair(path)
    from tests.app.cms_fixtures import publish_comparisons
    publish_comparisons(path, ("credito-e-taxa",))
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

READOUT = """() => ({
  text: document.querySelector('.chart-readout').textContent,
  period: (document.querySelector('.chart-readout-period') || {}).textContent || '',
  live: document.querySelector('.chart-live').textContent,
  rows: [...document.querySelectorAll('.chart-readout-row')].map((row) => ({
    axis: row.getAttribute('data-axis'),
    missing: row.getAttribute('data-missing'),
    swatch: (row.querySelector('.legend-swatch') || {}).className || '',
    unit: row.getAttribute('data-unit') || '',
    title: (row.querySelector('.chart-readout-title') || {}).textContent || '',
    native: (row.querySelector('.chart-readout-native') || {}).textContent || '',
    value: (row.querySelector('.chart-readout-value') || {}).textContent || ''
  }))
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


@pytest.mark.parametrize("width", [320, 390])
def test_structured_readout_rows_keep_exact_text_and_polite_keyboard_announcement(browser, site_url,
                                                                                  width):
    context, page, errors = _open(browser, site_url + PAIR, width)
    try:
        payload = _payload(page)
        ink = page.evaluate(SCAN)
        box = ink["box"]
        _move(page, box, (ink["min"] + ink["max"]) / 2)
        index = page.evaluate(READ)["value"]
        state = page.evaluate(READOUT)
        assert state["period"] == payload["periods"][index]
        assert len(state["rows"]) == len(payload["series"]) == 2
        # Existing consumers still get the reviewed one-line sentence from textContent.
        assert state["text"] == readout_text(payload, index)
        for side, row in enumerate(state["rows"]):
            assert row["title"] == payload["series"][side]["title"]
            assert row["value"] == payload["display"][index][side]
            assert row["axis"] == str(payload["series"][side].get("axis", side))
            assert payload["series"][side]["style"] in row["swatch"]
            assert row["unit"] == payload["series"][side]["unit"]
            assert row["missing"] is None
        # Pointer movement updates the visible rows but never floods the polite live region.
        assert state["live"] == ""
        assert page.evaluate(TOOLTIP)["rows"] == tooltip_rows(payload, index)

        # Keyboard stepping is the announced path: the full exact sentence, politely.
        page.locator(".chart-range").focus()
        page.keyboard.press("Home")
        page.wait_for_timeout(80)
        state = page.evaluate(READOUT)
        assert state["period"] == payload["periods"][0]
        assert state["text"] == readout_text(payload, 0)
        assert state["live"] == readout_text(payload, 0)
        assert state["rows"][0]["value"] == payload["display"][0][0]
        assert state["rows"][1]["value"] == payload["display"][0][1]

        # The parent links chart-inspector.css. Applying it here proves the native range grows
        # without the reading type shrinking and the rows stay inside the page.
        page.add_style_tag(url=site_url + "/static/css/chart-inspector.css")
        page.wait_for_timeout(80)
        metrics = page.evaluate("""() => {
          const range = document.querySelector('.chart-range');
          const readout = document.querySelector('.chart-readout');
          const row = document.querySelector('.chart-readout-row');
          const sep = document.querySelector('.chart-readout-sep');
          return {
            rangeH: range.getBoundingClientRect().height,
            font: parseFloat(getComputedStyle(readout).fontSize),
            rowDisplay: getComputedStyle(row).display,
            sepDisplay: getComputedStyle(sep).display,
            swatches: [...document.querySelectorAll('.chart-readout-row > .legend-swatch')]
              .map((swatch) => {
                const style = getComputedStyle(swatch);
                return {width: swatch.getBoundingClientRect().width,
                        colour: style.backgroundColor, pattern: style.backgroundImage};
              }),
            scrollW: document.documentElement.scrollWidth,
            innerW: window.innerWidth
          };
        }""")
        assert metrics["rangeH"] >= 47.5, metrics
        assert metrics["font"] >= 25.2, metrics
        assert metrics["rowDisplay"] == "flex", metrics
        assert metrics["sepDisplay"] == "none", metrics
        # Both prepared series show their own painted key beside the title: solid ink and the
        # dashed carmim pattern, never a colour inferred here from a translated label.
        assert len(metrics["swatches"]) == len(payload["series"]), metrics
        assert all(swatch["width"] >= 17 for swatch in metrics["swatches"]), metrics
        assert all(swatch["colour"] != "rgba(0, 0, 0, 0)" or swatch["pattern"] != "none"
                   for swatch in metrics["swatches"]), metrics
        assert metrics["scrollW"] <= metrics["innerW"] + 1, metrics
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


def calendar_rows(payload, index):
    rows = [payload["periods"][index]]
    for side in range(len(payload["series"])):
        period = payload["cell_periods"][index][side]
        title = payload["series"][side]["title"]
        if period is None:
            rows.append(title + " - " + payload["missing"])
        else:
            rows.append(title + " - " + period + ": " + payload["display"][index][side])
    return rows


def calendar_readout(payload, index):
    rows = calendar_rows(payload, index)
    return rows[0] + " - " + "; ".join(rows[1:])


def test_mobile_keyboard_end_replaces_the_previous_calendar_tooltip(browser, site_url):
    """121 native-calendar rows at 390 touch: End must repaint every tooltip line.

    The last period converts to the plot's right edge. ECharts rejects a pixel point whose
    round-trip back to local coordinates lands outside the grid, so the tooltip can keep the
    previous period even though the native range and readout already moved. This checks the
    rendered tooltip itself, line by line, not only the readout.
    """
    from playwright.sync_api import expect

    context, page, errors = _open(browser, site_url + CALENDAR, 390, touch=True)
    try:
        payload = _payload(page)
        assert payload["version"] == 2 and payload["kind"] == "calendar"
        assert len(payload["periods"]) == 121
        last = len(payload["periods"]) - 1
        assert payload["periods"][last] == "01/10/2026"

        page.locator(".chart-range").focus()
        page.keyboard.press("Home")
        expect(page.locator(".chart-readout")).to_have_text(
            calendar_readout(payload, 0), timeout=3000)
        page.keyboard.press("ArrowRight")
        expect(page.locator(".chart-readout")).to_have_text(
            calendar_readout(payload, 1), timeout=3000)
        # A visible tooltip for the previous period is the state End has to replace.
        expect(page.locator(".chart-tooltip")).to_be_visible(timeout=3000)
        expect(page.locator(".chart-tip-line").first).to_have_text(
            payload["periods"][1], timeout=3000)

        page.keyboard.press("End")
        expect(page.locator(".chart-readout")).to_have_text(
            calendar_readout(payload, last), timeout=3000)
        expect(page.locator(".chart-tooltip")).to_be_visible(timeout=3000)
        expected = calendar_rows(payload, last)
        expect(page.locator(".chart-tip-line")).to_have_count(len(expected), timeout=3000)
        for index, line in enumerate(expected):
            expect(page.locator(".chart-tip-line").nth(index)).to_have_text(
                line, timeout=3000)
        assert page.evaluate(
            "() => document.querySelector('.chart-range').getAttribute('aria-valuetext')"
        ) == payload["periods"][last]
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert not errors
    finally:
        context.close()


def test_structured_calendar_readout_keeps_long_missing_text_inside_the_page(browser, site_url):
    context, page, errors = _open(browser, site_url + CALENDAR, 320)
    try:
        page.add_style_tag(url=site_url + "/static/css/chart-inspector.css")
        page.wait_for_timeout(80)
        page.locator(".chart-range").focus()
        page.keyboard.press("End")
        page.wait_for_timeout(120)
        payload = _payload(page)
        last = len(payload["periods"]) - 1
        state = page.evaluate(READOUT)
        assert state["text"] == calendar_readout(payload, last)
        assert len(state["rows"]) == len(payload["series"]) == 2
        assert state["rows"][1]["missing"] == "true"
        assert state["rows"][1]["value"] == payload["missing"]
        assert state["live"] == calendar_readout(payload, last)
        metrics = page.evaluate("""() => {
          const out = document.querySelector('.chart-readout').getBoundingClientRect();
          const box = document.querySelector('.chart-readout-row:last-child .chart-readout-value')
            .getBoundingClientRect();
          return {scrollW: document.documentElement.scrollWidth,
                  innerW: window.innerWidth,
                  inside: box.left >= out.left - 0.5 && box.right <= out.right + 0.5};
        }""")
        assert metrics["scrollW"] <= metrics["innerW"] + 1, metrics
        assert metrics["inside"], metrics
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
        structured = page.evaluate(READOUT)
        assert structured["period"] == "outubro de 2026"
        assert len(structured["rows"]) == 1
        assert structured["rows"][0]["title"] == ""
        assert structured["rows"][0]["value"] == "0,3 p.p."
        assert structured["live"] == ""
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
        # No empty inspector gap between the plot and the legend when enhancement never runs.
        assert page.locator(".chart-controls").evaluate(
            "el => getComputedStyle(el).display") == "none"
    finally:
        context.close()
