"""The 10 percent typography increment: roots, clamps and chart label roles move together.

The approved legibility release set the public root at 25.5px (body 25.5px) and the Admin
root at 24px (`.875rem` body 21px). The owner asked for a further modest increase. These
static pins follow each functional text role to 28.05px / 26.4px and assert that fixed SVG
and canvas chart labels, their margins and the narrow-chart floor grew with the same scale,
so no role stays at the previous size by accident. Rendered geometry is covered by the
browser acceptance run, not here.
"""
import re
from pathlib import Path

import pytest

from app import chart_model

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "static" / "css"
ADAPTER = ROOT / "tools" / "charts" / "src" / "adapter.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _root_px(css: str) -> float:
    match = re.search(r"html \{ font-size: ([\d.]+)px; \}", css)
    assert match, "root size declaration"
    return float(match.group(1))


def test_public_and_admin_roots_grow_by_ten_percent():
    public = _read(CSS / "prumo.css")
    admin = _read(CSS / "admin.css")
    assert _root_px(public) == pytest.approx(25.5 * 1.10)
    assert _root_px(admin) == pytest.approx(24 * 1.10)
    # The body role stays a rem token so it follows the root: 23.1px in Admin.
    assert "font: 400 0.875rem/1.5 var(--sans);" in admin
    assert _root_px(admin) * 0.875 == pytest.approx(23.1)


def test_clamp_preferred_sizes_track_the_ten_percent_increase():
    public = _read(CSS / "prumo.css")
    admin = _read(CSS / "admin.css")
    assert "clamp(2.1rem, 7.6vw, 3.3rem)" in public
    assert "clamp(1.35rem, 4vw, 1.75rem)" in public
    assert "clamp(2.4rem, 8.25vw, 3.2rem)" in public
    assert "clamp(1.5rem, 3.63vw, 1.9rem)" in admin
    assert "clamp(1.25rem, 3.3vw, 1.55rem)" in admin


def test_fixed_svg_and_canvas_labels_use_the_new_type_role():
    css = _read(CSS / "prumo.css")
    adapter = _read(ADAPTER)
    assert css.count("font-size: 18.15px") == 2   # x/y ticks and axis unit names
    assert css.count("font-size: 19.8px") == 2    # axis title and last-value labels
    assert adapter.count("fontSize: 18.15") == 2  # ECharts axis labels
    assert adapter.count("fontSize: 19.8") == 2   # axis names and tooltip text
    assert "lineHeight: 29.7" in adapter
    for stale in ("fontSize: 16.5", "fontSize: 18,", "lineHeight: 27"):
        assert stale not in adapter, stale


def test_chart_gutters_and_adapter_grid_share_the_scaled_geometry():
    adapter = _read(ADAPTER)
    # The SVG model and the canvas overlay must keep the same plot box and label gutters.
    assert (chart_model.LEFT, chart_model.RIGHT, chart_model.TOP, chart_model.BOTTOM) == \
        (97, 33, 31, 68)
    assert chart_model.RIGHT_DUAL == 172
    for token in (
        f"const right = payload.axes.length > 1 ? {chart_model.RIGHT_DUAL} : "
        f"{chart_model.RIGHT};",
        f"left: {chart_model.LEFT} * scale,",
        "right: right * scale,",
        f"top: {chart_model.TOP} * scale,",
        f"bottom: {chart_model.BOTTOM} * scale,",
        "nameGap: 13 * scale,",
    ):
        assert token in adapter, token


def test_narrow_chart_floor_keeps_the_rendered_label_size():
    css = _read(CSS / "prumo.css")
    assert "min-width: 660px; min-height: 264px;" in css
    assert ".chart-enhanced .chart-wrap { min-width: 0; }" in css


def test_authored_css_has_no_fixed_text_size_below_the_axis_tick_role():
    sizes = [float(value) for value in re.findall(
        r"font-size:\s*([\d.]+)px", _read(CSS / "prumo.css") + _read(CSS / "admin.css"))]
    assert sizes and min(sizes) >= 18.15
