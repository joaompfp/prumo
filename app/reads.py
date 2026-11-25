"""Page composition for the public site: Db reads turned into reader-facing values.

No SQL here (every query is a Db method) and no reader text outside `presentation`. Values keep
their stored token; dates, periods and flags get Portuguese text. Dataclasses are frozen so a
template cannot mutate what the page was assembled from.
"""
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Generic, TypeVar
from urllib.parse import urlencode

from app import chart_model, interactive
from app.chart_model import ComparisonModel, LineChartModel
from app.formatting import (
    decimal_or_none,
    format_count,
    format_date,
    format_datetime,
    format_period,
    format_value,
)
from ingest.db import Db
from ingest.editorial_rules import SlotFacts, page_problems, slot_problem
from presentation import (
    MissingText,
    base_unit_text,
    calculated_attribution,
    caveat_text,
    chart_ui,
    comparison_intro,
    comparison_pair,
    comparisons,
    derived_title,
    describe_formula,
    family_of,
    family_title,
    flag_text,
    frequency_text,
    geography_name,
    page_text,
    search_aliases,
    seasonal_text,
    series_title,
    source_text,
    source_title,
    theme_blurb,
    theme_text,
    unit_text,
    withheld_note,
)
from presentation.catalog import pt

log = logging.getLogger("prumo.app")

PAGE_SIZE = 50
SEARCH_PAGE_SIZE = 24
SEARCH_CAP = 100
SEARCH_MAX_QUERY = 200
SEARCH_MAX_PAGE_DIGITS = 6
TABLE_CAP = 60
REVISION_CAP = 30
CATALOGUE_TTL_S = 30.0

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

THEME_ORDER = ("economy", "demography", "energy")
EU_GEOS = frozenset({"EU27_2020", "EA", "EU", "EL", "GR"})
PT_GEOS = frozenset({"PT", "Continente"})
GROUPS = (("", "Todos"), ("pt", "Portugal"), ("eu", "União Europeia"), ("world", "Mundo"))

_catalogue_cache: dict[str, tuple[float, list[dict]]] = {}
_day_cache: dict[tuple[str, str], tuple[float, tuple[tuple[str, int], ...]]] = {}
DAY_COUNTS_TTL_S = 60.0


def clear_cache() -> None:
    _catalogue_cache.clear()
    _day_cache.clear()


def _db_key(db: Db) -> str:
    """The database file this handle reads, as the cache key. The PRAGMA lives on the handle
    (`Db.file_label`), so the read layer holds no SQL of its own (see test_boundaries)."""
    return db.file_label()


def catalogue(db: Db, *, fresh: bool = False) -> list[dict]:
    """The served primary catalogue, cached for a few seconds per database file."""
    key = _db_key(db)
    now = time.monotonic()
    hit = _catalogue_cache.get(key)
    if hit is not None and hit[0] > now and not fresh:
        return hit[1]
    rows = db.public_catalogue()
    _catalogue_cache[key] = (now + CATALOGUE_TTL_S, rows)
    return rows


def _day_counts(db: Db, series_id: str) -> tuple[tuple[str, int], ...]:
    """Days and interval counts of a 15-minute series, cached: one scan of the series is 80 ms
    and the page only needs to know which day to open and which days exist."""
    key = (_db_key(db), series_id)
    now = time.monotonic()
    hit = _day_cache.get(key)
    if hit is not None and hit[0] > now:
        return hit[1]
    rows = db.public_day_counts(series_id)
    _day_cache[key] = (now + DAY_COUNTS_TTL_S, rows)
    return rows


def _title(row: dict, lang: str) -> str:
    return series_title(lang, row["family"], row["geography"])


def _flag(row: dict, lang: str) -> str:
    code = row.get("latest_status_flag") or row.get("status_flag")
    return flag_text(lang, code) if code else ""


def _geo_group(geography: str) -> str:
    if geography in PT_GEOS:
        return "pt"
    if geography in EU_GEOS:
        return "eu"
    return "world"


# Built-in series pages count calendar years (10/25 includes the current year); the CMS
# vocabulary is a rolling window that starts that many years before the latest data time.
_CALENDAR_WINDOW_YEARS = {"10": 10, "25": 25}
_ROLLING_WINDOW_YEARS = {"1y": 1, "5y": 5, "10y": 10}


def window_start(latest: str, frequency: str, window: str) -> str | None:
    """First canonical period a window must include, measured from the latest data time.

    None means "no lower bound" (the maximum window, an unknown token or a series whose
    periods are not year-shaped). The clock is never consulted: a stale dataset still shows
    its own newest periods instead of an empty window.
    """
    if not latest[:4].isdigit():
        return None
    if window in _CALENDAR_WINDOW_YEARS:
        target_year = int(latest[:4]) - (_CALENDAR_WINDOW_YEARS[window] - 1)
    elif window in _ROLLING_WINDOW_YEARS:
        target_year = int(latest[:4]) - _ROLLING_WINDOW_YEARS[window]
    else:
        return None
    if frequency == "A":
        return str(target_year)
    if frequency == "M" and len(latest) >= 7:
        return f"{target_year}-{latest[5:7]}"
    if frequency in ("Q", "S") and len(latest) >= 7:
        return f"{target_year}{latest[4:7]}"
    return None


@dataclass(frozen=True)
class ValueView:
    period: str
    period_text: str
    value_text: str
    value_display: str
    status: str | None
    status_text: str
    fetched_at: str
    fetched_text: str
    raw_sha: str | None = None


def _value_view(row: dict, frequency: str, lang: str) -> ValueView:
    status = row.get("status_flag")
    return ValueView(period=row["period"],
                     period_text=format_period(row["period"], frequency),
                     value_text=row["value_text"],
                     value_display=format_value(row["value_text"]),
                     status=status, status_text=flag_text(lang, status) if status else "",
                     fetched_at=row.get("fetched_at") or "",
                     fetched_text=format_datetime(row.get("fetched_at")),
                     raw_sha=row.get("raw_sha"))


@dataclass(frozen=True)
class ProvenanceView:
    value_display: str
    period_text: str
    fetched_text: str
    run_id: int
    run_state: str
    http_status: int | None
    sha256: str | None
    bytes_text: str
    raw_url: str | None
    verification_created_text: str
    sample_size_text: str
    verification_passed: bool
    sample_procedure: str
    verifier_channel: str
    sampled: bool
    native_code: str | None
    series_url: str | None
    licence: str
    licence_url: str
    attribution: str


