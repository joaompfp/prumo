# Task 15 OECD - quality review fix round 1 (C1/C2/I1 + M2)

Date: 2026-11-12. Author: fix-implementer subagent (kimi-k3). Base e34c60f, branch
pipeline-rebuild, /home/joao/projects/prumo-pipeline. Scope per dispatch: fix the three
blocking live-test defects from task-15-quality-review.md (C1 endpoint min/max, C2 empty
quarantine, I1 overclaimed archive fidelity), add non-network regressions, restore the real
archived http_status (never hardcode 200), and normalize ONLY Task-15-newly-authored em-dashes
(M2). Production code untouched; semantics/behaviour of adapters unchanged. No HTTP in this
dispatch; the controller re-runs the live gate.

## Results

- Tests: targeted OECD scope `tests/ingest/test_verifier_oecd.py test_source_oecd.py
  test_registry_oecd_units.py` = **107 passed, 1 live deselected in 14.5 s** (104 pre-existing
  targeted + 3 new regression tests; was 140 passed in the review's broader target set, same
  pass rate). No full-suite run, no live run, no HTTP, per dispatch.
- Ruff: clean on every OECD-authored Python file. (One pre-existing F401 in
  test_verifier_eurostat.py is untouched and out of scope.)
- GitNexus: impact on `test_live_run_with_refetch_all_six_verified_and_served_zero`
  (-r /home/joao/projects/prumo-pipeline, --include-tests): **LOW, 0 upstream, 0 processes**;
  index sits at 5d27624 (stale vs e34c60f; tests-only edit). detect-changes before commit 1:
  LOW, 0 affected processes. Only the three review-flagged assertions and their helpers
  changed; no existing behaviour-bearing production symbol was edited.

## Commits (author kimi-k3-subagent <noreply@local>, no push)

1. `4b95bb1` test(ingest): OECD live gate whole-archive fidelity + offline regressions
   (Task 15 quality fix 1 C1/C2/I1) - 1 file: tests/ingest/test_verifier_oecd.py
   (+153/-17).
2. `4d178da` style: normalize em-dashes to hyphens in Task 15 authored prose (Task 15
   quality fix 1 M2); publisher evidence bytes untouched - 12 files, +56/-56,
   punctuation only.

Controller-owned files (HANDOFF.md modification by controller, brief/discovery/spec/quality
review reports, evidence dir) were NOT staged or touched; the live-test failure found by the
controller at its 51.577 s live run is exactly the C1/C2 pair fixed here.

## C1 - live test asserted SQL MIN/MAX against emission-row endpoints

Fix (live test): `(lo, hi)` now compares against `(min, max)` over ALL parsed
`row.period_raw` of the freshly re-parsed archive, never `rows[0]`/`rows[-1]`. RED proof on
the six genuine archived fixtures (offline parse, byte-identical to discovery items 1-11
odd): the old endpoint pair fails on all six, exactly the review's table - e.g. cli first
2026-02/last 2026-01 vs min 2025-10/max 2026-10. GREEN: new regression
`test_whole_archive_compare_on_unsorted_genuine_fixtures` pins the unsorted emission shape
(`(min, max) != (first, last)` on cli; at least one series unsorted, all periods unique) and
passes the whole-archive comparison offline.

## C2 - empty quarantine must equal [], never a 0-count entry

Fix: new helper `_expected_quarantine(expected)` maps only reasons with count > 0; a complete
archive expects `{}` (SQL GROUP BY over an empty quarantine set returns `[]`). The live
assertion is now `sorted(quar) == sorted(_expected_quarantine(expected).items())`. RED proof:
on the genuine archive (0 nulls) the old expression produced `[('non_numeric', 0)] != []`.
Regressions: the unsorted-fixtures test asserts quarantine empty + `{}` expectation;
`test_quarantine_expectation_maps_only_positive_counts` uses ONE hand-made null (docstring
explicitly labelled SYNTHETIC - the real archived window holds zero missing cells) expecting
exactly `{"non_numeric": 1}`.

## I1 - overclaim made true: FULL DB == publisher-archive comparison

New test-local helper `_assert_db_matches_archive(db, run_id, expected, archive_ids)`:
set-compares EVERY stored `(series_id, period, value_text, status_flag, raw-response
position)` tuple of the run against the offline re-parse of the run's OWN archived publisher
bytes (all six series, no sampling), with duplicate-detection on both sides and provenance
via raw_fetch-id -> response-position mapping. The live docstring now states exactly this
coverage (was an overclaim per review). Regression
`test_full_compare_catches_tampered_unsampled_interior_value`: corrupts one UNSAMPLED,
non-extreme observation (value_text/value) in the DB of a clean verified offline run; counts,
endpoints and the 12-item sample would still pass, while the set comparison raises
(AssertionError "DB != publisher archive"). This is the assertion a live run could not rely
on before.

Also fixed at the same site: the collector replay now restores and asserts the ARCHIVED
`raw_fetch.http_status` (2xx) into each `RawResponse` via `_archive_responses` - the old code
hardcoded `status=200` with ok=1 standing in. All prior acceptance signals remain: all six
active series covered, `served == 0` under redistribution_ok=false, `verifs == [(12, 1)]`,
per-item CSV envelope offline replay unchanged, <=15 req/min / <=18 attempts / 150 s
deadline / retries=0 / max_attempts=1 all unchanged.

## M2 - em-dash normalization, Task-15-authored prose only

58 U+2014 normalized to plain hyphens, exactly the review's per-file counts: sources/oecd.py 7,
verifiers/oecd.py 4, core.yaml 4 + core.proposed.yaml 4 (OECD block lines only, both files
still byte-identical - cmp verified), licences-todo.md 2 (oecd row only), mappings-oecd.md 11,
oecd_fixtures.py 4, oecd_verifier_fixtures.py 1, test_registry_oecd_units.py 1,
test_source_oecd.py 4, test_verifier_oecd.py 4, task-15-source-implementation.md 12.
Preserved untouched: pre-task baseline em-dashes (core.yaml/proposed 7 lines incl.
PROVISIONAL header and BPstat/REN/DGEG/licence lines, licences-todo.md non-OECD rows), all
publisher evidence bytes (fixtures, discovery evidence, publisher quoted text incl. the INE
'Estatística - Portugal' en-dash), controller-authored handoff/brief/review reports (M1
discovery accounting stays with the controller), and non-OECD registry lines. No id, code,
unit, data, URL, flag or licence eligibility changed.

## Limits

No live run and no HTTP in this dispatch: C1/C2/I1 were proven deterministic on the genuine
archived bytes (RED above) and by new offline regressions (GREEN); the controller's fresh
f0nix acceptance re-run over the fixed live gate stays the final acceptance evidence. The
`_archive_responses` helper assumes the 6 collector raw_fetch rows for the run arrive in one
fetch order per dataset attempt (true for max_attempts=1 as bounded); a future multi-attempt
refetch would make each attempt its own run_id, which this helper already handles by scoping
on `dataset_run_id`.
