# Task 17 design proposal (superseded)

Historical, unapproved research only. The controller rejected the subprocess-per-locale proposal; task-17a-brief.md, task-17b-brief.md and task-17-controller-review.md define the implemented and reviewed contract.

Read-only design, 2026-11-12. Bases: current code on `pipeline-rebuild` (Task 15/16 state), plan
`docs/superpowers/plans/2026-11-10-base-data-pipeline.md` Task 17, HANDOFF deferred minors,
Rulings Q/S/U/V/AC. No code edited; nothing executed.

## 1. Current contracts the CLI must reuse (verified in code)

- `ingest.pipeline.run_dataset(db, store, source, specs, http, now) -> DatasetRunResult(state, run_id, n_written, n_quarantined)`. Failed-fetch/failed-validation never write observations; identical-payload-after-verified short-circuits to `verified` with no rows (callers must NOT verify it). `dataset_key(source.name, series_ids)`.
- `ingest.verify.run_with_refetch(db, store, source, verifier, specs, http, max_attempts=3, size=50, now)`: refuses `verifiable: false` (SourceNotVerifiable) and unregistered sources (NoVerifierRegistered) BEFORE fetch; `registered is not verifier` identity check. Verifier gets `BlindItem`s only — no expected values ever reach it (guard intact, do not change).
- `ingest.verify.verify_run(db, run_id, verifier, http, seed=None, size=50, *, specs, store, now)` requires state `pending-verification`, writes one `verification` + per-item rows, CAS state transition. Deferred minor: `verify_run` accepts an unregistered verifier — the CLI must register and pass `get_verifier(source_name)`'s instance.
- `ingest.verify.replay_item(db, store, verification_item_id)` re-decides stored items offline.
- `ingest.verifiers.register_verifier(verifier)` / `get_verifier(source_name)` — ONE verifier instance per source per process; a differently-configured second instance for the same source correctly refuses registration. Orchestration must not mutate the private `_REGISTRY`.
- `ingest.db.Db`: existing methods include `begin_run/set_run_state/run_state/previous_run/record_raw_fetch/observations_of_run/add_verification/add_event/transition_run_state/upsert_source_and_series`. **No status-query methods exist yet** — they must be added to `Db` (new SQL only there and in `ingest/migrations/`).
- `ingest.models.SourceSpec.verifiable` (scheduler/CLI must skip false), `SourceSpec.timeout_s` (INE needs 300), `SeriesSpec.active`, `.schedule` ("1d"/"7d"), `.throttle_rps`, `.frequency` (incl. PT15M).
- `ingest.http.Http` protocol: `get(url, params=None, headers=None, timeout=None) -> HttpResult(status, body, url)`; `RequestsHttp(throttle_rps, timeout, retries, backoff)`.
- `ingest.sources.eredes.EredesSource(from_ts: str | None = None, to_ts: str | None = None, ...)` — explicit `[from_ts, to_ts)` UTC day-boundary window for replay; default = last 3 complete UTC days. `EredesVerifier.source_name = "eredes"`.
- `ingest.legacy_import.import_legacy(db, csv_path: Path, registry=None) -> LegacyImportReport` — already CSV (Ruling U), no DuckDB.
- Licence gate: view `served_observation` (migrations 0001/0005/0006) joins `source.redistribution_ok = 1`; legacy rows additionally need `setting legacy_served = '1'` (currently GLOBAL, seeded '0').
- Registry: `eredes` source is `verifiable: true` (metadata licence CC BY 4.0 asserted at parse). DGEG: 17 inactive entries, blocked, no adapter. WorldBank verifier: `WorldBankVerifier(csv_language='en'|'es')`, default 'en'.

## 2. Files

**Create (T17 brief files):**
- `ingest/cli.py`, `ingest/__main__.py`, `ingest/status.py`, `tests/ingest/test_cli.py`

**Modify (minimal, justified):**
- `ingest/db.py` — add read-only status queries (§5). Only new SQL outside migrations.
- `ingest/migrations/0007_scoped_legacy_served.sql` — scoped dated-data eligibility (§7). **Owner-confirmation item.**
- `requirements.txt` — drop `duckdb`, `pandas`, `pyarrow`, `Pillow`, `pytest-asyncio` (import-legacy is CSV; nothing else imports them). No DuckDB anywhere → no `requirements-migration.txt` (plan still said "keep duckdb for legacy_import"; superseded by Ruling U). Runtime stays requests/pydantic/pyyaml/fastapi/uvicorn.
- `entrypoint.sh` — remove the dead `crond` block (cron dead block; scheduler is Task 18).
- `.github/workflows/ci.yml`, `pytest.ini`, `tests/conftest.py`, `tests/README.md` — remove references to deleted collectors/scripts/duckdb only.

