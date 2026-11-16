# Derived layer v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compute a closed set of derived series (period / year-on-year change, % change, rebased index) from verified served observations only, with exact Decimal arithmetic, 100% independent Fraction recomputation, full input provenance, a `served_derived` view that marks every value as calculated, a CLI + scheduler trigger, status counts and backoffice pages.

**Architecture:** Derived series are declared under a new top-level `derived:` list in `registry/core.yaml`, loaded by a new `ingest.registry.load_derived` (the existing `load_registry` series-list contract is unchanged). Migration 0014 adds `derived_series`, `derived_run`, `derived_observation`, `derived_event` and the `served_derived` view; all SQL stays in `ingest/db.py`. `ingest/derive.py` holds the pure Decimal formulas and the run orchestration; `ingest/derive_verify.py` is a second, independent implementation (fractions only, its own parsing and period arithmetic) that gates the run. The scheduler calls the deriver after each verified group; `status` and the backoffice read derived state through new `Db` read functions.

**Tech Stack:** Python 3.12 stdlib `decimal` / `fractions`, SQLite JSON1 (`json_each`, `json_group_array`), existing `ingest.db` / `ingest.registry` / `ingest.scheduler` / `ingest.status` / `backoffice` (FastAPI + Jinja2), pytest.

**Spec:** `docs/superpowers/specs/2026-11-14-derived-layer-design.md` (Parts 1-6). Read `docs/superpowers/handoff/HANDOFF.md` for standing rulings.

## Global Constraints

