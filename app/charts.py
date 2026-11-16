"""Inline SVG charts. No JavaScript, no external library, no inline style attribute.

The chart is decoration over a table that the template always renders: values keep their
stored precision, the axis is the only rounded thing on the page.
"""
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from markupsafe import Markup, escape

from app.formatting import MONTHS_SHORT, decimal_or_none, format_axis, format_period, format_value

WIDTH, HEIGHT = 880, 340
LEFT, RIGHT, TOP, BOTTOM = 68, 20, 18, 44
RIGHT_DUAL = 104


def _ordinal(period: str, frequency: str) -> float:
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


def _ticks(lo: Decimal, hi: Decimal, target: int = 5) -> list[Decimal]:
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
    ticks: list[Decimal] = []
    value = first
    guard = 0
    while value <= last + step / 1000 and guard < 20:
        ticks.append(value)
        value += step
        guard += 1
    return ticks


def _year_indices(periods: list[str]) -> list[int]:
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


def _x_labels(periods: list[str], frequency: str) -> list[tuple[int, str]]:
    if not periods:
        return []
    distinct_years = {p[:4] for p in periods if p[:4].isdigit()}
    years_only = len(distinct_years) >= 3
    indices = (_year_indices(periods)
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
            label = format_period(period, frequency)[:5]
        else:
            label = format_period(period, frequency)
        out.append((i, label))
    return out


def line_chart(points: list[dict], *, frequency: str, title: str, unit: str = "",
               width: int = WIDTH, height: int = HEIGHT) -> Markup:
    """One series as an SVG line. `points` are dicts with `period` and `value_text`, oldest
    first. Returns an empty-state paragraph when there is nothing numeric to draw."""
    values = [(p["period"], decimal_or_none(p["value_text"]), p["value_text"]) for p in points]
    values = [v for v in values if v[1] is not None]
    if not values:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')

    periods = [v[0] for v in values]
    numbers = [v[1] for v in values if v[1] is not None]
    lo, hi, ticks = _range(numbers)

    plot_w = width - LEFT - RIGHT
    plot_h = height - TOP - BOTTOM
    span = hi - lo or Decimal(1)

    def y(number: Decimal) -> float:
        return float(TOP + (hi - number) / span * plot_h)

    ordinals = [_ordinal(p, frequency) for p in periods]
    if any(o != o for o in ordinals):  # NaN: fall back to even spacing
        ordinals = [float(i) for i in range(len(periods))]
    first, last = ordinals[0], ordinals[-1]
    if first == last:
        xs = [LEFT + plot_w / 2 for _ in ordinals]
    else:
        xs = [LEFT + (o - first) / (last - first) * plot_w for o in ordinals]

    parts: list[str] = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title + (f' ({unit})' if unit else ''))}" '
        f'preserveAspectRatio="xMidYMid meet">',
        f"<title>{escape(title + (f' ({unit})' if unit else ''))}</title>",
    ]
    for tick in ticks:
        ty = round(y(tick), 1)
        cls = "chart-grid chart-zero" if tick == 0 else "chart-grid"
        parts.append(f'<line class="{cls}" x1="{LEFT}" y1="{ty}" x2="{width - RIGHT}" '
                     f'y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{LEFT - 8}" y="{ty + 4}" '
                     f'text-anchor="end">{escape(format_axis(tick))}</text>')

    area = " ".join(f"{'M' if i == 0 else 'L'}{round(xs[i], 1)},{round(y(numbers[i]), 1)}"
                    for i in range(len(xs)))
    parts.append(f'<path class="chart-line" d="{area}" />')

    for i, (period, number, token) in enumerate(values):
        cx, cy = round(xs[i], 1), round(y(number), 1)
        parts.append(f'<circle class="chart-point" cx="{cx}" cy="{cy}" r="7">'
                     f'<title>{escape(format_period(period, frequency))}: '
                     f'{escape(format_value(token))} {escape(unit)}</title></circle>')
    lx, ly = round(xs[-1], 1), round(y(numbers[-1]), 1)
    parts.append(f'<circle class="chart-last" cx="{lx}" cy="{ly}" r="3.5" />')
    anchor = "end" if lx > width - 40 else "middle"
    dx = -6 if anchor == "end" else 0
    label_y = ly - 12 if ly - 12 >= TOP + 10 else ly + 20
    parts.append(f'<text class="chart-last-label" x="{round(lx + dx, 1)}" '
                 f'y="{round(label_y, 1)}" text-anchor="{anchor}">'
                 f'{escape(format_value(values[-1][2]))}</text>')

    for index, label in _x_labels(periods, frequency):
        parts.append(f'<text class="chart-tick" x="{round(xs[index], 1)}" '
                     f'y="{height - 14}" text-anchor="middle">{escape(label)}</text>')
    parts.append("</svg>")
    return Markup("".join(parts))


