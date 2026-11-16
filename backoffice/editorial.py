"""Editorial composition: the backoffice's only write path.

No SQL in this module. Every read and every mutation is a `Db` method; what lives here is the
catalogue side of the eligibility rule (a title in both languages), the publish refusal that
names every failing slot, and the origin check for forms.

The write handle is opened per request and never cached: `open_db_for_write` refuses a schema
this code does not know, so a stale deployment cannot write into a newer table shape.
"""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app import reads as app_reads
from ingest.db import (
    Db,
    EditorialRefused,
    OperationalError,
    SchemaMismatchError,
    open_db_for_write,
    read_db_readonly,
)
from ingest.editorial_rules import MAX_SLOTS, SlotFacts, page_problems, slot_problem
from presentation import (
    LANGUAGES,
    MissingText,
    derived_title,
    family_of,
    page_text,
    series_title,
    unit_text,
)
from presentation.catalog import pt as pt_catalog

LANGS = LANGUAGES


class EditorialUnavailable(RuntimeError):
    """The writable mount is not configured, missing, or at a schema this code does not know."""


class EditorialBusy(RuntimeError):
    """The writer (the scheduler) holds the lock; nothing was written, try again."""


@dataclass(frozen=True)
class Slot:
    series_id: str
    title: str
    source: str
    geography: str
    frequency: str
    unit: str
    derived_key: str | None
    derived_label: str | None
    problem: str | None


@dataclass(frozen=True)
class Candidate:
    series_id: str
    title: str
    source: str
    theme: str
    frequency: str
    derived: tuple[tuple[str, str], ...]  # (key, rendered title) for this series' own keys


@dataclass(frozen=True)
class Diff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    moved: tuple[str, ...]


@dataclass(frozen=True)
class PageView:
    slug: str
    title: str
    version: int
    published_at: str | None
    draft_saved_at: str | None
    draft: tuple[Slot, ...]
    published: tuple[Slot, ...]
    diff: Diff
    titles: dict[str, str]  # series id -> rendered title, for the diff and the audit list


def same_origin(request) -> bool:
    """CSRF without a session: the browser cannot forge `Origin`, and there is no cookie to
    ride. A cross-site form is refused by `Sec-Fetch-Site` too, belt and braces.

    The comparison is exact, against the request's own `Host`: same scheme, same host, same
    port. Matching only the hostname would accept any port on an allowed host, and the
    healthcheck's `localhost`/`127.0.0.1` are in the allowed list, so a page served from any
    other local port could drive the editor. `Host` itself is allow-listed by
    TrustedHostMiddleware before this runs (400 otherwise)."""
    site = (request.headers.get("sec-fetch-site") or "").strip().lower()
    if site and site not in ("same-origin", "none"):
        return False
    origin = request.headers.get("origin")
    if not origin:
        return False
    parts = urlsplit(origin)
    if parts.scheme not in ("http", "https") or parts.username or parts.password:
        return False
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        return False
    host = (request.headers.get("host") or "").strip()
    if not host:
        return False
    return parts.netloc.lower() == host.lower() and parts.scheme == request.url.scheme


