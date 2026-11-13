# Task 17 fix 2 — scoped independent specification re-review

Commit under review: `6cf6777` (`fix(ingest): Task17 quality F1 - refuse future receipts at bundle
loader and pipeline write boundary`), branch `pipeline-rebuild`, diff `eddb91c..6cf6777`.
Reviewer: independent subagent, read-only spec review. No code/commits/task closure performed.

## Verdict: PASS

Every acceptance criterion in the review scope was verified against the actual tree and a real
test run, not just the fix report's claims.

## Criterion-by-criterion verification

| Criterion | Result | Evidence |
|---|---|---|
| New `ingest/receipts.py` is the single pure policy | ✅ | `MAX_CLOCK_SKEW = timedelta(minutes=5)`; `receipt_fetched_at(raw, *, now, what)` is a pure function — no I/O, no hidden clock, tz-aware ISO → UTC normalize, refuses only `dt > now + MAX_CLOCK_SKEW`. `now` is caller-supplied; a defensive guard rejects a naive `now`. No parser/verifier coupling introduced. |
| Both boundaries delegate, independently | ✅ | `bundle._entry_ts` → helper (re-raises as `BundleError`, same message shape); `pipeline._receipt_ts` → same helper. pipeline.py:134 passes `now=now()` — the run's own injected clock, NOT the manifest's or loader's judgment. Independence proven by `test_pipeline_receipt_checked_against_injected_run_clock` (real-now receipt refused against a 1-year-behind run clock). |
| Loader rejects future 365d BEFORE any DB open | ✅ | cli.py:429 `load_bundle(...)` with explicit "BEFORE any DB open/mutation" comment; `BundleError` → return 2 before `_open_run`. `test_future_bundle_creates_no_db` is an end-to-end CLI test: rc==2 AND the DB file does not exist. Passed in the run below. |
| Direct `RawResponse` future receipt writes nothing | ✅ | pipeline.py ordering: receipt validated at line 134, `_record` (raw_fetch provenance) only reached at line 139. Test asserts `failed-validation`, `format_change` event containing "future", and `(n_obs, n_raw) == (0, 0)` — no observations, no dated raw provenance, loader bypassed. |
| Skew boundary exact semantics | ✅ | Rule is strict `>`. Tests pin both sides: `now+skew+1s` refused; exactly `now+skew` accepted at BOTH boundaries (loader entry kept verbatim; pipeline run lands `pending-verification`, 3 obs, provenance written). Equal-to-now accepted. `MAX_CLOCK_SKEW == 5 min` pinned by an explicit test. |
| Historical tz receipts preserved | ✅ | Offset-tz receipt `2020-06-30T12:30:00+02:00` accepted, normalized to `2020-06-30T10:30:00+00:00` (unchanged pre-fix behavior); pipeline historical receipt kept verbatim in `raw_fetch.fetched_at`. |
| No value/status/independence regressions | ✅ | Diff touches only receipt-time validation: bundle status/bytes/hash/cap checks untouched; pipeline outcome vocabulary (`failed-validation`+`format_change`) is the pre-existing path for bad receipts; capture-side `_utc_now()` stamping unmodified; `cli.py` unchanged. Scope held: only F1, M1–M3 and Task-17 closure untouched, plus one honest operator bullet in `docs/data/manual-refresh.md`. |
| Focused tests, no network/full suite | ✅ | Real run this tree: `.venv-ci/bin/python -m pytest tests/ingest/test_task17_fix2.py test_bundle.py test_task17_fixes.py test_pipeline.py -q` → **66 passed** (matches the fix report's count exactly). Report's RED→GREEN TDD sequence and ruff/GitNexus claims were not re-executable in scope but are consistent with the diff contents. |

## Notes (non-blocking)

- Loader clock default: `load_bundle(now=None)` resolves `now` once per call — correct and
  deterministic within a load.
- `test_task17_fix2.py` computes `FUTURE_365` at module import; harmless.
- Pre-existing repo-wide `ruff check` findings in unrelated test files pre-date this fix and
  remain out of scope, as the fix report states.

## Conclusion

**PASS.** The fix implements exactly what the spec required: one authoritative 5-minute
clock-skew policy, enforced independently at the load boundary (before any DB open) and at the
pipeline write boundary (against the run's own clock, before any provenance write), with exact
boundary semantics, historical receipts preserved, and no behavioral drift elsewhere. No
remaining gap found within the review scope.
