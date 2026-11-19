"""Reader-configured notebook chart: bounded address settings and one-snapshot preparation.

The notebook address carries an explicit chart subset (`g`), a scale, a bounded window and an
optional UTC day. This module parses exactly those parameters before the database is opened and
then prepares the chart from the same read-only handle that composed the cards. It holds no SQL,
no cache and no template markup: `reads.prepare_*`, `chart_model` and `interactive.build_payload`
stay the authoritative preparation path, and the shared `_chart.html` shell renders the result.

Nothing here interpolates, rebases, normalises or invents a value. Periods are intersected N-way
before the model is built, every plotted period is returned for the table, and a chosen side that
cannot be drawn makes the whole chart unavailable while the eligible cards remain.
"""
import math
import re
from dataclasses import dataclass, replace
from datetime import date

from app import reads
from app.chart_model import (
    GROUP_MAX_SERIES,
    ComparisonModel,
    LineChartModel,
    calendar_position,
)
from app.formatting import decimal_or_none, format_count, format_date, format_period, format_value
from ingest.db import Db
from presentation import (
    base_unit_text,
    flag_text,
    frequency_text,
    geography_name,
    seasonal_text,
    source_text,
    source_title,
)
from presentation.notebook import NotebookCopy, text

PARAM_NAMES = ("g", "grafico", "escala", "janela", "dia")
MAX_GROUP = GROUP_MAX_SERIES
_WINDOW_CODES = (("10a", "10y", "chart_window_10a"), ("5a", "5y", "chart_window_5a"),
                 ("max", "max", "chart_window_max"))
_ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


@dataclass(frozen=True)
class ChartSettings:
    """The chart settings a notebook address can carry, with its defaults made explicit.

    `mode="all"` is the ordinary old address: every eligible addressed series, implicitly.
    `mode="explicit"` came from `g` values or `grafico=on`; its group may be empty, which is a
    deliberate empty chart and never another way to say "all". `mode="off"` is disabled.
    """

    mode: str = "all"
    group: tuple[str, ...] = ()
    scale: str = "comum"
    window: str = "10a"
    day: str | None = None

    def params(self) -> list[tuple[str, str]]:
        """The address parameters, defaults omitted, in one stable order."""
        out: list[tuple[str, str]] = []
        if self.mode == "off":
            out.append(("grafico", "off"))
        elif self.mode == "explicit":
            out.append(("grafico", "on"))
            out.extend(("g", series_id) for series_id in self.group)
        if self.scale != "comum":
            out.append(("escala", self.scale))
        if self.window != "10a":
            out.append(("janela", self.window))
        if self.day:
            out.append(("dia", self.day))
        return out


class _BadAddress(Exception):
    """A chart parameter that cannot be honoured; the route turns it into the generic 404."""


def parse_settings(values, selection: tuple[str, ...]) -> ChartSettings | None:
    """The chart settings, or None for an invalid or over-limit chart address.

    `values` maps each chart parameter to its repeated values (`MultiDict.getlist` shape). A
    Starlette `QueryParams` object is accepted too: the route and the focused tests then exercise
    the same repeated-value semantics. Repeated singleton parameters and excess `g` values are
    refused before any database read. A `g` value must already belong to the validated
    `selection`; duplicate `g` values collapse in first-appearance order, exactly like `s`.
    """
    if hasattr(values, "getlist"):
        values = {name: values.getlist(name) for name in PARAM_NAMES}
    try:
        return _parse_settings(values, selection)
    except _BadAddress:
        return None


def _values(values, name: str) -> list[str]:
    """One parameter's repeated values; a single string or None is accepted for callers."""
    raw = values.get(name, ())
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def _single(values, name: str) -> str | None:
    raw = _values(values, name)
    if len(raw) > 1:
        raise _BadAddress(name)
    return raw[0] if raw else None