@dataclass(frozen=True)
class VersionView:
    value_display: str
    status_text: str
    fetched_text: str
    served: bool


@dataclass(frozen=True)
class RevisionView:
    period: str
    period_text: str
    versions: tuple[VersionView, ...]


@dataclass(frozen=True)
class DerivedLink:
    key: str
    title: str
    unit_text: str
    latest_value_text: str | None
    latest_value_display: str | None
    latest_period_text: str | None
    caveats: tuple[str, ...]


@dataclass(frozen=True)
class CrossCheck:
    id: str
    source_title: str
    attribution: str
    value_display: str
    period_text: str
    fetched_text: str
    status_text: str
    unit_text: str


@dataclass(frozen=True)
class SeriesView:
    id: str
    title: str
    family_title: str
    geography: str
    geography_text: str
    theme: str
    theme_text: str
    frequency: str
    frequency_text: str
    unit: str
    unit_text: str
    seasonal_text: str
    base_year: int | None
    source: str
    source_title: str
    attribution: str
    licence: str
    licence_url: str
    native_code: str | None
    series_url: str | None
    latest: ValueView


@dataclass(frozen=True)
class SeriesDetail:
    series: SeriesView
    values: tuple[ValueView, ...]
    chart_points: tuple[dict, ...]
    chart: LineChartModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str
    provenance: ProvenanceView | None
    revisions: tuple[RevisionView, ...]
    revised_periods: int
    unchanged_periods: int
    derived: tuple[DerivedLink, ...]
    cross_checks: tuple[CrossCheck, ...]
    window: str
    windows: tuple[tuple[str, str], ...]
    is_15m: bool
    days: tuple[str, ...]
    day: str | None
    total_periods: int
    table_note: str


def provenance_view(p: dict, frequency: str, lang: str) -> ProvenanceView:
    return ProvenanceView(
        value_display=format_value(p["value_text"]),
        period_text=format_period(p["period"], frequency),
        fetched_text=format_datetime(p["fetched_at"]),
        run_id=p["run_id"], run_state=p["run_state"], http_status=p["http_status"],
        sha256=p["sha256"], bytes_text=format_count(p["bytes"]) if p["bytes"] is not None else "",
        raw_url=p["raw_url"],
        verification_created_text=format_datetime(p["verification_created_at"]),
        sample_size_text=format_count(p["sample_size"]) if p["sample_size"] is not None else "",
        verification_passed=bool(p["verification_passed"]),
        sample_procedure=p["sample_procedure"] or "",
        verifier_channel=p["verifier_channel"] or "",
        sampled=bool(p["sampled"]),
        native_code=p["native_code"], series_url=p["series_url"],
        licence=source_text(p["licence"]), licence_url=p["licence_url"],
        attribution=source_text(p["attribution"]))


ChartModel = TypeVar("ChartModel", LineChartModel, ComparisonModel)


@dataclass(frozen=True)
class PreparedChart(Generic[ChartModel]):
    """One prepared chart: the SVG model, its optional browser payload and its control copy.

    The same object feeds the built-in detail pages and a CMS chart block, so the fallback and
    the interactive canvas can never come from two different preparations.
    """

    chart: ChartModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str


def prepare_line_chart(points, *, frequency: str, title: str, unit: str = "",
                       display_unit: str | None = None, badge: str = "",
                       lang: str = "pt") -> PreparedChart[LineChartModel]:
    """Prepare a single-series line from stored tokens (`points`: period/value_text)."""
    chart = chart_model.line_model(list(points), frequency=frequency, title=title, unit=unit,
                                   display_unit=display_unit)
    return PreparedChart(
        chart=chart,
        chart_payload=interactive.build_payload(chart, badge=badge) if chart is not None else None,
        chart_range_label=chart_ui(lang, "range"), chart_hint=chart_ui(lang, "hint"))


def prepare_comparison_chart(points, *, frequency: str, title: str,
                             labels: tuple[str, str], unit_a: str, unit_b: str,
                             dual: bool, badge: str = "",
                             lang: str = "pt") -> PreparedChart[ComparisonModel]:
    """Prepare a two-series chart from already aligned points (`a`/`b` tokens)."""
    chart = chart_model.comparison_model(list(points), frequency=frequency, title=title,
                                         labels=labels, unit_a=unit_a, unit_b=unit_b,
                                         dual=dual)
    return PreparedChart(
        chart=chart,
        chart_payload=interactive.build_payload(chart, badge=badge) if chart is not None else None,
        chart_range_label=chart_ui(lang, "range"), chart_hint=chart_ui(lang, "hint"))


def prepare_group_chart(points, *, frequency: str, title: str, labels: tuple[str, ...],
                        unit: str = "", units: tuple[str, ...] | None = None,
                        axes: tuple[int, ...] | None = None, badge: str = "",
                        lang: str = "pt") -> PreparedChart[ComparisonModel]:
    """Prepare three to six series from already aligned points (`values` tokens).

    `units` and `axes` carry the explicit per-series units and 0/1 axis membership; omitting
    them keeps the existing same-unit, single-axis preparation. This is the same preparation
    boundary as the pair wrapper: one model feeds the SVG, the interactive payload and the page
    table, so geometry and exact reader strings cannot diverge.
    """
    chart = chart_model.group_model(list(points), frequency=frequency, title=title,
                                    labels=labels, unit=unit, units=units, axes=axes)
    return PreparedChart(
        chart=chart,
        chart_payload=interactive.build_payload(chart, badge=badge) if chart is not None else None,
        chart_range_label=chart_ui(lang, "range"), chart_hint=chart_ui(lang, "hint"))


