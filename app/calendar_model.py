"""Sparse calendar chart model for series with different native frequencies.

The dense line/comparison models assume one shared period grid. Mixed annual, quarterly,
semester, monthly and daily selections cannot share that grid without inventing observations,
so this model merges only real observations: every distinct Gregorian start day becomes one row
and each side keeps its own native token, exact display string and gaps.

`app.calendar_svg` draws the model; `app.interactive.build_payload` serialises the same rows as
payload v2. A missing cell is explicitly `None` (a missing observation at this calendar
position), never zero, carry-forward or interpolation. The module is pure: no HTML, database or
request state.

Native period placement comes from `analysis.periods.period_start` and `period_index`, the one
canonical spelling authority. A cell is excluded when its token is non-canonical or its value is
non-finite; callers count those exclusions upstream so the reader sees an honest total.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from analysis.periods import period_index, period_start
from app.chart_model import (
    BOTTOM,
    GROUP_STYLES,
    HEIGHT,
    RIGHT,
    RIGHT_DUAL,
    TOP,
    WIDTH,
    XTick,
    YTick,
    _left_gutter,
    axis_interval,
    padded_domain,
    positions,
)
from app.formatting import decimal_or_none, format_axis, format_date, format_period, format_value

MIN_SERIES, MAX_SERIES = 1, 6
MISSING_TEXT = "sem observação nesta posição temporal"


@dataclass(frozen=True)
class CalendarCell:
    """One present native observation on a merged calendar row."""

    period: str
    period_text: str
    value_text: str
    value_display: str
    number: Decimal
    y: float


@dataclass(frozen=True)
class CalendarRow:
    """One real Gregorian start day shared by at least one series.

    `ordinal` is the day's Gregorian ordinal, `period_text` is that actual date formatted for the
    reader, and `cells` has one entry per series in label order. A `None` cell means the series
    has no observation at this calendar position.
    """

    ordinal: float
    x: float
    period_text: str
    cells: tuple[CalendarCell | None, ...]


@dataclass(frozen=True)
class CalendarSeries:
    """Per-side metadata: native frequency, own gap boundaries and last plotted row."""

    label: str
    unit: str
    style: str
    frequency: str
    breaks: tuple[int, ...]
    latest_index: int


@dataclass(frozen=True)
class CalendarModel:
    """One prepared sparse calendar chart.

    Axis fields mirror `ComparisonModel` so readers and the v2 adapter can handle both without a
    second shape: `ticks_a`/`lo_a`/`hi_a`/`interval_a`/`unit_a` describe the left axis and the
    `_b` fields the deliberate right axis of a two-side dual chart. `rows` is the authoritative
    representation; `points` is an alias for templates that iterate points.
    """

    kind: str
    title: str
    labels: tuple[str, ...]
    units: tuple[str, ...]
    styles: tuple[str, ...]
    frequencies: tuple[str, ...]
    dual: bool
    name: str
    width: int
    height: int
    left: int
    right: int
    top: int
    bottom: int
    rows: tuple[CalendarRow, ...]
    series: tuple[CalendarSeries, ...]
    ticks_a: tuple[YTick, ...]
    ticks_b: tuple[YTick, ...]
    lo_a: Decimal
    hi_a: Decimal
    lo_b: Decimal
    hi_b: Decimal
    interval_a: Decimal
    interval_b: Decimal
    unit_a: str
    unit_b: str
    x_ticks: tuple[XTick, ...]

    @property
    def points(self) -> tuple[CalendarRow, ...]:
        return self.rows


def _series_name(title: str, labels: tuple[str, ...], units: tuple[str, ...],
                 dual: bool) -> str:
    if len(labels) == 1:
        return title + (f" ({units[0]})" if units[0] else "")
    if dual:
        return f"{title}: {labels[0]} ({units[0]}) e {labels[1]} ({units[1]})"
    joined = ", ".join(labels[:-1]) + " e " + labels[-1]
    return f"{title}: {joined}" + (f" ({units[0]})" if units[0] else "")


def _metadata(histories, labels, units, frequencies, dual, title):
    """Validate the authored definition; data cells are filtered separately."""
    if not isinstance(title, str) or not title:
        raise ValueError("calendar charts need a title")
    for name, values in (("labels", labels), ("units", units), ("frequencies", frequencies)):
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"calendar {name} must be a sequence")
    labels, units, frequencies = tuple(labels), tuple(units), tuple(frequencies)
    count = len(histories) if isinstance(histories, (list, tuple)) else -1
    if count < 0:
        raise ValueError("calendar histories must be a sequence of histories")
    if count == 0:
        return None
    if not MIN_SERIES <= count <= MAX_SERIES:
        raise ValueError(f"calendar charts need {MIN_SERIES} to {MAX_SERIES} sides")
    if len(labels) != count or len(units) != count or len(frequencies) != count:
        raise ValueError("every calendar side needs one label, unit and frequency")
    if any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ValueError("every calendar side needs a short non-empty label")
    if len(set(labels)) != len(labels):
        raise ValueError("calendar side labels must be unique")
    if any(not isinstance(unit, str) for unit in units):
        raise ValueError("calendar units must be text")
    if any(not isinstance(frequency, str) or not frequency for frequency in frequencies):
        raise ValueError("every calendar side needs a frequency")
    if dual and count != 2:
        raise ValueError("a dual calendar chart needs exactly two sides")
    return labels, units, frequencies


def _side_cells(history, frequency: str) -> dict[int, tuple[str, str, Decimal, int, date]]:
    """Drawable cells keyed by Gregorian start ordinal, with native indices for gap detection."""
    if not isinstance(history, (list, tuple)):
        raise ValueError("every calendar history must be a sequence")
    seen: set[str] = set()
    cells: dict[int, tuple[str, str, Decimal, int, date]] = {}
    for item in history:
        if not isinstance(item, dict):
            raise ValueError("every calendar observation must be a mapping")
        period = item.get("period")
        if not isinstance(period, str) or not period:
            raise ValueError("every calendar observation needs a period token")
        if period in seen:
            raise ValueError(f"duplicate calendar period token: {period}")
        seen.add(period)
        token = item.get("value_text")
        if not isinstance(token, str):
            continue
        number = decimal_or_none(token)
        if number is None:
            continue
        start = period_start(period, frequency)
        if start is None:
            continue
        index = period_index(period, frequency)
        if index is None:
            continue
        ordinal = start.toordinal()
        if ordinal in cells:
            raise ValueError(f"two calendar periods start on the same day: {period}")
        cells[ordinal] = (period, token, number, index, start)
    return cells


def _x_labels(row_dates: list[str]) -> list[tuple[int, str]]:
    """At most six axis labels on real calendar dates.

    Three or more distinct years get one label per year at the first row of that year. A shorter
    window labels actual dates, evenly sampled when there are more than six rows. This avoids
    repeating the same year at two sampled row indices and never invents a period token.
    """
    if not row_dates:
        return []
    years = [int(item[:4]) for item in row_dates]
    distinct = sorted(set(years))
    if len(distinct) >= 3:
        indices = [years.index(year) for year in distinct]
        if len(indices) > 6:
            indices = sorted({indices[round(i * (len(indices) - 1) / 5)] for i in range(6)})
        return [(index, row_dates[index][:4]) for index in indices]
    if len(row_dates) <= 6:
        indices = list(range(len(row_dates)))
    else:
        indices = sorted({round(i * (len(row_dates) - 1) / 5) for i in range(6)})
    return [(index, format_date(row_dates[index])) for index in indices]


def calendar_model(histories: tuple[tuple[dict, ...], ...], *, labels: tuple[str, ...],
                   units: tuple[str, ...], frequencies: tuple[str, ...], title: str,
                   dual: bool = False,
                   width: int = WIDTH, height: int = HEIGHT) -> CalendarModel | None:
    """Prepare one sparse calendar chart, or None when any side has nothing drawable.

    `histories` is one sequence per side; each item is a dict with `period` and `value_text`,
    oldest-first or unordered (rows are sorted by real Gregorian start). Duplicate native tokens
    raise `ValueError`: two observations on one side for the same token cannot be silently
    resolved. Non-canonical periods and non-finite values are excluded, and a side left with no
    drawable value makes the whole chart unavailable rather than silently dropping that side.
    """
    metadata = _metadata(histories, labels, units, frequencies, dual, title)
    if metadata is None:
        return None
    labels, units, frequencies = metadata

    per_side: list[dict[int, tuple[str, str, Decimal, int, date]]] = []
    for history, frequency in zip(histories, frequencies):
        side_cells = _side_cells(history, frequency)
        if not side_cells:
            return None
        per_side.append(side_cells)

    ordinals = sorted({ordinal for side_cells in per_side for ordinal in side_cells})
    if not ordinals:
        return None

    numbers = [number for side_cells in per_side
               for (_, _, number, _, _) in side_cells.values()]
    if dual:
        lo_a, hi_a, ticks_a = padded_domain(
            [number for (_, _, number, _, _) in per_side[0].values()])
        lo_b, hi_b, ticks_b = padded_domain(
            [number for (_, _, number, _, _) in per_side[1].values()])
    else:
        lo_a, hi_a, ticks_a = padded_domain(numbers)
        lo_b, hi_b, ticks_b = lo_a, hi_a, ticks_a

    right = RIGHT_DUAL if dual else RIGHT
    texts_a = [format_axis(t) for t in ticks_a]
    texts_b = [format_axis(t) for t in ticks_b] if dual else []
    left = _left_gutter(texts_a + texts_b, width, right)
    plot_w, plot_h = width - left - right, height - TOP - BOTTOM

    def y_of(number: Decimal, lo: Decimal, hi: Decimal) -> float:
        side_span = hi - lo or Decimal(1)
        return TOP + float((hi - number) / side_span * plot_h)

    def y_for(index: int, number: Decimal) -> float:
        return y_of(number, lo_b, hi_b) if dual and index == 1 else y_of(number, lo_a, hi_a)

    ordinals_f = [float(ordinal) for ordinal in ordinals]
    xs = positions(ordinals_f, left, plot_w)
    row_dates = [date.fromordinal(ordinal).isoformat() for ordinal in ordinals]

    rows: list[CalendarRow] = []
    for ordinal, x, row_date in zip(ordinals, xs, row_dates):
        row_cells: list[CalendarCell | None] = []
        for index, side_cells in enumerate(per_side):
            found = side_cells.get(ordinal)
            if found is None:
                row_cells.append(None)
                continue
            period, token, number, _, _ = found
            row_cells.append(CalendarCell(
                period=period,
                period_text=format_period(period, frequencies[index]),
                value_text=token,
                value_display=format_value(token),
                number=number,
                y=y_for(index, number),
            ))
        rows.append(CalendarRow(
            ordinal=float(ordinal), x=x,
            period_text=format_date(row_date),
            cells=tuple(row_cells)))

    series: list[CalendarSeries] = []
    for index, side_cells in enumerate(per_side):
        # A break belongs to this side only: compare its own native indices. Rows where another
        # series observes an extra month are not gaps in a complete annual line.
        present = [(row_index, side_cells[ordinal][3])
                   for row_index, ordinal in enumerate(ordinals) if ordinal in side_cells]
        breaks: list[int] = []
        previous = None
        for row_index, native_index in present:
            if previous is not None and native_index - previous > 1:
                breaks.append(row_index)
            previous = native_index
        latest_index = present[-1][0]
        style = ("a", "b")[index] if len(labels) == 2 else GROUP_STYLES[index]
        series.append(CalendarSeries(
            label=labels[index], unit=units[index], style=style,
            frequency=frequencies[index], breaks=tuple(breaks),
            latest_index=latest_index))

    row_dates = [date.fromordinal(ordinal).isoformat() for ordinal in ordinals]
    return CalendarModel(
        kind="calendar", title=title, labels=labels, units=units,
        styles=tuple(item.style for item in series), frequencies=frequencies, dual=dual,
        name=_series_name(title, labels, units, dual),
        width=width, height=height, left=left, right=right, top=TOP, bottom=BOTTOM,
        rows=tuple(rows), series=tuple(series),
        ticks_a=tuple(YTick(value=t, text=text, y=y_of(t, lo_a, hi_a), zero=(not dual and t == 0))
                      for t, text in zip(ticks_a, texts_a)),
        ticks_b=tuple(YTick(value=t, text=text, y=y_of(t, lo_b, hi_b), zero=False)
                      for t, text in zip(ticks_b, texts_b)),
        lo_a=lo_a, hi_a=hi_a, lo_b=lo_b, hi_b=hi_b,
        interval_a=axis_interval(ticks_a, lo_a, hi_a),
        interval_b=axis_interval(ticks_b, lo_b, hi_b),
        unit_a=units[0], unit_b=units[1] if dual else units[0],
        x_ticks=tuple(XTick(index=i, ordinal=float(ordinals[i]), x=xs[i], text=text)
                      for i, text in _x_labels(row_dates)),
    )


__all__ = [
    "CalendarCell",
    "CalendarModel",
    "CalendarRow",
    "CalendarSeries",
    "MISSING_TEXT",
    "calendar_model",
]
