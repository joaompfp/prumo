"""The indicator notebook: a read-only selection of eligible public series.

The selection is a list of series ids carried in the address. This module validates that
address, then composes cards and search results from one read-only snapshot. It holds no SQL,
no cache and no write path: `reads.prepare_card` and `reads.search` remain the authoritative
readers, and `ingest.editorial_rules` stays the authoritative eligibility rule.
"""
import re
from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlencode

from app import reads
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


def selection_path(selection: Sequence[str], query: str | None = None) -> str:
    """A local notebook address carrying `selection` in order, and the search only when asked.

    The path never accepts a host or a caller-supplied prefix: the template adds the one
    validated mount prefix. `query=None` is the clean, canonical address a reader bookmarks.
    """
    params = [("s", series_id) for series_id in selection]
    if query:
        params.append(("q", query))
    encoded = urlencode(params)
    return f"/caderno?{encoded}" if encoded else "/caderno"


@dataclass(frozen=True)
class NotebookCard:
    card: reads.Card
    remove_path: str


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
    max_selection: int
    query: str
    results: tuple[NotebookResult, ...]
    canonical_path: str
    clear_path: str | None
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


def page(db: Db, selection: tuple[str, ...], query: str = "", *,
         lang: str = "pt") -> NotebookPage:
    """Compose the notebook from one read-only handle.

    `selection` and `query` must already have passed `parse_selection`/`parse_query`; this
    function is deliberately pure composition and does not repeat address parsing. Selected
    ids that no longer qualify are omitted with a reader-facing count, never with their id or
    a machine reason.
    """
    if parse_selection(selection) != tuple(selection):
        raise ValueError("selection must be validated, ordered and deduplicated")
    if parse_query(query) != query:
        raise ValueError("query must be validated and stripped")

    cards: list[reads.Card] = []
    valid_ids: list[str] = []
    for series_id in selection:
        card, reason = reads.prepare_card(db, series_id, lang=lang)
        if card is None:
            if reason == "missing_title":
                # The slot rule turns an unnameable series into a dropped card; the notebook
                # must not turn a missing built-in catalogue entry into a silent omission.
                raise MissingText(f"no reader title for selected notebook series {series_id!r}")
            continue
        valid_ids.append(series_id)
        cards.append(card)

    selected = set(valid_ids)
    results: list[NotebookResult] = []
    if query:
        for row in _eligible_search_rows(db, query, lang):
            if row.id in selected:
                path = selection_path([i for i in valid_ids if i != row.id], query)
            elif len(valid_ids) >= MAX_SELECTION:
                path = None
            else:
                path = selection_path([*valid_ids, row.id], query)
            results.append(NotebookResult(row=row, selected=row.id in selected,
                                          action_path=path))

    card_views = tuple(NotebookCard(
        card=card,
        remove_path=selection_path([i for i in valid_ids if i != card.series_id], query),
    ) for card in cards)
    copy_text = text(lang)
    skipped = len(selection) - len(valid_ids)
    return NotebookPage(
        cards=card_views,
        skipped_count=skipped,
        skipped_notice=skipped_text(lang, skipped) if skipped else "",
        selection=tuple(valid_ids),
        max_selection=MAX_SELECTION,
        query=query,
        results=tuple(results),
        canonical_path=selection_path(valid_ids),
        clear_path=selection_path((), query) if valid_ids else None,
        at_limit=len(valid_ids) >= MAX_SELECTION,
        search_empty_text=search_empty_text(lang, query) if query else "",
        results_notice=results_text(lang, len(results)) if results else "",
        copy=copy_text,
    )
