# Task 14 — Fix round 2 SPEC re-review (independent, read-only)

Date: 2026-11-12 · Reviewer: independent spec gate (read-only) · Diffs reviewed: `8bc06d4..6e867c7`
· Branch: pipeline-rebuild · Prior: round-1 quality review REQUEST_CHANGES (superset operator)

**Verdict: PASS (spec level).** Quality re-review is a separate downstream gate and is not
unblocked/declared here. Task 14 is NOT declared complete by this report.

## What was reviewed (and ONLY what was reviewed)

- `git diff 8bc06d4..6e867c7` (single commit `6e867c7`): 1 production line in
  `ingest/sources/fred.py`, 45-line round-2 test block appended to
  `tests/ingest/test_source_fred.py`, plus the round-2 fix report — nothing else.
- Focused test run of the FRED source battery (see below).
- No implementation, no edits outside this report, no network, no key material read,
  no commits, no handoff/HANDOFF/ledger changes.

## Spec checks

| # | Check | Result |
|---|-------|--------|
| 1 | Production change is exactly one line: `set(params) > allowed` → `not set(params) <= allowed` in `_identify` (fred.py:325) | PASS — diff shows 1 insertion / 1 deletion, single line |
| 2 | Wire credential guard (netloc == `api.stlouisfed.org`) still precedes the params guard | PASS — unchanged in diff context above the edited line |
| 3 | `series_id`-presence clause and `file_type` literal `'json'` guard unchanged | PASS — both visible unchanged in diff context |
| 4 | Strict URL-query identity (`not set(q) <= allowed`) and the reviewed allowed set (`{"series_id","file_type","limit","offset"}`) untouched | PASS — no other hunks in fred.py |
| 5 | Page-1 (no `offset`) unknown-param rejection: parametrized `observation_start`/`frequency`/`units` on genuine PALUMUSDM first page, asserting `ValueError` "archived params drifted" | PASS — test present, URL/body/reviewed params byte-genuine so only the params guard can fire |
| 6 | Self-consistent window case: smuggled `observation_start=2010-01-01` with body mutated in-test to agree (201 monthly rows, `count` redeclared 201), so truncation/count/extent/limit-offset guards stay silent | PASS — test present, in-test mutation via `_mut_obs`, fixture originals untouched, 201-row window pinned by assertion |
| 7 | Regression: full FRED source battery still green | PASS — `.venv-ci/bin/python -m pytest tests/ingest/test_source_fred.py -q` → **53 passed in 8.19s** (incl. the 4 new cases and the round-1 URL-side test) |

## Notes / residual observations (non-blocking)

- The subset form is a strict fail-closed tightening: any key set rejected before contains an
  unreviewed key and is still rejected; previously accepted corpora are unaffected within the
  reviewed contract.
- Symmetry between the params side and the URL-query side (both now subset) restores the
  invariant the round-1 review flagged.
- Runtime timing variance vs. the fix report's full 293-test battery is expected; this gate
  ran the focused file only, per scope.

## Scope of this PASS

This PASS covers spec conformance of commit `6e867c7` only. It permits the separate
independent quality review to proceed. It does NOT mark Task 14 complete, does not review
the fixture corpus or the wider plan, and makes no claim on any file outside the three
touched by the diff.
