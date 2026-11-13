# Task 15 source fix 1 - key pin count and semantic dimension identity (F1/F2/F3)

Date: 2026-11-12. Implementer: scoped fix subagent (kimi-k3) on pipeline-rebuild,
/home/joao/projects/prumo-pipeline. Base: 5d27624 (post Part B). Mandatory fix round for the
Part A spec review's one Important (F1) and two Minor (F2, F3) findings in
reports/task-15-source-spec-review.md, per controller dispatch. Scope owned: ONLY
ingest/sources/oecd.py, tests/ingest/test_source_oecd.py and this report. No verifier,
registry, other test, handoff, ledger or vault file touched. A parallel read-only verifier
spec reviewer works on Part B only and is unaffected.

## What was wrong (from the review, confirmed by re-probe)

- F1 (Important, latent): `_payload` iterated the payload series-key segments against the
  registry key pins but never checked the two lengths are equal, so a 10-pin registry
  native_code parsed against a real 9-dimension payload with the 10th pin silently
  unasserted (fail-open identity class).
- F2 (Minor): a registry key SHORTER than the payload dimension count escaped the adapter's
  error contract as a raw IndexError (still fail closed, wrong exception type).
- F3 (Minor): series dimension ids were shape-checked only; renaming MEASURE to MEASUREE in
  the payload still parsed (defense-in-depth gap against a silent DSD revision).

## Fix (minimal, evidence-grounded)

Genuine fixture evidence (tests/ingest/fixtures/oecd/, sha256-pinned, byte-identical to
discovery items 1,3,5,7,9,11): all three flows carry exactly 9 series dimensions with a
specific keyPosition id order - the two DSD_STES flows (DF_CLI, DF_BTS) share REF_AREA, FREQ,
MEASURE, UNIT_MEASURE, ACTIVITY, ADJUSTMENT, TRANSFORMATION, TIME_HORIZ, METHODOLOGY;
DSD_LFS@DF_IALFS_UNE_M uses REF_AREA, MEASURE, UNIT_MEASURE, TRANSFORMATION, ADJUSTMENT, SEX,
AGE, ACTIVITY, FREQ.

- ingest/sources/oecd.py:
  - `_KEY_SEGMENTS = 9` plus `_SERIES_DIM_IDS` (per-dataflow expected id sequence in
    keyPosition order).
  - `parse_native_code` now requires exactly 9 canonical key segments: wrong pin counts fail
    closed BEFORE any HTTP request (fetch calls `_native_code`) and in offline parsing
    (`_identify`).
  - `_payload` asserts (a) request key pin count == payload series dimension count (kills F1
    extra-pin and F2 short-key IndexError at the semantic site) and (b) the payload series
    dimension ids, by keyPosition, equal the reviewed sequence for the request dataflow -
    renamed (MEASUREE), duplicated, repositioned or unreviewed-flow ids all raise ValueError.
  - Module docstring updated to state the new invariants.
- UNSORTED TIME_PERIOD index mapping and real parent dimension values are untouched and still
  supported (all 77 observations of the six genuine fixtures decode exactly as before).

## TDD evidence

RED (pre-fix, 6 new tests all fail):
`.venv-ci/bin/python -m pytest tests/ingest/test_source_oecd.py -q -k "wrong_pin_count or
archived_url_with_wrong or payload_asserts_key or dimension_id_rename or
dimension_id_duplicate or dimension_position_drift"` -> 6 failed, 43 deselected
(DID NOT RAISE / wrong-exception-class failures exactly as the review predicted: the 10-pin
key parsed silently, the short key raised raw IndexError).

New regression tests (tests/ingest/test_source_oecd.py):
- test_registry_key_with_wrong_pin_count_is_rejected_before_any_http (10-pin and 8-pin keys
  raised by the grammar; fetch over a 10-pin spec raises with ZERO HTTP calls made)
- test_archived_url_with_wrong_pin_count_fails_closed_offline (archived 10-pin URL identity)
- test_payload_asserts_key_pin_count_against_dimension_count (direct _payload: extra pin,
  short pin, unreviewed dataflow - the last with the fixture dataflow URN mutated to match so
  the probe reaches the new guard)
- test_series_dimension_id_rename_fails_closed (MEASURE -> MEASUREE on BOTH the STES CLI and
  the LFS unemployment fixtures)
- test_series_dimension_id_duplicate_fails_closed (FREQ id duplicated as MEASURE)
- test_series_dimension_position_drift_fails_closed (REF_AREA <-> FREQ keyPosition swap)

GREEN (post-fix), targeted source + registry + verifier suites only, per dispatch:
`.venv-ci/bin/python -m pytest tests/ingest/test_source_oecd.py
tests/ingest/test_registry_oecd_units.py tests/ingest/test_verifier_oecd.py -q`
-> 89 passed, 1 deselected in 10.57 s (49 source + 8 registry + 32 verifier; the deselected
one is the live-marked test). Ruff: `All checks passed!` on both edited Python files.
The full 230 s suite was NOT rerun (dispatch scoped this fix to the targeted suites;
controller re-runs the full gate at acceptance).

## GitNexus impact (pre-edit, per preflight)

Index refreshed on this exact worktree (`gitnexus analyze --skip-agents-md --name
prumo-pipeline`; 8,030 nodes/13,054 edges; scope extraction warning on
ingest/sources/oecd.py means the graph is partial for this file, so grep cross-checked).
Impact on modified symbols - `parse_native_code`: LOW, 0 direct upstream, 0 processes;
`_payload`: LOW, 0 direct, 0 processes. Real callers per grep: the two OECD test modules and
in-module `_native_code`/`_identify`/`OecdSource.parse` only; no external production callers
(new adapter). No HIGH/CRITICAL finding.

## Commits

Single scoped commit on pipeline-rebuild (paths: ingest/sources/oecd.py,
tests/ingest/test_source_oecd.py,
docs/superpowers/handoff/reports/task-15-source-fix-1.md), hash reported to the controller in
the session summary. No push, no merge, no deploy; truthful authorship, no Claude trailers.

## Limitations

- The 9-pin grammar is a reviewed constant of the three current flows, not a generic SDMX
  rule: admitting a future flow with a different dimension count must update `_KEY_SEGMENTS`
  and `_SERIES_DIM_IDS` with genuine fixture evidence and independent review (fail-closed by
  default until then).
- `_payload`'s pin-count == dimension-count check is now redundant in practice for the
  reviewed flows (parse_native_code pins 9 and every reviewed dataflow has 9 series dims); it
  is kept as the defense-in-depth assertion the review asked for.
- The OBS_STATUS fail-closed posture is unchanged: only 'A' exists in evidence; any future
  unseen status still fails closed (codelist not enumerable, discovery item 13).
- Source-phase preflight gate noted by the controller (full 6-history HTTP 200 parse, all
  status A) is unaffected: no live fetch was performed and fixture bytes are unchanged.
