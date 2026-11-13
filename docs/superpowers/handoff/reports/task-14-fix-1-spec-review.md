# Task 14 fix round 1 — independent scoped SPEC re-review (I1/I2/M2 only)

Reviewer: independent spec-review subagent. Scope bound honored: read only the diff
`7b93ab8..8bc06d4` (`ingest/sources/fred.py`, `tests/ingest/test_source_fred.py`,
`tests/ingest/test_live_fred.py`), the fix-round-1 report, and two grep probes (reviewed-key
sets, key-hygiene ordering). Did NOT re-read the plan, the original corpus, or the 48
fixtures; no code changes, network, commits, or handoff writes. Controller owns the quality
scoped pass and the full-suite run (already running); this is the spec gate only.

**Verdict: PASS** — every required I1/I2/M2 item is present in the actual diff with the
required semantics (file/line checks below). Minors noted, none blocking. Task 14 itself is
NOT declared complete by this review.

## I1 — complete/stable FRED archives: verified in `ingest/sources/fred.py`

- **One authoritative `_PageLedger`** (new class, after line 255): first page pins
  `(count, (limit, realtime, extent))`; later pages must match count and identity exactly
  (count drift and limit/realtime/extent drift each raise); offsets must be contiguous from 0
  (`expected_offset` starts 0, mismatch raises); `assert_complete()` fails when no obs page was
  archived or `accumulated != declared count` (missing tail / partial / truncated). Consumed by
  BOTH `fetch()` (mid-stream, raises at the drifting page) and `parse()` (per-code ledger +
  `assert_complete` per archive).
- **Strict ascending dates** across the whole archive in `parse()` (`d <= last_date` raises) —
  subsumes cross-page duplicates; per-spec duplicate-period check retained.
- **Strict url/query identity** in `_identify`: probed — `_META_PARAMS = {series_id, file_type}`,
  `_OBS_PARAMS = {+ limit, offset}` (lines 89-90; no restriction keys admissible). URL query
  keys must be a subset and must exist in AND match params exactly; duplicated query keys
  rejected via `parse_qsl` pair-count (dict view would hide them); params `file_type` must be
  the literal `json`; `limit`/`offset` must be canonical ASCII decimals (`v == str(int(v))`,
  so `007`/`+7` rejected); `api_key` in archived params/URL rejected at line 312, strictly
  BEFORE any `params!r` message (line 325).
- **Extent containment, not endpoint equality**: `_observations` validates
  `observation_start/end` as Gregorian, rejects inverted extent, asserts every row date within
  `[obs_start, obs_end]`; no first/last-row == envelope equality anywhere. Realtime envelope
  dates now `_date()`-validated (were `_str`-only).
- **Old contract preserved**: API error shape (`error_code`) still rejected; top-key drift sets
  unchanged; value STRING-token check, `MISSING = "."` normal-token path, `units`/`file_type`/
  `order_by`/`sort_order` envelope tuple check, month-first day==01 gate, per-page
  `offset + rows > count` truncation guard, metadata unit == registry unit, and
  `response_index` provenance all unchanged. `_strip_key` wire-only hygiene untouched (absent
  from the diff). Happy-path fixtures/tests only extended (+268 lines, zero deletions in test
  file), so the genuine 561-count / 417-row / 144-`.` archive still parses; a new multi-page
  fetch happy test asserts byte-equality with the single-page archive.

Regression coverage (tests added, all mutations built in-test from genuine bytes): truncated
archive with intact count, missing tail page, metadata-only series, rows outside extent (both
bounds), cross-page count grow + extent narrow, unknown/duplicated/mismatched URL query keys,
non-canonical limit/offset + `file_type=JSON` literals, mid-pagination realtime/extent/limit
drift via a re-slicing HTTP double that also asserts the wire request DOES carry the api_key,
and an end-to-end pipeline refusal (failed state, zero rows written, evidence kept).

## I2 — canonical ASCII Gregorian dates: verified

- `_DATE`/`_LAST_UPDATED` digit classes switched `\d` → `[0-9]` (Unicode aliases rejected).
- `_date()` now additionally validates real Gregorian existence via `datetime.date(...)`
  (year 0000, Feb 30, month 13 raise) and returns the original text verbatim — no
  normalization, no alias repair. Applied to row dates (month-first), envelope extent +
  realtime bounds, and metadata dates (unchanged caller). Tests pin appended + in-place
  Arabic-Indic aliases, year-0000 row, `9999-02-30`/`0000-01-01` envelope bounds, unicode
  realtime and `last_updated`.
- No value-layer conversion added: `1e5`-style tokens still pass the source as strings for
  downstream quarantine (per the report's P5 re-verification); no rounding, no new units.

## M2 — live test unpinned and bounded: verified in `tests/ingest/test_live_fred.py`

- Frozen `n == 417`, `("1992-01", "2026-09")`, `12*144` all REMOVED. Per-series count/range,
  metadata `observation_start/end`[:7] range, and the `non_numeric` quarantine total are now
  derived from the run's OWN archived publisher bytes (raw-store responses re-parsed offline
  via `FredSource.parse`, no HTTP), asserted exactly against the DB, with nonempty-values and
  canonical `YYYY-MM` period assertions.
- Kept pinned: all-12 active series set, `state == "verified"`, `served == 0` (licence gate),
  `run_with_refetch(..., size=120, max_attempts=1)`, `verifs == [(120, 1)]`, and the full
  offline value+unit HTML evidence replay tightened to `replayed == len(rows) == 120`.
- `RequestsHttp(throttle_rps=1.0, timeout=120.0, retries=0)` explicit; module docstring states
  the 120 s bound is PER-REQUEST and that NO whole-phase deadline is implemented (f0nix
  acceptance cap is the phase bound) — matches the "no fake deadline" requirement.
- No raw key anywhere in test source: key comes from `FRED_API_KEY` env only (skip without it);
  `FredSource(api_key=key)` keeps wire-only hygiene; offline re-parse reuses it without
  leaking (key never rendered; `_identify` rejects archived credentials).

## Grounding

- Independent re-run of the touched unit file: `pytest tests/ingest/test_source_fred.py -q`
  → **49 passed in 8.12 s** (matches the fix report's 49/49 claim; controller's full-suite
  run is separate). Live test not run here (no key/network — by design; controller owns the
  f0nix live re-run). Diff stat confirmed only `ingest/sources/fred.py` + the two test files +
  the fix report changed; registry/verifier/core/rawstore/fixtures untouched.

## Minors (observed, not inflated, non-blocking)

1. `_PageLedger.add` returns `expected_offset >= count`; exactness is enforced indirectly
   (per-page `offset + rows > count` bound + count pinning make overrun unreachable), so
   semantics are correct — `==` would merely be more literal.
2. Parse would accept a zero-row mid-archive page (contiguity preserved); harmless because
   count reconciliation in `assert_complete` still governs completeness, and fetch retains the
   no-progress guard.
3. Report claim spot-check consistent: docstring fail-closed list, red/green test inventory,
   and the "count drift was already terminal pre-fix" note all match the diff as read.

## Residual risks carried from the review (unchanged, controller-tracked)

- M1 verifier interior-row absence-only tamper: accepted residual; verifier untouched here.
- Extent contract is containment-only by design (genuine broad 1600..9999 envelope); silent
  window loss rests on count reconciliation + strict url/params identity + downstream sampling.
- Live f0nix re-run (48 calls / 180 s cap) remains the acceptance gate for Task 14 completion.
