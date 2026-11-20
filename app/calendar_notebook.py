"""Notebook analysis service: mixed-frequency calendars and annual analytical views.

`app.notebook_chart` keeps the original dense paths and delegates here only after the
selection, eligibility, labels and scale checks have passed. This module holds no SQL and no
request parsing: histories come from `Db` public reads and the pure `analysis` domain performs
every calendar decision, annual method and scale transformation.

Original mixed A/S/Q/M/D selections merge real Gregorian start days and keep each side's own
native token. An annual request annualises full histories first, intersects complete annual
years and only then trims a display window. A transformation normalises exact full inputs and
trims afterwards, so a rounded display token never feeds another calculation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from analysis.periods import period_start
from analysis.transforms import (
    AnalysisUnavailable,
    AnalyticalValue,
    AnnualSeries,
    InputValue,
    annualise,
    normalise,
)
from app import interactive, notebook_chart, reads
from app.calendar_model import calendar_model
from app.formatting import (
    decimal_or_none,
    format_count,
    format_datetime,
    format_period,
    format_value,
)
from ingest.db import Db
from presentation import base_unit_text, chart_ui, flag_text, frequency_text
from presentation.notebook import NotebookCopy

log = logging.getLogger("prumo.app.calendar_notebook")


@dataclass(frozen=True)
class _AnnualSide:
    row: dict
    raw_by_period: dict[str, dict]
    series: AnnualSeries
    finite: dict[int, AnalyticalValue]


def _window_label(copy: NotebookCopy, window: str) -> str:
    key = next(key for label, _, key in notebook_chart._WINDOW_CODES if label == window)
    return getattr(copy, key)


def _window_code(window: str) -> str:
    return next(code for label, code, _ in notebook_chart._WINDOW_CODES if label == window)


def _rollback(anchor: date, years: int) -> date:
    target_year = max(1, anchor.year - years)
    try:
        return anchor.replace(year=target_year)
    except ValueError:  # 29 February in a non-leap target year
        return date(target_year, 2, 28)


def _drawable(values: tuple[dict, ...], frequency: str) -> list[date]:
    """Real calendar positions of finite canonical observations, oldest first."""
    out = []
    for value in values:
        start = period_start(value["period"], frequency)
        if start is not None and decimal_or_none(value["value_text"]) is not None:
            out.append(start)
    return out


def _raw(values: tuple[dict, ...]) -> dict[str, dict]:
    return {value["period"]: value for value in values}


def _calendar_excluded(values: tuple[dict, ...], frequency: str,
                       bound: date | None) -> int:
    """Native observations the sparse calendar cannot place inside the shown window.

    A non-canonical period cannot be compared with the window bound, so it is counted
    unconditionally; a canonical period outside the window is not a display exclusion.
    """
    count = 0
    for value in values:
        start = period_start(value["period"], frequency)
        if start is None:
            count += 1
            continue
        if bound is not None and start < bound:
            continue
        if decimal_or_none(value["value_text"]) is None:
            count += 1
    return count


def _calendar_side(db: Db, row: dict, label: str, style: str, cell, lang: str,
                   raw_by_period: dict[str, dict], *, axis_text: str = ""
                   ) -> notebook_chart.ChartSide:
    value = raw_by_period[cell.period]
    provenance = db.public_provenance_at(row["id"], cell.period)
    return notebook_chart.ChartSide(
        series_id=row["id"], label=label, style=style, title=label,
        source_title=reads.source_title(lang, row["source"]),
        attribution=reads.source_text(row["attribution"]),
        unit_text=base_unit_text(lang, row["unit"]),
        frequency_text=frequency_text(lang, row["frequency"]),
        geography_text=reads.geography_name(lang, row["geography"]),
        seasonal_text=(reads.seasonal_text(lang, row["seasonal_adjustment"])
                       if row["seasonal_adjustment"] else ""),
        base_year=row["base_year"], multiplier=row["multiplier"],
        last_display=cell.value_display,
        last_status_text=flag_text(lang, value["status_flag"]) if value["status_flag"] else "",
        provenance=(reads.provenance_view(provenance, row["frequency"], lang)
                    if provenance else None),
        period_text=cell.period_text,
        axis_text=axis_text,
    )


def prepare_calendar(db: Db, rows: tuple[dict, ...], labels: tuple[str, ...],
                     settings: notebook_chart.ChartSettings,
                     choices: tuple[notebook_chart.ChartChoice, ...],
                     copy: NotebookCopy, lang: str, *,
                     axes: tuple[int, ...]) -> notebook_chart.NotebookChart:
    """Sparse calendar for original A/S/Q/M/D selections with more than one frequency.

    The window is anchored on the newest finite observation start in the union and rolls back
    real calendar years. Every chosen side must keep at least one drawable observation inside
    that window; otherwise the chart is unavailable rather than silently losing a side.
    """
    code = _window_code(settings.window)
    histories: list[list[dict]] = []
    full: list[tuple[dict, ...]] = []
    drawable: list[list[date]] = []
    for row in rows:
        values = tuple(db.public_series_values(row["id"]))
        full.append(values)
        drawable.append(_drawable(values, row["frequency"]))

    anchors = [start for starts in drawable for start in starts]
    if not anchors:
        return notebook_chart._empty(
            "unavailable", copy.chart_no_common, settings, choices, copy)
    bound = None
    if code in ("10y", "5y"):
        bound = _rollback(max(anchors), 10 if code == "10y" else 5)

    for row, values, starts in zip(rows, full, drawable):
        if bound is None:
            kept = list(values)
            inside = starts
        else:
            kept = [value for value in values
                    if (start := period_start(value["period"], row["frequency"])) is not None
                    and start >= bound]
            inside = [start for start in starts if start >= bound]
        if not inside:
            return notebook_chart._empty(
                "unavailable", copy.chart_no_common, settings, choices, copy)
        histories.append([{"period": value["period"], "value_text": value["value_text"]}
                          for value in kept])

    units = tuple(base_unit_text(lang, row["unit"]) for row in rows)
    frequencies = tuple(row["frequency"] for row in rows)
    try:
        model = calendar_model(
            tuple(tuple(history) for history in histories), labels=labels, units=units,
            frequencies=frequencies, title=labels[0] if len(labels) == 1 else copy.chart_heading,
            axes=axes)
    except ValueError:
        log.warning("notebook calendar refused an unusable history")
        model = None
    if model is None:
        return notebook_chart._empty(
            "unavailable", copy.chart_no_draw, settings, choices, copy)
    payload = interactive.build_payload(model, missing=copy.chart_missing_cell)

    raw_maps = [_raw(values) for values in full]
    exclusions = [_calendar_excluded(values, row["frequency"], bound)
                  for row, values in zip(rows, full)]
    sides = []
    for index, (row, label, side) in enumerate(zip(rows, labels, model.series)):
        latest = model.rows[side.latest_index].cells[index]
        assert latest is not None  # latest_index names a row where this side is present
        axis_text = (model.axis_labels[index]
                     if len(labels) > 2 and model.dual else "")
        sides.append(_calendar_side(db, row, label, side.style, latest, lang,
                                    raw_maps[index], axis_text=axis_text))

    def table_cell(index: int, cell) -> notebook_chart.ChartCell:
        if cell is None:
            return notebook_chart.ChartCell(
                display=copy.chart_missing_cell, status_text="", missing=True)
        status = raw_maps[index].get(cell.period, {}).get("status_flag")
        return notebook_chart.ChartCell(
            display=cell.value_display,
            status_text=flag_text(lang, status) if status else "",
            period_text=cell.period_text)

    table_rows = tuple(
        notebook_chart.ChartTableRow(
            period_text=row.period_text,
            cells=tuple(table_cell(index, cell) for index, cell in enumerate(row.cells)))
        for row in reversed(model.rows))

    last_texts = tuple(side.period_text for side in sides)
    last_period_text = " · ".join(last_texts) if len(last_texts) > 1 else (
        last_texts[0] if last_texts else "")
    excluded_parts = []
    for label, count in zip(labels, exclusions):
        if not count:
            continue
        template = (copy.chart_calendar_excluded_one if count == 1
                    else copy.chart_calendar_excluded_many)
        excluded_parts.append(template.format(count=format_count(count), label=label))
    alignment_text = " ".join((copy.chart_calendar_alignment, *excluded_parts))
    return notebook_chart.NotebookChart(
        state="ready", state_label="", reason="", chart=model, chart_payload=payload,
        chart_range_label=chart_ui(lang, "range"), chart_hint=chart_ui(lang, "hint"),
        choices=choices, sides=tuple(sides), table_rows=table_rows,
        window_text=copy.chart_calendar_window.format(
            window=_window_label(copy, settings.window),
            first=model.rows[0].period_text, last=model.rows[-1].period_text),
        alignment_text=alignment_text,
        one_point_note="", settings=settings, max_group=notebook_chart.MAX_GROUP,
        last_period_text=last_period_text,
        period_label=(copy.chart_period_mixed if len(sides) > 1
                      else copy.chart_period_calendar),
        axis_groups=notebook_chart.axis_groups(model, labels),
    )


def _method_text(copy: NotebookCopy, value: AnalyticalValue) -> str:
    if value.method == "mean":
        return copy.chart_method_mean
    if value.method == "year_end":
        return copy.chart_method_year_end
    if value.method == "native":
        return copy.chart_method_native
    return copy.chart_method_year_end


def _analysis_reason(error: AnalysisUnavailable, copy: NotebookCopy) -> str:
    reasons = {
        "unsupported_annual": copy.chart_annual_unsupported,
        "unsupported_base100": copy.chart_base100_unsupported,
        "unsupported_pp": copy.chart_pp_unsupported,
        "base_not_positive": copy.chart_base_not_positive,
        "missing_base": copy.chart_base_missing,
    }
    reason = reasons.get(error.code)
    if reason is not None:
        return reason
    log.warning("notebook analysis refused with %s", error.code)
    return copy.chart_method_unavailable


def _annual_side(row: dict, values: tuple[dict, ...]) -> _AnnualSide:
    inputs = tuple(InputValue(series_id=row["id"], period=value["period"],
                               value_text=value["value_text"],
                               status_flag=value["status_flag"]) for value in values)
    series = annualise(row["indicator_key"], row["frequency"], row["unit"], inputs)
    finite = {int(value.period): value for value in series.values
              if decimal_or_none(value.value_text) is not None}
    return _AnnualSide(row=row, raw_by_period=_raw(values), series=series, finite=finite)


def _annual_output_signature(side: _AnnualSide) -> tuple[str, int | float | None, int | None]:
    """The scale identity of an annual output, checked after harmonisation.

    Every reviewed annual method is unit-gated and returns values in the source unit: a mean of
    monthly percentages stays a percentage, and a December stock stays in millions of euros.
    Re-reading the signature from the annualised side makes a future method that changes the
    effective unit fail closed instead of silently joining a mismatched axis group.
    """
    return (side.row["unit"], side.row["multiplier"], side.row["base_year"])


def _common_years(sides: tuple[_AnnualSide, ...]) -> list[int]:
    if not sides:
        return []
    common = set(sides[0].finite)
    for side in sides[1:]:
        common &= set(side.finite)
    return sorted(common)


def _window_years(years: list[int], window: str) -> list[int]:
    if not years:
        return []
    code = _window_code(window)
    if code == "max":
        return years
    floor = max(years) - (10 if code == "10y" else 5)
    return [year for year in years if year >= floor]


def _evidence_input(item: InputValue, raw_by_period: dict[str, dict],
                    frequency: str, lang: str) -> notebook_chart.EvidenceInput:
    raw = raw_by_period.get(item.period, {})
    status = item.status_flag
    return notebook_chart.EvidenceInput(
        period_text=format_period(item.period, frequency),
        value_display=format_value(item.value_text),
        status_text=flag_text(lang, status) if status else "",
        fetched_text=format_datetime(raw.get("fetched_at")),
        run_id=raw.get("run_id"),
        sha256=raw.get("raw_sha"),
    )


def _evidence_output(copy: NotebookCopy, value: AnalyticalValue, raw_by_period: dict[str, dict],
                     frequency: str, lang: str) -> notebook_chart.EvidenceOutput:
    return notebook_chart.EvidenceOutput(
        period_text=format_period(value.period, "A"),
        value_display=format_value(value.value_text),
        method_text=_method_text(copy, value),
        calculated=value.method != "native" or value.transformation != "original",
        inputs=tuple(_evidence_input(item, raw_by_period, frequency, lang)
                     for item in value.inputs),
    )


def _dropped_text(copy: NotebookCopy, label: str, years: tuple[str, ...]) -> str:
    if not years:
        return ""
    template = copy.chart_analysis_dropped_one if len(years) == 1 else copy.chart_analysis_dropped
    return template.format(label=label, count=format_count(len(years)), years=", ".join(years))


def _analysis_note(copy: NotebookCopy, sides: tuple[_AnnualSide, ...],
                   transform: str, base_year: int | None, auto_base: bool,
                   labels: tuple[str, ...]) -> str:
    parts = [copy.chart_analysis_annual]
    if transform == "base100":
        parts.append(f"{copy.chart_evidence_formula}: {copy.chart_formula_base100}.")
    elif transform == "pp":
        parts.append(f"{copy.chart_evidence_formula}: {copy.chart_formula_pp}.")
    if base_year is not None:
        kind = copy.chart_base_auto if auto_base else copy.chart_base_explicit
        parts.append(f"{copy.chart_evidence_base}: {base_year:04d} ({kind}).")
    parts.append(copy.chart_analysis_rounding)
    parts.append(copy.chart_analysis_calculated)
    if any(side.series.method == "native" for side in sides) and transform == "original":
        parts.append(copy.chart_analysis_native)
    families = [side.row["indicator_key"].split(".", 1)[0] for side in sides]
    if any(family == "hicp_yoy" and side.series.method == "mean"
           for family, side in zip(families, sides)):
        parts.append(copy.chart_analysis_hicp)
    if any(family == "unemployment_rate" and side.series.method == "mean"
           for family, side in zip(families, sides)):
        parts.append(copy.chart_analysis_unemployment)
    if any(side.series.method == "year_end" for side in sides):
        parts.append(copy.chart_analysis_year_end)
    methods = []
    for side, label in zip(sides, labels):
        methods.append(f"{label}: {_method_text(copy, side.series.values[-1])}"
                       if side.series.values else f"{label}: {copy.chart_method_native}")
    if methods:
        parts.append(copy.chart_analysis_methods.format(parts=copy.chart_join.join(methods)))
    for side, label in zip(sides, labels):
        if side.series.dropped_years:
            parts.append(_dropped_text(copy, label, side.series.dropped_years))
    return " ".join(parts)


def _mark_payload_badges(payload: dict | None, calculated_flags: list[bool],
                         badge: str) -> None:
    """Mark computed sides only in the browser payload, leaving native sides unmarked.

    The shared payload builder has one badge argument; the notebook has an independent method
    per side. Annotating the returned series metadata keeps the adapter contract unchanged.
    """
    if not payload:
        return
    series = payload.get("series")
    if not isinstance(series, list):
        return
    for item, calculated in zip(series, calculated_flags):
        if isinstance(item, dict):
            item["badge"] = badge if calculated else ""


def prepare_annual(db: Db, rows: tuple[dict, ...], cards: dict[str, reads.Card],
                   labels: tuple[str, ...],
                   settings: notebook_chart.ChartSettings,
                   choices: tuple[notebook_chart.ChartChoice, ...],
                   copy: NotebookCopy, lang: str, *,
                   axes: tuple[int, ...]) -> notebook_chart.NotebookChart:
    """Annual harmonisation and optional base100/pp view over full histories.

    Annualise first, find the common complete years, choose the base (an explicit base may sit
    outside the window but must exist on every side; an automatic base is the first common year
    in the window), normalise exact full inputs, and only then trim the display years.
    """
    sides: list[_AnnualSide] = []
    for row in rows:
        if row["frequency"] not in ("A", "M"):
            # No reviewed annual method exists for a semester, quarter or daily history. Refuse
            # before reading a potentially large full history.
            return notebook_chart._empty(
                "unavailable", copy.chart_annual_unsupported, settings, choices, copy)
        try:
            sides.append(_annual_side(row, tuple(db.public_series_values(row["id"]))))
        except AnalysisUnavailable as error:
            return notebook_chart._empty(
                "unavailable", _analysis_reason(error, copy), settings, choices, copy)
    side_tuple = tuple(sides)

    common = _common_years(side_tuple)
    if not common:
        return notebook_chart._empty(
            "unavailable", copy.chart_no_common, settings, choices, copy)
    window_years = _window_years(common, settings.window)
    if not window_years:
        return notebook_chart._empty(
            "unavailable", copy.chart_no_common, settings, choices, copy)

    transform = settings.transform
    if transform == "original":
        # The source signatures selected the axes. Annualisation must preserve that allocation;
        # a future method with a different output unit is refused instead of mis-grouped.
        output_plan = notebook_chart.allocate_axes(
            tuple(_annual_output_signature(side) for side in side_tuple), settings.scale)
        if output_plan.axes != axes:
            log.warning("annual output scales changed the notebook axis allocation")
            return notebook_chart._empty(
                "unavailable", copy.chart_no_draw, settings, choices, copy)
    base_year = None
    auto_base = False
    if transform != "original":
        if settings.base:
            base_year = int(settings.base)
            if any(base_year not in side.finite for side in side_tuple):
                return notebook_chart._empty(
                    "unavailable", copy.chart_base_missing, settings, choices, copy)
        else:
            base_year = window_years[0]
            auto_base = True

    selected: list[dict[int, AnalyticalValue]] = []
    full_values: list[dict[int, AnalyticalValue]] = []
    for side in side_tuple:
        if transform == "original":
            values = tuple(side.series.values)
        else:
            try:
                values = normalise(
                    tuple(side.series.values), indicator_key=side.row["indicator_key"],
                    unit=side.row["unit"], mode=transform, base_year=f"{base_year:04d}")
            except AnalysisUnavailable as error:
                return notebook_chart._empty(
                    "unavailable", _analysis_reason(error, copy), settings, choices, copy)
        full_values.append({int(value.period): value for value in values})
        selected.append({year: full_values[-1][year] for year in window_years})

    chart_units = []
    for row in rows:
        if transform == "base100":
            chart_units.append(copy.chart_unit_base100.format(base=f"{base_year:04d}"))
        elif transform == "pp":
            chart_units.append(copy.chart_unit_pp)
        else:
            chart_units.append(base_unit_text(lang, row["unit"]))

    points = [{"period": f"{year:04d}",
               "value_text": selected[0][year].value_text} for year in window_years]
    latest_year = window_years[-1]
    calculated_flags = [transform != "original" or side.series.method != "native"
                        for side in side_tuple]
    chart_labels = tuple(
        f"{label} ({copy.chart_calculated_badge})" if calculated else label
        for label, calculated in zip(labels, calculated_flags))
    title = chart_labels[0] if len(labels) == 1 else copy.chart_heading
    if len(labels) == 1:
        prepared = reads.prepare_line_chart(
            points, frequency="A", title=title, unit=chart_units[0])
    elif len(labels) == 2:
        prepared = reads.prepare_comparison_chart(
            [{"period": point["period"],
              "a": selected[0][year].value_text,
              "b": selected[1][year].value_text}
             for point, year in zip(points, window_years)],
            frequency="A", title=title, labels=(chart_labels[0], chart_labels[1]),
            unit_a=chart_units[0], unit_b=chart_units[1],
            dual=settings.scale == "dupla")
    else:
        prepared = reads.prepare_group_chart(
            [{"period": point["period"],
              "values": tuple(selected[index][year].value_text
                              for index in range(len(labels)))}
             for point, year in zip(points, window_years)],
            frequency="A", title=title, labels=chart_labels,
            units=tuple(chart_units), axes=axes)
    if prepared.chart is None:
        return notebook_chart._empty(
            "unavailable", copy.chart_no_draw, settings, choices, copy)
    _mark_payload_badges(prepared.chart_payload, calculated_flags,
                         copy.chart_calculated_badge)

    chart_sides = []
    evidence = []
    any_calculated = any(calculated_flags)
    axis_texts = (("",) if len(labels) == 1 else
                  tuple(getattr(prepared.chart, "axis_labels", ()))
                  if len(labels) > 2 and getattr(prepared.chart, "dual", False)
                  else ("",) * len(labels))
    for index, (side, label) in enumerate(zip(side_tuple, labels)):
        latest = selected[index][latest_year]
        calculated = calculated_flags[index]
        if calculated:
            provenance = None
            status_text = ""
        else:
            provenance = db.public_provenance_at(side.row["id"], f"{latest_year:04d}")
            raw = side.raw_by_period.get(latest.inputs[0].period) if latest.inputs else None
            status = raw["status_flag"] if raw else None
            status_text = flag_text(lang, status) if status else ""
        chart_sides.append(notebook_chart.ChartSide(
            series_id=side.row["id"], label=label,
            style=("a" if len(labels) == 1 else ("a", "b")[index]
                   if len(labels) == 2
                   else getattr(prepared.chart, "styles", ("a",))[index]),
            title=cards[side.row["id"]].title,
            source_title=reads.source_title(lang, side.row["source"]),
            attribution=reads.source_text(side.row["attribution"]),
            unit_text=chart_units[index],
            source_unit_text=base_unit_text(lang, side.row["unit"]),
            frequency_text=frequency_text(lang, side.row["frequency"]),
            display_frequency_text=(copy.chart_frequency_annual_computed
                                    if calculated and side.row["frequency"] != "A" else ""),
            geography_text=reads.geography_name(lang, side.row["geography"]),
            seasonal_text=(reads.seasonal_text(lang, side.row["seasonal_adjustment"])
                           if side.row["seasonal_adjustment"] else ""),
            base_year=side.row["base_year"], multiplier=side.row["multiplier"],
            last_display=format_value(latest.value_text),
            last_status_text=status_text,
            provenance=(reads.provenance_view(provenance, "A", lang)
                        if provenance else None),
            period_text=format_period(f"{latest_year:04d}", "A"),
            method_text=(_method_text(copy, latest) if calculated else ""),
            calculated=calculated,
            axis_text=axis_texts[index],
        ))
        if calculated:
            outputs = tuple(
                _evidence_output(copy, selected[index][year], side.raw_by_period,
                                 side.row["frequency"], lang)
                for year in window_years)
            base_value = full_values[index].get(base_year) if base_year is not None else None
            evidence.append(notebook_chart.SideEvidence(
                label=label,
                series_path=f"/series/{side.row['id']}",
                method_text=_method_text(copy, latest),
                formula_text=(copy.chart_formula_base100 if transform == "base100"
                              else copy.chart_formula_pp if transform == "pp" else ""),
                base_text=(f"{base_year:04d} ({copy.chart_base_auto if auto_base else copy.chart_base_explicit})"
                           if base_year is not None else ""),
                rounding_text=copy.chart_analysis_rounding,
                source_unit_text=base_unit_text(lang, side.row["unit"]),
                chart_unit_text=chart_units[index],
                calculated=True,
                latest=outputs[-1],
                base=(_evidence_output(copy, base_value, side.raw_by_period,
                                       side.row["frequency"], lang)
                      if base_value is not None else None),
                outputs=outputs,
                note=_dropped_text(copy, label, side.series.dropped_years),
            ))
        elif any_calculated:
            # A native annual side shares the panel with calculated sides. Its own provenance
            # must survive in the same evidence disclosure; dropping it would hide the source
            # run, fetched time, archived file and unit behind the other side's calculation.
            evidence.append(notebook_chart.SideEvidence(
                label=label,
                series_path=f"/series/{side.row['id']}",
                method_text=copy.chart_method_native,
                formula_text="",
                base_text="",
                rounding_text="",
                source_unit_text=base_unit_text(lang, side.row["unit"]),
                chart_unit_text=chart_units[index],
                calculated=False,
                latest=_evidence_output(copy, latest, side.raw_by_period,
                                        side.row["frequency"], lang),
                base=None,
                outputs=(),
                note="",
            ))

    table_rows = tuple(
        notebook_chart.ChartTableRow(
            period_text=format_period(f"{year:04d}", "A"),
            cells=tuple(
                notebook_chart.ChartCell(
                    display=format_value(selected[index][year].value_text),
                    status_text=(
                        flag_text(lang, selected[index][year].inputs[0].status_flag or "")
                        if selected[index][year].method == "native"
                        and selected[index][year].transformation == "original"
                        and selected[index][year].inputs
                        and selected[index][year].inputs[0].status_flag else ""),
                    period_text=format_period(f"{year:04d}", "A"),
                    calculated=(selected[index][year].method != "native"
                                or selected[index][year].transformation != "original"),
                )
                for index in range(len(labels))))
        for year in reversed(window_years))

    first = format_period(f"{window_years[0]:04d}", "A")
    last = format_period(f"{latest_year:04d}", "A")
    return notebook_chart.NotebookChart(
        state="ready", state_label="", reason="", chart=prepared.chart,
        chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        choices=choices, sides=tuple(chart_sides), table_rows=table_rows,
        window_text=copy.chart_window_note.format(
            window=_window_label(copy, settings.window), first=first, last=last),
        alignment_text=copy.chart_annual_alignment.format(
            count=format_count(len(window_years)), first=first, last=last),
        one_point_note="", settings=settings, max_group=notebook_chart.MAX_GROUP,
        last_period_text=last,
        period_label=copy.chart_period_annual,
        analysis_note=_analysis_note(copy, side_tuple, transform, base_year, auto_base,
                                     labels),
        evidence=tuple(evidence),
        axis_groups=notebook_chart.axis_groups(prepared.chart, chart_labels),
    )


__all__ = ["prepare_annual", "prepare_calendar"]
