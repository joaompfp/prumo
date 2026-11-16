# Final-review fix round - derived layer v1

Branch `pipeline-rebuild`, from fcf2490. One round, no subagents. Commits, in order:

| SHA | Concern |
|---|---|
| 26e3238 | I1 + M1: redefined derived key no longer stops the worker; `derive` exits 2 on refusal / `OperationalError` |
| 63313d2 | I3 + M3: `served_derived` candidate-first (0014 edited in place), known-inputs = newest candidate, cheaper status read, `/derived` TTL cache, zero-served = stale |
| 2c9e4dd | M5: verifier token parser accepts a separator only between thousands groups |
| 58024e2 | Docs: I2 deploy order, I3 serving rule, I1 limitation, M2 runbook lines, M9, HANDOFF owner decisions (a)-(d) |

The coordinator's correction to HANDOFF item (d) arrived before any doc was written. Only the corrected wording (INE only; Eurostat not affected; bportugal one value-identical vintage) was ever written, so no follow-up commit was needed.

## Per finding

### I1 - redefined derived key must not stop the worker
- `ingest/scheduler.py:289` new `_sync_derived_or_log`, called at `:307` in place of the bare `sync_derived`. On `ValueError` it logs ONE record through the existing `_derive_record` (`:135`, `group` now `str | None`): `{"event": "derive", "group": null, "state": "error", "detail": "ValueError: ..."}`. Then base refresh continues. `upsert_derived_series` runs in one transaction, so nothing is written and derive keeps using the definitions stored in the DB. Scheduler state and exit code are untouched.
- `ingest/cli.py:574`: the `ValueError` from `sync_derived` prints `derive refused: <message>` (one line, `_one_line` at `:542`) and exits 2. The catch covers only `sync_derived`, so a `ValueError` from `run_derive` keeps its existing behaviour.
- Tests:
  - `tests/ingest/test_scheduler_derive.py:187` `test_redefined_derived_key_logs_one_error_and_base_refresh_continues`: real `scheduler.main(["--once", ...])` twice; the second run has the formula changed in the registry. The runner is still called for X.ONE, the exit code is 0, there is exactly one derive error record, and the stored definition is unchanged.
  - `tests/ingest/test_derive_run.py:486` `test_cli_redefined_key_exits_2_with_one_line`.
  - Both failed before the fix with the reviewer's `ValueError`.
- Docs: `docs/data/operations.md` "Known limitations" gets one bullet. It also notes that a NEW key added in the same edit is not synced until the edit is reverted, because the whole sync rolls back.

### I2 - deploy order includes `prumo`
- `docs/data/operations.md` (Derived layer → Known limitations → Deploy order): `bash -lic "dc-web-up prumo-ingest"` (migrates 0014), then `bash -lic "dc-web-up prumo"`, then `bash -lic "dc-web-up prumo-backoffice"`, with the reason (one image; old code refuses a 0014 DB).
- "After deploy" names a container for each check:
  - `status` in `prumo`;
  - the first `derive` in `prumo-ingest`;
  - `/derived` on `prumo-backoffice` (:8089, curl from the host);
  - a read-only `served_derived` check in `prumo`, with an exact `python -c` command.
- `docs/superpowers/handoff/HANDOFF.md`: same order and checks in the derived paragraph.
- No raw `docker compose` or `docker run` was added. `tests/test_docker_contract.py` and `tests/test_manual_runbook.py` pass.

### I3 - derived read cost must not grow with base history
1. **View** `ingest/migrations/0014_derived_layer.sql:202` (the header comment, section 3, is rewritten too).
   - The new view is a plain join `derived_series ds ⋈ derived_observation d ⋈ series ⋈ source`, filtered by `ds.active = 1` and:
     `CASE WHEN d.id = (SELECT c.id FROM derived_observation c JOIN derived_run r ON r.id = c.run_id AND r.state='verified' WHERE c.derived_series_id = d.derived_series_id AND c.period = d.period AND c.state='match' ORDER BY c.id DESC LIMIT 1) THEN NOT EXISTS(<input not served as fetched of the base>) ELSE 0 END`.
   - The CASE fixes the order: the candidate is chosen first, and the input check runs only for that one row.
   - There is no window and no aggregate, so the view flattens and `derived_key = ?` reaches the key index.
   - The column list and meanings are unchanged, and the input check is the same correlated per-id lookup as before. The table CHECKs and the insert trigger are untouched, so the malformed-JSON protections still hold.
   - Fail-closed check: on both scenario DBs the full `SELECT * FROM served_derived` output is identical between the old and new view (6,665 rows each). No withdrawal happened there, so the subset rule is exercised by the tests below.
