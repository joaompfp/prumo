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
        index = next(i for i, value in enumerate(years) if value == year)
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
    numbers = [v[1] for v in values]
    lo, hi = min(numbers), max(numbers)
    if lo == hi:
        pad = abs(lo) * Decimal("0.1") or Decimal(1)
        lo, hi = lo - pad, hi + pad
    else:
        pad = (hi - lo) * Decimal("0.08")
        lo, hi = lo - pad, hi + pad
    if min(numbers) < 0:
        lo, hi = min(lo, Decimal(0)), max(hi, Decimal(0))
    ticks = _ticks(lo, hi)
    if ticks:
        lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])

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
