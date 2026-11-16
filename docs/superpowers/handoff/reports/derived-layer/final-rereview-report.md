### Finding Verdicts

- **I1** - ADDRESSED. `ingest/scheduler.py:289-297` `_sync_derived_or_log` catches the `ValueError` and logs one `derive` record (`group: null`), called at `:307` in place of the bare `sync_derived`. `upsert_derived_series` runs inside `Db.transaction()` (`ingest/db.py:60-69`, ROLLBACK on exception), so nothing is written. CLI: `ingest/cli.py:571-575` prints one `derive refused:` line and exits 2. Tests: `tests/ingest/test_scheduler_derive.py:187` (runner still called, exit 0, one error record, stored definition unchanged) and `tests/ingest/test_derive_run.py:486`. The Known limitations bullet is in operations.md.
- **I2** - ADDRESSED. `docs/data/operations.md` deploy order is now `prumo-ingest` → `prumo` → `prumo-backoffice`, all through `bash -lic "dc-web-up …"`. Each post-deploy check names its container: `status` in `prumo`, `derive` in `prumo-ingest`, `/derived` curl from the host to `prumo-backoffice`, the read-only SQL check in `prumo`. The `HANDOFF.md` STATUS 2026-11-15 paragraph says the same. No raw `docker compose` or `docker run` was added.
- **I3** - ADDRESSED. The view now picks the candidate first and checks only that row's inputs (`ingest/migrations/0014_derived_layer.sql:202-227`). `derived_known_inputs` uses the same candidate (`ingest/db.py:820-830`). Per-key reads reach the key index. The `base` CTE walks newest-first (`db.py:960-967`). `/derived` has a TTL cache (`backoffice/app.py:65,186-193`). Structural test at `tests/ingest/test_db_derived.py:573` and a 30-vintage test at `:586`. Docs are updated. The `derived_status_rows` target is missed by about 0.8 s (1.8 s over base-only at ~50 vintages). The report states this with numbers and puts the remaining cost in the 0011 view, which the brief allows.
- **M1** - ADDRESSED. `ingest/cli.py:576-578` catches `sqlite3.OperationalError` around sync and derive and exits 2 with one line. Test: `test_derive_run.py:503`. `open_db` sits outside the catch (see Out-of-Scope).
- **M2** - ADDRESSED. "Then run `derive`" plus the exact `docker exec prumo-ingest … derive` command was added after the manual-import resume block (`operations.md:386-391`) and after the withdraw block (`:441-447`).
- **M3** - ADDRESSED for the case the finding describes: `ingest/status.py:276-277` returns `stale` when served = 0 and the base has served data. Test: `tests/ingest/test_status_derived.py:85`. A partial-withdrawal variant still reads `current`; it is listed under New Breakage.
- **M5** - ADDRESSED. `ingest/derive_verify.py:19-37` has its own regex with the same grammar as `models._number_re` and still imports no `decimal`, `ingest.derive` or `ingest.models`. `'1,23'` is refused. Tests: `test_derive_verify.py:101` (14 bad tokens refused by both parsers) and `:110` (60k-token agreement fuzz).
- **M9** - ADDRESSED. `HANDOFF.md:9` now reads "migration 0015 - 0014 is the derived layer".

### Answers to checks 1–8

1. **Holds.** A row is served only when four things hold:
   - `ds.active = 1`;
   - `d.id` equals the correlated candidate, which requires `c.state='match'` and `r.state='verified'`;
   - every `json_each` input is in `served_observation` with `kind='fetched'` and `series_id = ds.base_series_id` (0014 lines 211-227);
   - a NULL candidate falls to `ELSE 0`.

   Experiment: a random model check, 40 seeds × 40 steps. Each step was one of: new full or partial vintages with revisions, withdrawal of a random run, `run_derive` (re-run after each), newer `match`/`mismatch`/`pending` rows in `failed`/`computing` runs, and deactivation and reactivation of a key. After every step, `served_derived` was compared with an independent Python reference. The run covered 185 withdrawals, 934 verified and 198 non-verified derive runs, and 12,965 derived rows. 0 differences (`scratchpad/final-rereview/model.py`).
2. **Holds: fail-closed.** Only `d.id = candidate` can pass, so an older row of the same period is never served in place of an unserved candidate. The model check covers this, and `test_db_derived.py:227` pins it.
3. **Holds: "newest" agrees.** `derived_known_inputs` uses the same predicate as the view: highest id, `match`, verified run, same (series, period).
   - Failed, computing and `mismatch` rows are excluded from both, so the skip and the view always look at the same row.
   - The model check asserted after every verified derive that the served set equals a fresh `compute()` over the currently served inputs. That covers "a revision always yields a new row" and the withdrawal back-fill. An immediate identical re-run wrote 0 rows every time.
   - I found no case where the skip compares against a row the view does not serve, except where its inputs are unserved; and then the skip cannot fire, because derive's current inputs come from the same `served_observation` filter (`db.py:808-811`).