def _parse_settings(values, selection: tuple[str, ...]) -> ChartSettings:
    raw_group = _values(values, "g")
    if len(raw_group) > MAX_GROUP:
        raise _BadAddress("g")
    addressed = set(selection)
    group: list[str] = []
    for series_id in raw_group:
        if not isinstance(series_id, str) or series_id not in addressed:
            raise _BadAddress("g")
        if series_id not in group:
            group.append(series_id)

    grafico = _single(values, "grafico")
    if grafico == "off":
        mode = "off"
        group = []
    elif grafico == "on":
        mode = "explicit"
    elif grafico is None:
        mode = "explicit" if raw_group else "all"
    else:
        raise _BadAddress("grafico")

    scale = _single(values, "escala")
    if scale is None:
        scale = "comum"
    if scale not in ("comum", "dupla"):
        raise _BadAddress("escala")

    window = _single(values, "janela")
    if window is None:
        window = "10a"
    if window not in {code for code, _, _ in _WINDOW_CODES}:
        raise _BadAddress("janela")

    day = _single(values, "dia")
    if day in (None, ""):
        day_value = None
    else:
        if _ISO_DAY.fullmatch(day) is None:
            raise _BadAddress("dia")
        try:
            date.fromisoformat(day)
        except ValueError:
            raise _BadAddress("dia") from None
        day_value = day
    return ChartSettings(mode=mode, group=tuple(group), scale=scale, window=window, day=day_value)


def without_side(settings: ChartSettings, series_id: str) -> ChartSettings:
    """The settings after a deliberate card removal: prune `g`, never switch an empty group to all.

    A deliberate removal is the only event that prunes an explicit group. A rights or availability
    loss keeps every addressed reference, so the link keeps saying which series the reader chose.
    """
    if settings.mode != "explicit" or series_id not in settings.group:
        return settings
    group = tuple(item for item in settings.group if item != series_id)
    if not group:
        return replace(settings, mode="off", group=())
    return replace(settings, group=group)


@dataclass(frozen=True)
class ChartChoice:
    series_id: str
    label: str
    checked: bool
    available: bool


@dataclass(frozen=True)
class ChartSide:
    series_id: str
    label: str
    style: str
    title: str
    source_title: str
    attribution: str
    unit_text: str
    frequency_text: str
    geography_text: str
    seasonal_text: str
    base_year: int | None
    multiplier: int | None
    last_display: str
    last_status_text: str
    provenance: reads.ProvenanceView | None


@dataclass(frozen=True)
class ChartCell:
    display: str
    status_text: str


@dataclass(frozen=True)
class ChartTableRow:
    period_text: str
    cells: tuple[ChartCell, ...]


@dataclass(frozen=True)
class NotebookChart:
    """One chart panel: a prepared chart or a readable unavailable state, never both."""

    state: str
    state_label: str
    reason: str
    chart: LineChartModel | ComparisonModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str
    choices: tuple[ChartChoice, ...]
    sides: tuple[ChartSide, ...]
    table_rows: tuple[ChartTableRow, ...]
    window_text: str
    alignment_text: str
    one_point_note: str
    settings: ChartSettings
    max_group: int
    last_period_text: str

    @property
    def drawable(self) -> bool:
        return self.chart is not None

    @property
    def public_state(self) -> str:
        """The five reader states the page and the cards distinguish.

        `empty_group` (an explicit empty `g`/`grafico=on`) is the same reader state as an empty
        selection; `choose` and `unavailable` stay distinct so a requested but undrawable chart
        is never presented as a plotted one.
        """
        if self.state == "ready":
            return "ready"
        if self.state in ("empty", "empty_group"):
            return "empty"
        return self.state


def _choices(addressed: tuple[str, ...], cards: dict[str, reads.Card],
             settings: ChartSettings, copy: NotebookCopy) -> tuple[ChartChoice, ...]:
    out = []
    for position, series_id in enumerate(addressed, start=1):
        card = cards.get(series_id)
        label = (card.title if card is not None
                 else f"{copy.chart_unavailable_side_label} {position}")
        if settings.mode == "explicit":
            checked = series_id in settings.group
        else:
            checked = (settings.mode == "all" and len(cards) <= MAX_GROUP
                       and card is not None)
        out.append(ChartChoice(series_id=series_id, label=label, checked=checked,
                               available=card is not None))
    return tuple(out)


