"""Curated country comparisons: the same indicator for five countries on one shared scale.

A group is authored in the presentation catalogue, never assembled from an address. Every side
must be an active, primary, redistributable series whose fetched values share one family, source,
frequency, unit, adjustment, multiplier, base year and exact pinned native dimensions, except the
country dimension itself. Any missing, withheld, withdrawn, legacy-only or mismatched side hides
the whole group: half a comparison is a claim the reader cannot check.

All reads go through `Db.public_series`, `Db.public_series_values` and
`Db.public_provenance_at` on the one read-only transaction the route opens. There is no SQL and
no write path here. Values stay the publisher's tokens; only `app.formatting` changes separators.
"""
import logging
from dataclasses import dataclass

from app import reads
from app.chart_model import ComparisonModel
from app.formatting import decimal_or_none, format_count, format_period, format_value
from app.statistical_definitions import native_parts as _native_parts
from ingest.db import Db
from presentation import (
    base_unit_text,
    country_comparison,
    country_comparison_countries,
    country_comparisons,
    country_comparisons_intro,
    country_comparisons_title,
    flag_text,
    frequency_text,
    geography_name,
    series_title,
    source_text,
    source_title,
)

log = logging.getLogger("prumo.app")

# The group must be one axis. These are not renderer options: a group with different units is a
# different comparison and needs a separately reviewed definition.
_COUNTRY_FIELDS = ("source", "unit", "frequency", "seasonal_adjustment", "multiplier", "base_year")


@dataclass(frozen=True)
class CountrySide:
    """One country at the last common period the chart actually draws."""

    id: str
    label: str
    title: str
    source_title: str
    attribution: str
    unit_text: str
    latest_display: str
    latest_period_text: str
    status_flag: str
    status_text: str
    licence: str
    provenance: reads.ProvenanceView | None


@dataclass(frozen=True)
class CountryValueCell:
    display: str
    status_text: str


@dataclass(frozen=True)
class CountryTableRow:
    period_text: str
    cells: tuple[CountryValueCell, ...]


@dataclass(frozen=True)
class CountryComparisonPage:
    slug: str
    title: str
    subtitle: str
    mechanism: str
    caption_note: str
    definition_note: str
    notebook_action: str
    chart: ComparisonModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str
    table_rows: tuple[CountryTableRow, ...]
    alignment_text: str
    countries: tuple[CountrySide, ...]
    latest_period_text: str
    unit_text: str
    frequency_text: str


@dataclass(frozen=True)
class CountryComparisonSummary:
    """A bounded index row: coverage and counts, never a prepared chart."""

    slug: str
    title: str
    subtitle: str
    countries_text: str
    span_text: str
    common_text: str


@dataclass(frozen=True)
class CountryComparisonIndex:
    title: str
    intro: str
    rows: tuple[CountryComparisonSummary, ...]


@dataclass(frozen=True)
class _Side:
    row: dict
    values_by_period: dict[str, dict]


@dataclass(frozen=True)
class _PublishedGroup:
    sides: tuple[_Side, ...]
    points: tuple[dict, ...]
    missing: tuple[int, ...]
    dropped: tuple[int, ...]
    unparsed: int
    frequency: str


def _check_side(db: Db, definition: dict, country: str, slug: str) -> _Side | None:
    series_id = f"{definition['family']}.{country}"
    row = db.public_series(series_id)
    if row is None:
        log.warning("country comparison %s hidden: %s is not published", slug, series_id)
        return None
    if row["role"] != "primary":
        log.error("country comparison %s hidden: %s is not primary", slug, series_id)
        return None
    if row["geography"] != country:
        log.error("country comparison %s hidden: %s has geography %s", slug, series_id,
                  row["geography"])
        return None
    expected_key = (f"{definition['family'].replace('.', '_')}.{country}."
                    f"{definition['frequency']}")
    if row["indicator_key"] != expected_key:
        log.error("country comparison %s hidden: %s has indicator key %s", slug, series_id,
                  row["indicator_key"])
        return None
    if row["family"] != definition["family"].replace(".", "_"):
        log.error("country comparison %s hidden: %s is another family", slug, series_id)
        return None
    native = _native_parts(row["native_code"])
    if native is None:
        log.error("country comparison %s hidden: %s has a malformed native code", slug, series_id)
        return None
    dataset, dimensions = native
    if dataset != definition["dataset"]:
        log.error("country comparison %s hidden: %s is dataset %s", slug, series_id, dataset)
        return None
    if dimensions.get("geo") != country:
        log.error("country comparison %s hidden: %s native geo is %s", slug, series_id,
                  dimensions.get("geo"))
        return None
    without_geo = {key: value for key, value in dimensions.items() if key != "geo"}
    if without_geo != definition["dimensions"]:
        log.error("country comparison %s hidden: %s native dimensions differ", slug, series_id)
        return None
    values = db.public_series_values(series_id)
    if not values:
        log.warning("country comparison %s hidden: %s has no served values", slug, series_id)
        return None
    by_period = {value["period"]: value for value in values}
    if len(by_period) != len(values):
        log.error("country comparison %s hidden: %s has duplicate served periods", slug, series_id)
        return None
    return _Side(row=row, values_by_period=by_period)


