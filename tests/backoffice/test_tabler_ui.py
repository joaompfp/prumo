"""Tabler presentation contract for the backoffice.

The backoffice keeps its server-rendered forms and progressive admin.js. These checks pin
the visual layer: pinned local Tabler loads first, real Tabler controls replace the old
handcrafted ones, the CMS keeps its stacked narrow-screen records, and the palette keeps
semantic danger separate from the green primary.
"""
import re
from pathlib import Path

from tests.backoffice.test_cms_routes import ORIGIN, Env, page_create, page_form

ROOT = Path(__file__).resolve().parents[2]
TABLER = "/static/vendor/tabler/1.7.5/tabler.min.css"


def _stylesheets(html):
    return re.findall(r'<link rel="stylesheet" href="([^"]+)">', html)


def _control_tags(html):
    return re.findall(r"<(input|select|textarea)\b[^>]*>", html)


def _visible_controls(html):
    tags = re.findall(r"<(?:input|select|textarea)\b[^>]*>", html)
    return [tag for tag in tags if 'type="hidden"' not in tag]


def test_editor_publication_dates_are_readable_and_preserve_machine_time(tmp_path):
    from html import unescape

    env = Env(tmp_path)
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/publish", data={"version": "1", "note": "Publicar"},
                  headers=ORIGIN).status_code == 303
    html = c.get("/cms/page/precos").text
    match = re.search(r'<p class="editor-status">(.*?)</p>', html, re.S)
    assert match is not None
    status = match.group(1)
    assert "<time datetime=" in status
    assert "UTC</time>" in status
    visible = unescape(re.sub(r"<[^>]+>", " ", status))
    assert not re.search(r"\d{4}-\d{2}-\d{2}T", visible)
    assert re.search(r"\d{2}/\d{2}/\d{4}, \d{2}:\d{2} UTC", visible)


def test_small_neutral_badges_override_tabler_utility_colour():
    css = (ROOT / "static/css/admin.css").read_text()
    assert ".badge.bg-secondary-lt { color: var(--muted) !important; }" in css


def test_tabler_is_pinned_local_and_loads_before_prumo_styles(env):
    html = env.client().get("/").text
    links = _stylesheets(html)
    assert TABLER in links
    assert links.index(TABLER) < links.index("/static/css/admin.css")
    assert links.index("/static/css/admin.css") < links.index("/static/css/icons.css")
    assert "cdn" not in TABLER and "http" not in TABLER


def test_tabler_stays_under_the_validated_admin_mount(env):
    html = env.client().get("/series", headers={"X-Forwarded-Prefix": "/dados/admin"}).text
    links = _stylesheets(html)
    assert "/dados/admin" + TABLER in links
    assert "/dados/admin/static/css/admin.css" in links


def test_cms_dashboard_uses_tabler_cards_tables_buttons_and_controls(tmp_path):
    env = Env(tmp_path)
    c = env.client()
    assert page_create(c).status_code == 303
    html = c.get("/cms").text

    assert '<section class="card' in html or '<div class="card' in html
    assert 'class="table ' in html
    assert "btn btn-primary" in html
    assert "form-control" in html
    assert "form-select" in html
    assert 'class="button ' not in html and 'class="button"' not in html
    assert 'class="btn btn-primary"' in html


def test_editor_visible_controls_are_actual_tabler_components(tmp_path):
    env = Env(tmp_path)
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "Primeiro parágrafo."}]),
                  headers=ORIGIN).status_code == 303
    html = c.get("/cms/page/precos").text

    for tag in _visible_controls(html):
        if tag.startswith("<select"):
            assert re.search(r'class="[^"]*\bform-select\b', tag), tag
        elif 'type="checkbox"' in tag:
            assert re.search(r'class="[^"]*\bform-check-input\b', tag), tag
        else:
            assert re.search(r'class="[^"]*\bform-control\b', tag), tag

    for button in re.findall(r"<button\b[^>]*>", html):
        assert re.search(r'class="[^"]*\bbtn\b', button), button

    assert 'class="button ' not in html and 'class="button"' not in html
    assert re.search(r'class="[^"]*\bbtn-outline-danger\b', html)
    assert html.count('name="version"') >= 1
    assert "data-dirty-watch" in html and "data-block-type-select" in html


def test_cms_list_keeps_labelled_stacked_records_for_narrow_screens(tmp_path):
    env = Env(tmp_path)
    c = env.client()
    assert page_create(c).status_code == 303
    html = c.get("/cms").text
    table = re.search(r'<table class="[^"]*cms-table[^"]*"[^>]*>(.*?)</table>', html, re.S)
    assert table is not None
    cells = re.findall(r"<td\b[^>]*>", table.group(1))
    assert cells
    assert all("data-label=" in cell for cell in cells)

    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    assert ".cms-table thead" in css and "display: none" in css
    assert "td::before" in css and "attr(data-label)" in css


def test_block_summaries_lead_with_the_content_not_the_repeated_kind(tmp_path):
    env = Env(tmp_path)
    c = env.client()
    assert page_create(c).status_code == 303
    blocks = [{"type": "card", "series_id": "ine.hicp_yoy.PT",
               "label": "IHPC, variação homóloga"}]
    assert c.post("/cms/page/precos/save", data=page_form(1, blocks=blocks),
                  headers=ORIGIN).status_code == 303
    html = c.get("/cms/page/precos").text
    match = re.search(r'<summary class="block-summary">(.*?)</summary>', html, re.S)
    assert match is not None
    summary = match.group(1)
    assert "IHPC, variação homóloga" in summary
    assert summary.index("IHPC, variação homóloga") < summary.index("Cartão de série")


def test_the_generated_option_filter_is_a_tabler_control():
    js = (ROOT / "static/js/admin.js").read_text(encoding="utf-8")
    assert 'input.className = "select-filter form-control form-control-sm";' in js


def test_admin_css_overrides_tabler_with_the_prumo_palette_only():
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    for token in ("#f6f5f0", "#ffffff", "#18322f", "#1b514b", "#123d38",
                  "#52645f", "#dbe2dd", "#99672d"):
        assert token in css, token
    assert "--tblr-primary" in css
    assert "light-dark(" in css
    assert "prefers-color-scheme: dark" in css
    assert "linear-gradient" not in css and "radial-gradient" not in css
    assert "prefers-reduced-motion" in css

    # The old stylesheet redefined every native control. Tabler owns that layer now.
    assert not re.search(r"^input, select, textarea", css, re.M)
    assert not re.search(r"^button, \.button", css, re.M)
    assert ".button-primary" not in css
    assert ".button-danger" not in css


def test_danger_stays_semantic_and_distinct_from_primary():
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    danger = re.search(r"--danger:\s*([^;]+);", css)
    primary = re.search(r"--primary:\s*([^;]+);", css)
    assert danger is not None and primary is not None
    assert danger.group(1) != primary.group(1)
    assert re.fullmatch(r"#[0-9a-f]{6}", danger.group(1).strip())
