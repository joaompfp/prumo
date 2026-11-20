"""Interactive chart payloads from the same prepared model as the SVG fallback.

The payload is inert JSON: reader-facing values are server-formatted strings, geometry is
numbers, and internal series ids, derived keys, licence notes and stored vocabulary codes never
enter it. A payload is `None` when safe numeric coordinates cannot be produced, and the page
keeps the SVG instead of changing a stored value.

`build_payload` is reusable: a CMS chart reader builds a `chart_model` model and serialises it
here exactly like the built-in detail pages do.
"""
import json
import math
from pathlib import Path

from app.calendar_model import MISSING_TEXT, CalendarModel
from app.chart_model import ComparisonModel, LineChartModel

MANIFEST = Path(__file__).resolve().parent.parent / "static" / "js" / "prumo-charts.manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def asset_path() -> str:
    """The content-fingerprinted local bundle URL, relative to the validated mount base."""
    manifest = _manifest()
    return f"/static/{manifest['asset']}?v={manifest['sha256'][:12]}"


def asset_sha256() -> str:
    return _manifest()["sha256"]


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe(number) -> bool:
    return _finite(number) is not None


def _axis(lo, hi, interval, ticks, unit: str) -> dict | None:
    values = [(_finite(lo), _finite(hi), _finite(interval))]
    tick_rows = [{"value": _finite(t.value), "text": t.text} for t in ticks]
    if not all(v is not None for row in values for v in row):
        return None
    if not tick_rows or any(row["value"] is None for row in tick_rows):
        return None
    return {"unit": unit, "min": _finite(lo), "max": _finite(hi),
            "interval": _finite(interval), "ticks": tick_rows}


def _bounds(xs: list[float]) -> tuple[float, float]:
    """A single point gets a small window so ECharts can centre it on a value axis."""
    return (min(xs), max(xs)) if len(xs) > 1 else (xs[0] - 1.0, xs[0] + 1.0)


def _x_ticks(model) -> list[dict] | None:
    rows = [{"x": _finite(tick.ordinal), "text": tick.text} for tick in model.x_ticks]
    if not rows or any(row["x"] is None for row in rows):
        return None
    return rows


def _comparison_series(model: ComparisonModel) -> list[dict]:
    """Series metadata in label order.

    Existing pairs keep their ink/red contract without an axis field. A bounded group declares
    its style key and its single explicit axis so the adapter never infers a second scale.
    """
    if model.kind == "comparison":
        return [{"title": model.labels[0], "unit": model.unit_a, "style": "ink", "badge": ""},
                {"title": model.labels[1], "unit": model.unit_b, "style": "red", "badge": ""}]
    return [{"title": label, "unit": unit, "style": style, "badge": "", "axis": 0}
            for label, unit, style in zip(model.labels, model.units, model.styles)]


def _calendar_payload(model: CalendarModel, *, badge: str, missing: str) -> dict | None:
    """Payload v2 for sparse calendar rows.

    `y`, `display` and `cell_periods` keep one column per side and one row per real calendar
    date. A missing observation is `None` in all three arrays: not zero, not the previous
    value, and not an inspectable cell. Breaks are per side and address row indices where that
    side skips its own native period.
    """
    xs = [_finite(row.ordinal) for row in model.rows]
    if not xs or any(x is None for x in xs):
        return None
    xs_clean: list[float] = [x for x in xs if x is not None]
    x_ticks = _x_ticks(model)
    if x_ticks is None:
        return None
    x_min, x_max = _bounds(xs_clean)

    ys: list[list[float | None]] = []
    display: list[list[str | None]] = []
    cell_periods: list[list[str | None]] = []
    for row in model.rows:
        y_row: list[float | None] = []
        display_row: list[str | None] = []
        period_row: list[str | None] = []
        for index, cell in enumerate(row.cells):
            if cell is None:
                y_row.append(None)
                display_row.append(None)
                period_row.append(None)
                continue
            value = _finite(cell.number)
            if value is None:
                return None
            y_row.append(value)
            display_row.append(_display(cell.value_display, model.units[index]))
            period_row.append(cell.period)
        ys.append(y_row)
        display.append(display_row)
        cell_periods.append(period_row)

    axes = [_axis(model.lo_a, model.hi_a, model.interval_a, model.ticks_a, model.unit_a)]
    if model.dual:
        axes.append(_axis(model.lo_b, model.hi_b, model.interval_b, model.ticks_b,
                          model.unit_b))
    if any(axis is None for axis in axes):
        return None

    series = [
        {"title": item.label, "unit": item.unit, "style": item.style, "badge": badge,
         "axis": 1 if model.dual and index == 1 else 0, "frequency": item.frequency,
         "breaks": list(item.breaks)}
        for index, item in enumerate(model.series)
    ]
    return {
        "version": 2,
        "kind": "calendar",
        "name": model.name,
        "x": xs_clean,
        "x_min": x_min,
        "x_max": x_max,
        "x_ticks": x_ticks,
        "periods": [row.period_text for row in model.rows],
        "y": ys,
        "display": display,
        "cell_periods": cell_periods,
        "axes": axes,
        "series": series,
        "missing": missing,
    }


def build_payload(model: LineChartModel | ComparisonModel | CalendarModel, *, badge: str = "",
                  lang: str = "pt", missing: str = MISSING_TEXT) -> dict | None:
    """The browser model for one prepared chart, or None to decline enhancement safely."""
    del lang  # text arrives prepared from the catalogue by the caller
    if isinstance(model, CalendarModel):
        return _calendar_payload(model, badge=badge, missing=missing)
    xs = [x for x in (_finite(point.ordinal) for point in model.points) if x is not None]
    if not xs or len(xs) != len(model.points):
        return None
    x_ticks = _x_ticks(model)
    if x_ticks is None:
        return None
    x_min, x_max = _bounds(xs)

    if isinstance(model, LineChartModel):
        ys = [[_finite(point.number)] for point in model.points]
        periods = [point.period_text for point in model.points]
        display = [[_display(point.value_display, model.display_unit)]
                   for point in model.points]
        axes = [_axis(model.lo, model.hi, model.interval, model.y_ticks, model.display_unit)]
        series = [{"title": model.title, "unit": model.display_unit, "style": "ink",
                   "badge": badge}]
        breaks: list[int] = []
    else:
        ys = [[_finite(value.number) for value in point.values] for point in model.points]
        periods = [point.period_text for point in model.points]
        display = [[_display(value.value_display, unit)
                    for value, unit in zip(point.values, model.units)]
                   for point in model.points]
        axes = [_axis(model.lo_a, model.hi_a, model.interval_a, model.ticks_a, model.unit_a)]
        if model.dual:
            axes.append(_axis(model.lo_b, model.hi_b, model.interval_b, model.ticks_b,
                              model.unit_b))
        series = _comparison_series(model)
        breaks = list(model.breaks)

    if any(value is None for row in ys for value in row):
        return None
    if any(axis is None for axis in axes):
        return None
    return {
        "version": 1,
        "kind": model.kind,
        "name": model.name,
        "x": xs,
        "x_min": x_min,
        "x_max": x_max,
        "x_ticks": x_ticks,
        "periods": periods,
        "display": display,
        "y": ys,
        "breaks": breaks,
        "axes": axes,
        "series": series,
    }


def _display(value: str, unit: str) -> str:
    return f"{value} {unit}" if unit else value
