# Task 14 — FRED fix round 2: independent quality review (micro gate)

Date: 2026-11-12 · Reviewer: independent quality gate (round 2) · Range reviewed: `8bc06d4..6e867c7` on `pipeline-rebuild` (HEAD verified = 6e867c71bf57) · Prior gate: `task-14-fix-1-quality-review.md` = REQUEST_CHANGES, sole remaining P1 = params-branch strict-superset hole.

## VERDICT: APPROVED

The one remaining P1 from the round-1 quality review is fixed correctly, minimally, and provably. No new findings.

## What was independently verified (not self-reports)

1. **The production change is exactly one line** (`git diff 8bc06d4..6e867c7 -- ingest/sources/fred.py`, working tree confirmed clean for this file):
   `ingest/sources/fred.py:325` — `if set(params) > allowed or "series_id" not in params:` → `if not set(params) <= allowed or "series_id" not in params:`.
   Confirmed in the checked-out source. Line 343 (`if not set(q) <= allowed:`) confirms the URL-query side already used the same subset form — the two identity sides are now consistent, which was the P1. `allowed` resolves to `_OBS_PARAMS` for the `/fred/series/observations` endpoint (lines 317–319).
2. **Focused tests actually run here**: `pytest tests/ingest/test_source_fred.py -k "unreviewed" -q` → **5 passed, 48 deselected in 0.59s** (the 4 round-2 cases — 3 parametrized unknown keys on a genuine no-offset first page + the self-consistent `/window` smuggle — plus the round-1 URL-side regression selected by the same filter).
3. **Independent negative probes rerun against the real `_identify`** (own probe script, byte-genuine fixture `RawResponse` via `_obs()`, no network, no key):
   - First-page genuine params are `{file_type, limit, series_id}` (3 keys). With one unreviewed key (`observation_start`) the set has 4 keys: **old strict-superset check does NOT fire** (hole confirmed real), **new subset check fires**; the real function raises `ValueError: FRED observations archived params drifted`.
   - Genuine first page passes `_identify` cleanly → `obs | PALUMUSDM` (no over-tightening).
   - Truth table over the four shapes: new check stays silent on genuine first and second pages, fires on first-page+1-unknown and second-page+1-unknown — a strict generalisation of the old guard; every previously-rejected corpus is still rejected (fail-closed tightening only).
4. **Scope discipline**: diff contains only the 1-line production change, the appended round-2 test block, and the fix report. Verifier, registry, core, fixtures, live tests untouched. The round-2 `ValueError` message matches the round-1 URL-side contract tests that pin both directions.

## Disposition of prior items

- Round-1 P1 (params-branch inconsistency): **cleared** by the verified line-325 change + probes above.
- Original I1/I2 items: previously cleared; nothing in this range reopens them.
- Round-1 accepted minor (verifier interior absence / sampling): remains an accepted, documented minor; not re-scoped here per gate instructions.

## Residual risk

None identified. Subset is the strongest form of this identity guard; RED/GREEN evidence in the fix report is consistent with my own probe results. Controller's full suite runs independently; this gate does not close the task.

## Gate boundaries observed

No whole-project exploration, no network, no API-key reads, no implementation, no commits, no edits to HANDOFF/ledger/prior reviews. Owned artifact: this report only.
