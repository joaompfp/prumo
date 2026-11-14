# Task 21 report: final-review part B fixes (B-I1, B-I2, B-I3, B-I4, B-M1, B-M3, with B-M5)

Branch `pipeline-rebuild`, base ebd4b13. Commits: 8c0f159 (pure sample design + tests),
1038f99 (verification, verifiers, migration 0012, CLI and tests), d395fcf (World Bank exponent
cells, found by the live census), 30c9b6f (docs), plus this report. Nothing pushed or deployed;
f0nix and the production DB untouched; AGENTS.md / CLAUDE.md left unstaged as found.

## What changed

### B-I1 / B-M5: the sample scales with N and covers history (`ingest/sampling.py`)
Procedure `prumo-sample-v2` (pure module, no DB, no network). Each step records its reason
on the item:
1. `latest`: the latest period of every series.
2. `changed`: see B-I2.
3. `series-stratum`: each series' remaining rows are split by period into an older half and a
   recent half; one random row is drawn from each half (up to 2 per series).
4. `random`: a simple random sample of the history pool, of size n = the smallest n with
   hypergeometric P(no defect | D = ceil(1% of pool), n) <= 5%. The arithmetic is exact
   (`Fraction`). n is 258 for a pool of 1,000, 281 for 2,500 and 294 for 10,000, tending to 298.
5. `same-response`: every other row whose `Verifier.request_key` equals a chosen row's. These
   cells come from a response that is fetched anyway, so they cost no extra HTTP. This gives a
   census for Eurostat (TSV), World Bank (ZIP), FRED (table page), OECD (CSV per series),
   E-REDES (day CSV) and REN (chart-month CSV).

Why the statistical claim holds:
- Steps 1, 2 and 5 are censuses of the rows they cover.
- Step 4 alone gives the 95% / 1% guarantee.
- Steps 3 and 5 only add rows, and drawing step 4 after step 3 can only lower the probability
  of a miss. The proof is in the module docstring and in `docs/data/methodology.md`.

Randomness uses a documented ranking: sha256("prumo-sample-v2" US seed US stratum US series US
period), taking the lowest ranks in each stratum. It does not use `random.Random.sample`, so the
draw does not depend on the Python version.
- The seed (63 bits from `secrets`) is stored.
- The design summary is stored in the new `verification.sample_procedure` and
  `verification.sample_design` columns.
- `draw_sample` reproduces the sample from the seed, the run's rows and events, and the
  verifier's `request_key`.
- Old verifications are labelled `v1-python-random-sample`. Their items stay stored, but the v1
  draw is not re-implemented (declined: YAGNI).

`test_sample_covers_every_series_even_when_size_smaller` is replaced by
`test_sample_checks_history_beyond_the_latest_of_every_series`, plus 21 tests in
`tests/ingest/test_sampling.py`. They cover exact minimal n, the 329-series Eurostat shape, the
cap, the closure and reproducibility.

### B-I2: changed cells are must-check, with reasons
- `pipeline._write` now emits `event(new_periods, {series_id, periods})` for periods new to a
  series that already had verified fetched data.
- Together with the existing `revision` events, this is the run's changed set. It is fixed at
  write time, so a redraw sees the same set.
- Changed cells are forced into the sample, capped at 500 per run. The total, the number checked
  and the cap are stored in `sample_design`.
- `verification_item.reason` takes one of: latest, changed, series-stratum, random,
  same-response.
- First ingestions produce no `new_periods` (nothing to be new against), so the cap is not
  wasted on them.

### B-I3: recorded input is verified over live HTTP
`run_with_refetch` and `run_source`/`run_all` take a separate verifier client
(`verify_http` / `verify_http_for`) and a `verifier_channel`.

In `run <src> --bundle DIR`:
- The collector reads only the pinned bundle.
- The verifier uses the normal live client. Offline, verification fails with
  `failed-verification`, the report detail `verifier channel unavailable...` and an escalation
  event. Nothing is served.

`--pinned-verifier` keeps the old offline behaviour:
- It is valid with `--bundle` only.
- `--help` and the docs say it is NOT audit-grade.
- It is recorded as `verification.verifier_channel='pinned-bundle'`.

