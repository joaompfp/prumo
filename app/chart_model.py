"""Prepared chart model: the one Python truth for chart geometry and reader strings.

`app.charts` renders SVG from this model; the interactive adapter's payload is serialised from
the same model, so the fallback, the canvas renderer and the point readout share periods,
coordinates, domains, ticks and exact display strings. Nothing here formats a value back from a
number: values are the stored tokens rendered by `app.formatting.format_value`.

The module is pure: no HTML, no database, no request state. A CMS reader can call
`line_model`/`comparison_model` and `app.interactive.build_payload` exactly as the built-in
pages do.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from app.formatting import (
    MONTHS_SHORT,
    decimal_or_none,
    format_axis,
    format_period,
    format_value,
)

WIDTH, HEIGHT = 880, 340
# Margins were enlarged with the readable SVG type scale. The left gutter must hold a
# publisher value such as "1 000 000" at 16.5 user units without clipping; the top gutter
# holds the 18-unit axis name.
LEFT, RIGHT, TOP, BOTTOM = 88, 30, 28, 62
RIGHT_DUAL = 156


def _text_width(text: str) -> int:
    """A conservative SVG text width at the 16.5-unit axis type scale.

    Digits are close to 9 units in Lato tabular; spaces and punctuation are narrower. This is
    an estimate for margin allocation only; it never formats or rounds a reader value.
    """
    return sum(9 if char.isdigit() else 5 for char in text)


def _left_gutter(texts: list[str], width: int, right: int) -> int:
    """Grow the left gutter for long publisher values, leaving at least 200 units of plot."""
    needed = max((_text_width(text) for text in texts), default=0) + 12
    return max(LEFT, min(needed, width - right - 200))


def calendar_position(period: str, frequency: str) -> float:
    """A sortable position for a canonical period, so gaps occupy real space on the x axis."""
    try:
        if frequency == "A" and len(period) == 4:
            return float(period)
        if frequency == "M" and len(period) == 7:
            year, month = period.split("-")
            return int(year) * 12 + int(month) - 1
        if frequency == "Q" and "-Q" in period:
            year, quarter = period.split("-Q")
            return int(year) * 4 + int(quarter) - 1
        if frequency == "S" and "-S" in period:
            year, semester = period.split("-S")
            return int(year) * 2 + int(semester) - 1
        if "T" in period:
            return datetime.fromisoformat(period).timestamp()
    except (TypeError, ValueError):
        pass
    return float("nan")


def ticks(lo: Decimal, hi: Decimal, target: int = 5) -> list[Decimal]:
    span = hi - lo
    if span <= 0:
        span = abs(hi) if hi else Decimal(1)
    raw = span / target
    exponent = raw.adjusted()
    magnitude = Decimal(10) ** exponent
    step = magnitude
    for multiplier in ("1", "2", "2.5", "5", "10"):
        step = magnitude * Decimal(multiplier)
        if step >= raw:
            break
    # Ticks must bound the data: the top gridline is never below the highest point.
    first = (lo / step).to_integral_value(rounding=ROUND_FLOOR) * step
    last = (hi / step).to_integral_value(rounding=ROUND_CEILING) * step
    out: list[Decimal] = []
    value = first
    guard = 0
    while value <= last + step / 1000 and guard < 20:
        out.append(value)
        value += step
        guard += 1
    return out


def year_indices(periods: list[str]) -> list[int]:
    """Indices at round 5- or 10-year boundaries, so the axis reads 2000, 2005, ..."""
    years = [int(p[:4]) for p in periods]
    first, last = years[0], years[-1]
    step = 5 if last - first <= 40 else 10
    wanted = [year for year in range(first, last + 1) if year % step == 0]
    if len(wanted) < 3:
        return []
    out: list[int] = []
    for year in wanted:
        try:
            index = years.index(year)
        except ValueError:
            continue
        if index not in out:
            out.append(index)
    return out


def x_labels(periods: list[str], frequency: str) -> list[tuple[int, str]]:
    if not periods:
        return []
    distinct_years = {p[:4] for p in periods if p[:4].isdigit()}
    years_only = len(distinct_years) >= 3
    indices = (year_indices(periods)
               if frequency in ("A", "M", "Q", "S") and all(p[:4].isdigit() for p in periods)
               else [])
    if not indices:
        if len(periods) <= 6:
            indices = list(range(len(periods)))
        else:
            indices = sorted({round(i * (len(periods) - 1) / 5) for i in range(6)})
    out = []
    for i in indices:
        period = periods[i]
        if years_only and period[:4].isdigit():
            label = period[:4]
        elif frequency == "M" and len(period) == 7:
            year, month = period.split("-")
            label = f"{MONTHS_SHORT[int(month) - 1]} {year}"
        elif frequency == "Q" and "-Q" in period:
            year, quarter = period.split("-Q")
            label = f"T{quarter} {year}"
        elif frequency == "S" and "-S" in period:
            year, semester = period.split("-S")
            label = f"S{semester} {year}"
        elif "T" in period and len(period) >= 16:
            # The period is canonical UTC; the hour label must not follow the browser timezone.
            label = period[11:16]
        else:
            label = format_period(period, frequency)
        out.append((i, label))
    return out


def padded_domain(nums: list[Decimal]) -> tuple[Decimal, Decimal, list[Decimal]]:
    """Padded bounds and nice ticks for one set of numbers, zero included when crossed."""
    lo, hi = min(nums), max(nums)
    if lo == hi:
        pad = abs(lo) * Decimal("0.1") or Decimal(1)
        lo, hi = lo - pad, hi + pad
    else:
        pad = (hi - lo) * Decimal("0.08")
        lo, hi = lo - pad, hi + pad
    if min(nums) < 0:
        lo, hi = min(lo, Decimal(0)), max(hi, Decimal(0))
    nice = ticks(lo, hi)
    if nice:
        lo, hi = min(lo, nice[0]), max(hi, nice[-1])
    return lo, hi, nice


def axis_interval(axis_ticks: list[Decimal], lo: Decimal, hi: Decimal) -> Decimal:
    """The uniform step ECharts must use, taken from the same ticks the SVG draws."""
    if len(axis_ticks) > 1:
        return axis_ticks[1] - axis_ticks[0]
    return hi - lo or Decimal(1)


_PERIOD_SHAPES = {
    "A": re.compile(r"\d{4}\Z"),
    "M": re.compile(r"\d{4}-\d{2}\Z"),
    "Q": re.compile(r"\d{4}-Q[1-4]\Z"),
    "S": re.compile(r"\d{4}-S[1-2]\Z"),
}
_ISO_STEP = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?\Z")


def expected_step(periods: list[str], frequency: str) -> float | None:
    """The x distance one period occupies, when its frequency and tokens are parseable.

    Annual, monthly, quarterly and semester tokens are exactly one ordinal apart; no month is
    ever converted to a fixed 30-day span. An ISO 8601 duration (`PT15M`, `PT1H`, `P1D`) fixes
    a timestamp step in seconds. An unknown shape returns None and lets the caller fall back.
    """
    shape = _PERIOD_SHAPES.get(frequency)
    if shape is not None:
        return 1.0 if periods and all(shape.fullmatch(p) for p in periods) else None
    duration = _ISO_STEP.fullmatch(frequency or "")
    if duration:
        days, hours, minutes = (int(part or 0) for part in duration.groups())
        seconds = days * 86400 + hours * 3600 + minutes * 60
        return float(seconds) if seconds else None
    return None


def break_indices(ordinals: list[float], step: float | None = None) -> tuple[int, ...]:
    """Point indices where a missing period must break the line.

    `step` is the expected distance between consecutive periods. It comes from the period
    tokens and frequency, so a two-point series can still show its gap: the median of the
    observed steps would call that one step typical. The fallback median is only for an
    unrecognised frequency. Indices address the existing points; a break never adds a point
    to the slider or the x axis.
    """
    steps = [ordinals[i] - ordinals[i - 1] for i in range(1, len(ordinals))]
    typical = step
    if typical is None:
        typical = sorted(steps)[(len(steps) - 1) // 2] if steps else 0.0
    return tuple(i for i, distance in enumerate(steps, start=1)
                 if typical and distance > typical * 1.5)


def positions(ordinals: list[float], left: float, plot_w: float) -> list[float]:
    """Proportional x coordinates, or a centred point when every period is the same instant."""
    first, last = ordinals[0], ordinals[-1]
    if first == last:
        return [left + plot_w / 2 for _ in ordinals]
    return [left + (o - first) / (last - first) * plot_w for o in ordinals]


def ordinals_for(periods: list[str], frequency: str) -> list[float]:
    out = [calendar_position(p, frequency) for p in periods]
    if any(o != o for o in out):  # NaN: fall back to even spacing
        return [float(i) for i in range(len(periods))]
    return out


@dataclass(frozen=True)
class LinePoint:
    period: str
    period_text: str
    value_text: str
    value_display: str
    number: Decimal
    ordinal: float
    x: float
    y: float


@dataclass(frozen=True)
class YTick:
    value: Decimal
    text: str
    y: float
    zero: bool


@dataclass(frozen=True)
class XTick:
    index: int
    ordinal: float
    x: float
    text: str


@dataclass(frozen=True)
class LineChartModel:
    kind: str
    title: str
    unit: str
    display_unit: str
    name: str
    frequency: str
    width: int
    height: int
    left: int
    right: int
    top: int
    bottom: int
    points: tuple[LinePoint, ...]
    y_ticks: tuple[YTick, ...]
    x_ticks: tuple[XTick, ...]
    lo: Decimal
    hi: Decimal
    interval: Decimal
    last_x: float
    last_y: float
    last_label: str
    last_anchor: str
    last_dx: int
    last_label_y: float


def line_model(points: list[dict], *, frequency: str, title: str, unit: str = "",
               display_unit: str | None = None,
               width: int = WIDTH, height: int = HEIGHT) -> LineChartModel | None:
    """Prepare one series; None when there is nothing numeric to draw."""
    values = [(p["period"], decimal_or_none(p["value_text"]), p["value_text"]) for p in points]
    values = [v for v in values if v[1] is not None]
    if not values:
        return None
    periods = [v[0] for v in values]
    numbers = [v[1] for v in values]
    lo, hi, nice = padded_domain(numbers)
    tick_texts = [format_axis(t) for t in nice]
    left = _left_gutter(tick_texts, width, RIGHT)

    plot_w = width - left - RIGHT
    plot_h = height - TOP - BOTTOM
    span = hi - lo or Decimal(1)

    def y(number: Decimal) -> float:
        return TOP + float((hi - number) / span * plot_h)

    ordinals = ordinals_for(periods, frequency)
    xs = positions(ordinals, left, plot_w)
    prepared = tuple(
        LinePoint(period=period, period_text=format_period(period, frequency),
                  value_text=token, value_display=format_value(token), number=number,
                  ordinal=ordinal, x=x, y=y(number))
        for (period, number, token), ordinal, x in zip(values, ordinals, xs))
    name = title + (f" ({unit})" if unit else "")
    last_x, last_y = prepared[-1].x, prepared[-1].y
    lx, ly = round(last_x, 1), round(last_y, 1)
    anchor = "end" if lx > width - 40 else "middle"
    return LineChartModel(
        kind="line", title=title, unit=unit,
        display_unit=unit if display_unit is None else display_unit,
        name=name, frequency=frequency,
        width=width, height=height, left=left, right=RIGHT, top=TOP, bottom=BOTTOM,
        points=prepared,
        y_ticks=tuple(YTick(value=t, text=text, y=y(t), zero=t == 0)
                      for t, text in zip(nice, tick_texts)),
        x_ticks=tuple(XTick(index=i, ordinal=ordinals[i], x=xs[i], text=text)
                      for i, text in x_labels(periods, frequency)),
        lo=lo, hi=hi, interval=axis_interval(nice, lo, hi),
        last_x=last_x, last_y=last_y, last_label=format_value(values[-1][2]),
        last_anchor=anchor, last_dx=-8 if anchor == "end" else 0,
        last_label_y=float(ly - 18 if ly - 18 >= TOP + 10 else ly + 26))


@dataclass(frozen=True)
class ComparisonValue:
    number: Decimal
    value_text: str
    value_display: str
    y: float


@dataclass(frozen=True)
class ComparisonPoint:
    period: str
    period_text: str
    ordinal: float
    x: float
    a: ComparisonValue
    b: ComparisonValue


@dataclass(frozen=True)
class LastMark:
    y: float
    label: str
    suffix: str
    label_y: float


@dataclass(frozen=True)
class ComparisonModel:
    kind: str
    title: str
    labels: tuple[str, str]
    unit_a: str
    unit_b: str
    dual: bool
    name: str
    frequency: str
    width: int
    height: int
    left: int
    right: int
    top: int
    bottom: int
    points: tuple[ComparisonPoint, ...]
    ticks_a: tuple[YTick, ...]
    ticks_b: tuple[YTick, ...]
    lo_a: Decimal
    hi_a: Decimal
    lo_b: Decimal
    hi_b: Decimal
    interval_a: Decimal
    interval_b: Decimal
    x_ticks: tuple[XTick, ...]
    breaks: tuple[int, ...]
    last_x: float
    last_anchor: str
    last_dx: int
    marks: tuple[LastMark, ...]


def comparison_model(points: list[dict], *, frequency: str, title: str,
                     labels: tuple[str, str], unit_a: str, unit_b: str | None = None,
                     dual: bool | None = None, width: int = WIDTH,
                     height: int = HEIGHT) -> ComparisonModel | None:
    """Prepare a curated pair; None when no common period is drawable.

    `dual` is the catalogue's decision and wins over the unit comparison. Nothing is
    interpolated: a missing token drops the period for both lines. A gap breaks the line via
    `breaks`, which the adapter turns into null sentinels.
    """
    rows = []
    for p in points:
        a, b = decimal_or_none(p["a"]), decimal_or_none(p["b"])
        if a is None or b is None:
            continue
        rows.append((p["period"], a, b, p["a"], p["b"]))
    if not rows:
        return None

    periods = [r[0] for r in rows]
    if dual is None:
        dual = unit_b is not None and unit_b != unit_a
    if dual:
        lo_a, hi_a, ticks_a = padded_domain([r[1] for r in rows])
        lo_b, hi_b, ticks_b = padded_domain([r[2] for r in rows])
    else:
        lo_a, hi_a, ticks_a = padded_domain([r[1] for r in rows] + [r[2] for r in rows])
        lo_b, hi_b, ticks_b = lo_a, hi_a, ticks_a

    right = RIGHT_DUAL if dual else RIGHT
    texts_a = [format_axis(t) for t in ticks_a]
    texts_b = [format_axis(t) for t in ticks_b] if dual else []
    left = _left_gutter(texts_a + texts_b, width, right)
    plot_w, plot_h = width - left - right, height - TOP - BOTTOM

    def y_of(number: Decimal, lo: Decimal, hi: Decimal) -> float:
        span = hi - lo or Decimal(1)
        return TOP + float((hi - number) / span * plot_h)

    ordinals = ordinals_for(periods, frequency)
    xs = positions(ordinals, left, plot_w)
    prepared = tuple(
        ComparisonPoint(
            period=period, period_text=format_period(period, frequency), ordinal=ordinal, x=x,
            a=ComparisonValue(number=a, value_text=token_a, value_display=format_value(token_a),
                              y=y_of(a, lo_a, hi_a)),
            b=ComparisonValue(number=b, value_text=token_b, value_display=format_value(token_b),
                              y=y_of(b, lo_b, hi_b)))
        for (period, a, b, token_a, token_b), ordinal, x in zip(rows, ordinals, xs))

    name = f"{title}: {labels[0]} ({unit_a}) e {labels[1]} ({unit_b or unit_a})"
    last = prepared[-1]
    lx = round(last.x, 1)
    anchor = "end" if lx > width - right - 40 else "middle"
    marks = [LastMark(y=last.a.y, label=last.a.value_display, suffix="a", label_y=0.0)]
    if abs(last.a.y - last.b.y) >= 30:
        marks.append(LastMark(y=last.b.y, label=last.b.value_display, suffix="b", label_y=0.0))
    marks = tuple(
        LastMark(y=m.y, label=m.label, suffix=m.suffix,
                 label_y=float(m.y - 18 if m.y - 18 >= TOP + 10 else m.y + 26))
        for m in marks)
    return ComparisonModel(
        kind="comparison", title=title, labels=labels, unit_a=unit_a,
        unit_b=unit_b or unit_a, dual=bool(dual), name=name, frequency=frequency,
        width=width, height=height, left=left, right=right, top=TOP, bottom=BOTTOM,
        points=prepared,
        ticks_a=tuple(YTick(value=t, text=text, y=y_of(t, lo_a, hi_a),
                            zero=(not dual and t == 0))
                      for t, text in zip(ticks_a, texts_a)),
        ticks_b=tuple(YTick(value=t, text=text, y=y_of(t, lo_b, hi_b), zero=False)
                      for t, text in zip(ticks_b, texts_b)),
        lo_a=lo_a, hi_a=hi_a, lo_b=lo_b, hi_b=hi_b,
        interval_a=axis_interval(ticks_a, lo_a, hi_a),
        interval_b=axis_interval(ticks_b, lo_b, hi_b),
        x_ticks=tuple(XTick(index=i, ordinal=ordinals[i], x=xs[i], text=text)
                      for i, text in x_labels(periods, frequency)),
        breaks=break_indices(ordinals, expected_step(periods, frequency)),
        last_x=last.x, last_anchor=anchor, last_dx=-6 if anchor == "end" else 0,
        marks=marks)
