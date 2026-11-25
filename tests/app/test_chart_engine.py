"""Shared comparison engine: pair byte baselines and bounded country groups.

The pair assertions pin what existing pages already render, so the generic series refactor can
be proven byte-identical before any new shape is added. Group assertions cover the bounded
three-to-six series factory, its exact tokens and its one-axis contract.
"""
import json
from pathlib import Path

import pytest

from app import chart_model
from app.charts import chart_legend, chart_plot, comparison_svg, group_chart
from app.formatting import format_value
from app.interactive import build_payload

ROOT = Path(__file__).parents[2]
GOLDEN = Path(__file__).parent / "golden" / "charts"
PAIR_ROWS = [{"period": "2026-01", "a": "1.0", "b": "100000"},
             {"period": "2026-02", "a": "1.5", "b": "101000"}]
GROUPS = {
    3: ("Portugal", "Espanha", "França"),
    5: ("Portugal", "Espanha", "França", "Alemanha", "Itália"),
    6: ("Portugal", "Espanha", "França", "Alemanha", "Itália", "Países Baixos"),
}


def pair_model(*, dual: bool):
    return chart_model.comparison_model(
        PAIR_ROWS, frequency="M", title="Par", labels=("A", "B"), unit_a="%",
        unit_b="milhões de euros" if dual else "%", dual=dual)


def test_pair_svg_stays_byte_identical_to_the_reviewed_capture():
    model = pair_model(dual=True)
    assert model is not None
    svg = str(comparison_svg(model))
    assert svg == (GOLDEN / "cmp_dual.svg").read_text(encoding="utf-8")
    # The shell splits this output into plot and legend without changing either byte stream.
    assert str(chart_plot(model)) + str(chart_legend(model)) == svg


def test_pair_payload_stays_byte_shaped_for_existing_readers():
    model = pair_model(dual=True)
    assert model is not None
    payload = build_payload(model)
    assert payload is not None
    assert list(payload) == ["version", "kind", "name", "x", "x_min", "x_max", "x_ticks",
                             "periods", "display", "y", "breaks", "axes", "series"]
    assert [list(entry) for entry in payload["series"]] == [
        ["title", "unit", "style", "badge"], ["title", "unit", "style", "badge"]]
    assert payload == {
        "version": 1,
        "kind": "comparison",
        "name": "Par: A (%) e B (milhões de euros)",
        "x": [24312.0, 24313.0],
        "x_min": 24312.0,
        "x_max": 24313.0,
        "x_ticks": [{"x": 24312.0, "text": "jan 2026"},
                    {"x": 24313.0, "text": "fev 2026"}],
        "periods": ["janeiro de 2026", "fevereiro de 2026"],
        "display": [["1 %", "100\u00a0000 milhões de euros"],
                    ["1,5 %", "101\u00a0000 milhões de euros"]],
        "y": [[1.0, 100000.0], [1.5, 101000.0]],
        "breaks": [],
        "axes": [
            {"unit": "%", "min": 0.8, "max": 1.6, "interval": 0.2,
             "ticks": [{"value": 0.8, "text": "0,8"}, {"value": 1.0, "text": "1"},
                       {"value": 1.2, "text": "1,2"}, {"value": 1.4, "text": "1,4"},
                       {"value": 1.6, "text": "1,6"}]},
            {"unit": "milhões de euros", "min": 99750.0, "max": 101250.0, "interval": 250.0,
             "ticks": [{"value": 99750.0, "text": "99\u00a0750"},
                       {"value": 100000.0, "text": "100\u00a0000"},
                       {"value": 100250.0, "text": "100\u00a0300"},
                       {"value": 100500.0, "text": "100\u00a0500"},
                       {"value": 100750.0, "text": "100\u00a0800"},
                       {"value": 101000.0, "text": "101\u00a0000"},
                       {"value": 101250.0, "text": "101\u00a0300"}]},
        ],
        "series": [
            {"title": "A", "unit": "%", "style": "ink", "badge": ""},
            {"title": "B", "unit": "milhões de euros", "style": "red", "badge": ""},
        ],
    }
    # The template serialises this object as JSON; ordering is part of the inert block.
    assert json.dumps(payload, ensure_ascii=False).startswith(
        '{"version": 1, "kind": "comparison", "name": "Par: A (%) e B (milhões de euros)"')


