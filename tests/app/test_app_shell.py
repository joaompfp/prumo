"""Focused contract checks for the shared public app shell and action roles."""
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "app" / "templates"
SHELL = ROOT / "static" / "css" / "app-shell.css"
PRUMO = ROOT / "static" / "css" / "prumo.css"
HEADER = re.compile(r"<header class=\"site-header\">.*?</header>", re.S)

# These names are the shared vocabulary promised to the notebook and settings work.
ICON_NAMES = (
    "plus", "settings", "share", "trash", "search", "filter", "chart", "notebook",
    "table", "info", "chevron", "home", "list", "close",
)


def _icon(name: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    return str(env.get_template("_ui.html").module.icon(name))


def _header(html: str) -> str:
    match = HEADER.search(html)
    assert match
    return match.group(0)


def test_ui_icon_macro_covers_every_shell_name_with_safe_inline_svg():
    for name in ICON_NAMES:
        markup = _icon(name)
        assert markup.count("<svg") == 1 and markup.endswith("</svg>"), name
        assert 'class="ui-icon"' in markup, name
        assert 'aria-hidden="true"' in markup, name
        assert 'focusable="false"' in markup, name
        assert 'stroke="currentColor"' in markup, name
        assert "<script" not in markup.lower(), name
        assert "onclick" not in markup.lower(), name
        assert "href=" not in markup.lower(), name
        assert "<path" in markup or "<circle" in markup or "<rect" in markup, name


def test_header_has_one_direct_primary_rail_with_visible_icons_and_labels(client):
    header = _header(client.get("/").text)
    assert header.count('<nav class="site-nav" aria-label="Secções">') == 1
    assert '<details class="nav-menu">' not in header
    assert 'aria-label="Secções no telemóvel"' not in header
    assert [header.count(f">{label}</span>")
            for label in ("Catálogo", "Comparações", "Caderno")] == [1, 1, 1]
    assert header.count('class="app-nav-link"') == 3
    for label in ("Catálogo", "Comparações", "Caderno"):
        start = header.index(f">{label}</span>")
        start = header.rfind("<a ", 0, start)
        assert '<svg class="ui-icon"' in header[start:start + 500], label
    assert header.count('href="/pesquisa"') == 1
    assert header.count('href="/comparar"') == 1
    assert header.count('href="/caderno"') == 1
    assert 'aria-label="Comparar"' not in header


def test_header_current_state_comes_from_the_navigation_model(client):
    home = _header(client.get("/").text)
    assert 'href="/" class="brand" aria-current="page"' in home
    compare = _header(client.get("/comparar").text)
    assert 'href="/comparar" class="app-nav-link" aria-current="page"' in compare
    nested = _header(client.get("/comparar/inflacao-e-desemprego").text)
    assert 'href="/comparar" class="app-nav-link" aria-current="location"' in nested
    catalogue = _header(client.get("/pesquisa").text)
    assert 'href="/pesquisa" class="app-nav-link" aria-current="page"' in catalogue


def test_more_disclosure_groups_themes_and_support_with_one_current_marker(client):
    home = _header(client.get("/").text)
    assert '<details class="app-disclosure app-more">' in home
    assert '<p class="app-panel-title">Temas</p>' in home
    assert '<p class="app-panel-title">Sobre</p>' in home
    for href in ("/temas/economy", "/temas/demography", "/temas/energy",
                 "/paginas", "/fontes", "/metodologia"):
        assert home.count(f'href="{href}"') == 1, href
    theme = _header(client.get("/temas/demography").text)
    assert '<details class="app-disclosure app-more" data-state="page">' in theme
    assert '<span class="sr-only">: Demografia</span>' in theme
    assert 'aria-current="page">Demografia</a>' in theme
    assert '<details class="app-disclosure app-more" data-state="page">' in \
        _header(client.get("/fontes").text)
    assert '<details class="app-disclosure app-more" data-state="page">' in \
        _header(client.get("/metodologia").text)


def test_global_search_is_one_native_labeled_disclosure_and_stays_off_task_pages(client):
    home = client.get("/").text
    assert '<details class="app-disclosure app-more">' in home
    assert '<p class="app-panel-title">Pesquisar séries</p>' in home
    assert home.count('class="search"') == 1
    assert home.count('id="q"') == 1
    assert home.count('name="q"') == 1
    for path in ("/pesquisa", "/pesquisa/series/calculadas", "/caderno"):
        body = client.get(path).text
        assert '<form class="search"' not in body, path
        assert '<details class="app-disclosure app-search">' not in body, path
        assert 'id="q"' not in body, path


def test_search_icon_is_local_and_the_visible_submit_label_remains(client):
    css = client.get("/static/css/app-shell.css").text
    assert ".search button::before" in css and "data:image/svg+xml" in css
    assert "cdn." not in css and "googleapis" not in css
    assert '<button type="submit">Procurar</button>' in client.get("/").text


def test_app_shell_stylesheet_is_served_and_ordered_after_prumo(client):
    html = client.get("/").text
    assert html.index("/static/css/prumo.css") < html.index("/static/css/app-shell.css")
    assert html.index("/static/css/app-shell.css") < html.index(
        "/static/css/chart-inspector.css")
    assert html.index("/static/css/app-shell.css") < html.index(
        "/static/css/discovery.css")
    css = client.get("/static/css/app-shell.css")
    assert css.status_code == 200
    assert "@import" not in css.text
    assert "url(http" not in css.text
    prefixed = client.get("/", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert "/dados/static/css/app-shell.css" in prefixed


def test_prumo_no_longer_owns_the_shared_navigation_or_action_rules():
    prumo = PRUMO.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    for stale in (".masthead", ".destination-rail", ".nav-menu", ".nav-disclosure",
                  ".site-nav > a", ".button, .button-quiet", ".search button::before",
                  ".nav-compact-group"):
        assert stale not in prumo, stale
    assert ".app-nav-link" in shell
    assert ".site-nav {" in shell and "display: flex;" in shell
    assert ".app-disclosure > summary" in shell
    assert ".button, .button-quiet, .button-danger" in shell


def test_action_roles_are_distinct_and_keep_the_approved_control_size():
    shell = SHELL.read_text(encoding="utf-8")
    assert ".button { background: var(--accent); border-color: var(--accent); color: #fff; }" in shell
    assert ".button-quiet { background: var(--surface); border-color: var(--rule-strong); color: var(--ink); }" in shell
    assert ".button-danger { background: var(--surface); border-color: var(--accent); color: var(--accent); }" in shell
    assert ".button-link {" in shell and "text-decoration: underline;" in shell
    assert "min-height: 54px;" in shell
    assert "padding: 13px 22px;" in shell
    assert "font-size: 0.9rem;" in shell
    assert ".button-danger:hover { background: var(--accent);" in shell


def test_narrow_primary_nav_is_a_three_cell_grid_with_the_reading_scale():
    shell = SHELL.read_text(encoding="utf-8")
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in shell
    assert "font-size: 0.95rem;" in shell
    assert ".app-nav-link .ui-icon { width: 20px; height: 20px; }" in shell
    assert ".app-nav-label-wide { display: none; }" in shell
    assert ".site-nav { display: none; }" not in shell
    assert ".app-nav-label { display: none; }" not in shell


def test_intermediate_bar_stacks_the_rail_before_it_can_overrun_utilities():
    shell = SHELL.read_text(encoding="utf-8")
    assert "@media (max-width: 1120px)" in shell
    assert 'grid-template-areas: "brand utilities" "nav nav";' in shell
    assert ".site-nav { display: none; }" not in shell


def test_mobile_panels_are_in_flow_and_no_fixed_bar_covers_content():
    shell = SHELL.read_text(encoding="utf-8")
    assert "@media (max-width: 900px)" in shell
    assert "position: static;" in shell
    assert "position: fixed" not in shell
    assert "position: sticky" not in shell
    assert "bottom: 0" not in shell
    assert ".app-disclosure:not([open]) > .app-panel { display: none; }" in shell
