"""Inline SVG charts. No JavaScript, no external library, no inline style attribute.

The chart is decoration over a table that the template always renders: values keep their
stored precision, the axis is the only rounded thing on the page. Geometry, domains, ticks and
the exact point strings come from `app.chart_model`; this module only turns a prepared model
into SVG, so the interactive canvas and the fallback cannot describe different charts.
"""
from markupsafe import Markup, escape

from app.chart_model import (  # noqa: F401 - WIDTH/HEIGHT kept as the module's documented size
    BOTTOM,
    HEIGHT,
    LEFT,
    RIGHT,
    RIGHT_DUAL,
    TOP,
    WIDTH,
    comparison_model,
    line_model,
)
from app.formatting import decimal_or_none


def line_chart(points: list[dict], *, frequency: str, title: str, unit: str = "",
               width: int = WIDTH, height: int = HEIGHT) -> Markup:
    """One series as an SVG line. `points` are dicts with `period` and `value_text`, oldest
    first. Returns an empty-state paragraph when there is nothing numeric to draw."""
    return line_svg(line_model(points, frequency=frequency, title=title, unit=unit,
                               width=width, height=height))


def line_svg(model) -> Markup:
    """The SVG for an already prepared line model (the page renders it once)."""
    if model is None:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')
    width, height = model.width, model.height

    parts: list[str] = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(model.name)}" preserveAspectRatio="xMidYMid meet">',
        f"<title>{escape(model.name)}</title>",
    ]
    for tick in model.y_ticks:
        ty = round(tick.y, 1)
        cls = "chart-grid chart-zero" if tick.zero else "chart-grid"
        parts.append(f'<line class="{cls}" x1="{LEFT}" y1="{ty}" x2="{width - RIGHT}" '
                     f'y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{LEFT - 8}" y="{ty + 4}" '
                     f'text-anchor="end">{escape(tick.text)}</text>')

    area = " ".join(f"{'M' if i == 0 else 'L'}{round(p.x, 1)},{round(p.y, 1)}"
                    for i, p in enumerate(model.points))
    parts.append(f'<path class="chart-line" d="{area}" />')

    for point in model.points:
        cx, cy = round(point.x, 1), round(point.y, 1)
        parts.append(f'<circle class="chart-point" cx="{cx}" cy="{cy}" r="7">'
                     f'<title>{escape(point.period_text)}: '
                     f'{escape(point.value_display)} {escape(model.display_unit)}</title></circle>')
    lx, ly = round(model.last_x, 1), round(model.last_y, 1)
    parts.append(f'<circle class="chart-last" cx="{lx}" cy="{ly}" r="3.5" />')
    parts.append(f'<text class="chart-last-label" x="{round(model.last_x + model.last_dx, 1)}" '
                 f'y="{round(model.last_label_y, 1)}" text-anchor="{model.last_anchor}">'
                 f'{escape(model.last_label)}</text>')

    for tick in model.x_ticks:
        parts.append(f'<text class="chart-tick" x="{round(tick.x, 1)}" '
                     f'y="{height - 14}" text-anchor="middle">{escape(tick.text)}</text>')
    parts.append("</svg>")
    return Markup("".join(parts))


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
    return comparison_svg(comparison_model(points, frequency=frequency, title=title,
                                           labels=labels, unit_a=unit_a, unit_b=unit_b,
                                           dual=dual, width=width, height=height))