def test_pair_axes_are_explicit_and_keep_the_same_unit_dual_semantics():
    common = pair_model(dual=False)
    assert common is not None
    assert common.axes == (0, 0) and common.dual is False
    assert common.axis_labels == ("", "")

    # A deliberate same-unit pair still gets two independent scales; the unit text never decides
    # the axes, and the series position never decides the y geometry.
    same_unit = chart_model.comparison_model(
        PAIR_ROWS, frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%",
        dual=True)
    assert same_unit is not None
    assert same_unit.axes == (0, 1) and same_unit.dual is True
    assert same_unit.axis_labels == ("Eixo esquerdo", "Eixo direito")
    assert same_unit.hi_a < 10 and same_unit.lo_b > 90000
    for point in same_unit.points:
        assert point.values[0].y == pytest.approx(
            chart_model.TOP + float((same_unit.hi_a - point.values[0].number)
                                    / (same_unit.hi_a - same_unit.lo_a)
                                    * (chart_model.HEIGHT - chart_model.TOP
                                       - chart_model.BOTTOM)))
        assert point.values[1].y == pytest.approx(
            chart_model.TOP + float((same_unit.hi_b - point.values[1].number)
                                    / (same_unit.hi_b - same_unit.lo_b)
                                    * (chart_model.HEIGHT - chart_model.TOP
                                       - chart_model.BOTTOM)))


def group_rows(labels, periods=("2024-S1", "2024-S2", "2025-S1")):
    rows = []
    for step, period in enumerate(periods):
        rows.append({"period": period,
                     "values": [f"{0.2 + index * 0.01 + step * 0.002:.3f}"
                                for index, _label in enumerate(labels)]})
    return rows


@pytest.mark.parametrize("count", [3, 5, 6])
def test_group_accepts_the_bounded_counts_on_one_shared_axis(count):
    labels = GROUPS[count]
    model = chart_model.group_model(group_rows(labels), frequency="S", title="Preço",
                                    labels=labels, unit="EUR/kWh")
    assert model is not None
    assert model.kind == "group" and model.dual is False
    assert model.axes == (0,) * count
    assert model.axis_labels == ("",) * count
    assert len(model.labels) == count
    assert all(len(point.values) == count for point in model.points)
    assert model.styles == chart_model.GROUP_STYLES[:count]
    assert model.styles[0] == "g0" and len(set(model.styles)) == count
    assert model.ticks_b == () and model.unit_a == model.unit_b == "EUR/kWh"
    assert model.lo_a <= min(v.number for p in model.points for v in p.values)
    assert model.hi_a >= max(v.number for p in model.points for v in p.values)

    svg = str(group_chart(group_rows(labels), frequency="S", title="Preço", labels=labels,
                          unit="EUR/kWh"))
    assert "NaN" not in svg and "None" not in svg
    assert svg.count('class="chart-line chart-line-g') == count
    assert svg.count('class="legend-swatch swatch-g') == count
    assert svg.count('class="chart-last chart-last-g') == count
    assert svg.count("chart-axis-label") == 1
    # The generic plot/legend dispatch serves a group through the same paths as a pair.
    assert str(chart_plot(model)) + str(chart_legend(model)) == str(comparison_svg(model))


@pytest.mark.parametrize("count", [0, 1, 2, 7])
def test_group_rejects_counts_outside_three_to_six(count):
    labels = tuple(f"S{index}" for index in range(count))
    with pytest.raises(ValueError, match="3 to 6 series"):
        chart_model.group_model([], frequency="S", title="Preço", labels=labels,
                                unit="EUR/kWh")


def test_group_rejects_row_shapes_that_cannot_name_every_series():
    labels = GROUPS[3]
    with pytest.raises(ValueError, match="one value per label"):
        chart_model.group_model([{"period": "2024-S1", "values": ["1", "2"]}],
                                frequency="S", title="Preço", labels=labels, unit="EUR/kWh")
    with pytest.raises(ValueError, match="one value per label"):
        chart_model.group_model([{"period": "2024-S1"}], frequency="S", title="Preço",
                                labels=labels, unit="EUR/kWh")
    with pytest.raises(ValueError, match="period"):
        chart_model.group_model([{"values": ["1", "2", "3"]}], frequency="S", title="Preço",
                                labels=labels, unit="EUR/kWh")
    with pytest.raises(ValueError, match="unique"):
        chart_model.group_model(group_rows(("A", "A", "B")), frequency="S", title="Preço",
                                labels=("A", "A", "B"), unit="EUR/kWh")
    with pytest.raises(ValueError, match="non-empty label"):
        chart_model.group_model(group_rows(("A", " ", "B")), frequency="S", title="Preço",
                                labels=("A", " ", "B"), unit="EUR/kWh")