Other rules:
- `verification.input_origin` records live or recorded input.
- Recorded input gets one attempt, because re-reading the same bundle is not a refetch.
- Migration 0012 backfills historical recorded verifications as `pinned-bundle`, because that is
  how they were verified.

### B-I4: evidence is mandatory and replay re-reads it
- An item without evidence bytes fails.
- `Verifier` now requires:
  - `reread(evidence, item) -> ItemResult`, a pure function;
  - `request_key(item)`;
  - `not_compared`, a dict of {unit|flag: reason}.
- `register_verifier` refuses a verifier without them.
- The spec each series was verified with is stored in the new `verification_spec` table.
- `replay_item(db, store, id, verifier, specs=None)` (with `replay_check` giving the reason):
  1. loads the evidence and integrity-checks it (a corrupt file raises `RawIntegrityError`; a
     missing one is "not a match");
  2. runs `reread`, which must not raise and must reproduce the stored claim exactly (key, text,
     decimal, unit, flag);
  3. re-decides the comparison.
- `reread` is implemented for all 8 verifiers. Each shares its decision helper with `check`, so
  the two cannot diverge:
  - World Bank: the locale comes from the archived URL;
  - OECD: the window comes from the archived URL query;
  - INE: re-reads the selection HTML alone. Its echoed Classificacoes was checked equal to the
    indicator page's on all 20 recorded selections, and `check` now asserts that equality.
- Per-verifier tests use recorded fixtures: `test_every_item_replays_from_its_archived_evidence_via_reread`
  in each `test_verifier_<source>.py` (via `tests/ingest/replay_helpers.py`). Each test:
  - replays the verified items;
  - checks that a forged claim (observed and expected edited together) is rejected as
    "disagrees with the stored claim".

### B-M1: what was compared, and why not
Each item now records:
- `compared`: for example `series_id,period,value,unit`;
- `unit_not_compared` / `flag_not_compared`: the verifier's declared reason.

An item that leaves out unit or flag without a declared reason fails. Old rows (NULL) keep the
old semantics. A per-source table is in the methodology.

### B-M3: outage vs mismatch, escalation
- A new `VerifierUnavailable(ValueError)` is raised by all 8 verifiers on a non-2xx response.
  It and `OSError` (requests connection errors and timeouts) count as an OUTAGE, which:
  - writes `event(verifier_outage)`;
  - stops the loop at once, with no dataset re-download;
  - writes `event(verification_escalated, {reason: verifier_outage, run_ids})`.
- A content-drift exception or a value mismatch still refetches.
- When the last attempt fails, `verification_escalated` is written with reason `max_attempts`
  (or `recorded_input_single_attempt`) and the failed run ids.
- `DatasetRunResult.detail` carries the reason into the CLI report.

### Migration 0012 (`ingest/migrations/0012_verification_audit_v2.sql`)
- Adds the verification columns and backfills them.
- Adds the verification_item columns; `reason` has a CHECK constraint.
- Adds the `verification_spec` table.
- Rebuilds `event` with the kinds `new_periods`, `verifier_outage` and
  `verification_escalated`. The withdrawal trigger that reads `event` is dropped and recreated
  unchanged.
- Test: a populated 0011 database upgrades. Tested:
  - the backfill values;
  - the event CHECK;
  - the trigger still refuses a bare `withdrawn`, and `withdraw_run` still works.
- The Task 20 migration test is pinned to the 0011 upgrade (migrations up to 0011 only), because
  0012 adds columns to `verification`.

## Live census evidence (clearly marked live tests, run once each)
- **Eurostat**, `test_live_eurostat.py` (3 series): 474/474 cells verified.
- **World Bank**, `test_live_worldbank.py` (all 930 series, 18 indicators):
  - First run: FAILED on 4 cells (AR trade balance 1960-64). The CSV writes
    `2.12913319746322E-06` where the API writes `0.00000212913319746322`. The old latest-only
    sample could never have seen this.
  - Fix d395fcf: the verifier rewrites exponent tokens exactly via `Decimal`.
  - After the fix: **45,915/45,915 cells verified**.