4. **Correct either way.** EXPLAIN shows two forms:
   - With `LIMIT -1`: co-routine `n`, sorted, then `SCAN n` stops at the first served row.
   - Without it: SQLite flattens and moves the ORDER BY to the outer query (`USE TEMP B-TREE FOR ORDER BY` after the filter), which tests every row first but returns the same answer.

   The model check compared the `LIMIT -1` form, the form without it, and `MAX(fetched_at)` over `served_observation` at every step: always equal.
5. **Would fail.** I installed the fcf2490 view on a fresh migrated DB and ran the test's two queries on a new connection. The plan has `SCAN d USING INDEX derived_observation_key`, `SCAN (subquery-16)` and `SCAN e`, and no `SEARCH d … (derived_series_id=?)`. Both assertions of `test_per_key_view_read_never_scans_a_table` fail. The new view passes.
6. **Correct literal reading of the brief (item 5), but it can mislead.**
   - Every active key that legitimately serves nothing while its base serves data stays `stale` forever, and running `derive` does not clear it. Examples: `rebase_100` with `missing_base_period`, YoY on a base with fewer than 13 periods, all periods zero-denominator.
   - The backoffice has no `derived_event` listing (T8), so the cause is found only by hand SQL.
   - It is fail-safe, since no value is served. But the operations.md status rule does not mention this case; only the fix report does.
7. **Holds.** The `/derived` cache is a separate single-slot `TtlCache` (`backoffice/app.py:65`). The route has no parameters, so there is no per-key data to mix. A compute that raises is not cached (`ttl_cache.py:25-27`).
   - Expiry uses the injected monotonic clock, `>= ttl`; the test at `test_app_derived.py:147` pins 29 s cached and 31 s recomputed.
   - Each `create_app` builds a fresh cache, and `env.client()` builds a new app, so no cache outlives a test.
8. **Holds.**
   - `sync_derived` runs once in `_locked_main`, before `tick`/`serve`. That is exactly one record per `--once` pass, and one per process start in serve mode; never one per dataset.
   - The whole sync is one transaction that rolls back, so nothing is half-written.
   - `derived` is used only for the sync, and `_derive_after` reads the stored definitions (`scheduler.py:59-61`).
   - The test checks runner called, exit 0, one record and the unchanged stored row.

### New Breakage in the Fix Diff

- **Minor.** After a partial base withdrawal, status reads `current` while some periods serve nothing, and the new docs say otherwise. The docs touched are `docs/data/operations.md:632-634` ("status shows those keys as `DERIVED STALE` meanwhile"), the withdraw runbook `:441-443`, and the HANDOFF serving-rule sentence. The rule at `ingest/status.py:276` covers only served = 0.
  - Input (`scratchpad/final-rereview/partial.py`): full vintage A (2024-11..2025-02), derive, then partial vintage B revising only 2025-02, derive, then `withdraw_run(B)`.
  - Result: `served_derived` drops 2025-02 (`[('2024-12','10'), ('2025-01','2')]`), but `derived_status_rows` gives served 2 and base_latest 2026-11-01 < last covered 2026-11-02, so the state is `current`.
  - The fix itself creates this gap: the old view revived the older row. It fails closed, the runbook says to run `derive` after every withdrawal anyway, and the next verified scheduler attempt fills the gap. So no wrong number, but the docs overstate what status detects. Fix: soften the doc sentences, or extend the rule, for example by counting candidate rows whose inputs are not served.

### Out-of-Scope Observations

- `ingest/cli.py:562` `open_db(db_path)` is outside the new `OperationalError` catch. A lock hit during open or migration would still print a traceback. This is unlikely with no pending migration.
- Value-identical daily INE vintages create new observation ids. Every INE-based derived key therefore writes a full new version per day, about 6.6k rows per day across the starter set, so `derived_observation` and the whole-view status cost keep growing linearly. That is decision (d) in HANDOFF; it is not something the fix can bound.
- `derive_verify._parse` now duplicates `parse_decimal`'s grammar verbatim. The two parsers agree by construction, so the independence of the token parse is nominal; the arithmetic and period logic remain independent.

### Verdict

Fix round: all findings addressed, no new Critical/Important breakage.
