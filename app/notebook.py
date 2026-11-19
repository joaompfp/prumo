"""The indicator notebook: a read-only selection of eligible public series.

The selection is a list of series ids carried in the address. This module validates that
address, then composes cards and search results from one read-only snapshot. It holds no SQL,
no cache and no write path: `reads.prepare_card` and `reads.search` remain the authoritative
readers, and `ingest.editorial_rules` stays the authoritative eligibility rule.
"""
import re
from dataclasses import dataclass, replace
from typing import Sequence
from urllib.parse import urlencode

from app import notebook_chart, reads
from ingest.db import Db
from ingest.editorial_rules import MAX_SLOTS, slot_problem
from presentation import MissingText
from presentation.notebook import NotebookCopy, results_text, search_empty_text, skipped_text, text

MAX_SELECTION = MAX_SLOTS
MAX_QUERY = 200
_SERIES_ID = re.compile(r"[A-Za-z0-9_.-]{1,255}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def parse_selection(values: Sequence[str]) -> tuple[str, ...] | None:
    """The ordered, deduplicated selection, or None for an invalid address.

    Over-limit means over-limit before deduplication: a reader who sends thirteen `s` values
    gets the generic 404 rather than a silently truncated notebook. The order of first
    appearance is kept, so reopening the same address keeps the reader's card order.
    """
    if len(values) > MAX_SELECTION:
        return None
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, str) or _SERIES_ID.fullmatch(value) is None:
            return None
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def parse_query(value: str) -> str | None:
    """The search term, stripped, or None when it is too long or carries control characters."""
    if not isinstance(value, str):
        return None
    if len(value) > MAX_QUERY or _CONTROL.search(value):
        return None
    return value.strip()


def selection_path(selection: Sequence[str], query: str | None = None, *,
                   chart: notebook_chart.ChartSettings | None = None) -> str:
    """A local notebook address carrying `selection` in order, and the search only when asked.

    The path never accepts a host or a caller-supplied prefix: the template adds the one
    validated mount prefix. `query=None` is the clean, canonical address a reader bookmarks.
    Chart settings are appended only when a caller passes them; the old one-argument form used by
    the series pages keeps its exact `/caderno?s=...` behaviour and defaults.
    """
    params = [("s", series_id) for series_id in selection]
    if chart is not None:
        params.extend(chart.params())
    if query:
        params.append(("q", query))
    encoded = urlencode(params)
    return f"/caderno?{encoded}" if encoded else "/caderno"


@dataclass(frozen=True)
class NotebookCard:
    card: reads.Card
    remove_path: str
    chart_state: str
    chart_status: str


@dataclass(frozen=True)
class NotebookResult:
    row: reads.Row
    selected: bool
    action_path: str | None


@dataclass(frozen=True)
class NotebookPage:
    cards: tuple[NotebookCard, ...]
    skipped_count: int
    skipped_notice: str
    selection: tuple[str, ...]
    addressed: tuple[str, ...]
    max_selection: int
    query: str
    results: tuple[NotebookResult, ...]
    canonical_path: str
    clear_path: str | None
    chart_panel: notebook_chart.NotebookChart
    chart_off_path: str
    chart_auto_path: str
    at_limit: bool
    search_empty_text: str
    results_notice: str
    copy: NotebookCopy


def _eligible_search_rows(db: Db, query: str, lang: str) -> tuple[reads.Row, ...]:
    """Search rows rechecked against fresh registry/source facts, before any add link.

    `reads.search` keeps the existing public search semantics but resolves through the short
    catalogue cache. A series deactivated or a source withdrawn a moment ago can still be in
    that list, so each row is passed through the same eligibility rule the cards use.
    """
    rows = reads.search(db, query, lang=lang)
    facts, _ = reads.slot_facts(db, [(row.id, None) for row in rows], lang=lang)
    eligible = []
    for row, fact in zip(rows, facts):
        reason = slot_problem(fact, titles_taken=set(), lang=lang)
        if reason == "missing_title":
            raise MissingText(f"no reader title for notebook search series {row.id!r}")
        if reason is None:
            eligible.append(row)
    return tuple(eligible)


