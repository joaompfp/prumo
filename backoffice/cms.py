"""CMS service: the backoffice's contract for authored pages and reusable charts.

No SQL here. Reads go through `read_db_readonly` (one snapshot per call); writes open the
restricted `open_db_for_write` handle and never migrate it. The service layer owns three
things the storage deliberately does not:

* shape: an untrusted body is parsed into `ingest.cms`'s typed document before any write, and
  a parse failure is `CmsRefused`, never a 500;
* eligibility at publication: the draft body is checked inside the storage publish
  transaction (`Db.cms_publish(check=...)`), so the decision and the pointer swap see the same
  snapshot. Saving an unfinished, currently ineligible draft stays allowed;
* reader choices: eligible primary series with raw tokens, rendered text and the served period
  range they actually cover, so the editor labels fields without reimplementing the catalogue
  and without loading each series' history.

`preview` returns exactly `(template_name, view)` where the name is `cms_page.html` or
`cms_chart.html`; the backoffice renders it with `preview=True` and its own `admin_base`.
"""
import logging
from pathlib import Path

from app import cms_reads, reads
from app.formatting import format_period
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
    page_text,
    source_title,
    unit_text,
)
from presentation.catalog import pt

__all__ = ["Cms", "CmsBusy", "CmsConflict", "CmsNotFound", "CmsRefused", "CmsUnavailable"]

log = logging.getLogger("backoffice")