def _empty(state: str, reason: str, settings: ChartSettings,
           choices: tuple[ChartChoice, ...], copy: NotebookCopy) -> NotebookChart:
    labels = {
        "off": copy.chart_state_off,
        "empty": copy.chart_state_empty,
        "empty_group": copy.chart_state_empty,
        "choose": copy.chart_state_choose,
        "unavailable": copy.chart_state_unavailable,
    }
    return NotebookChart(
        state=state, state_label=labels[state], reason=reason, chart=None, chart_payload=None,
        chart_range_label="", chart_hint="", choices=choices, sides=(), table_rows=(),
        window_text="", alignment_text="", one_point_note="", settings=settings,
        max_group=MAX_GROUP, last_period_text="")


def _labels(rows: tuple[dict, ...], titles: tuple[str, ...], lang: str,
            copy: NotebookCopy) -> tuple[str, ...] | None:
    """Use the series title; add publisher/unit only to disambiguate colliding labels.

    Full source metadata remains available in the definition and provenance disclosures.
    Repeating it in every legend and readout obscures the actual indicator on small screens.
    """
    if len(set(titles)) == len(titles):
        return titles
    sources = tuple(source_title(lang, row["source"]) for row in rows)
    base = tuple(f"{title} - {source}" for title, source in zip(titles, sources))
    if len(set(base)) == len(base):
        return base
    detailed = []
    for row, title, source in zip(rows, titles, sources):
        unit = base_unit_text(lang, row["unit"])
        adjustment = (seasonal_text(lang, row["seasonal_adjustment"])
                      if row["seasonal_adjustment"] else copy.chart_meta_no_adjustment)
        detailed.append(f"{title} - {source} ({unit}, {adjustment})")
    if len(set(detailed)) != len(detailed):
        return None
    return tuple(detailed)


def _calendar_ok(period: str, frequency: str) -> bool:
    """True when the pure model can place this period on its real calendar.

    `calendar_position` is the one canonical-spelling authority: an annual year, a zero-padded
    month, a numbered quarter or semester, a Gregorian date, or a canonical UTC interval
    timestamp. `2026-1`, month 13 or 31 February is excluded here and counted, never drawn at a
    fabricated position or used as a reason to flatten every point onto even spacing.
    """
    return math.isfinite(calendar_position(period, frequency))


def _common_periods(maps: list[dict[str, dict]]) -> list[str]:
    if not maps:
        return []
    return sorted(set.intersection(*(set(map_) for map_ in maps)))


def _finite_rows(common: list[str], maps: list[dict[str, dict]],
                 frequency: str) -> tuple[list[dict], int]:
    """Common periods every side can draw, and the count of common periods that cannot.

    A common period is dropped whole when any side's stored token is missing, non-numeric,
    non-finite or its period has no real calendar position. The row keeps the exact stored value
    dicts, so the table, model and provenance all read the same tokens.
    """
    rows: list[dict] = []
    unparsed = 0
    for period in common:
        values = [map_[period] for map_ in maps]
        numbers = [decimal_or_none(value["value_text"]) for value in values]
        if any(number is None for number in numbers) or not _calendar_ok(period, frequency):
            unparsed += 1
            continue
        rows.append({"period": period, "values": values, "numbers": numbers})
    return rows, unparsed


def _window_start(latest: str, frequency: str, code: str) -> str | None:
    """A bounded start for this chart, including daily dates the shared helper leaves open.

    `reads.window_start` knows the year-shaped calendar and deliberately returns None for a
    daily token. A daily series still has a bounded rolling ten or five year default, measured
    from its newest data date, never the server clock.
    """
    if frequency == "D" and code in ("10y", "5y"):
        try:
            anchor = date.fromisoformat(latest[:10])
        except (TypeError, ValueError):
            return None
        years = 10 if code == "10y" else 5
        try:
            return anchor.replace(year=anchor.year - years).isoformat()
        except ValueError:  # 29 February in a non-leap target year
            return date(anchor.year - years, 2, 28).isoformat()
    return reads.window_start(latest, frequency, code)