2. **Known inputs** `ingest/db.py:820` `derived_known_inputs` now returns only the newest candidate row per period, with the same predicate as the view. `ingest/derive.py` is unchanged.
   - After a base withdrawal, derive writes a new version on the older inputs, and history keeps all versions.
   - Tests:
     - `test_derive_run.py:112` `test_withdrawn_newest_base_vintage_unserves_until_derive_writes_a_new_version` covers revision → new version served; withdrawal → `{}` served; derive writes 2 new rows; 3 versions of 2025-01 with only the newest served; identical re-run writes 0.
     - `test_db_derived.py:227` `test_view_serves_only_the_newest_candidate_after_base_withdrawal` replaces the old `test_view_follows_base_withdrawal_back_to_older_vintage`, which pinned the old reviving behaviour.
     - `test_db_derived.py:290` (extended): newer mismatch/failed, match/failed, match/computing and pending/computing rows do not hide the older valid row.
     - `test_db_derived.py:303` `test_known_inputs_are_the_newest_candidate_per_period_only`.
     - The expectation in `test_derived_reads_decode_json_and_mark_served_versions` was updated to newest-only.
     - `test_incremental_equals_full_recompute` still passes unchanged.
3. **Per-key reads** `served_derived_rows` (`db.py:922`) and `derived_rows_of_series` (`:940`) needed no SQL change. Both already put `derived_key = ?` in the query, and with the flattening view that predicate now reaches the key index.
   - `served_derived_rows` still runs COUNT + page. Each is now a per-key index search: 0.09 s together at ~50 vintages, against 17.9 s before.
   - I kept the two statements: a single `COUNT(*) OVER ()` statement cannot report the total for an offset past the end.
   - `derived_status_rows` (`:954`) evaluates the served counts once, as before (one GROUP BY over the view).
   - Its `base` CTE (`:967`) used to scan `served_observation` for 20 bases (6.7 s at ~50 vintages). It now walks each base's fetched rows newest first and stops at the first served one. This gives the same answer as MAX over the view (pinned by the unchanged status tests and identical on the scenario DB) and takes 0.48 s.
   - `LIMIT -1` on the ordered subquery stops SQLite from flattening it, which would otherwise test every row before sorting. This is commented in the code.
4. **Backoffice `/derived`** `backoffice/app.py:90,173`: a second `TtlCache(status_ttl_s, monotonic)` holds `(generated_at, rows)`. The page says when the list was generated and for how long it is reused. Test: `tests/backoffice/test_app_derived.py:147` `test_derived_list_is_cached_for_the_status_ttl`.
5. **M3** `ingest/status.py:272`: when the base has served data and the key serves 0 values, the state is `stale`. Test: `tests/ingest/test_status_derived.py:85` `test_zero_served_values_with_base_data_is_stale`; it failed before the fix with served 5, stale 0.
6. **Evidence**: see Timings and EXPLAIN below.
7. **Structural regression tests**:
   - `test_db_derived.py:573` `test_per_key_view_read_never_scans_a_table` (two queries): the key and `derived_observation_key` are searched, and the only SCANs are `json_each` and the inputs co-routine. Against the old view this test fails: the old plan had `SCAN d USING INDEX derived_observation_key`, `SCAN (subquery-16)` and `SCAN e`.
   - `test_db_derived.py:586` `test_per_key_reads_stay_cheap_after_30_base_vintages`: 30 full vintages of a 60-period base, derive after each (3,210 derived rows). Page plus versions stay under 2 s; the actual time is milliseconds. The test takes about 2.5 s, most of it base setup.
8. **Docs**:
   - `operations.md` gets a "Serving rule" paragraph, an extended status rule, and a read-cost bullet.
   - `methodology.md` "Derived values → Serving" is rewritten.
   - M2: "Then run `derive`" with the exact command after the withdraw block and after the manual-import resume block.

### M1 - `derive` and `sqlite3.OperationalError`
`ingest/cli.py:579`: `derive refused: <message>` on one line, exit 2. Test: `test_derive_run.py:503` `test_cli_database_locked_exits_2_with_one_line`; it monkeypatches `run_derive` to raise `database is locked`.

