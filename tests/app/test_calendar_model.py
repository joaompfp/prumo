"""Sparse calendar model, SVG and payload v2, with dense v1 contracts pinned unchanged."""
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from app import chart_model
from app.calendar_model import calendar_model
from app.calendar_svg import calendar_legend, calendar_plot, calendar_svg
from app.charts import chart_legend, chart_plot, chart_svg, line_chart, two_series_chart
from app.interactive import build_payload

GOLDEN = Path(__file__).parent / "golden" / "charts"


def observations(rows):
    return [{"period": period, "value_text": value} for period, value in rows]


def monthly(year, values, start=1):
    return [{"period": f"{year}-{month:02d}", "value_text": str(value)}
            for month, value in enumerate(values, start=start)]


def annual(*pairs):
    return [{"period": str(year), "value_text": value} for year, value in pairs]


def test_union_merges_every_frequency_that_starts_on_the_same_day():
    model = calendar_model(
        (
            observations([("2026", "1")]),
            observations([("2026-01", "2")]),
            observations([("2026-Q1", "3")]),
            observations([("2026-S1", "4")]),
            observations([("2026-01-01", "5")]),
        ),
        labels=("Anual", "Mensal", "Trimestral", "Semestral", "Diário"),
        units=("%",) * 5,
        frequencies=("A", "M", "Q", "S", "D"),
        title="Cinco frequências",
    )
    assert model is not None
    assert len(model.rows) == 1
    row = model.rows[0]
    assert row.period_text == "01/01/2026"
    assert [cell.period for cell in row.cells if cell is not None] == [
        "2026", "2026-01", "2026-Q1", "2026-S1", "2026-01-01"]
    assert [cell.period_text for cell in row.cells if cell is not None] == [
        "2026", "janeiro de 2026", "1.º trimestre de 2026", "1.º semestre de 2026",
        "01/01/2026"]
    assert model.points == model.rows
    assert model.styles == ("g0", "g1", "g2", "g3", "g4")
    assert [item.frequency for item in model.series] == ["A", "M", "Q", "S", "D"]
    assert all(item.breaks == () for item in model.series)
    assert all(item.latest_index == 0 for item in model.series)


def test_rows_are_strictly_increasing_calendar_days_not_token_order():
    model = calendar_model(
        (
            observations([("2026-03", "3"), ("2026-01", "1"), ("2026-02", "2")]),
            observations([("2026", "10")]),
        ),
        labels=("Mensal", "Anual"),
        units=("%", "%"),
        frequencies=("M", "A"),
        title="Ordem",
    )
    assert model is not None
    ordinals = [row.ordinal for row in model.rows]
    assert ordinals == sorted(ordinals) and len(set(ordinals)) == 3
    assert [row.period_text for row in model.rows] == [
        "01/01/2026", "01/02/2026", "01/03/2026"]
    xs = [row.x for row in model.rows]
    assert xs == sorted(xs) and len(set(xs)) == 3


def test_annual_gap_breaks_only_its_own_line_and_never_invents_a_year():
    model = calendar_model(
        (annual((2023, "1"), (2025, "2")),
         monthly(2023, range(1, 13)) + monthly(2024, range(1, 13))
         + monthly(2025, range(1, 13))),
        labels=("PIB", "IHPC"),
        units=("euros", "%"),
        frequencies=("A", "M"),
        title="Anual e mensal",
        dual=True,
    )
    assert model is not None
    annual_index = next(i for i, row in enumerate(model.rows)
                        if row.cells[0] is not None and row.cells[0].period == "2025")
    assert model.series[0].breaks == (annual_index,)
    assert model.series[0].latest_index == annual_index
    assert model.series[1].breaks == ()
    assert model.series[1].latest_index == len(model.rows) - 1
    # The missing 2024 annual observation is a break, never a carried 2023 value.
    assert sum(row.cells[0] is not None for row in model.rows) == 2

    svg = str(calendar_plot(model))
    annual_path = re.search(r'class="chart-line chart-line-a" d="([^"]+)"', svg).group(1)
    monthly_path = re.search(r'class="chart-line chart-line-b" d="([^"]+)"', svg).group(1)
    assert annual_path.count("M") == 2
    assert monthly_path.count("M") == 1


def test_intervening_months_do_not_break_a_complete_annual_line():
    model = calendar_model(
        (annual((2023, "1"), (2024, "2"), (2025, "3")),
         monthly(2023, range(1, 13)) + monthly(2024, range(1, 13))
         + monthly(2025, range(1, 13))),
        labels=("PIB", "IHPC"),
        units=("euros", "%"),
        frequencies=("A", "M"),
        title="Anual completo",
        dual=True,
    )
    assert model is not None
    assert model.series[0].breaks == ()
    assert model.series[1].breaks == ()