def _window_maps(db: Db, rows: tuple[dict, ...], window: str,
                 frequency: str) -> tuple[list[dict[str, dict]], list[str]]:
    """Complete non-interval histories, trimmed to the newest common finite period's window.

    A rolling window is a display trim, never a read bound. The full served history is
    intersected first, so a side whose own newest value is older cannot hide an older period
    every side shares. The anchor is the newest common period every side can actually draw: a
    newer common period carrying a non-numeric token must not pull the window past the last
    finite point and hide it. Interval history stays range-bounded in `_find_day`.
    """
    code = next(code for label, code, _ in _WINDOW_CODES if label == window)
    maps = [{value["period"]: value for value in db.public_series_values(row["id"])}
            for row in rows]
    common = _common_periods(maps)
    if not common or code == "max":
        return maps, common
    finite, _ = _finite_rows(common, maps, frequency)
    if not finite:
        return maps, common
    anchored = _window_start(finite[-1]["period"], frequency, code)
    if anchored is None:
        return maps, common
    trimmed = [{period: value for period, value in map_.items() if period >= anchored}
               for map_ in maps]
    return trimmed, [period for period in common if period >= anchored]


def _day_maps(db: Db, rows: tuple[dict, ...], day: str) -> list[dict[str, dict]]:
    """One UTC day per side: the existing indexed range read, never unbounded interval history."""
    maps = []
    for row in rows:
        values = db.public_values_between(row["id"], day, f"{day}T99")
        maps.append({value["period"]: value for value in values})
    return maps


def _find_day(db: Db, rows: tuple[dict, ...], day: str | None,
              frequency: str) -> tuple[list[dict[str, dict]], list[str], list[dict], int, str] | None:
    """The chosen interval day, its bounded maps, finite rows and unparsed count.

    An explicit day is never substituted. Without one, the newest shared day with at least two
    common finite points wins; a day with a single point is reserved for an explicit request and
    is rendered with a visible marker.
    """
    counts = [dict(db.public_day_counts(row["id"])) for row in rows]
    if day is not None:
        if any(day not in count for count in counts):
            return None
        maps = _day_maps(db, rows, day)
        common = _common_periods(maps)
        finite, unparsed = _finite_rows(common, maps, frequency)
        if not finite:
            return None
        return maps, common, finite, unparsed, day
    shared = sorted(set.intersection(*(set(count) for count in counts)), reverse=True)
    for candidate in shared:
        if any(count[candidate] < 2 for count in counts):
            continue
        maps = _day_maps(db, rows, candidate)
        common = _common_periods(maps)
        finite, unparsed = _finite_rows(common, maps, frequency)
        if len(finite) >= 2:
            return maps, common, finite, unparsed, candidate
    return None


def _side(db: Db, row: dict, card: reads.Card, label: str, style: str, period: str,
          value: dict, lang: str) -> ChartSide:
    provenance = db.public_provenance_at(row["id"], period)
    return ChartSide(
        series_id=row["id"], label=label, style=style, title=card.title,
        source_title=source_title(lang, row["source"]),
        attribution=source_text(row["attribution"]),
        unit_text=base_unit_text(lang, row["unit"]),
        frequency_text=frequency_text(lang, row["frequency"]),
        geography_text=geography_name(lang, row["geography"]),
        seasonal_text=(seasonal_text(lang, row["seasonal_adjustment"])
                       if row["seasonal_adjustment"] else ""),
        base_year=row["base_year"], multiplier=row["multiplier"],
        last_display=format_value(value["value_text"]),
        last_status_text=(flag_text(lang, value["status_flag"])
                          if value["status_flag"] else ""),
        provenance=(reads.provenance_view(provenance, row["frequency"], lang)
                    if provenance else None))


