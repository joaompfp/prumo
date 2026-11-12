# Task 17 quality fix 2 — F1: future-dated receipts refused at both boundaries

Scope: ONLY finding F1 of task-17-quality-review.md (`pipeline-rebuild` @ eddb91c).
M1/M2/M3, the legacy-collector deletion and Task 17 closure are all untouched.

## What was wrong (F1)

Neither the bundle loader (`ingest/bundle.py:_entry_ts`) nor the pipeline receipt check
(`ingest/pipeline.py:_receipt_ts`) rejected a `fetched_at` in the future. A capture laptop
with a wrong clock produced bundles that passed validation, beat both stale guards (false
freshness in the served view) and then locked every genuine later bundle out as "stale"
until real time caught up with the fake date.

## Fix — one clock-skew policy, enforced twice

- **New `ingest/receipts.py`**: the single authoritative rule. `MAX_CLOCK_SKEW =
  timedelta(minutes=5)` and pure `receipt_fetched_at(raw, *, now, what)` — tz-aware ISO,
  normalized to UTC as before, refused only when `> now + MAX_CLOCK_SKEW`. The `now`
  argument is the caller's actual import-time clock (injected in tests; never a fake
  production clock). No parser/verifier coupling; the duplicated parse/tz/normalize
  knowledge that existed in both boundaries now lives in exactly one place.
- **`ingest/bundle.py`**: `_entry_ts` delegates to the shared helper (re-raising as
  `BundleError`, same message shape). `load_bundle(..., now=None)` defaults to the real
  `_utc_now()` and still raises BEFORE any DB open — a future bundle creates no DB.
  Capture-side stamping (`_utc_now()` original-attempt clock) unmodified.
- **`ingest/pipeline.py`**: `_receipt_ts` delegates to the same helper and is checked
  against the run's own injected clock (`now()`) at the write boundary, BEFORE `_record`
  writes any raw_fetch provenance — a future `RawResponse` writes no observations and no
  raw provenance, loader bypassed or not. Failed outcome stays the existing
  `failed-validation` + `format_change` event; no statuses/bytes/value-precision changes.

## Tests added (`tests/ingest/test_task17_fix2.py`, 10 tests)

Loader: future +365d refused; now+skew+1s refused; equal-to-now and exactly-now+skew
accepted; historical offset-tz receipt accepted and normalized to UTC; CLI future bundle
exits 2 and creates no DB file. Pipeline (direct `RawResponse`, loader bypassed): future
+365d → `failed-validation` with "future" in the event, zero observations, zero raw_fetch
rows; real-now receipt vs a 1-year-behind injected run clock refused (proves the boundary
uses its own clock); receipt at the exact skew edge accepted (3 obs, provenance written);
historical receipt accepted and kept verbatim. Policy pinned: `MAX_CLOCK_SKEW == 5 min`.

## Verification (real runs this tree)

- TDD: new tests ran RED first (8 failed: future accepted as `pending-verification`,
  loader took no `now`), then GREEN.
- `pytest test_task17_fix2.py test_bundle.py test_task17_fixes.py test_pipeline.py -q` →
  66 passed. `test_cli.py`/`test_status.py` untouched by the diff (`cli.py` unchanged).
- `ruff check` clean on the touched code (repo files are not `ruff format`-conformant at
  HEAD and ruff.toml configures lint only, so no whole-file reformat was mixed in). The
  remaining `ruff check ingest tests` findings (unused imports in `tests/conftest.py`,
  `test_verifier_eurostat.py`, ...) pre-date this fix and are out of scope.
- GitNexus `detect-changes`/`impact` run pre-commit (`.gitnexus` index); output in commit
  notes below. AGENTS.md/CLAUDE.md local generated diffs deliberately NOT staged.
- `docs/data/manual-refresh.md`: one added bullet in "Limites honestos" stating the 5-min
  skew refusal rule for operators; no other doc change.

Task 17 stays OPEN pending the controller's scoped independent spec/quality re-reviews.