**Delete (superseded collectors/scripts — conservative, dependency-checked):**
- `collectors/`: `base.py`, `bportugal.py`, `eurostat.py`, `fred.py`, `habitacao.py`, `ine.py`, `oecd.py`, `ren.py`, `worldbank.py`, `collect_new_indicators.py`.
- `scripts/`: `audit_nightly.py`, `collect_scheduled.py`, `backfill_full.py`, `backfill_missing.py`, `backfill_eu27.py`, `test_all_indicators.py`, `collectors/` (empty superseded), `maintenance/` (old UI ops), `warm_cache.py` (if present), plus `ingest.py`, `create_seed_db.py`, `generate_share_cards.py` after confirming nothing deployed imports them (grep repo + f0nix checkout reference in entrypoint).
- **KEEP (explicit):** `collectors/eredes.py` until Task 16 E-REDES integration is owner-accepted; `collectors/dgeg_fuel_api.py` and `collectors/dadosgov.py` (DGEG blocked, dado unresolved — reconciliation open per ledger rule). `collectors/base.py` deletion must follow an import check of the kept files; if the three kept collectors import it, KEEP `base.py` too.

## 3. Grouping/orchestration contract (one-verifier-per-source, no registry mutation)

```python
# ingest/cli.py
@dataclass(frozen=True)
class DatasetSpec:
    name: str                          # CLI dataset id, e.g. "worldbank-en"
    make_source: Callable[[], Source]           # fresh instance per run (Eredes windows differ)
    make_verifier: Callable[[], Verifier]       # fresh instance per process
    select: Callable[[SeriesSpec], bool]        # registry predicate; inactive filtered separately
```

`DATASETS: dict[str, DatasetSpec]` — the ONE supported grouping point. Entries:
`eurostat`, `ine`, `bportugal`, `ren`, `fred`, `oecd`, `eredes`, `worldbank-en` (14 en indicators... exact current set: the 16 en-verified indicators minus GDP-growth/unemployment), `worldbank-es` (explicit `csv_language='es'` for GDP growth + unemployment only). **No DGEG entry ever** (all-inactive, `verifiable: false`) — it appears only in status as blocked.

- `run <name>`: one process = one dataset. Steps: load registry (`registry/core.yaml`), `db.upsert_source_and_series`, specs = `[s for s in registry if DATASETS[name].select(s) and s.active]`, build `RequestsHttp(throttle_rps=min(s.throttle_rps for s in specs), timeout=specs[0].source.timeout_s or default)`, `v = DATASETS[name].make_verifier(); register_verifier(v)`, `run_with_refetch(db, store, DATASETS[name].make_source(), get_verifier(source_name), specs, http)` — pass the registry-returned instance so the identity check also guards CLI misuse.
- `run all`: loops datasets **as subprocesses** `[sys.executable, "-m", "ingest", "run", name]` (sequential; this is the reviewed way two WorldBank locales coexist — disjoint processes — and matches how the recorded en/es run was accepted). Continues after a failed dataset, collects exit codes, prints a one-line-per-dataset summary, exit 1 if any failed. Never spawns dgeg.
- No expected values, no config, ever cross into `make_verifier` constructors beyond the already-reviewed `csv_language` (verifier semantics unchanged; independence allowlist untouched).

## 4. Subcommands

`python -m ingest` (= `ingest/__main__.py`: `raise SystemExit(main())`).

- `run <dataset|all> [--dry-run] [--from-bundle DIR]`
  - `--dry-run`: identical flow against a throwaway Db under `$TMPDIR` (registry synced empty schema), prints state/n_written/n_quarantined/sample outcome; the real DB is never opened. Purpose: f0nix smoke per plan step 5.
  - `--from-bundle DIR`: manual-file mode (§6).
- `status [--json]` — prints `status.report(db)` (§5).
- `verify <run_id>`: looks up the run's source and series ids (`db.observations_of_run`), registers that dataset's verifier, fetches the REGISTERED instance via `get_verifier`, calls `verify_run(db, run_id, v, http, specs=run_specs, store=store)`. Non-pending runs surface the existing ValueError, exit 2. Never constructs the expected side anywhere new.
- `import-legacy <csv>`: wraps `ingest.legacy_import.import_legacy` (CSV, Ruling U). Argument help corrected from the plan's `<duckdb>`.
- `replay --from 2026-04`: catch-up, not a different pipeline. Parses `YYYY-MM`, rejects invalid/future/<2020 cutoffs. Per dataset: identical to `run`, except `eredes` gets `EredesSource(from_ts="<cutoff>-01T00:00:00+00:00", to_ts="<today>T00:00:00+00:00")` (day-boundary canonical, asserted by the adapter); all other sources already fetch their full native windows, so replay == run. Replay touches only fresh runs and verifications: legacy rows (`kind='legacy'`, `legacy:<source>` runs) are never re-stated, never gain `verified` from replay (`test_replay_never_marks_legacy_verified`).

