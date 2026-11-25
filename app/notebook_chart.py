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

from app import chart_model, interactive, reads
from app.calendar_model import CalendarModel
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
    chart_ui,
    flag_text,
    frequency_text,
    geography_name,
    seasonal_text,
    source_text,
    source_title,
)
from presentation.notebook import NotebookCopy, text

PARAM_NAMES = ("g", "grafico", "escala", "janela", "dia",
               "frequencia", "transformacao", "base")
MAX_GROUP = GROUP_MAX_SERIES
_WINDOW_CODES = (("1a", "1y", "chart_window_1a"),
                 ("10a", "10y", "chart_window_10a"),
                 ("5a", "5y", "chart_window_5a"),
                 ("max", "max", "chart_window_max"))
# Reader addresses keep their reviewed three windows. The 1a code is internal to the authored
# CMS adapter: an authored document may ask for one year, but a reader link never gains it.
_READER_WINDOWS = frozenset({"10a", "5a", "max"})
_WINDOW_YEARS = {"1y": 1, "5y": 5, "10y": 10}
_ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_BASE_YEAR = re.compile(r"[0-9]{4}\Z")


@dataclass(frozen=True)
class AxisPlan:
    """The one compatibility allocation for a chart's series.

    `axes` is the authoritative 0/1 membership per series; `problem` names the reader-facing
    refusal when the selection cannot be drawn as requested. The legacy two-side dual chart maps
    to (0, 1) even when both sides share a unit, so old links keep their independent axes.
    """

    axes: tuple[int, ...] = ()
    problem: str = ""


def axis_signature(row: dict) -> tuple[str, int | float | None, int | None]:
    """The raw scale identity of one series: unit, multiplier and base year.

    The stored tokens are compared together. A translated unit label is not evidence that two
    series share a scale: `% GDP` and `% PIB` render alike but are different published tokens.
    """
    return (row["unit"], row["multiplier"], row["base_year"])


def allocate_axes(signatures: tuple[tuple, ...], scale: str) -> AxisPlan:
    """Assign compatible raw scales to the left then right axis, in stable first-seen order.

    Three to six sides on `dupla` may share an axis when their unit, multiplier and base year
    match. Exactly two first-seen groups are required: one group asks for the common scale instead
    of silently splitting it, and more than two groups names the limit. `comum` requires one group.
    """
    two_side_dual = scale == "dupla" and len(signatures) == 2
    if two_side_dual:
        return AxisPlan(axes=(0, 1))
    groups: list[tuple] = []
    members: list[int] = []
    for signature in signatures:
        if signature not in groups:
            groups.append(signature)
        members.append(groups.index(signature))
    if scale == "dupla":
        if len(groups) == 1:
            return AxisPlan(problem="one_group")
        if len(groups) > 2:
            return AxisPlan(problem="too_many_groups")
        return AxisPlan(axes=tuple(members))
    if len(groups) > 1:
        return AxisPlan(problem="mixed_scale")
    return AxisPlan(axes=(0,) * len(signatures))


def _plan_reason(copy: NotebookCopy, plan: AxisPlan) -> str:
    reasons = {
        "one_group": copy.chart_dual_one_group,
        "too_many_groups": copy.chart_dual_many_groups,
        "mixed_scale": copy.chart_mixed_scale,
        "invalid_axes": copy.chart_mixed_scale,
    }
    return reasons[plan.problem]


def axes_shape_problem(axes: tuple[int, ...], count: int) -> str:
    """Structural refusal for an explicit assignment, independent of any data.

    Every selected series carries exactly one 0/1 axis and the left axis is never empty. The
    authored chart contract enforces the same shape before storage; this keeps a caller that
    builds settings directly from reaching the model with a malformed assignment.
    """
    if len(axes) != count or not axes:
        return "invalid_axes"
    if any(axis not in (0, 1) for axis in axes):
        return "invalid_axes"
    if 0 not in axes:
        return "one_group"
    return ""


