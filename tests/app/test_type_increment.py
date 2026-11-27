"""The public compact scale: smaller reading type, unchanged chart geometry and Admin.

The owner reviewed the installed 28.05px public release and asked for a more compact,
app-like surface. The public root is now 22px; Admin stays at 26.4px and the fixed SVG
and canvas chart labels keep their reviewed role and geometry. These static pins catch a
role that silently returns to the old public scale. Rendered geometry is covered by the
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


def test_public_root_is_compact_and_admin_is_unchanged():
    public = _read(CSS / "prumo.css")
    admin = _read(CSS / "admin.css")
    assert _root_px(public) == pytest.approx(22.0)
    assert _root_px(admin) == pytest.approx(26.4)
    # The body role stays a rem token so it follows each root: 23.1px in Admin.
    assert "font: 400 0.875rem/1.5 var(--sans);" in admin
    assert _root_px(admin) * 0.875 == pytest.approx(23.1)


def test_public_clamps_track_the_compact_scale():
    public = _read(CSS / "prumo.css")
    admin = _read(CSS / "admin.css")
    assert "clamp(1.65rem, 5.2vw, 2.35rem)" in public
    assert "clamp(1.2rem, 3.4vw, 1.55rem)" in public
    assert "clamp(2rem, 6.6vw, 2.7rem)" in public
    assert "clamp(1.5rem, 3.63vw, 1.9rem)" in admin
    assert "clamp(1.25rem, 3.3vw, 1.55rem)" in admin


def test_fixed_svg_and_canvas_labels_keep_their_reviewed_type():
    css = _read(CSS / "prumo.css")
    adapter = _read(ADAPTER)
    assert css.count("font-size: 18.15px") == 2   # x/y ticks and axis unit names
    assert css.count("font-size: 19.8px") == 2    # unused axis-title role and last-value labels
    assert adapter.count("fontSize: 18.15") == 2  # ECharts axis labels
    assert adapter.count("fontSize: 19.8") == 2   # axis names and tooltip text
    assert "lineHeight: 29.7" in adapter
    for stale in ("fontSize: 16.5", "fontSize: 18,", "lineHeight: 27"):
        assert stale not in adapter, stale


def test_chart_gutters_and_adapter_grid_keep_the_reviewed_geometry():
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
        f"const top = Math.max({chart_model.TOP} * scale, {chart_model.TOP});",
        f"bottom: {chart_model.BOTTOM} * scale,",
        "const nameGap = Math.max(13 * scale, 13);",
        "top,",
        "nameGap,",
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