def series_page(db: Db, series_id: str, *, window: str = "max", day: str | None = None,
                lang: str = "pt") -> SeriesDetail | None:
    row = db.public_series(series_id)
    if row is None or row["role"] != "primary":
        return None
    if row["latest_period"] is None:
        return None
    frequency = row["frequency"]
    is_15m = frequency == "PT15M"
    days: tuple[str, ...] = ()
    chosen_day = None
    if is_15m:
        counts = _day_counts(db, series_id)
        if not counts:
            return None
        days = tuple(d for d, _ in counts)
        # The newest day is usually partial; open on the newest day that can draw a line.
        if day is not None:
            if day not in days:
                # An explicitly requested day that the cached metadata lacks gets ONE fresh
                # metadata read on the same handle. If it still does not exist, the reader gets
                # a 404 rather than a different day silently substituted under the same URL.
                counts = db.public_day_counts(series_id)
                days = tuple(d for d, _ in counts)
                if not days or day not in days:
                    return None
            chosen_day = day
        else:
            chosen_day = next((d for d, n in counts if n > 1), days[0])
        # Only the chosen day is read: a 15-minute series holds tens of thousands of rows.
        shown = db.public_values_between(series_id, chosen_day, f"{chosen_day}T99")
        total_periods = len(shown)
        table_rows = list(reversed(shown))[:96]
        table_note = (f"{format_count(total_periods)} intervalos neste dia."
                      if total_periods else "Sem intervalos neste dia.")
    else:
        start = window_start(row["latest_period"], frequency, window)
        shown = (db.public_values_between(series_id, start) if start
                 else db.public_series_values(series_id))
        total_periods = len(shown)
        table_rows = list(reversed(shown))[:TABLE_CAP]
        table_note = (f"A mostrar os {len(table_rows)} períodos mais recentes de "
                      f"{format_count(len(shown))}." if len(shown) > len(table_rows)
                      else f"{format_count(len(shown))} períodos.")
    provenance = db.public_provenance(series_id)
    revised, unchanged = db.public_revisions(series_id)
    revisions = []
    for r in revised[:REVISION_CAP]:
        revisions.append(RevisionView(
            period=r["period"], period_text=format_period(r["period"], frequency),
            versions=tuple(VersionView(value_display=format_value(v["value_text"]),
                                       status_text=flag_text(lang, v["status_flag"])
                                       if v["status_flag"] else "",
                                       fetched_text=format_datetime(v["fetched_at"]),
                                       served=v["served"]) for v in r["versions"])))
    derived = []
    for d in db.public_derived_for_base(series_id):
        derived.append(DerivedLink(
            key=d["key"], title=derived_title(lang, d["key"]),
            unit_text=unit_text(lang, d["unit"]),
            latest_value_text=d["latest_value_text"],
            latest_value_display=format_value(d["latest_value_text"])
            if d["latest_value_text"] is not None else None,
            latest_period_text=format_period(d["latest_period"], frequency)
            if d["latest_period"] is not None else None,
            caveats=tuple(caveat_text(lang, c) for c in d["caveats"])))
    cross = tuple(CrossCheck(id=c["id"], source_title=source_title(lang, c["source"]),
                             attribution=source_text(c["attribution"]),
                             value_display=format_value(c["latest_value_text"]),
                             period_text=format_period(c["latest_period"], frequency),
                             fetched_text=format_datetime(c["latest_fetched_at"]),
                             status_text=flag_text(lang, c["latest_status_flag"])
                             if c["latest_status_flag"] else "",
                             unit_text=base_unit_text(lang, c["unit"]))
                  for c in db.public_cross_checks(series_id))
    latest = _value_view({"period": row["latest_period"], "value_text": row["latest_value_text"],
                          "status_flag": row["latest_status_flag"],
                          "fetched_at": row["latest_fetched_at"]}, frequency, lang)
    chart_points = tuple({"period": v["period"], "value_text": v["value_text"]} for v in shown)
    series = SeriesView(
        id=row["id"], title=_title(row, lang), family_title=family_title(lang, row["family"]),
        geography=row["geography"], geography_text=geography_name(lang, row["geography"]),
        theme=row["theme"], theme_text=theme_text(lang, row["theme"]), frequency=frequency,
        frequency_text=frequency_text(lang, frequency), unit=row["unit"],
        unit_text=base_unit_text(lang, row["unit"]),
        seasonal_text=seasonal_text(lang, row["seasonal_adjustment"])
        if row["seasonal_adjustment"] else "",
        base_year=row["base_year"], source=row["source"],
        source_title=source_title(lang, row["source"]), attribution=source_text(row["attribution"]),
        licence=source_text(row["licence"]), licence_url=row["licence_url"],
        native_code=row["native_code"], series_url=row["url"], latest=latest)
    prepared = prepare_line_chart(chart_points, frequency=frequency, title=series.title,
                                  unit=series.unit_text)
    return SeriesDetail(
        series=series,
        values=tuple(_value_view(v, frequency, lang) for v in table_rows),
        chart_points=chart_points,
        chart=prepared.chart,
        chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        provenance=provenance_view(provenance, frequency, lang) if provenance else None,
        revisions=tuple(revisions), revised_periods=len(revised), unchanged_periods=unchanged,
        derived=tuple(derived), cross_checks=cross,
        window=window if window in ("10", "25") else "max",
        windows=(("10", "10 anos"), ("25", "25 anos"), ("max", "Máximo")),
        is_15m=is_15m, days=days, day=chosen_day, total_periods=total_periods,
        table_note=table_note)


@dataclass(frozen=True)
class InputView:
    series_id: str
    title: str
    period_text: str
    value_display: str


@dataclass(frozen=True)
class DerivedDetail:
    key: str
    title: str
    frequency: str
    formula_text: str
    unit_text: str
    caveats: tuple[str, ...]
    latest: ValueView
    values: tuple[ValueView, ...]
    chart_points: tuple[dict, ...]
    chart: LineChartModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str
    base_id: str
    base_title: str
    inputs: tuple[InputView, ...]
    computed_text: str
    licence: str
    licence_url: str
    attribution: str
    served_count: int


def derived_page(db: Db, key: str, lang: str = "pt") -> DerivedDetail | None:
    d = db.public_derived(key)
    if d is None or d["latest_period"] is None:
        return None
    frequency = "M"
    base = db.public_series(d["base_series_id"])
    if base is not None:
        frequency = base["frequency"]
    _, rows = db.served_derived_rows(key, 1)
    newest = rows[0] if rows else None
    values = db.public_derived_values(key)
    base_title = series_title(lang, family_of(d["base_indicator_key"]), d["base_geography"])
    inputs = ()
    if newest is not None:
        observed = db.observations_by_ids([i["observation_id"] for i in newest["inputs"]])
        inputs = tuple(InputView(
            series_id=i["series_id"],
            title=base_title,
            period_text=format_period(i["period"], frequency),
            value_display=format_value(observed[i["observation_id"]]["value_text"])
            if i["observation_id"] in observed else "")
            for i in newest["inputs"])
    title = derived_title(lang, key)
    chart_points = tuple({"period": v["period"], "value_text": v["value_text"]} for v in values)
    prepared = prepare_line_chart(chart_points, frequency=frequency, title=title,
                                  display_unit=unit_text(lang, d["unit"]),
                                  badge=chart_ui(lang, "calculated"))
    return DerivedDetail(
        key=key, title=title, frequency=frequency,
        formula_text=describe_formula(lang, d["formula"], d["params"], base_title),
        unit_text=unit_text(lang, d["unit"]),
        caveats=tuple(caveat_text(lang, c) for c in d["caveats"]),
        latest=ValueView(period=d["latest_period"],
                         period_text=format_period(d["latest_period"], frequency),
                         value_text=d["latest_value_text"],
                         value_display=format_value(d["latest_value_text"]), status=None,
                         status_text="", fetched_at="", fetched_text=""),
        values=tuple(ValueView(period=v["period"],
                               period_text=format_period(v["period"], frequency),
                               value_text=v["value_text"],
                               value_display=format_value(v["value_text"]), status=None,
                               status_text="", fetched_at="", fetched_text="")
                     for v in reversed(values)),
        chart_points=chart_points,
        chart=prepared.chart,
        chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        base_id=d["base_series_id"],
        base_title=series_title(lang, family_of(d["base_indicator_key"]),
                                d["base_geography"]),
        inputs=inputs,
        computed_text=format_datetime(newest["computed_at"]) if newest else "",
        licence=source_text(newest["licence"]) if newest else "",
        licence_url=newest["licence_url"] if newest else "",
        attribution=calculated_attribution(lang, newest["attribution"]) if newest else "",
        served_count=d["served_count"])


