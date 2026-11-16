"""CMS service: the backoffice's contract for authored pages and reusable charts.

No SQL here. Reads go through `read_db_readonly` (one snapshot per call); writes open the
restricted `open_db_for_write` handle and never migrate it. The service layer owns three
things the storage deliberately does not:

* shape: an untrusted body is parsed into `ingest.cms`'s typed document before any write, and
  a parse failure is `CmsRefused`, never a 500;
* eligibility at publication: the draft body is checked inside the storage publish
  transaction (`Db.cms_publish(check=...)`), so the decision and the pointer swap see the same
  snapshot. Saving an unfinished, currently ineligible draft stays allowed;
* reader choices: eligible primary series with both their raw tokens and rendered text, so the
  editor labels fields without reimplementing the catalogue.

`preview` returns exactly `(template_name, view)` where the name is `cms_page.html` or
`cms_chart.html`; the backoffice renders it with `preview=True` and its own `admin_base`.
"""
import logging
from pathlib import Path

from app import cms_reads, reads
from ingest import cms as documents
from ingest.db import (
    CmsConflict,  # noqa: F401 - re-exported as the service's own exception surface
    CmsNotFound,  # noqa: F401
    CmsRefused,
    Db,
    OperationalError,
    ReadOnlyOpenError,
    SchemaMismatchError,
    open_db_for_write,
    read_db_readonly,
)
from ingest.editorial_rules import page_problems, slot_problem
from presentation import (
    MissingText,
    base_unit_text,
    derived_title,
    frequency_text,
    geography_name,
    source_title,
    unit_text,
)

__all__ = ["Cms", "CmsBusy", "CmsConflict", "CmsNotFound", "CmsRefused", "CmsUnavailable"]

log = logging.getLogger("backoffice")


class CmsUnavailable(RuntimeError):
    """The writable mount is absent, missing, or at a schema this code does not know."""


class CmsBusy(RuntimeError):
    """The worker holds the database lock; nothing was written, retry shortly."""


