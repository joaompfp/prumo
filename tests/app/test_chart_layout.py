"""The comparison legend must live outside the canvas overlay.

`.chart-canvas` is absolute with `inset: 0` inside `.chart-wrap`. If the legend were inside that
wrapper, ECharts would size the plot to the SVG plus the legend and the opaque canvas would
cover it. The parser test pins the DOM contract; the optional Playwright test measures the real
boxes with JavaScript off and after enhancement, so a regression cannot hide in a source string.
"""
import os
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.app.conftest import build
from tests.app.test_comparisons import _add_bp

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
COMPARISON = "/comparar/inflacao-e-desemprego"


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None" = None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node] = []

    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def find_all(self, tag: str | None = None, cls: str | None = None) -> list["Node"]:
        found = []
        for child in self.children:
            if (tag is None or child.tag == tag) and (cls is None or cls in child.classes()):
                found.append(child)
            found.extend(child.find_all(tag, cls))
        return found


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {name: value or "" for name, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {name: value or "" for name, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def dom(html: str) -> Node:
    parser = _Parser()
    parser.feed(html)
    return parser.root


@pytest.fixture(scope="module")
def comparison_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("chart-layout") / "layout.db"
    build(path)
    _add_bp(path)
    from tests.app.cms_fixtures import publish_comparisons
    publish_comparisons(path, ("inflacao-e-desemprego",))
    return path


@pytest.fixture
def comparison_html(comparison_path):
    with TestClient(create_app(str(comparison_path))) as client:
        response = client.get(COMPARISON)
    assert response.status_code == 200
    return response.text


def test_legend_is_a_sibling_of_the_plot_that_the_canvas_covers(comparison_html):
    root = dom(comparison_html)
    shells = root.find_all("div", "chart-shell")
    assert len(shells) == 1
    shell = shells[0]
    wraps = shell.find_all("div", "chart-wrap")
    assert len(wraps) == 1
    wrap = wraps[0]
    legends = shell.find_all("ul", "legend")
    assert len(legends) == 1
    legend = legends[0]
    canvases = wrap.find_all("div", "chart-canvas")
    assert len(canvases) == 1

    # The legend is a sibling of the positioned wrapper, never a child the overlay can cover.
    assert legend.parent is shell and legend not in wrap.find_all("ul", "legend")
    assert canvases[0].parent is wrap
    assert len(legend.find_all("li")) == 2

    # One accessible chart: the named SVG remains; the canvas stays ornamental.
    svgs = [node for node in wrap.find_all("svg") if "chart" in node.classes()]
    assert len(svgs) == 1
    images = [node for node in root.find_all("svg") if node.attrs.get("role") == "img"]
    assert images == svgs
    assert svgs[0].attrs.get("aria-label") and svgs[0].find_all("title")
    assert canvases[0].attrs.get("aria-hidden") == "true"


def _chromium() -> str | None:
    configured = os.environ.get("PRUMO_TEST_CHROMIUM")
    if configured:
        return configured
    cache = Path.home() / ".cache" / "ms-playwright"
    patterns = ("chromium-*/chrome-linux*/chrome",
                "chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")
    for pattern in patterns:
        found = sorted(cache.glob(pattern))
        if found:
            return str(found[-1])
    return None


@pytest.fixture
def live_comparison_url(comparison_path):
    import uvicorn

    config = uvicorn.Config(create_app(str(comparison_path)), host="127.0.0.1", port=0,
                            log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    if not server.started:
        pytest.skip("uvicorn did not start the comparison site")
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}{COMPARISON}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


BOXES = """() => {
  const box = (selector) => {
    const el = document.querySelector(selector);
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return {top: rect.top + scrollY, bottom: rect.bottom + scrollY,
            left: rect.left + scrollX, width: rect.width, height: rect.height};
  };
  return {shell: box('.chart-shell'), wrap: box('.chart-wrap'),
          svg: box('.chart-wrap > svg.chart'), canvas: box('.chart-canvas'),
          legend: box('.chart-shell > ul.legend'), controls: box('.chart-controls')};
}"""


def test_enhancement_keeps_the_legend_visible_without_layout_shift(live_comparison_url):
    sync_api = pytest.importorskip("playwright.sync_api")
    executable = _chromium()
    options = {"headless": True, "args": ["--no-sandbox"]}
    if executable:
        options["executable_path"] = executable
    try:
        playwright = sync_api.sync_playwright().start()
    except Exception as exc:  # Playwright is installed but its driver is not usable
        pytest.skip(f"Playwright unavailable: {exc}")
    browser = None
    try:
        browser = playwright.chromium.launch(**options)
    except Exception as exc:  # a browser is an optional local/CI dependency
        playwright.stop()
        pytest.skip(f"Chromium unavailable: {exc}")
    try:
        viewport = {"width": 1100, "height": 900}
        plain_context = browser.new_context(viewport=viewport, java_script_enabled=False)
        plain = plain_context.new_page()
        plain.goto(live_comparison_url, wait_until="networkidle")
        before = plain.evaluate(BOXES)
        assert before["legend"]["height"] > 0
        plain_context.close()

        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_comparison_url, wait_until="networkidle")
        page.wait_for_selector(".chart-enhanced canvas", timeout=10000)
        after = page.evaluate(BOXES)

        assert page.locator(".chart-shell > ul.legend").is_visible()
        assert len(page.query_selector_all("svg[role=img]")) == 1
        # The canvas covers the SVG plot exactly; the legend starts at or below its bottom.
        assert after["canvas"]["height"] == pytest.approx(after["svg"]["height"], abs=1)
        assert after["canvas"]["bottom"] <= after["legend"]["top"] + 1
        # Enhancement changes paint, not the plot/legend boxes. Controls and the hint become
        # visible below by design; their tops stay put and only their own height grows.
        for key in ("shell", "wrap", "legend", "controls"):
            assert after[key]["top"] == pytest.approx(before[key]["top"], abs=1), key
        for key in ("wrap", "legend"):
            assert after[key]["height"] == pytest.approx(before[key]["height"], abs=1), key
        assert not errors
        context.close()
    finally:
        if browser is not None:
            browser.close()
        playwright.stop()