@dataclass(frozen=True)
class Card:
    series_id: str
    href: str
    label: str
    title: str
    value_display: str
    unit_text: str
    period_text: str
    source_title: str
    fetched_text: str
    status_text: str
    derived_title: str | None
    derived_label: str | None
    derived_value_display: str | None
    derived_unit_text: str | None
    derived_period_text: str | None
    spark_points: tuple[dict, ...]


@dataclass(frozen=True)
class ThemeCard:
    code: str
    title: str
    blurb: str
    count: int
    href: str


@dataclass(frozen=True)
class HomePage:
    series_count: int
    source_count: int
    last_update_text: str
    last_update_iso: str
    cards: tuple[Card, ...]
    themes: tuple[ThemeCard, ...]
    sources: tuple[str, ...]
    section_title: str
    note: str
    composed: bool  # True when the page has a published composition (cards may be zero)


def _derived_fact_title(lang: str, key: str | None, d: dict | None) -> str | None:
    """A derived companion must be nameable in this language: title and unit both resolve."""
    if not key or d is None:
        return None
    try:
        unit_text(lang, d["unit"])
        return derived_title(lang, key)
    except MissingText:
        return None


def slot_facts(db: Db, pairs: list[tuple[str, str | None]],
               lang: str = "pt") -> tuple[list[SlotFacts | None], dict[str, dict]]:
    """Resolve the facts the one eligibility rule needs for ordered (series, derived) slots.

    Returns one fact object per requested slot (None for an unknown series) plus the raw
    registry rows by series id. No SQL: `series_facts`/`derived_facts` are one indexed lookup
    per id, which is what both the publish refusal and the render-time drop need.
    """
    del lang  # both catalogues are resolved because the rule is asked per render language
    ids = list(dict.fromkeys(series_id for series_id, _ in pairs))
    raw = db.series_facts(ids)
    keys = list(dict.fromkeys(key for _, key in pairs if key))
    derived = db.derived_facts(keys)
    out: list[SlotFacts | None] = []
    for series_id, key in pairs:
        row = raw.get(series_id)
        if row is None:
            out.append(None)
            continue
        d = derived.get(key) if key else None
        titles: dict[str, str | None] = {}
        derived_titles: dict[str, str | None] = {}
        for language in ("pt", "en"):
            try:
                titles[language] = series_title(language, family_of(row["indicator_key"]),
                                                row["geography"])
            except MissingText:
                titles[language] = None
            derived_titles[language] = _derived_fact_title(language, key, d)
        out.append(SlotFacts(
            series_id=series_id, active=bool(row["active"]), role=row["role"],
            redistribution_ok=bool(row["redistribution_ok"]),
            has_served=bool(row["has_served"]), titles=titles, derived_key=key,
            derived_active=bool(d and d["active"]),
            derived_base_series_id=d["base_series_id"] if d else None,
            derived_titles=derived_titles))
    return out, raw


def page_composition(db: Db, slug: str, lang: str = "pt") -> tuple[tuple[dict, str | None], ...] | None:
    """The published composition of `slug` as (catalogue-shaped row, derived key) pairs.

    Applies the SAME rule the backoffice enforces at publish time (`ingest.editorial_rules`),
    so a series that stopped qualifying costs one card, never the page: it is dropped here with
    one WARNING naming the slug, the series and the reason, and the rest render.

    Returns None when the page has no published composition (the caller renders the list in
    code) and a tuple - possibly EMPTY - when it has one. The distinction matters: a composition
    whose every slot stopped qualifying must render no cards, never twelve series nobody
    published. That is the case a revoked licence produces, and it is why this is not `if not
    slots: return ()`.
    """
    slots = db.editorial_slots(slug, "published")
    if not slots:
        return None  # no composition: the page renders the list in code
    facts, rows = slot_facts(db, [(s["series_id"], s["derived_key"]) for s in slots], lang)
    problems = dict(page_problems(facts, lang=lang))
    out = []
    for position, slot in enumerate(slots):
        if position in problems:
            log.warning("editorial slot dropped slug=%s series=%s reason=%s",
                        slug, slot["series_id"], problems[position])
            continue
        row = dict(rows[slot["series_id"]])
        row["family"] = family_of(row["indicator_key"])
        out.append((row, slot["derived_key"]))
    return tuple(out)


def _card(db: Db, row: dict, value: dict, label: str, derived_key: str | None,
          lang: str) -> Card:
    """One home card. The only place a card is built, so the backoffice preview and the public
    page cannot render different values for the same slot."""
    badge = db.public_derived(derived_key) if derived_key else None
    spark = db.public_recent_values(row["id"], 24)
    return Card(
        series_id=row["id"], href=f"/series/{row['id']}", label=label, title=_title(row, lang),
        value_display=format_value(value["value_text"]),
        unit_text=base_unit_text(lang, row["unit"]),
        period_text=format_period(value["period"], row["frequency"]),
        source_title=source_title(lang, row["source"]),
        fetched_text=format_date(value["fetched_at"]),
        status_text=flag_text(lang, value["status_flag"]) if value["status_flag"] else "",
        derived_title=derived_title(lang, derived_key)
        if badge and badge["latest_value_text"] is not None else None,
        derived_label=("Variação homóloga" if badge["formula"].startswith("yoy")
                       else "Face ao período anterior")
        if badge and badge["latest_value_text"] is not None else None,
        derived_value_display=format_value(badge["latest_value_text"])
        if badge and badge["latest_value_text"] is not None else None,
        derived_unit_text=unit_text(lang, badge["unit"])
        if badge and badge["latest_value_text"] is not None else None,
        derived_period_text=format_period(badge["latest_period"], row["frequency"])
        if badge and badge["latest_period"] is not None else None,
        spark_points=tuple({"period": p["period"], "value_text": p["value_text"]}
                           for p in spark))


