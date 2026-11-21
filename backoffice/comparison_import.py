"""One-time, audited conversion of the real comparison catalogue into CMS content.

The old definitions are import material only. Public requests never call this module. Existing
operator documents, including private or deliberately unpublished drafts, are never overwritten.
"""
from dataclasses import dataclass

from app import cms_reads
from backoffice.cms import Cms, CmsRefused
from ingest import cms as documents
from ingest.db import read_db_readonly
from presentation import portugal_comparisons
from presentation.catalog import pt


@dataclass(frozen=True)
class ComparisonImport:
    slug: str
    body: dict


def _body(title, note, ids, *, group, scale="single", window="max", axes=None):
    return {
        "title": title, "note": note, "series_a": ids[0],
        "series_b": ids[1] if len(ids) > 1 else None,
        "series_extra": list(ids[2:]), "window": window, "scale": scale,
        "day": None, "axes": axes, "comparison_group": group,
        "frequency": "original", "transform": "original", "base": None,
    }


def definitions() -> tuple[ComparisonImport, ...]:
    """The nine existing compositions, with their reviewed text and statistical references."""
    entries = []
    for slug, definition in pt.COMPARISONS.items():
        note = "\n\n".join(definition[key] for key in ("subtitle", "mechanism", "caption_note"))
        dual = definition["scale"] == "dual_axis"
        entries.append(ComparisonImport(slug, _body(
            definition["title"], note, (definition["series_a"], definition["series_b"]),
            group="portugal", scale="dual" if dual else "single",
            axes=[0, 1] if dual else [0, 0])))
    for definition in portugal_comparisons.definitions("pt"):
        entries.append(ComparisonImport(definition.slug, _body(
            definition.title, definition.summary + "\n\n" + definition.caveat,
            definition.series, group="portugal", scale="dual", window="10y",
            axes=list(definition.axes))))
    for slug, definition in pt.COUNTRY_COMPARISONS.items():
        note = "\n\n".join(dict.fromkeys(definition[key] for key in
                                       ("subtitle", "mechanism", "caption_note", "definition_note")))
        ids = tuple(f"{definition['family']}.{country}"
                    for country in pt.COUNTRY_COMPARISONS_COUNTRIES)
        entries.append(ComparisonImport(slug, _body(
            definition["title"], note, ids, group="countries", axes=[0] * len(ids))))
    return tuple(entries)


def install(cms: Cms, *, actor: str, note: str, publish: bool,
            entries: tuple[ComparisonImport, ...] | None = None) -> tuple[dict, ...]:
    """Create real CMS drafts and optionally publish; a rerun preserves existing publications.

    Preflight every selected entry before the first write. Any existing unpublished document
    is an operator collision, not permission to publish their draft. If a later publication is
    refused because data eligibility changed, the audited draft stays private for the operator.
    """
    candidates = definitions() if entries is None else entries
    if len({entry.slug for entry in candidates}) != len(candidates):
        raise CmsRefused("a importação repete um endereço")
    pending = []
    result = []
    for entry in candidates:
        document = documents.parse_body("chart", entry.body)
        if not isinstance(document, documents.ChartDocument):
            raise CmsRefused("a importação aceita apenas gráficos")
        documents.validate_slug(entry.slug)
        existing = cms.get("chart", entry.slug)
        if existing is not None:
            if existing["meta"]["published_revision_id"] is None:
                raise CmsRefused(f"chart/{entry.slug}: já existe um rascunho; não foi alterado")
            result.append({"slug": entry.slug, "status": "preserved",
                           "version": existing["meta"]["version"]})
            continue
        problem = read_db_readonly(cms.db_path, lambda db: cms_reads.chart_problem(db, document))
        if problem:
            raise CmsRefused(f"chart/{entry.slug}: {problem}")
        pending.append(entry)
    for entry in pending:
        meta = cms.create("chart", entry.slug, entry.body, actor=actor, note=note)
        if publish:
            meta = cms.publish("chart", entry.slug, meta["version"], actor=actor, note=note)
        result.append({"slug": entry.slug, "status": "published" if publish else "draft",
                       "version": meta["version"],
                       "published_revision_id": meta["published_revision_id"]})
    return tuple(result)
