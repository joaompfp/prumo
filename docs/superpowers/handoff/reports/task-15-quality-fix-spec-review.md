# Task 15 OECD - quality fix 1 SPEC re-review (scoped, independent)

- Date: 2026-11-12, f3nix. Reviewer: independent subagent (read-only spec gate).
- Scope: diff `e34c60f..decc048` ONLY (3 commits: 4b95bb1 tests, 4d178da punctuation, decc048
  fix report). Verifies the C1/C2/I1 quality fixes claimed in
  `docs/superpowers/handoff/reports/task-15-quality-fix-1.md` against spec, after the full-CODE
  PASS at e34c60f (`task-15-final-spec-review.md`). No live run, no full suite, no HTTP -
  parent owns those. This is a spec gate; a separate quality re-review follows.

## Verdict: PASS

## What the diff changes

- `tests/ingest/test_verifier_oecd.py` (+178/-~40): the only behavioural change. Adds shared
  helpers `_archive_responses`, `_expected_quarantine`, `_assert_db_matches_archive`, three
  offline regressions, and rewrites the live test's expectations to use them.
- `ingest/sources/oecd.py`, `ingest/verifiers/oecd.py`, `registry/core.yaml`,
  `registry/core.proposed.yaml`, `registry/licences-todo.md`, `registry/mappings-oecd.md`,
  4 test files' docstrings: em-dash to hyphen punctuation ONLY (4d178da). No logic, no flag,
  no licence-eligibility change: `redistribution_ok: false`, `licence_url`, `attribution`,
  `verifiable` and all series metadata identical; only the dash glyph in the licence prose.
- Publisher evidence bytes untouched: `git diff e34c60f..decc048 -- tests/ingest/fixtures/
  docs/superpowers/handoff/evidence/` is EMPTY (fixtures remain sha256-pinned by MANIFEST.json).

## C1/C2/I1 fix verification (spec points)

1. Archived http_status restored (I1 provenance): `_archive_responses` SELECTs `http_status`
   from `raw_fetch`, asserts `isinstance(status, int) and 200 <= status < 300` (a NULL or
   non-2xx fails, never papered over), and builds `RawResponse(status=status)` - the old code
   hardcoded `status=200`. Real status also re-validated by `OecdSource.parse`
   (ingest/sources/oecd.py:664 raises unless 2xx). OK.
2. FULL observation tuples from fresh archive: `_assert_db_matches_archive` set-compares EVERY
   stored (series_id, period, value_text, status_flag, raw-response position) against an
   offline re-parse of the run's own archived bytes; `raw_fetch_id` is mapped to fetch-position
   via archive ids (ORDER BY id), so provenance position is compared, not just values. Row
   loss, duplicates (`len(got) == len(got_rows)`), silent collisions (`len(want) == total`) and
   non-collector linkage all raise. DB schema confirmed: `observation(series_id, period,
   value_text, status_flag, raw_fetch_id, ...)`. OK.
3. Unsorted periods handled (C1): regression asserts a genuine fixture arrives unsorted
   (`ps != sorted(ps)`) and that CLI (min,max) != (first,last) - non-vacuous; live test now
   compares SQL MIN/MAX to `min/max` over ALL archived periods, never emission endpoints. OK.
4. Empty quarantine (C2): `_expected_quarantine` returns {} when zero nulls (SQL GROUP BY over
   an empty set returns []), asserted both offline (quarantine COUNT == 0 AND expectation {})
   and live (`sorted(quar) == sorted(_expected_quarantine(expected).items())`). OK.
5. Single labelled synthetic null: `test_quarantine_expectation_maps_only_positive_counts`
   hand-makes ONE null via `replace(r, value_raw=None)` in memory (docstring explicitly labels
   it synthetic; genuine window holds none), expects exactly {non_numeric: 1}; zero nulls -> {}.
   No mutated bytes stored as evidence anywhere. OK.
6. Unsampled tamper detected (I1): corrupts one UNSAMPLED, non-extreme row's value_text/value
   in the DB (victims derived from verification_item vs min/max; asserts non-empty) and
   expects AssertionError matching "archive" - counts, endpoints and the 12-item sample would
   all still pass. OK.

## Production behavior unchanged claim

Verified: the entire non-test diff is dash-glyph punctuation in comments/docstrings/licence
prose. Registry licence posture flag (`redistribution_ok: false`) and eligibility semantics
byte-identical modulo dashes; no code path touched. Original publisher bodies untouched (above).

## Tests run (bounded, no HTTP, no full suite)

- `.venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py -q -k "whole_archive or
  quarantine_expectation or tampered_unsampled"` -> 3 passed, 48 deselected (1.96 s).
- `.venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py
  tests/ingest/test_source_oecd.py tests/ingest/test_registry_oecd_units.py -q` -> 107 passed,
  1 deselected (14.12 s; the deselected is the @pytest.mark.live test, parent-run).

## Nits (non-blocking, no change requested)

- `_assert_db_matches_archive` uses `row.flag_raw or "normal"` on the expected side; for OECD
  all published flags are OBS_STATUS=A->'normal', so a future None flag would surface as a
  mismatch against the DB's NULL rather than being masked. Acceptable for this source.
- Live test kept its acceptance signals (`attempts <= 18`, `elapsed <= 150.0`, served == 0,
  verifs == [(12, 1)]) - unchanged and consistent with the e34c60f PASS.

No defects found in scope. Spec gate PASSED; ready for the separate quality re-review and the
parent's fresh full suite/live run.
