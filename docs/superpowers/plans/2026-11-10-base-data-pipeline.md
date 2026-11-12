# Base Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Prumo's DuckDB collectors with an auditable ingestion pipeline (raw → validated → served) in SQLite, with independent 100%-match sampling verification, and put the public site in maintenance mode meanwhile.

**Architecture:** A new top-level Python package `ingest/` (separate from the old `app/`) owns everything: one data-access module (`ingest/db.py`) is the only code that touches SQL; sources are plug-ins (`fetch` → raw payload files, `parse` → `Observation`s); a pipeline runs one dataset at a time inside one transaction; a verifier re-checks a random sample through an independent channel and gates "served". The old UI/AI code is deleted (recoverable by git tag) and `app/` becomes a maintenance page.

**Tech Stack:** Python 3.12, stdlib `sqlite3` (STRICT tables, WAL), Pydantic v2, PyYAML, requests, pytest. DuckDB is not used by `ingest/`.

**Spec:** `docs/superpowers/specs/2026-11-10-base-data-pipeline-design.md` (read it first; this plan implements it).

## Owner amendment: dated-data continuity

The owner authorizes keeping existing BM/E-REDES data usable with honest original fetch dates when refresh channels fail. Maximize automatic updates and provide precise, executable manual refresh procedures. Do not fabricate April E-REDES rows: reconciliation found integration code but no persisted records. Rebuild its previously attempted native national-production integration without aggregation or unit conversion. Technical verification, legacy origin, staleness, and legal eligibility remain separate; failed fresh runs are never relabelled verified. This amendment supersedes the registry-only Task16 exclusion and global disabling of otherwise valid approved-source legacy continuity.

## Global Constraints

