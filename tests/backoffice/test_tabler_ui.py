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
    # The public Bootstrap subset belongs to the public/CMS preview surface only.
    assert all("bootstrap-subset" not in link for link in links)
    assert all("bootstrap-theme" not in link for link in links)


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
    for token in ("#f6f4f1", "#ffffff", "#1c1b19", "#9b1c2e", "#7d1524",
                  "#5f5a53", "#ddd7cc", "#99672d"):
        assert token in css, token
    for retired in ("#f6f5f0", "#18322f", "#1b514b", "#123d38", "#52645f",
                    "#dbe2dd", "#b8c8c0", "#111714", "#18211f"):
        assert retired not in css, retired
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


def _luminance(value):
    value = value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045
              else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first, second):
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _light_dark(css, name):
    match = re.search(rf"--{name}:\s*light-dark\(([^,]+),\s*([^)]+)\);", css)
    assert match is not None, name
    return match.group(1).strip(), match.group(2).strip()


def test_danger_stays_semantic_and_distinct_from_primary():
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    danger = re.search(r"--danger:\s*([^;]+);", css)
    primary = re.search(r"--primary:\s*([^;]+);", css)
    assert danger is not None and primary is not None
    assert danger.group(1).strip() == "#c1121f"
    assert primary.group(1).strip() == "#9b1c2e"
    assert danger.group(1) != primary.group(1)
    assert re.fullmatch(r"#[0-9a-f]{6}", danger.group(1).strip())


def test_light_and_dark_primary_control_text_meet_aa_contrast():
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    paper_light, paper_dark = _light_dark(css, "paper")
    primary_light, primary_dark = _light_dark(css, "primary")
    fill_light, fill_dark = _light_dark(css, "primary-fill")
    soft_light, soft_dark = _light_dark(css, "primary-soft")
    danger_light, danger_dark = _light_dark(css, "danger")
    danger_soft_light, danger_soft_dark = _light_dark(css, "danger-soft")

    assert _contrast(primary_light, paper_light) >= 4.5
    assert _contrast(primary_dark, paper_dark) >= 4.5
    assert _contrast("#ffffff", fill_light) >= 4.5
    assert _contrast("#ffffff", fill_dark) >= 4.5
    assert _contrast(primary_light, soft_light) >= 4.5
    assert _contrast(primary_dark, soft_dark) >= 4.5
    assert _contrast(danger_light, danger_soft_light) >= 4.5
    assert _contrast(danger_dark, danger_soft_dark) >= 4.5
    assert "color-mix(in oklab, var(--primary) 65%, transparent)" in css

def test_keyboard_focus_on_tabler_controls_uses_solid_primary_outline():
    css = (ROOT / "static/css/admin.css").read_text(encoding="utf-8")
    generic = css.index(":focus-visible { outline: 2px solid var(--primary)")
    match = re.search(r"(\.form-control:focus-visible[^{}]*\{[^}]*\})", css)
    assert match is not None
    rule = match.group(1)
    for selector in (".form-control:focus-visible",
                     ".form-select:focus-visible",
                     ".form-check-input:focus-visible"):
        assert selector in rule
    # Must land after the bare :focus-visible rule so it wins the cascade.
    assert css.index(rule) > generic
    assert re.search(r"outline:\s*3px solid var\(--primary\)", rule)
    assert "color-mix" not in rule
    assert re.search(r"box-shadow:\s*none", rule)
    # No fade-in from a transparent ring: focus must paint at full contrast.
    assert re.search(r"transition:\s*none", rule)

    surface_light, surface_dark = _light_dark(css, "surface")
    primary_light, primary_dark = _light_dark(css, "primary")
    assert _contrast(primary_light, surface_light) >= 3
    assert _contrast(primary_dark, surface_dark) >= 3
