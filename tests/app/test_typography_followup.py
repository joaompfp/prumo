"""Follow-up regressions for the typography release review.

Three findings were left open by the independent quality review: the SVG gutter under-
estimated real Lato digit advances, the canvas top gutter scaled below its fixed CSS type,
and the figure block narrowed the latest value between 1101px and 1139px. The public h1
now uses the compact clamp with an overflow fallback rather than dictionary hyphenation.
These are static pins plus measured Lato widths; the parent browser matrix still owns the
rendered check.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.charts import line_chart

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "static" / "css" / "prumo.css"
ADAPTER = ROOT / "tools" / "charts" / "src" / "adapter.js"

# Chromium 1248 with the served Lato subset, weight 400 at 18.15px. The y tick renderer
# anchors at model.left - 11, so the measured advance is the full ink width for these tokens.
LONG_TICKS = (
    ("10000000", "10\u00a0000\u00a0000", 93.46142578125),
    ("10000000000", "10\u00a0000\u00a0000\u00a0000", 129.67047119140625),
)


def _tick_x(svg: str, text: str) -> float:
    root = ET.fromstring(svg)
    positions = [float(node.attrib["x"]) for node in root.iter()
                 if node.tag.endswith("text") and node.attrib.get("class") == "chart-tick"
                 and node.text == text and node.attrib.get("text-anchor") == "end"]
    assert len(positions) == 1, text
    return positions[0]


@pytest.mark.parametrize("value,label,rendered_width", LONG_TICKS)
def test_long_axis_ticks_clear_the_left_edge_with_measured_lato_width(
        value, label, rendered_width):
    svg = str(line_chart([{"period": "2026-01", "value_text": value}],
                         frequency="M", title="T"))
    tick_x = _tick_x(svg, label)
    assert tick_x - rendered_width >= 2.0


def test_canvas_top_gutter_keeps_a_css_pixel_floor_for_fixed_type():
    adapter = ADAPTER.read_text(encoding="utf-8")
    assert "const top = Math.max(31 * scale, 31);" in adapter
    assert "const nameGap = Math.max(13 * scale, 13);" in adapter
    assert "top," in adapter
    assert "nameGap," in adapter
    assert "top: 31 * scale," not in adapter
    assert "nameGap: 13 * scale," not in adapter
    # The fixed CSS type roles are the reason the gutter cannot scale below 31px.
    assert adapter.count("fontSize: 19.8") == 2


def test_figure_block_stacks_at_1200px_before_the_value_column_narrows():
    css = CSS.read_text(encoding="utf-8")
    start = css.index("@media (max-width: 1200px) {")
    end = css.index("@media (max-width: 1100px) {")
    assert start < end
    block = css[start:end]
    assert ".figure-block { grid-template-columns: 1fr; gap: 20px; }" in block
    assert ".figure-meta { border-left: 0; border-top: 1px solid var(--rule);" in block
    # The old 1100px query no longer collapses the figure block.
    narrow = css[end:css.index("@media (max-width: 900px) {")]
    assert ".figure-block" not in narrow


def test_h1_uses_the_compact_clamp_and_an_overflow_fallback():
    css = CSS.read_text(encoding="utf-8")
    heading = re.search(r"\nh1 \{([^}]*)\}", css)
    shared = re.search(r"h1, h2, h3 \{([^}]*)\}", css)
    assert heading and shared
    assert "font-size: clamp(1.65rem, 5.2vw, 2.35rem);" in heading.group(1)
    assert "hyphens: auto;" not in heading.group(1)
    assert "overflow-wrap: anywhere;" in shared.group(1)