def _alignment_text(copy: NotebookCopy, finite: list[dict], common: list[str],
                    maps: list[dict[str, dict]], labels: tuple[str, ...], frequency: str,
                    unparsed: int) -> str:
    first = format_period(finite[0]["period"], frequency)
    last = format_period(finite[-1]["period"], frequency)
    if len(finite) == 1:
        parts = [copy.chart_common_one.format(first=first)]
    else:
        parts = [copy.chart_common_many.format(count=format_count(len(finite)),
                                               first=first, last=last)]
    gaps = []
    for map_, label in zip(maps, labels):
        dropped = len(map_) - len(common)
        if dropped:
            template = copy.chart_gap_one if dropped == 1 else copy.chart_gap_many
            gaps.append(template.format(count=format_count(dropped), label=label))
    if gaps:
        parts.append(copy.chart_excluded.format(parts=copy.chart_join.join(gaps)))
    if unparsed:
        template = copy.chart_unparsed_one if unparsed == 1 else copy.chart_unparsed_many
        parts.append(template.format(count=format_count(unparsed)))
    if not gaps and not unparsed:
        parts.append(copy.chart_all_common)
    return " ".join(parts)


def _model(copy: NotebookCopy, finite: list[dict], frequency: str,
           labels: tuple[str, ...], units: tuple[str, ...], scale: str):
    if len(labels) == 1:
        points = [{"period": row["period"], "value_text": row["values"][0]["value_text"]}
                  for row in finite]
        return reads.prepare_line_chart(points, frequency=frequency, title=labels[0],
                                        unit=units[0])
    if len(labels) == 2:
        points = [{"period": row["period"],
                   "a": row["values"][0]["value_text"],
                   "b": row["values"][1]["value_text"]} for row in finite]
        return reads.prepare_comparison_chart(
            points, frequency=frequency, title=copy.chart_heading, labels=labels,
            unit_a=units[0], unit_b=units[1], dual=(scale == "dupla"))
    points = [{"period": row["period"],
               "values": tuple(value["value_text"] for value in row["values"])}
              for row in finite]
    return reads.prepare_group_chart(points, frequency=frequency, title=copy.chart_heading,
                                     labels=labels, unit=units[0])


