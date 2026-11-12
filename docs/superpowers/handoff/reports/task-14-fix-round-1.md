# Task 14 FRED — Fix round 1 report (quality-review I1, I2, M2)

Implementer: scoped fix subagent, on `pipeline-rebuild` base `7b93ab8`. Read-only review
`task-14-quality-review.md` (REQUEST_CHANGES) reproduced independently before editing:
`~/.hermes/cache/scratch/t14_probe_src2.py` re-run post-fix. No edits outside ownership:
only `ingest/sources/fred.py`, `tests/ingest/test_source_fred.py`,
`tests/ingest/test_live_fred.py`, and this report. No HANDOFF/ledger/brief/old-report edits,
no verifier/core/HTTP/importer/registry/fixture changes, no key read (sentinel fixtures only),
no network, no full suite, no push. Verdict on Task 14 completion stays with the controller.

## I1 — complete, stable FRED archives (parse + fetch + identity)

Root cause: the per-series pagination identity was scattered across one-sided checks — per-page
`offset + rows > count` (catches overruns only), page contiguity in `parse()` (catches order
only), envelope `observation_start/end` values never asserted — so a truncated/restricted
archive parsed silently as a full history, and `_identify` compared only the intersection of
URL query and params.

Fix (AGENTS hard rule — refactor to the principle first, then validate):

- The page contract `_observations()` is the ONE authoritative representation: it now returns
  `count/offset/limit/realtime/extent/rows`, with the envelope dates validated as Gregorian
  (`realtime_*` were `_str`-only before) and **every row date asserted within the declared
  observation extent** (`obs_start <= d <= obs_end`). The genuine unrestricted envelope is the
  broad `1600-01-01..9999-12-31` echo (recorded fixtures), so containment — never endpoint
  equality with first/last rows — is the assertion.
- New internal `_PageLedger` (fetch AND parse consume the same pin): the first page pins
  `(count, limit, realtime, extent)`; every later page must declare the same identity; offsets
  must be contiguous from 0; the archive is complete iff accumulated rows reach the declared
  count exactly (`assert_complete` — a missing tail / shrunk total fails closed).
  `parse()` additionally requires strictly ascending dates across the whole archive
  (subsumes cross-page duplicates; the per-spec duplicate-period check stays for multi-spec
  codes) and a series with metadata but no observations page now fails (was: 0 silent rows).
- `fetch()` enforces the ledger mid-stream: count/extent/realtime/limit drift or an offset
  mismatch raises at the drifting page (fail closed, never promote); the yielded page still
  lands as evidence first. Loop termination is `ledger.add(...) == complete`.
- `_identify` strict symmetric identity: URL query keys must be a reviewed-key subset
  (`observation_start`, `frequency`, `units`, ... rejected) AND agree with archived params
  exactly; duplicated query keys rejected (a dict view would hide them); `file_type` must be
  the literal `json`; `limit`/`offset` must be canonical ASCII decimal literals
  (`v == str(int(v))`, so `007`/`+7` rejected). params may carry identity alone; any present
  query key must match them.
- `_strip_key` unchanged: removes only the wire credential; all archived params stay key-free
  (the api_key-in-params/URL guard runs before any message that could print `params!r`).

## I2 — canonical ASCII Gregorian dates

- `_DATE`/​`_LAST_UPDATED` digit classes are `[0-9]` (the old `\d` is Unicode-aware on `str`).
- `_date()` additionally validates real Gregorian existence via `datetime.date` (year 0000,
  Feb 30, month 13 all rejected) and returns the original text verbatim — no normalization,
  no alias repair. Applies to row dates (month-first), metadata and envelope dates, realtime
  bounds.
- Value-token layer split is preserved verbatim (review-verified-good probe P5): a numeric-
  shape-odd token like `1e5` still passes the source as a string and is quarantined
  `non_numeric` by `validate()`; no conversions were added.

## M2 — live test unpinned and explicitly bounded

`tests/ingest/test_live_fred.py` no longer freezes `n == 417`, `("1992-01", "2026-09")` or
`12*144` (guaranteed stale at the next FRED monthly release). Expectations are derived from
the run's OWN archived publisher bytes: raw-store responses re-parsed offline by the reviewed
adapter must equal the DB exactly per series (nonempty, canonical `YYYY-MM` periods, exact
count and range; DB range also asserted equal to the publisher-declared metadata
`observation_start/end` of the same run), and the `non_numeric` quarantine total must equal
the archived `.` count. Kept: all-12 active series, `verified`, `served == 0`,
`size=120` + `verifs == [(120, 1)]`, and the offline value/unit evidence replay (now
`replayed == len(rows) == 120`). HTTP is explicitly bounded per request:
`RequestsHttp(throttle_rps=1.0, timeout=120.0, retries=0)` — documented in the module
docstring as a PER-REQUEST bound, not a whole-phase deadline (none is implemented; the f0nix
acceptance cap stays the phase bound). Not runnable here (no key/network); the derivation
block was validated offline against the recorded fixtures by
`~/.hermes/cache/scratch/t14_livetest_dryrun.py` — healthy run passed (12 metas, 12 series,
derived 417 / 1992-01..2026-09), negative control (one fabricated DB hole) raised
`AssertionError`. Controller owns the f0nix live re-run.

