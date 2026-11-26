"""Chart-first detail pages share a working layout, never public CMS composition controls."""
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from backoffice.cms import Cms
from tests.app.conftest import DERIVED, HICP, UNEMP, build
from tests.app.test_chart_layout import _chromium, dom
from tests.app.test_cms_comparisons import body
from tests.app.test_cms_reads import _chart
from tests.app.test_comparisons import _add_bp
from tests.app.test_interactive import payload_of


@pytest.fixture(scope="module")
def analytical_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("analytical-pages") / "pages.db"
    build(path)
    _add_bp(path)
    cms = Cms(path, path)
    for slug, config in (
        ("publicado", body()),
        ("biblioteca", _chart()),
        ("calculado", _chart(series_a=UNEMP, series_b=None, derived_key=DERIVED)),
    ):
        meta = cms.create("chart", slug, config, actor="fixture", note="criar")
        cms.publish("chart", slug, meta["version"], actor="fixture", note="publicar")
    return path


ROUTES = (
    f"/series/{HICP}",
    f"/calculadas/{DERIVED}",
    "/graficos/biblioteca",
    "/graficos/calculado",
    "/comparar/publicado",
)


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("prefix", ("", "/dados"))
def test_detail_pages_share_the_analytical_shell_and_local_inspector(analytical_path, route, prefix):
    with TestClient(create_app(str(analytical_path))) as client:
        response = client.get(route, headers={"X-Forwarded-Prefix": prefix})
        assert response.status_code == 200
        html = response.text
        root = dom(html)
        assert "notebook-main" in root.find_all("main")[0].classes()
        assert len(root.find_all("div", "notebook-workspace")) == 1
        assert len(root.find_all("h1")) == 1
        assert len(root.find_all("section", "notebook-chart")) == 1
        assert f'href="{prefix}/static/css/chart-inspector.css"' in html
        asset = client.get("/static/css/chart-inspector.css")
        assert asset.status_code == 200 and "min-height: 48px" in asset.text
        assert payload_of(html)["display"]
        assert len(root.find_all("output", "chart-readout")) == 1
        assert root.find_all("output", "chart-readout")[0].attrs["aria-live"] == "off"
        if route.startswith(("/comparar/", "/graficos/")):
            assert not root.find_all("main")[0].find_all("form")
            assert "notebook-chart-form" not in html
            assert "Configurar" not in html and "Acrescentar" not in html
            assert "/caderno?" not in html
        if route.startswith("/series/"):
            assert html.index('class="chart-section notebook-chart"') < html.index('class="figure-block"')
            assert f'href="{prefix}/series/{HICP}.csv"' in html
            assert "Último valor da série em" in html
        if route.startswith("/calculadas/"):
            assert html.index('class="chart-section notebook-chart"') < html.index('class="formula"')
            assert html.index('class="chart-section notebook-chart"') < html.index('class="figure-block"')
            assert f'href="{prefix}/calculadas/{DERIVED}.csv"' in html
        if route == "/graficos/biblioteca":
            assert html.index('class="chart-shell"') < html.index('class="authored-reading"')
        if route == "/comparar/publicado":
            shell = root.find_all("div", "chart-shell")[0]
            meta = root.find_all("details", "chart-meta")[0]
            links = root.find_all("ul", "authored-series-links")[0]
            legend = root.find_all("ul", "legend")[0]
            assert meta.parent is shell and links.parent is meta and legend.parent is shell
            assert shell.children.index(meta) < shell.children.index(legend)


@pytest.fixture(scope="module")
def analytical_origin(analytical_path):
    import uvicorn

    config = uvicorn.Config(create_app(str(analytical_path)), host="127.0.0.1", port=0,
                            log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(.02)
    assert server.started, "analytical acceptance server did not start"
    try:
        yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_chart_first_geometry_print_and_exact_inspection(analytical_origin):
    sync_api = pytest.importorskip("playwright.sync_api")
    executable = _chromium()
    if not executable:
        pytest.skip("Chromium is an optional browser dependency")
    with sync_api.sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        try:
            for width, height in ((1440, 1000), (390, 844), (320, 844)):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                for route in ROUTES:
                    response = page.goto(analytical_origin + route)
                    assert response.status == 200
                    page.evaluate("document.fonts.ready")
                    page.wait_for_selector(".chart-enhanced canvas")
                    page.evaluate("window.scrollTo(0,0)")
                    assert page.evaluate("scrollY") == 0
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        route, width, page.evaluate("""() => [...document.querySelectorAll('main *')]
                        .filter(el => { const r = el.getBoundingClientRect(); return r.right > innerWidth + 1; })
                        .slice(0, 8).map(el => [el.tagName, el.className, el.getBoundingClientRect().width])"""))
                    plot = page.locator(".chart-wrap").bounding_box()
                    assert plot and plot["height"] >= 250
                    if width == 1440:
                        assert plot["y"] + plot["height"] <= height, (route, plot)
                    slider = page.locator(".chart-range")
                    payload = json.loads(page.locator(".chart-data").text_content())
                    if len(payload["periods"]) > 1:
                        assert slider.bounding_box()["height"] >= 48
                        slider.focus()
                        slider.press("End")
                    else:
                        assert not slider.is_visible()  # no meaningless range for a single point
                    rows = page.locator(".chart-readout-row")
                    assert rows.count() == len(payload["series"])
                    assert rows.locator(".chart-readout-value").all_text_contents() == payload["display"][-1]
                    page.emulate_media(media="print")
                    assert page.locator(".chart-canvas").evaluate("el => getComputedStyle(el).display") == "none"
                    assert page.locator("svg.chart").first.evaluate("el => getComputedStyle(el).opacity") == "1"
                    assert page.locator(".table-details tbody").bounding_box()["height"] > 0
                    if route == "/graficos/biblioteca":
                        assert page.locator(".authored-note").is_visible()
                    page.emulate_media(media="screen")
                    if route.startswith("/series/"):
                        page.get_by_role("link", name="Intervalo e ações", exact=True).click()
                        assert page.locator(".analytical-options").get_attribute("open") is not None
                        assert page.locator(".analytical-options .windows").is_visible()
                assert not errors
                context.close()
            nojs = browser.new_context(java_script_enabled=False)
            page = nojs.new_page()
            for route in ROUTES:
                page.goto(analytical_origin + route)
                assert page.locator("svg.chart").is_visible()
                assert not page.locator(".chart-canvas canvas").count()
                if route.startswith("/series/"):
                    page.get_by_role("link", name="Intervalo e ações", exact=True).click()
                    assert page.locator(".analytical-options .windows").is_visible()
            nojs.close()
        finally:
            browser.close()