- Numbers are text or `Decimal`/`Fraction`, never `float`: no `float(`, no `observation.value` (REAL) column read anywhere in derive/derive_verify; derived values are stored as text.
- Arithmetic: `decimal.Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow])`; scales: `*_pct` = 4, `rebase_100` = 4, `period_change`/`yoy_change` = max fractional digits of the two input tokens.
- Canonical derived text: plain fixed-point, exactly `scale` fractional digits (no `.` when scale 0), `.` as decimal separator, no exponent, no `+`, `-` only for a non-zero value (`-0.0000` is written `0.0000`).
- Inputs: only `kind = 'fetched'` rows currently in `served_observation` (verified run, licence ok, series active). Legacy-unverified rows are never inputs, even with `legacy_served = '1'`.
- Missing input period -> no derived row, no event. Zero denominator -> no row + `derived_event(kind='zero_denominator')`. Missing `rebase_100` base period -> no rows for that series + `derived_event(kind='missing_base_period')`.
- Frequencies: formulas allowed only for base frequency `M`, `Q`, `A`; `S`, `D`, `PT15M` are refused at registry load.
- SQL only in `ingest/db.py`; `ingest/derive.py`, `ingest/derive_verify.py` and `backoffice/` contain no SQL (extend `tests/backoffice/test_boundaries.py`).
- `ingest/derive_verify.py` imports neither `ingest.derive` nor `decimal` nor `ingest.models`.
- Attribution of a derived row: base source attribution + `' - Calculado pelo Prumo'`; licence/licence_url of the base source. The view exposes `is_calculated = 1` on every row.
- Never `docker run` / `docker compose`; deploy only with owner authorization and not before 2026-11-15 10:25 UTC (24 h worker observation). Worker and backoffice are rebuilt in the SAME deploy, worker first: after 0014 the old backoffice code would answer 503 (`open_db_readonly` refuses a newer schema).
- Commits: `git add <files> && git commit -m "..." </dev/null`, message ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_013yKteVjdtPthwSSih1oeWB`. Never touch `AGENTS.md` / `CLAUDE.md` (they carry unrelated dirt: never `git add -A`).
- Tests: `.venv-ci/bin/python -m pytest <paths> -q`; lint: `.venv-ci/bin/ruff check ingest backoffice tests`.

## Review Focus

1. An input vintage is revised (new verified base run) but `derive` has not run yet -> the old derived value disappears from `served_derived` (its input id is no longer served) rather than being served next to the new base value; after `derive` a new derived row version appears and the old row is kept in `derived_observation`. Pinned in Task 2 (`test_view_hides_row_whose_input_was_superseded`) and Task 5 (`test_revision_adds_new_version_and_keeps_old`).
2. A base run is withdrawn -> the derived rows built from it stop being served, and the derived rows built from the vintage that is served again come back without recomputation. Pinned in Task 2 (`test_view_follows_base_withdrawal_back_to_older_vintage`).
3. ROUND_HALF_EVEN ties and negative zero (`100` -> `100.00005` gives `0.0000`, `100` -> `100.00015` gives `0.0002`, `100` -> `99.99999` gives `0.0000`) -> identical text from derive and derive_verify. Pinned in Task 3 and Task 4.
4. Base series made inactive or its source licence withheld (`redistribution_ok: false`) -> no derived row served; the registry refuses an active derived entry whose base is inactive. Pinned in Task 1 and Task 2.
5. Scheduler: a derive failure (exception or mismatch) never fails, retries or alters the base attempt record, and the `--once` exit code depends only on base attempts. Pinned in Task 6 (`test_derive_exception_is_logged_not_fatal`).

---

### Task 1: Registry `derived:` section and loader validation

**Files:**
- Modify: `ingest/models.py` (add `DerivedSpec`, `FORMULAS`)
- Modify: `ingest/registry.py` (add `load_derived`; `load_registry` unchanged)
- Test: `tests/ingest/test_derived_registry.py`

**Interfaces:**
- Produces:
  - `ingest.models.FORMULAS: tuple[str, ...] = ("period_change", "period_change_pct", "yoy_change", "yoy_change_pct", "rebase_100")`
  - `ingest.models.DerivedSpec` (pydantic, `extra="forbid"`): `key: str`, `base: str` (a series id), `formula: Literal[*FORMULAS]`, `params: dict[str, str] = {}`, `label: str` (Portuguese display name, non-empty), `unit: str` (non-empty), `active: bool = True`.
  - `ingest.registry.load_derived(path: Path, specs: list[SeriesSpec]) -> list[DerivedSpec]` - reads the top-level `derived:` list (absent or empty -> `[]`), validates, raises `ValueError` naming the key on: duplicate key; key not starting with `derived.`; key equal to a series id; unknown base; active entry whose base is inactive; base frequency not in `M`/`Q`/`A`; base `decimal != "."` (none exist today; v1 refuses rather than carrying the separator); `rebase_100` without exactly `params == {"base_period": P}` where `normalize_period(P, base.frequency) == P`; any other formula with non-empty `params`.

- [ ] **Step 1: Write failing tests** (registry YAML written to `tmp_path`, sources/series shaped like `tests/backoffice/conftest.py`): `test_absent_derived_section_gives_empty_list`, `test_valid_entries_load_in_file_order`, `test_unknown_formula_rejected`, `test_unknown_base_rejected`, `test_active_entry_on_inactive_base_rejected`, `test_inactive_entry_on_inactive_base_allowed`, `test_daily_semester_and_pt15m_bases_rejected` (parametrize `D`, `S`, `PT15M`), `test_duplicate_key_rejected`, `test_key_must_start_with_derived_and_not_shadow_series`, `test_rebase_requires_valid_base_period` (missing param, `"2021-13"` for M, `"2021"` for M all raise; `"2021-01"` for M loads), `test_params_refused_for_non_rebase`, `test_load_registry_ignores_derived_section` (`load_registry` returns the same specs with and without a `derived:` list).
- [ ] **Step 2: Run** `.venv-ci/bin/python -m pytest tests/ingest/test_derived_registry.py -q` -> FAIL (`load_derived` missing).
- [ ] **Step 3: Implement** `DerivedSpec`, `FORMULAS`, `load_derived` (reuse `normalize_period` for the base-period check; build `{s.id: s}` from `specs`).
- [ ] **Step 4: Run** the new tests plus `tests/ingest/test_registry.py tests/ingest/test_docgen.py` -> PASS; ruff.
- [ ] **Step 5: Commit** `feat(registry): derived series declarations and validation`.

### Task 2: Migration 0014, Db functions, `served_derived` view

**Files:**
- Create: `ingest/migrations/0014_derived_layer.sql`
- Modify: `ingest/db.py` (new section `# --- derived layer (project 3) ---`), `ingest/registry.py` (add `sync_derived`)
- Create: `tests/ingest/derived_helpers.py` (shared test helper)
- Test: `tests/ingest/test_db_derived.py`