### M5 - verifier parser
- `ingest/derive_verify.py:19,23` has its own regex: optional sign; then either 1–3 digits followed by groups of exactly 3 with one separator throughout (`,`, space, NBSP, NNBSP), or plain digits; then an optional `.digits`. Only those three spaces are trimmed at the ends, as `parse_decimal` does.
- It still imports no `decimal`, `ingest.derive` or `ingest.models`; the existing AST test still passes.
- Tests:
  - `test_derive_verify.py:101` checks 14 bad tokens (`'1,23'`, `'1,2345'`, `'12,34,567'`, `'1.2,3'`, mixed separators, `' 5\n'`, ...). Both parsers must refuse each one.
  - `test_derive_verify.py:110` is a seeded fuzz over about 60k tokens from `0-9 , . + - spaces` plus grouped tokens. It requires the verifier to accept exactly the tokens `parse_decimal` accepts, with equal values; more than 1,000 tokens are accepted.

### M9 and HANDOFF owner decisions
- `HANDOFF.md`: backoffice v1.1 → "migration 0015 - 0014 is the derived layer".
- Open owner decisions now list (d) first, with the corrected 2026-11-15 production numbers, and then (a), (b) and (c) as briefed.

## Timings (same machine, best of 2)

Scenario: the reviewer's production copy (`final-review/prod.sqlite3`, 1–2 vintages) and the same copy plus about 50 simulated daily full vintages of the 20 bases (`final-review/prod-e2.sqlite3`; `ine.ipi_seasonal_cae_TOT.PT` has 52 fetched runs; 339,915 derived rows). Each was copied to `scratchpad/final-fix/`. For "after", the view was dropped and recreated from the new 0014 text. Base-only status means `build_status` with the derived part stubbed out.

| Measure | 1 vintage before | 1 vintage after | ~50 vintages before | ~50 vintages after |
|---|---|---|---|---|
| `SELECT COUNT(*) FROM served_derived` | 0.099 s | 0.080 s | 8.851 s | 1.352 s |
| `derived_status_rows` | 0.127 s | 0.092 s | 15.924 s | 1.745 s |
| `build_status` | 2.179 s | 2.126 s | 18.800 s | 4.582 s |
| `build_status`, base only (reference) | - | 1.943 s | - | 2.784 s |
| one key `served_derived_rows(…, 500)` | 0.208 s | 0.012 s | 17.884 s | 0.092 s |
| `derived_rows_of_series(…, 200)` | 0.113 s | 0.005 s | 9.043 s | 0.046 s |

**Targets.** Per-key reads are well under 1 s: 0.09 s and 0.05 s.

`derived_status_rows` at ~50 vintages is 1.75 s, so status costs 4.58 s against 2.78 s base-only. That is about 1.8 s over the base-only cost, not the targeted ~1 s. The reasons, with numbers:
- **Candidate selection over the whole history:** 0.45 s. This is one indexed lookup for each of the 340k derived rows.
- **Input checks:** about 0.9 s. These are the per-id `served_observation` lookups, and they sit in the deployed 0011 base view: each lookup re-tests every vintage of that (series, period), so it grows with the number of vintages.
- **The `base` CTE:** 0.48 s, mostly sorting each base's fetched rows (about 20 × 52 × 250–500 rows). An index on `observation(series_id, fetched_at)` would remove this. I did not add one, because it is a base-schema change outside this brief.

Under the 2026-11-15 measurements only INE grows daily, so the ~50-vintage scenario (all 20 bases growing) is pessimistic for the 8 non-INE bases. The lever that bounds this is decision (d), value-level dedupe of base vintages.

## EXPLAIN QUERY PLAN (new view, ~50-vintage DB)

Per key (`SELECT COUNT(*) FROM served_derived WHERE derived_key = ?`):
```
SEARCH ds USING INDEX sqlite_autoindex_derived_series_1 (key=?)
SEARCH s USING INDEX sqlite_autoindex_series_1 (id=?)
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
SEARCH d USING INDEX derived_observation_key (derived_series_id=?)
CORRELATED SCALAR SUBQUERY 5                              -- the candidate
  SEARCH c USING INDEX derived_observation_key (derived_series_id=? AND period=?)
  SEARCH r USING INTEGER PRIMARY KEY (rowid=?)
CORRELATED SCALAR SUBQUERY 6                              -- inputs of that row only
  SCAN j VIRTUAL TABLE INDEX 1:                           -- json_each
  CORRELATED SCALAR SUBQUERY 7                            -- served_observation, so.id = ? pushed
    SEARCH o USING INTEGER PRIMARY KEY (rowid=?)
    CORRELATED SCALAR SUBQUERY 12                         -- 0011 "newer eligible" check
      SEARCH s / SEARCH p / SEARCH o USING INDEX sqlite_autoindex_observation_1 (series_id=? AND period=?)
      SEARCH setting ... / SEARCH r ...
    SEARCH r / SEARCH s / SEARCH p / SEARCH setting ...
```
The page query adds only the `inputs` co-routine (`SCAN j`, `SEARCH o USING INTEGER PRIMARY KEY`, a temp B-tree for that small ordered sub-select, `SCAN x`). The outer `ORDER BY period DESC` is served by the index, with no temp B-tree. The whole-view count starts with `SCAN d` and then follows the same per-row plan; that scan is inherent, because it counts every key. The full output is in `scratchpad/final-fix/eqp.txt`.

