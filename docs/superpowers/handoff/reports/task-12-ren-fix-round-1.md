# Task 12 REN — quality fix round 1 (F1/F2/F5/F6/F7)

Scoped fix implementer on pipeline-rebuild, base 34abed5. Owns REN source/verifier/tests/
fixture additions + this report only; no DGEG/ERSE, no shared engine/collector files, no
controller files staged (progress-ledger/HANDOFF/briefs untouched), no merge/push/deploy.
Task 12 is NOT claimed complete (DGEG disposition open).

## RED (run BEFORE the fixes — all failing for the intended reason)

`.venv-ci/bin/python -m pytest tests/ingest/test_source_ren.py tests/ingest/test_verifier_ren.py -q`
→ **8 failed, 58 passed**: test_quoted_number_token_raises_even_when_numeric_shaped,
test_price_quoted_token_raises, test_pipeline_quoted_number_fails_validation_and_writes_nothing
(all DID NOT RAISE / wrong state), test_verifier_interior_empty_line_raises (accepted),
test_verifier_malformed_quote_fails_closed (accepted), test_verifier_evidence_envelope_...,
test_archived_evidence_recovers_offline_and_replays, test_subprocess_independence (JSONDecode
on the envelope contract). The first numeric-label test version passed pre-fix for the WRONG
reason (the missing-selected-type guard tripped); retargeted to an unmapped row →
`1 failed` (DID NOT RAISE) → 9 genuine RED.

## GREEN (after fixes)

- Targeted: `.venv-ci/bin/python -m pytest tests/ingest/test_source_ren.py
  tests/ingest/test_verifier_ren.py tests/ingest/test_registry_ren_units.py
  tests/ingest/test_licence_gate.py -q` → **79 passed** (67 pre-existing + 12 new).
- Full: `.venv-ci/bin/python -m pytest tests -q` → **830 passed, 4 deselected, 1 warning**
  (818 + 12 new, baseline warning), 125.53s.
- `ruff check` on all 8 touched Python files → clean.
- Rejection axes re-probed on the new loader: NaN/Infinity/-Infinity/null/bool/exponent still
  raise (default parse_constant leaves floats; _token requires the _Num tag), quoted numbers
  raise, numeric type labels raise, genuine numbers round-trip as plain `str`.
- Live suite NOT re-run (controller reruns; no redundant network). Its offline-recovery block
  now decodes the envelope and asserts final-URL continuity + 2xx status from the archive.

## Fixes mapped to findings

- **F1 (Important)** — `_loads` tags real JSON numbers via `parse_int=_Num, parse_float=_Num`
  (internal str subclass); `_token` requires `type(v) is _Num` and returns plain `str(v)`
  (no subclass leaks into RawRow); balance `type` labels must be genuine JSON strings
  (`"type": 5` raises); `parse_prices_body` returns `_token(...)` so the price output is a
  validated plain str. Raw JSON strings now fail closed even when numeric-shaped.
- **F2** — `_rows` runs blank-row analysis on the UNFILTERED `csv.reader` output: zero-cell
  lines and all-empty-cell rows both count as blank; blanks tolerated only as a trailing
  suffix (the archived shape's trailing `\r\n` still passes); interior blank raises.
  `strict=True` — a stray quote fails closed as malformed CSV instead of reshaping the table.
- **F5** — new tests: permanent HTML page, non-UTF-8, empty CSV, interior blank (zero-cell +
  comma-blank), trailing-blank tolerance, malformed-quote.
- **F6** — evidence is now a REN-local versioned envelope `ren-portal-evidence` v1:
  `{"schema","version","responses":[{"url","status","body_base64"}]}`. One deciding response,
  still enveloped so the ACTUAL HTTP status (from the received HttpResult, never implied) is
  archived with exact bytes + final URL; `ItemResult.evidence_url` unchanged. Offline
  recovery/replay/subprocess-entry/live tests decode the envelope and pin bytes+status+URL.
  Registration passes the EXISTING static allowlists (base64/json already in the stdlib
  allowlist) — no global loosening.
- **F7(a)** — `completed_months` docstring example corrected: 2026-11-11 → first element
  `2025-10` (13 completed months).
- **F7(b)** — verifier docstring corrected: market CSV columns 3/4 are the CURRENT-YEAR block
  under the 4-digit-year header cell (archived 2026-09: month PT 143.9 vs block PT 74.08);
  code validates `head[3]==str(year)` and reads only column 1.
- **F7(c)** — market page body committed: `tests/ingest/fixtures/ren/portal/mercado.body`
  (41,625 bytes ≤ 200 KB, €/MWh ×8), sha256-verified byte-identical copy of the
  controller-reviewed discovery archive, MANIFEST.json `unit_evidence.market_page` records
  file/final URL/status 200/sha256 a27cc396…. New test pins hash + narrative presence
  (value-agnostic — the narrative number changes over time). observed_unit=None stays honest;
  no unit invented, no extra HTTP unit fetch added.
- **F3** — documented, behavior unchanged: `parse()` reconstructs each archived response's
  period from validated request params rather than re-enforcing `self.periods` (replay
  support); actual requested coverage is guaranteed by `fetch()` (one response per
  endpoint+month) and the pipeline's failed-fetch path.
- **F4 (deferred, engine issue — report only)** — revision events compare against the gated
  served view, so a denied publisher's 10.5→10.6 restatement fires no `revision` event
  (rows/history intact). Follow-up would compare against the latest verified fetched vintage;
  outside this pass's scope (shared engine, DGEG-affecting).

## GitNexus (per brief)

Pre-edit impacts, all LOW (own checks): parse_balance_body 1, parse_prices_body 1, _rows 3,
completed_months 1, _loads 3, _token 3; methods not caller-indexed (controller: RenVerifier LOW
1 direct). `gitnexus detect-changes --scope all -r prumo-pipeline` before each commit → both
times **risk LOW, 0 affected processes**; staged diffs inspected (source commit: 2 files;
verifier commit: 5 files; controller's dirty progress-ledger.md never staged).

## Commits (authored joaompfp, scoped to owned files)

1. `0e01cb7` source: REN JSON number-token tagging (F1) + completed_months docstring (F7a) +
   parse() trust contract (F3) — ingest/sources/ren.py, tests/ingest/test_source_ren.py.
2. `78173c7` verifier: interior-blank guard fix, strict CSV, status-bearing evidence envelope
   (F2/F5/F6) — ingest/verifiers/ren.py, tests/ingest/test_verifier_ren.py,
   ren_verifier_fixtures.py, ren_verifier_entry.py, test_live_ren.py.
3. this commit: durable market unit evidence (F7c) + hash-pinning test + this report —
   tests/ingest/fixtures/ren/portal/mercado.body, fixtures/ren/MANIFEST.json,
   tests/ingest/test_registry_ren_units.py.

## Unchanged guarantees

Terms stay restrictive (redistribution_ok=false, no approval invented); served=0 with the real
registry; no DGEG/ERSE/registry edits; no shared helper modules; no engine changes.