def axis_membership_problem(signatures: tuple[tuple, ...], axes: tuple[int, ...],
                            scale: str) -> str:
    """Check one authoritative 0/1 membership against raw or annual output signatures.

    Each used axis must contain one scale signature: unit, multiplier and base year together.
    A common scale uses the left axis only, and a dual chart must genuinely use both. Series
    order never decides membership: the same rule accepts (1, 0), so the first authored series
    can sit on the right axis.
    """
    problem = axes_shape_problem(tuple(axes), len(signatures))
    if problem:
        return problem
    used = set(axes)
    if scale == "comum":
        if used != {0}:
            return "mixed_scale"
        return "" if len(set(signatures)) == 1 else "mixed_scale"
    if used != {0, 1}:
        return "one_group"
    for axis in (0, 1):
        group = {signature for signature, assigned in zip(signatures, axes) if assigned == axis}
        if len(group) > 1:
            return "mixed_scale"
    return ""


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
    frequency: str = "original"
    transform: str = "original"
    base: str | None = None
    axes: tuple[int, ...] = ()

    def params(self) -> list[tuple[str, str]]:
        """The address parameters, defaults omitted, in one stable order.

        The five original parameters keep their exact order so an old address is byte-identical.
        The analytical controls are appended last and only when they leave their defaults. The
        internal `axes` membership is never a reader address parameter: it is authored in the
        CMS document and passed directly to `prepare`.
        """
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
        if self.frequency != "original":
            out.append(("frequencia", self.frequency))
        if self.transform != "original":
            out.append(("transformacao", self.transform))
        if self.base:
            out.append(("base", self.base))
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
    if window not in _READER_WINDOWS:
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
    frequency = _single(values, "frequencia")
    if frequency is None:
        frequency = "original"
    if frequency not in ("original", "anual"):
        raise _BadAddress("frequencia")

    transform = _single(values, "transformacao")
    if transform is None:
        transform = "original"
    if transform not in ("original", "base100", "pp"):
        raise _BadAddress("transformacao")

    base = _single(values, "base")
    if base in (None, ""):
        base_value = None
    else:
        if _BASE_YEAR.fullmatch(base) is None or not 1 <= int(base) <= 9999:
            raise _BadAddress("base")
        base_value = base
    return ChartSettings(mode=mode, group=tuple(group), scale=scale, window=window,
                          day=day_value, frequency=frequency, transform=transform,
                          base=base_value)


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


def without_all_sides(settings: ChartSettings) -> ChartSettings:
    """Clear every card while keeping the analytical controls a reader chose.

    An explicit group cannot survive an empty selection (a `g` must belong to `s`), so it becomes
    the honest off state. Frequency, transformation, base, scale and window are preserved.
    """
    if settings.mode == "explicit" and settings.group:
        return replace(settings, mode="off", group=())
    return settings


@dataclass(frozen=True)
class ChartChoice:
    series_id: str
    label: str
    checked: bool
    available: bool
    unit_text: str = ""


@dataclass(frozen=True)
class ChartAxisGroup:
    """One visible axis group: its reader name, shared unit and member labels."""

    index: int
    label: str
    unit_text: str
    labels: tuple[str, ...]


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
    period_text: str = ""
    source_unit_text: str = ""
    display_frequency_text: str = ""
    method_text: str = ""
    calculated: bool = False
    axis_text: str = ""


@dataclass(frozen=True)
class EvidenceInput:
    """One exact original input behind a calculated output, with its stored receipt."""

    period_text: str
    value_display: str
    status_text: str
    fetched_text: str
    run_id: int | None
    sha256: str | None
    raw_value: str = ""


@dataclass(frozen=True)
class EvidenceOutput:
    """One calculated annual output and every raw observation that entered it."""

    period_text: str
    value_display: str
    method_text: str
    calculated: bool
    inputs: tuple[EvidenceInput, ...]
    raw_value: str = ""


@dataclass(frozen=True)
class SideEvidence:
    """Reader-facing calculation disclosure for one side, rendered after the plot."""

    label: str
    series_path: str
    method_text: str
    formula_text: str
    base_text: str
    rounding_text: str
    source_unit_text: str
    chart_unit_text: str
    calculated: bool
    latest: EvidenceOutput
    base: EvidenceOutput | None
    outputs: tuple[EvidenceOutput, ...]
    note: str