def _lcs(a: list[str], b: list[str]) -> list[str]:
    """Longest common subsequence (these lists hold at most twelve ids)."""
    table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i, x in enumerate(a, 1):
        for j, y in enumerate(b, 1):
            table[i][j] = table[i - 1][j - 1] + 1 if x == y else max(table[i - 1][j],
                                                                    table[i][j - 1])
    out: list[str] = []
    i, j = len(a), len(b)
    while i and j:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1])
            i -= 1
            j -= 1
        elif table[i - 1][j] >= table[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return list(reversed(out))


class Editorial:
    """Reads from the same read-only handle every other backoffice page uses; writes through
    `open_db_for_write` only. `editorial_db_path` None means the writable mount is absent."""

    def __init__(self, db_path: Path, editorial_db_path: Path | None, *, lang: str = "pt"):
        self.db_path = db_path
        self.editorial_db_path = editorial_db_path
        self.lang = lang

    # --- reads ------------------------------------------------------------------------------

    def available(self) -> bool:
        return self.editorial_db_path is not None

    def pages(self) -> list[dict]:
        composed = self._read(lambda db: db.editorial_pages())
        by_slug = {p["slug"]: p for p in composed}
        out = []
        for slug, text in self._code_pages():
            row = by_slug.get(slug, {})
            out.append({
                "slug": slug,
                "title": text["title"],
                "version": row.get("version", 0),
                "draft_count": row.get("draft_count", 0),
                "published_count": row.get("published_count", 0),
                "published_at": row.get("published_at"),
                "composed": bool(row.get("published_count")),
            })
        return out

    def page(self, slug: str) -> PageView:
        text = page_text(self.lang, slug)  # unknown slug -> MissingText -> 404 at the route
        return self._read(lambda db: self._page(db, slug, text))

    def candidates(self, slug: str, *, query: str = "", source: str = "", theme: str = "",
                   limit: int = 40, offset: int = 0) -> list[Candidate]:
        return self._read(
            lambda db: self._candidates(db, slug, query, source, theme, limit, offset))

    def draft_cards(self, slug: str):
        """The cards the home would draw for the draft, built by the home's own card builder."""
        def build(db: Db):
            slots = db.editorial_slots(slug, "draft")
            rows = db.series_facts([s["series_id"] for s in slots])
            wanted = []
            for slot in slots:
                row = rows.get(slot["series_id"])
                if row is None:
                    continue
                try:
                    label = series_title(self.lang, family_of(row["indicator_key"]),
                                         row["geography"])
                except MissingText:
                    continue
                row["family"] = family_of(row["indicator_key"])
                wanted.append((slot["series_id"], label, slot["derived_key"]))
            return app_reads.cards_for(db, wanted, self.lang, rows_by_id=rows)

        return self._read(build)

    # --- writes -----------------------------------------------------------------------------

    def add(self, slug: str, series_id: str, derived_key: str | None,
            expected_version: int, note: str) -> int:
        self._require_page(slug)
        draft = self._read(lambda db: db.editorial_slots(slug, "draft"))
        if len(draft) >= MAX_SLOTS:
            raise EditorialRefused(
                f"the page already holds {MAX_SLOTS} cards, which is the grid limit")
        facts, _raw = self._read(lambda db: self._facts(
            db, [(r["series_id"], r["derived_key"]) for r in draft] + [(series_id, derived_key)]))
        # Only the new slot must be clean: an existing draft may hold a slot whose series was
        # deactivated meanwhile, and blocking every edit until it is removed helps nobody.
        problems = [p for p in page_problems(facts) if p[0] == len(facts) - 1]
        if problems:
            raise EditorialRefused(self._explain(problems, facts))
        return self._write(lambda db: db.editorial_add(
            slug, series_id, derived_key, expected_version, note))

    def move(self, slug: str, series_id: str, to_position: int,
             expected_version: int, note: str) -> int:
        self._require_page(slug)
        return self._write(lambda db: db.editorial_move(
            slug, series_id, to_position, expected_version, note))

    def remove(self, slug: str, series_id: str, expected_version: int, note: str) -> int:
        self._require_page(slug)
        return self._write(lambda db: db.editorial_remove(
            slug, series_id, expected_version, note))

    def discard(self, slug: str, expected_version: int, note: str) -> int:
        self._require_page(slug)
        return self._write(lambda db: db.editorial_discard(slug, expected_version, note))

    def publish(self, slug: str, expected_version: int, note: str) -> int:
        """Refuse before writing when any draft slot would not render.

        The rule needs catalogue text, which is why it runs here and not in the store. A
        licence revoked after this check is still dropped at render time, so the refusal is
        a courtesy to the operator, not the safety net.
        """
        self._require_page(slug)
        if not note or not note.strip():
            raise EditorialRefused("a publish needs a reason")
        draft = self._read(lambda db: db.editorial_slots(slug, "draft"))
        if not draft:
            raise EditorialRefused("the draft is empty; use reset to return to the code list")
        facts, _raw = self._read(lambda db: self._facts(
            db, [(r["series_id"], r["derived_key"]) for r in draft]))
        problems = page_problems(facts)
        if problems:
            raise EditorialRefused(self._explain(problems, facts))
        return self._write(lambda db: db.editorial_publish(slug, expected_version, note))

    def reset(self, slug: str, expected_version: int, note: str) -> int:
        self._require_page(slug)
        return self._write(lambda db: db.editorial_reset(slug, expected_version, note))

    # --- internals --------------------------------------------------------------------------

    def _read(self, fn):
        return read_db_readonly(self.db_path, fn)

    def _write(self, fn):
        if self.editorial_db_path is None:
            raise EditorialUnavailable(
                "the writable mount is not configured (PRUMO_EDITORIAL_DB)")
        try:
            db = open_db_for_write(self.editorial_db_path)
        except (FileNotFoundError, SchemaMismatchError) as e:
            raise EditorialUnavailable(str(e)) from e
        except OperationalError as e:
            raise self._classify(e) from e
        try:
            return fn(db)
        except OperationalError as e:
            raise self._classify(e) from e
        finally:
            db.close()

    @staticmethod
    def _classify(e: OperationalError) -> RuntimeError:
        """A busy database is a conflict the operator retries, not a broken deployment."""
        text = str(e).lower()
        if "locked" in text or "busy" in text:
            return EditorialBusy(
                "the worker is writing to the database; nothing was changed, try again in a "
                "few seconds")
        return EditorialUnavailable(f"database error: {e}")

    def _require_page(self, slug: str) -> None:
        page_text(self.lang, slug)

    def _code_pages(self) -> list[tuple[str, dict]]:
        return list(pt_catalog.PAGES.items())

    def _page(self, db: Db, slug: str, text: dict) -> PageView:
        row = db.editorial_page(slug) or {}
        draft_rows = db.editorial_slots(slug, "draft")
        published_rows = db.editorial_slots(slug, "published")
        draft = self._slots(db, draft_rows)
        published = self._slots(db, published_rows)
        titles = {s.series_id: s.title for s in (*published, *draft)}
        return PageView(
            slug=slug,
            title=text["title"],
            version=row.get("version", 0),
            published_at=row.get("published_at"),
            draft_saved_at=row.get("draft_saved_at"),
            draft=draft,
            published=published,
            diff=self._diff(draft, published),
            titles=titles,
        )

    def _slots(self, db: Db, rows: list[dict]) -> tuple[Slot, ...]:
        facts, raw = self._facts(db, [(r["series_id"], r["derived_key"]) for r in rows])
        problems = dict(page_problems(facts))
        out = []
        for position, (row, fact) in enumerate(zip(rows, facts)):
            info = raw.get(row["series_id"], {})
            out.append(Slot(
                series_id=row["series_id"],
                title=(fact.titles.get(self.lang) if fact else None) or row["series_id"],
                source=info.get("source") or "?",
                geography=info.get("geography") or "?",
                frequency=info.get("frequency") or "?",
                unit=self._unit_label(info.get("unit")),
                derived_key=row["derived_key"],
                derived_label=(fact.derived_titles.get(self.lang)
                               if fact and fact.derived_titles.get(self.lang) else None),
                problem=problems.get(position),
            ))
        return tuple(out)

    def _unit_label(self, unit: str | None) -> str:
        if not unit:
            return "?"
        try:
            return unit_text(self.lang, unit)
        except MissingText:
            return "?"

    def _facts(self, db: Db, pairs: list[tuple[str, str | None]]):
        """(facts per slot, raw rows by series id). One lookup per id, never a join."""
        ids = [sid for sid, _ in pairs]
        raw = db.series_facts(ids)
        derived = db.derived_facts([key for _, key in pairs if key])
        out: list[SlotFacts | None] = []
        for series_id, key in pairs:
            row = raw.get(series_id)
            if row is None:
                out.append(None)
                continue
            title_pt, title_en = self._titles(row)
            d = derived.get(key) if key else None
            out.append(SlotFacts(
                series_id=series_id,
                active=bool(row["active"]),
                role=row["role"],
                redistribution_ok=bool(row["redistribution_ok"]),
                has_served=bool(row["has_served"]),
                titles={"pt": title_pt, "en": title_en},
                derived_key=key,
                derived_active=bool(d and d["active"]),
                derived_base_series_id=d["base_series_id"] if d else None,
                derived_titles={lang: self._derived_title(lang, key, d) for lang in LANGS},
            ))
        return out, raw

    def _titles(self, row: dict) -> tuple[str | None, str | None]:
        family = family_of(row["indicator_key"])
        out: list[str | None] = []
        for lang in LANGS:
            try:
                out.append(series_title(lang, family, row["geography"]))
            except MissingText:
                out.append(None)
        return out[0], out[1]

    def _derived_title(self, lang: str, key: str | None, d: dict | None) -> str | None:
        """A companion must be nameable in this language: title and unit both resolve."""
        if not key or d is None:
            return None
        try:
            unit_text(lang, d["unit"])
            return derived_title(lang, key)
        except MissingText:
            return None

    def _candidates(self, db: Db, slug: str, query: str, source: str, theme: str,
                    limit: int, offset: int) -> list[Candidate]:
        ids = db.all_series_ids()
        raw = db.series_facts(ids)
        companions: dict[str, list[tuple[str, str]]] = {}
        for d in db.derived_list():
            if not d["active"] or d["base_series_id"] not in raw:
                continue
            try:
                companions.setdefault(d["base_series_id"], []).append(
                    (d["key"], derived_title(self.lang, d["key"])))
            except MissingText:
                continue
        needle = query.strip().lower()
        draft = db.editorial_slots(slug, "draft")
        taken_ids = {s["series_id"] for s in draft}
        taken_titles: set[str] = set()
        for series_id in taken_ids:
            row = raw.get(series_id)
            if row is not None:
                title, _ = self._titles(row)
                if title:
                    taken_titles.add(title)
        out: list[Candidate] = []
        skipped = 0
        for series_id in ids:
            row = raw.get(series_id)
            if row is None:
                continue
            title_pt, title_en = self._titles(row)
            facts = SlotFacts(
                series_id=series_id, active=bool(row["active"]), role=row["role"],
                redistribution_ok=bool(row["redistribution_ok"]),
                has_served=bool(row["has_served"]),
                titles={"pt": title_pt, "en": title_en})
            if series_id in taken_ids:
                continue
            if slot_problem(facts, titles_taken=taken_titles) is not None:
                continue
            if source and row["source"] != source:
                continue
            if theme and row["theme"] != theme:
                continue
            if needle and needle not in (title_pt or "").lower() and needle not in series_id.lower():
                continue
            if skipped < offset:
                skipped += 1
                continue
            out.append(Candidate(
                series_id=series_id, title=title_pt or series_id, source=row["source"],
                theme=row["theme"], frequency=row["frequency"],
                derived=tuple(sorted(companions.get(series_id, [])))))
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _diff(draft: tuple[Slot, ...], published: tuple[Slot, ...]) -> Diff:
        """What the publish changes: added, removed, and the cards whose ORDER changed.

        `moved` is the complement of the longest common subsequence of the two common orders,
        so moving the last card to the front reports one card moved, not eleven. Comparing raw
        indices reported every shifted slot, which is noise on the one screen that asks the
        operator to confirm.
        """
        draft_ids = [s.series_id for s in draft]
        published_ids = [s.series_id for s in published]
        added = tuple(sid for sid in draft_ids if sid not in published_ids)
        removed = tuple(sid for sid in published_ids if sid not in draft_ids)
        common_draft = [sid for sid in draft_ids if sid in published_ids]
        common_pub = [sid for sid in published_ids if sid in draft_ids]
        keep = set(_lcs(common_draft, common_pub))
        moved = tuple(sid for sid in common_draft if sid not in keep)
        return Diff(added=added, removed=removed, moved=moved)

    def _explain(self, problems: list[tuple[int, str]], facts: list[SlotFacts | None]) -> str:
        parts = []
        for position, reason in problems:
            fact = facts[position] if position < len(facts) else None
            who = fact.series_id if fact is not None else f"slot {position}"
            parts.append(f"{who}: {reason}")
        return "; ".join(parts)