## Blast radius (callers, grepped; GitNexus unavailable)

| Changed symbol | Callers / readers |
|---|---|
| `served_derived` (view, 0014) | `Db.served_derived_rows`, `Db.derived_rows_of_series`, `Db.derived_status_rows` (all in `ingest/db.py`). No other code reads the view. Not deployed anywhere. |
| `Db.derived_known_inputs` | `ingest/derive.py:206` (`_evaluate`) only. Contract narrowed to newest candidate per period. |
| `Db.derived_status_rows` | `ingest/status.py:278` (`_derived_status` → `build_status` → CLI `status`, backoffice overview/queue via the status cache), `backoffice/reads.py:159` (`derived_list`). Same columns and values. |
| `Db.served_derived_rows`, `Db.derived_rows_of_series` | `backoffice/reads.py:189-190` (`derived_detail`), tests. Signatures unchanged. |
| `ingest.status.derived_state` | `ingest/status.py:279`, `backoffice/reads.py:163`. New stale case only. |
| `scheduler._derive_record` (group may be `None`) | `scheduler._derive`, new `scheduler._sync_derived_or_log`. Nothing parses these records in code (grep for `prumo-scheduler` outside `scheduler.py` finds nothing); docs updated. |
| `scheduler._locked_main` | `scheduler.main` only. |
| `cli._cmd_derive` | `cli.main` only. |
| `derive_verify._parse` | `derive_verify.expected_text` → `_check_row` → `verify_run` (called by `derive.run_derive`). It is stricter now, but every token the Decimal path accepts is still accepted (fuzz-pinned). |
| `backoffice.app.create_app` `/derived` route | Route only; template `derived_list.html` gets three context keys. |

## Full suite and lint
- `.venv-ci/bin/ruff check ingest backoffice tests`: All checks passed.
- Full suite (`tests/ingest tests/backoffice tests/test_docker_contract.py`): `1886 passed, 7 deselected, 3 warnings in 673.92s (0:11:13)`, exit 0, no failures. The `-q` run does not print a warnings summary. A separate backoffice-only run shows the starlette deprecation warning described in the next bullet. I did not identify the other two.
- The one warning in backoffice runs is starlette's `StarletteDeprecationWarning` about `httpx`, raised when `fastapi.testclient` is imported in `tests/backoffice/conftest.py`. It is in a third-party package and was there before these changes.
- `registry/core.yaml` and `registry/core.proposed.yaml` are byte-identical (`cmp`). AGENTS.md and CLAUDE.md were neither edited nor staged.

## Chosen not to do, and why
- **`observation(series_id, fetched_at)` index**, which would remove the remaining 0.48 s of the base CTE: a base-schema change outside the brief. It would go in 0014, or later in 0015.
- **No change to 0011 `served_observation`**: forbidden. Its per-(series, period) re-test of all vintages is now the main remaining cost (see Targets).
- **One statement instead of COUNT + page in `served_derived_rows`**: both are per-key index searches now (0.09 s total at ~50 vintages). A single `COUNT(*) OVER ()` statement cannot return the total when the offset is past the end.
- **M3 side effect, recorded**: an active key that legitimately serves nothing while its base has data (for example `rebase_100` whose base period is not served: `missing_base_period`) now reads `stale` instead of `current`. That is the brief's rule, and it keeps the anti-goal safe by flagging rather than hiding.
- **I1 scope of the refusal**: a refused sync rolls back the WHOLE `derived:` sync, including unrelated label/unit edits and new keys in the same registry change. This is documented; it is the existing `upsert_derived_series` contract.
- **Not touched**, as ruled: M4, M6, M7 and M8 (M7/M8 are listed under HANDOFF owner decisions as (a)/(b)).
