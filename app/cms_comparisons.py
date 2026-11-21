"""The public comparison directory reads published CMS content only.

This is a listing of authored chart revisions, not another curation registry. Drafts cannot
change it; withdrawing a publication cannot revive a hard-coded comparison. All chart values
and eligibility still come from the authoritative CMS preparation on the caller's snapshot.
"""
from dataclasses import dataclass

from app import cms_reads
from ingest import cms as documents
from ingest.db import Db
from presentation import MissingText, base_unit_text, family_of, series_title

GROUPS = (("portugal", "Portugal"), ("countries", "Entre países"), ("general", "Outras leituras"))


@dataclass(frozen=True)
class ComparisonSummary:
    slug: str
    title: str
    note: str
    window_text: str
    series_count: int


@dataclass(frozen=True)
class ComparisonGroup:
    code: str
    title: str
    rows: tuple[ComparisonSummary, ...]


@dataclass(frozen=True)
class ComparisonIndex:
    groups: tuple[ComparisonGroup, ...]


def public_chart(db: Db, slug: str, lang: str = "pt") -> cms_reads.CmsChartView | None:
    """The published editorial comparison, never a query-string selection."""
    view = cms_reads.public_chart(db, slug, lang)
    return view if view is not None and view.comparison_group is not None else None


def index(db: Db, lang: str = "pt") -> ComparisonIndex:
    groups: dict[str, list[ComparisonSummary]] = {code: [] for code, _ in GROUPS}
    catalogue = {row["id"]: {**row, "family": family_of(row["indicator_key"])}
                 for row in db.public_catalogue()}
    for meta in db.cms_list("chart", published_only=True):
        # Read the published body first: library charts do not incur a statistical read.
        row = db.cms_revision("chart", meta["slug"], meta["published_revision_id"])
        if row is None:
            continue
        try:
            document = documents.parse_body("chart", row["body_json"])
        except (documents.CmsDocumentError, ValueError):
            continue
        if not isinstance(document, documents.ChartDocument) or document.comparison_group is None:
            continue
        rows = tuple(catalogue[sid] for sid in document.series_ids if sid in catalogue)
        if cms_reads.chart_definition_problem(document, rows):
            continue
        try:
            for selected in rows:
                series_title(lang, selected["family"], selected["geography"])
                base_unit_text(lang, selected["unit"])
        except MissingText:
            continue
        groups[document.comparison_group].append(ComparisonSummary(
            slug=meta["slug"], title=document.title, note=document.note,
            window_text=cms_reads.WINDOW_TEXT[document.window], series_count=len(rows)))
    return ComparisonIndex(groups=tuple(
        ComparisonGroup(code=code, title=title, rows=tuple(rows))
        for code, title in GROUPS if (rows := groups[code])))