def test_long_mixed_window_samples_ticks_from_distinct_year_first_rows():
    monthly_rows = [item for year in range(2016, 2026)
                    for item in monthly(year, [1] * 12)]
    annual_rows = annual(*[(str(year), "1") for year in range(2016, 2026)])
    model = calendar_model(
        (monthly_rows, annual_rows),
        labels=("Mensal", "Anual"), units=("%", "%"),
        frequencies=("M", "A"), title="Dez anos",
    )
    assert model is not None
    assert len(model.rows) == 120
    ticks = model.x_ticks
    texts = [tick.text for tick in ticks]
    assert len(texts) == 6 and len(set(texts)) == 6
    assert texts[0] == "2016" and texts[-1] == "2025"
    # A label points at the first row of the year it prints, not at a position sampled
    # inside the list of year-first row indexes.
    assert [model.rows[tick.index].period_text[-4:] for tick in ticks] == texts


def test_exact_native_tokens_survive_and_hostile_labels_are_xml_escaped():
    hostile = '</title><script>alert(1)</script> & "x"'
    model = calendar_model(
        (observations([("2026-01", "1.10")]),),
        labels=(hostile,),
        units=("%",),
        frequencies=("M",),
        title=hostile,
    )
    assert model is not None
    cell = model.rows[0].cells[0]
    assert cell is not None
    assert cell.period == "2026-01"
    assert cell.period_text == "janeiro de 2026"
    assert cell.value_text == "1.10"
    assert cell.value_display == "1,10"
    assert cell.number == Decimal("1.10")
    assert model.labels == (hostile,)

    svg = str(calendar_svg(model))
    assert "<script>" not in svg and "</title><script>" not in svg
    assert "&lt;/title&gt;&lt;script&gt;" in svg
    assert "janeiro de 2026" in svg and "1,10 %" in svg


def test_payload_v2_has_null_cells_per_side_and_two_axes():
    model = calendar_model(
        (annual((2023, "100"), (2025, "110")),
         observations([("2024-01", "1.0"), ("2024-02", "1.5"), ("2025-01", "2.0")])),
        labels=("Nível", "Taxa"),
        units=("milhões de euros", "%"),
        frequencies=("A", "M"),
        title="Duas escalas",
        dual=True,
    )
    assert model is not None
    payload = build_payload(model, badge="Calculado pelo Prumo")
    assert payload is not None
    assert payload["version"] == 2 and payload["kind"] == "calendar"
    assert payload["missing"] == "sem observação nesta posição temporal"
    assert len(payload["y"]) == len(payload["display"]) == len(payload["cell_periods"])
    assert len(payload["y"]) == len(model.rows)
    assert payload["x"] == [row.ordinal for row in model.rows]
    assert payload["x_min"] < payload["x_max"]
    assert payload["periods"] == [row.period_text for row in model.rows]
    assert len(payload["axes"]) == 2
    assert [axis["unit"] for axis in payload["axes"]] == ["milhões de euros", "%"]
    assert [item["axis"] for item in payload["series"]] == [0, 1]
    assert [item["style"] for item in payload["series"]] == ["a", "b"]
    assert [item["frequency"] for item in payload["series"]] == ["A", "M"]
    assert [item["badge"] for item in payload["series"]] == ["Calculado pelo Prumo"] * 2

    for row_index, row in enumerate(model.rows):
        for side, cell in enumerate(row.cells):
            if cell is None:
                assert payload["y"][row_index][side] is None
                assert payload["display"][row_index][side] is None
                assert payload["cell_periods"][row_index][side] is None
            else:
                assert payload["y"][row_index][side] == float(cell.number)
                assert payload["display"][row_index][side] == (
                    f"{cell.value_display} {model.units[side]}")
                assert payload["cell_periods"][row_index][side] == cell.period_text
    # The month where only the monthly side observed is a real null, not zero and not a repeat.
    february = next(i for i, row in enumerate(model.rows) if row.period_text == "01/02/2024")
    assert payload["y"][february] == [None, 1.5]
    assert payload["display"][february] == [None, "1,5 %"]
    assert payload["cell_periods"][february] == [None, "fevereiro de 2024"]

    encoded = json.dumps(payload, ensure_ascii=False)
    assert "value_text" not in encoded and "series_id" not in encoded
    assert payload["series"][0]["breaks"] == [3]  # 2025 annual row skips 2024


def test_six_sides_share_one_axis_and_keep_ordered_styles():
    histories = tuple(monthly(2026, (index, index + 1, index + 2)) for index in range(6))
    model = calendar_model(
        histories,
        labels=tuple(f"Série {index}" for index in range(6)),
        units=("%",) * 6,
        frequencies=("M",) * 6,
        title="Seis lados",
    )
    assert model is not None
    assert model.styles == ("g0", "g1", "g2", "g3", "g4", "g5")
    payload = build_payload(model)
    assert payload is not None and len(payload["axes"]) == 1
    assert len(payload["series"]) == 6
    assert all(item["axis"] == 0 for item in payload["series"])