def prepare_card(db: Db, series_id: str, derived_key: str | None = None, *,
                 label: str | None = None, lang: str = "pt",
                 titles_taken: set[str] | None = None) -> tuple[Card | None, str | None]:
    """One eligible card, or (None, the machine reason it may not render).

    The card markup itself still comes from `_card`, the one builder the home uses. This
    wrapper re-applies the shared slot rule at READ time, so a revoked licence, a deactivated
    series, a missing title or a derived companion whose base changed drops the card instead
    of publishing a number the rule forbids. `titles_taken` carries the page-order duplicate
    rule used by an authored page.
    """
    facts, raw = slot_facts(db, [(series_id, derived_key)], lang)
    problem = slot_problem(facts[0], titles_taken=set(titles_taken or ()), lang=lang)
    if problem is not None:
        return None, problem
    row = dict(raw[series_id])
    row["family"] = family_of(row["indicator_key"])
    latest = db.public_latest_values([series_id])
    value = latest.get(series_id)
    if value is None:
        return None, "no_served_value"
    return _card(db, row, value, label or _title(row, lang), derived_key, lang), None


def cards_for(db: Db, wanted: list[tuple[str, str, str | None]],
              lang: str = "pt", *,
              rows_by_id: dict[str, dict] | None = None) -> tuple[Card, ...]:
    """The cards for an ordered (series id, label, derived key) list, skipping any series the
    catalogue does not serve. Used by the home and by the backoffice's publish preview.

    `rows_by_id` lets a caller that already holds fresh registry rows (the composition read,
    which goes through `series_facts`) hand them over instead of looking them up in the 30 s
    catalogue cache. Without it a series that just became eligible would be dropped by
    `cards_for` for up to 30 s after its publish: `page_composition` would keep the slot and
    the card list would silently lose it."""
    by_id = rows_by_id if rows_by_id is not None else {r["id"]: r for r in catalogue(db)}
    ids = [sid for sid, _, _ in wanted if sid in by_id]
    latest = db.public_latest_values(ids)
    out = []
    for sid, label, derived_key in wanted:
        row = by_id.get(sid)
        if row is None or sid not in latest:
            continue
        out.append(_card(db, row, latest[sid], label, derived_key, lang))
    return tuple(out)


def home(db: Db, lang: str = "pt") -> HomePage:
    rows = catalogue(db)
    counts = db.public_counts()
    composed = page_composition(db, "inicio", lang)
    if composed is not None:
        by_id = {row["id"]: row for row, _ in composed}
        wanted = [(row["id"], _title(row, lang), key) for row, key in composed]
        cards = cards_for(db, wanted, lang, rows_by_id=by_id)
    else:
        by_id = {r["id"]: r for r in rows}
        wanted = [(c["series"], c["label"], c["derived"]) for c in pt.CURATED_HOME]
        cards = cards_for(db, wanted, lang)
    themes = tuple(ThemeCard(code=code, title=theme_text(lang, code),
                             blurb=theme_blurb(lang, code),
                             count=sum(1 for r in rows if r["theme"] == code),
                             href=f"/temas/{code}") for code in THEME_ORDER)
    published = tuple(source_title(lang, s["name"]) for s in db.public_sources()
                      if s["redistribution_ok"] and s["series"])
    # Built from the same rows the cards were built from: a composed slot is not in the
    # cached catalogue, and looking it up there raised KeyError inside the read.
    all_pt = all(by_id[c.series_id]["geography"] in PT_GEOS for c in cards)
    text = page_text(lang, "inicio")
    return HomePage(series_count=counts["series"], source_count=counts["sources"],
                    last_update_text=format_datetime(counts["last_fetched_at"]),
                    last_update_iso=counts["last_fetched_at"] or "",
                    cards=cards, themes=themes, sources=published,
                    section_title=text["section_title"],
                    note=text["note_all_pt"] if all_pt else text["note_mixed"],
                    composed=composed is not None)


@dataclass(frozen=True)
class Row:
    id: str
    href: str
    title: str
    family_title: str
    geography_text: str
    frequency_text: str
    unit_text: str
    source_title: str
    value_display: str
    period_text: str
    status_text: str
    fetched_text: str


@dataclass(frozen=True)
class Group:
    title: str
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class ThemePage:
    code: str
    title: str
    blurb: str
    groups: tuple[Group, ...]
    total: int
    page: int
    pages: int
    group: str
    source: str
    frequency: str
    sources: tuple[tuple[str, str], ...]
    frequencies: tuple[tuple[str, str], ...]
    groups_filter: tuple[tuple[str, str], ...] = GROUPS
    filters_active: bool = False
    clear_path: str = ""
    prev_path: str | None = None
    next_path: str | None = None


@dataclass(frozen=True)
class SearchPage:
    """The complete served catalogue as the reader can browse and filter it.

    `total` is the real number of catalogue rows that match before pagination, never
    the number of rows prepared for this page. Choices are derived from the whole
    catalogue and kept even when a filter is active, so a reader can widen the search
    again without losing the context that produced an empty page.
    """

    query: str
    notice: str
    rows: tuple[Row, ...]
    total: int
    page: int
    pages: int
    per_page: int
    theme: str
    group: str
    source: str
    frequency: str
    theme_options: tuple[tuple[str, str], ...]
    group_options: tuple[tuple[str, str], ...]
    source_options: tuple[tuple[str, str], ...]
    frequency_options: tuple[tuple[str, str], ...]
    filters_active: bool
    clear_path: str
    prev_path: str | None
    next_path: str | None
    rows_missing: int


def _row(row: dict, value: dict, lang: str) -> Row:
    return Row(id=row["id"], href=f"/series/{row['id']}", title=_title(row, lang),
               family_title=family_title(lang, row["family"]),
               geography_text=geography_name(lang, row["geography"]),
               frequency_text=frequency_text(lang, row["frequency"]),
               unit_text=base_unit_text(lang, row["unit"]),
               source_title=source_title(lang, row["source"]),
               value_display=format_value(value["value_text"]),
               period_text=format_period(value["period"], row["frequency"]),
               status_text=flag_text(lang, value["status_flag"])
               if value["status_flag"] else "",
               fetched_text=format_date(value["fetched_at"]))