def comparison_svg(model) -> Markup:
    """The SVG and legend for an already prepared comparison model."""
    if model is None:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')
    width, height = model.width, model.height
    right = model.right
    parts = [f'<svg class="chart chart-compare" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{escape(model.name)}" preserveAspectRatio="xMidYMid meet">',
             f"<title>{escape(model.name)}</title>"]

    for tick in model.ticks_a:
        ty = round(tick.y, 1)
        # With two scales the highlighted "zero" belongs to the left series only, so a thick line
        # there would read as zero for both.
        cls = "chart-grid chart-zero" if tick.zero else "chart-grid"
        parts.append(f'<line class="{cls}" x1="{LEFT}" y1="{ty}" x2="{width - right}" '
                     f'y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{LEFT - 8}" y="{ty + 4}" '
                     f'text-anchor="end">{escape(tick.text)}</text>')
    if model.dual:
        for tick in model.ticks_b:
            ty = round(tick.y, 1)
            parts.append(f'<text class="chart-tick" x="{width - right + 8}" y="{ty + 4}" '
                         f'text-anchor="start">{escape(tick.text)}</text>')

    parts.append(f'<text class="chart-axis-label" x="{LEFT - 8}" y="{TOP - 6}" '
                 f'text-anchor="end">{escape(model.unit_a)}</text>')
    if model.dual:
        # Anchored to the viewBox edge: a long unit ("milhões de euros") grows leftwards instead
        # of past the right border, where it would be clipped.
        parts.append(f'<text class="chart-axis-label" x="{width - 4}" y="{TOP - 6}" '
                     f'text-anchor="end">{escape(model.unit_b)}</text>')

    for index, value, cls in ((1, lambda p: p.a, "chart-line-a"),
                              (2, lambda p: p.b, "chart-line-b")):
        commands = [f"{'M' if i == 0 or i in model.breaks else 'L'}"
                    f"{round(p.x, 1)},{round(value(p).y, 1)}"
                    for i, p in enumerate(model.points)]
        d = " ".join(commands)
        parts.append(f'<path class="chart-line {cls}" d="{d}" />')

    for point in model.points:
        cx = round(point.x, 1)
        for cy, token, label, unit in (
                (point.a.y, point.a.value_display, model.labels[0], model.unit_a),
                (point.b.y, point.b.value_display, model.labels[1], model.unit_b)):
            parts.append(f'<circle class="chart-point" cx="{cx}" cy="{round(cy, 1)}" r="7">'
                         f'<title>{escape(label)} - {escape(point.period_text)}: '
                         f'{escape(token)} {escape(unit)}</title></circle>')

    lx = round(model.last_x, 1)
    for mark in model.marks:
        parts.append(f'<text class="chart-last-label chart-last-{mark.suffix}" '
                     f'x="{round(model.last_x + model.last_dx, 1)}" '
                     f'y="{round(mark.label_y, 1)}" text-anchor="{model.last_anchor}">'
                     f'{escape(mark.label)}</text>')

    # A dot on each last point: a pair with one common period draws a one-command path, which is
    # invisible, so the dot is what makes the value locatable.
    for suffix, cy in (("a", model.points[-1].a.y), ("b", model.points[-1].b.y)):
        parts.append(f'<circle class="chart-last chart-last-{suffix}" cx="{lx}" '
                     f'cy="{round(cy, 1)}" r="3.5" />')

    for tick in model.x_ticks:
        parts.append(f'<text class="chart-tick" x="{round(tick.x, 1)}" '
                     f'y="{height - 14}" text-anchor="middle">{escape(tick.text)}</text>')
    parts.append("</svg>")

    last = model.points[-1]
    legend = (
        '<ul class="legend">'
        f'<li><span class="legend-swatch swatch-a" aria-hidden="true"></span>{escape(model.labels[0])}'
        f'<span class="legend-value">{escape(last.a.value_display)} {escape(model.unit_a)}</span>'
        '</li>'
        f'<li><span class="legend-swatch swatch-b" aria-hidden="true"></span>{escape(model.labels[1])}'
        f'<span class="legend-value">{escape(last.b.value_display)} '
        f'{escape(model.unit_b)}</span></li>'
        '</ul>')
    return Markup("".join(parts) + legend)


def chart_svg(model) -> Markup:
    """Render a prepared model of either kind; used by the detail templates."""
    if model is None:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')
    return line_svg(model) if model.kind == "line" else comparison_svg(model)


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
