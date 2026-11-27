"""The public navigation contract: task entries, exact, nested, theme and mount states.

The model is tested without templates; the rendered checks exercise a real public
request. The goldens under `golden/` stay historical captures of the old chrome.
"""
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.navigation import build_navigation, legacy_links
from tests.app.conftest import HICP

HEADER = re.compile(r"<header class=\"site-header\">.*?</header>", re.S)
CSS = Path(__file__).resolve().parents[2] / "static" / "css" / "prumo.css"
SHELL = Path(__file__).resolve().parents[2] / "static" / "css" / "app-shell.css"


def _attrs(html: str, href: str) -> str:
    match = re.search(rf'<a [^>]*href="{re.escape(href)}"([^>]*)>', html)
    assert match, href
    return match.group(1)


def _header(html: str) -> str:
    match = HEADER.search(html)
    assert match
    return match.group(0)


def test_exact_destination_is_a_current_page():
    nav = build_navigation("/comparar", "")
    assert nav.home.current == ""
    assert [link.current for link in nav.sections] == ["page", ""]
    assert nav.compact_current == "Comparações"
    assert not nav.more.state


def test_primary_tasks_are_direct_and_secondary_destinations_move_to_more():
    nav = build_navigation("/", "")
    assert [link.label for link in nav.primary] == [
        "Catálogo", "Comparações", "Caderno"]
    assert [link.icon for link in nav.primary] == ["list", "chart", "notebook"]
    assert [link.compact_label for link in nav.primary] == ["", "Comparar", ""]
    assert nav.catalogue.href == "/pesquisa"
    assert [link.label for link in nav.sections] == ["Comparações", "Caderno"]
    assert [link.label for link in nav.support.links] == [
        "Páginas", "Fontes", "Metodologia"]
    # One More disclosure owns both themes and support, with one resolved state.
    assert nav.more.label == "Mais"
    assert [link.label for link in nav.more.links] == [
        "Economia", "Demografia", "Energia", "Páginas", "Fontes", "Metodologia"]
    assert not nav.more.state
    # The old `explore` and `themes` views remain readable by existing callers.
    assert nav.themes.links == nav.explore.links[1:]


def test_catalogue_is_a_page_only_at_its_exact_address_and_a_location_below_it():
    exact = build_navigation("/pesquisa", "")
    assert exact.catalogue.current == "page"
    assert exact.catalogue.is_current
    assert exact.explore.state == "page"
    assert exact.explore.current_label == "Catálogo"
    assert exact.compact_current == "Catálogo"

    nested = build_navigation("/pesquisa/series/calculadas", "")
    assert nested.catalogue.current == "location"
    assert not nested.catalogue.is_current
    assert nested.explore.state == "location"
    assert nested.home.current == ""
    assert all(link.current == "" for link in (*nested.themes.links, *nested.sections))
    assert nested.compact_current == "Catálogo"


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
    assert nav.explore.current_label == "Economia"
    assert [link.current for link in nav.themes.links] == ["page", "", ""]
    assert nav.compact_current == "Economia"
    assert nav.home.current == ""


def test_nested_theme_route_keeps_honest_section_context():
    nav = build_navigation("/temas/energy/2026", "")
    assert nav.themes.current_label == "Energia"
    assert nav.themes.state == "location"
    assert [link.current for link in nav.themes.links] == ["", "", "location"]
    assert nav.explore.state == "location"
    assert nav.more.state == "location"
    assert nav.more.current_label == "Energia"
    assert nav.compact_current == "Energia"


def test_support_link_is_current_without_claiming_the_home():
    nav = build_navigation("/fontes", "")
    fontes = next(link for link in nav.support.links if link.label == "Fontes")
    assert fontes.current == "page"
    assert nav.support.current_label == "Fontes"
    assert nav.support.state == "page"
    assert nav.home.current == ""
    assert nav.compact_current == "Fontes"
    assert nav.more.current_label == "Fontes"
    assert nav.more.state == "page"