@dataclass(frozen=True)
class ChartCell:
    display: str
    status_text: str
    period_text: str = ""
    missing: bool = False
    calculated: bool = False


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
    chart: LineChartModel | ComparisonModel | CalendarModel | None
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
    period_label: str = ""
    analysis_note: str = ""
    evidence: tuple[SideEvidence, ...] = ()
    axis_groups: tuple[ChartAxisGroup, ...] = ()

    @property
    def drawable(self) -> bool:
        return self.chart is not None

    def side_period_text(self, series_id: str) -> str:
        """This side's own last native or calculated period, never a fictitious common one."""
        for side in self.sides:
            if side.series_id == series_id:
                return side.period_text or self.last_period_text
        return self.last_period_text

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
                               available=card is not None,
                               unit_text=(card.unit_text if card is not None else "")))
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
    daily token. A daily series still has a bounded rolling default, measured from its newest
    data date, never the server clock. The authored 1y window uses the same real-date rule.
    """
    if frequency == "D" and code in _WINDOW_YEARS:
        try:
            anchor = date.fromisoformat(latest[:10])
        except (TypeError, ValueError):
            return None
        years = _WINDOW_YEARS[code]
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
          value: dict, lang: str, *, axis_text: str = "") -> ChartSide:
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
                    if provenance else None),
        period_text=format_period(period, row["frequency"]),
        axis_text=axis_text)


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


def axis_groups(chart, labels: tuple[str, ...]) -> tuple[ChartAxisGroup, ...]:
    """The visible left/right groups of a grouped or sparse dual chart, never a pair.

    The prepared model owns membership and names; this only assembles the small settings list.
    Two-side dual charts keep their reviewed metadata without an extra group block.
    """
    if chart is None or isinstance(chart, LineChartModel) or not chart.dual:
        return ()
    if len(labels) <= 2:
        return ()
    groups = []
    for axis in (0, 1):
        members = [index for index, assigned in enumerate(chart.axes) if assigned == axis]
        if not members:
            continue
        groups.append(ChartAxisGroup(
            index=axis, label=chart.axis_labels[members[0]],
            unit_text=chart.units[members[0]],
            labels=tuple(labels[index] for index in members)))
    return tuple(groups)


def _pair_axes_prepared(points, *, frequency: str, title: str, labels: tuple[str, ...],
                        units: tuple[str, ...], axes: tuple[int, ...],
                        lang: str) -> reads.PreparedChart:
    """A two-series chart with explicit membership, including a first series on the right.

    The reviewed pair wrapper only knows `dual=True` and therefore always assigns (0, 1). An
    authored document may put its first series on the right, so this path uses the same shared
    comparison factory with the group payload contract: `series[].axis` then states the authored
    membership to the browser instead of letting the adapter infer it from series position.
    """
    assert set(axes) == {0, 1}, "a reordered pair needs both axes"
    rows = []
    for point in points:
        a, b = decimal_or_none(point["a"]), decimal_or_none(point["b"])
        if a is None or b is None:
            continue
        rows.append((point["period"], ((a, point["a"]), (b, point["b"]))))
    chart = chart_model._comparison_model(
        rows, kind="group", title=title,
        name=f"{title}: {labels[0]} ({units[0]}) e {labels[1]} ({units[1]})",
        labels=labels, units=units,
        unit_a=next(units[index] for index, axis in enumerate(axes) if axis == 0),
        unit_b=next(units[index] for index, axis in enumerate(axes) if axis == 1),
        styles=chart_model.GROUP_STYLES[:2], axes=axes, frequency=frequency)
    return reads.PreparedChart(
        chart=chart,
        chart_payload=(interactive.build_payload(chart, lang=lang)
                       if chart is not None else None),
        chart_range_label=chart_ui(lang, "range"), chart_hint=chart_ui(lang, "hint"))


def _model(copy: NotebookCopy, finite: list[dict], frequency: str,
           labels: tuple[str, ...], units: tuple[str, ...], axes: tuple[int, ...],
           *, title: str | None = None, lang: str = "pt"):
    """Prepare the one model every surface reads, with authoritative axis membership.

    `title` lets an authored CMS document keep its own title; the notebook keeps the shared
    heading. A single series stays a line, two series keep the reviewed pair wrapper when their
    membership is the legacy (0, 1)/(0, 0), and every other count or assignment goes through the
    explicit group factory.
    """
    chart_title = title or (labels[0] if len(labels) == 1 else copy.chart_heading)
    if len(labels) == 1:
        points = [{"period": row["period"], "value_text": row["values"][0]["value_text"]}
                  for row in finite]
        return reads.prepare_line_chart(points, frequency=frequency, title=chart_title,
                                        unit=units[0], lang=lang)
    if len(labels) == 2:
        points = [{"period": row["period"],
                   "a": row["values"][0]["value_text"],
                   "b": row["values"][1]["value_text"]} for row in finite]
        if tuple(axes) in ((0, 1), (0, 0)):
            return reads.prepare_comparison_chart(
                points, frequency=frequency, title=chart_title, labels=labels,
                unit_a=units[0], unit_b=units[1], dual=tuple(axes) == (0, 1), lang=lang)
        return _pair_axes_prepared(points, frequency=frequency, title=chart_title,
                                   labels=labels, units=units, axes=tuple(axes), lang=lang)
    points = [{"period": row["period"],
               "values": tuple(value["value_text"] for value in row["values"])}
              for row in finite]
    return reads.prepare_group_chart(points, frequency=frequency, title=chart_title,
                                     labels=labels, units=units, axes=axes, lang=lang)


def prepare(db: Db, addressed: tuple[str, ...], cards: dict[str, reads.Card],
            settings: ChartSettings, *, lang: str = "pt",
            title: str | None = None) -> NotebookChart:
    """Prepare the chart for one validated address from the current read-only snapshot.

    `cards` are the eligible cards `notebook.page` just composed, by series id. Only they can be
    chart sides. A `g` reference without a card makes the chart unavailable, while every eligible
    card stays on the page. `title` is the authored CMS title; without it the notebook's shared
    heading is used. An internal `settings.axes` tuple is the authoritative membership from an
    authored document and is validated here, never inferred from series order.
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
    mixed = len(frequencies) != 1
    frequency = None if mixed else rows_tuple[0]["frequency"]
    annual_request = settings.frequency == "anual"
    transform_request = settings.transform != "original"

    if "PT15M" in frequencies and (mixed or annual_request or transform_request):
        # Interval history has one valid view: the bounded shared UTC day. It never enters the
        # calendar union, an annualisation or a scale transformation.
        return _empty("unavailable", copy.chart_interval_analysis, settings, choices, copy)

    if transform_request:
        if not annual_request:
            return _empty("unavailable", copy.chart_transform_annual, settings, choices, copy)
        if settings.scale == "dupla":
            # Every transformed side shares one index or p.p. unit; two axes would claim two
            # scales where there is one. Refuse explicitly instead of silently flattening.
            return _empty("unavailable", copy.chart_transform_shared, settings, choices, copy)

    signatures = tuple(axis_signature(row) for row in rows_tuple)
    if settings.axes:
        if transform_request:
            if axes_shape_problem(settings.axes, len(group)) \
                    or any(axis != 0 for axis in settings.axes):
                return _empty("unavailable", copy.chart_transform_shared,
                              settings, choices, copy)
            plan = AxisPlan(axes=settings.axes)
        else:
            problem = axis_membership_problem(signatures, settings.axes, settings.scale)
            if problem:
                return _empty("unavailable", _plan_reason(copy, AxisPlan(problem=problem)),
                              settings, choices, copy)
            plan = AxisPlan(axes=settings.axes)
    elif transform_request:
        plan = AxisPlan(axes=(0,) * len(group))
    else:
        plan = allocate_axes(signatures, settings.scale)
        if plan.problem:
            return _empty("unavailable", _plan_reason(copy, plan), settings, choices, copy)
    axes = plan.axes

    titles = tuple(cards[series_id].title for series_id in group)
    labels = _labels(rows_tuple, titles, lang, copy)
    if labels is None:
        return _empty("unavailable", copy.chart_duplicate_labels, settings, choices, copy)

    if transform_request or (annual_request and (mixed or frequency != "A")):
        from app import calendar_notebook
        return calendar_notebook.prepare_annual(
            db, rows_tuple, cards, labels, settings, choices, copy, lang, axes=axes,
            title=title)

    if mixed and not frequencies <= {"A", "S", "Q", "M", "D"}:
        return _empty("unavailable", copy.chart_method_unavailable, settings, choices, copy)

    if mixed:
        from app import calendar_notebook
        return calendar_notebook.prepare_calendar(
            db, rows_tuple, labels, settings, choices, copy, lang, axes=axes, title=title)

    assert frequency is not None  # a single original frequency was checked above

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
                      axes, title=title, lang=lang)
    if prepared.chart is None:
        return _empty("unavailable", copy.chart_no_draw, settings, choices, copy)

    last = finite[-1]
    styles = (("a",) if isinstance(prepared.chart, LineChartModel) else prepared.chart.styles)
    axis_texts = (tuple(prepared.chart.axis_labels)
                  if len(labels) > 2 and not isinstance(prepared.chart, LineChartModel)
                  and prepared.chart.dual else ("",) * len(labels))
    sides = tuple(_side(db, row, cards[series_id], label, style, last["period"], value, lang,
                        axis_text=axis_text)
                  for row, series_id, label, style, value, axis_text
                  in zip(rows_tuple, group, labels, styles, last["values"], axis_texts))
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
        last_period_text=format_period(last["period"], frequency),
        axis_groups=axis_groups(prepared.chart, labels))


__all__ = [
    "AxisPlan",
    "ChartAxisGroup",
    "ChartChoice",
    "ChartSettings",
    "ChartSide",
    "ChartCell",
    "ChartTableRow",
    "EvidenceInput",
    "EvidenceOutput",
    "SideEvidence",
    "MAX_GROUP",
    "NotebookChart",
    "PARAM_NAMES",
    "allocate_axes",
    "axis_groups",
    "axis_membership_problem",
    "axis_signature",
    "axes_shape_problem",
    "parse_settings",
    "prepare",
    "without_side",
]