- Runs on f0nix; container `prumo`, Tailscale `100.118.19.6:8088`; public `cae.joao.date` and `joao.date/dados` show "Em manutenção" until project 4.
- Data dir `/data` in the container = `stacks/web/appdata/prumo`; SQLite file `/data/prumo.sqlite3`; raw payloads under `/data/raw/<source>/<sha256[:2]>/<sha256>`.
- All SQL lives in `ingest/db.py` and `ingest/migrations/*.sql` (portable SQL, versioned `NNNN_name.sql`); no other module imports `sqlite3`.
- Nothing invented: no interpolation, gap-filling, unit conversion or rounding. Store the publisher's value string exactly (`value_text`) plus `value REAL`.
- Two dates per value: `period` (reference, ISO: `YYYY`, `YYYY-Sn`, `YYYY-Qn`, `YYYY-MM`) and `fetched_at` / `released_at` (nullable).
- A failed fetch/parse/verify never overwrites or hides previously verified data; verified data is served, everything else is not.
- Verification: random sample, independent channel, **100% required match**; any mismatch → dataset `failed-verification`, not served, whole dataset re-fetched and re-verified with a fresh sample.
- No Telegram or other push alerts. No backups. No Claude/Anthropic code or env vars anywhere. AI features are off.
- Each source's licence name, URL and attribution text recorded in the registry; a source restricting redistribution is reported to the owner and not served.
- Compose conventions: new service = its own `compose/<service>.yml`; deploy via `bash -lic "dc-web-up <service>"`; mount `${DOCKER_DIR}/resolv.conf:/etc/resolv.conf:ro`; never raw `docker compose`/`docker run`.
- Revision history starts at the first ingestion date (recorded); gap-month revisions are unrecoverable and documented as such.
- Commit trailers on every commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_013yKteVjdtPthwSSih1oeWB`.

## Review Focus

1. A source answers HTTP 200 with an HTML error page, an empty body or a truncated JSON → recorded as a failed fetch; no rows written; previously verified data still served. (Task 6)
2. Re-fetching an identical payload (same sha256) → idempotent: no new vintage, no duplicate rows. (Task 6)
3. A fetch that dies halfway through pagination → nothing from that run is committed (one transaction per dataset). (Task 6)
4. Period/unit oddities (INE "Setembro de 2025", half-years, missing unit, non-numeric value like `:` or `..`) → normalized to the ISO period or quarantined with a reason; never served. (Tasks 3, 5)
5. The verifier shares code with the collector's parser (so it can't disagree with it) or a sample item mismatches → verification must not pass. (Task 7)

---

### Task 1: Tag the legacy UI, delete it, serve "Em manutenção"

**Files:**
- Delete: `app/routes/`, `app/services/`, `app/constants/`, `app/analytics.py`, `app/database.py`, `templates/`, `prompts/`, `stats_lib/`, `tests/routes/`, `tests/services/`, `tests/db/`, `tests/browser/`, `scripts/ai/`, `warm_cache.py`, `test_all_indicators.py`
- Modify: `app/main.py`, `Dockerfile`, `requirements.txt`, `CLAUDE.md`, `AGENTS.md`, delete `SETUP_NOTES.md`
- Create: `app/maintenance.py`, `tests/test_maintenance.py`
- Keep: `static/` (the apex `/static` route serves it), `collectors/` and `scripts/` until replaced by later tasks

**Interfaces:**
- Produces: `app.main.app` (FastAPI) answering `GET /healthz` → 200 `{"status":"ok"}` and every other `GET` path → 200 HTML containing `Em manutenção` (also under the `/dados` prefix, which Traefik strips).

- [ ] **Step 1:** `git tag legacy-ui-final` on current `main` (recoverable reference; do not push tags unless asked).
- [ ] **Step 2: Write failing test** `tests/test_maintenance.py`: `test_root_is_maintenance` (`GET /` → 200, `"Em manutenção" in text`), `test_deep_path_is_maintenance` (`GET /painel/xyz` → 200, same text), `test_healthz` (`GET /healthz` → 200 json `status == "ok"`), `test_no_claude_references` (walk the repo excluding `.git`, `venv`, `docs`, `tests`: no file contains `claude-max-proxy`, `ANTHROPIC`, `anthropic`).
- [ ] **Step 3: Run** `pytest tests/test_maintenance.py -v` → FAIL.
- [ ] **Step 4:** Delete the listed paths; rewrite `app/main.py` to create `app` with `/healthz` and a catch-all route returning `app.maintenance.PAGE` (static HTML string, `lang="pt-PT"`, uses `/static` favicon/CSS already present, no JS, no external requests). Remove `duckdb`, `pandas`, `pyarrow`, `Pillow`, `pytest-asyncio` from `requirements.txt` only if nothing left imports them (check `collectors/` first; leave them until Task 17 if still used).
- [ ] **Step 5:** Rewrite `CLAUDE.md`/`AGENTS.md` deploy sections: aliases are `dc-web-*` (not `dc-jarbas`), host is f0nix, remove token env var rows and `cae-dashboard` mentions; delete `SETUP_NOTES.md`.
- [ ] **Step 6: Run** `pytest tests/test_maintenance.py -v` → PASS; `grep -rIl -i "anthropic\|claude-max" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=docs` → empty.
- [ ] **Step 7:** On f0nix: `git pull` in `stacks/web/images/prumo`, `bash -lic "dc-web-up prumo"`; verify `curl -s https://cae.joao.date/ | grep "Em manutenção"` and `curl -s -o /dev/null -w "%{http_code}" https://joao.date/dados/` → 200.
- [ ] **Step 8: Commit** (`prumo: legacy UI removed, maintenance page`).

---

### Task 2: SQLite schema and data-access module

**Files:**
- Create: `ingest/__init__.py`, `ingest/db.py`, `ingest/migrations/0001_init.sql`, `tests/ingest/__init__.py`, `tests/ingest/test_db.py`, `tests/ingest/conftest.py`

**Interfaces:**
- Produces: `ingest.db.open_db(path: str | Path) -> Db` (WAL, `foreign_keys=ON`, runs pending migrations, records them in `schema_migration`); class `Db` with context-managed `transaction()`; all later tasks add methods to `Db`.
- Tables (STRICT, all with CHECK/UNIQUE/FK): `source(id, name UNIQUE, licence, licence_url, attribution, redistribution_ok INTEGER CHECK IN (0,1))`; `series(id TEXT PK, source_id FK, indicator_key, role CHECK IN ('primary','cross_check'), theme CHECK IN ('economy','demography','energy'), geography, frequency CHECK IN ('A','S','Q','M','D'), unit NOT NULL, multiplier, seasonal_adjustment, base_year, native_code, url, active)`; `raw_fetch(id, source_id, url, params_json, fetched_at, http_status, sha256, path, bytes, ok INTEGER)`; `dataset_run(id, source_id, started_at, finished_at, state CHECK IN ('running','fetched','failed-fetch','failed-validation','pending-verification','verified','failed-verification'))`; `observation(id, series_id FK, period, value_text, value REAL NOT NULL, status_flag, kind CHECK IN ('fetched','legacy-unverified'), dataset_run_id FK, raw_fetch_id FK NULL only when kind='legacy-unverified', fetched_at, released_at, UNIQUE(series_id, period, raw_fetch_id))`; `quarantine(id, dataset_run_id, series_id, raw_period, raw_value, reason, created_at)`; `event(id, ts, dataset_run_id, kind CHECK IN ('fetch_failure','format_change','revision','cross_check_gap','verification_failure','refetch'), detail_json)`; `verification(id, dataset_run_id, seed, sample_size, passed INTEGER, created_at)`; `verification_item(id, verification_id, series_id, period, expected_text, observed_text, evidence_url, match INTEGER)`; view `served_observation` = latest `observation` per (series, period) from a `dataset_run` in state `verified` (legacy rows only until superseded, and only when `legacy_served` setting is 1, default 0).
- Constraints that must be enforced by the DB: `period` GLOB patterns per frequency; `unit` non-empty; `value` NOT NULL; unique raw per observation; `observation.kind='fetched'` requires `raw_fetch_id`.