def test_unknown_route_has_no_false_current_destination():
    nav = build_navigation("/series/ine.hicp_yoy.PT", "")
    assert nav.home.current == ""
    assert nav.explore.current_label == ""
    assert nav.themes.current_label == ""
    assert nav.support.current_label == ""
    assert nav.compact_current == ""
    assert all(link.current == "" for link in nav.destinations)


def test_task_pages_do_not_repeat_the_global_search_above_their_own():
    assert not build_navigation("/pesquisa", "").show_search
    assert not build_navigation("/pesquisa/series/calculadas", "").show_search
    assert not build_navigation("/caderno", "").show_search
    assert build_navigation("/", "").show_search
    assert build_navigation("/temas/economy", "").show_search


def test_prefix_is_joined_once_and_a_trailing_slash_is_the_same_destination():
    nav = build_navigation("/comparar/", "/dados")
    assert nav.home.href == "/dados/"
    assert nav.search_href == "/dados/pesquisa"
    assert nav.catalogue.href == "/dados/pesquisa"
    assert next(link for link in nav.sections if link.label == "Comparações").current == "page"
    assert all(link.href.startswith("/dados/") for link in nav.destinations)
    assert "/dados/dados" not in repr(nav)


def test_legacy_flat_links_keep_their_pair_shape_for_the_preview_caller():
    assert legacy_links() == (
        ("/", "Início"), ("/pesquisa", "Catálogo"),
        ("/temas/economy", "Economia"), ("/temas/demography", "Demografia"),
        ("/temas/energy", "Energia"), ("/comparar", "Comparações"),
        ("/caderno", "Caderno"), ("/paginas", "Páginas"), ("/fontes", "Fontes"),
        ("/metodologia", "Metodologia"),
    )


def test_rendered_exact_and_nested_sections_use_page_and_location(client):
    exact = client.get("/comparar").text
    assert 'aria-current="page"' in _attrs(exact, "/comparar")
    nested = client.get("/comparar/inflacao-e-desemprego").text
    assert 'aria-current="location"' in _attrs(nested, "/comparar")
    assert "aria-current" not in _attrs(nested, "/")
    assert "aria-current" not in _attrs(nested, "/caderno")
    assert "aria-current" not in _attrs(nested, "/temas/economy")


def test_nested_catalogue_route_never_claims_the_catalogue_page_itself(client):
    html = client.get("/pesquisa/series/calculadas").text  # the shared 404 shell
    header = _header(html)
    assert 'aria-current="location"' in _attrs(header, "/pesquisa")
    assert 'aria-current="page"' not in _attrs(header, "/pesquisa")
    assert '<details class="app-disclosure app-more">' in header


def test_the_current_theme_is_marked_on_the_more_disclosure(client):
    header = _header(client.get("/temas/demography").text)
    assert '<details class="app-disclosure app-more" data-state="page">' in header
    assert '<span class="app-disclosure-label">Mais</span>' in header
    assert '<span class="sr-only">: Demografia</span>' in header
    assert 'aria-current="page">Demografia</a>' in header
    assert "aria-current" not in _attrs(header, "/temas/economy")
    assert "aria-current" not in _attrs(header, "/")


def test_supporting_page_marks_the_more_disclosure_without_hiding_its_label(client):
    header = _header(client.get("/fontes").text)
    assert '<details class="app-disclosure app-more" data-state="page">' in header
    assert '<span class="app-disclosure-label">Mais</span>' in header
    assert 'aria-current="page">Fontes</a>' in header
    assert '<span class="sr-only">: Fontes</span>' in header


def test_every_destination_is_discoverable_once_in_the_shared_nav(client):
    html = client.get("/").text
    header = html[:html.index('<main id="conteudo"')]
    hrefs = {"/", "/pesquisa", "/temas/economy", "/temas/demography", "/temas/energy",
             "/comparar", "/caderno", "/paginas", "/fontes", "/metodologia"}
    for href in hrefs:
        assert header.count(f'href="{href}"') == 1, href
    assert '<nav class="site-nav nav" aria-label="Secções">' in header
    assert '<details class="app-disclosure app-more">' in header
    assert '<form class="search app-search"' in header
    assert '<details class="nav-menu">' not in header
    assert header.count('href="/pesquisa"') == 1


