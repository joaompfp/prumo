# Task 15 OECD - quality fix round 1 QUALITY re-review (independent, read-only)

Date: 2026-11-12, f3nix. Reviewer: independent quality-review subagent, read-only (no repo
edits except this report; no commits; no HTTP; no full suite - parent runs those).
Repo /home/joao/projects/prumo-pipeline, branch pipeline-rebuild, frozen HEAD decc048.
Scope: `git diff e34c60f..decc048` ONLY (4b95bb1 test fixes, 4d178da punctuation, decc048
fix report). Inputs: task-15-quality-review.md (C1/C2/I1/M2), task-15-quality-fix-1.md,
task-15-quality-fix-spec-review.md (SPEC PASS) - treated as claims, independently
re-derived below. Probe script: /home/joao/.hermes/cache/scratch/oecd_t15_qr1_probes.py
(all state under /home/joao/.hermes/cache/scratch/oecd_t15_qr1_v*/).

## Verdict

APPROVED. The C1/C2/I1 fixes are correct, the new helpers genuinely DETECT every failure
class they claim (17/17 independent adversarial probes, mutations well beyond the fix's
own regression tests), fixtures are authentic and untouched, production changes are
dash-glyph punctuation only, and every acceptance pin the dispatch named is retained.

## Scope verification (what the range actually touches)

`git diff --name-only e34c60f..decc048`: 13 files - test_verifier_oecd.py (behavioral),
10 dash-only files (2 production adapters, 4 registry, 4 test-support, 1 report), 1 new
fix report, plus task-15-source-implementation.md (dash-only). ZERO fixture or
evidence-tree files; no CLI/scheduler/deploy files; no SQL/core-contract edits. Commit
authorship kimi-k3-subagent <noreply@local>, no push. OK.

## C1 - live min/max vs unsorted emission endpoints: fixed, non-vacuous RED proof

- Old form reproduced RED by me on the genuine bytes: parsed all six sha256-pinned
  fixtures with the real OecdSource; (first,last) == (min,max) fails on ALL SIX, 6/6
  arrive unsorted (cli 2026-02/2026-01 vs 2025-10/2026-10; employment 2026-07/2026-02;
  order_books 2025-12/2025-11; production 2026-07/2026-04; selling_prices 2026-06/2026-05;
  unemp 2025-10/2026-08 vs 2025-10/2026-09) - identical to the original review's table.
- New form (test_verifier_oecd.py:857-858): `(lo, hi) == (min/max over ALL r.period_raw)`
  - order-independent on both sides, correct.
- Regression test:717-731 is non-vacuous: asserts `any(ps != sorted(ps))` and CLI
  `(min,max) != (first,last)` before the whole-archive compare. OK.

## C2 - empty quarantine: fixed, both directions probed

- sqlite3 semantics reproduced: `GROUP BY` over an empty set returns `[]`; the OLD
  expression `{non_numeric: 0}.items()` produced `[('non_numeric', 0)] != []` (RED on the
  complete genuine archive, n_nulls == 0).