HOME_SLUG = cms_reads.HOME_SLUG


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

    def home(self) -> dict | None:
        """The reserved homepage's head summary (title, version, published), or None."""
        def build(db: Db):
            meta = db.cms_get("page", HOME_SLUG)
            if meta is None:
                return None
            doc = self._doc(db, "page", HOME_SLUG, meta["draft_revision_id"])
            return {
                **meta,
                "kind": "page",
                "title": getattr(doc, "title", None) or HOME_SLUG,
                "published": meta["published_revision_id"] is not None,
            }
        return self._read(build)

    def home_prepared(self) -> bool:
        """True once the private home draft exists; the legacy editor must stop writing."""
        return self._read(lambda db: db.cms_get("page", HOME_SLUG) is not None)

    def legacy_home_locked(self, slug: str) -> bool:
        """Gate for the retired fixed-home editor: only the reserved slug is locked."""
        return slug == HOME_SLUG and self.home_prepared()

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
        """Eligible primary series: raw tokens, reader text and the period range they cover."""
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
                    unit_text_value = base_unit_text(self.lang, row["unit"])
                    frequency_text_value = self._text(frequency_text, row["frequency"])
                    geography_text_value = self._text(geography_name, row["geography"])
                    source_title_value = self._text(source_title, row["source"])
                    title = fact.titles.get(self.lang) or ""
                    first, latest = db.public_served_bounds(series_id)
                    coverage = self._coverage_text(row["frequency"], first, latest)
                    out.append({
                        "id": series_id,
                        "title": title,
                        "unit": row["unit"],
                        "unit_text": unit_text_value,
                        "frequency": row["frequency"],
                        "frequency_text": frequency_text_value,
                        "geography": row["geography"],
                        "geography_text": geography_text_value,
                        "source": row["source"],
                        "source_title": source_title_value,
                        "theme": row["theme"],
                        "first_period": first,
                        "latest_period": latest,
                        "coverage_text": coverage,
                        "option_label": self._option_label(
                            title, coverage, row["unit"],
                            frequency_text_value or row["frequency"],
                            geography_text_value or row["geography"],
                            source_title_value or row["source"]),
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

    def prepare_home(self, *, actor: str, note: str) -> dict:
        """Create the private `inicio` draft from the effective legacy/default home.

        This is the only way the reserved page appears, and it never overwrites: an existing
        document raises `CmsConflict` before anything is written. The imported body carries
        registry references only, so source metadata, observation values and the legacy
        editorial slots stay untouched. Publication remains a separate explicit step.
        """
        def write(db: Db):
            existing = db.cms_get("page", HOME_SLUG)
            if existing is not None:
                raise CmsConflict("page", HOME_SLUG, 0, existing["version"])
            body = self._canonical("page", self._home_body(db))
            return db.cms_create("page", HOME_SLUG, body, actor=actor, note=note)

        return self._write(write)

    def create(self, kind: str, slug: str, body_dict, *, actor: str, note: str) -> dict:
        kind = self._kind(kind)
        slug = self._slug(slug)
        if kind == "page" and slug == HOME_SLUG:
            raise CmsRefused(
                "page/inicio é reservado à página inicial; use /cms/home para a preparar")
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

    def duplicate(self, kind: str, slug: str, new_slug: str, *, version: int, actor: str,
                  note: str) -> dict:
        kind = self._kind(kind)
        slug = self._slug(slug)
        new_slug = self._slug(new_slug, "new_slug")
        if kind == "page" and new_slug == HOME_SLUG:
            raise CmsRefused(
                "page/inicio é reservado à página inicial; use /cms/home para a preparar")
        return self._write(lambda db: db.cms_duplicate(kind, slug, new_slug,
                                                       expected_version=version, actor=actor,
                                                       note=note))

    # --- internals -----------------------------------------------------------------------

    def _home_body(self, db: Db) -> dict:
        """The private draft body imported from whatever `/` renders today.

        A published editorial composition wins over the code list, exactly as `reads.home`
        does. Each slot goes through the same `prepare_card` rule the public CMS renderer
        uses, so the draft contains only cards that can actually render. A calculated
        companion that is no longer eligible degrades to its base card instead of silently
        removing the card the reader currently sees.
        """
        composed = reads.page_composition(db, HOME_SLUG, self.lang)
        slots = ([(row["id"], key) for row, key in composed] if composed is not None
                 else [(item["series"], item["derived"]) for item in pt.CURATED_HOME])
        facts, raw = reads.slot_facts(db, slots, self.lang)
        taken: set[str] = set()
        blocks: list[dict] = []
        kept: list[str] = []
        for (series_id, derived_key), fact in zip(slots, facts):
            if fact is None:
                continue  # not part of this database's effective home
            card, reason = reads.prepare_card(db, series_id, derived_key, lang=self.lang,
                                              titles_taken=taken)
            used_key = derived_key
            if card is None and derived_key is not None:
                card, reason = reads.prepare_card(db, series_id, None, lang=self.lang,
                                                  titles_taken=taken)
                used_key = None
            if card is None:
                log.warning("cms home prepare: card dropped series=%s reason=%s",
                            series_id, reason)
                continue
            taken.add(card.title)
            blocks.append({"type": "card", "series_id": series_id, "derived_key": used_key})
            kept.append(series_id)
        text = page_text(self.lang, HOME_SLUG)
        all_pt = all(raw[series_id]["geography"] in reads.PT_GEOS for series_id in kept)
        return {
            "title": text["title"],
            "introduction": text["note_all_pt"] if all_pt else text["note_mixed"],
            "section": "general",
            "blocks": blocks,
        }

    @staticmethod
    def _coverage_text(frequency: str, first: str | None, latest: str | None) -> str:
        """The served period range in reader words, empty when the series has no value."""
        if not first or not latest:
            return ""
        first_text = format_period(first, frequency)
        latest_text = format_period(latest, frequency)
        return first_text if first_text == latest_text else f"{first_text} a {latest_text}"

    @staticmethod
    def _option_label(title: str, coverage: str, unit: str, frequency: str,
                      geography: str, source: str) -> str:
        """One option's label: the exact raw unit token, reader text for the rest.

        The operator picks the stored registry object, so the unit stays the raw code the
        series carries (the editor also gets `unit_text` separately); coverage comes from the
        served periods, never from an assumed range.
        """
        parts = [title]
        if coverage:
            parts.append(coverage)
        parts.extend((unit, frequency, geography, source))
        return " | ".join(part for part in parts if part)

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
                body = documents.require_canonical_body("chart", row["body_json"])
                chart_doc = documents.parse_body("chart", body)
            except (documents.CmsDocumentError, ValueError):
                return f"o gráfico {block.chart_slug} tem um corpo inválido"
            if not isinstance(chart_doc, documents.ChartDocument):
                return f"o gráfico {block.chart_slug} tem um corpo inválido"
            # The page's eligibility depends on the chart's CURRENT data, not on the fact that
            # the chart was publishable when its own pointer moved. Same transaction, same
            # snapshot: a licence revoked or a run withdrawn since then refuses the page too.
            problem = cms_reads.chart_problem(db, chart_doc, self.lang)
            if problem:
                return f"o gráfico {block.chart_slug} já não pode ser publicado: {problem}"
        return None
