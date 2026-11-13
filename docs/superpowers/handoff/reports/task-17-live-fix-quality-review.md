# Task 17 live-fix — independent QUALITY re-review (SCOPED, READ-ONLY)

2026-11-12 · reviewer: independent quality gate (after spec gate PASS) · target:
`pipeline-rebuild` @ `d05e24b`, diff `6cf6777..d05e24b` · prior whole-Task-17 quality review
APPROVED at `6cf6777`; this pass checks ONLY the new E-REDES 97-row Nov-1 conflicting
canonical-duplicate fix. Task 17 is NOT closed by this review; the tool-gate cleanup remains
an owner-approval gate outside this review.

**Verdict: APPROVED**

## Review constraints honored

READ-ONLY; no HTTP calls, no full test suite, no prod touch, no code edits, no deletion.
Targeted tests + one own small byte-level probe only (within call cap); the parent's full
live-history run / full suite continues separately.

## Contract item-by-item (quality axis)

| Check | Verdict | Evidence |
|---|---|---|
| Minimal: canonical dups handed **unchanged** to existing `validate()`; `duplicate_period` quarantines BOTH copies | PASS | Source diff replaces `t_raw <= prev` raise with strict `<` only — equal-stamp rows fall through untouched. `ingest/validate.py` is NOT in this diff: the rule is the one already approved at `6cf6777`. Green tests prove BOTH copies quarantined: `test_validator_quarantines_every_duplicate_copy_and_keeps_all_other_cells` (8 rejections, all `duplicate_period`, obs disjoint from the 4 dup stamps) and the registered-run test (n==2 per (series, stamp); 0 observations at quarantined periods). |
| Strict backward order still fails closed | PASS | `if prev is not None and t_raw < prev: raise ("not strictly ascending")` retained. `test_nov1_out_of_order_still_fails_closed` (swap on the genuine fixture) + new `test_parse_rejects_out_of_order_records` (swapped unique rows) both green. |
| Verifier per-day ambiguous → `observed_text=None`; independent; NO last-write overwrite; NO day abort; unaffected cells verifiable | PASS | Per-day `ambiguous` set; 2nd occurrence does `by_ts.pop(ts, None)` + `continue` (first copy retracted, neither stored; 3rd+ hits `ts in ambiguous`); no raise on the dup path — the day file completes. Item lookup: `None if item.period in d["ambiguous"]`. Green: genuine-fixture test (4 stamps × 3 series → None, evidence intact; 5 named unique stamps verify exact tokens; absent 23:45 → None by the same path), the tampered-window created-duplicate test, and the explicit ambiguous BlindItem test. Verifier diff adds **no imports** — duplicated constants preserved, collector code untouched. |
| Exact evidence/numbers/types/header/metadata/registration unchanged | PASS | `_envelope([csv, meta])` untouched; test asserts archived csv evidence body == fixture bytes, status 200. CSV header/row-width checks unchanged; metadata double-type check unchanged; quoted-number-token and HTML guards re-asserted ON the Nov-1 fixture; registration/independence tests in the touched files green. MANIFEST change is append-only (nov1 sets + one addendum key; no previous set rewritten — confirmed in diff). |
| Genuine fixture, derived counts 267 valid / 24 quarantined | PASS | Own probe from bytes (independent of test code): sha256 + length + status 200 match MANIFEST for both `nov1_window_json.body` and `nov1_window_csv.body`; 97 rows in both channels with an IDENTICAL stamp multiset and IDENTICAL value tokens per occurrence; 4 doubled stamps (01:00/01:15/01:30/01:45 UTC), each pair genuinely CONFLICTING (e.g. dgm `980304.0` vs `1020794.0` at 01:00); zero backward-order violations, 4 equal-adjacent pairs. Derived: 89 unique stamps × 3 series = **267 valid**, 8 dup rows × 3 = **24 quarantined** — matches the tests' `_derive_counts()` and the registered-run assertions. |
| Tests cover genuine conflicting values + named unique values + ambiguous BlindItems | PASS | `NOV1_DUP_PAIRS` asserts both conflicting copies with exact tokens in publisher order on BOTH channels; `NOV1_UNIQUE` (5 named stamps) verified verbatim on all 3 series; explicit `BlindItem` at an ambiguous stamp → `observed_text None` with per-item evidence archived. |

## Test execution (targeted, this review)

`.venv-ci` pytest on `test_task17_live_fix.py`, `test_source_eredes.py`,
`test_verifier_eredes.py` → **92 passed** (6.2 s) — reproduces the spec review's count,
including the strengthened (inverted per approved contract, not deleted) prior expectations.

## Non-blocking reservations

- Full-suite and full controller-history claims were not re-run here (cap + parent's run
  ongoing). Every changed behavior is covered by the green targeted files.
- The raw_fetch id 216 provenance (receipt copied verbatim from the run DB) is consistent
  with manifest/bytes but not independently re-checkable without DB access — same standing
  as in the spec review; it does not weaken the fixture, whose genuineness is proven from
  its own bytes (conflicting pairs are unforgeable by the fix being tested).
- One probe iteration of this review tripped on a float-vs-string token comparison in MY
  probe code (`parse_float` omitted); corrected and re-derived. No fixture/test issue.

No new blocking issues found. Prior known minors are not reopened. Task 17 stays open;
legacy tool-gate cleanup awaits owner approval, outside this review.