def test_native_menu_and_search_need_no_script(client):
    html = client.get("/").text
    assert '<details class="app-disclosure app-more">' in html
    assert '<form class="search app-search" action="/pesquisa" method="get" role="search">' in html
    assert '>Procurar</button>' in html
    assert 'name="q"' in html
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()


def test_task_pages_suppress_the_global_search_and_keep_their_own(client):
    for path in ("/pesquisa", "/pesquisa?q=desemprego", "/pesquisa/series/calculadas"):
        assert '<form class="search"' not in client.get(path).text, path
        assert '<details class="app-disclosure app-search">' not in client.get(path).text, path
    notebook = client.get(f"/caderno?s={HICP}").text
    assert '<form class="search app-search"' not in notebook
    assert '<form id="notebook-search-form"' in notebook
    add_link = re.search(
        rf'<a class="btn btn-primary" href="/pesquisa\?s={re.escape(HICP)}" '
        r'aria-label="Acrescentar séries">(.*?)</a>', notebook, re.S)
    assert add_link is not None
    assert 'class="ui-icon"' in add_link.group(1)
    assert add_link.group(1).endswith("Acrescentar")


def test_discovery_stylesheet_is_unconditional_and_mount_aware(client):
    for path in ("/", "/pesquisa", "/caderno", f"/series/{HICP}"):
        assert '<link rel="stylesheet" href="/static/css/discovery.css">' in client.get(path).text
    prefixed = client.get("/", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert '<link rel="stylesheet" href="/dados/static/css/discovery.css">' in prefixed


def test_footer_keeps_the_admin_entry_discoverable(client):
    html = client.get("/").text
    assert '<a href="https://joao.date/dados/admin/">Admin</a>' in html


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
        header = _header(html)
        assert 'href="/dados/"' in header
        assert 'href="/dados/temas/economy"' in header
        assert 'href="/dados/pesquisa"' in header
        assert 'href="/dados/comparar"' in header
        assert 'action="/dados/pesquisa"' in header
        assert 'href="/dados/static/css/prumo.css"' in html
        assert 'href="/dados/static/css/app-shell.css"' in html
        assert 'href="/dados/static/css/discovery.css"' in html
        assert "/dados/dados" not in html
        assert 'aria-current="page"' in _attrs(header, "/dados/comparar")


def test_narrow_grid_uses_the_short_visible_label_without_renaming_the_link(client):
    header = _header(client.get("/comparar").text)
    assert '<span class="app-nav-label app-nav-label-wide">Comparações</span>' in header
    assert '<span class="app-nav-label app-nav-label-narrow">Comparar</span>' in header
    shell = SHELL.read_text(encoding="utf-8")
    assert ".app-nav-label-narrow { display: none; }" in shell
    assert ".app-nav-label-wide { display: none; }" in shell


def test_each_disclosure_panel_is_anchored_inside_the_viewport():
    shell = SHELL.read_text(encoding="utf-8")
    # Desktop panels open below their trigger, anchored to its right edge; the narrow
    # layout returns the same panel to normal flow instead of covering the page.
    assert ".app-panel {" in shell
    assert "right: 0;" in shell
    assert "position: static;" in shell
    assert ".app-disclosure:not([open]) > .app-panel { display: none; }" in shell


def test_responsive_wrap_padding_preserves_header_block_padding():
    css = CSS.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    # `.wrap` also carries the masthead. A shorthand in a narrow media query silently
    # resets its vertical padding, so only the inline axis may change at each breakpoint.
    assert ".wrap { padding: 0 24px; }" not in css
    assert ".wrap { padding: 0 18px; }" not in css
    assert ".wrap { padding-inline: 20px; }" in css
    assert ".wrap { padding-inline: 16px; }" in css
    assert ".masthead" in shell and "padding-block: 6px;" in shell
    assert ".masthead" in shell and "padding-block: 2px;" in shell
