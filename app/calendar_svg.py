"""SVG fallback for the sparse calendar model.

Every present cell is a real native observation; a missing cell is simply absent from the
series path. A path command restarts only at that series' own native gap, so an annual line
runs through months observed by another side without inventing an annual value. Markers carry
the original native period and exact stored value, and the legend states each side's own last
value and native period instead of a floating label that could collide.
"""
from markupsafe import Markup, escape

from app.calendar_model import CalendarModel


def _empty() -> Markup:
    return Markup('<p class="chart-empty">Sem valores para representar.</p>')


def _x_ticks(model: CalendarModel) -> list[str]:
    labels = []
    for index, tick in enumerate(model.x_ticks):
        anchor = ("start" if index == 0 else "end" if index == len(model.x_ticks) - 1
                  else "middle") if len(model.x_ticks) > 1 else "middle"
        labels.append(f'<text class="chart-tick" x="{round(tick.x, 1)}" '
                      f'y="{model.height - 20}" text-anchor="{anchor}">'
                      f'{escape(tick.text)}</text>')
    return labels


def _display(value: str, unit: str) -> str:
    return f"{value} {unit}" if unit else value


def calendar_plot(model: CalendarModel | None) -> Markup:
    """The calendar SVG alone: shared axes, one path per side, real observation markers."""
    if model is None:
        return _empty()
    width, height = model.width, model.height
    parts = [f'<svg class="chart chart-compare chart-calendar" viewBox="0 0 {width} {height}" '
             f'role="img" aria-label="{escape(model.name)}" '
             f'preserveAspectRatio="xMidYMid meet">',
             f"<title>{escape(model.name)}</title>"]

    for tick in model.ticks_a:
        ty = round(tick.y, 1)
        cls = "chart-grid chart-zero" if tick.zero else "chart-grid"
        parts.append(f'<line class="{cls}" x1="{model.left}" y1="{ty}" '
                     f'x2="{width - model.right}" y2="{ty}" />')
        parts.append(f'<text class="chart-tick" x="{model.left - 11}" y="{ty + 7}" '
                     f'text-anchor="end">{escape(tick.text)}</text>')
    if model.dual:
        for tick in model.ticks_b:
            ty = round(tick.y, 1)
            parts.append(f'<text class="chart-tick" x="{width - model.right + 11}" y="{ty + 7}" '
                         f'text-anchor="start">{escape(tick.text)}</text>')

    parts.append(f'<text class="chart-axis-label" x="{model.left}" y="{model.top - 9}" '
                 f'text-anchor="start">{escape(model.unit_a)}</text>')
    if model.dual:
        parts.append(f'<text class="chart-axis-label" x="{width - 7}" y="{model.top - 9}" '
                     f'text-anchor="end">{escape(model.unit_b)}</text>')

    for index, series in enumerate(model.series):
        commands: list[str] = []
        for row_index, row in enumerate(model.rows):
            cell = row.cells[index]
            if cell is None:
                continue
            command = "M" if not commands or row_index in series.breaks else "L"
            commands.append(f"{command}{round(row.x, 1)},{round(cell.y, 1)}")
        parts.append(f'<path class="chart-line chart-line-{series.style}" '
                     f'd="{" ".join(commands)}" />')

    for row in model.rows:
        cx = round(row.x, 1)
        for index, cell in enumerate(row.cells):
            if cell is None:
                continue
            series = model.series[index]
            parts.append(f'<circle class="chart-point" cx="{cx}" cy="{round(cell.y, 1)}" r="7">'
                         f'<title>{escape(series.label)} - {escape(cell.period_text)} '
                         f'({escape(cell.period)}): '
                         f'{escape(_display(cell.value_display, series.unit))}</title></circle>')

    # Each side marks its own latest actual observation. The exact value and native period live
    # in the legend, so no floating label can collide with another side.
    for index, series in enumerate(model.series):
        row = model.rows[series.latest_index]
        cell = row.cells[index]
        if cell is None:  # latest_index is derived from a present cell; keep the invariant explicit
            continue
        parts.append(f'<circle class="chart-last chart-last-{series.style}" '
                     f'cx="{round(row.x, 1)}" cy="{round(cell.y, 1)}" r="3.5" />')

    parts.extend(_x_ticks(model))
    parts.append("</svg>")
    return Markup("".join(parts))


def calendar_legend(model: CalendarModel | None) -> Markup:
    """The side key: label, last exact value and that side's own last native period."""
    if model is None:
        return Markup("")
    items = []
    for index, series in enumerate(model.series):
        row = model.rows[series.latest_index]
        cell = row.cells[index]
        if cell is None:
            continue
        items.append(
            f'<li><span class="legend-swatch swatch-{series.style}" aria-hidden="true"></span>'
            f'{escape(series.label)}'
            f'<span class="legend-value">{escape(_display(cell.value_display, series.unit))} '
            f'({escape(cell.period_text)})</span></li>')
    return Markup(f'<ul class="legend">{"".join(items)}</ul>')


def calendar_svg(model: CalendarModel | None) -> Markup:
    """The calendar SVG and legend for a prepared model."""
    return Markup(str(calendar_plot(model)) + str(calendar_legend(model)))


__all__ = ["calendar_legend", "calendar_plot", "calendar_svg"]