def test_group_drops_a_period_with_any_missing_country_and_keeps_the_gap():
    labels = GROUPS[3]
    rows = [{"period": "2024-S1", "values": ["1.0", "2.0", "3.0"]},
            {"period": "2024-S2", "values": ["1.1", "n.d.", "3.1"]},
            {"period": "2025-S1", "values": ["1.2", "2.2", "3.2"]},
            {"period": "2026-S1", "values": ["1.3", "2.3", "3.3"]}]
    model = chart_model.group_model(rows, frequency="S", title="Preço", labels=labels,
                                    unit="EUR/kWh")
    assert model is not None
    assert [p.period for p in model.points] == ["2024-S1", "2025-S1", "2026-S1"]
    assert [v.value_text for p in model.points for v in p.values].count("n.d.") == 0
    # The dropped semester and the absent 2025-S2 are both visual breaks, not joined lines.
    assert model.breaks == (1, 2)


def test_group_single_period_is_centred_with_one_visible_mark_per_series():
    labels = GROUPS[3]
    model = chart_model.group_model([{"period": "2024-S1", "values": ["1.0", "2.0", "3.0"]}],
                                    frequency="S", title="Preço", labels=labels,
                                    unit="EUR/kWh")
    assert model is not None
    assert len(model.points) == 1
    assert model.points[0].x == chart_model.LEFT + (chart_model.WIDTH - chart_model.LEFT
                                                    - chart_model.RIGHT) / 2
    assert model.breaks == ()
    svg = str(group_chart([{"period": "2024-S1", "values": ["1.0", "2.0", "3.0"]}],
                          frequency="S", title="Preço", labels=labels, unit="EUR/kWh"))
    assert svg.count('class="chart-last chart-last-g') == 3


def test_group_never_prints_overlapping_last_value_labels():
    labels = GROUPS[5]
    rows = [{"period": "2024-S1",
             "values": ["0.250", "0.250", "0.250", "0.250", "0.250"]}]
    model = chart_model.group_model(rows, frequency="S", title="Preço", labels=labels,
                                    unit="EUR/kWh")
    assert model is not None
    assert len(model.marks) == 1 and model.marks[0].suffix == "g0"
    svg = str(group_chart(rows, frequency="S", title="Preço", labels=labels, unit="EUR/kWh"))
    assert svg.count('class="chart-last-label') == 1


def test_group_keeps_exact_tokens_in_the_svg_payload_and_values():
    labels = GROUPS[3]
    tokens = ["0.2315", "0.2100", "0.2500"]
    rows = [{"period": "2024-S1", "values": tokens},
            {"period": "2024-S2", "values": ["0.2316", "0.2101", "0.2501"]}]
    model = chart_model.group_model(rows, frequency="S", title="Preço", labels=labels,
                                    unit="EUR/kWh")
    assert model is not None
    first = model.points[0]
    assert [value.value_text for value in first.values] == tokens
    assert [value.value_display for value in first.values] == [format_value(t) for t in tokens]
    payload = build_payload(model)
    assert payload is not None
    assert payload["kind"] == "group"
    assert payload["display"][0] == [f"{format_value(t)} EUR/kWh" for t in tokens]
    assert payload["y"][0] == [float(t) for t in tokens]
    assert payload["periods"][0] == "1.º semestre de 2024"
    svg = str(group_chart(rows, frequency="S", title="Preço", labels=labels, unit="EUR/kWh"))
    assert "Portugal - 1.º semestre de 2024: 0,2315 EUR/kWh" in svg
    assert "Espanha - 1.º semestre de 2024: 0,21 EUR/kWh" in svg
    assert "França - 1.º semestre de 2024: 0,25 EUR/kWh" in svg


def test_group_payload_declares_n_dimensions_and_one_explicit_axis():
    labels = GROUPS[5]
    model = chart_model.group_model(group_rows(labels), frequency="S", title="Preço",
                                    labels=labels, unit="EUR/kWh")
    assert model is not None
    payload = build_payload(model)
    assert payload is not None
    assert len(payload["axes"]) == 1
    assert len(payload["series"]) == len(labels)
    assert all(entry["axis"] == 0 for entry in payload["series"])
    assert [entry["style"] for entry in payload["series"]] == list(chart_model.GROUP_STYLES[:5])
    assert all(len(row) == len(labels) for row in payload["y"])
    assert all(len(row) == len(labels) for row in payload["display"])
    assert len(payload["periods"]) == len(payload["x"]) == len(payload["y"])
    # Every SVG point title is built from the same display rows the payload carries.
    svg = str(group_chart(group_rows(labels), frequency="S", title="Preço", labels=labels,
                          unit="EUR/kWh"))
    for row_index, point in enumerate(model.points):
        for value, display in zip(point.values, payload["display"][row_index]):
            assert display == f"{value.value_display} EUR/kWh"
            assert f"{value.value_display} EUR/kWh</title>" in svg


