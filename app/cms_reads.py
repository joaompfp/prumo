"""Public reads of authored CMS documents, prepared from one read-only snapshot.

No SQL here: every value comes through a `Db` method. Public calls read the PUBLISHED revision
only; `render_preview` reads the CURRENT DRAFT and is reachable only from the authenticated
backoffice. Both paths revalidate every series, derived key and chart reference with the same
eligibility rule the publish refusal uses, so a licence revoked after publication cannot be
exposed through a page: the block is dropped, one generic note is shown and the machine reason
is logged for the operator.

Chart values and provenance come from `app.reads` preparation helpers, never from a second
implementation of the built-in detail pages.
"""
import logging
import re
from dataclasses import dataclass

from app import reads
from app.chart_model import ComparisonModel, LineChartModel
from app.formatting import format_count, format_datetime, format_period, format_value
from ingest import cms as documents
from ingest.db import Db
from ingest.editorial_rules import slot_problem
from presentation import (
    MissingText,
    base_unit_text,
    calculated_attribution,
    caveat_text,
    chart_ui,
    derived_title,
    describe_formula,
    family_of,
    frequency_text,
    series_title,
    source_text,
    source_title,
    theme_text,
    unit_text,
)

log = logging.getLogger("prumo.app")

SECTION_ORDER = ("economy", "demography", "energy", "general")
SECTION_TITLES = {"general": "Geral"}
WINDOW_TEXT = {"max": "Máximo", "1y": "1 ano", "5y": "5 anos", "10y": "10 anos"}
AVAILABILITY_NOTE = "Parte desta página não está disponível neste momento."
CHART_UNAVAILABLE_NOTE = "Este gráfico não está disponível neste momento."
_SUMMARY_CHARS = 180


# --- reader views ----------------------------------------------------------------------------

@dataclass(frozen=True)
class ChartTableRow:
    period_text: str
    a_display: str
    b_display: str = ""


@dataclass(frozen=True)
class ChartLine:
    """One plotted series at the LAST PERIOD THE CHART DRAWS, with its own provenance."""

    title: str
    href: str
    unit_text: str
    frequency_text: str
    source_title: str
    attribution: str
    licence: str
    licence_url: str
    period_text: str
    value_display: str
    provenance: reads.ProvenanceView | None
    base_href: str = ""
    base_title: str = ""
    is_derived: bool = False


@dataclass(frozen=True)
class CalculatedNote:
    """The declared arithmetic behind a one-series calculated chart."""

    badge: str
    formula_text: str
    caveats: tuple[str, ...]
    base_title: str
    base_value_display: str
    base_unit_text: str
    base_period_text: str
    computed_text: str
    attribution: str
    licence: str
    licence_url: str


@dataclass(frozen=True)
class CmsChartView:
    slug: str
    title: str
    note: str
    scale: str
    window: str
    window_text: str
    day: str | None
    frequency: str
    frequency_text: str
    is_pair: bool
    chart: LineChartModel | ComparisonModel | None
    chart_payload: dict | None
    chart_range_label: str
    chart_hint: str
    provenance: tuple[ChartLine, ...]
    table: tuple[ChartTableRow, ...]
    table_note: str
    calculated: CalculatedNote | None

    @property
    def unit_text(self) -> str:
        return self.provenance[0].unit_text if self.provenance else ""


@dataclass(frozen=True)
class TextBlockView:
    type: str
    paragraphs: tuple[str, ...]


@dataclass(frozen=True)
class CardBlockView:
    type: str
    card: reads.Card


@dataclass(frozen=True)
class ChartBlockView:
    type: str
    chart: CmsChartView


BlockView = TextBlockView | CardBlockView | ChartBlockView


@dataclass(frozen=True)
class CmsPageView:
    slug: str
    title: str
    introduction: tuple[str, ...]
    section: str
    section_text: str
    blocks: tuple[BlockView, ...]
    has_charts: bool
    availability_note: str

    @property
    def chart_payload(self) -> dict | None:
        """The first payload the page carries: the public renderer's script decision."""
        for block in self.blocks:
            if isinstance(block, ChartBlockView) and block.chart.chart_payload is not None:
                return block.chart.chart_payload
        return None


@dataclass(frozen=True)
class CmsPageSummary:
    slug: str
    title: str
    section: str
    section_text: str
    introduction: str


@dataclass(frozen=True)
class CmsSection:
    code: str
    title: str
    pages: tuple[CmsPageSummary, ...]


