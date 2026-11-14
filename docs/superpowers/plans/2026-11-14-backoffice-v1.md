# Backoffice v1 (read-only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Tailscale-only, strictly read-only web backoffice that shows pipeline health, per-series provenance, and a derived review queue, consistent with `python -m ingest status`.

**Architecture:** New package `backoffice/` (FastAPI + Jinja2, server-rendered, no JS build). All data comes through new read functions on `ingest.db.Db` plus the existing `build_status` / `lagging_series`, opened via `ingest.db.read_db_readonly` (can never write or migrate). A separate container `prumo-backoffice` from the same image, bound to the Tailscale address only, with the data volume mounted `:ro`.

**Tech Stack:** Python 3.12, FastAPI, Jinja2 (add to `requirements.txt`), SQLite via existing `ingest.db`, pytest + httpx TestClient (already in `requirements-dev.txt`).

**Spec:** `docs/superpowers/specs/2026-11-14-backoffice-design.md` (v1 = its parts 1-3; the audited write actions and migration 0014 are a separate later plan).

## Global Constraints

- SQL only in `ingest/db.py` (new read functions go there, with tests); the `backoffice/` package contains no SQL and no `sqlite3` import.
- The backoffice never writes the DB: it opens only via `read_db_readonly`; the compose mount is `:ro`; there is no POST/PUT/DELETE route (a test asserts every route is GET/HEAD).
- Numbers are shown exactly as stored (`value_text`, publisher token string); never converted through float; units/labels as in the registry; nothing invented.
- Never deploy by restarting `prumo-ingest`; deploy only the new `prumo-backoffice` service (`bash -lic "dc-web-up prumo-backoffice"`), own file `compose/prumo-backoffice.yml`, no `docker run`.
- No public route: bind `100.118.19.6:8089` only; do not touch the f3nix Traefik rules.
- Pages must render with an empty DB, a never-fetched series, and must refuse (HTTP 503 with a clear message) a missing DB or schema mismatch, like `ingest status`.
- Commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_013yKteVjdtPthwSSih1oeWB`; never touch `AGENTS.md`/`CLAUDE.md`; use `</dev/null` on `git commit` and `command cp -f`. Python is `.venv-ci/bin/python`.

## Review Focus

1. A series with registry entry but zero fetched rows (never fetched) -> series page shows "never fetched", not an error.
2. A series whose served vintage is `legacy-unverified` -> clearly labelled as unverified legacy, never styled like verified data.
3. Withdrawn / failed / pending runs in a series' history -> shown with their state; the "served" marker only on the vintage the `served_observation` view actually serves.
4. HTML injection: publisher strings, evidence URLs and event details are untrusted -> Jinja autoescape on, URLs rendered as text not auto-linked unless `https://`.
5. Very large series (daily/PT15M, tens of thousands of observations) -> list pages paginate, detail page caps observations shown (newest N) with a total count.
6. Schema older/newer than the code -> 503 page, not a traceback.

---

### Task 1: Read layer in `ingest/db.py`

**Files:**
- Modify: `ingest/db.py` (new methods on `Db`)
- Test: `tests/ingest/test_db_backoffice_reads.py`

**Interfaces:**
- Produces (all read-only, plain tuples/dicts, no SQL leaks):
  - `Db.series_observations(series_id: str, limit: int, offset: int = 0) -> tuple[int, list[dict]]` -> (total served rows, rows newest period first) with keys `period, value_text, status_flag, run_id, fetched_at, raw_sha, origin` (`origin` = `fetched` or `legacy`).
  - `Db.series_vintages(series_id: str, period: str) -> list[dict]` -> every stored version of one period across runs: `run_id, run_state, fetched_at, value_text, status_flag, served: bool`.
  - `Db.series_quarantine(series_id: str, limit: int = 200) -> list[dict]` -> `run_id, period, raw_value, reason, created_at`.
  - `Db.series_verification_items(series_id: str, limit: int = 200) -> list[dict]` -> `item_id, verification_id, run_id, period, expected_text, observed_text, evidence_url, match, reason, created_at`.
  - `Db.series_raw_fetches(series_id: str) -> list[dict]` -> distinct raw fetches behind its fetched rows: `sha256, url, fetched_at, http_status, run_id`.
  - `Db.recent_events(since: str | None, kinds: list[str] | None, limit: int) -> list[dict]` -> `id, ts, kind, run_id, detail: dict`.
  - `Db.runs_in_state(state: str, older_than: str | None = None) -> list[dict]`.
- Consumes: existing tables/view (`served_observation`, `observation`, `dataset_run`, `quarantine`, `verification`, `verification_item`, `event`, `raw_fetch`); check actual column names in `ingest/migrations/*.sql` first.