**Schema (0014; header comment in the style of 0011/0013; no existing table, view or row changes):**
- `derived_series(id INTEGER PK, key TEXT NOT NULL UNIQUE, formula TEXT NOT NULL CHECK (formula IN (<FORMULAS>)), base_series_id TEXT NOT NULL REFERENCES series(id), params_json TEXT NOT NULL DEFAULT '{}', label TEXT NOT NULL, formula_label_pt TEXT NOT NULL, unit TEXT NOT NULL, active INTEGER NOT NULL CHECK (active IN (0,1))) STRICT`
- `derived_run(id INTEGER PK, started_at TEXT NOT NULL, finished_at TEXT, state TEXT NOT NULL CHECK (state IN ('computing','verified','failed','withdrawn')), trigger TEXT NOT NULL CHECK (trigger IN ('cli','scheduler')), scope_json TEXT NOT NULL, n_written INTEGER, n_checked INTEGER, n_mismatch INTEGER) STRICT` - `scope_json` = JSON list of the derived keys this run evaluated.
- `derived_observation(id INTEGER PK, derived_series_id INTEGER NOT NULL REFERENCES derived_series(id), period TEXT NOT NULL, value_text TEXT NOT NULL CHECK (length(value_text) > 0), scale INTEGER NOT NULL CHECK (scale >= 0), input_obs_ids_json TEXT NOT NULL, computed_at TEXT NOT NULL, run_id INTEGER NOT NULL REFERENCES derived_run(id), state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','match','mismatch'))) STRICT` + index on `(derived_series_id, period, id)`.
- `derived_event(id INTEGER PK, ts TEXT NOT NULL, run_id INTEGER NOT NULL REFERENCES derived_run(id), derived_series_id INTEGER REFERENCES derived_series(id), period TEXT, kind TEXT NOT NULL CHECK (kind IN ('zero_denominator','missing_base_period','mismatch')), detail_json TEXT) STRICT`.
- Triggers: `derived_run_withdrawn_ins` (no INSERT in state `withdrawn`); `derived_run_terminal` (UPDATE OF state where OLD.state is `verified`/`failed`/`withdrawn` and NEW differs is refused, except `verified` -> `withdrawn`); `derived_observation_immutable` (UPDATE OF `derived_series_id, period, value_text, scale, input_obs_ids_json, run_id, computed_at` refused); `derived_observation_state_once` (UPDATE OF state refused unless OLD.state = `pending`).
- View `served_derived`: among `derived_observation` rows with `state='match'`, run `state='verified'`, `derived_series.active=1`, and EVERY id in `input_obs_ids_json` present in `served_observation` with `kind='fetched'`, the highest `id` per `(derived_series_id, period)`. Columns: `derived_key, period, value_text, scale, unit, is_calculated (constant 1), formula, formula_label_pt, label, base_series_id, inputs (json_group_array of json_object('series_id','period','observation_id') in input_obs_ids_json order), licence, licence_url, attribution (source.attribution || ' - Calculado pelo Prumo'), computed_at, derived_run_id, derived_observation_id`.
- `withdrawn` has no writer in v1 (withdrawing the base run already unserves its derived rows through the view); the state and its guard exist so a later reviewed withdrawal command needs no table rebuild.

**Interfaces:**
- Produces on `Db` (all JSON decoded to Python; ids are ints):
  - `upsert_derived_series(rows: list[dict]) -> None` - rows keys `key, formula, base_series_id, params_json, label, formula_label_pt, unit, active`; the WHOLE derived registry: an active key absent from `rows` is set `active=0`.
  - `derived_series_rows(*, active_only: bool = True) -> list[dict]` - keys `id, key, formula, base_series_id, frequency` (joined from `series`), `params` (dict), `label, formula_label_pt, unit, active` (bool); ordered by key.
  - `served_fetched_inputs(series_id: str) -> dict[str, tuple[int, str]]` - period -> (observation id, value_text) from `served_observation` where `kind='fetched'`.
  - `begin_derived_run(started_at: str, trigger: str, scope: list[str]) -> int` (state `computing`).
  - `derived_known_inputs(derived_series_id: int) -> set[tuple[str, str]]` - `(period, input_obs_ids_json)` of rows with `state='match'` in `verified` runs.
  - `write_derived_observations(run_id: int, computed_at: str, rows: list[tuple[int, str, str, int, str]]) -> None` - `(derived_series_id, period, value_text, scale, input_obs_ids_json)`.
  - `add_derived_event(ts: str, run_id: int, derived_series_id: int | None, period: str | None, kind: str, detail: dict | None = None) -> None`.
  - `derived_observations_of_run(run_id: int) -> list[dict]` - keys `id, derived_series_id, key, formula, params, base_series_id, frequency, period, value_text, scale, input_ids` (list[int]); ordered by id.
  - `observations_by_ids(ids: list[int]) -> dict[int, dict]` - keys `series_id, period, value_text, kind, served` (True iff the id is in `served_observation` with `kind='fetched'`); unknown ids absent.
  - `set_derived_row_states(states: list[tuple[int, str]]) -> None`.
  - `finish_derived_run(run_id: int, state: str, finished_at: str, *, n_written: int, n_checked: int, n_mismatch: int) -> None` - compare-and-set from `computing`; `ValueError` otherwise.
  - Reads for Tasks 7-8: `served_derived_rows(key: str, limit: int, offset: int = 0) -> tuple[int, list[dict]]` (view columns, newest period first, `inputs` decoded); `derived_rows_of_series(key: str, limit: int) -> list[dict]` (every version: `id, period, value_text, scale, state, run_id, run_state, computed_at, input_ids, served` bool); `derived_status_rows() -> list[dict]` per ACTIVE derived series: `key, base_series_id, served_values, last_covered_run_id, last_covered_at` (latest `verified` run whose `scope_json` contains the key, its `started_at`), `base_latest_fetched_at` (max `fetched_at` of served fetched base rows); `derived_runs(limit: int) -> list[dict]` (`id, started_at, finished_at, state, trigger, scope, n_written, n_checked, n_mismatch`, newest first).
  - `ingest.registry.sync_derived(db: Db, derived: list[DerivedSpec]) -> None` - calls `upsert_derived_series`, filling `formula_label_pt` from `ingest.derive.formula_label_pt`.
  - `ingest.derive.formula_label_pt(formula: str, params: dict[str, str], base_series_id: str) -> str` - created in THIS task as the first content of the new `ingest/derive.py` (Task 3 adds to the module); `{base}` is the base series id. Exact copy:
  - `period_change`: `"Variação face ao período anterior (diferença), calculada pelo Prumo a partir de {base}"`
  - `period_change_pct`: `"Variação face ao período anterior (%), calculada pelo Prumo a partir de {base}"`
  - `yoy_change`: `"Variação homóloga (diferença), calculada pelo Prumo a partir de {base}"`
  - `yoy_change_pct`: `"Variação homóloga (%), calculada pelo Prumo a partir de {base}"`
  - `rebase_100`: `"Índice rebaseado ({base_period} = 100), calculado pelo Prumo a partir de {base}"`
