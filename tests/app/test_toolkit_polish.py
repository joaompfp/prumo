"""Regressions caught by the independent component-cascade review."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "static" / "css"


def test_native_anchor_and_form_focus_do_not_inherit_animated_document_scroll():
    css = (CSS / "prumo.css").read_text()
    assert "scroll-behavior: auto;" in css.split("* { box-sizing", 1)[0]


def test_evidence_headings_do_not_inherit_larger_bootstrap_reboot_sizes():
    css = (CSS / "prumo.css").read_text()
    assert "h4, h5, h6 { font-family: var(--sans); font-weight: 700;" in css
    for heading, size in (("h4", "1rem"), ("h5", "0.9rem"), ("h6", "0.8rem")):
        assert f"{heading} {{ font-size: {size}; }}" in css


def test_card_actions_share_left_alignment_and_keep_bootstrap_hit_area():
    css = (CSS / "prumo.css").read_text()
    assert ".card > .btn-link, .card-actions .btn-link { justify-content: flex-start; text-align: left; }" in css
    theme = (CSS / "bootstrap-theme.css").read_text()
    assert "min-height: 44px;" in theme


def test_support_section_retains_current_visual_context():
    css = (CSS / "app-shell.css").read_text()
    assert ".app-disclosure[data-state] > .app-disclosure-toggle { color: var(--accent); border-color: var(--accent); }" in css


def test_pagination_targets_and_print_follow_the_actual_component():
    theme = (CSS / "bootstrap-theme.css").read_text()
    assert ".page-link { min-height: 44px;" in theme
    css = (CSS / "workspace.css").read_text().split("@media print", 1)[1]
    assert ".pagination, .app-pagination" in css.split("display: none;", 1)[0]
    assert ".pager {" not in (CSS / "prumo.css").read_text()


def test_stacked_search_overrides_vendor_joined_corners_and_margin():
    css = (CSS / "app-shell.css").read_text()
    assert ".app-search > .input-group > .form-control:not(:last-child)" in css
    assert ".app-search > .input-group > .btn:not(:first-child)" in css
    assert "margin-left: 0 !important;" in css