def test_group_escapes_hostile_labels_in_svg_and_keeps_them_inert_in_payload():
    hostile = '</script><img src=x onerror="alert(1)">'
    labels = (hostile, "Espanha", "França")
    model = chart_model.group_model(group_rows(labels), frequency="S", title="Preço",
                                    labels=labels, unit="EUR/kWh")
    assert model is not None
    svg = str(group_chart(group_rows(labels), frequency="S", title="Preço", labels=labels,
                          unit="EUR/kWh"))
    assert "<img src=x" not in svg and "&lt;img src=x" in svg
    payload = build_payload(model)
    assert payload is not None
    assert payload["series"][0]["title"] == hostile
    # The template's tojson escaping is pinned by the series hostile-title test; here the engine
    # proves the SVG never emits the label as markup.
    assert payload["series"][0]["title"].startswith("</script>")


def test_group_styles_are_defined_once_in_css_and_honoured_by_the_adapter():
    css = (ROOT / "static" / "css" / "prumo.css").read_text(encoding="utf-8")
    for index in range(6):
        assert f".chart-line-g{index} " in css
        assert f".chart-last-g{index} " in css
        assert f".swatch-g{index} " in css
    assert ".chart-line-g0 { stroke: var(--accent); }" in css
    adapter = (ROOT / "tools" / "charts" / "src" / "adapter.js").read_text(encoding="utf-8")
    assert "g0: { color: css('--accent', '#9b1c2e'), type: 'solid' }" in adapter
    assert "const style = seriesStyles[entry.style] || seriesStyles.ink;" in adapter
    assert "const axis = Number.isInteger(entry.axis) ? entry.axis" in adapter
    assert "if (payload.axes.length > 2) return false;" in adapter
    # A grouped payload must declare every series axis, and neither validator accepts an axis
    # without a member: no renderer may fall back to the series position for a group.
    assert "if (payload.kind === 'group' || payload.series.length > 2) return false;" in adapter
    assert "if (usedAxes.size !== payload.axes.length) return false;" in adapter


def expected_axis_y(model, number, axis):
    lo, hi = (model.lo_b, model.hi_b) if axis else (model.lo_a, model.hi_a)
    span = hi - lo or 1
    return chart_model.TOP + float((hi - number) / span
                                   * (chart_model.HEIGHT - chart_model.TOP
                                      - chart_model.BOTTOM))


MIXED_UNITS = ("milhões de euros", "%", "%")


def test_group_axes_bind_domains_and_geometry_to_every_member():
    labels = GROUPS[3]
    rows = [{"period": "2024-S1", "values": ["100000", "1.0", "2.0"]},
            {"period": "2024-S2", "values": ["101000", "1.5", "3.0"]},
            {"period": "2025-S1", "values": ["102500", "1.2", "2.5"]}]
    model = chart_model.group_model(rows, frequency="S", title="Preço", labels=labels,
                                    units=MIXED_UNITS, axes=(0, 1, 1))
    assert model is not None
    assert model.axes == (0, 1, 1) and model.dual is True
    assert model.units == MIXED_UNITS
    assert (model.unit_a, model.unit_b) == ("milhões de euros", "%")
    assert model.axis_labels == ("Eixo esquerdo", "Eixo direito", "Eixo direito")

    # Axis 0 contains only the first series; axis 1 is bounded by both later members.
    assert model.lo_a <= 100000 and model.hi_a >= 102500
    assert model.lo_b <= 1.0 and model.hi_b >= 3.0 and model.hi_b < 1000
    assert model.ticks_a[0].value == model.lo_a and model.ticks_a[-1].value == model.hi_a
    assert model.ticks_b[0].value == model.lo_b and model.ticks_b[-1].value == model.hi_b

    for point in model.points:
        for index, value in enumerate(point.values):
            assert value.y == expected_axis_y(model, value.number, model.axes[index])
    assert model.name == "Preço: Portugal (milhões de euros), Espanha (%) e França (%)"

    payload = build_payload(model)
    assert payload is not None
    assert [axis["unit"] for axis in payload["axes"]] == ["milhões de euros", "%"]
    assert [entry["axis"] for entry in payload["series"]] == [0, 1, 1]
    assert payload["y"] == [[100000.0, 1.0, 2.0], [101000.0, 1.5, 3.0],
                            [102500.0, 1.2, 2.5]]
    assert payload["display"][0] == [f"{format_value('100000')} milhões de euros",
                                     "1 %", "2 %"]

    svg = str(group_chart(rows, frequency="S", title="Preço", labels=labels,
                          units=MIXED_UNITS, axes=(0, 1, 1)))
    assert svg.count("chart-axis-label") == 2
    assert svg.count('class="chart-line chart-line-g') == 3
    assert svg.count('class="legend-axis"') == 3
    assert svg.count("Eixo esquerdo") == 1 and svg.count("Eixo direito") == 2
    for label in labels:
        assert label in svg