def prepare(db: Db, addressed: tuple[str, ...], cards: dict[str, reads.Card],
            settings: ChartSettings, *, lang: str = "pt") -> NotebookChart:
    """Prepare the chart for one validated address from the current read-only snapshot.

    `cards` are the eligible cards `notebook.page` just composed, by series id. Only they can be
    chart sides. A `g` reference without a card makes the chart unavailable, while every eligible
    card stays on the page.
    """
    copy = text(lang)
    choices = _choices(addressed, cards, settings, copy)
    if not addressed:
        return _empty("empty", copy.chart_empty_selection, settings, choices, copy)
    if settings.mode == "off":
        return _empty("off", copy.chart_off, settings, choices, copy)

    eligible = tuple(series_id for series_id in addressed if series_id in cards)
    if settings.mode == "all":
        if not eligible:
            return _empty("unavailable", copy.chart_unavailable_no_eligible, settings, choices, copy)
        group = eligible
        if len(group) > MAX_GROUP:
            return _empty("choose", copy.chart_choose_many, settings, choices, copy)
    else:
        group = settings.group
        if not group:
            return _empty("empty_group", copy.chart_empty_group, settings, choices, copy)
        if any(series_id not in cards for series_id in group):
            return _empty("unavailable", copy.chart_unavailable_ineligible, settings, choices, copy)

    rows = []
    for series_id in group:
        row = db.public_series(series_id)
        if row is None:
            return _empty("unavailable", copy.chart_unavailable_side, settings, choices, copy)
        rows.append(row)
    rows_tuple = tuple(rows)

    frequencies = {row["frequency"] for row in rows_tuple}
    if len(frequencies) != 1:
        return _empty("unavailable", copy.chart_mixed_frequency, settings, choices, copy)
    frequency = rows_tuple[0]["frequency"]

    if settings.scale == "dupla":
        if len(group) != 2:
            # Three sides on two axes cannot be drawn. When their units also differ, pointing at
            # the common scale alone would be misleading, so use the instruction that names both
            # ways out: exactly two sides, or a comparable shared set.
            signatures = {(row["unit"], row["multiplier"], row["base_year"])
                          for row in rows_tuple}
            reason = copy.chart_dual_count if len(signatures) == 1 else copy.chart_mixed_scale
            return _empty("unavailable", reason, settings, choices, copy)
    else:
        signatures = {(row["unit"], row["multiplier"], row["base_year"])
                      for row in rows_tuple}
        if len(signatures) > 1:
            return _empty("unavailable", copy.chart_mixed_scale, settings, choices, copy)

    titles = tuple(cards[series_id].title for series_id in group)
    labels = _labels(rows_tuple, titles, lang, copy)
    if labels is None:
        return _empty("unavailable", copy.chart_duplicate_labels, settings, choices, copy)

    one_point_note = ""
    if frequency == "PT15M":
        found = _find_day(db, rows_tuple, settings.day, frequency)
        if found is None:
            reason = copy.chart_day_unavailable if settings.day else copy.chart_no_day
            return _empty("unavailable", reason, settings, choices, copy)
        maps, common, finite, unparsed, chosen_day = found
        window_text = copy.chart_day_note.format(day=format_date(chosen_day))
        if len(finite) == 1:
            one_point_note = copy.chart_one_point
    else:
        maps, common = _window_maps(db, rows_tuple, settings.window, frequency)
        if not common:
            return _empty("unavailable", copy.chart_no_common, settings, choices, copy)
        finite, unparsed = _finite_rows(common, maps, frequency)
        if not finite:
            return _empty("unavailable", copy.chart_no_common, settings, choices, copy)
        window_label = next(getattr(copy, key) for label, _, key in _WINDOW_CODES
                            if label == settings.window)
        window_text = copy.chart_window_note.format(
            window=window_label,
            first=format_period(finite[0]["period"], frequency),
            last=format_period(finite[-1]["period"], frequency))

    prepared = _model(copy, finite, frequency, labels,
                      tuple(base_unit_text(lang, row["unit"]) for row in rows_tuple),
                      settings.scale)
    if prepared.chart is None:
        return _empty("unavailable", copy.chart_no_draw, settings, choices, copy)

    last = finite[-1]
    styles = ("a",) if isinstance(prepared.chart, LineChartModel) else prepared.chart.styles
    sides = tuple(_side(db, row, cards[series_id], label, style, last["period"], value, lang)
                  for row, series_id, label, style, value
                  in zip(rows_tuple, group, labels, styles, last["values"]))
    table_rows = tuple(
        ChartTableRow(
            period_text=format_period(row["period"], frequency),
            cells=tuple(
                ChartCell(
                    display=format_value(value["value_text"]),
                    status_text=(flag_text(lang, value["status_flag"])
                                 if value["status_flag"] else ""))
                for value in row["values"]))
        for row in reversed(finite))
    return NotebookChart(
        state="ready", state_label="", reason="", chart=prepared.chart,
        chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        choices=choices, sides=sides, table_rows=table_rows,
        window_text=window_text,
        alignment_text=_alignment_text(copy, finite, common, maps, labels, frequency, unparsed),
        one_point_note=one_point_note, settings=settings, max_group=MAX_GROUP,
        last_period_text=format_period(last["period"], frequency))


__all__ = [
    "ChartChoice",
    "ChartSettings",
    "ChartSide",
    "ChartCell",
    "ChartTableRow",
    "MAX_GROUP",
    "NotebookChart",
    "PARAM_NAMES",
    "parse_settings",
    "prepare",
    "without_side",
]