- Test helper `tests/ingest/derived_helpers.py`: `verified_values(db, sid: str, values: dict[str, str], fetched_at: str, key: str, *, source: str = "fake") -> int` (begin_run -> record_raw_fetch -> write_observations -> set_run_state verified, exactly like `_direct_verified` in `tests/ingest/test_task20_serving.py`; returns run id) and `derived_spec(key, base, formula, **kw) -> DerivedSpec`.

- [ ] **Step 1: Write failing tests** in `tests/ingest/test_db_derived.py`:
  - `test_0014_applies_on_fresh_db_and_tables_are_strict`
  - `test_0014_upgrades_populated_0013_db_without_touching_rows` (pattern of `test_0010_upgrades_populated_0009_and_preserves_everything`: migrations dir limited to <= 0013, insert source/series/run/observation, reopen with real dir; row counts and `served_observation` unchanged)
  - `test_sync_derived_deactivates_absent_keys`
  - `test_view_serves_verified_matched_row_with_calculated_marker` (`is_calculated == 1`, `attribution == "Fake - Calculado pelo Prumo"`, `inputs` equals `[{"series_id": "s1", "period": "2025-01", "observation_id": id_t}, {... "2024-12" ...}]`)
  - `test_view_excludes_pending_mismatch_and_unverified_runs`
  - `test_view_hides_row_whose_input_was_superseded` (newer verified base vintage for one input period -> row gone)
  - `test_view_follows_base_withdrawal_back_to_older_vintage` (derived rows for vintage A and B exist; `withdraw_run(B)` -> served row is the A-based one)
  - `test_view_excludes_inactive_base_series_and_withheld_licence` (two cases: `series.active=0`; source `redistribution_ok=0`)
  - `test_view_never_uses_legacy_inputs_even_when_legacy_served` (setting `legacy_served='1'`, input id of a legacy row -> not served)
  - `test_view_picks_highest_id_among_eligible_versions`
  - `test_derived_observation_value_is_immutable` (UPDATE of value_text raises `sqlite3.IntegrityError`) and `test_row_state_changes_only_from_pending`
  - `test_derived_run_terminal_states_guarded` (verified -> failed refused; verified -> withdrawn allowed; INSERT withdrawn refused)
  - `test_finish_derived_run_is_compare_and_set`
  - `test_derived_status_rows_reports_coverage_and_base_latest`
  - `test_open_applies_migrations_once` in `tests/ingest/test_db.py` stays green unchanged.
- [ ] **Step 2: Run** `.venv-ci/bin/python -m pytest tests/ingest/test_db_derived.py -q` -> FAIL.
- [ ] **Step 3: Implement** the migration, Db methods, `sync_derived`, `formula_label_pt` in a new `ingest/derive.py`.
- [ ] **Step 4: Run** the new tests plus `tests/ingest tests/backoffice -q -m "not live"` (migration affects every DB) -> PASS; ruff.
- [ ] **Step 5: Commit** `feat(db): migration 0014 derived layer and served_derived view`.

### Task 3: Pure Decimal formulas in `ingest/derive.py`

**Files:**
- Modify: `ingest/derive.py`
- Test: `tests/ingest/test_derive_formulas.py`

