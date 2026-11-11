# Task 12 REN — fix round 1 SPEC re-review (34abed5..7f58a21)

**Verdict: PASS.** Independent, read-only, scoped to the fix diff and closed findings
(F1/F2/F5/F6/F7) plus integration boundaries. Prior full spec review: PASS
(task-12-ren-spec-review.md); this pass reviews only the fix commits' correctness against the
fix spec. Task 12 remains OPEN (DGEG disposition) — unchanged by this review.

## What was executed (real output, this machine)

- `git diff --stat 34abed5..7f58a21` — 11 files, all REN-owned (sources/verifiers/tests/
  fixtures) + the fix report. No registry, engine, licence, shared-helper, or controller files.
- Targeted suite: `.venv-ci/bin/python -m pytest tests/ingest/test_source_ren.py
  tests/ingest/test_verifier_ren.py tests/ingest/test_registry_ren_units.py -q`
  → **71 passed in 8.75s** (report's 79 adds test_licence_gate.py, outside my named scope).
- Focused independence selector: `-k "independ or offline or replay or envelope"` on
  test_verifier_ren.py → **3 passed** (subprocess independence + static
  `assert_verifier_independent` + archived-envelope offline recovery incl. `replay_item`).
- Focused probes (direct module calls, output verified):
  - Quoted JSON numbers `"04442"`/`"143.9"` raise even when numeric-shaped (F1 core).
  - `"type": 535` (JSON number) raises "must be a non-empty JSON string"; string label passes.
  - Genuine numbers round-trip as **plain `str`** (`type(tok) is str`, no `_Num` leak into the
    value that reaches RawRow); sign `-263`, trailing zero `143.90`, and a 30-digit integer
    beyond float range all preserved token-exact. `NaN/±Infinity/1e3/null` still raise.
  - `_rows`: interior zero-cell (`\r\n\r\n`) AND interior comma-blank (`,,`) raise "interior
    blank"; trailing blank suffix tolerated; `strict=True` CSV raises "malformed" on a stray
    quote (F2). Blank analysis runs on unfiltered reader output — verified in code.
  - `_envelope` v1 (`ren-portal-evidence`): round-trips exact binary body bytes, final URL and
    the ACTUAL status (probe used 404 to prove the status is recorded from the HttpResult, not
    implied) (F6).
- Manifest hash: `sha256sum tests/ingest/fixtures/ren/portal/mercado.body` =
  `a27cc396ff5bfc06b46feb71892077a3a170d010933900ede4ea6265b3270da2` — **byte-identical to
  MANIFEST.json `unit_evidence.market_page.sha256`**; 41,625 bytes (≤ 200 KB), status 200,
  final URL `https://datahub.ren.pt/pt/eletricidade/mercado/`; hash + `€/MWh`-narrative presence
  pinned by `test_market_unit_evidence_is_committed_and_hash_pinned` (value-agnostic) (F7c).

## Findings closed — verification per requirement

- **F1 (numeric primitive tag)** — `_loads` tags real JSON numbers via `parse_int=parse_float=
  _Num` (module-internal str subclass); `_token` requires `type(v) is _Num` and returns
  `str(v)` (plain str). Balance `type` labels require `type(rtype) is str`. Price output routes
  through `_token`. Confirmed by probes + `test_pipeline_quoted_number_fails_validation_and_
  writes_nothing` (failed-validation, 0 rows written).
- **F2/F5 (CSV guards)** — unfiltered blank-row analysis, suffix-only tolerance, strict CSV;
  new tests cover permanent HTML page, non-UTF-8, empty CSV, both interior-blank shapes,
  trailing-blank tolerance, malformed quote. Code and tests agree; probes reproduced each axis.
- **F6 (versioned evidence envelope)** — `evidence` is now the envelope (exact bytes + final
  URL + actual status from the received HttpResult); `evidence_url` unchanged. Offline recovery
  decodes the envelope from the integrity-checked raw store without HTTP and `replay_item`
  re-decides offline; subprocess entry (`ren_verifier_entry.py`) and the live test's offline
  block pin url/status/bytes from the archive. Static independence passes with only stdlib
  `base64`/`json` added — no shared helper modules, no allowlist loosening.
- **F7 (docs/evidence)** — `completed_months` example corrected (2026-11-11 → first element
  `2025-10`, 13 completed months); verifier docstring corrected (columns 3/4 = current-year
  block under the 4-digit-year header, validated not read); durable market-page evidence
  committed and hash-pinned (verified above). `observed_unit=None` stays honest.
- **Boundaries** — no licence enablement (terms stay restrictive; licence-gate tests unchanged
  and still assert served=0 / redistribution_ok=false), no framework contracts, no new shared
  helper imports, no registry/engine edits, no DGEG/ERSE scope creep. F3 documented (parse()
  replay contract), F4 correctly reported-only (shared engine, deferred).

## Not re-verified here (by design/budget)

- The RED half (9 genuine fails on base 34abed5) and the full-suite 830 passed: claimed in the
  fix report and rerun by the controller. Targeted GREEN (3 files) verified independently above.
- Live network evidence freshness: fixture provenance rests on the controller-reviewed
  2026-11-11 discovery archive; the committed copy is hash-pinned, so only the archive→fixture
  copy step is taken on controller trust (hash continuity claimed, not re-checked against the
  scratch archive, which is outside this review's read scope).

## Remaining blockers

None within this fix round's scope. Task 12 stays open on the DGEG disposition only.