## 5. `ingest/status.py`

```python
@dataclass(frozen=True)
class SeriesStatus:
    series_id: str; frequency: str; active: bool
    last_verified: str | None          # latest finished_at of a verified run that wrote this series
    latest_state: str | None           # state of the source's most recent run
    stale_days: int | None             # None if never verified → reported as "never verified"
    open_events: dict[str, int]        # per kind: fetch_failure/format_change/verification_failure/revision
    last_verification_passed: bool | None

@dataclass(frozen=True)
class SourceStatus:
    name: str; verifiable: bool; redistribution_ok: bool
    series: list[SeriesStatus]
    pending_stale_runs: list[int]      # run ids pending-verification older than STALE_PENDING_HOURS (24)
    blocked: bool; blocked_reason: str | None   # dgeg: "blocked: no adapter, channels unresolved (task 16 discovery)"

def report(db: Db, registry: list[SeriesSpec], now: Callable[[], datetime]) -> StatusReport
def to_json(report: StatusReport) -> str   # pinned schema (test_status_json_schema)
def to_text(report: StatusReport) -> str   # per-source sections, stale + blocked first
```

Staleness: `expected = registry SeriesSpec.schedule ("1d"/"7d")` else `DEFAULT_INTERVAL = {"A": 456d, "S": 228d, "Q": 122d, "M": 45d, "D": 2d, "PT15M": 2d}` (interval + release lag, documented constants — a tuning knob, not publisher fact). `stale_days = max(0, (now - last_verified - expected).days)`; a series with no verified run is listed under "never verified". Series-level last_verified uses the run's finished_at of verified runs containing that series. Failed fresh runs never advance it — old verified rows stay served (view gate), and status shows the LAST VERIFIED date honestly even when it's April.

New `Db` read-only methods (SQL lives here only):
`latest_run_per_source() -> dict[str, tuple[int, str, str | None]]`, `verified_series_dates() -> dict[str, str]`, `event_counts_by_source(since: str | None) -> dict[str, dict[str, int]]`, `pending_runs_older_than(cutoff: str) -> list[tuple[int, str, str]]`, `last_verification_outcome() -> dict[str, bool]`. DGEG blocked block is assembled from the registry (17 inactive) plus a static reason string — no fetch, no adapter.

## 6. Manual refresh — pinned-bundle mode (max automatic, honest manual fallback)

Automatic refresh remains the default on every command (live `RequestsHttp`); manual mode is the documented escape hatch while a publisher channel is failing (current: WB en CSV timeouts/502).

```python
# ingest/http.py — the one non-brief production file added (infra client, not a verifier)
class PinnedHttp:  # implements Http, read-only
    """Answers ONLY requests recorded in a manifest. Manifest v1:
    [{"url": <original request URL>, "params": {...}|null, "final_url": ..., "status": int,
      "sha256": ..., "fetched_at": <original UTC time>, "file": <relpath>}]
    get(): canonical (url, sorted params) must match exactly one entry; body bytes are sha256-
    checked on load; returns HttpResult(status=recorded status, body=exact bytes, url=final_url).
    Any other URL/mismatched params/missing-file/bad-hash raises (network-failure path →
    failed-fetch). An entry WITHOUT original url+status+hash is rejected at load: user-supplied
    extracted CSVs never acquire an invented HTTP status (task-13 attachment lesson)."""
```

- `run <dataset> --from-bundle DIR`: loads `DIR/manifest.json`, uses `PinnedHttp` for collector AND registered verifier through the unchanged `run_with_refetch`/`verify_run`, raw store keeps original bytes, verification items keep real evidence_url/sha256. Fetched-at timestamps in the DB are the replay time (honest); the bundle's original `fetched_at` + final URLs are pinned in an `add_event(..., "manual_snapshot", run_id, {manifest_sha256, originals})` event, and status surfaces it. A dated snapshot bootstraps/continues served data; it is NOT recorded as fresh success, and the `verified`-shortcut on identical bytes applies only when identical original bytes genuinely repeat.
- E-REDES: bundle pins the JSON records pages + metadata (collector) and `/exports/csv` downloads (verifier) with the same manifest. No invented April rows: replay from 2026-04 with a bundle containing only genuine downloads writes exactly what those bytes contain.
- Executable manual instructions (deliverable: `docs/superpowers/handoff/reports/evidence/task-13-csv-language/` manifest pattern reused): for each pinned URL, download with the exact recorded URL/params, then `sha256sum` + fill manifest template fields `url/final_url/status/sha256/fetched_at/file`, then `python -m ingest run worldbank-en --from-bundle DIR`; the CLI pre-load validates the entire manifest before any DB write. Template + per-source URL lists ship as comments in `status` output when a source is failed/stale — pointing at this exact procedure.