@dataclass(frozen=True)
class CmsIndex:
    sections: tuple[CmsSection, ...]


# --- helpers ---------------------------------------------------------------------------------

def section_title(lang: str, code: str) -> str:
    if code in SECTION_TITLES:
        return SECTION_TITLES[code]
    try:
        return theme_text(lang, code)
    except MissingText:
        return code


def _paragraphs(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in re.split(r"\n\s*\n", text) if part.strip())


def _summary_text(text: str) -> str:
    first = (_paragraphs(text) or ("",))[0]
    return first if len(first) <= _SUMMARY_CHARS else first[:_SUMMARY_CHARS - 3] + "..."


def _document(db: Db, kind: str, slug: str, revision_id: int | None):
    """The typed body of one exact revision, or None when the stored body is unusable."""
    if revision_id is None:
        return None
    row = db.cms_revision(kind, slug, revision_id)
    if row is None:
        log.error("cms %s/%s: revision %s is missing", kind, slug, revision_id)
        return None
    try:
        return documents.parse_body(kind, row["body_json"])
    except (documents.CmsDocumentError, ValueError) as exc:
        log.error("cms %s/%s: stored body is invalid: %s", kind, slug, exc)
        return None


def _frequency_text(lang: str, frequency: str) -> str:
    try:
        return frequency_text(lang, frequency)
    except MissingText:
        return ""


def _primary_line(db: Db, row: dict, period: str, token: str, frequency: str,
                  lang: str) -> ChartLine:
    provenance = db.public_provenance_at(row["id"], period)
    return ChartLine(
        title=series_title(lang, family_of(row["indicator_key"]), row["geography"]),
        href=f"/series/{row['id']}",
        unit_text=base_unit_text(lang, row["unit"]),
        frequency_text=_frequency_text(lang, frequency),
        source_title=source_title(lang, row["source"]),
        attribution=source_text(row["attribution"]),
        licence=source_text(row["licence"]),
        licence_url=row["licence_url"],
        period_text=format_period(period, frequency),
        value_display=format_value(token),
        provenance=reads.provenance_view(provenance, frequency, lang) if provenance else None)


def _prepared_view(slug: str, doc: documents.ChartDocument, prepared: reads.PreparedChart,
                   *, frequency: str, lang: str, lines: tuple[ChartLine, ...],
                   table: tuple[ChartTableRow, ...], table_note: str,
                   calculated: CalculatedNote | None) -> CmsChartView:
    return CmsChartView(
        slug=slug, title=doc.title, note=doc.note, scale=doc.scale, window=doc.window,
        window_text=WINDOW_TEXT.get(doc.window, doc.window), day=doc.day, frequency=frequency,
        frequency_text=_frequency_text(lang, frequency), is_pair=len(lines) == 2,
        chart=prepared.chart, chart_payload=prepared.chart_payload,
        chart_range_label=prepared.chart_range_label, chart_hint=prepared.chart_hint,
        provenance=lines, table=table, table_note=table_note, calculated=calculated)


# --- the one chart preparation used by the public site, the preview and publish -------------

def chart_view(db: Db, slug: str, doc: documents.ChartDocument,
               lang: str = "pt") -> tuple[CmsChartView | None, str | None]:
    """(view, None) when the chart can be drawn from current public data, else (None, reason).

    The reason is operator text: it may name a series id or a machine token and is only ever
    logged. Nothing here checks or mutates the published pointer; the caller chose the revision.
    """
    try:
        view = _chart_view(db, slug, doc, lang)
    except (MissingText, ValueError) as exc:
        return None, f"unavailable:{exc}"
    if view is None:
        return None, "unavailable"
    return view, None


def chart_problem(db: Db, doc: documents.ChartDocument, lang: str = "pt") -> str | None:
    """None when `doc` is publishable now, else the operator reason (used inside the tx)."""
    view, reason = chart_view(db, "", doc, lang)
    return None if view is not None else (reason or "unavailable")


