"""Chart preparation and the geometry shared by SVG and canvas.

Goldens were deliberately recaptured for the approved 50 percent legibility pass: wider
label margins and inward endpoint anchors. The 2026-11-17 typography increment recaptured
the same cases again for the further 10 percent label role and gutter scale. Original
captures remain in golden/pre_legibility. Every point/title/tick text is identical in both
captures and in the versioned golden-deltas receipt.
"""
import math
import re
from datetime import date
from pathlib import Path

from app import chart_model
from app.charts import chart_legend, chart_plot, comparison_svg, line_chart, two_series_chart
from app.interactive import build_payload

GOLDEN = Path(__file__).parent / "golden" / "charts"


def monthly(values):
    return [{"period": f"2026-{m:02d}", "value_text": v} for m, v in enumerate(values, 1)]


def compare(rows):
    return [{"period": p, "a": a, "b": b} for p, a, b in rows]


CASES = {
    "line_monthly": lambda: line_chart(monthly(["1.0", "2.05", "3.90"]), frequency="M",
                                       title="Taxa de desemprego", unit="%"),
    "line_single": lambda: line_chart(monthly(["3.90"]), frequency="M", title="Um valor",
                                      unit="pp"),
    "line_negative": lambda: line_chart(monthly(["-30.5", "-20.0", "-25.0"]), frequency="M",
                                        title="Saldo"),
    "line_nonfinite": lambda: line_chart(monthly(["1.0", "n.d.", "3.0", "NaN"]),
                                         frequency="M", title="Falhas", unit="%"),
    "line_annual": lambda: line_chart(
        [{"period": str(y), "value_text": v}
         for y, v in ((2000, "1"), (2001, "2"), (2002, "3"), (2003, "4"), (2004, "5"),
                      (2005, "6"))], frequency="A", title="Anual"),
    "line_empty": lambda: line_chart([], frequency="M", title="x"),
    "cmp_gap": lambda: two_series_chart(
        compare([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "2.5"),
                 ("2026-06", "1.2", "2.2")]), frequency="M", title="Par", labels=("A", "B"),
        unit_a="%", unit_b="%"),
    "cmp_dual": lambda: two_series_chart(
        compare([("2026-01", "1.0", "100000"), ("2026-02", "1.5", "101000")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%",
        unit_b="milhões de euros"),
    "cmp_single": lambda: two_series_chart(compare([("2026-01", "1.0", "2.0")]),
                                           frequency="M", title="Par", labels=("A", "B"),
                                           unit_a="%", unit_b="%"),
    "cmp_negative": lambda: two_series_chart(
        compare([("2026-01", "-1.0", "2.0"), ("2026-02", "1.5", "2.5")]), frequency="M",
        title="Par", labels=("A", "B"), unit_a="%", unit_b="%"),
    "cmp_empty": lambda: two_series_chart(compare([("2026-01", "x", "y")]), frequency="M",
                                          title="Par", labels=("A", "B"), unit_a="%"),
}


def test_svg_output_matches_the_reviewed_legibility_capture():
    for name, render in CASES.items():
        expected = (GOLDEN / f"{name}.svg").read_text(encoding="utf-8")
        assert str(render()) == expected, name


def test_chart_plot_and_legend_reassemble_the_public_comparison_output():
    model = chart_model.comparison_model(
        compare([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "2.5")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%")
    assert model is not None
    # The wrapper splits the old public output without changing either byte stream.
    assert str(chart_plot(model)) + str(chart_legend(model)) == str(comparison_svg(model))
    line = chart_model.line_model(monthly(["1.0"]), frequency="M", title="T")
    assert line is not None and str(chart_legend(line)) == ""


def test_line_model_filters_nonfinite_tokens_and_keeps_exact_strings():
    model = chart_model.line_model(monthly(["1.0", "n.d.", "3.90", "NaN"]), frequency="M",
                                   title="T", unit="%")
    assert [p.value_text for p in model.points] == ["1.0", "3.90"]
    assert [p.value_display for p in model.points] == ["1,0", "3,90"]
    assert [p.period_text for p in model.points] == ["janeiro de 2026", "março de 2026"]
    assert all(math.isfinite(p.x) and math.isfinite(p.y) for p in model.points)


def test_line_domain_bounds_every_point_and_ticks_are_uniform():
    model = chart_model.line_model(monthly(["2.1", "9.7", "3.3"]), frequency="M", title="T")
    values = [p.number for p in model.points]
    assert model.lo <= min(values) and model.hi >= max(values)
    assert model.lo == model.y_ticks[0].value and model.hi == model.y_ticks[-1].value
    gaps = {model.y_ticks[i].value - model.y_ticks[i - 1].value
            for i in range(1, len(model.y_ticks))}
    assert gaps == {model.interval}


def test_negative_domain_crosses_zero_and_marks_a_single_zero_tick():
    model = chart_model.line_model(monthly(["-30.5", "-20.0", "-25.0"]), frequency="M",
                                   title="Saldo")
    assert model.lo <= 0 <= model.hi
    assert [t.zero for t in model.y_ticks].count(True) == 1


def test_x_is_proportional_to_calendar_distance():
    model = chart_model.line_model(
        [{"period": p, "value_text": v} for p, v in
         (("2026-01", "1"), ("2026-02", "2"), ("2026-06", "3"))],
        frequency="M", title="T")
    xs = [p.x for p in model.points]
    first_step, second_step = xs[1] - xs[0], xs[2] - xs[1]
    assert second_step > first_step * 3.5  # five months, not one index step


def test_unknown_period_shape_falls_back_to_even_spacing_without_nan():
    model = chart_model.line_model([{"period": "sem-data-1", "value_text": "1"},
                                    {"period": "sem-data-2", "value_text": "2"}],
                                   frequency="M", title="T")
    assert [p.x for p in model.points] == [chart_model.LEFT,
                                           chart_model.LEFT + 880 - chart_model.LEFT
                                           - chart_model.RIGHT]


def test_single_point_is_centred_and_has_a_visible_last_mark():
    model = chart_model.line_model(monthly(["3.90"]), frequency="M", title="T")
    assert len(model.points) == 1
    assert model.points[0].x == chart_model.LEFT + (chart_model.WIDTH - chart_model.LEFT
                                                    - chart_model.RIGHT) / 2
    assert model.last_label == "3,90"


def test_comparison_intersects_finite_pairs_and_records_breaks():
    model = chart_model.comparison_model(
        compare([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "n.d."),
                 ("2026-03", "1.2", "2.2"), ("2026-07", "1.3", "2.3")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%")
    assert model is not None
    assert [p.period for p in model.points] == ["2026-01", "2026-03", "2026-07"]
    # February and April-June are both missing: monthly cadence breaks at each surviving point.
    assert model.breaks == (1, 2)
    for point in model.points:
        assert point.period_text.startswith(("janeiro", "março", "julho"))
        assert math.isfinite(point.a.y) and math.isfinite(point.b.y)


def test_expected_step_comes_from_the_frequency_and_token_shape():
    assert chart_model.expected_step(["2020", "2022"], "A") == 1.0
    assert chart_model.expected_step(["2026-01", "2026-06"], "M") == 1.0
    assert chart_model.expected_step(["2026-Q1", "2026-Q3"], "Q") == 1.0
    assert chart_model.expected_step(["2026-S1", "2026-S2"], "S") == 1.0
    assert chart_model.expected_step(["2026-01", "bad"], "M") is None
    assert chart_model.expected_step(["2026-01T00:00:00+00:00",
                                      "2026-01T00:15:00+00:00"], "PT15M") == 900.0
    # A month is one ordinal unit, never a fixed 30-day duration.
    assert chart_model.expected_step(["2026-01", "2026-02"], "P1M") is None
    assert chart_model.expected_step(["2026-01", "2026-02"], "custom") is None


def test_daily_periods_use_gregorian_ordinals_and_a_one_day_step():
    jan1, jan2, dec31 = "2025-01-01", "2025-01-02", "2025-12-31"
    assert chart_model.calendar_position(jan1, "D") == float(date(2025, 1, 1).toordinal())
    assert chart_model.calendar_position(jan2, "D") == float(date(2025, 1, 2).toordinal())
    assert (chart_model.calendar_position(dec31, "D")
            - chart_model.calendar_position(jan2, "D")) == 363
    assert chart_model.expected_step([jan1, jan2, dec31], "D") == 1.0
    # A date that does not exist is not placeable and cannot claim a day step.
    assert math.isnan(chart_model.calendar_position("2025-02-30", "D"))
    assert chart_model.expected_step(["2025-02-30", "2025-03-01"], "D") is None

    model = chart_model.line_model([{"period": p, "value_text": v} for p, v in
                                    ((jan1, "1"), (jan2, "2"), (dec31, "3"))],
                                   frequency="D", title="Diário")
    assert model is not None
    xs = [point.x for point in model.points]
    assert math.isclose((xs[2] - xs[1]) / (xs[1] - xs[0]), 363, rel_tol=1e-9)


def test_daily_gap_breaks_on_the_same_point_the_payload_marks():
    rows = compare([("2025-01-01", "1.0", "2.0"), ("2025-01-02", "1.5", "2.5"),
                    ("2025-12-31", "1.2", "2.2")])
    model = chart_model.comparison_model(rows, frequency="D", title="Par", labels=("A", "B"),
                                         unit_a="%", unit_b="%")
    assert model is not None
    assert model.breaks == (2,)
    data = build_payload(model)
    assert data is not None
    assert data["x"] == [point.ordinal for point in model.points]
    assert data["breaks"] == [2]

    # SVG and payload are two renderings of the same ordinals: same pixel gaps and same break.
    svg = str(chart_plot(model))
    match = re.search(r'class="chart-line chart-line-a" d="([^"]+)"', svg)
    assert match is not None
    assert match.group(1).count("M") == 2
    xs = sorted({float(value) for value in
                 re.findall(r'class="chart-point" cx="([0-9.]+)"', svg)})
    assert xs == sorted({round(point.x, 1) for point in model.points})


def test_non_canonical_calendar_tokens_never_trigger_the_even_spacing_fallback():
    # Canonical shapes only, for every frequency the catalogue publishes.
    assert math.isnan(chart_model.calendar_position("2026-1", "M"))
    assert math.isnan(chart_model.calendar_position("2026-13", "M"))
    assert math.isnan(chart_model.calendar_position("2026-Q5", "Q"))
    assert math.isnan(chart_model.calendar_position("2026-S3", "S"))
    assert math.isnan(chart_model.calendar_position("2026-11-01T00:15:00", "PT15M"))
    assert math.isnan(chart_model.calendar_position("2026-11-01T00:07:00+00:00", "PT15M"))
    assert math.isfinite(chart_model.calendar_position("2026-11-01T00:15:00+00:00", "PT15M"))
    assert chart_model.expected_step(["2026-01", "2026-1", "2026-12"], "M") is None

    # One malformed token is dropped; the canonical points keep their real calendar distance
    # instead of every point being flattened onto even spacing.
    model = chart_model.line_model(
        [{"period": p, "value_text": v} for p, v in
         (("2026-01", "1"), ("2026-1", "2"), ("2026-02", "3"), ("2026-12", "4"))],
        frequency="M", title="T")
    assert model is not None
    assert [point.period for point in model.points] == ["2026-01", "2026-02", "2026-12"]
    xs = [point.x for point in model.points]
    assert math.isclose((xs[2] - xs[1]) / (xs[1] - xs[0]), 10, rel_tol=1e-9)


def test_two_annual_points_still_break_across_a_missing_year():
    model = chart_model.comparison_model(
        compare([("2020", "1.0", "2.0"), ("2022", "1.5", "2.5")]),
        frequency="A", title="Par", labels=("A", "B"), unit_a="%", unit_b="%")
    assert model is not None
    assert model.breaks == (1,)
    assert len(model.points) == 2  # the break indexes existing points; it adds no point


def test_two_monthly_points_break_across_the_missing_month():
    model = chart_model.comparison_model(
        compare([("2026-01", "1.0", "2.0"), ("2026-03", "1.5", "2.5")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%")
    assert model is not None
    # A single observed step is the gap itself; the old median called it typical.
    assert model.breaks == (1,)


def test_missing_monthly_period_breaks_even_when_the_gap_is_first():
    model = chart_model.comparison_model(
        compare([("2026-01", "1.0", "2.0"), ("2026-03", "1.5", "2.5"),
                 ("2026-04", "1.2", "2.2")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%")
    assert model is not None
    assert model.breaks == (1,)


def test_monthly_and_annual_consecutive_periods_never_break():
    for frequency, periods in (("M", ["2026-01", "2026-02", "2026-03"]),
                               ("A", ["2020", "2021", "2022"])):
        model = chart_model.comparison_model(
            compare([(period, "1.0", "2.0") for period in periods]),
            frequency=frequency, title="Par", labels=("A", "B"), unit_a="%", unit_b="%")
        assert model is not None
        assert model.breaks == (), frequency


def test_comparison_single_axis_shares_domain_and_dual_does_not():
    rows = compare([("2026-01", "1.0", "200000"), ("2026-02", "1.5", "250000")])
    single = chart_model.comparison_model(rows, frequency="M", title="P", labels=("A", "B"),
                                          unit_a="%", unit_b="%")
    assert (single.lo_a, single.hi_a) == (single.lo_b, single.hi_b)
    assert single.interval_a == single.interval_b
    dual = chart_model.comparison_model(rows, frequency="M", title="P", labels=("A", "B"),
                                        unit_a="%", unit_b="milhões de euros")
    assert dual.dual and dual.hi_b < single.hi_b and dual.lo_a != dual.lo_b
    assert all(not t.zero for t in dual.ticks_a + dual.ticks_b)


def test_empty_and_nonfinite_inputs_produce_no_model():
    assert chart_model.line_model([], frequency="M", title="x") is None
    assert chart_model.line_model(monthly(["n.d."]), frequency="M", title="x") is None
    assert chart_model.comparison_model(compare([("2026-01", "x", "y")]), frequency="M",
                                        title="P", labels=("A", "B"), unit_a="%") is None
