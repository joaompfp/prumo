"""Inline SVG charts. No JavaScript, no external library, no inline style attribute.

The chart is decoration over a table that the template always renders: values keep their
stored precision, the axis is the only rounded thing on the page. Geometry, domains, ticks and
the exact point strings come from `app.chart_model`; this module only turns a prepared model
into SVG, so the interactive canvas and the fallback cannot describe different charts.
"""
from markupsafe import Markup, escape

from app.calendar_model import CalendarModel
from app.calendar_svg import calendar_legend, calendar_plot, calendar_svg
from app.chart_model import (  # noqa: F401 - WIDTH/HEIGHT kept as the module's documented size
    BOTTOM,
    HEIGHT,
    LEFT,
    RIGHT,
    RIGHT_DUAL,
    TOP,
    WIDTH,
    comparison_model,
    group_model,
    line_model,
)
from app.formatting import decimal_or_none


def line_chart(points: list[dict], *, frequency: str, title: str, unit: str = "",
               width: int = WIDTH, height: int = HEIGHT) -> Markup:
    """One series as an SVG line. `points` are dicts with `period` and `value_text`, oldest
    first. Returns an empty-state paragraph when there is nothing numeric to draw."""
    return line_svg(line_model(points, frequency=frequency, title=title, unit=unit,
                               width=width, height=height))


def _x_tick_markup(model) -> list[str]:
    """Keep enlarged endpoint labels inside the shared SVG viewBox."""
    labels = []
    for index, tick in enumerate(model.x_ticks):
        anchor = ("start" if index == 0 else "end" if index == len(model.x_ticks) - 1
                  else "middle") if len(model.x_ticks) > 1 else "middle"
        labels.append(f'<text class="chart-tick" x="{round(tick.x, 1)}" '
                      f'y="{model.height - 20}" text-anchor="{anchor}">'
                      f'{escape(tick.text)}</text>')
    return labels


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
        parts.append(f'<line class="{cls}" x1="{model.left}" y1="{ty}" x2="{width - RIGHT}" '
                     f'y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{model.left - 11}" y="{ty + 7}" '
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

    parts.extend(_x_tick_markup(model))
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


def group_chart(points: list[dict], *, frequency: str, title: str,
                labels: tuple[str, ...], unit: str = "", width: int = WIDTH,
                height: int = HEIGHT) -> Markup:
    """Three to six same-unit series on one shared axis, with the same legend and geometry.

    `points` are dicts with `period` and `values`, the exact stored tokens in label order. The
    first series uses the Carmim style; every other series keeps a distinct colour and dash. A
    missing or non-finite token drops the whole period, never one country.
    """
    return comparison_svg(group_model(points, frequency=frequency, title=title, labels=labels,
                                      unit=unit, width=width, height=height))


def _comparison_plot(model) -> Markup:
    """The comparison SVG alone; the shell renders the key outside the canvas overlay."""
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
        parts.append(f'<line class="{cls}" x1="{model.left}" y1="{ty}" x2="{width - right}" '
                     f'y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{model.left - 11}" y="{ty + 7}" '
                     f'text-anchor="end">{escape(tick.text)}</text>')
    if model.dual:
        for tick in model.ticks_b:
            ty = round(tick.y, 1)
            parts.append(f'<text class="chart-tick" x="{width - right + 11}" y="{ty + 7}" '
                         f'text-anchor="start">{escape(tick.text)}</text>')

    # Unit names grow into the plot, not off the left edge of the viewBox.
    parts.append(f'<text class="chart-axis-label" x="{model.left}" y="{TOP - 9}" '
                 f'text-anchor="start">{escape(model.unit_a)}</text>')
    if model.dual:
        # Anchored to the viewBox edge: a long unit ("milhões de euros") grows leftwards instead
        # of past the right border, where it would be clipped.
        parts.append(f'<text class="chart-axis-label" x="{width - 7}" y="{TOP - 9}" '
                     f'text-anchor="end">{escape(model.unit_b)}</text>')

    for index, style in enumerate(model.styles):
        commands = [f"{'M' if i == 0 or i in model.breaks else 'L'}"
                    f"{round(p.x, 1)},{round(p.values[index].y, 1)}"
                    for i, p in enumerate(model.points)]
        d = " ".join(commands)
        parts.append(f'<path class="chart-line chart-line-{style}" d="{d}" />')

    for point in model.points:
        cx = round(point.x, 1)
        for index, value in enumerate(point.values):
            parts.append(f'<circle class="chart-point" cx="{cx}" cy="{round(value.y, 1)}" r="7">'
                         f'<title>{escape(model.labels[index])} - '
                         f'{escape(point.period_text)}: '
                         f'{escape(value.value_display)} {escape(model.units[index])}'
                         f'</title></circle>')

    lx = round(model.last_x, 1)
    for mark in model.marks:
        parts.append(f'<text class="chart-last-label chart-last-{mark.suffix}" '
                     f'x="{round(model.last_x + model.last_dx, 1)}" '
                     f'y="{round(mark.label_y, 1)}" text-anchor="{model.last_anchor}">'
                     f'{escape(mark.label)}</text>')

    # A dot on each last point: a pair with one common period draws a one-command path, which is
    # invisible, so the dot is what makes the value locatable.
    for index, style in enumerate(model.styles):
        parts.append(f'<circle class="chart-last chart-last-{style}" cx="{lx}" '
                     f'cy="{round(model.points[-1].values[index].y, 1)}" r="3.5" />')

    parts.extend(_x_tick_markup(model))
    parts.append("</svg>")
    return Markup("".join(parts))


def _comparison_legend(model) -> Markup:
    if model is None:
        return Markup("")
    last = model.points[-1]
    items = "".join(
        f'<li><span class="legend-swatch swatch-{style}" aria-hidden="true"></span>'
        f'{escape(model.labels[index])}'
        f'<span class="legend-value">{escape(value.value_display)} '
        f'{escape(model.units[index])}</span></li>'
        for index, (style, value) in enumerate(zip(model.styles, last.values)))
    return Markup(f'<ul class="legend">{items}</ul>')


def comparison_svg(model) -> Markup:
    """The SVG and legend for an already prepared comparison model."""
    return Markup(str(_comparison_plot(model)) + str(_comparison_legend(model)))


def chart_plot(model) -> Markup:
    """The drawing alone: SVG for a prepared model, empty state for no model."""
    if model is None:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')
    if isinstance(model, CalendarModel):
        return calendar_plot(model)
    return line_svg(model) if model.kind == "line" else _comparison_plot(model)


def chart_legend(model) -> Markup:
    """The comparison or calendar key, rendered outside the canvas overlay; empty for a line."""
    if model is None:
        return Markup("")
    if isinstance(model, CalendarModel):
        return calendar_legend(model)
    if model.kind == "line":
        return Markup("")
    return _comparison_legend(model)


def chart_svg(model) -> Markup:
    """Render a prepared model of any kind; used by the fallback templates."""
    if model is None:
        return Markup('<p class="chart-empty">Sem valores para representar.</p>')
    if isinstance(model, CalendarModel):
        return calendar_svg(model)
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