- **REN**: 182/182.
- **OECD**: 83/83. Its live test now asserts census size instead of 12.
- **BPstat** (`test_live_bportugal.py`): verified, 313 items (10 latest + 20 strata + discovery
  fill + changed cells), 4,318 served, 6 min at 1 request/second.
- Not run: INE live (slow, ~400 requests), FRED live (needs a key), E-REDES live.

## Sample sizes for the current registry groups (before -> after)
| Source (groups) | Series/group | Before (fixed 50) | After |
|---|---|---|---|
| Eurostat (1) | 329 | 329 latest cells, no history | census of all observations |
| World Bank (18) | ~52 | ~52 latest per indicator (949 total), no history | census (~45,915) |
| FRED (1) | 12 | 50 | census (5,004 in fixtures) |
| OECD (1) | 6 | 50 | census (77 fixtures, 83 live) |
| E-REDES (1) | 3 | 50 of 864 | every cell of each sampled day (all days of a 3-day run) |
| REN (1) | 14 | 50 of 182 | ~all 182 (chart-month closure; 182/182 live) |
| INE (1) | 41 | 50 of ~1,394 | ~383 (41 latest + 82 strata + 260 random) + changed cells |
| BPstat (1) | 10 | 50 of ~4,310 | ~318 (10 latest + 20 strata + 288 random) + changed cells |

INE and BPstat need one request per item, so a verification now takes several hundred
throttled requests. At 1 request/second that is minutes for BPstat and longer for INE.

## Tests
- New files:
  - `tests/ingest/test_sampling.py` (21 tests);
  - `tests/ingest/test_task21_verification.py` (22 tests): changed/cap, record columns,
    compared/reasons, evidence-mandatory, replay paths, outage vs mismatch vs drift,
    escalation, verifier client separation, recorded single attempt, CLI live and
    offline/pinned/flag validation, contract registration, 0012 migration;
  - `tests/ingest/replay_helpers.py`.
- Recorded-fixture tests for BPstat and INE use a latest-only policy. Their recorded portal and
  table fixtures cover only those cuts; full draws are exercised live.
- Bundle CLI tests that must stay offline pass `--pinned-verifier`.
- Assertions on old sample sizes (50, 16, 12, 40, 200) are updated to the new census or
  latest counts.
- Full suite (`.venv-ci/bin/python -m pytest tests/ingest -m "not live" -q`): **1469 passed,
  7 deselected (live), 2 warnings in 443 s**.
- `ruff check ingest tests/ingest`: clean.
- `tests --ignore=tests/ingest` (runbook/docker contract): 74 passed.

## Declined / notes
- B-M2, B-M4, B-M6 and B-M7 were not touched, as scoped. The v1 sample draw is not
  re-implemented.
- **Deployment impact.**
  - 0012 runs on the production DB at the next deploy. It is an additive ALTER, plus an `event`
    table rebuild similar to 0011's.
  - Every group's verification becomes much larger: Eurostat and World Bank go from ~1.3k items
    to tens of thousands of `verification_item` rows per run. The DB and raw store grow
    accordingly. Evidence is stored once per response, deduplicated by object.
  - A live dry-run of each source before deploying is advisable. The World Bank census
    already found one real channel difference, now handled.
- **Manual bundle imports on f0nix** run their verifier live from the container.
  - If the verifier route is down there (the reason for capturing elsewhere), the import fails
    by design.
  - `--pinned-verifier` is the explicit, recorded, non-audit-grade fallback. Whether to accept it
    is an owner decision, documented in operations.md and manual-refresh.md.
- **INE `check`.** Before taking a cut, `check` now also asserts that the selection response's
  classes equal the indicator page's. This holds on all recorded selections.
- The project CLAUDE.md asks for GitNexus impact analysis. No GitNexus tools were available in
  this session, so blast radius was checked by grep:
  - `verify_run` / `run_with_refetch` callers: operations, cli, tests;
  - `add_verification` callers: verify, tests.