def _served_rows(db: Db, rows: list[dict], lang: str) -> tuple[Row, ...]:
    """Prepare the reader-facing row for each catalogue row that still has a served value.

    One latest-value read for the visible rows: a series whose value disappeared between the
    catalogue read and this read is skipped, never rendered with a blank value. Search and
    the theme list share this boundary so their rows always carry the same fields.
    """
    latest = db.public_latest_values([r["id"] for r in rows])
    return tuple(_row(r, latest[r["id"]], lang) for r in rows if r["id"] in latest)


def _grouped_rows(rows: tuple[Row, ...]) -> tuple[Group, ...]:
    """Group prepared rows by family, keeping the order each family first appears in."""
    grouped: dict[str, list[Row]] = {}
    for row in rows:
        grouped.setdefault(row.family_title, []).append(row)
    return tuple(Group(title=title, rows=tuple(group)) for title, group in grouped.items())


def _filtered_catalogue(rows: list[dict], *, theme: str = "", group: str = "",
                        source: str = "", frequency: str = "") -> list[dict]:
    """Apply the catalogue's theme, geography, source and frequency filters."""
    return [r for r in rows
            if (not theme or r["theme"] == theme)
            and (not group or _geo_group(r["geography"]) == group)
            and (not source or r["source"] == source)
            and (not frequency or r["frequency"] == frequency)]


def _ordered_catalogue(rows: list[dict], lang: str) -> list[dict]:
    """Order catalogue rows by reader-facing family, geography and identifier."""
    return sorted(rows, key=lambda r: (family_title(lang, r["family"]),
                                       geography_name(lang, r["geography"]), r["id"]))