- [ ] **Step 1: Write failing tests** in `tests/ingest/test_db.py` (use `tmp_path`): `test_open_applies_migrations_once`; `test_rejects_null_value`; `test_rejects_empty_unit`; `test_rejects_bad_period_format` (`"Setembro de 2025"`); `test_fetched_observation_requires_raw_fetch`; `test_duplicate_series_period_raw_rejected`; `test_served_view_excludes_unverified_runs` (insert observation in a `pending-verification` run → view empty; flip run to `verified` → 1 row); `test_served_view_returns_latest_vintage_only`.
- [ ] **Step 2: Run** `pytest tests/ingest/test_db.py -v` → FAIL.
- [ ] **Step 3: Implement** `open_db`, `Db.transaction`, `schema_migration` runner (applies `NNNN_*.sql` in order inside a transaction), and `0001_init.sql` per the table list above.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** (`ingest: sqlite schema + data-access module`).

---

### Task 3: Models and indicator registry

**Files:**
- Create: `ingest/models.py`, `ingest/registry.py`, `registry/core.yaml` (empty skeleton, filled in Task 8), `tests/ingest/test_models.py`, `tests/ingest/test_registry.py`

**Interfaces:**
- Produces: Pydantic models `Observation(series_id: str, period: str, value_text: str, value: float, status_flag: str | None, released_at: datetime | None)` and `SeriesSpec` (mirrors `series` + source info); `ingest.models.normalize_period(raw: str, frequency: str) -> str` (raises `ValueError`); `ingest.registry.load_registry(path: Path) -> list[SeriesSpec]`; `ingest.registry.sync_registry(db: Db, specs: list[SeriesSpec]) -> None` (upsert source+series).

- [ ] **Step 1: Write failing tests:** `test_normalize_period` table-driven: `("Setembro de 2025","M")→"2025-09"`, `("2025","A")→"2025"`, `("2025Q3","Q")→"2025-Q3"`, `("3º Trimestre de 2025","Q")→"2025-Q3"`, `("2025-S1","S")→"2025-S1"`, `("2025M09","M")→"2025-09"`; `test_normalize_period_rejects_garbage` (`"n/d"`, `""`, `"2025-13"`); `test_observation_rejects_non_numeric` (`":"`, `".."`, `""`); `test_registry_exactly_one_primary_per_indicator_key`; `test_registry_requires_licence_fields`; `test_sync_registry_idempotent`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (Portuguese month/quarter names in a lookup; registry validator raises on 0 or >1 primary per `indicator_key`). **Step 4: Run** → PASS. **Step 5: Commit.**

---

### Task 4: Raw store

**Files:** Create `ingest/rawstore.py`, `tests/ingest/test_rawstore.py`

**Interfaces:**
- Produces: `RawStore(root: Path)` with `save(source: str, body: bytes) -> tuple[str, Path]` (returns `sha256`, path; idempotent; writes via temp file + atomic rename; gzip not applied to keep bytes verbatim) and `load(path: Path) -> bytes`.