def _range(nums: list[Decimal]) -> tuple[Decimal, Decimal, list[Decimal]]:
    """Padded bounds and nice ticks for one set of numbers, zero included when it is crossed."""
    lo, hi = min(nums), max(nums)
    if lo == hi:
        pad = abs(lo) * Decimal("0.1") or Decimal(1)
        lo, hi = lo - pad, hi + pad
    else:
        pad = (hi - lo) * Decimal("0.08")
        lo, hi = lo - pad, hi + pad
    if min(nums) < 0:
        lo, hi = min(lo, Decimal(0)), max(hi, Decimal(0))
    ticks = _ticks(lo, hi)
    if ticks:
        lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    return lo, hi, ticks


def two_series_chart(points: list[dict], *, frequency: str, title: str, labels: tuple[str, str],
                     unit_a: str, unit_b: str | None = None, dual: bool | None = None,
                     width: int = WIDTH, height: int = HEIGHT) -> Markup:
    """Two series as two SVG lines over the periods the caller aligned.

    `points` are dicts with `period`, `a` and `b` (the stored tokens), oldest first. Equal units
    share one axis; different units get two independent axes, gridlines from the left one and both
    sides labelled, because two scales on one gridline set would let any two series look related.
    `dual` is the catalogue's decision for the pair and wins over the unit comparison: a level and
    a rate can share the `%` token and still be two different things. Nothing is interpolated: a
    missing token drops that period for both lines, and a gap breaks the line instead of crossing it.
    """
    rows = []
    for p in points:
        a, b = decimal_or_none(p["a"]), decimal_or_none(p["b"])
        if a is None or b is None:
            continue
        rows.append((p["period"], a, b, p["a"], p["b"]))
    if not rows:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')

    periods = [r[0] for r in rows]
    if dual is None:
        dual = unit_b is not None and unit_b != unit_a
    if dual:
        lo_a, hi_a, ticks_a = _range([r[1] for r in rows])
        lo_b, hi_b, ticks_b = _range([r[2] for r in rows])
    else:
        lo_a, hi_a, ticks_a = _range([r[1] for r in rows] + [r[2] for r in rows])
        lo_b, hi_b, ticks_b = lo_a, hi_a, ticks_a

    # A dual axis needs room for two-digit tick labels and a unit as long as "milhões de euros";
    # with the single-axis margin both are clipped at the viewBox edge and the axis reads 15/10
    # instead of 150/100.
    right = RIGHT_DUAL if dual else RIGHT
    plot_w, plot_h = width - LEFT - right, height - TOP - BOTTOM

    def y_of(number: Decimal, lo: Decimal, hi: Decimal) -> float:
        span = hi - lo or Decimal(1)
        return float(TOP + (hi - number) / span * plot_h)

    ordinals = [_ordinal(p, frequency) for p in periods]
    if any(o != o for o in ordinals):  # NaN: fall back to even spacing
        ordinals = [float(i) for i in range(len(periods))]
    first, last = ordinals[0], ordinals[-1]
    xs = ([LEFT + plot_w / 2 for _ in ordinals] if first == last
          else [LEFT + (o - first) / (last - first) * plot_w for o in ordinals])

    name = f"{title}: {labels[0]} ({unit_a}) e {labels[1]} ({unit_b or unit_a})"
    parts = [f'<svg class="chart chart-compare" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{escape(name)}" preserveAspectRatio="xMidYMid meet">',
             f"<title>{escape(name)}</title>"]

    for tick in ticks_a:
        ty = round(y_of(tick, lo_a, hi_a), 1)
        # With two scales the highlighted "zero" belongs to the left series only, so a thick line
        # there would read as zero for both.
        cls = "chart-grid" if dual or tick != 0 else "chart-grid chart-zero"
        parts.append(f'<line class="{cls}" x1="{LEFT}" y1="{ty}" x2="{width - right}" '
                     f'y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{LEFT - 8}" y="{ty + 4}" '
                     f'text-anchor="end">{escape(format_axis(tick))}</text>')
    if dual:
        for tick in ticks_b:
            ty = round(y_of(tick, lo_b, hi_b), 1)
            parts.append(f'<text class="chart-tick" x="{width - right + 8}" y="{ty + 4}" '
                         f'text-anchor="start">{escape(format_axis(tick))}</text>')

    parts.append(f'<text class="chart-axis-label" x="{LEFT - 8}" y="{TOP - 6}" '
                 f'text-anchor="end">{escape(unit_a)}</text>')
    if dual:
        # Anchored to the viewBox edge: a long unit ("milhões de euros") grows leftwards instead
        # of past the right border, where it would be clipped.
        parts.append(f'<text class="chart-axis-label" x="{width - 4}" y="{TOP - 6}" '
                     f'text-anchor="end">{escape(unit_b)}</text>')

    # A period missing from the middle must break the line, not be crossed by it: compare every
    # step with the typical step of this pair.
    steps = [ordinals[i] - ordinals[i - 1] for i in range(1, len(ordinals))]
    typical = sorted(steps)[(len(steps) - 1) // 2] if steps else 0.0
    breaks = {i for i, step in enumerate(steps, start=1) if typical and step > typical * 1.5}

    for index, lo, hi, cls in ((1, lo_a, hi_a, "chart-line-a"), (2, lo_b, hi_b, "chart-line-b")):
        commands = [f"{'M' if i == 0 or i in breaks else 'L'}"
                    f"{round(xs[i], 1)},{round(y_of(row[index], lo, hi), 1)}"
                    for i, row in enumerate(rows)]
        d = " ".join(commands)
        parts.append(f'<path class="chart-line {cls}" d="{d}" />')

    for i, (period, a, b, token_a, token_b) in enumerate(rows):
        cx = round(xs[i], 1)
        for cy, token, label, unit in ((y_of(a, lo_a, hi_a), token_a, labels[0], unit_a),
                                       (y_of(b, lo_b, hi_b), token_b, labels[1],
                                        unit_b or unit_a)):
            parts.append(f'<circle class="chart-point" cx="{cx}" cy="{round(cy, 1)}" r="7">'
                         f'<title>{escape(label)} — {escape(format_period(period, frequency))}: '
                         f'{escape(format_value(token))} {escape(unit)}</title></circle>')

    # One label per line; when the two ends sit close, the second is dropped and the legend
    # carries both values, rather than stacking two labels on the same spot.
    last_y_a = y_of(rows[-1][1], lo_a, hi_a)
    last_y_b = y_of(rows[-1][2], lo_b, hi_b)
    lx = round(xs[-1], 1)
    anchor = "end" if lx > width - right - 40 else "middle"
    dx = -6 if anchor == "end" else 0
    marks = [(last_y_a, format_value(rows[-1][3]), "a")]
    if abs(last_y_a - last_y_b) >= 22:
        marks.append((last_y_b, format_value(rows[-1][4]), "b"))
    for ly, text, suffix in marks:
        label_y = ly - 12 if ly - 12 >= TOP + 10 else ly + 20
        parts.append(f'<text class="chart-last-label chart-last-{suffix}" '
                     f'x="{round(lx + dx, 1)}" y="{round(label_y, 1)}" '
                     f'text-anchor="{anchor}">{escape(text)}</text>')

    # A dot on each last point: a pair with one common period draws a one-command path, which is
    # invisible, so the dot is what makes the value locatable.
    for cy, suffix in ((last_y_a, "a"), (last_y_b, "b")):
        parts.append(f'<circle class="chart-last chart-last-{suffix}" cx="{lx}" '
                     f'cy="{round(cy, 1)}" r="3.5" />')

    for index, label in _x_labels(periods, frequency):
        parts.append(f'<text class="chart-tick" x="{round(xs[index], 1)}" '
                     f'y="{height - 14}" text-anchor="middle">{escape(label)}</text>')
    parts.append("</svg>")

    legend = (
        '<ul class="legend">'
        f'<li><span class="legend-swatch swatch-a" aria-hidden="true"></span>{escape(labels[0])}'
        f'<span class="legend-value">{escape(format_value(rows[-1][3]))} {escape(unit_a)}</span>'
        '</li>'
        f'<li><span class="legend-swatch swatch-b" aria-hidden="true"></span>{escape(labels[1])}'
        f'<span class="legend-value">{escape(format_value(rows[-1][4]))} '
        f'{escape(unit_b or unit_a)}</span></li>'
        '</ul>')
    return Markup("".join(parts) + legend)


def sparkline(points: list[dict], *, width: int = 132, height: int = 40) -> Markup:
    """A bare trend line for a card: no axes, no labels, no meaning beyond direction."""
    numbers = [n for n in (decimal_or_none(p["value_text"]) for p in points) if n is not None]
    if not numbers:
        return Markup("")
    if len(numbers) == 1:
        return Markup(f'<svg class="spark" viewBox="0 0 {width} {height}" aria-hidden="true">'
                      f'<circle class="chart-last" cx="{width / 2:.0f}" cy="{height / 2:.0f}" '
                      f'r="2.5" /></svg>')
    lo, hi = min(numbers), max(numbers)
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    pad = (height - 8)
    xs = [4 + i * (width - 8) / (len(numbers) - 1) for i in range(len(numbers))]
    ys = [4 + float((hi - n) / (hi - lo)) * pad for n in numbers]
    line = " ".join(f"{'M' if i == 0 else 'L'}{round(xs[i], 1)},{round(ys[i], 1)}"
                    for i in range(len(xs)))
    return Markup(f'<svg class="spark" viewBox="0 0 {width} {height}" aria-hidden="true">'
                  f'<path class="spark-line" d="{line}" />'
                  f'<circle class="spark-end" cx="{round(xs[-1], 1)}" '
                  f'cy="{round(ys[-1], 1)}" r="2.2" /></svg>')
