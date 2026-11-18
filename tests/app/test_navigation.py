"""The public navigation contract: exact, nested, theme and mount-prefix states.

The model is tested without templates; the rendered checks exercise a real public
request. The goldens under `golden/` stay historical captures of the old chrome.
"""
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.navigation import build_navigation

HEADER = re.compile(r"<header class=\"site-header\">.*?</header>", re.S)
CSS = Path(__file__).resolve().parents[2] / "static" / "css" / "prumo.css"


def _attrs(html: str, href: str) -> str:
    match = re.search(rf'<a href="{re.escape(href)}"([^>]*)>', html)
    assert match, href
    return match.group(1)


def test_exact_destination_is_a_current_page():
    nav = build_navigation("/comparar", "")
    assert nav.home.current == ""
    assert [link.current for link in nav.sections] == ["page", "", ""]
    assert nav.compact_current == "Comparações"


def test_nested_section_is_a_location_and_never_a_current_home():
    nav = build_navigation("/comparar/inflacao-e-desemprego", "")
    compare = next(link for link in nav.sections if link.label == "Comparações")
    assert compare.current == "location"
    assert not compare.is_current
    assert nav.home.current == ""
    assert all(link.current == "" for link in (*nav.themes.links, *nav.support.links))
    assert nav.compact_current == "Comparações"


def test_theme_disclosure_names_the_current_theme_and_marks_only_its_child():
    nav = build_navigation("/temas/economy", "")
    assert nav.themes.current_label == "Economia"
    assert nav.themes.current
    assert [link.current for link in nav.themes.links] == ["page", "", ""]
    assert nav.compact_current == "Economia"
    assert nav.home.current == ""


def test_nested_theme_route_keeps_honest_section_context():
    nav = build_navigation("/temas/energy/2026", "")
    assert nav.themes.current_label == "Energia"
    assert nav.themes.state == "location"
    assert [link.current for link in nav.themes.links] == ["", "", "location"]
    assert nav.compact_current == "Energia"


def test_support_link_is_current_without_claiming_the_home():
    nav = build_navigation("/fontes", "")
    fontes = next(link for link in nav.support.links if link.label == "Fontes")
    assert fontes.current == "page"
    assert nav.support.current_label == "Fontes"
    assert nav.home.current == ""
    assert nav.compact_current == "Fontes"


def test_unknown_route_has_no_false_current_destination():
    nav = build_navigation("/series/ine.hicp_yoy.PT", "")
    assert nav.home.current == ""
    assert nav.themes.current_label == ""
    assert nav.support.current_label == ""
    assert nav.compact_current == ""
    assert all(link.current == "" for link in nav.destinations)


def test_prefix_is_joined_once_and_a_trailing_slash_is_the_same_destination():
    nav = build_navigation("/comparar/", "/dados")
    assert nav.home.href == "/dados/"
    assert nav.search_href == "/dados/pesquisa"
    assert next(link for link in nav.sections if link.label == "Comparações").current == "page"
    assert all(link.href.startswith("/dados/") for link in nav.destinations)
    assert "/dados/dados" not in repr(nav)


def test_rendered_exact_and_nested_sections_use_page_and_location(client):
    exact = client.get("/comparar").text
    assert 'aria-current="page"' in _attrs(exact, "/comparar")
    nested = client.get("/comparar/inflacao-e-desemprego").text
    assert 'aria-current="location"' in _attrs(nested, "/comparar")
    assert "aria-current" not in _attrs(nested, "/")
    assert "aria-current" not in _attrs(nested, "/caderno")
    assert "aria-current" not in _attrs(nested, "/temas/economy")


def test_the_current_theme_stays_visible_in_the_closed_disclosure(client):
    html = client.get("/temas/demography").text
    match = HEADER.search(html)
    assert match
    header = match.group(0)
    assert '<details class="nav-disclosure" data-state="page">' in header
    assert '<span class="nav-disclosure-current">Demografia</span>' in header
    assert '<span class="nav-menu-current">Demografia</span>' in header
    assert 'aria-current="page">Demografia</a>' in header
    assert "aria-current" not in _attrs(header, "/temas/economy")
    assert "aria-current" not in _attrs(header, "/")


def test_every_destination_is_discoverable_in_desktop_and_compact_nav(client):
    html = client.get("/").text
    hrefs = {"/", "/temas/economy", "/temas/demography", "/temas/energy", "/comparar",
             "/caderno", "/paginas", "/fontes", "/metodologia"}
    for href in hrefs:
        assert html.count(f'href="{href}"') >= 2, href
    assert '<details class="nav-menu">' in html
    assert 'aria-label="Secções no telemóvel"' in html


def test_native_menu_and_search_need_no_script(client):
    html = client.get("/").text
    assert '<form class="search" action="/pesquisa" method="get" role="search">' in html
    assert '<button type="submit">Procurar</button>' in html
    assert 'name="q"' in html
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()


def test_forwarded_prefix_root_path_and_real_mount_render_the_same_mounted_chrome(site_path):
    with TestClient(create_app(str(site_path))) as client:
        forwarded = client.get("/comparar", headers={"X-Forwarded-Prefix": "/dados"}).text
    with TestClient(create_app(str(site_path)), root_path="/dados") as rooted:
        root_path_html = rooted.get("/comparar").text
    outer = FastAPI()
    outer.mount("/dados", create_app(str(site_path)))
    with TestClient(outer) as mounted:
        mounted_html = mounted.get("/dados/comparar").text

    for html in (forwarded, root_path_html, mounted_html):
        match = HEADER.search(html)
        assert match
        header = match.group(0)
        assert 'href="/dados/"' in header
        assert 'href="/dados/temas/economy"' in header
        assert 'href="/dados/comparar"' in header
        assert 'action="/dados/pesquisa"' in header
        assert 'href="/dados/static/css/prumo.css"' in html
        assert "/dados/dados" not in html
        assert 'aria-current="page"' in _attrs(header, "/dados/comparar")


def test_last_disclosure_panel_is_anchored_to_the_rail_edge():
    css = CSS.read_text(encoding="utf-8")
    # The last rail disclosure sits near the viewport edge; its 16rem panel must
    # open leftwards instead of crossing the 901-1100px desktop widths.
    assert ".site-nav > .nav-disclosure:last-child > .nav-disclosure-panel" in css
    assert "left: auto; right: 0;" in css


def test_responsive_wrap_padding_preserves_masthead_and_rail_block_padding():
    css = CSS.read_text(encoding="utf-8")
    # `.wrap` also carries the masthead and destination rail. A shorthand in a
    # narrow media query silently resets their vertical padding, so only the
    # inline axis may change at each breakpoint.
    assert ".wrap { padding: 0 24px; }" not in css
    assert ".wrap { padding: 0 18px; }" not in css
    assert ".wrap { padding-inline: 24px; }" in css
    assert ".wrap { padding-inline: 18px; }" in css
    assert ".masthead" in css and "padding-top: 12px; padding-bottom: 12px;" in css