- [ ] **Step 1: Failing tests:** `test_save_returns_sha256_and_path`; `test_save_is_idempotent` (second save doesn't rewrite, same path); `test_load_roundtrip_is_byte_identical`; `test_partial_write_never_visible` (monkeypatch rename to raise → no final file exists).
- [ ] **Step 2–4:** run (FAIL) → implement → run (PASS). **Step 5: Commit.**

---

### Task 5: Validators and quarantine

**Files:** Create `ingest/validate.py`, `tests/ingest/test_validate.py`

**Interfaces:**
- Consumes: `Observation`, `SeriesSpec`.
- Produces: `validate(spec: SeriesSpec, rows: Iterable[RawRow]) -> tuple[list[Observation], list[Rejection]]` where `RawRow(period_raw: str, value_raw: str, unit_raw: str | None, flag_raw: str | None)` and `Rejection(period_raw, value_raw, reason)`. Rules: period normalizes for `spec.frequency`; value numeric (accepts comma decimal, exact string preserved); unit (if provided) equals `spec.unit` else reject; duplicate periods within a payload rejected (both); reasons are fixed strings: `bad_period`, `non_numeric`, `unit_mismatch`, `duplicate_period`.

- [ ] **Step 1: Failing tests:** one per reason; `test_comma_decimal_preserves_text` (`"1 234,5"` → `value_text == "1 234,5"`, `value == 1234.5`); `test_no_rounding` (`"0.30000000000000004"` stays); `test_dash_and_colon_are_non_numeric`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5: Commit.**

---

### Task 6: Pipeline core (one dataset, one transaction)

**Files:** Create `ingest/pipeline.py`, `ingest/sources/__init__.py` (protocol), `tests/ingest/test_pipeline.py`, `tests/ingest/fakes.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces: `Source` protocol in `ingest/sources/__init__.py`: `name: str`; `fetch(specs: list[SeriesSpec], http) -> list[RawResponse]` (`RawResponse(url, params, status, body: bytes)`); `parse(specs: list[SeriesSpec], responses: list[RawResponse]) -> dict[str, list[RawRow]]` (keyed by `series_id`; `RawRow` from Task 5; `run_dataset` passes each list to `validate`). `pipeline.run_dataset(db: Db, store: RawStore, source: Source, specs: list[SeriesSpec], http, now: Callable[[], datetime]) -> DatasetRunResult(state, run_id, n_written, n_quarantined)`. Behaviour: opens `dataset_run` (`running`); saves every response to the raw store and `raw_fetch`; a non-2xx status, empty body or parse error → state `failed-fetch`/`failed-validation`, `event(fetch_failure|format_change)`, **no observations written**; otherwise one transaction writes observations + quarantine, state `pending-verification`. An observation whose `(series, period)` exists with a different value from an earlier verified run emits `event(revision)` and is stored as a new vintage; identical sha256 to the previous successful fetch → no new rows (state `verified` unchanged, event none).

- [ ] **Step 1: Failing tests** with a `FakeSource` and a `FakeHttp`: `test_happy_path_pending_verification`; `test_html_200_body_is_failed_fetch_and_serves_previous` (RF1); `test_empty_body_is_failed_fetch`; `test_truncated_json_is_failed_validation`; `test_identical_payload_is_idempotent` (RF2); `test_revision_creates_new_vintage_and_event`; `test_midway_failure_commits_nothing` (FakeHttp raises on page 2 → zero observation rows, run state `failed-fetch`) (RF3); `test_bad_rows_are_quarantined_not_written` (RF4).
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5: Commit.**

---

### Task 7: Verification framework (independent sampling, 100% rule)

**Files:** Create `ingest/verify.py`, `ingest/verifiers/__init__.py`, `tests/ingest/test_verify.py`

**Interfaces:**
- Produces: `Verifier` protocol: `source_name: str`; `check(items: list[SampleItem], http) -> list[ItemResult]` where `SampleItem(series_id, period, expected_text, spec)` and `ItemResult(observed_text: str | None, evidence_url: str)`. `verify.draw_sample(db, run_id, seed: int, size: int) -> list[SampleItem]` (stratified by series, then by recency: at least the latest period of every series is included, rest random); `verify.verify_run(db, run_id, verifier, http, seed: int | None = None, size: int = 50) -> bool`; `verify.run_with_refetch(db, store, source, verifier, specs, http, max_attempts: int = 3) -> DatasetRunResult` — on any mismatch (or `observed_text is None`) marks the run `failed-verification`, writes `verification` + `verification_item` rows (seed, evidence) and `event(verification_failure)`, then re-runs the dataset with a **new** seed; after `max_attempts` leaves it unserved and returns `failed-verification`. Passing runs are set `verified`. A verifier whose module imports the source's parse module is rejected at registration (`register_verifier` raises `ValueError`).

- [ ] **Step 1: Failing tests:** `test_all_match_marks_verified`; `test_single_mismatch_marks_failed_and_not_served` (RF5); `test_none_observed_counts_as_mismatch`; `test_sample_always_includes_latest_period_of_each_series`; `test_sample_is_reproducible_from_seed`; `test_refetch_uses_new_seed_each_attempt`; `test_gives_up_after_max_attempts_and_stays_unserved`; `test_verifier_importing_parser_is_rejected` (RF5); `test_verification_items_store_evidence_url`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5: Commit.**

---

### Task 8: Legacy import and registry proposal

**Files:** Create `ingest/legacy_import.py`, `ingest/propose_registry.py`, `tests/ingest/test_legacy_import.py`, `tests/ingest/fixtures/legacy_sample.duckdb` (≤200 rows built by a helper in the test)

**Interfaces:**
- Produces: `legacy_import.import_legacy(db: Db, duckdb_path: Path) -> LegacyImportReport(n_imported, n_quarantined_by_reason: dict[str,int])` — reads the old `indicators` table (the only place `duckdb` is imported; add `duckdb` as a dev/migration-only dependency), writes `observation(kind='legacy-unverified', raw_fetch_id=NULL)` under a synthetic run in state `verified` but not served (`legacy_served` setting stays 0); null value/unit and unparseable periods → `quarantine`. `propose_registry.propose(duckdb_path: Path, out: Path) -> None` writes `registry/core.proposed.yaml`: one entry per (source, indicator, region) in the core themes with proposed `role`, `theme`, `frequency`, `unit`, source licence stubs, and an overlap report `registry/overlaps.md` listing indicators published by more than one source with the proposed primary (Portuguese institution first, else closest to origin).

- [ ] **Step 1: Failing tests:** `test_null_value_and_unit_quarantined`; `test_ine_free_text_period_normalized_or_quarantined`; `test_legacy_rows_not_in_served_view`; `test_import_is_idempotent`; `test_proposal_has_one_primary_per_indicator_key`; `test_proposal_prefers_portuguese_institution`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** run against the real `/data/cae-data.duckdb` on f0nix; save `registry/overlaps.md` and `core.proposed.yaml`; **stop and give the owner both files to review once** (spec §11.3). After review, copy to `registry/core.yaml`. **Step 6: Commit.**

---

### Tasks 9–16: One source each (adapter + independent verifier)

Each task is the same shape and delivers `ingest/sources/<name>.py` (implements `Source`) and `ingest/verifiers/<name>.py` (implements `Verifier` through a **different endpoint or format** than the collector: e.g. API vs the publisher's downloadable file/CSV), plus `tests/ingest/test_source_<name>.py` and recorded fixtures in `tests/ingest/fixtures/<name>/` (real payloads fetched once, committed, ≤200 KB each).

| Task | Source | Collector reuse | Independent channel (builder confirms) | Scope |
|---|---|---|---|---|
| 9 | Eurostat | `collectors/eurostat.py` | bulk TSV download vs JSON-stat API | EU+PT economy, demography, energy |
| 10 | INE | `collectors/ine.py` | INE indicator page export vs API | PT economy, demography |
| 11 | Banco de Portugal | `collectors/bportugal.py` | BPstat bulk/CSV vs API | PT economy |
| 12 | REN (+ DGEG, ERSE if registry marks them core) | `collectors/ren.py`, `dgeg_fuel_api.py` | publisher CSV/portal vs API | PT energy |
| 13 | World Bank | `collectors/worldbank.py` | bulk CSV vs API v2 | world basics |
| 14 | FRED | `collectors/fred.py` | `fredgraph.csv` vs API | US/world reference series in registry |
| 15 | OECD | `collectors/oecd.py` | SDMX-CSV vs SDMX-JSON | registry-listed series |
| 16 | E-REDES/dadosgov | only if the registry marks series core | portal export vs API | registry-listed |

**Per-task steps (identical):**
- [ ] **Step 1: Failing tests:** `test_parse_fixture_yields_expected_rows` (assert exact `period`, `value_text`, `unit`, `status_flag` for ≥5 named observations copied from the fixture and cross-checked by hand against the publisher site); `test_parse_html_error_page_raises`; `test_parse_preserves_status_flags` (provisional/estimated mapped to the flag vocabulary in `ingest/flags.py`: `provisional`, `estimated`, `revised`, `break`, `normal`); `test_verifier_does_not_import_parser`; `test_verifier_detects_tampered_value` (change one `expected_text` → mismatch).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** the adapter (reuse the request logic from the existing collector but return `RawResponse`s; no DB access, no writes) and the verifier. If **no independent channel exists** for the source, do not invent one: record it in `registry/unverifiable.md`, mark the source `not served`, and report to the owner (spec §6b).
- [ ] **Step 4: Run** → PASS. **Step 5: Live smoke** on f0nix: `python -m ingest run <name> --dry-run` then `python -m ingest run <name>`; expect state `verified` and non-empty `served_observation` for that source. **Step 6: Commit.**

---

### Task 17: CLI, status report, replay

**Files:** Create `ingest/cli.py`, `ingest/__main__.py`, `ingest/status.py`, `tests/ingest/test_cli.py`; Delete: old `collectors/` and `scripts/` collectors/orchestrators superseded by Tasks 9–16 (`collect_scheduled.py`, `audit_nightly.py`, `backfill_*.py`, `scripts/collectors/`, `scripts/maintenance/`, `warm_cache.py`), then drop `duckdb`, `pandas`, `pyarrow`, `Pillow` from `requirements.txt` (keep `duckdb` only for `legacy_import` via a separate `requirements-migration.txt`).

**Interfaces:**
- Produces: `python -m ingest` subcommands: `run <source|all> [--dry-run]`, `status [--json]`, `verify <run_id>`, `import-legacy <duckdb>`, `replay --from 2026-04`. `status.report(db) -> StatusReport` per series/source: last verified date, state of latest run, stale-by (days since expected release per frequency), open events counts, last verification pass/fail.

- [ ] **Step 1: Failing tests:** `test_status_flags_stale_series`; `test_status_json_schema`; `test_run_all_continues_after_one_source_fails`; `test_replay_never_marks_legacy_verified`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** run the catch-up on f0nix: `python -m ingest replay --from 2026-04`, then `python -m ingest status`; confirm every core series is `verified` or listed as failed with its reason. Rate limits: throttle per source (config in registry, default 1 req/s). **Step 6: Commit.**

---

### Task 18: Scheduler service and deployment

**Files:** Create `ingest/scheduler.py`, `tests/ingest/test_scheduler.py`, `compose/prumo-ingest.yml` (in the infra repo, `stacks/web/compose/`); Modify: infra `stacks/web/compose.yml` (include), `Dockerfile` (`COPY ingest/ registry/`), `entrypoint.sh` (drop the dead `crond` block and DuckDB/site.json seeding).

**Interfaces:**
- Produces: `scheduler.due(spec_group, last_success: datetime | None, now: datetime) -> bool` using the registry's per-source release calendar (`schedule: {cron-like or interval}`); `python -m ingest.scheduler` loops every 15 min, runs due sources via `run_with_refetch`, logs one JSON line per run to stdout; service `prumo-ingest` shares `/data` with `prumo`, `restart: unless-stopped`, `mem_limit: 512m`, resolv.conf mount, `SOPS` secrets for source API keys only.

- [ ] **Step 1: Failing tests:** `test_due_when_never_run`; `test_not_due_before_release_window`; `test_failed_run_retries_with_backoff` (1h, 4h, 12h cap); `test_scheduler_survives_source_exception`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** deploy: `bash -lic "dc-web-up prumo-ingest"` on f0nix; after 24 h `docker logs prumo-ingest` shows runs and `python -m ingest status` shows nothing stale. **Step 6: Commit** (images repo and infra repo separately).

---

### Task 19: Docs and final audit pack

**Files:** Modify `README.md`, `CLAUDE.md`, `DOCS_MAP.md`; Create `docs/data/methodology.md`, `docs/data/sources.md`

- [ ] **Step 1:** `docs/data/methodology.md`: three stages, vintage rules, flag vocabulary, verification procedure (sampling, independent channel, 100% rule, re-fetch), the gap-month revision caveat, ingestion-date recording. `docs/data/sources.md`: generated from the registry by `python -m ingest docs` (add `ingest/docgen.py` with test `test_sources_md_lists_every_source_with_licence`): per source licence, attribution, primary indicators, independent verification channel.
- [ ] **Step 2:** Run the full suite `pytest tests -v` → PASS; `python -m ingest status` → no stale or failed-verification series for the core set (or each listed with a reason in `registry/unverifiable.md`).
- [ ] **Step 3: Commit.** Hand the owner the status report and the sources doc; project 1 is done when the owner accepts them, then brainstorm project 2 (backoffice).