def test_single_point_is_centred_and_gets_a_visible_last_marker_and_legend():
    model = calendar_model(
        (observations([("2026-01", "3.90")]),),
        labels=("Um",),
        units=("%",),
        frequencies=("M",),
        title="Um valor",
    )
    assert model is not None
    assert len(model.rows) == 1
    assert model.rows[0].x == chart_model.LEFT + (
        chart_model.WIDTH - chart_model.LEFT - chart_model.RIGHT) / 2
    payload = build_payload(model)
    assert payload is not None
    assert payload["x_min"] < model.rows[0].ordinal < payload["x_max"]
    svg = str(calendar_plot(model))
    assert 'class="chart-last chart-last-g0"' in svg
    legend = str(calendar_legend(model))
    assert "3,90 %" in legend and "janeiro de 2026" in legend


def test_chart_dispatch_uses_the_calendar_renderer_without_changing_dense_models():
    model = calendar_model(
        (observations([("2026-01", "1")]),),
        labels=("A",), units=("%",), frequencies=("M",), title="Calendário",
    )
    assert model is not None
    assert str(chart_plot(model)) == str(calendar_plot(model))
    assert str(chart_legend(model)) == str(calendar_legend(model))
    assert str(chart_svg(model)) == str(calendar_svg(model))
    assert str(chart_plot(model)) + str(chart_legend(model)) == str(chart_svg(model))

    dense = chart_model.line_model(monthly(2026, ("1.0",)), frequency="M", title="Linha",
                                   unit="%")
    assert dense is not None
    assert str(chart_legend(dense)) == ""
    assert str(chart_svg(dense)) == str(chart_plot(dense))


def test_noncanonical_and_nonfinite_cells_are_excluded_without_flattening_rows():
    model = calendar_model(
        (observations([("2026-1", "9"), ("2026-01", "1.0"),
                       ("2026-02", "NaN"), ("2026-03", "3.0")]),),
        labels=("Mensal",), units=("%",), frequencies=("M",), title="Filtrado",
    )
    assert model is not None
    assert [row.cells[0].period for row in model.rows] == ["2026-01", "2026-03"]
    assert model.series[0].breaks == (1,)
    assert all(isinstance(row.cells[0].number, Decimal) for row in model.rows)


def test_empty_sides_duplicate_tokens_and_invalid_definitions_are_refused():
    assert calendar_model((), labels=(), units=(), frequencies=(), title="x") is None
    assert calendar_model(([],), labels=("A",), units=("%",), frequencies=("M",),
                          title="x") is None
    assert calendar_model(
        (observations([("2026", "1")]), observations([("n.d.", "NaN")])),
        labels=("A", "B"), units=("%", "%"), frequencies=("A", "M"), title="x") is None
    assert calendar_model(
        (observations([("2026-13", "1")]),),
        labels=("A",), units=("%",), frequencies=("M",), title="x") is None

    with pytest.raises(ValueError):
        calendar_model((observations([("2026-01", "1"), ("2026-01", "2")]),),
                       labels=("A",), units=("%",), frequencies=("M",), title="x")
    with pytest.raises(ValueError):
        calendar_model(([],) * 7, labels=("A",) * 7, units=("%",) * 7,
                       frequencies=("M",) * 7, title="x")
    with pytest.raises(ValueError):
        calendar_model(([],) * 3, labels=("A", "B", "C"), units=("%",) * 3,
                       frequencies=("M",) * 3, title="x", dual=True)
    with pytest.raises(ValueError):
        calendar_model(([],), labels=("A", "B"), units=("%",), frequencies=("M",),
                       title="x")


def test_dense_svg_goldens_stay_exact():
    cases = {
        "line_monthly": lambda: line_chart(
            monthly(2026, ("1.0", "2.05", "3.90")), frequency="M",
            title="Taxa de desemprego", unit="%"),
        "cmp_dual": lambda: two_series_chart(
            [{"period": "2026-01", "a": "1.0", "b": "100000"},
             {"period": "2026-02", "a": "1.5", "b": "101000"}],
            frequency="M", title="Par", labels=("A", "B"), unit_a="%",
            unit_b="milhões de euros"),
    }
    for name, render in cases.items():
        assert str(render()) == (GOLDEN / f"{name}.svg").read_text(encoding="utf-8"), name


def test_dense_payload_v1_is_byte_for_byte_the_existing_contract():
    model = chart_model.line_model(monthly(2026, ("1.0",)), frequency="M", title="T", unit="%")
    assert model is not None
    assert build_payload(model) == {
        "version": 1, "kind": "line", "name": "T (%)",
        "x": [24312.0], "x_min": 24311.0, "x_max": 24313.0,
        "x_ticks": [{"x": 24312.0, "text": "jan 2026"}],
        "periods": ["janeiro de 2026"], "display": [["1,0 %"]], "y": [[1.0]],
        "breaks": [],
        "axes": [{"unit": "%", "min": 0.9, "max": 1.1, "interval": 0.05,
                  "ticks": [{"value": 0.9, "text": "0,9"},
                            {"value": 0.95, "text": "0,95"},
                            {"value": 1.0, "text": "1"},
                            {"value": 1.05, "text": "1,05"},
                            {"value": 1.1, "text": "1,1"}]}],
        "series": [{"title": "T", "unit": "%", "style": "ink", "badge": ""}],
    }