def _card_chart_status(panel: notebook_chart.NotebookChart, series_id: str,
                       copy: NotebookCopy) -> tuple[str, str]:
    """The card's actual chart role in this response, never just its checkbox intent.

    A requested but undrawable chart reports `unavailable` for every card: no eligible card
    may claim to be plotted when the reader will not see a line. An explicit subset labels the
    cards outside the drawn group honestly, and only a ready panel can say "no gráfico".
    """
    if panel.state == "ready":
        if any(side.series_id == series_id for side in panel.sides):
            return "drawn", copy.card_chart_drawn.format(period=panel.last_period_text)
        return "excluded", copy.card_chart_excluded.format(period=panel.last_period_text)
    state = panel.public_state
    if state == "off":
        return "off", copy.card_chart_off
    if state == "empty":
        return "empty", copy.card_chart_empty
    if state == "choose":
        return "choose", copy.card_chart_choose
    return "unavailable", copy.card_chart_unavailable


def page(db: Db, selection: tuple[str, ...], query: str = "", *,
         lang: str = "pt",
         chart_settings: notebook_chart.ChartSettings | None = None) -> NotebookPage:
    """Compose the notebook from one read-only handle.

    `selection` and `query` must already have passed `parse_selection`/`parse_query`; this
    function is deliberately pure composition and does not repeat address parsing. Selected
    ids that no longer qualify are omitted from the cards and the eligible selection with a
    reader-facing count, never with their id or a machine reason. `addressed` keeps the whole
    validated address, so chart settings and action links do not silently drop a series that
    merely lost eligibility.
    """
    if parse_selection(selection) != tuple(selection):
        raise ValueError("selection must be validated, ordered and deduplicated")
    if parse_query(query) != query:
        raise ValueError("query must be validated and stripped")
    settings = chart_settings if chart_settings is not None else notebook_chart.ChartSettings()
    if len(settings.group) > notebook_chart.MAX_GROUP:
        raise ValueError("chart group must have at most six sides")
    if any(series_id not in selection for series_id in settings.group):
        raise ValueError("chart group must belong to the addressed selection")

    cards_by_id: dict[str, reads.Card] = {}
    for series_id in selection:
        card, reason = reads.prepare_card(db, series_id, lang=lang)
        if card is None:
            if reason == "missing_title":
                # The slot rule turns an unnameable series into a dropped card; the notebook
                # must not turn a missing built-in catalogue entry into a silent omission.
                raise MissingText(f"no reader title for selected notebook series {series_id!r}")
            continue
        cards_by_id[series_id] = card
    valid_ids = list(cards_by_id)

    addressed_set = set(selection)
    results: list[NotebookResult] = []
    if query:
        for row in _eligible_search_rows(db, query, lang):
            if row.id in addressed_set:
                pruned = notebook_chart.without_side(settings, row.id)
                path = selection_path([i for i in selection if i != row.id], query, chart=pruned)
            elif len(selection) >= MAX_SELECTION:
                path = None
            else:
                path = selection_path([*selection, row.id], query, chart=settings)
            results.append(NotebookResult(row=row, selected=row.id in addressed_set,
                                          action_path=path))

    copy_text = text(lang)
    skipped = len(selection) - len(valid_ids)
    chart_panel = notebook_chart.prepare(db, selection, cards_by_id, settings, lang=lang)
    cards = tuple(cards_by_id[series_id] for series_id in valid_ids)
    card_views_list = []
    for card in cards:
        chart_state, chart_status = _card_chart_status(chart_panel, card.series_id, copy_text)
        card_views_list.append(NotebookCard(
            card=card,
            remove_path=selection_path(
                [i for i in selection if i != card.series_id], query,
                chart=notebook_chart.without_side(settings, card.series_id)),
            chart_state=chart_state,
            chart_status=chart_status,
        ))
    card_views = tuple(card_views_list)
    canonical_path = selection_path(selection, chart=settings) if selection else "/caderno"
    return NotebookPage(
        cards=card_views,
        skipped_count=skipped,
        skipped_notice=skipped_text(lang, skipped) if skipped else "",
        selection=tuple(valid_ids),
        addressed=selection,
        max_selection=MAX_SELECTION,
        query=query,
        results=tuple(results),
        canonical_path=canonical_path,
        clear_path=selection_path((), query) if selection else None,
        chart_panel=chart_panel,
        chart_off_path=(selection_path(selection, query, chart=replace(
            settings, mode="off", group=())) if selection else ""),
        chart_auto_path=(selection_path(selection, query, chart=replace(
            settings, mode="all", group=())) if selection else ""),
        at_limit=len(selection) >= MAX_SELECTION,
        search_empty_text=search_empty_text(lang, query) if query else "",
        results_notice=results_text(lang, len(results)) if results else "",
        copy=copy_text,
    )