def _published_group(db: Db, definition: dict, slug: str,
                     lang: str) -> _PublishedGroup | None:
    """Validate every side and align the common finite periods, or hide the group whole."""
    sides = []
    for country in country_comparison_countries(lang):
        side = _check_side(db, definition, country, slug)
        if side is None:
            return None
        sides.append(side)
    for field in _COUNTRY_FIELDS:
        expected = definition[field]
        if any(side.row[field] != expected for side in sides):
            log.error("country comparison %s hidden: sides disagree on %s", slug, field)
            return None

    period_sets = [set(side.values_by_period) for side in sides]
    common = sorted(set.intersection(*period_sets))
    common_set = set(common)
    dropped = tuple(len(periods - common_set) for periods in period_sets)
    # A country's missing periods are periods every OTHER country publishes but it does not.
    # This distinguishes a country that is behind from one that is ahead with an unpaired period.
    missing = tuple(
        len(set.intersection(*(period_sets[j] for j in range(len(period_sets)) if j != i))
            - period_sets[i])
        for i in range(len(period_sets)))
    finite = [
        period for period in common
        if all(decimal_or_none(side.values_by_period[period]["value_text"]) is not None
               for side in sides)
    ]
    unparsed = len(common) - len(finite)
    if not finite:
        log.warning("country comparison %s hidden: no common finite period", slug)
        return None
    points = tuple(
        {"period": period,
         "values": tuple(side.values_by_period[period]["value_text"] for side in sides)}
        for period in finite)
    return _PublishedGroup(
        sides=tuple(sides), points=points, missing=missing,
        dropped=dropped, unparsed=unparsed, frequency=sides[0].row["frequency"])


def _periods_text(count: int) -> str:
    return "1 período" if count == 1 else f"{format_count(count)} períodos"


def _common_text(count: int) -> str:
    return "1 período comum" if count == 1 else f"{format_count(count)} períodos comuns"


def _join_labels(labels: tuple[str, ...]) -> str:
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " e " + labels[-1]


def alignment_text(points: tuple[dict, ...], missing: tuple[int, ...],
                   dropped: tuple[int, ...], unparsed: int, labels: tuple[str, ...],
                   frequency: str) -> str:
    """State the shared span and every period a country or the reader loses.

    `missing` counts periods every other country publishes but this one does not. `dropped`
    counts this country's periods left out of the shared intersection because at least one other
    side lacks them. Common periods with a nonnumeric token are a separate count once. No country
    is ever described as covering a period it does not publish.
    """
    first = format_period(points[0]["period"], frequency)
    last = format_period(points[-1]["period"], frequency)
    parts = [f"{_common_text(len(points))}, de {first} a {last}."]
    for count, label in zip(missing, labels):
        if count:
            parts.append(f"{label} não publica {_periods_text(count)} que os outros países "
                         "publicam.")
    gaps = [f"{_periods_text(count)} de {label}"
            for count, label in zip(dropped, labels) if count]
    if gaps:
        verb = "Fica" if sum(dropped) == 1 else "Ficam"
        parts.append(f"{verb} de fora " + " e ".join(gaps)
                     + ", por faltar pelo menos um dos outros países em cada período.")
    if unparsed:
        parts.append(
            f"{_common_text(unparsed)} sem valor numérico na fonte "
            + ("fica" if unparsed == 1 else "ficam")
            + " fora do gráfico e da tabela.")
    if not gaps and not unparsed and not any(missing):
        parts.append("Todos os países cobrem exactamente os mesmos períodos.")
    return " ".join(parts)


