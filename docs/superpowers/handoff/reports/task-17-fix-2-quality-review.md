# Task 17 fix 2 — independent quality re-review (F1 only)

**Commit under review:** `6cf6777` (`eddb91c..6cf6777`), `pipeline-rebuild`, HEAD confirmed `6cf6777...`.
**Reviewer posture:** independent read-only quality re-review after specification PASS. No production edits, no HTTP, no full suite, no closure/commits. M1/M2/M3 remain non-blocking and already documented; not re-expanded here.

## Verdict: APPROVED

The single blocking flaw F1 from `task-17-quality-review.md` is fixed correctly and verifiably.

## What was checked

1. **Diff scope.** 6 files: new `ingest/receipts.py`; delegation changes in `ingest/bundle.py` and `ingest/pipeline.py`; new focused test file; a task report; a one-bullet operator doc note. No unrelated production churn. Capture-side stamping unmodified. Legacy-collector deletion and Task 17 closure untouched, as scoped.
2. **Single policy, enforced twice.** `ingest/receipts.py` holds `MAX_CLOCK_SKEW = timedelta(minutes=5)` and the pure `receipt_fetched_at(raw, *, now, what)` validator (parse, tz-aware check, UTC normalization, future-beyond-skew refusal). Both boundaries delegate to it, so the rule cannot drift between loader and pipeline (grep confirms no other definition site).
3. **Bundle boundary.** `load_bundle(..., now=None)` resolves `now` to the real `_utc_now()` at import time; `_entry_ts` re-raises `ValueError` as `BundleError` with the same message shape as before. Validation of the entire manifest still happens before any DB open — CLI test proves a future bundle exits 2 and creates no DB file.
4. **Pipeline boundary.** In `run_dataset`, `_receipt_ts(resp.fetched_at, now=now())` is checked against the run's own injected clock **before** `_record(...)` writes raw evidence: failure returns `failed-validation` + `format_change` with "future" in the detail, and zero observations / zero raw_fetch rows are written. The pipeline does not trust the loader for its own invariant — a direct recorded `RawResponse` is refused independently.
5. **Behavior-preserving edges.** Historical receipts accepted and normalized to UTC exactly as before (`2020-06-30T12:30:00+02:00` → `...+00:00`, kept verbatim in raw_fetch); equal-to-now and exactly-`now+skew` accepted (strict `>` comparison); `now+skew+1s` and +365d refused. Naive `now` is itself rejected — fail-fast, no silent fallback. Production default path always uses the real clock; `now` injection is test-only.
6. **Real runs in this tree** (`.venv-ci/bin/python`):
   - `pytest tests/ingest/test_task17_fix2.py -q` → **10 passed** (includes policy pin `MAX_CLOCK_SKEW == 5 min`).
   - `ruff check ingest/receipts.py ingest/bundle.py ingest/pipeline.py tests/ingest/test_task17_fix2.py` → **All checks passed!**

## Notes (non-blocking)

- `_receipt_ts`'s `now=None` fallback is unreachable from its only call site (which always passes `now=now()`); harmless belt-and-braces consistent with `_entry_ts`, keeps helpers standalone-safe.
- Reported prior verification (66 passed across the touched modules, TDD red/green) was not re-run — out of this review's scope; the parent controller owns the fresh full-suite authority.

## Conclusion

F1 is resolved: future receipts beyond the 5-minute skew are refused at both the bundle-load boundary (pre-DB) and the pipeline write boundary (pre-raw-provenance), under one non-duplicated policy, with clock injection done right and historical/equal-edge behavior unchanged. Nothing still blocking from the F1 scope.