## 7. Dated-data continuity (owner authorization, scoped)

- Owner-authorized: existing BM (52,618 legacy CSV rows, latest fetch 2026-04-06T01:42:08Z) and E-REDES data stay usable with honest dates while refresh is impossible. E-REDES legacy stored **zero** rows (task-16 discovery) — so scoped eligibility covers `worldbank` legacy rows ONLY; nothing is granted to eredes/dgeg/others.
- Implementation: migration `0007_scoped_legacy_served.sql` replaces the global check in the served view's `eligible` CTE with a membership check against a new table `legacy_served_source(source TEXT PRIMARY KEY)` seeded with `('worldbank')`; the `setting legacy_served` key stays seeded '0' for back-compat and the global OR-branch is REMOVED (no `legacy_served=1`-for-all path remains). The `redistribution_ok = 1` licence join is byte-identical — the licence gate is unchanged. View is recreated verbatim otherwise (0005/0006 pattern).
- Status labels these rows `dated (legacy, fetched ≤ 2026-04-06)` via the `legacy:<source>` runs' finished_at — labels, not silence. Fresh failures (failed-fetch/failed-verification runs) never verify or serve; the state machine already guarantees this.
- **POLICY-AMBIGUOUS — confirm with owner before implementer touches SQL:** whether T17 ships 0007 at all, or whether scoped legacy eligibility belongs to the T16 fix task (it owns db/models/tests edits). Default proposal: 0007 here, seeded `worldbank` only.

**POLICY-AMBIGUOUS 2:** `run all` skipping non-verifiable sources entirely (proposal: skip — fetching revision history from DGEG is blocked anyway; BM/E-REDES verifiable=true so never skipped). **POLICY-AMBIGUOUS 3:** dataset names `worldbank-en`/`worldbank-es` are new CLI vocabulary — visible to user; owner may prefer one `worldbank` name with locale resolved internally (rejected: would need two verifier instances in one process or registry mutation).

## 8. Tests (tests/ingest/test_cli.py)

Required by plan + coverage of every new branch:
1. `test_status_flags_stale_series` — fixture DB: verified run old finished_at → stale_days>0; recent → 0; never verified → reason.
2. `test_status_json_schema` — exact key set/types; blocked dgeg entry present with no fetches made.
3. `test_run_all_continues_after_one_source_fails` — two fake DATASETS entries; first fake source raises on fetch (failed-fetch), second verifies; assert both ran and exit code 1 with both lines in summary.
4. `test_replay_never_marks_legacy_verified` — `import_legacy` then fake replay; legacy rows/observation kinds unchanged; no `verified` gained; served identical.
5. `test_run_ignores_inactive_series` — active:false specs never reach source.fetch.
6. `test_verify_command_uses_registered_verifier` — CLI registers then passes `get_verifier` instance (spies).
7. `test_status_lists_stale_pending_runs` — pending-verification run older than 24h listed with run id.
8. `test_pinned_http_refuses_unpinned_url` / `test_pinned_http_rejects_provenanceless_entry` — no fabricated status, sha256 enforced, mismatch → failed-fetch, no writes.
9. `test_replay_eredes_window` — `--from 2026-04` constructs `EredesSource(from_ts="2026-04-01T00:00:00+00:00", ...)`; invalid/future cutoff rejected.
10. `test_dry_run_does_not_touch_real_db` — real DB path unmodified (no new runs).
11. `test_import_legacy_csv` — CSV accepted; a `.duckdb` path errors clearly.
12. Keep per-verifier registration and `assert_verifier_independent` subprocess assertions intact (existing adapter tests).

## 9. Out of scope (do not creep)

No scheduler/Task 18 (crond removal only), no docs generation (`docgen` is Task 19), no FastAPI/serving changes, no DGEG/dadosgov adapters, no main merge, no deploy, no licence-gate semantics change, no verifier independence-guard change, no rounding/tolerance anywhere, no global legacy flips.