def _chart_view(db: Db, slug: str, doc: documents.ChartDocument,
                lang: str) -> CmsChartView | None:
    if not isinstance(doc, documents.ChartDocument):
        return None
    derived_key = doc.derived_key if doc.series_b is None else None
    pairs = [(doc.series_a, derived_key)]
    if doc.series_b is not None:
        pairs.append((doc.series_b, None))
    facts, raw = reads.slot_facts(db, pairs, lang)
    if any(fact is None for fact in facts):
        return None
    for fact in facts:
        if slot_problem(fact, titles_taken=set(), lang=lang) is not None:
            return None
    frequency = raw[doc.series_a]["frequency"]
    if doc.day and frequency != "PT15M":
        raise ValueError("o dia UTC só é válido para séries de 15 minutos")

    if derived_key is not None:
        return _derived_chart_view(db, slug, doc, derived_key, facts[0], raw[doc.series_a], lang)
    if doc.series_b is not None:
        return _pair_chart_view(db, slug, doc, lang)
    return _single_chart_view(db, slug, doc, lang)


def _window_values(db: Db, series_id: str, latest: str, frequency: str, window: str
                   ) -> list[dict]:
    start = reads.window_start(latest, frequency, window)
    return (db.public_values_between(series_id, start) if start
            else db.public_series_values(series_id))


def _single_chart_view(db: Db, slug: str, doc: documents.ChartDocument,
                       lang: str) -> CmsChartView | None:
    row = db.public_series(doc.series_a)
    if row is None:
        return None
    frequency = row["frequency"]
    if frequency == "PT15M":
        if not doc.day:
            return None
        values = db.public_values_between(doc.series_a, doc.day, f"{doc.day}T99")
    else:
        values = _window_values(db, doc.series_a, row["latest_period"], frequency, doc.window)
    if not values:
        return None
    points = tuple({"period": v["period"], "value_text": v["value_text"]} for v in values)
    prepared = reads.prepare_line_chart(points, frequency=frequency, title=doc.title,
                                        unit=base_unit_text(lang, row["unit"]))
    if prepared.chart is None:
        return None  # every stored token is non-finite: not a drawable chart
    last = values[-1]
    line = _primary_line(db, row, last["period"], last["value_text"], frequency, lang)
    table = tuple(ChartTableRow(period_text=format_period(v["period"], frequency),
                                a_display=format_value(v["value_text"]))
                  for v in reversed(values))
    note = (f"{format_count(len(table))} intervalos no dia UTC escolhido."
            if frequency == "PT15M" else f"{format_count(len(table))} períodos no intervalo.")
    return _prepared_view(slug, doc, prepared, frequency=frequency, lang=lang, lines=(line,),
                          table=table, table_note=note, calculated=None)


def _pair_chart_view(db: Db, slug: str, doc: documents.ChartDocument,
                     lang: str) -> CmsChartView | None:
    if doc.series_b is None:
        return None
    series_b = doc.series_b
    row_a = db.public_series(doc.series_a)
    row_b = db.public_series(series_b)
    if row_a is None or row_b is None or row_a["frequency"] != row_b["frequency"]:
        return None
    frequency = row_a["frequency"]
    if frequency == "PT15M":
        if not doc.day:
            return None
        values_a = db.public_values_between(doc.series_a, doc.day, f"{doc.day}T99")
        values_b = db.public_values_between(series_b, doc.day, f"{doc.day}T99")
    else:
        latest = max(row_a["latest_period"], row_b["latest_period"])
        values_a = _window_values(db, doc.series_a, latest, frequency, doc.window)
        values_b = _window_values(db, series_b, latest, frequency, doc.window)
    points, dropped_a, dropped_b, unparsed = reads.align_periods(values_a, values_b)
    if not points:
        return None
    unit_a = base_unit_text(lang, row_a["unit"])
    unit_b = base_unit_text(lang, row_b["unit"])
    dual = doc.scale == "dual"
    if unit_a != unit_b and not dual:
        return None
    title_a = series_title(lang, family_of(row_a["indicator_key"]), row_a["geography"])
    title_b = series_title(lang, family_of(row_b["indicator_key"]), row_b["geography"])
    prepared = reads.prepare_comparison_chart(
        points, frequency=frequency, title=doc.title, labels=(title_a, title_b),
        unit_a=unit_a, unit_b=unit_b, dual=dual)
    if prepared.chart is None:
        return None
    last = points[-1]
    lines = (_primary_line(db, row_a, last["period"], last["a"], frequency, lang),
             _primary_line(db, row_b, last["period"], last["b"], frequency, lang))
    table = tuple(ChartTableRow(period_text=format_period(p["period"], frequency),
                                a_display=format_value(p["a"]),
                                b_display=format_value(p["b"]))
                  for p in reversed(points))
    note = reads.alignment_text(points, dropped_a, dropped_b, unparsed, title_a, title_b,
                                frequency)
    return _prepared_view(slug, doc, prepared, frequency=frequency, lang=lang, lines=lines,
                          table=table, table_note=note, calculated=None)