def test_group_six_series_use_both_explicit_axis_groups():
    labels = GROUPS[6]
    units = ("%", "%", "milhões de euros", "milhões de euros", "%", "milhões de euros")
    axes = (0, 0, 1, 1, 0, 1)
    rows = [{"period": "2024-S1", "values": ["1.0", "2.0", "100000", "200000", "5.0",
                                             "500000"]},
            {"period": "2024-S2", "values": ["1.5", "2.5", "101000", "201000", "5.5",
                                             "510000"]}]
    model = chart_model.group_model(rows, frequency="S", title="Preço", labels=labels,
                                    units=units, axes=axes)
    assert model is not None
    assert model.axes == axes and model.dual is True
    assert model.styles == chart_model.GROUP_STYLES
    # The later axis-1 member sets the domain; the old index == 1 inference would have used
    # only series 1 (a percentage) and clipped every million-euro series.
    assert model.lo_b <= 100000 and model.hi_b >= 510000
    assert model.lo_a <= 1.0 and model.hi_a >= 5.5
    payload = build_payload(model)
    assert payload is not None
    assert len(payload["axes"]) == 2
    assert [entry["axis"] for entry in payload["series"]] == list(axes)
    svg = str(group_chart(rows, frequency="S", title="Preço", labels=labels, units=units,
                          axes=axes))
    assert svg.count("chart-axis-label") == 2
    assert svg.count('class="legend-axis"') == 6
    assert svg.count("Eixo esquerdo") == 3 and svg.count("Eixo direito") == 3
    for label in labels:
        assert label in svg


def test_group_reversed_axis_members_keep_their_own_scale():
    labels = GROUPS[3]
    rows = [{"period": "2024-S1", "values": ["100000", "1.0", "200000"]},
            {"period": "2024-S2", "values": ["101000", "1.5", "201000"]}]
    model = chart_model.group_model(rows, frequency="S", title="Preço", labels=labels,
                                    units=("milhões de euros", "%", "milhões de euros"),
                                    axes=(1, 0, 1))
    assert model is not None
    assert model.axes == (1, 0, 1) and model.dual is True
    assert (model.unit_a, model.unit_b) == ("%", "milhões de euros")
    assert model.axis_labels == ("Eixo direito", "Eixo esquerdo", "Eixo direito")
    assert model.lo_b <= 100000 and model.hi_b >= 201000
    assert model.lo_a <= 1.0 and model.hi_a >= 1.5
    for point in model.points:
        for index, value in enumerate(point.values):
            assert value.y == expected_axis_y(model, value.number, model.axes[index])
    payload = build_payload(model)
    assert payload is not None
    assert [axis["unit"] for axis in payload["axes"]] == ["%", "milhões de euros"]
    assert [entry["axis"] for entry in payload["series"]] == [1, 0, 1]


@pytest.mark.parametrize("axes, message", [
    ((), "one axis assignment"),
    ((0, 1), "one axis assignment"),
    ("010", "one axis assignment"),
    (1, "one axis assignment"),
    ((0, 1, 2), "0 or 1"),
    ((0, 1, "1"), "0 or 1"),
    ((True, 0, 0), "0 or 1"),
    ((1, 1, 1), "at least one series"),
])
def test_group_rejects_invalid_axis_assignments(axes, message):
    with pytest.raises(ValueError, match=message):
        chart_model.group_model([], frequency="S", title="Preço", labels=GROUPS[3],
                                axes=axes)


def test_group_rejects_per_series_unit_shape_faults():
    with pytest.raises(ValueError, match="one unit per series"):
        chart_model.group_model([], frequency="S", title="Preço", labels=GROUPS[3],
                                units=("%", "%"))
    bad_units: tuple = ("%", "%", 1)
    with pytest.raises(ValueError, match="units must be text"):
        chart_model.group_model([], frequency="S", title="Preço", labels=GROUPS[3],
                                units=bad_units)
