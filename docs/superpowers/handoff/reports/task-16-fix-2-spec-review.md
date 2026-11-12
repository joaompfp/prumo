# Task 16 fix 2 — independent specification review (60e2469)

Reviewer: independent spec-review subagent. Scope: ONLY diff `5feb13f..60e2469` on
`pipeline-rebuild` (C1 summer Lisbon wall-time aux echo, M3 UTC default clock) and its
stated invariants. No broader audit, no network, no edits. Fixture manifest re-verified
locally; targeted test files only.

## Verdict: PASS

Every stated acceptance criterion verified against real evidence at `/home/joao/projects/prumo-pipeline`:

1. **C1 fix is correct and minimal.** `ingest/sources/eredes.py` and `ingest/verifiers/eredes.py`
   replace the false aux-echo-equals-UTC-`datahora` guard with `_wall_time_echo`/`_wall_cells`:
   genuine-string checks, canonical `YYYY-MM-DD` real-Gregorian date and `HH:MM` real time, and
   internal consistency (`date == ano-mes-dia/dia/mes/ano`). The UTC `datahora` is never equated
   with the local echo and no offset/DST is recomputed. Metadata now also fail-closes on the
   publisher-declared echo field types (text/text/text/date/text) — appropriate drift guard.
   Purposeful source/verifier rule duplication matches the verifier's independence contract.

2. **Exact original 288 tokens, 0 conversions.** Re-verified against
   `tests/ingest/fixtures/eredes/summer_window_json.body` and `summer_window_csv.body`:
   96 records × 3 fields, token sets byte-identical across both channels, every token matching
   the native grammar verbatim (`945304.0`, `410629.514`, `1369057.51` — trailing `.0` and float
   tails preserved as plain str via `parse_float=str`). sha256 and byte counts of both new
   fixture files match MANIFEST.json entries exactly. No value transformation, no zoneinfo,
   no aggregation in the diff.

3. **Period still datahora.** `RawRow.period_raw` is built solely from canonical UTC `datahora`
   (`_DATAHORA` fullmatch + real date + inside-requested-window guard `t_raw[:10] != day`,
   all unchanged). Summer regression asserts `period == "2026-04-01T23:45:00+00:00"` with
   native UTC ts unchanged and `value_text == "1369057.51"`, `status_flag is None`.

4. **Strict identity/date/header/duplicates maintained.** Source: strictly ascending/unique
   `datahora` guard intact (lines 383–385); new `test_parse_rejects_out_of_window_record` keeps
   real date-vs-window enforcement. Verifier: `EXPECTED_HEADER` check, 9-cell width check,
   `_PERIOD` fullmatch, duplicate-`datahora` (`ts in by_ts`) and window-bound guards all intact;
   new parametrized fail-closed tests cover non-canonical shape, unreal date, `dia ≠ date`,
   bad HH:MM. Tampered row still fails via the timestamp-duplicate guard.

5. **UTC default is aware, not host-local (M3).** `date.today()` →
   `datetime.now(timezone.utc).date()`; test monkeypatches the module `datetime` and asserts
   the tz argument is `timezone.utc`.

6. **Raw archive honest times.** MANIFEST.json addendum honestly distinguishes provenance:
   `summer_window_json` = unmodified controller raw_fetch id 2 bytes (sha256 confirmed equal to
   the archived fixture), `summer_window_csv` = one genuine `/exports/csv` fetch with real
   fetched_at/status/bytes; winter entries untouched. The genuine wall-time property is proven
   by the fixture itself: first record 00:00Z shows local 01:00; 23:45Z carries date 2026-04-02 /
   00:45; exactly 4 cross-midnight rows (23:00/23:15/23:30/23:45Z).

## Execution evidence

- `pytest tests/ingest/test_source_eredes.py tests/ingest/test_verifier_eredes.py
  tests/ingest/test_registry_eredes_units.py -q` → **88 passed**.
- Working tree dirt is exclusively controller-owned docs/handoff, untouched by the reviewed
  commits; reviewed diff is 10 files, 472+/32−.

## Findings

- None blocking. Minor note only: the new summer CSV set required one live fetch at archiving
  time (honestly declared in the addendum); the fix itself and this review remain offline.
- M1/M2 remain documented minors, untouched — consistent with scope.

Controller owns closure.