def _derived_chart_view(db: Db, slug: str, doc: documents.ChartDocument, key: str, fact,
                        base_row: dict, lang: str) -> CmsChartView | None:
    d = db.public_derived(key)
    if d is None or d["base_series_id"] != doc.series_a:
        return None
    frequency = base_row["frequency"]
    values = db.public_derived_values(key)
    if not values:
        return None
    start = reads.window_start(values[-1]["period"], frequency, doc.window)
    shown = [v for v in values if start is None or v["period"] >= start]
    if not shown:
        return None
    points = tuple({"period": v["period"], "value_text": v["value_text"]} for v in shown)
    calc_unit = unit_text(lang, d["unit"])
    badge = chart_ui(lang, "calculated")
    prepared = reads.prepare_line_chart(points, frequency=frequency, title=doc.title,
                                        display_unit=calc_unit, badge=badge)
    if prepared.chart is None:
        return None
    base_title = fact.titles.get(lang) or doc.series_a
    base = db.public_series(doc.series_a)
    newest = db.served_derived_rows(key, 1)[1]
    newest = newest[0] if newest else None
    last = shown[-1]
    line = ChartLine(
        title=derived_title(lang, key), href=f"/calculadas/{key}",
        unit_text=calc_unit,
        frequency_text=_frequency_text(lang, frequency),
        source_title=source_title(lang, base_row["source"]),
        attribution=calculated_attribution(lang, newest["attribution"]) if newest else "",
        licence=source_text(newest["licence"]) if newest else "",
        licence_url=newest["licence_url"] if newest else "",
        period_text=format_period(last["period"], frequency),
        value_display=format_value(last["value_text"]), provenance=None,
        base_href=f"/series/{doc.series_a}", base_title=base_title, is_derived=True)
    table = tuple(ChartTableRow(period_text=format_period(v["period"], frequency),
                                a_display=format_value(v["value_text"]))
                  for v in reversed(shown))
    calculated = CalculatedNote(
        badge=badge,
        formula_text=describe_formula(lang, d["formula"], d["params"], base_title),
        caveats=tuple(caveat_text(lang, c) for c in d["caveats"]),
        base_title=base_title,
        base_value_display=format_value(base["latest_value_text"]) if base else "",
        base_unit_text=base_unit_text(lang, base["unit"]) if base else "",
        base_period_text=format_period(base["latest_period"], frequency) if base else "",
        computed_text=format_datetime(newest["computed_at"]) if newest else "",
        attribution=calculated_attribution(lang, newest["attribution"]) if newest else "",
        licence=source_text(newest["licence"]) if newest else "",
        licence_url=newest["licence_url"] if newest else "")
    note = f"{format_count(len(table))} períodos no intervalo."
    return _prepared_view(slug, doc, prepared, frequency=frequency, lang=lang, lines=(line,),
                          table=table, table_note=note, calculated=calculated)


# --- pages -----------------------------------------------------------------------------------

def _page_view(db: Db, slug: str, doc: documents.PageDocument, lang: str) -> CmsPageView:
    blocks: list[BlockView] = []
    dropped = 0
    taken: set[str] = set()
    for block in doc.blocks:
        if isinstance(block, documents.TextBlock):
            blocks.append(TextBlockView(type="text", paragraphs=_paragraphs(block.text)))
            continue
        if isinstance(block, documents.CardBlock):
            try:
                card, reason = reads.prepare_card(db, block.series_id, block.derived_key,
                                                  lang=lang, titles_taken=taken)
            except MissingText as exc:
                card, reason = None, f"missing_text:{exc}"
            if card is None:
                dropped += 1
                log.warning("cms page block dropped slug=%s kind=card series=%s reason=%s",
                            slug, block.series_id, reason)
                continue
            taken.add(card.title)
            blocks.append(CardBlockView(type="card", card=card))
            continue
        meta = db.cms_get("chart", block.chart_slug)
        chart_doc = (_document(db, "chart", block.chart_slug, meta["published_revision_id"])
                     if meta is not None else None)
        view, reason = (chart_view(db, block.chart_slug, chart_doc, lang)
                        if isinstance(chart_doc, documents.ChartDocument) else (None, "not_published"))
        if view is None:
            dropped += 1
            log.warning("cms page block dropped slug=%s kind=chart chart=%s reason=%s",
                        slug, block.chart_slug, reason)
            continue
        blocks.append(ChartBlockView(type="chart", chart=view))
    has_charts = any(isinstance(block, ChartBlockView) and block.chart.chart_payload is not None
                     for block in blocks)
    return CmsPageView(
        slug=slug, title=doc.title, introduction=_paragraphs(doc.introduction),
        section=doc.section, section_text=section_title(lang, doc.section),
        blocks=tuple(blocks), has_charts=has_charts,
        availability_note=AVAILABILITY_NOTE if dropped else "")


