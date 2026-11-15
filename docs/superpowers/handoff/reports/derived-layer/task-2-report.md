# Task 2 report: migration 0014, Db derived functions, served_derived view

Status: DONE. Commit `3b84af6` feat(db): migration 0014 derived layer and served_derived view.

## Files
- `ingest/migrations/0014_derived_layer.sql` (new): 4 STRICT tables, 2 indexes, 6 triggers, view `served_derived`, header in the style of 0011/0013.
- `ingest/db.py`: new section `# --- derived layer (project 3) ---` with every interface in the brief (upsert_derived_series, derived_series_rows, served_fetched_inputs, begin_derived_run, derived_known_inputs, write_derived_observations, add_derived_event, derived_observations_of_run, observations_by_ids, set_derived_row_states, finish_derived_run, served_derived_rows, derived_rows_of_series, derived_status_rows, derived_runs).
- `ingest/registry.py`: `sync_derived` (params_json = `json.dumps(params, sort_keys=True)`).
- `ingest/derive.py` (new): `formula_label_pt`, label text copied exactly from the brief.
- `tests/ingest/derived_helpers.py` (new): `verified_values`, `derived_spec`.
- `tests/ingest/test_db_derived.py` (new): 20 tests (all the brief's tests plus 4 extras).
- `tests/ingest/test_task24_withdrawal_and_runs.py`: the 0013 upgrade test hard-coded `== 13` applied migrations. It now compares against `len(dbmod._expected_migrations())`, so 0014 does not break it.

## TDD evidence
- Red: collection failed with `ModuleNotFoundError: ingest.derive`. The Db methods and the migration did not exist yet.
- Green: all 20 tests pass.
- Mutation checks (each reverted afterwards):
  - Dropping the "every input served" clause made 4 view tests fail: superseded input, withdrawal, inactive/licence, legacy.
  - Dropping the `kind='fetched'` filter on inputs made the legacy test fail.
  - `rn = 1` -> `rn >= 1` made the highest-id test fail.

## Tests
- `tests/ingest tests/backoffice tests/test_docker_contract.py -m "not live"`: 1716 passed, 7 deselected, 600 s. The 3 warnings are pre-existing (starlette httpx, fork). I removed the 3 warnings my own code first caused (`?1` placeholders with a positional tuple).
- `ruff check ingest backoffice tests`: clean.

## Decisions beyond the brief (please review)
1. **Derived key definition is immutable.**
   - What: `upsert_derived_series` raises a ValueError that names the key when an existing key's formula, base or params change. Trigger `derived_series_definition_immutable` also enforces this in the database. Label, unit, formula_label_pt and active may still change.
   - Why: otherwise rows computed under the old formula would be served under the new formula's label. That is the anti-goal "calculated value silently changes".
   - Consequence: changing a definition needs a new key.
2. **REPLACE cannot bypass the guards** (the 0013 M-2 lesson).
   - `derived_run_withdrawn_ins` also refuses an INSERT whose id belongs to a verified, failed or withdrawn run.
   - New trigger `derived_observation_no_replace` refuses INSERT OR REPLACE over an existing derived row. Without it, the immutability trigger could be bypassed.
3. **`withdrawn` is reachable only from `verified`.** `derived_run_terminal` also refuses `computing -> withdrawn`. The brief's wording covered terminal OLD states only.
4. **The view requires a non-empty input list.** `json_array_length > 0`, so an empty list cannot pass "every input served" vacuously.
5. **The view's input check is a correlated per-id lookup** (`NOT EXISTS ... served_observation so WHERE so.id = j.value AND so.kind='fetched'`), not `IN (SELECT id FROM served_observation)`. The synthetic benchmark used 270k observations, 90k served and 12k derived rows:

   | Query | Before | After |
   | --- | --- | --- |
   | Full view count | 1.23 s | 0.24 s |
   | `served_derived_rows` for one key | 2.43 s | 0.44 s |

6. **`finish_derived_run` accepts only `verified` or `failed`** as the target state (ValueError otherwise), in addition to the compare-and-set from `computing`.
7. **Extra index** `derived_observation_run(run_id, id)`, for `derived_observations_of_run`.

## Concerns / notes for later tasks
- **Per-key reads still scan every eligible row.** `served_derived_rows(key)` takes about 0.44 s at the synthetic scale above. The view's ROW_NUMBER window covers all eligible rows, so the key filter is not pushed into it. This is fine for v1; if backoffice pages are slow, add a key-scoped query in db.py.
- **The served view does not check the derived run's scope.** A derived row in a verified run is served even if its key is not in that run's `scope_json`. Task 3 writes rows only for keys it scoped, so this is consistent by construction.
- **A future table rebuild must also handle served_derived.** A later migration that rebuilds series, source, observation or dataset_run must DROP and recreate `served_derived` as well as `served_observation`. This is noted in the 0014 header.
- **GitNexus checks were skipped.** The repo CLAUDE.md asks for GitNexus impact and detect_changes checks, but GitNexus tools were not available in this session. The only existing code touched is the 0013 upgrade test assertion. Everything else is new symbols.

---

## Fix round 1 (review I1-I3, M1, M3-M5)

0014 is not deployed, so I edited it in place.

### Changes
- **I1. A row cannot reach `served_derived` without its run's verification.**
  - New trigger `derived_observation_ins`: a row is inserted only as `pending`, only into a `computing` run, and never over an existing id. It also replaces the earlier `derived_observation_no_replace`.
  - `derived_observation_state_once`: the state now also changes only while the run is `computing`.
  - `derived_run_withdrawn_ins`: a run is inserted only as `computing`, never over an existing id.
  - New trigger `derived_run_verified_complete`: a run goes `computing -> verified` only if every one of its rows is `match`.
  - `Db.finish_derived_run('verified')` raises a ValueError naming the `pending`/`mismatch` rows before trying the update.
  - Contract for Task 5: write the rows, `set_derived_row_states` for every row, then `finish_derived_run`. Any mismatch means finish as `failed`.
- **I2. Inputs must come from the base series.** The view's per-id lookup now includes `AND so.series_id = ds.base_series_id`, so licence and attribution always belong to the inputs' own source.
- **I3. Input lists are validated.**
  - CHECK constraints: `scope_json` must be a JSON array; `input_obs_ids_json` must be a non-empty JSON array. The json_valid test runs first (via CASE), so bad JSON fails as an IntegrityError rather than a "malformed JSON" OperationalError.
  - `derived_observation_ins` also refuses an input list whose elements are not integers (strings or floats), contain duplicates, or name an observation that does not exist.
  - **Consequence for Task 3:** a `rebase_100` row at its own base period must store `[t]`, not `[t, t]`.
- **M1. Derived history cannot be deleted.**
  - BEFORE DELETE guards on derived_series, derived_run, derived_observation and derived_event.
  - `derived_series_no_replace` (no INSERT over an existing key or id), so REPLACE cannot bypass the definition guard. `Db.upsert_derived_series` now updates existing keys in place and inserts only new ones.
  - Migrations 0011-0013 do not guard deletes of observation/dataset_run. That was not a deliberate allowance: nothing there deletes rows. The 0014 header explains this.
- **M3. Deterministic `inputs` order.** The view's aggregate order is not guaranteed before SQLite 3.44. That includes the python:3.12-slim image (Debian bookworm, SQLite 3.40) as far as I can tell. The view now also exposes `input_ids` (the stored array). `Db.served_derived_rows` decodes `input_ids` and sorts `inputs` into that order.
- **M4. Migration header corrected** to the measured figures: 0.44 s per key versus 2.4 s with the uncorrelated form, at 270k observations / 12k derived rows.
- **M5. `formula_label_pt` raises ValueError** for `rebase_100` without `base_period` (the message names `base_period`), and for an unknown formula.

### Tests (red first)
- **New tests:**
  - `test_rows_enter_only_a_computing_run_as_pending`
  - `test_row_state_changes_only_while_run_is_computing`
  - `test_finish_verified_refused_while_rows_pending_or_mismatched`
  - `test_view_refuses_inputs_from_another_series` (the reviewer's s2 / CC-BY-NC reproduction)
  - `test_input_list_must_be_distinct_existing_integer_ids`, 8 cases: not json, object, empty, duplicate, string id, float id, unknown id, JSON string
  - `test_run_scope_must_be_a_json_array`, 3 cases
  - `test_derived_history_is_never_deleted_or_replaced`
  - `test_inputs_follow_the_stored_input_order`
  - `test_rebase_label_without_base_period_names_the_param`
- **Red run:** `pytest tests/ingest/test_db_derived.py -q` gave 17 failed, 21 passed. Every new test failed except `test_inputs_follow_the_stored_input_order`. That one passes either way, because the engine happens to keep the subquery order; it pins the reader contract.
- **Removed case:** I deleted the `_derive(state="pending", run_state="verified")` case from `test_view_excludes_pending_mismatch_and_unverified_runs`. That combination can no longer be created.
- **Mutation checks:**
  - Removing the base-series clause makes `test_view_refuses_inputs_from_another_series` fail.
  - Disabling `derived_run_verified_complete` makes `test_finish_verified_refused...` fail (the trigger backstop is exercised on its own).
- **Reviewer probe file:** A, B, C, C2, E and F now raise IntegrityError, ValueError or IntegrityError as intended. D serves nothing (`D []`). G is refused. I raises ValueError. H passes.
- **Command:** `.venv-ci/bin/python -m pytest tests/ingest/test_db_derived.py tests/ingest/test_db.py tests/ingest/test_task24_withdrawal_and_runs.py tests/ingest/test_derived_registry.py -q`
  - Result: **103 passed in 36.18s**
- **Lint:** `.venv-ci/bin/ruff check ingest backoffice tests` reports "All checks passed!"
- **Full suite not re-run:** only derived files changed (0014, the derived section of db.py, derive.py, derived tests).
