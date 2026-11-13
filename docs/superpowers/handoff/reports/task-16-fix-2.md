# Task 16 fix 2 report: E-REDES summer local-wall-time rejection (C1) + UTC default (M3)

Branch `pipeline-rebuild` at 5feb13f, worktree /home/joao/projects/prumo-pipeline. Scoped fix
implementer for the controller live-gate finding C1: the genuine April 2026 window failed
validation (`failed-validation`, 0 observations in the controller DB) because the source and
verifier asserted the `dia/mes/ano/date/time` echo columns equal the UTC `datahora`.

## Root cause (reproduced before editing)

The publisher's `datahora` is native UTC, but `dia/mes/ano/date/time` are LISBON-LOCAL wall
time (WEST = UTC+1 in summer). The withdrawn assumption "echo == UTC parts" holds in winter
(2026-11 fixture) and fails in summer. TDD reproduction with the unmodified controller-archive
bytes (raw_fetch id 2) against the pre-fix code:

```
C1-REPRODUCED: E-REDES record's dia/mes/ano/date/time echo columns disagree with datahora
'2026-04-01T00:00:00+00:00'
```

Genuine evidence (controller live run 2026-11-12): first record `datahora
2026-04-01T00:00:00+00:00` with `time 01:00` / `date 2026-04-01`; last `2026-04-01T23:45:00
+00:00` with `date 2026-04-02` / `time 00:45`. 4 of 96 records cross local midnight.

## Evidence archived (fixtures, unmodified bytes)

- `tests/ingest/fixtures/eredes/summer_window_json.body` — exact original bytes of the f0nix
  controller live-gate run (raw_fetch id 2), COPIED from its raw store, not re-fetched:
  status 200, fetched_at 2026-11-12T19:03:10.859621+00:00, sha256
  ef0a13d7ae66e8966adc1f19127b7975d16b3a7138a117365a5381bb30c4b9ad, 17543 B.
- `tests/ingest/fixtures/eredes/summer_window_csv.body` — ONE additional network request from
  f0nix egress (urllib, in-memory, no installs/files; 10 s timeout, 0 retries, 0.912 s elapsed,
  well inside the 20 s deadline): the same UTC window via /exports/csv. Status 200,
  fetched_at 2026-11-12T19:11:27.382428+00:00, sha256
  24bb889cfb62b7646ab00703f992c602c682e7495099b64a2be94c61b0a74992, 8536 B (< 200 KB).
- MANIFEST.json: existing winter entries untouched; new sets carry their own honest
  url/params/status/fetched_at/sha256/bytes + an addendum. Metadata response is the shared
  genuine `metadata.body` (byte-identical in the controller run, sha 396af188…).
- Cross-check at archiving time: all 96 rows x 3 fields (288 tokens) Decimal-exact between
  channels, plain tokens preserved (`410629.514`, trailing-`.0` floats); all 9 columns
  byte-identical.

## Fix (minimal; no timestamp/value transformation, no aggregation, no zoneinfo)

- `datahora` remains the SOLE authoritative period: canonical UTC quarter-hour spelling, real
  Gregorian date, inside the requested window, strictly ascending/unique (unchanged guards,
  still tested).
- Aux wall-time columns: remain archived/validated as genuine JSON strings with canonical
  shapes (`YYYY-MM-DD` real Gregorian date, `HH:MM` real time) and internal consistency
  (`date == ano-mes-dia`), on both source and (duplicated on purpose) verifier. They are NEVER
  equated with the UTC datahora and no DST/offset is inferred. Metadata now also asserts the
  publisher-declared types for the echo fields (text/text/text/date/text) — fail closed on
  drift.
- M3: default window clock `date.today()` -> `datetime.now(timezone.utc).date()` in
  EredesSource (contract is UTC; no other window change).
- M1 (duplicate keys) / M2 (offline whole-window coverage) remain documented minors, untouched.

## Tests (changed semantics, not blind deletion)

- Replaced `test_parse_rejects_date_column_inconsistent_with_datahora` with parametrized
  `test_parse_rejects_malformed_aux_wall_time_echo` (bad shape, unreal date 2026-11-31,
  non-string cell, bad HH:MM, dia/ano disagreeing with date) + new
  `test_parse_rejects_out_of_window_record` (bad actual date vs requested window still fails).
- Verifier: new parametrized `test_verifier_aux_wall_time_cells_fail_closed`; the tampered-row
  test comment updated (it still fails closed via the timestamp-duplicate guard).
- New genuine-summer regressions (source): fixture property proof (01:00 at 00:00 UTC; 4
  midnight crossers), exact-token parse with 5 named samples, validate() to 96 canonical UTC
  observations (`1369057.51` at 2026-04-01T23:45:00+00:00, native UTC ts unchanged).
- New genuine-summer regressions (verifier): 5 named CSV cases read from the wall-time export;
  full registered `run_with_refetch` on the summer fixture ends `verified` with ALL 288
  observations served under CC BY 4.0 and every sampled item's evidence replayed offline from
  the raw store (no HTTP).
- M3 clock test with a stubbed UTC datetime.

## Verification results (all real runs)

- `.venv-ci/bin/python -m pytest tests/ingest/test_source_eredes.py tests/ingest/test_verifier_eredes.py
  tests/ingest/test_registry_eredes_units.py -q` -> 88 passed.
- `.venv-ci/bin/python -m pytest tests/ingest/test_independence.py -q` -> 13 passed.
- `.venv-ci/bin/ruff check <6 changed .py files>` -> All checks passed.
- GitNexus (index refreshed to 5feb13f before editing): impact EredesSource LOW/0,
  EredesVerifier LOW/1; `detect-changes` pre-commit maps only the scoped symbols/flows
  (check/fetch/parse/_assert_metadata), 10 files incl. controller docs (NOT staged here).

## Scope notes

No migration/db/models/core changes; no retry/budget changes; no branch merge/deploy/push.
Controller-owned handoff/ledger/plan docs and untracked discovery evidence were not staged.
Task 16 acceptance remains controller-owned (independent spec + quality reviews, live gate).