**Interfaces:**
- Consumes: `ingest.models.parse_decimal(text, ".")`, `FORMULAS`.
- Produces:
  - `CONTEXT: decimal.Context` (Global Constraints values); `PCT_SCALE = 4`; `INDEX_SCALE = 4`.
  - `previous_period(period: str, frequency: str) -> str` (`"2025-01","M"` -> `"2024-12"`; `"2025-Q1","Q"` -> `"2024-Q4"`; `"2025","A"` -> `"2024"`); `year_ago(period: str, frequency: str) -> str` (`"2025-03","M"` -> `"2024-03"`; `"2025-Q2"` -> `"2024-Q2"`; A -> previous year). Other frequencies -> `ValueError`.
  - `format_fixed(value: Decimal, scale: int) -> str` - quantize with `CONTEXT` to `scale`, canonical text per Global Constraints.
  - `@dataclass(frozen=True) DerivedValue: period: str, value_text: str, scale: int, input_ids: tuple[int, int]` (current input first, reference input second; for `rebase_100` the reference is the base-period row, so the base period itself yields `(id, id)` and `"100.0000"`).
  - `@dataclass(frozen=True) Skip: period: str | None, reason: Literal["zero_denominator", "missing_base_period"]`.
  - `compute(formula: str, params: dict[str, str], frequency: str, inputs: dict[str, tuple[int, str]]) -> tuple[list[DerivedValue], list[Skip]]` - values ordered by period; `inputs` is `Db.served_fetched_inputs` output. `*_pct` = (v_t − v_ref) / v_ref × 100 with the denominator as published (sign kept); absolute change scale = max fractional digits of the two input tokens.

- [ ] **Step 1: Write failing tests**: `test_previous_period_and_year_ago_m_q_a` (incl. January and Q1 rollovers), `test_period_helpers_refuse_d_s_pt15m`, `test_period_change_scale_is_max_input_decimals` (`"1.50"`, `"1.2"` -> `"0.30"`, scale 2), `test_yoy_change_pct_value` (`"100"` -> `"103.5"` gives `"3.5000"`), `test_half_even_ties` (`"100"`->`"100.00005"`: `"0.0000"`; `"100"`->`"100.00015"`: `"0.0002"`), `test_negative_zero_is_written_as_zero` (`"100"`->`"99.99999"` pct: `"0.0000"`; equal values abs change `"0"` at scale 0), `test_missing_reference_period_yields_nothing_and_no_skip`, `test_zero_denominator_skipped_with_reason`, `test_rebase_100_base_period_is_100` and `test_rebase_missing_base_period_skips_whole_series` (one Skip with `period=None`), `test_input_ids_are_current_then_reference`, `test_no_float_in_module` (source text of `ingest/derive.py` contains no `float(`).
- [ ] **Step 2: Run** `.venv-ci/bin/python -m pytest tests/ingest/test_derive_formulas.py -q` -> FAIL.
- [ ] **Step 3: Implement**; every arithmetic call goes through `CONTEXT` (`CONTEXT.subtract`, `CONTEXT.divide`, `CONTEXT.multiply`, `Decimal.quantize(..., context=CONTEXT)`).
- [ ] **Step 4: Run** -> PASS; ruff. **Step 5: Commit** `feat(derive): exact Decimal formulas`.

### Task 4: Independent recomputation `ingest/derive_verify.py`

**Files:**
- Create: `ingest/derive_verify.py`
- Test: `tests/ingest/test_derive_verify.py`

**Interfaces:**
- Consumes: Task 2 `Db.derived_observations_of_run`, `Db.observations_by_ids`, `Db.set_derived_row_states`, `Db.add_derived_event`.
- Produces:
  - `expected_text(formula: str, current: str, reference: str) -> tuple[str, int]` - own token parser (strip; drop `,`, space, NBSP, NNBSP thousands separators; then must fully match `[+-]?[0-9]+(\.[0-9]+)?`, else `ValueError`), `fractions.Fraction` arithmetic, half-even rounding via `round(Fraction * 10**scale)`, own fixed-point formatter; returns `(text, scale)`. `ZeroDivisionError` propagates.
  - `@dataclass(frozen=True) VerifyOutcome: n_checked: int, n_mismatch: int, mismatches: list[dict]` (each `{"row_id", "key", "period", "reason", "stored", "expected"}`).
  - `verify_run(db: Db, run_id: int, at: str) -> VerifyOutcome` - for every row of the run: inputs re-read by id must exist, be `kind='fetched'`, `served`, belong to `base_series_id`; first input period == row period; second input period == the expected reference (own period arithmetic: previous / year-ago / `params["base_period"]`); recomputed text and scale equal the stored ones. Reasons: `input_missing`, `input_not_served`, `input_wrong_series`, `input_wrong_period`, `unparseable_input`, `zero_denominator`, `value`, `scale`. Sets every row `match`/`mismatch` and writes one `derived_event(kind='mismatch', detail=<mismatch dict>)` per mismatch.

