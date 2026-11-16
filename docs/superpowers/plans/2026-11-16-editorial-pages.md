# Editorial pages (backoffice v1.1, part 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the backoffice choose which series a public page shows, and in what order, without touching data, licences or reader text: a composition that the backoffice edits, previews and publishes, and that the home page renders in place of the hard-coded twelve.

**Architecture:** One additive migration (0018) adds `editorial_page`, `editorial_slot` and `editorial_event`. `ingest/db.py` gains `open_db_for_write()` (never migrates, refuses a schema that differs from this code) and the editorial reads and mutations. `ingest/editorial_rules.py` holds the eligibility rule as a pure function called by both the publish path and the render path. `backoffice/editorial.py` orchestrates and the backoffice app adds its first POST routes. `app/reads.page_composition()` reads the published composition and the home falls back to `pt.CURATED_HOME` when there is none.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, SQLite via `ingest.db`, pytest + `httpx` TestClient. No JavaScript, no build step, no new service.

**Spec:** `docs/superpowers/specs/2026-11-16-editorial-pages-design.md`.

## Global Constraints

- SQL only in `ingest/db.py`. `backoffice/editorial.py` and `app/reads.py` import no `sqlite3` and hold no SQL string. A test asserts it.
- The public app keeps GET/HEAD only and never writes; the backoffice is the only component allowed to write, and only through `open_db_for_write` on the `editorial_*` tables. No mutation touches `observation`, `quarantine`, `dataset_run`, `derived_*`, `series`, `source` or `event`.
- Reader text only from `presentation/catalog/pt.py` and `en.py`. A composition stores series ids, a derived key, a position and a state; never a title, a label, a unit or a note.
- Numbers still come from `value_text` at request time. A composed card and a catalogue card are built by the same card builder, so a composition cannot invent or round anything.
- No JavaScript, no external asset. Every POST is a form. CSP unchanged. No `style=` attributes.
- Python is `.venv-ci/bin/python`. Tests must not touch the network. The gate is `ruff check app/ ingest/` (the scope CI's command) plus the full suite.
- No merge to `main`, no deploy, no worker restart without the owner's explicit instruction. This plan ends at a reviewed branch.
- The migration number is 0018 only if `ingest/migrations/` still ends at 0017 when the work starts. Check it first; never trust this plan for it.
- Commit messages describe the change truthfully. No co-author trailer, no session trailer.
- Protected `AGENTS.md` and `CLAUDE.md` are not touched.

## Review Focus

1. A writable path in the backoffice that can reach anything other than the three `editorial_*` tables, or a flipped existing mount -> defect.
2. Reader-facing text or a number stored in the composition -> defect.
3. A published slot whose series lost eligibility 503-ing the page or leaving a hole instead of dropping one card with a log line -> defect.
4. A stale form writing over a newer composition -> defect.
5. A POST accepted without a same-origin `Origin` -> defect.
6. A mutation that writes an event outside its transaction, or two events for one click -> defect.
7. The home changing when the composition is empty -> defect; this is the deploy's whole safety argument.
8. A composed card labelled with the short hand-written label instead of `series_title` -> defect (it would collide with catalogue pages).
9. A composition page showing the Portugal-only section note over non-Portuguese cards -> defect.

---

## Part 1 - Schema and the writable opener

### Task 1: Migration 0018

**Files:**
- Create: `ingest/migrations/0018_editorial_composition.sql`
- Test: `tests/ingest/test_migration_0018.py`

**Interfaces:**
- Produces three tables exactly as the spec's section 4: `editorial_page(slug PK, version, draft_saved_at, published_version, published_at)`, `editorial_slot(slug, state, position, series_id, derived_key, PK (slug,state,series_id), UNIQUE (slug,state,position))`, `editorial_event(id, ts, slug, action, version, note, detail_json)`, all `STRICT`, plus `editorial_slot_state`.
- Consumes: nothing. No existing table changes.

- [ ] **Step 1: Confirm the number.** `ls ingest/migrations/ | sort | tail -3` must end at `0017_derived_caveats.sql`. If it does not, stop and renumber.
- [ ] **Step 2: Write the failing test.** In `tests/ingest/test_migration_0018.py`:
  - `test_tables_exist_and_are_strict` reads `sqlite_master` after `open_db(tmp_path / "p.sqlite3")` and asserts the three tables exist and their `sql` contains `STRICT`.
  - `test_position_cap_is_schema_enforced` inserts one page row and twelve slots at positions `0..11`, then asserts a thirteenth at position `12` raises `sqlite3.IntegrityError`; asserts a position of `-1` raises too.
  - `test_state_and_action_vocabularies_are_closed` asserts an `editorial_slot` with `state='live'` raises and an `editorial_event` with `action='published '` raises.
  - `test_series_foreign_key_and_page_cascade` asserts a slot with an unknown `series_id` raises, and `DELETE FROM editorial_page` removes its slots.
  - `test_migration_is_additive` compares the table set of a fresh 0018 database with the table set of the pre-0018 schema from `tests/ingest/fixtures/` (or a database opened before applying it, if the fixtures carry one) and asserts the difference is exactly the three new tables plus `sqlite_sequence` if present.
  - `test_integrity_and_foreign_keys_clean`: `PRAGMA integrity_check` is `ok` and `PRAGMA foreign_key_check` yields nothing.
- [ ] **Step 3: Run it.** `.venv-ci/bin/python -m pytest tests/ingest/test_migration_0018.py -q` -> FAIL (missing migration).
- [ ] **Step 4: Write the migration.** Copy the DDL from the spec's section 4 verbatim. Comment at the top: additive, no rebuild, why `derived_key` has no FK, why the audit has its own table.
- [ ] **Step 5: Run it again.** Same command -> PASS. Then `tests/ingest` whole directory -> PASS.
- [ ] **Step 6: Commit.** `feat(db): migration 0018, editorial page composition`

### Task 2: `open_db_for_write`

**Files:**
- Modify: `ingest/db.py`
- Test: `tests/ingest/test_db_for_write.py`

**Interfaces:**
- Produces `class SchemaMismatchError(RuntimeError)` carrying `applied: set[str]`, `expected: set[str]` and a message naming both differences.
- Produces `open_db_for_write(path: str | Path) -> Db`: WAL, `foreign_keys=ON`, `timeout=BUSY_TIMEOUT_S`, `isolation_level=None`, **no `_migrate`**, and a refusal when `_applied_migrations(conn)` differs from `_expected_migrations()` in either direction. Refuses a missing file instead of creating an empty database.
- Consumes the existing `Db` class, `_expected_migrations()`, `BUSY_TIMEOUT_S`.

- [ ] **Step 1: Write the failing tests.** In `tests/ingest/test_db_for_write.py`:
  - `test_opens_an_exactly_current_database` migrates a temp database with `open_db`, closes it, then opens it with `open_db_for_write` and reads `PRAGMA journal_mode` = `wal` and `PRAGMA foreign_keys` = `1`.
  - `test_refuses_an_older_schema` deletes the `0018` row from `schema_migration` and asserts `SchemaMismatchError` names `0018` as expected-only.
  - `test_refuses_a_newer_schema` inserts a fake `0019_x` row and asserts the error names it as applied-only.
  - `test_never_migrates` deletes the 0018 row, opens with `open_db_for_write` inside `pytest.raises`, and asserts `editorial_page` still does not exist afterwards.
  - `test_refuses_a_missing_file` asserts `SchemaMismatchError` (or `FileNotFoundError`) and that no file was created at that path.
  - `test_foreign_keys_are_enforced` inserts a child row with an unknown parent through the returned handle and asserts `sqlite3.IntegrityError`.
- [ ] **Step 2: Run** -> FAIL.
- [ ] **Step 3: Implement.** Model it on `open_db` at `ingest/db.py:1425` and `_open_refusal` at `:1450`; share the pragma block instead of copying it, so the two openers cannot drift. Do not reuse `_migrate`.
- [ ] **Step 4: Run** the new file, then `tests/ingest` -> PASS.
- [ ] **Step 5: Commit.** `feat(db): writable opener that never migrates and refuses a foreign schema`

---

## Part 2 - The composition store

### Task 3: Eligibility as one pure rule

**Files:**
- Create: `ingest/editorial_rules.py`
- Test: `tests/ingest/test_editorial_rules.py`

**Interfaces:**
- Produces `MAX_SLOTS = 12`.
- Produces `slot_problem(series: dict, *, source: dict, has_served: bool, title_pt: str | None, title_en: str | None, titles_taken: set[str], derived: dict | None, base_series_id: str) -> str | None`. Returns `None` when the slot may stand, else a short machine key from a closed set: `unknown_series`, `inactive`, `cross_check`, `withheld`, `no_served_value`, `missing_title_pt`, `missing_title_en`, `duplicate_title`, `unknown_derived`, `inactive_derived`, `derived_base_mismatch`, `derived_missing_title`.
- Produces `page_problems(slots: list[dict], **lookups) -> list[tuple[int, str]]` returning `(position, reason)` for every failing slot, so a publish refusal can name them all. No I/O, no logging, no formatting.

- [ ] **Step 1: Write the failing tests**, one per returned key, with a table-driven test that every key in the module's closed set has at least one test. Cover: a valid primary series returns `None`; `active=0`; `role='cross_check'`; `redistribution_ok=0`; no served `kind='fetched'` row; missing PT title; missing EN title; two slots whose titles collide (the second fails, the first stands); a derived key that does not exist, is inactive, or is based on another series.
- [ ] **Step 2: Run** -> FAIL.
- [ ] **Step 3: Implement** the module. It takes plain dicts and booleans; it must not import `sqlite3`, `db`, `logging` or any catalogue module. Comment that the publish path and the render path both call it, which is why it has no I/O.
- [ ] **Step 4: Run** -> PASS.
- [ ] **Step 5: Commit.** `feat(editorial): one eligibility rule for publish and render`

### Task 4: Composition reads and mutations on `Db`

**Files:**
- Modify: `ingest/db.py`
- Test: `tests/ingest/test_db_editorial.py`

**Interfaces:**
- Reads: `editorial_pages() -> list[dict]` (`slug`, `version`, `published_version`, `published_at`, `draft_saved_at`, `draft_count`, `published_count`); `editorial_page(slug) -> dict | None`; `editorial_slots(slug, state) -> list[dict]` ordered by position (`position`, `series_id`, `derived_key`); `editorial_events(slug, limit=20) -> list[dict]` newest first.
- Mutations, all taking `expected_version: int` and `note: str`: `editorial_add(slug, series_id, derived_key, ...)`, `editorial_move(slug, series_id, to_position, ...)`, `editorial_remove(slug, series_id, ...)`, `editorial_discard(slug, ...)`, `editorial_publish(slug, ...)`, `editorial_reset(slug, ...)`. Each returns the new version.
- Typed errors: `EditorialConflict` (stale version, or the write lock is held), `EditorialRefused` (cap reached, unknown series, unknown derived key).
- Internal: one `_editorial_write(slug, expected_version, action, note, mutate)` that does `BEGIN IMMEDIATE`, ensures the page row, compares the version, calls the mutator, rewrites the whole draft list contiguously, increments `version`, inserts exactly one `editorial_event`, and commits; rollback on any exception so no event survives a failed mutation.

- [ ] **Step 1: Write the failing tests** against the `db` fixture from `tests/ingest/conftest.py`, adding series/source/run rows with the existing helpers in `tests/ingest/test_db_public_reads.py` (`_verified`, `_verification`) and real source and family names, not `fake`/`foo`:
  - add/move/remove each bump `version` by one and leave positions `0..n-1` with no gaps, including moving the first slot to the end and removing from the middle;
  - adding a thirteenth slot raises `EditorialRefused` and writes nothing;
  - adding the same series twice raises `EditorialRefused` and writes nothing;
  - a stale `expected_version` raises `EditorialConflict` and writes nothing (assert slot count and version unchanged);
  - each successful mutation leaves exactly one `editorial_event` with the matching `action`, and a mutation forced to fail after the page row update (monkeypatch the mutator to raise) leaves zero events and an unchanged version;
  - `editorial_publish` copies draft to published, sets `published_version` and `published_at`, leaves the draft intact, and stores the full slot list in `detail_json`;
  - editing the draft after a publish does not change the published list until the next publish;
  - `editorial_discard` copies published back over draft;
  - `editorial_reset` deletes both states and the page row, and the page then reads as absent;
  - `editorial_pages()` counts draft and published slots without a scan of `served_observation`.
- [ ] **Step 2: Run** -> FAIL.
- [ ] **Step 3: Implement** the reads and mutations in `ingest/db.py`, next to the other public reads, with the SQL inline in the methods and no view.
- [ ] **Step 4: Run** `tests/ingest` -> PASS.
- [ ] **Step 5: Commit.** `feat(db): editorial composition reads, mutations and audit`

---

## Part 3 - The backoffice editor

### Task 5: Orchestration, CSRF and routes

**Files:**
- Create: `backoffice/editorial.py`
- Modify: `backoffice/app.py`, `backoffice/deps.py`, `backoffice/templates/base.html`
- Test: `tests/backoffice/test_editorial_routes.py`, `tests/backoffice/test_editorial_csrf.py`

**Interfaces:**
- Produces in `backoffice/editorial.py`: `EditorialService(db_path, registry_path, catalogue)` with `pages()`, `page(slug)`, `candidates(query, source, theme, page, page_size)`, `add`, `move`, `remove`, `discard`, `publish_preview`, `publish`, `reset`. No SQL. Eligibility comes from `ingest.editorial_rules`; the candidate list is filtered through the same `slot_problem`, so the editor cannot offer something publishing would refuse.
- Produces `same_origin(request, allowed_hosts) -> bool` in `backoffice/editorial.py`: true only when `Origin` is present, its `scheme://host[:port]` host is in `allowed_hosts`, and `Sec-Fetch-Site` is absent or `same-origin`/`none`.
- Produces routes on the backoffice app: `GET /editorial`, `GET /editorial/{slug}`, `POST /editorial/{slug}/add`, `/move`, `/remove`, `/discard`, `/publish`, `/reset`. Each POST reads `version` from the form, calls the service, and renders 409 (`EditorialConflict`), 422 (`EditorialRefused`) or 403 (origin) with the current state.
- `app_from_env()` passes `PRUMO_EDITORIAL_DB` into the service; when it is unset the editorial routes render a 503 page saying the writable mount is not configured, and the rest of the backoffice works unchanged.

- [ ] **Step 1: Write the failing CSRF tests:** POST without `Origin` -> 403 and no row change; POST with `Origin: https://evil.example` -> 403; POST with `Sec-Fetch-Site: cross-site` -> 403; POST with the correct origin against the configured host -> 200/303 and one event.
- [ ] **Step 2: Write the failing route tests:** `GET /editorial` lists `inicio` with "sem composição, em vigor a lista do código" when empty; `GET /editorial/inicio` shows the twelve candidates and the empty draft; add renders the row and one event; move reorders; remove drops; publish preview shows the diff and the rendered cards; publish without a reason is refused; stale `version` -> 409 and no write; unknown slug -> 404; `PRUMO_EDITORIAL_DB` unset -> 503 page while `/healthz` stays 200.
- [ ] **Step 3: Run** -> FAIL.
- [ ] **Step 4: Implement** the service, the origin check and the routes. Keep `PAGE_METHODS` for the existing pages; the new POSTs are explicit. Update `tests/backoffice/test_boundaries.py` deliberately: it must now assert that the *public* app has no POST route and that the backoffice's only POST routes are the six editorial ones, named exactly.
- [ ] **Step 5: Run** `tests/backoffice` -> PASS.
- [ ] **Step 6: Commit.** `feat(backoffice): editorial editor service, origin check and routes`

### Task 6: Templates, compose mount and the contract test

**Files:**
- Create: `backoffice/templates/editorial_list.html`, `backoffice/templates/editorial_page.html`
- Modify: `backoffice/templates/base.html` (nav entry), `deploy/prumo-backoffice.yml`, `tests/test_docker_contract.py`, `docs/data/operations.md`
- Test: `tests/backoffice/test_editorial_templates.py`

**Interfaces:**
- The page template holds two panels (Publicado, Rascunho), each row with up/down/remove forms carrying `version` and `series_id`; a candidate panel with a search box, source and theme filters and an "acrescentar" form per row; a publish block with the diff, the rendered cards and a required `note`; a separately marked reset with a required `note`.
- `deploy/prumo-backoffice.yml` gains `PRUMO_EDITORIAL_DB: /data-w/prumo.sqlite3` and exactly one writable mount of the same host directory at `/data-w`. Nothing else changes: `read_only: true`, `/data:ro`, uid 1000, Tailscale bind and no Traefik label stay.

- [ ] **Step 1: Write the failing contract test update.** In `tests/test_docker_contract.py`, assert the backoffice has exactly one `:rw` volume, that its host side equals the read-only one, that it targets `/data-w`, that `PRUMO_EDITORIAL_DB` points inside `/data-w`, and that `read_only` is still true. The existing assertions that there is no writable mount must be replaced, not deleted silently: the new test states the narrower invariant.
- [ ] **Step 2: Write the failing template tests:** rendered draft rows carry a `version` hidden input and one form per action; the publish form has a `note` field and a `required` attribute; the diff names added, removed and moved series by title; the card preview uses the same card markup as the home; no `<script>`, no `style=`, no inline handler anywhere in the three templates.
- [ ] **Step 3: Run** -> FAIL.
- [ ] **Step 4: Implement** the templates and the compose change. Reuse the home card partial for the preview if the card markup can be shared without moving business rules into a template; otherwise copy the markup and add a test that both render the same value, unit and provenance lines for the same fixture.
- [ ] **Step 5: Run** the template and contract tests -> PASS.
- [ ] **Step 6: Document** in `docs/data/operations.md`: the second mount, why it exists, how to install the include on f0nix, that the backoffice now has six POST routes, and that the editor refuses a schema mismatch rather than migrating.
- [ ] **Step 7: Commit.** `feat(backoffice): editorial UI, writable mount and docker contract`

---

## Part 4 - The public read path and the proof

### Task 7: Catalogue pages, `page_composition` and the home fallback

**Files:**
- Modify: `presentation/catalog/pt.py`, `presentation/catalog/en.py`, `presentation/__init__.py`, `app/reads.py`, `app/templates/home.html`
- Test: `tests/presentation/test_catalog_pages.py`, `tests/app/test_home_composition.py`

**Interfaces:**
- Produces `PAGES: dict[str, dict]` in both catalogues: `{"inicio": {"section_title": str, "note_all_pt": str, "note_mixed": str}}`, with `note_all_pt` equal to today's string ("Portugal. Valores publicados tal como a fonte os publica.") and `note_mixed` neutral ("Cada número indica a instituição e a data da recolha."). `en.py` carries the same keys with empty strings so a missing key raises `MissingText` rather than `AttributeError`.
- Produces `page_text(lang, slug) -> dict` in `presentation/__init__.py`, raising `MissingText` for an unknown slug.
- Produces `app/reads.page_composition(db, slug, lang) -> list[Card]` and `HomePage.note` plus `HomePage.composed: bool`. `home()` builds cards from the composition when it has published slots, else from `pt.CURATED_HOME` exactly as today.
- A slot that fails the eligibility rule at render is dropped and logged once per request: `log.warning("editorial slot dropped slug=%s series=%s reason=%s", ...)`. Titles are computed per slot, and a duplicate title keeps the first position and drops the later one with the same log line.

- [ ] **Step 1: Capture the no-op golden before touching the render path.** On the production copy at `/home/joao/.hermes/cache/scratch/prumo-ui/`, run the current build (`git stash` or a worktree at `main`) and save the rendered home HTML to `tests/app/golden/home_before_editorial.html`, with a README line saying which commit and database produced it. This file is the D4 proof; it is committed before the code that must match it.
- [ ] **Step 2: Write the failing tests:**
  - `test_empty_composition_renders_the_code_list` asserts the home card ids and order equal `CURATED_HOME`'s and `HomePage.composed is False`;
  - `test_empty_composition_home_is_byte_identical` renders `/` against a fixture database with 0018 applied and zero editorial rows, and asserts equality with the golden (normalise nothing; if the comparison needs a date, fix the fixture instead);
  - `test_publishing_the_code_list_reproduces_the_cards` publishes the twelve series ids with their derived keys, and asserts the ids, order, values and derived-change lines match the fallback, while the labels equal `series_title(...)`;
  - `test_ineligible_slot_is_dropped_and_the_rest_render` deactivates one published series' source licence (or deactivates the series) after publishing, asserts 200, the other eleven cards, and one WARNING naming slug, series and reason (caplog);
  - `test_duplicate_title_keeps_the_first_slot` publishes a seasonal and an unadjusted variant of one family and asserts one card plus a warning;
  - `test_section_note_switches_when_a_card_is_not_portuguese` publishes one Eurozone series and asserts the neutral note; with only PT series asserts the current note;
  - `test_unknown_slug_row_is_inert` inserts a page row for a slug the catalogue lacks and asserts the home is unchanged;
  - `test_missing_page_text_is_a_503` deletes `PAGES["inicio"]` by monkeypatch and asserts 503, not 500.
- [ ] **Step 3: Run** -> FAIL.
- [ ] **Step 4: Implement** the catalogue entries, `page_text`, `page_composition` and the `home()` branch. `page_composition` must call `ingest.editorial_rules.slot_problem`, not re-implement the rule; the reads it needs (`public_catalogue`, `public_latest_values`, derived rows) are already loaded by `home()`, so do not add a per-slot query storm. Measure: the home must stay under 250 ms on the production copy.
- [ ] **Step 5: Run** `tests/app` and `tests/presentation` -> PASS, including the byte-identical test.
- [ ] **Step 6: Commit.** `feat(ui): render a composed home with the code list as fallback`

### Task 8: Proof on a copy of production, suite and independent review

**Files:**
- Modify: `docs/superpowers/handoff/HANDOFF.md`, `docs/data/operations.md`
- Test: none new; this task produces evidence, not code.

- [ ] **Step 1: Take a fresh copy** of the production database (online backup on f0nix, scp to scratch) and record its size, `observation` and `quarantine` counts.
- [ ] **Step 2: Dry-run 0018** with the worker opener on that copy: assert tables created, `integrity_check` ok, zero `foreign_key_check` rows, `observation` and `quarantine` counts identical, `editorial_*` empty. Record the migration time.
- [ ] **Step 3: Measure the home** on that copy before and after: warm latency, and the same for `/series/{id}` and `/fontes`, to prove the new read adds no per-request cost when the composition is empty.
- [ ] **Step 4: Exercise the loop end to end** on the copy through the backoffice TestClient: compose the twelve, publish with a reason, render the home, edit the draft, confirm the home did not change, publish again, reset, confirm the home returns to the golden bytes.
- [ ] **Step 5: Freeze the tree**, then run `.venv-ci/bin/python -m pytest -q` and `ruff check app/ ingest/` (also `backoffice/` if it is clean; do not fix unrelated dirt). Report the run that finished against the final tree, with the pass count and the excluded tests.
- [ ] **Step 6: Independent review** of the diff against the spec and this plan's Review Focus. Fix what it finds, re-run the touched directories, and re-review if the fix is not trivial.
- [ ] **Step 7: Commit and push** `docs(handoff): editorial pages built, reviewed and ready; deploy is owner-gated`. The handoff records: migration 0018 dry run numbers, the byte-identical proof, the measured latencies, the review verdict, the deploy order, the rollback point and the fact that nothing is merged.

### Task 9: Deploy (owner-gated; do not start without an explicit instruction)

**Files:**
- Modify: `docs/superpowers/handoff/HANDOFF.md`, `docs/data/operations.md`

- [ ] **Step 1: Merge and push** `pipeline-rebuild` into `main` in the worktree that holds `main`, fast-forward on f0nix, and record the previous commit.
- [ ] **Step 2: Record the rollback point:** current `prumo:latest`, `prumo-ingest:latest` and `prumo-backoffice:latest` image ids, and the current `main` commit.
- [ ] **Step 3: Copy the database** online, verify integrity, note the path.
- [ ] **Step 4: Install the backoffice include** with the new `:rw` mount on f0nix before the container is recreated, so the mount exists when the new image starts.
- [ ] **Step 5: Rebuild in dependency order:** `dc-web-up prumo-ingest` (applies 0018), then `dc-web-up prumo`, then `dc-web-up prumo-backoffice`. Between the first and second, the old web image answers 503; that is the expected window, not a fault.
- [ ] **Step 6: Verify:** new image ids and `StartedAt` on all three containers; `/healthz`; the home 200 and byte-identical to before (the composition is empty); `/editorial` 200 on `100.118.19.6:8089`; one publish through the real backoffice; the home showing the published twelve; `editorial_event` holding one row for that publish; the worker log free of errors and the worker's restart count unchanged.
- [ ] **Step 7: Record the release** in the handoff: commits, image ids, the 503 window, the checks that held, and the rollback cost (previous commit plus the pre-deploy copy; any composition published after it is lost).

---

## What this plan deliberately does not do

No second public page; no page creation from the UI; no reader text in the database; no colours, images or layout per card; no scheduling; no drag and drop; no login; no operational write actions (`withdraw run`, `verify run`, queue acknowledgement), which get their own spec and their own migration. No two-series chart: that stays curated and named, and is not part of this release.