def _published_page(db: Db, slug: str) -> documents.PageDocument | None:
    meta = db.cms_get("page", slug)
    if meta is None or meta["published_revision_id"] is None:
        return None
    doc = _document(db, "page", slug, meta["published_revision_id"])
    return doc if isinstance(doc, documents.PageDocument) else None


def public_page(db: Db, slug: str, lang: str = "pt") -> CmsPageView | None:
    """One published page, or None for an unknown, unpublished or unusable document."""
    try:
        documents.validate_slug(slug)
    except documents.CmsDocumentError:
        return None
    doc = _published_page(db, slug)
    return _page_view(db, slug, doc, lang) if doc is not None else None


def public_chart(db: Db, slug: str, lang: str = "pt") -> CmsChartView | None:
    """One published chart by slug; None (a 404) when it cannot be drawn from public data."""
    try:
        documents.validate_slug(slug)
    except documents.CmsDocumentError:
        return None
    meta = db.cms_get("chart", slug)
    doc = (_document(db, "chart", slug, meta["published_revision_id"])
           if meta is not None else None)
    if not isinstance(doc, documents.ChartDocument):
        return None
    view, reason = chart_view(db, slug, doc, lang)
    if view is None:
        log.warning("cms chart unavailable slug=%s reason=%s", slug, reason)
    return view


def render_preview(db: Db, kind: str, slug: str,
                   lang: str = "pt") -> tuple[str, CmsPageView | CmsChartView] | None:
    """(template name, view) for the CURRENT DRAFT, in the caller's one read snapshot.

    The preview is reachable only from the authenticated backoffice. It deliberately uses the
    same availability rules as the public site, so it shows what publication would show; it
    never swaps a public revision. A chart whose data cannot be drawn has no preview.
    """
    try:
        kind = documents.validate_kind(kind)
        documents.validate_slug(slug)
    except documents.CmsDocumentError:
        return None
    meta = db.cms_get(kind, slug)
    if meta is None:
        return None
    doc = _document(db, kind, slug, meta["draft_revision_id"])
    if doc is None:
        return None
    if kind == "page" and isinstance(doc, documents.PageDocument):
        return "cms_page.html", _page_view(db, slug, doc, lang)
    if kind == "chart" and isinstance(doc, documents.ChartDocument):
        view, reason = chart_view(db, slug, doc, lang)
        if view is None:
            log.warning("cms preview unavailable kind=chart slug=%s reason=%s", slug, reason)
            return None
        return "cms_chart.html", view
    return None


# --- listings --------------------------------------------------------------------------------

def published_page_summaries(db: Db, lang: str = "pt") -> tuple[CmsPageSummary, ...]:
    """Published pages, section order then title, for /paginas and the theme links."""
    out: list[CmsPageSummary] = []
    for meta in db.cms_list("page", published_only=True):
        doc = _document(db, "page", meta["slug"], meta["published_revision_id"])
        if not isinstance(doc, documents.PageDocument):
            continue
        out.append(CmsPageSummary(
            slug=meta["slug"], title=doc.title, section=doc.section,
            section_text=section_title(lang, doc.section),
            introduction=_summary_text(doc.introduction)))
    order = {code: position for position, code in enumerate(SECTION_ORDER)}
    return tuple(sorted(out, key=lambda p: (order.get(p.section, len(order)), p.title, p.slug)))


def section_pages(db: Db, section: str, lang: str = "pt") -> tuple[CmsPageSummary, ...]:
    return tuple(page for page in published_page_summaries(db, lang)
                 if page.section == section)


def index(db: Db, lang: str = "pt") -> CmsIndex:
    summaries = published_page_summaries(db, lang)
    sections = []
    for code in SECTION_ORDER:
        pages = tuple(page for page in summaries if page.section == code)
        if pages:
            sections.append(CmsSection(code=code, title=section_title(lang, code), pages=pages))
    return CmsIndex(sections=tuple(sections))