def _page_slice(rows: list[dict], page: int,
                size: int = PAGE_SIZE) -> tuple[list[dict], int, int]:
    """Clamp a requested page to the list and return its chunk plus page and page count."""
    pages = max(1, (len(rows) + size - 1) // size)
    page = min(max(1, page), pages)
    return rows[(page - 1) * size: page * size], page, pages


def _page_path(path: str, params: list[tuple[str, str]], page: int) -> str:
    """A relative address carrying every non-empty state value plus a non-first page."""
    pairs = [(name, value) for name, value in params if value]
    if page > 1:
        pairs.append(("pagina", str(page)))
    encoded = urlencode(pairs)
    return f"{path}?{encoded}" if encoded else path


def theme(db: Db, code: str, *, group: str = "", source: str = "", frequency: str = "",
          page: int = 1, lang: str = "pt") -> ThemePage | None:
    if code not in THEME_ORDER:
        return None
    rows = [r for r in catalogue(db) if r["theme"] == code]
    sources = sorted({r["source"] for r in rows})
    frequencies = sorted({r["frequency"] for r in rows})
    filtered = _filtered_catalogue(rows, group=group, source=source, frequency=frequency)
    ordered = _ordered_catalogue(filtered, lang)
    chunk, page, pages = _page_slice(ordered, page)
    prepared = _served_rows(db, chunk, lang)
    params = [("grupo", group), ("fonte", source), ("frequencia", frequency)]
    path = f"/temas/{code}"
    return ThemePage(
        code=code, title=theme_text(lang, code), blurb=theme_blurb(lang, code),
        groups=_grouped_rows(prepared),
        total=len(ordered), page=page, pages=pages, group=group, source=source,
        frequency=frequency,
        sources=tuple((s, source_title(lang, s)) for s in sources),
        frequencies=tuple((f, frequency_text(lang, f)) for f in frequencies),
        filters_active=any((group, source, frequency)),
        clear_path=path,
        prev_path=_page_path(path, params, page - 1) if page > 1 else None,
        next_path=_page_path(path, params, page + 1) if page < pages else None)


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _search_haystack(row: dict, lang: str) -> str:
    return " ".join((_title(row, lang), geography_name(lang, row["geography"]),
                     source_title(lang, row["source"]), row["id"], row["indicator_key"],
                     search_aliases(lang, row["family"])))


def _search_terms(query: str) -> tuple[str, ...]:
    """The normalised terms of one reader query; an empty query has no terms."""
    return tuple(term for term in _norm(query.strip()).split() if term)


def _matches_all(row: dict, terms: tuple[str, ...], lang: str) -> bool:
    """Every term must occur in the same row. Token matching is conjunctive."""
    haystack = _norm(_search_haystack(row, lang))
    return all(term in haystack for term in terms)


def parse_search_query(value: str) -> str | None:
    """The stripped term, or None when the address carries too much or control bytes."""
    if not isinstance(value, str):
        return None
    if len(value) > SEARCH_MAX_QUERY or _CONTROL.search(value):
        return None
    return value.strip()


def parse_page_number(value: str | int | None) -> int:
    """A safe page number before any `int` conversion of untrusted address text."""
    if isinstance(value, int) and not isinstance(value, bool):
        return max(1, value)
    text = "" if value is None else str(value).strip()
    if not text or len(text) > SEARCH_MAX_PAGE_DIGITS or not text.isdecimal():
        return 1
    return max(1, int(text))


def search(db: Db, query: str, lang: str = "pt") -> tuple[Row, ...]:
    """Keep the notebook's original phrase matching, order and 100-row cap.

    Token matching and full pagination belong to `search_page`; the notebook's
    add/remove workflow continues to consume this existing bounded contract.
    """
    needle = _norm(query.strip())
    if not needle:
        return ()
    matched = []
    for r in catalogue(db):
        if needle in _norm(_search_haystack(r, lang)):
            matched.append(r)
            if len(matched) >= SEARCH_CAP:
                break
    return _served_rows(db, matched, lang)


def search_page(db: Db, query: str = "", *, theme: str = "", group: str = "",
                source: str = "", frequency: str = "", page: int = 1,
                lang: str = "pt") -> SearchPage:
    """The complete served catalogue for `/pesquisa`, with honest counts and state.

    Choices are taken from the whole catalogue before any filter is applied. Unknown
    filter values therefore produce a truthful, recoverable empty page instead of a
    silently widened result. The query is bounded here, before the catalogue scan, so
    a hostile address costs one notice, not a request error.
    """
    parsed = parse_search_query(query)
    notice = "" if parsed is not None else (
        "O termo de pesquisa é inválido ou demasiado longo. "
        "O termo não foi aplicado. Reveja a pesquisa; os filtros mantêm-se.")
    clean_query = parsed or ""
    rows = catalogue(db)
    theme_options = tuple((code, theme_text(lang, code)) for code in THEME_ORDER
                          if any(r["theme"] == code for r in rows))
    source_options = tuple((name, source_title(lang, name))
                           for name in sorted({r["source"] for r in rows}))
    frequency_options = tuple((code, frequency_text(lang, code))
                              for code in sorted({r["frequency"] for r in rows}))
    terms = _search_terms(clean_query)
    matched = [r for r in rows if not terms or _matches_all(r, terms, lang)]
    filtered = _filtered_catalogue(matched, theme=theme, group=group, source=source,
                                   frequency=frequency)
    ordered = _ordered_catalogue(filtered, lang)
    chunk, page, pages = _page_slice(ordered, page, SEARCH_PAGE_SIZE)
    prepared = _served_rows(db, chunk, lang)
    params = [("q", clean_query), ("tema", theme), ("grupo", group),
              ("fonte", source), ("frequencia", frequency)]
    return SearchPage(
        query=clean_query, notice=notice, rows=prepared, total=len(ordered),
        page=page, pages=pages, per_page=SEARCH_PAGE_SIZE,
        theme=theme, group=group, source=source, frequency=frequency,
        theme_options=theme_options, group_options=GROUPS,
        source_options=source_options, frequency_options=frequency_options,
        filters_active=any((theme, group, source, frequency)),
        clear_path=_page_path("/pesquisa", [("q", clean_query)], 1),
        prev_path=_page_path("/pesquisa", params, page - 1) if page > 1 else None,
        next_path=_page_path("/pesquisa", params, page + 1) if page < pages else None,
        rows_missing=len(chunk) - len(prepared))


@dataclass(frozen=True)
class SourceView:
    name: str
    title: str
    licence: str
    licence_url: str
    attribution: str
    series: int
    last_fetched_text: str
    published: bool
    note: str


@dataclass(frozen=True)
class SourcesPage:
    published: tuple[SourceView, ...]
    withheld: tuple[SourceView, ...]


def sources_page(db: Db, lang: str = "pt") -> SourcesPage:
    published, withheld = [], []
    for s in db.public_sources():
        view = SourceView(name=s["name"], title=source_title(lang, s["name"]),
                          licence=source_text(s["licence"]), licence_url=s["licence_url"],
                          attribution=source_text(s["attribution"]), series=s["series"],
                          last_fetched_text=format_datetime(s["last_fetched_at"]),
                          published=s["redistribution_ok"],
                          note=withheld_note(lang, s["name"]) if not s["redistribution_ok"] else "")
        (published if s["redistribution_ok"] else withheld).append(view)
    return SourcesPage(published=tuple(published), withheld=tuple(withheld))


@dataclass(frozen=True)
class CsvExport:
    filename: str
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    footer: tuple[str, ...]


def _export_stamp() -> str:
    from datetime import datetime, timezone
    return f"{datetime.now(timezone.utc):%d/%m/%Y, %H:%M} UTC"


def series_csv(db: Db, series_id: str) -> CsvExport | None:
    """The served values of one series exactly as stored, with the licence in the footer."""
    row = db.public_series(series_id)
    if row is None or row["role"] != "primary":
        return None
    values = db.public_series_values(series_id)
    if not values:
        return None
    return CsvExport(
        filename=f"{series_id}.csv",
        header=("periodo", "valor", "estado", "recolhido_em"),
        rows=tuple((v["period"], v["value_text"],
                    flag_text("pt", v["status_flag"]) if v["status_flag"] else "",
                    v["fetched_at"])
                   for v in values),
        footer=(f"Série: {series_title('pt', family_of(row['indicator_key']), row['geography'])}",
                f"Unidade: {base_unit_text('pt', row['unit'])}",
                source_text(row["attribution"]),
                f"Licença: {source_text(row['licence'])} - {row['licence_url']}",
                f"Exportado a {_export_stamp()}"))


def derived_csv(db: Db, key: str) -> CsvExport | None:
    """The served values of one calculated series, with its formula and inherited licence."""
    d = db.public_derived(key)
    if d is None or d["latest_period"] is None:
        return None
    values = db.public_derived_values(key)
    if not values:
        return None
    _, rows = db.served_derived_rows(key, 1)
    newest = rows[0] if rows else None
    base_title = series_title("pt", family_of(d["base_indicator_key"]), d["base_geography"])
    footer = tuple(line for line in (
        f"Série calculada: {derived_title('pt', key)}",
        f"Base: {base_title}",
        describe_formula("pt", d["formula"], d["params"], base_title),
        f"{calculated_attribution('pt', newest['attribution'])}" if newest else "",
        f"Licença: {source_text(newest['licence'])} - {newest['licence_url']}" if newest else "",
        f"Exportado a {_export_stamp()}") if line)
    return CsvExport(
        filename=f"{key}.csv",
        header=("periodo", "valor", "unidade"),
        rows=tuple((v["period"], v["value_text"], unit_text("pt", d["unit"])) for v in values),
        footer=footer)


# --- two-series comparisons (project 4, extension) -------------------------------------------
# A comparison is a curated pair in `presentation.catalog`, never two ids from a query string.
# The page plots the periods both series publish; what each side loses is counted, never filled in.

@dataclass(frozen=True)
class ComparisonSeries:
    """One side of a pair: who publishes it, in what unit, and its value on the last period the
    two series share (not on that series' own newest period, which the chart may not reach)."""
    id: str
    title: str
    source_title: str
    attribution: str
    unit_text: str
    frequency: str
    frequency_text: str
    latest_display: str
    latest_period_text: str
    licence: str
    provenance: ProvenanceView | None


@dataclass(frozen=True)
class ComparisonPage:
    slug: str
    title: str
    subtitle: str
    mechanism: str
    caption_note: str
    scale: str
    chart_title: str
    chart_points: tuple[dict, ...]
    chart: ComparisonModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str
    table_rows: tuple[dict, ...]
    alignment_text: str
    a: ComparisonSeries
    b: ComparisonSeries


@dataclass(frozen=True)
class ComparisonSummary:
    slug: str
    title: str
    mechanism: str
    span_text: str
    common_text: str


@dataclass(frozen=True)
class ComparisonIndex:
    intro: str
    rows: tuple[ComparisonSummary, ...]


def _periods(n: int) -> str:
    return "1 período" if n == 1 else f"{format_count(n)} períodos"


def _common(n: int) -> str:
    return "1 período comum" if n == 1 else f"{format_count(n)} períodos comuns"


def align_periods(a_values: list[dict],
                  b_values: list[dict]) -> tuple[tuple[dict, ...], int, int, int]:
    """The periods both series publish with a numeric value on both sides, oldest first.

    No interpolation, no carry-forward, no resampling. Returns the points, the count of periods
    each side has that the other lacks, and the count of common periods dropped because a
    publisher token was not a number ("n.d.", an empty cell): the chart cannot draw those, and the
    page must not call the last drawn period "the last common period".
    """
    a_map = {v["period"]: v["value_text"] for v in a_values}
    b_map = {v["period"]: v["value_text"] for v in b_values}
    common = sorted(set(a_map) & set(b_map))
    points = tuple({"period": p, "a": a_map[p], "b": b_map[p]}
                   for p in common
                   if decimal_or_none(a_map[p]) is not None
                   and decimal_or_none(b_map[p]) is not None)
    return (points, len(a_map) - len(common), len(b_map) - len(common),
            len(common) - len(points))


def _comparison_side(db: Db, row: dict, token: str, period: str, frequency: str,
                     lang: str) -> ComparisonSeries:
    # The provenance of the value this page shows, not of the series' newest one.
    provenance = db.public_provenance_at(row["id"], period)
    return ComparisonSeries(
        id=row["id"], title=_title(row, lang), source_title=source_title(lang, row["source"]),
        attribution=source_text(row["attribution"]), unit_text=base_unit_text(lang, row["unit"]),
        frequency=frequency, frequency_text=frequency_text(lang, frequency),
        latest_display=format_value(token),
        latest_period_text=format_period(period, frequency),
        licence=source_text(row["licence"]),
        provenance=provenance_view(provenance, frequency, lang) if provenance else None)


def _published_pair(db: Db, pair: dict[str, str],
                    slug: str = "") -> tuple[dict, dict, tuple[dict, ...], int, int, int] | None:
    """Both series of a pair, or None when the pair cannot be drawn as it was curated.

    A pair whose series lost its licence or its served values disappears whole: half a
    comparison is a claim the reader cannot check.
    """
    a_row = db.public_series(pair["series_a"])
    b_row = db.public_series(pair["series_b"])
    if a_row is None or b_row is None:
        log.warning("comparison %s hidden: a series is not published", slug or pair["series_a"])
        return None
    if a_row["role"] != "primary" or b_row["role"] != "primary":
        return None
    if a_row["latest_period"] is None or b_row["latest_period"] is None:
        log.warning("comparison %s hidden: a series has no served value", slug)
        return None
    if a_row["frequency"] != b_row["frequency"]:
        # Curated pairs are same-frequency. A mismatch is a catalogue fault, not a reader's.
        log.error("comparison %s mixes frequencies %s and %s", slug,
                  a_row["frequency"], b_row["frequency"])
        return None
    points, dropped_a, dropped_b, unparsed = align_periods(db.public_series_values(a_row["id"]),
                                                           db.public_series_values(b_row["id"]))
    if not points:
        log.warning("comparison %s hidden: no common period", slug)
        return None
    return a_row, b_row, points, dropped_a, dropped_b, unparsed


def alignment_text(points: tuple[dict, ...], dropped_a: int, dropped_b: int, unparsed: int,
                   a_title: str, b_title: str, frequency: str) -> str:
    first = format_period(points[0]["period"], frequency)
    last = format_period(points[-1]["period"], frequency)
    parts = [f"{_common(len(points))}, de {first} a {last}."]
    missing = []
    if dropped_a:
        missing.append(f"{_periods(dropped_a)} de {a_title}")
    if dropped_b:
        missing.append(f"{_periods(dropped_b)} de {b_title}")
    if missing:
        parts.append("Ficam de fora " + " e ".join(missing) + ", sem par na outra série.")
    if unparsed:
        parts.append(f"{_common(unparsed)} sem valor numérico na fonte "
                     + ("fica" if unparsed == 1 else "ficam") + " fora do gráfico e da tabela.")
    if not missing and not unparsed:
        parts.append("As duas séries cobrem exactamente os mesmos períodos.")
    return " ".join(parts)


def comparison_page(db: Db, slug: str, *, lang: str = "pt") -> ComparisonPage | None:
    # An unknown slug is a reader's 404; a pair with a missing key raises MissingText and the app
    # answers 503 with a log line, because that is an operator fault on a page that should exist.
    if slug not in comparisons(lang):
        return None
    pair = comparison_pair(lang, slug)
    published = _published_pair(db, pair, slug)
    if published is None:
        return None
    a_row, b_row, points, dropped_a, dropped_b, unparsed = published
    frequency = a_row["frequency"]
    last = points[-1]
    a = _comparison_side(db, a_row, last["a"], last["period"], frequency, lang)
    b = _comparison_side(db, b_row, last["b"], last["period"], frequency, lang)
    # Every plotted period is in the table: the reader can check any point the chart draws.
    rows = tuple(
        {"period_text": format_period(p["period"], frequency),
         "a_display": format_value(p["a"]), "b_display": format_value(p["b"])}
        for p in reversed(points))
    prepared = prepare_comparison_chart(
        points, frequency=frequency, title=pair["title"], labels=(a.title, b.title),
        unit_a=a.unit_text, unit_b=b.unit_text, dual=(pair["scale"] == "dual_axis"))
    return ComparisonPage(
        slug=slug, title=pair["title"], subtitle=pair["subtitle"], mechanism=pair["mechanism"],
        caption_note=pair["caption_note"], scale=pair["scale"], chart_title=pair["title"],
        chart_points=points, chart=prepared.chart,
        chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        table_rows=rows,
        alignment_text=alignment_text(points, dropped_a, dropped_b, unparsed,
                                      a.title, b.title, frequency),
        a=a, b=b)


def comparisons_index(db: Db, *, lang: str = "pt") -> ComparisonIndex:
    rows = []
    for slug in comparisons(lang):
        pair = comparison_pair(lang, slug)
        published = _published_pair(db, pair, slug)
        if published is None:
            continue
        a_row, _b_row, points, _dropped_a, _dropped_b, _unparsed = published
        frequency = a_row["frequency"]
        rows.append(ComparisonSummary(
            slug=slug, title=pair["title"], mechanism=pair["mechanism"],
            span_text=(f"{format_period(points[0]['period'], frequency)} a "
                       f"{format_period(points[-1]['period'], frequency)}"),
            common_text=_common(len(points))))
    return ComparisonIndex(intro=comparison_intro(lang), rows=tuple(rows))
