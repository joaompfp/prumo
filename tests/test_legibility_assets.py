"""Presentation regression pins for the 2026-11-17 legibility pass.

These checks are static and fast: they pin the local licensed font assets, the two root
sizes, the minimum role tokens and the long-value wrapping rule. Real rendered geometry is
covered by the browser acceptance run, not here.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "static" / "fonts" / "prumo"


def _manifest():
    return json.loads((FONT_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


def test_local_font_subsets_match_their_bytes_and_manifest():
    manifest = _manifest()
    assert set(manifest["files"]) == {
        "lato-regular.woff2", "lato-semibold.woff2", "lato-bold.woff2",
        "schola-regular.woff2", "schola-bold.woff2",
    }
    for name, expected in manifest["files"].items():
        body = (FONT_DIR / name).read_bytes()
        assert body.startswith(b"wOF2"), name
        assert len(body) == expected["bytes"], name
        assert hashlib.sha256(body).hexdigest() == expected["sha256"], name


def test_font_licences_are_shipped_with_the_subsets():
    assert "SIL Open Font License 1.1" in (FONT_DIR / "OFL-1.1.txt").read_text()
    assert "GUST Font License" in (FONT_DIR / "GUST-FONT-LICENSE.txt").read_text()
    assert "Reproducible generation" in (FONT_DIR / "README.md").read_text()


def test_font_stylesheet_is_local_and_covers_regular_semibold_bold():
    css = (ROOT / "static" / "css" / "fonts.css").read_text()
    assert '@font-face' in css
    assert "http" not in css and "cdn" not in css
    for name in ("lato-regular.woff2", "lato-semibold.woff2", "lato-bold.woff2",
                 "schola-regular.woff2", "schola-bold.woff2"):
        assert f"../fonts/prumo/{name}" in css, name
    assert css.count('font-family: "Lato"') == 3
    assert css.count('font-family: "TeX Gyre Schola"') == 2


def test_public_root_and_wrap_support_the_approved_scale():
    css = (ROOT / "static" / "css" / "prumo.css").read_text()
    assert "html { font-size: 28.05px; }" in css
    assert "--wrap: 1240px;" in css
    assert '--sans: "Lato",' in css
    assert '--serif: "TeX Gyre Schola",' in css
    assert ".card-value--long { font-size: 2.1rem;" in css
    # The four-card grid recomposes to 3/2/1 rather than shrinking the text.
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert ".cards, .themes { grid-template-columns: 1fr; }" in css


def test_public_fixed_role_tokens_meet_the_one_and_a_half_floor():
    css = (ROOT / "static" / "css" / "prumo.css").read_text()
    for token in (
        ".site-nav > a {", "font-size: 0.95rem",        # grouped nav 26.6475px
        ".card-label {", "font-size: .8rem",            # 22.44px
        ".card-source {", "font-size: .78rem",          # 21.879px
        ".data-table th {", "font-size: .74rem",        # 20.757px
        ".figure-meta {", "font-size: .82rem",          # 23.001px
        ".site-footer p {", "font-size: .82rem",        # 23.001px
    ):
        assert token in css, token
    # SVG unit names use .chart-axis-label at 18.15px; .chart-axis-title at 19.8px has no
    # consumer. The canvas adapter draws its axis names at 19.8 CSS px.
    assert css.count("font-size: 18.15px") == 2           # SVG ticks and axis unit names
    assert css.count("font-size: 19.8px") == 2            # last-value labels, unused axis title
    assert "min-width: 660px; min-height: 264px;" in css
    assert ".chart-enhanced .chart-wrap { min-width: 0; }" in css


def test_admin_root_sidebar_and_record_stack_follow_the_approved_scale():
    css = (ROOT / "static" / "css" / "admin.css").read_text()
    assert "html { font-size: 26.4px; }" in css
    assert "font: 400 0.875rem/1.5 var(--sans);" in css    # 23.1px body
    assert "--sidebar: 330px;" in css
    assert ".cms-table > tbody > tr > td::before" in css
    assert "content: attr(data-label)" in css
    assert ".bo-menu { display: block; }" in css
    assert ".nav-desktop { display: none; }" in css
    assert "font-size: 0.65rem" in css                     # table th, 17.16px
    assert "font-size: 0.58rem" in css                     # legacy badge, 15.312px


def test_card_value_turns_group_spaces_into_wrappable_spaces_only():
    template = (ROOT / "app" / "templates" / "_card.html").read_text()
    assert "card.value_display | replace('\\u00a0', ' ')" in template
    assert "card.derived_value_display | replace('\\u00a0', ' ')" in template