## TDD evidence (actual red → green)

New tests added FIRST against base `7b93ab8` source, then the fix implemented. Final 15-item
regression set (`tests/ingest/test_source_fred.py`), re-measured against the pre-fix source by
stash/patch isolation:

- RED pre-fix (13): `test_parse_rejects_a_truncated_archive_that_keeps_the_declared_count` (P1),
  `..._archive_missing_its_tail_page`, `..._series_with_metadata_but_no_observations_page`,
  `..._rows_outside_the_declared_observation_extent` (P4, both bounds),
  `..._count_or_extent_drift_across_pages`,
  `..._unreviewed_duplicate_or_mismatched_url_query_keys` (P3/M3: restriction key, duplicated
  key, value mismatch, query key absent from params),
  `test_fetch_rejects_cross_page_identity_drift_mid_pagination[drift_realtime|drift_extent|drift_limit]`
  (count drift was already terminal pre-fix via per-page/no-progress guards; the ledger now
  fails AT the drift instead of later),
  `..._unicode_digit_date_aliases` (P2: appended + in-place), `..._dates_that_are_ascii_but_not_gregorian`
  (year-0000 row; `9999-02-30`/`0000-01-01` envelope bounds — Feb-30 on a row was already
  unreachable behind the month-first day==01 gate), `..._unicode_digit_realtime_and_last_updated`,
  `test_pipeline_refuses_a_truncated_or_unicode_aliased_archive_and_writes_nothing`
  (the unicode-aliased half reached `pending-verification` pre-fix — a full-pipeline promotion;
  the truncated half already failed pre-fix via offset-contiguity/params drift, pinned).
- GREEN pins pre-fix (2, kept to lock the behavior): `..._non_canonical_or_wrong_archived_param_literals`
  (already rejected via params/payload + query mismatch; the new `_identify` canonical-literal
  and `file_type` literals make it immediate) and `test_fetch_paginates_to_a_complete_stable_archive`
  (first coverage of the multi-page fetch path; OBS_LIMIT monkeypatched in-test to 300).
- Post-fix: `tests/ingest/test_source_fred.py` 49/49; FRED battery
  (source + verifier + registry units + independence) 106/106; wider targeted battery
  (+ validate, pipeline, licence-gate, verify) 358/358 in 96 s. `ruff check` clean on all
  three touched files (ruff format is not this repo's convention — base files fail
  `format --check` too; untouched). Live test: collects, deselected by default, skips cleanly
  without `FRED_API_KEY` (no key read here).

## Paths and commits

- `ingest/sources/fred.py` (+120/-34): page contract with extent, `_PageLedger`, ASCII+Gregorian
  `_date`/​`_LAST_UPDATED`, strict `_identify`, ledger-driven fetch/parse, docstring corrected
  to the real fail-closed set.
- `tests/ingest/test_source_fred.py` (+260): the 15-item regression set, all mutations built
  in-test from genuine archived bytes (never stored as genuine evidence).
- `tests/ingest/test_live_fred.py`: M2 rewrite above.
- `docs/superpowers/handoff/reports/task-14-fix-round-1.md`: this report.
- Commits: see report footer / `git log` (source fix; live test; this report). Controller-owned
  working-tree edits (HANDOFF.md, progress-ledger.md, task-14 reports) were left uncommitted
  and untouched.

## Remaining risks / minors (honest)

- M1 (verifier interior-row absence-only tamper) accepted as documented residual risk per the
  review and this task's scope — verifier semantics untouched.
- Fetch-time shape failures surface to the pipeline as `failed-fetch` (a run-level guard),
  parse-time as `failed-validation`; both are terminal with zero writes — the pipeline test
  asserts refusal + evidence kept, not a specific phase label.
- The extent contract is containment-only by design (broad genuine envelope), so a
  tampered-but-plausible envelope inside the true extent is not detectable by the source;
  completeness against silent window loss rests on count reconciliation + the strict
  url/params identity (restriction keys unrequestable), plus M1-style sampling downstream.
- Cross-page `count` growth mid-fetch was already terminal pre-fix (no-progress raise); the
  ledger makes every drift variant fail at the point of drift.
- No live re-run done here: the controller's f0nix acceptance (48 calls / 180 s cap) is the
  gate; the 2026-11-12 f0nix run's 5004/1728/120-exact/0-served results stand per the review.