class Cms:
    """One service instance per request; `writable_path` None means read-only/editor off."""

    def __init__(self, db_path: Path, writable_path: Path | None, lang: str = "pt"):
        self.db_path = Path(db_path)
        self.writable_path = Path(writable_path) if writable_path is not None else None
        self.lang = lang

    # --- reads ---------------------------------------------------------------------------

    def available(self) -> bool:
        return self.writable_path is not None

    def list(self, kind: str) -> tuple[dict, ...]:
        """Head summaries: kind, slug, title, version, published (and section for pages)."""
        kind = self._kind(kind)
        return self._read(lambda db: tuple(
            self._summary(db, kind, meta) for meta in db.cms_list(kind)))

    def get(self, kind: str, slug: str) -> dict | None:
        """meta, typed draft/published bodies, immutable history, events and chart usages."""
        kind = self._kind(kind)
        slug = self._slug(slug)
        return self._read(lambda db: self._get(db, kind, slug))

    def choices(self) -> tuple[dict, ...]:
        """Eligible primary series: raw tokens plus reader text, with their derived keys."""
        def build(db: Db):
            ids = db.all_series_ids()
            facts, raw = reads.slot_facts(db, [(sid, None) for sid in ids], self.lang)
            companions: dict[str, list[dict]] = {}
            for d in db.derived_list():
                if not d["active"]:
                    continue
                try:
                    unit_text(self.lang, d["unit"])
                    title = derived_title(self.lang, d["key"])
                except MissingText:
                    continue
                companions.setdefault(d["base_series_id"], []).append(
                    {"key": d["key"], "title": title})
            out = []
            for series_id, fact in zip(ids, facts):
                if fact is None or slot_problem(fact, titles_taken=set(),
                                                lang=self.lang) is not None:
                    continue
                row = raw[series_id]
                try:
                    out.append({
                        "id": series_id,
                        "title": fact.titles[self.lang],
                        "unit": row["unit"],
                        "unit_text": base_unit_text(self.lang, row["unit"]),
                        "frequency": row["frequency"],
                        "frequency_text": self._text(frequency_text, row["frequency"]),
                        "geography": row["geography"],
                        "geography_text": self._text(geography_name, row["geography"]),
                        "source": row["source"],
                        "source_title": self._text(source_title, row["source"]),
                        "theme": row["theme"],
                        "derived": tuple(sorted(companions.get(series_id, []),
                                                key=lambda item: item["key"])),
                    })
                except MissingText:
                    continue  # not nameable for the reader: not an eligible choice
            return tuple(sorted(out, key=lambda item: (item["title"], item["id"])))
        return self._read(build)

    def charts(self) -> tuple[dict, ...]:
        """Published chart summaries: what a page's chart block may reference."""
        return self._read(lambda db: tuple(
            summary for summary in (
                self._chart_summary(db, meta)
                for meta in db.cms_list("chart", published_only=True))
            if summary is not None))

    def preview(self, kind: str, slug: str) -> tuple[str, object] | None:
        """(template_name, view) for the current DRAFT, in one read-only snapshot.

        None when the document or its draft is missing, or when a chart cannot be drawn from
        current public data. The caller renders the named template with `preview=True` and
        `admin_base`; this method never touches a public revision.
        """
        kind = self._kind(kind)
        slug = self._slug(slug)
        return self._read(lambda db: cms_reads.render_preview(db, kind, slug, self.lang))

    # --- writes --------------------------------------------------------------------------

    def create(self, kind: str, slug: str, body_dict, *, actor: str, note: str) -> dict:
        kind = self._kind(kind)
        slug = self._slug(slug)
        body = self._canonical(kind, body_dict)
        return self._write(lambda db: db.cms_create(kind, slug, body, actor=actor, note=note))

    def save(self, kind: str, slug: str, version: int, body_dict, *, actor: str,
             note: str) -> dict:
        kind = self._kind(kind)
        slug = self._slug(slug)
        body = self._canonical(kind, body_dict)
        return self._write(lambda db: db.cms_save(kind, slug, version, body, actor=actor,
                                                  note=note))

    def publish(self, kind: str, slug: str, version: int, *, actor: str, note: str) -> dict:
        """Publish the draft only if every reference is eligible, atomically with the swap."""
        kind = self._kind(kind)
        slug = self._slug(slug)

        def write(db: Db):
            def check(check_kind: str, body_json: str) -> None:
                self._require_publishable(db, check_kind, slug, body_json)
            return db.cms_publish(kind, slug, version, actor=actor, note=note, check=check)

        return self._write(write)

    def unpublish(self, kind: str, slug: str, version: int, *, actor: str, note: str) -> dict:
        kind = self._kind(kind)
        slug = self._slug(slug)
        return self._write(lambda db: db.cms_unpublish(kind, slug, version, actor=actor,
                                                       note=note))

    def restore(self, kind: str, slug: str, version: int, revision_id: int, *, actor: str,
                note: str) -> dict:
        """Copy an old revision into a NEW draft; published content is untouched."""
        kind = self._kind(kind)
        slug = self._slug(slug)
        return self._write(lambda db: db.cms_restore(kind, slug, version, revision_id,
                                                     actor=actor, note=note))

    def duplicate(self, kind: str, slug: str, new_slug: str, *, actor: str,
                  note: str) -> dict:
        kind = self._kind(kind)
        slug = self._slug(slug)
        new_slug = self._slug(new_slug, "new_slug")
        return self._write(lambda db: db.cms_duplicate(kind, slug, new_slug, actor=actor,
                                                       note=note))

    # --- internals -----------------------------------------------------------------------

    def _read(self, fn):
        try:
            return read_db_readonly(self.db_path, fn)
        except ReadOnlyOpenError as exc:
            raise CmsUnavailable(str(exc)) from exc

    def _write(self, fn):
        if self.writable_path is None:
            raise CmsUnavailable("the writable mount is not configured (PRUMO_EDITORIAL_DB)")
        try:
            db = open_db_for_write(self.writable_path)
        except (FileNotFoundError, SchemaMismatchError) as exc:
            raise CmsUnavailable(str(exc)) from exc
        except OperationalError as exc:
            raise self._classify(exc) from exc
        try:
            return fn(db)
        except OperationalError as exc:
            raise self._classify(exc) from exc
        finally:
            db.close()

    @staticmethod
    def _classify(exc: OperationalError) -> RuntimeError:
        text = str(exc).lower()
        if "locked" in text or "busy" in text:
            return CmsBusy("the worker is writing to the database; nothing was changed, try "
                           "again in a few seconds")
        return CmsUnavailable(f"database error: {exc}")

    def _kind(self, kind: str) -> str:
        try:
            return documents.validate_kind(kind)
        except documents.CmsDocumentError as exc:
            raise CmsRefused(str(exc)) from None

    def _slug(self, slug: str, role: str = "slug") -> str:
        try:
            return documents.validate_slug(slug)
        except documents.CmsDocumentError as exc:
            raise CmsRefused(f"{role}: {exc}") from None

    def _canonical(self, kind: str, body) -> str:
        try:
            return documents.canonical_for(kind, body)
        except (documents.CmsDocumentError, TypeError, ValueError) as exc:
            raise CmsRefused(f"documento inválido: {exc}") from None

    def _text(self, fn, code: str) -> str:
        try:
            return fn(self.lang, code)
        except MissingText:
            return ""

    def _doc(self, db: Db, kind: str, slug: str, revision_id: int | None):
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

    def _summary(self, db: Db, kind: str, meta: dict) -> dict:
        doc = self._doc(db, kind, meta["slug"], meta["draft_revision_id"])
        summary = {"kind": kind, "slug": meta["slug"],
                   "title": getattr(doc, "title", None) or meta["slug"],
                   "version": meta["version"],
                   "published": meta["published_revision_id"] is not None}
        if kind == "page":
            summary["section"] = getattr(doc, "section", "")
        return summary

    def _chart_summary(self, db: Db, meta: dict) -> dict | None:
        doc = self._doc(db, "chart", meta["slug"], meta["published_revision_id"])
        if not isinstance(doc, documents.ChartDocument):
            return None
        return {"kind": "chart", "slug": meta["slug"], "title": doc.title,
                "version": meta["version"], "published": True, "note": doc.note}

    def _get(self, db: Db, kind: str, slug: str) -> dict | None:
        meta = db.cms_get(kind, slug)
        if meta is None:
            return None
        usages = ()
        if kind == "chart":
            usages = tuple(self._usage(db, row) for row in db.cms_chart_usages(slug))
        return {
            "meta": meta,
            "draft": self._doc(db, kind, slug, meta["draft_revision_id"]),
            "published": self._doc(db, kind, slug, meta["published_revision_id"]),
            "history": tuple(db.cms_history(kind, slug)),
            "events": tuple(db.cms_events(kind, slug)),
            "usages": usages,
        }

    def _usage(self, db: Db, row: dict) -> dict:
        doc = self._doc(db, "page", row["slug"],
                        (db.cms_get("page", row["slug"]) or {}).get("draft_revision_id"))
        return {"kind": "page", "slug": row["slug"],
                "title": getattr(doc, "title", None) or row["slug"],
                "published": bool(row["published"])}

    def _require_publishable(self, db: Db, kind: str, slug: str, body_json: str) -> None:
        """Raise CmsRefused unless this exact draft may become public now.

        Runs inside the storage publish transaction on the same connection. For a page the
        card slots go through the shared rule; chart blocks must reference a PUBLISHED chart
        (that chart enforced its own data eligibility when it was published, and the public
        read revalidates it again). A chart runs the full data/reference preparation.
        """
        doc = documents.parse_body(kind, body_json)
        if kind == "page":
            if not isinstance(doc, documents.PageDocument):
                raise CmsRefused(f"page/{slug}: corpo não é uma página")
            problem = self._page_problem(db, doc)
        else:
            if not isinstance(doc, documents.ChartDocument):
                raise CmsRefused(f"chart/{slug}: corpo não é um gráfico")
            problem = cms_reads.chart_problem(db, doc, self.lang)
        if problem:
            raise CmsRefused(f"{kind}/{slug}: {problem}; nada foi publicado")

    def _page_problem(self, db: Db, doc: documents.PageDocument) -> str | None:
        pairs = [(block.series_id, block.derived_key) for block in doc.blocks
                 if isinstance(block, documents.CardBlock)]
        facts, _raw = reads.slot_facts(db, pairs, self.lang)
        problems = page_problems(facts, lang=self.lang)
        if problems:
            return "; ".join(f"cartão {position + 1}: {reason}"
                             for position, reason in problems)
        for block in doc.blocks:
            if not isinstance(block, documents.ChartBlock):
                continue
            meta = db.cms_get("chart", block.chart_slug)
            if meta is None or meta["published_revision_id"] is None:
                return f"o gráfico {block.chart_slug} não está publicado"
            row = db.cms_revision("chart", block.chart_slug, meta["published_revision_id"])
            if row is None:
                return f"o gráfico {block.chart_slug} não tem revisão publicada"
            try:
                documents.require_canonical_body("chart", row["body_json"])
            except (documents.CmsDocumentError, ValueError):
                return f"o gráfico {block.chart_slug} tem um corpo inválido"
        return None