- New helper (:659-664) emits only positive counts: genuine archive -> `{}`; 3 synthetic
  nulls across 2 series (my mutation, beyond the fix's 1-null test) -> `{'non_numeric': 3}`.
  Live assertion :863. Any unexpected reason would surface as mismatch (helper predicts
  only non_numeric) - fail-closed direction. OK.

## I1 - whole-archive fidelity: overclaim removed AND made true, detection proven

`_assert_db_matches_archive` (:667-701) set-compares every stored
(series_id, period, value_text, status_flag, raw-response position) tuple against the
offline re-parse of the run's own archived bytes, with duplicate/collision and provenance
guards. My adversarial probes (fresh offline verified run per mutation, victims chosen
live from unsampled non-extreme rows) - every mutation DETECTED:

- row loss (DELETE 1 observation) -> "missing in DB"
- value_text drift, single appended char, unsampled row -> "extra/drifted"
- status_flag drift on unsampled interior row (NOT covered by the fix's own test) -> caught
- provenance swap (row re-linked to another collector response's raw_fetch_id) -> caught
- duplicate row content under a DIFFERENT response's raw_fetch_id (schema-legal) -> caught
- exact duplicate under the SAME raw_fetch_id is refused at the DB layer itself
  (UNIQUE(series_id, period, raw_fetch_id)); the helper's len(got)==len(got_rows) guard is
  unreachable under that constraint - belt-and-braces, harmless
- observation linked to a non-collector/bogus raw_fetch id -> "linked to non-collector"

Docstring :789-796 now states exactly this coverage (no more "exactly" overclaim). OK.

## _archive_responses (:637-657) - provenance status restored, assertions bite

- Baseline: exactly 6 ok raw_fetch rows for the run, ALL collector SDMX-JSON, all
  http_status 200; the verifier's CSV evidence is raw-store-only by verify.py design and
  NEVER enters raw_fetch (0 csvfilewithlabels urls - verified in scratch DB). The
  `format=csvfilewithlabels not in url` filter is therefore defensive redundancy; the real
  gate is `len == 6`, and the filter stays sound because HttpResult.url carries the query
  string by documented contract (ingest/http.py:26; fixture doubles urlencode params).
- Mutations all DETECTED: http_status=500 -> assert; http_status=NULL -> assert
  (isinstance+2xx check, no silent papering); injected 7th ok=1 row -> "expected 6
  archived SDMX-JSON responses, 7".
- Bonus: RawStore.load re-hashes bytes against the filename sha256 (rawstore.py:44), so the
  replay is integrity-checked; I additionally verified all 6 replayed bodies' sha256 ==
  fixture MANIFEST pins. The old hardcoded status=200 is gone from the live path. OK.

## Fixture authenticity / hashes (M-adjacent, dispatch requirement)

- tests/ingest/fixtures/oecd/{MANIFEST,verify/MANIFEST}.json: all 12 entries rehashed from
  disk - sha256 and byte counts match pins (12/12).
- Byte identity to discovery items re-derived myself: fixtures 1:1 identical to
  docs/superpowers/handoff/evidence/task-15-oecd/discovery items 1-12 (compared bytes) and
  discovery body sha256s match the discovery manifest. Publisher en/em-dashes inside the
  BTS JSON bodies preserved exactly (byte-identical proof covers this).
- `git diff e34c60f..decc048 -- tests/ingest/fixtures docs/superpowers/handoff/evidence`
  is EMPTY - original publisher bytes untouched by this range. OK.

## Production changes punctuation-only (M2): proven per file

- For the 8 logic-bearing dash-claimed files, `old.replace(U+2014,'-') == new` EXACTLY:
  sources/oecd.py, verifiers/oecd.py, mappings-oecd.md, oecd_fixtures.py,
  oecd_verifier_fixtures.py, test_registry_oecd_units.py, test_source_oecd.py,
  task-15-source-implementation.md.
- The 3 registry files keep residual em-dashes ONLY on pre-task baseline lines outside the
  diff hunks (core.yaml/proposed lines 1,11,17,21,44,88,90 vs hunks @@61-75,8632@@;
  licences-todo.md residual rows are dgeg/fred/ren/footer, non-OECD; 11->7 and 6->5 lines).
  PLUS side of the ENTIRE range adds ZERO U+2014 and ZERO U+2013. Per-file removed-glyph
  counts match the fix report's enumeration exactly (7+4+4+4+2+11+4+1+1+4+4+12 = 58, zero
  added). redistribution_ok: false / licence_url / attribution / verifiable semantics
  unchanged; the licence hunks are the dash swap only. OK.

## Retained contract pins (dispatch requirements checklist)

- Live bounds: retries=0 (:812, enforced at client), max_attempts=18 client / 150 s deadline
  (:813), hard_deadline(150.0) (:816), max_attempts=1 whole-dataset (:819), acceptance
  `attempts <= 18 and elapsed <= 150.0` (:842) - all retained.
- All-6 active-series coverage (:843, :869, plus helper asserts set(expected)==ALL_SIX and
  non-empty per series :668-669); served == 0 under redistribution_ok=false (:860);
  verifs == [(12, 1)] (:861); 12-item envelope offline replay preserved (:866+).
- Original numeric tokens, no rounding/conversion anywhere in the helpers: expected side is
  `str(row.value_raw).strip()` - the verbatim _Num publisher token; clean-run set equality
  over all 77 cells passed and a single-char token drift was caught.
- No shared parser/flags introduced between collector and verifier in the range; the
  independence guard tests sit inside the 107-test suite that passed.
- M1 discovery-budget prose: NOT edited by this range (controller-owned reconciliation
  pending) - confirmed in the file list, and I request no change for it here.

## Tests run (scoped, offline, my own execution)

- `.venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py
  tests/ingest/test_source_oecd.py tests/ingest/test_registry_oecd_units.py -q`
  -> 107 passed, 1 deselected in 14.73 s (deselected is the @pytest.mark.live gate).
- ruff clean on all 7 OECD-authored Python files.
- 17/17 adversarial probes behaved as required (listed above; full output captured).

## Minor observations (FYI/nit, non-blocking - no change requested)

- Nit: `row.flag_raw or "normal"` in _assert_db_matches_archive (:684) is unreachable for
  this source - the fail-closed parser maps only reviewed OBS_STATUS 'A'->'normal' and
  raises on anything else (referenced or not), so flag_raw is never None on a successful
  parse. Harmless default; spec review's nit stands, I concur.
- FYI: the len(got)==len(got_rows) duplicate guard is unreachable under the schema's
  UNIQUE(series_id, period, raw_fetch_id) (position derives from raw_fetch_id). Defense in
  depth; the schema itself refuses exact duplicates (probed).
- FYI: _archive_responses' csv URL filter is redundant under today's verify.py design
  (verifier evidence never lands in raw_fetch) but stays correct if that ever changes;
  the len==6 assert is the real gate.

No Critical or Important findings in scope. Prior SPEC PASS confirmed by independent
re-derivation. Ready for the controller's f0nix live gate and offline evidence audit.
