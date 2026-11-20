"""Read service for the curated Portugal comparisons on `/comparar`.

The reviewed configurations live in `presentation.portugal_comparisons`. This module resolves
each one against the current public catalogue on the route's read-only handle, validates that the
live scale signature still matches the reviewed groups, and builds the canonical Caderno address.
A configuration with any missing, withdrawn, inactive or re-scaled side is hidden whole: the index
never advertises half a comparison. There is no SQL and no chart preparation here.

Full series values, tables and provenance stay on the existing Caderno read path: the card is a
link to a configured notebook, not a second analytical service.
"""
import logging
from dataclasses import dataclass

from app import notebook, notebook_chart, reads
from ingest.db import Db
from presentation import base_unit_text, frequency_text, portugal_comparisons

log = logging.getLogger("prumo.app")


@dataclass(frozen=True)
class PortugalComparisonSummary:
    """One advertised configuration, resolved against current eligible catalogue rows."""

    slug: str
    title: str
    summary: str
    caveat: str
    path: str
    action: str
    groups_text: str
    frequency_text: str
    window_text: str
    series_text: str


@dataclass(frozen=True)
class PortugalComparisonIndex:
    title: str
    intro: str
    rows: tuple[PortugalComparisonSummary, ...]


def build_path(definition: portugal_comparisons.PortugalComparison) -> str:
    """The canonical Caderno address for one reviewed configuration."""
    settings = notebook_chart.ChartSettings(
        mode="explicit", group=definition.series, scale="dupla", window=definition.window)
    return notebook.selection_path(definition.series, chart=settings)


def _definition_groups_are_ordered(definition: portugal_comparisons.PortugalComparison) -> bool:
    """The first-seen group order must be left then right, with every group non-empty."""
    if len(definition.groups) != 2:
        return False
    seen: list[int] = []
    for group in definition.groups:
        if not group.series or group.axis not in (0, 1):
            return False
        if group.axis not in seen:
            seen.append(group.axis)
    return seen == [0, 1]


def _resolve(definition: portugal_comparisons.PortugalComparison,
             catalogue: dict[str, dict], lang: str) -> PortugalComparisonSummary | None:
    """One card, or None with a log line when the live data no longer matches the definition."""
    if not 3 <= len(definition.series) <= notebook_chart.MAX_GROUP:
        log.error("Portugal comparison %s has an invalid series count", definition.slug)
        return None
    if len(set(definition.series)) != len(definition.series):
        log.error("Portugal comparison %s repeats a series", definition.slug)
        return None
    if not _definition_groups_are_ordered(definition):
        log.error("Portugal comparison %s has invalid scale groups", definition.slug)
        return None
    if len(definition.axes) != len(definition.series):
        log.error("Portugal comparison %s has no axis for every series", definition.slug)
        return None

    group_by_axis = {group.axis: group for group in definition.groups}
    for series_id, axis in zip(definition.series, definition.axes):
        group = group_by_axis[axis]
        row = catalogue.get(series_id)
        if row is None:
            log.warning("Portugal comparison %s hidden: %s is not published",
                        definition.slug, series_id)
            return None
        if row["role"] != "primary" or row["frequency"] != definition.frequency:
            log.warning("Portugal comparison %s hidden: %s has the wrong role or frequency",
                        definition.slug, series_id)
            return None
        expected = (group.unit, group.multiplier, group.base_year)
        if notebook_chart.axis_signature(row) != expected:
            log.warning("Portugal comparison %s hidden: %s changed its scale signature",
                        definition.slug, series_id)
            return None

    copy = portugal_comparisons.text(lang)
    parts = []
    for group in definition.groups:
        label = copy.axis_left if group.axis == 0 else copy.axis_right
        parts.append(f"{label}: {base_unit_text(lang, group.unit)}")
    return PortugalComparisonSummary(
        slug=definition.slug, title=definition.title, summary=definition.summary,
        caveat=definition.caveat, path=build_path(definition), action=copy.action,
        groups_text=" · ".join(parts),
        frequency_text=frequency_text(lang, definition.frequency),
        window_text=portugal_comparisons.window_text(lang, definition.window),
        series_text=portugal_comparisons.series_text(lang, len(definition.series)))


def index(db: Db, *, lang: str = "pt") -> PortugalComparisonIndex:
    """The `/comparar` Portugal section, resolved on the same read-only snapshot."""
    catalogue = {row["id"]: row for row in reads.catalogue(db)}
    rows = []
    for definition in portugal_comparisons.definitions(lang):
        summary = _resolve(definition, catalogue, lang)
        if summary is not None:
            rows.append(summary)
    copy = portugal_comparisons.text(lang)
    return PortugalComparisonIndex(title=copy.title, intro=copy.intro, rows=tuple(rows))


__all__ = [
    "PortugalComparisonIndex",
    "PortugalComparisonSummary",
    "build_path",
    "index",
]
