# Task 14 — FRED fix round 2 report (params-subset guard)

Date: 2026-11-12 · Branch: pipeline-rebuild · Base: 8bc06d4 (fix round 1 report commit)

## Scope and trigger

Re-review of `docs/superpowers/handoff/reports/task-14-fix-1-quality-review.md`
(REQUEST_CHANGES) found exactly one remaining blocker: the archived-params identity check
in `_identify` was still a **strict-superset** test, while the URL-query side (already fixed
in round 1) correctly asserts **subset**. All other I1/I2 items were cleared by the 23/24
independent probes; spec/scope identity is unchanged and required no edit.

## Root cause

`ingest/sources/fred.py` line 325 (pre-fix):

```python
if set(params) > allowed or "series_id" not in params:   # strict superset
```

`_OBS_PARAMS = {"series_id", "file_type", "limit", "offset"}` (4 keys). A genuine archived
FIRST page carries no `offset` (fetch omits it when 0), so its reviewed key set has size 3.
One additional unreviewed key (e.g. `observation_start`, `frequency`, `units`) brings the set
to size 4 — **not** a strict superset of the 4-key allowed set — so the guard passed and the
unknown restriction/dimension key sailed through identity. Second pages happen to be caught
(offset present → extra key tips the set to a strict superset), which is why the hole is
specific to first pages. The URL-query side already rejected this shape via
`not set(q) <= allowed`, making the two sides inconsistent.

## Production change (exactly one line)

```diff
-    if set(params) > allowed or "series_id" not in params:
+    if not set(params) <= allowed or "series_id" not in params:
```

No other production code touched. The `series_id`-presence clause is unchanged; the subset
form is a strict generalisation of the old one (every previously-rejected superset contains
an unreviewed key, so no previously-rejected corpus is newly accepted — fail-closed only
tightens).

## Regression tests added (tests/ingest/test_source_fred.py, round-2 block at EOF)

1. `test_parse_rejects_params_with_an_unreviewed_key` — parametrized over
   `observation_start=2010-01-01`, `frequency=m`, `units=lin`. Genuine archived first-page
   URL/body/params (PALUMUSDM, no offset) plus exactly one unknown key; asserts
   `ValueError` matching `(?i)archived params drifted`. URL, body and reviewed params are
   byte-genuine, so ONLY the params guard can fire.
2. `test_parse_rejects_an_unreviewed_restriction_param_on_a_self_consistent_window` — the
   smuggle in its strongest form: unknown `observation_start=2010-01-01` param plus a body
   mutated in-test so the envelope AGREES with it: 201 monthly rows from 2010-01-01
   (asserted: the fixture yields exactly 201 rows ≥ 2010-01-01, first 2010-01-01, last
   2026-09-01) with `count` redeclared as 201. Truncation, count, extent, canonical-literal
   and limit/offset guards all stay silent; only the params-subset identity fails closed.
   Fixture originals untouched — tamper is built in-test via `_mut_obs`.

## TDD evidence

- **RED (pre-patch, base 8bc06d4 + tests only):**
  `pytest tests/ingest/test_source_fred.py -k "unreviewed" -q`
  → **4 failed, 1 passed** (all four new cases `Failed: DID NOT RAISE ValueError` — under the
  superset check every case, including the self-consistent window, parsed error-free;
  the pass is the older URL-side test matched by the same -k).
- **GREEN (post one-line patch):**
  `pytest tests/ingest/test_source_fred.py tests/ingest/test_verifier_*.py
   tests/ingest/test_registry*.py -q`
  → **293 passed in 168.33s** (full FRED source battery + all HTML-verifier batteries +
  all registry batteries).
- **Lint:** `.venv-ci/bin/ruff check ingest/sources/fred.py tests/ingest/test_source_fred.py`
  → All checks passed. (`ruff format --check` flags both entire files — the pre-existing
  codebase style is deliberately not ruff-format; no reformatting was done.)

## Impact analysis (GitNexus)

- `impact` on `_identify` before the edit: 1 direct caller — `FredSource.parse`
  (ingest/sources/fred.py); 1 affected module (Ingest); no cross-module processes. Contained.
- `detect-changes` before commit: symbols flagged are `fetch`/`FredSource` in
  ingest/sources/fred.py plus the controller's own handoff docs (HANDOFF.md,
  progress-ledger.md — NOT staged by this task).

## Boundaries kept

- Untouched by design: HTML verifier (`ingest/verifier*` / verifier tests/fixtures), core,
  registry, fixture originals, `live.py`/live tests, all other sources.
- No network, no FRED API key read (tests use the SENTINEL key), no full suite, no push,
  no main, no deploy, no HANDOFF/ledger/old-review edits.
- Owned paths only: `ingest/sources/fred.py` (1 line),
  `tests/ingest/test_source_fred.py` (round-2 block appended), this report.

## Residual risk

None identified for the guard itself: subset is the strongest form of this check. The one
remaining asymmetry — params may carry identity the URL omits (params ⊇ URL query) — is
documented contract, not a hole (round-1 test
`test_parse_rejects_unreviewed_duplicate_or_mismatched_url_query_keys` pins both directions).