- [ ] **Step 1: Write failing tests**: `test_independence_static` (AST of `ingest/derive_verify.py`: no import of `decimal`, `ingest.derive`, `ingest.models`), `test_expected_text_agrees_with_derive_on_grid` (for every formula and a fixed grid of token pairs incl. the Task 3 tie and negative-zero cases, `expected_text` equals `derive.compute`'s text and scale), `test_verify_marks_all_rows_match`, `test_tampered_value_is_mismatch` (row inserted directly via `write_derived_observations` with a wrong value -> reason `value`, event written), `test_input_no_longer_served_is_mismatch`, `test_input_from_other_series_or_wrong_period_is_mismatch`, `test_verify_covers_every_row_of_the_run` (`n_checked == len(rows)`).
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement.** **Step 4: Run** -> PASS; ruff. **Step 5: Commit** `feat(derive): independent Fraction recomputation`.

### Task 5: Run orchestration and CLI `derive`

**Files:**
- Modify: `ingest/derive.py`, `ingest/cli.py` (parser + dispatch), `tests/backoffice/test_boundaries.py` (also scan `ingest/derive.py`, `ingest/derive_verify.py` for SQL)
- Test: `tests/ingest/test_derive_run.py`

**Interfaces:**
- Consumes: Tasks 2-4.
- Produces:
  - `@dataclass(frozen=True) DeriveReport: run_id: int, state: Literal["verified", "failed"], n_series: int, n_written: int, n_skipped: int, n_mismatch: int`.
  - `run_derive(db: Db, *, keys: list[str] | None = None, base_series: set[str] | None = None, trigger: Literal["cli", "scheduler"], now: Callable[[], datetime]) -> DeriveReport | None` - selects active derived series (all, or those in `keys`, or those whose `base_series_id` is in `base_series`); returns `None` with no run row when the selection is empty. Otherwise one transaction: `begin_derived_run`, per series `compute` on `served_fetched_inputs`, skip values whose `(period, json.dumps(list(input_ids)))` is in `derived_known_inputs`, write the rest, write Skip events; then `verify_run`; then `finish_derived_run(verified if n_mismatch == 0 else failed)`. An exception after `begin_derived_run` finishes the run `failed` (if still `computing`) and re-raises.
  - CLI: `python -m ingest derive [--series KEY ...]` (`action="append"`); opens `open_db`, `load_derived` + `sync_derived`, `run_derive(trigger="cli")`. Unknown or inactive key -> stderr message, exit 2, no run row. Prints `derive run <id>: <state>; <n_series> series, <n_written> new values, <n_skipped> skipped, <n_mismatch> mismatches` (or `nothing to derive`). Exit 0 verified/nothing, 1 failed.

- [ ] **Step 1: Write failing tests**: `test_first_run_writes_and_verifies`, `test_second_run_without_changes_writes_nothing_but_records_run`, `test_revision_adds_new_version_and_keeps_old`, `test_incremental_equals_full_recompute` (DB A: base writes step 1, derive, step 2 revision, derive, step 3 withdrawal, derive; DB B: same base steps, one derive at the end; `served_derived` compared on `(derived_key, period, value_text, scale, inputs-without-observation_id)` -> equal), `test_mismatch_fails_run_and_nothing_served` (monkeypatch `derive.compute` to return a wrong value -> run `failed`, `served_derived` empty for it), `test_exception_marks_run_failed`, `test_base_series_filter_selects_dependents_only`, `test_empty_selection_returns_none_without_run`, `test_cli_derive_exit_codes_and_output` (0 / 1 / 2 cases via `cli.main([...,"derive", ...])`), `test_cli_unknown_series_key_writes_nothing`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement.** **Step 4: Run** new tests + `tests/ingest/test_cli.py tests/backoffice/test_boundaries.py` -> PASS; ruff. **Step 5: Commit** `feat(derive): run orchestration and derive CLI`.

### Task 6: Scheduler hook

**Files:**
- Modify: `ingest/scheduler.py`
- Test: `tests/ingest/test_scheduler_derive.py`

**Interfaces:**
- Consumes: `run_derive`, `load_derived`, `sync_derived`.
- Produces:
  - `Deriver = Callable[[Db, set[str]], DeriveReport | None]`; default `_derive_after(db, series_ids) -> DeriveReport | None` = `run_derive(db, base_series=series_ids, trigger="scheduler", now=_utc_now)`.
  - `tick(..., deriver: Deriver = _derive_after)`, `serve(..., deriver=...)`, `main(..., deriver=...)` pass it through. In `tick`, after a group's attempt record, when `outcome.state == "verified"`: call `deriver(db, {s.id for s in group.specs})`; a report emits `{"schema": "prumo-scheduler", "version": 1, "ts", "event": "derive", "group": group.label, "run_id", "state", "n_written", "n_mismatch"}`; `None` emits nothing; an exception emits `event "derive"` with `state "error"` and `detail "<Type>: <msg>"` and the pass continues. `scheduler_state` and the `--once` exit code are unaffected (exit code already counts only `event == "attempt"`).
  - `main` loads `load_derived(args.registry, specs)` before the lock (fail fast like the registry) and `_locked_main` calls `sync_derived(db, derived)` right after `sync_registry`.

- [ ] **Step 1: Write failing tests**: `test_verified_attempt_triggers_deriver_with_group_series_ids`, `test_failed_attempt_never_derives`, `test_none_report_emits_no_record` (existing `test_tick_emits_only_attempts_and_inactive_never_scheduled` keeps passing unchanged), `test_derive_exception_is_logged_not_fatal` (next group still attempted; `scheduler_state` of the group shows `verified`, streak 0), `test_once_exit_code_ignores_derive_failure`, `test_main_refuses_invalid_derived_registry_before_lock` (no lock file, no DB created), `test_main_syncs_derived_series`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement.** **Step 4: Run** new tests + `tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py` -> PASS; ruff. **Step 5: Commit** `feat(scheduler): derive after verified base runs`.

### Task 7: `status` integration

**Files:**
- Modify: `ingest/status.py`, `tests/ingest/test_status.py` (version assertion 3 -> 4 only)
- Test: `tests/ingest/test_status_derived.py`

**Interfaces:**
- Consumes: `Db.derived_status_rows`, `Db.derived_runs`.
- Produces:
  - `@dataclass(frozen=True) DerivedStatus: active_series: int, served_values: int, stale: int, never_computed: int, stale_series: tuple[str, ...], last_run_id: int | None, last_run_state: str | None, last_run_at: str | None, failed_runs_7d: int`.
  - `StatusReport.derived: DerivedStatus` (new field before the defaulted ones); `VERSION = 4`. A derived series is `never_computed` when its base has served fetched data and no verified run covered it; `stale` when `base_latest_fetched_at` > `last_covered_at` (compare with `_parse_ts`, never as text). `build_status` signature unchanged.
  - `render_text` adds one line after the totals: `derived: <n> active series; <served> served values; stale <k> / never computed <m>; last run <id> (<state>, <at>); failed runs 7d <f>` and `  DERIVED STALE <keys>` (capped by `STALE_LIST_CAP`) when any.

- [ ] **Step 1: Write failing tests**: `test_status_without_derived_series_reports_zeroes`, `test_derived_fresh_after_derive`, `test_derived_stale_after_new_base_vintage` (new verified base run with later `fetched_at`, no derive), `test_derived_never_computed`, `test_failed_runs_7d_counted`, `test_text_has_derived_line`, `test_json_has_derived_and_version_4`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement.** **Step 4: Run** new tests + `tests/ingest/test_status.py tests/ingest/test_status_readonly.py tests/backoffice` -> PASS; ruff. **Step 5: Commit** `feat(status): derived layer counts and staleness`.

### Task 8: Backoffice derived pages

**Files:**
- Modify: `backoffice/app.py`, `backoffice/reads.py`, `backoffice/templates/base.html` (nav link "Derivadas"), `backoffice/templates/overview.html` (derived status line from `report.derived`)
- Create: `backoffice/templates/derived_list.html`, `backoffice/templates/derived_detail.html`
- Test: `tests/backoffice/test_app_derived.py` (fixtures from `tests/backoffice/conftest.py`; add a `derived:` list to the `Env` registry when given)

**Interfaces:**
- Consumes: Task 2 reads, Task 7 `report.derived`.
- Produces:
  - `reads.derived_list(db: Db) -> list[dict]` (merge of `derived_series_rows(active_only=False)` and `derived_status_rows()` by key: key, label, formula_label_pt, base_series_id, unit, active, served_values, stale, last_covered_at); `reads.derived_detail(db: Db, key: str) -> DerivedDetail | None` (`@dataclass(frozen=True)`: `series: dict, total: int, served: list[dict]` (cap `OBSERVATION_CAP`), `versions: list[dict]` (cap `DETAIL_LIST_CAP`), `runs: list[dict]` (last 20)).
  - Routes (GET/HEAD only): `GET /derived` and `GET /derived/{key}`; unknown key -> 404 `error.html`. Every value cell carries the badge `<span class="calc" title="Valor calculado pelo Prumo">calculado</span>`; the detail page shows `formula_label_pt`, params, unit, attribution text, each input as a link `/series/<series_id>?period=<period>`, the version table with row state (`match`/`mismatch`/`pending`), run state and whether served, and the runs table with `n_checked`/`n_mismatch`.

- [ ] **Step 1: Write failing tests**: `test_derived_list_renders_empty_db`, `test_derived_list_shows_badge_label_and_status`, `test_detail_shows_exact_value_text_and_calculated_badge`, `test_detail_links_inputs_to_series_period_pages`, `test_detail_shows_mismatch_version_as_not_served`, `test_unknown_derived_key_404`, `test_derived_label_html_is_escaped`, and `test_all_routes_are_get_or_head_only` (existing) stays green.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Implement.** **Step 4: Run** `tests/backoffice` -> PASS; ruff. **Step 5: Commit** `feat(backoffice): derived series pages with calculado badge`.

### Task 9: Starter registry entries, docs, handoff

**Files:**
- Modify: `registry/core.yaml` (append top-level `derived:` list after `series:`; do NOT run `propose_registry`)
- Modify: `docs/data/operations.md` (new section `## Derived layer` before `## Rollback`: what is computed, `python -m ingest derive [--series KEY]` inside the worker container, scheduler trigger, how withdrawal/revision propagate, status line, backoffice pages, deploy order worker-then-backoffice in one deploy), `docs/data/methodology.md` (section on derived values: formulas, scales, rounding, no interpolation, independent Fraction recomputation of 100% of values, visual-cue contract for project 4: `is_calculated`, `formula_label_pt`, `inputs`), `docs/superpowers/handoff/HANDOFF.md` (status paragraph)
- Test: `tests/ingest/test_registry_derived_starter.py`

**Starter set (builder confirms each base is active/redistributable; ~25 entries, label in Portuguese, keys `derived.<base id without source prefix>.<formula>`):** `yoy_change_pct` on `ine.ipi_seasonal_cae_TOT.PT`, `_B`, `_C`, `_D`, `_E`, `ine.exports_monthly.PT`, `ine.imports_monthly.PT`, `bportugal.credit_housing.PT`, `bportugal.credit_consumer.PT`, `bportugal.deposits_households.PT`, `eurostat.metals.PT`, `eurostat.chemicals_pharma.PT`, `ine.population.PT`, `ine.live_births.PT`, `ine.deaths.PT`, `eurostat.gdp_per_capita_eur.PT`; `period_change_pct` on `ine.ipi_seasonal_cae_TOT.PT`; `period_change` + `yoy_change` (unit `p.p.`) on `ine.unemployment_monthly.PT` and `bportugal.pt_10y.PT`; `period_change` (unit `balance`) on `eurostat.cci.PT`; `rebase_100` with `base_period: "2015"` on `eurostat.unit_labour_cost_hour.PT` (unit `index 2015=100`). The builder may add entries meeting the same rules, total <= 60.

**Interfaces:**
- Consumes: `load_registry`, `load_derived`.

- [ ] **Step 1: Write failing test** `tests/ingest/test_registry_derived_starter.py`: `test_starter_set_loads` (`20 <= len(load_derived(core, specs)) <= 60`), `test_starter_bases_are_active_redistributable_primary`, `test_no_pct_formula_on_percent_or_balance_units` (base unit in `{"%", "balance", "% GDP"}` -> formula not in `{"period_change_pct", "yoy_change_pct"}`; rate series use `p.p.` differences), `test_pp_entries_declare_pp_unit` (`period_change`/`yoy_change` on a `%` base has unit `p.p.`), `test_every_label_is_nonempty_portuguese_text`.
- [ ] **Step 2: Run** -> FAIL. **Step 3: Add** the entries and docs. **Step 4: Run** the full suite `.venv-ci/bin/python -m pytest tests -q -m "not live"` and ruff -> PASS; then a local smoke on a COPY of a production-like DB if one is available in scratch (never the live DB): `python -m ingest --db <copy> derive` -> `verified`, `python -m ingest --db <copy> status` shows the derived line. **Step 5: Commit** `feat(registry): starter derived series; docs and handoff`.
- [ ] **Step 6 (controller, owner-authorized deploy only, not before 2026-11-15 10:25 UTC):** merge to main per owner, rebuild worker first (`bash -lic "dc-web-up prumo-ingest"`, migrates 0014), then `bash -lic "dc-web-up prumo-backoffice"`; verify `ingest status` derived line, `/derived` page, and that `served_derived` has rows only with `is_calculated = 1`.

## Self-review notes

Spec coverage: §4.1 formulas -> Tasks 1, 3; §4.2 arithmetic -> Tasks 3, 4; §4.3 storage -> Task 2; §4.4 trigger + versions -> Tasks 5, 6; §4.5 verification + eligibility -> Tasks 2 (view), 4; §4.6 licence/attribution -> Task 2; §4.7 visual-cue contract -> Tasks 2, 8; §4.8 starter set -> Task 9; §4.9 deploy -> Task 9 Step 6; §7 incremental == full -> Task 5. Parts 1-6 -> Tasks 1 / 2 / 3-5 / 6-7 / 8 / 9.

Planner resolutions of spec ambiguities: `derived_observation.state` = per-row recomputation result (`pending`/`match`/`mismatch`); `derived_event` is a new table (the base `event` table is not rebuilt and its `dataset_run_id` FK does not fit derived runs); `formula_label_pt` is an extra `derived_series` column generated in code (registry `label` is the display name); `derived_run.scope_json` added for staleness; `withdrawn` state reserved with guards but no writer in v1; `S` frequency refused (spec lists only M/Q/A); base series with `decimal: ","` refused in v1 (none exist); pct denominators keep their sign and pct formulas are refused by test on `%`/`balance`/`% GDP` bases (rate series use p.p. differences - answers the spec's open pp question provisionally).