- [ ] **Step 1: Write failing tests** in `tests/ingest/test_db_backoffice_reads.py` building a small DB through the real pipeline fixtures used by `tests/ingest/test_task20_serving.py` (reuse its helpers): `test_series_observations_total_and_newest_first`, `test_series_observations_marks_legacy_origin`, `test_series_vintages_marks_only_served_version`, `test_series_vintages_includes_withdrawn_and_pending_runs`, `test_series_quarantine_and_items_empty_for_unknown_series`, `test_recent_events_filters_by_kind_and_since_and_parses_detail`, `test_runs_in_state_older_than`.
- [ ] **Step 2: Run** `.venv-ci/bin/python -m pytest tests/ingest/test_db_backoffice_reads.py -q` -> FAIL (methods missing).
- [ ] **Step 3: Implement** the methods in `ingest/db.py` next to the existing read helpers; `served` in `series_vintages` is true iff the row's observation id equals the one the `served_observation` view returns for that (series, period).
- [ ] **Step 4: Run** the new tests and `tests/ingest/test_db.py` -> PASS.
- [ ] **Step 5: Commit** `feat(db): read-only queries for the backoffice`.

### Task 2: Review-queue derivation `backoffice/queue.py`

**Files:**
- Create: `backoffice/__init__.py`, `backoffice/queue.py`
- Test: `tests/backoffice/test_queue.py` (create `tests/backoffice/__init__.py` if the repo's tests use packages; check `tests/ingest`)

**Interfaces:**
- Consumes: `ingest.status.StatusReport` (from `build_status`), `ingest.data_lag.Lagging`, `Db.recent_events`, `Db.runs_in_state`.
- Produces: `QueueItem` (frozen dataclass: `kind: str, severity: Literal["high","medium","info"], ref: str, summary: str, detail: dict`) and `derive_queue(report: StatusReport, lagging: list[Lagging], events: list[dict], stuck_pending: list[dict]) -> list[QueueItem]` sorted by severity then kind then ref. Kinds and rules (thresholds as module constants): `verification_failed` / `verification_escalated` events in the last 7 d -> high; `stuck_pending` (pending-verification > 24 h) -> high; `stale_series` per source with stale > 0 -> medium; `lagging_series` per series -> medium; `blocked_source` (licence_withheld / not_verifiable) -> info; `revision_burst` (>= 100 revision events in one run) -> info.

- [ ] **Step 1: Write failing tests** `test_empty_inputs_give_empty_queue`, `test_failed_verification_event_is_high`, `test_events_older_than_7_days_ignored` (inject `now`), `test_stuck_pending_is_high`, `test_blocked_sources_are_info_only`, `test_sorting_is_severity_then_kind_then_ref`, `test_detail_strings_are_not_interpreted` (HTML in event detail passes through verbatim as data).
- [ ] **Step 2: Run** -> FAIL.
- [ ] **Step 3: Implement** `derive_queue(..., now: datetime | None = None)` as a pure function; no DB access inside.
- [ ] **Step 4: Run** -> PASS. **Step 5: Commit** `feat(backoffice): derive review queue`.

### Task 3: App skeleton, overview and queue pages

**Files:**
- Create: `backoffice/app.py`, `backoffice/templates/base.html`, `overview.html`, `queue.html`, `error.html`, `backoffice/deps.py` (DB path/registry path from env: `PRUMO_DB_PATH`, `PRUMO_REGISTRY` default `registry/core.yaml`)
- Modify: `requirements.txt` (add `jinja2>=3.1,<4`)
- Test: `tests/backoffice/test_app_overview.py`

**Interfaces:**
- Produces: `backoffice.app.create_app(db_path: Path, registry_path: Path, now: Callable | None = None) -> FastAPI` with routes `GET /healthz`, `GET /` (overview: totals and per-source table mirroring `render_text`), `GET /queue`. Overview data comes from `read_db_readonly(db_path, lambda db: build_status(db, specs))`. Errors from `ReadOnlyOpenError` -> 503 `error.html`.
- Consumes: Task 1 and Task 2 interfaces; `ingest.registry.load_registry`.

- [ ] **Step 1: Failing tests** with a temp migrated DB: `test_overview_shows_totals_matching_build_status`, `test_overview_empty_db_renders`, `test_missing_db_returns_503_with_message`, `test_schema_mismatch_returns_503`, `test_queue_page_lists_items_by_severity`, `test_all_routes_are_get_or_head_only` (iterate `app.routes`), `test_html_in_event_detail_is_escaped`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement** app + templates (plain dense tables, one shared stylesheet inline in `base.html`, dark/light via `prefers-color-scheme`). **Step 4: Run** -> PASS; run `ruff check backoffice tests/backoffice`. **Step 5: Commit** `feat(backoffice): overview and queue pages`.

### Task 4: Series list and series provenance pages

**Files:**
- Create: `backoffice/templates/series_list.html`, `series_detail.html`; modify `backoffice/app.py`
- Test: `tests/backoffice/test_app_series.py`

**Interfaces:**
- Produces: `GET /series?source=&theme=&geography=&frequency=&active=&q=&page=` (page size 100, filters from registry `SeriesSpec` fields + status per series from `build_status`); `GET /series/{series_id}` showing: registry spec (unit, frequency, native_code, source URL, licence/attribution, `redistribution_ok`), status (served/ stale / never fetched / legacy-only), newest 200 observations (Task 1 `series_observations`, with total), raw fetches, quarantine, verification items (with `reason` and match), and for a `?period=` query the vintage table (`series_vintages`). 404 for unknown series id.
- Consumes: Task 1 read functions, `build_status`.

- [ ] **Step 1: Failing tests** `test_list_filters_by_source_and_active`, `test_list_paginates_100`, `test_detail_shows_exact_value_text_not_float` (value token like `0.10` and `1E-6` renders verbatim), `test_detail_never_fetched_series_renders`, `test_detail_labels_legacy_served_rows_unverified`, `test_detail_vintages_marks_served_only_once`, `test_detail_caps_observations_and_shows_total`, `test_unknown_series_404`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement** routes/templates. **Step 4: Run** -> PASS + ruff. **Step 5: Commit** `feat(backoffice): series list and provenance page`.

### Task 5: Verification replay view

**Files:**
- Modify: `backoffice/app.py`; create `backoffice/templates/item.html`
- Test: `tests/backoffice/test_app_replay.py`

**Interfaces:**
- Produces: `GET /verification/item/{item_id}` showing the stored claim and, by calling the existing `ingest.verify.replay_item` against the raw store (`PRUMO_RAW_DIR`), whether re-reading the archived evidence reproduces the claim (match / mismatch / evidence missing or corrupt, with the reason string). The call is read-only (no DB write); check `replay_item`'s real signature in `ingest/verify.py` and the verifier registry used by `ingest/cli.py replay` before wiring, and reuse that wiring rather than duplicating it.
- Consumes: Task 1 `verification_item`, `ingest.verify.replay_item`, `ingest.rawstore.RawStore`.

- [ ] **Step 1: Failing tests** using a fixture-verified World Bank or BPstat run from existing tests: `test_replay_matches_for_genuine_item`, `test_replay_reports_corrupt_evidence`, `test_replay_reports_missing_evidence`, `test_unknown_item_404`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement.** **Step 4: Run** -> PASS + ruff. **Step 5: Commit** `feat(backoffice): replay a verification item from the browser`.

### Task 6: Container, compose, docs

**Files:**
- Create: `deploy/prumo-backoffice.yml` (candidate include, same convention as `deploy/prumo-ingest.yml`: service `prumo-backoffice`, image `prumo-ingest:latest` rebuilt from the same Dockerfile, `command: ["uvicorn","backoffice.app:app", "--factory"...]` or an `app` module-level instance reading env, port `100.118.19.6:8089:8080`, volumes `${DOCKER_DIR}/stacks/web/appdata/prumo:/data:ro` and resolv.conf ro, `mem_limit: 256m`, `no-new-privileges`, healthcheck on `/healthz`, same logging block); modify `Dockerfile` (`COPY backoffice/ ./backoffice/`; `.dockerignore` currently excludes everything by default: allow `backoffice/`); modify `docs/data/operations.md` (section "Backoffice": URL, read-only guarantee, no auth beyond Tailscale, deploy command, what each page shows).
- Test: `tests/test_docker_contract.py` (extend): backoffice compose file has `:ro` data mount, no public port, loopback/Tailscale bind only, image contains `backoffice/`, no write routes (already covered in Task 3).

- [ ] **Step 1: Extend contract tests** (FAIL). **Step 2: Implement** the files. **Step 3:** run full `tests --ignore=tests/ingest` and `tests/ingest -m "not live"` -> PASS; ruff. **Step 4: Commit** `feat(backoffice): container, compose and docs`.
- [ ] **Step 5 (controller, owner-authorized deploy only):** copy `deploy/prumo-backoffice.yml` to `~/docker/stacks/web/compose/`, add it to `compose.yml` includes, `git pull` the image dir on f0nix, `bash -lic "dc-web-up prumo-backoffice"`; verify `curl http://100.118.19.6:8089/healthz`, overview totals equal `docker exec prumo-ingest python -m ingest status` totals, `docker ps` shows `prumo-ingest` uptime unchanged (never restarted).

## Self-review notes

Spec coverage: G1 -> Task 3; G2 -> Task 4; G3 -> Tasks 2-3; G4 -> Task 4 (list + registry fields; read-only); G5 and the audited actions are v1.1 by design (spec section 4.1); G6 -> Task 5. Non-goals respected (no writes, no public route, no registry editing).
