# Task 17 live-fix — narrow spec re-review (SCOPED, READ-ONLY)

2026-11-12 · reviewer: independent spec gate · target: `pipeline-rebuild` @ `d05e24b`,
diff `6cf6777..d05e24b` · artifacts reviewed: `task-17-live-fix.md` + changed tests/code
only · Task 17 is NOT closed by this review; the pre-existing legacy cleanup / AGENTS.md
tool-gate remains an owner-approval gate outside this review.

**Verdict: PASS** — the diff implements exactly the approved minimal contract, the fixtures
are genuine receipts verified from their bytes, and the targeted tests are green.

## Review constraints honored

READ-ONLY; no HTTP calls, no full test suite, no code deletion, no edits other than this
report. Targeted tests only: `test_task17_live_fix.py`, `test_source_eredes.py`,
`test_verifier_eredes.py` via `.venv-ci` pytest.

## Contract item-by-item

| Approved contract clause | Verdict | Evidence |
|---|---|---|
| Canonical dup RawRows passed **unchanged** to existing `validate()` `duplicate_period`; BOTH copies quarantined, no copy chosen | PASS | Source diff replaces the `t_raw <= prev` RAISE with strict `<` only; equal-stamp rows reach validate() untouched. `test_validator_quarantines_every_duplicate_copy_and_keeps_all_other_cells`: 89 obs, 8 rejections all `duplicate_period`, obs disjoint from the 4 dup stamps. Registered-run test asserts quarantine `n==2` per (series, stamp) and 0 observations at quarantined periods. |
| Source raises ONLY on strict backward ordering | PASS | `if prev is not None and t_raw < prev: raise ("not strictly ascending")`. `test_nov1_out_of_order_still_fails_closed` + new `test_parse_rejects_out_of_order_records` (swapped unique rows) both green; out-of-order, quoted-number, HTML guards re-asserted unchanged ON the Nov 1 fixture. |
| Verifier: duplicated CSV period → ambiguous → `observed_text=None`; unaffected day rows still verifiable | PASS | Per-day `ambiguous` set in `EredesVerifier.check`; item lookup returns None when period ∈ ambiguous. `test_verifier_ambiguous_stamps_not_found_unaffected_still_verified`: all 4 stamps × 3 series → None with evidence intact; 5 named unique stamps verify with exact tokens; absent 23:45 → None via same path. |
| No last-row overwrite, no whole-day abort | PASS | On the 2nd occurrence `by_ts.pop(ts, None)` retracts the first copy and `continue` stores neither; 3rd+ occurrences hit `ts in ambiguous`. No raise on the dup path — the day file completes. `test_verifier_duplicate_timestamp_is_ambiguous_never_served` (created dup) and the tampered-window test both confirm unaffected stamps still serve. |
| Exact CSV metadata evidence and registration independence unchanged | PASS | `_envelope([csv, meta])` untouched; test asserts archived csv record body == fixture bytes, status 200. Verifier diff adds **no imports** — no collector code referenced; duplicated constants preserved; independence/registration tests in the touched files pass. Manifest addendum is append-only (no previous set rewritten — confirmed in diff). |

## Fixture genuineness (derived from bytes, independently of the tests)

- `nov1_window_json.body`: sha256 == manifest `6bc99c93…`, len == 17244 B, status 200,
  `total_count` 97 == results length == 89 unique stamps + 4 doubled stamps
  (01:00/01:15/01:30/01:45 UTC), each pair carrying genuinely **conflicting** dgm/pre/total
  tokens (e.g. dgm 980304.0 vs 1020794.0 at 01:00 — matches report). Receipt block (URL,
  params, `fetched_at_utc` 2026-11-12T21:38:32Z, raw_fetch id 216 provenance note) present
  and verbatim-copied per manifest note; not independently re-checkable against the run DB
  (out of scope, no DB access in this review).
- `nov1_window_csv.body`: sha256 == manifest `b5c7e77d…`, 8143 B, status 200, UTF-8 BOM /
  `;` / CRLF, 97 data rows, header starts `datahora`, the SAME 4 doubled stamps, stamp-set
  identical to the JSON channel. Capture facts (10 s timeout, 0 retries, 0.411 s, 200 KB
  cap, fetched 2026-11-12T21:47:14Z) documented in the manifest.
- Test-side counts are DERIVED from the bytes (`_derive_counts`), not invented literals;
  89×3 = 267 written / served and 8×3 = 24 quarantined asserted via those derivations.

## Test execution (targeted, this review)

`pytest tests/ingest/test_task17_live_fix.py tests/ingest/test_source_eredes.py
tests/ingest/test_verifier_eredes.py -q` → **92 passed** (7.17 s), including all 8 new
live-fix tests and the strengthened (not deleted) prior expectations.

## Reservations (do not block PASS)

- The report's full-suite claim (`tests/ingest/` = 1331 passed, 7 deselected) was NOT
  re-run — the review cap forbids the full suite. Targeted files covering every changed
  behavior are green.
- Live-run narrative (226 responses, ~64k obs, raw_store id 216, "no null numbers in 225
  payloads") is provenance context; only the archived receipt bytes were verified here.
- Existing-duplicate expectations were inverted per the approved contract and replaced with
  stronger assertions (both copies quarantined / neither served) — approved behavior change,
  not a regression.

No gaps found against the approved minimal contract. Task 17 stays open; legacy cleanup
awaits owner approval outside this review.