def _status_text(lang: str, flag: str | None) -> str:
    return flag_text(lang, flag) if flag else ""


def _side(db: Db, row: dict, value: dict, period: str, frequency: str,
          lang: str) -> CountrySide:
    provenance = db.public_provenance_at(row["id"], period)
    status = value["status_flag"] or ""
    return CountrySide(
        id=row["id"],
        label=geography_name(lang, row["geography"]),
        title=series_title(lang, row["family"], row["geography"]),
        source_title=source_title(lang, row["source"]),
        attribution=source_text(row["attribution"]),
        unit_text=base_unit_text(lang, row["unit"]),
        latest_display=format_value(value["value_text"]),
        latest_period_text=format_period(period, frequency),
        status_flag=status,
        status_text=_status_text(lang, status),
        licence=source_text(row["licence"]),
        provenance=reads.provenance_view(provenance, frequency, lang) if provenance else None)


def page(db: Db, slug: str, *, lang: str = "pt") -> CountryComparisonPage | None:
    """One curated group, or None when it cannot be drawn exactly as authored.

    An unknown slug is a reader's 404. A known slug with an incomplete or malformed authored
    definition raises MissingText, which the app logs and renders as the generic 503.
    """
    if slug not in country_comparisons(lang):
        return None
    definition = country_comparison(lang, slug)
    published = _published_group(db, definition, slug, lang)
    if published is None:
        return None
    last_period = published.points[-1]["period"]
    sides = tuple(
        _side(db, side.row, side.values_by_period[last_period], last_period,
              published.frequency, lang)
        for side in published.sides)
    labels = tuple(side.label for side in sides)
    unit_text = base_unit_text(lang, published.sides[0].row["unit"])
    prepared = reads.prepare_group_chart(
        published.points, frequency=published.frequency, title=definition["title"],
        labels=labels, unit=unit_text)
    if prepared.chart is None:
        log.warning("country comparison %s hidden: no drawable chart", slug)
        return None
    rows = tuple(
        CountryTableRow(
            period_text=format_period(point["period"], published.frequency),
            cells=tuple(
                CountryValueCell(
                    display=format_value(token),
                    status_text=_status_text(
                        lang, side.values_by_period[point["period"]]["status_flag"]))
                for token, side in zip(point["values"], published.sides)))
        for point in reversed(published.points))
    return CountryComparisonPage(
        slug=slug, title=definition["title"], subtitle=definition["subtitle"],
        mechanism=definition["mechanism"], caption_note=definition["caption_note"],
        definition_note=definition["definition_note"],
        notebook_action=definition["notebook_action"],
        chart=prepared.chart, chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        table_rows=rows,
        alignment_text=alignment_text(published.points, published.missing, published.dropped,
                                      published.unparsed, labels, published.frequency),
        countries=sides,
        latest_period_text=format_period(last_period, published.frequency),
        unit_text=unit_text,
        frequency_text=frequency_text(lang, published.frequency))


def index(db: Db, *, lang: str = "pt") -> CountryComparisonIndex:
    """The /comparar country section: validation and bounded coverage, no chart preparation."""
    rows = []
    for slug in country_comparisons(lang):
        definition = country_comparison(lang, slug)
        published = _published_group(db, definition, slug, lang)
        if published is None:
            continue
        labels = tuple(geography_name(lang, side.row["geography"]) for side in published.sides)
        first = format_period(published.points[0]["period"], published.frequency)
        last = format_period(published.points[-1]["period"], published.frequency)
        rows.append(CountryComparisonSummary(
            slug=slug, title=definition["title"], subtitle=definition["subtitle"],
            countries_text=_join_labels(labels), span_text=f"{first} a {last}",
            common_text=_common_text(len(published.points))))
    return CountryComparisonIndex(
        title=country_comparisons_title(lang), intro=country_comparisons_intro(lang),
        rows=tuple(rows))
