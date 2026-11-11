# Task 12 REN — fix round 1 QUALITY re-review (34abed5..7f58a21)

**Verdict: APPROVED.** Independent, read-only, bounded to the fix diff and the five closed
findings (F1/F2/F5/F6/F7) plus regression boundaries. Follows the fresh spec re-review PASS
(`task-12-ren-fix-spec-review.md`); prior full quality review REQUEST_CHANGES
(`task-12-ren-quality-review.md`). Reviewer is independent of implementer and spec reviewer.
No code/test/registry/shared-doc edits, no commit/push/deploy/outbound; no network, no duckdb,
no installs. Task 12 stays OPEN (DGEG disposition) — unchanged by this review.

## Execution evidence (fresh, this session)

- `git diff --stat 34abed5..7f58a21` — 11 files, all REN-owned (sources/verifier/tests/
  fixtures) + the fix report; no registry/engine/licence/controller files. HEAD = 7f58a21.
- `git diff` of both code files read line by line: `_Num` tagging (`parse_int=parse_float=_Num`),
  `_token` requires `type(v) is _Num` and returns plain `str(v)`; balance `type` label requires
  `type(rtype) is str`; `parse_prices_body` return routed through `_token`. `_rows` runs blank
  analysis on the UNFILTERED `csv.reader(strict=True)` output (zero-cell OR all-empty cells
  count as blank; suffix-only tolerance) before filtering. `_envelope` emits
  `ren-portal-evidence` v1 with url + ACTUAL status + base64 body; `ItemResult.evidence` uses
  it, `evidence_url` unchanged.
- Targeted suite: `.venv-ci/bin/python -m pytest tests/ingest/test_source_ren.py
  tests/ingest/test_verifier_ren.py tests/ingest/test_registry_ren_units.py
  tests/ingest/test_licence_gate.py -q` → **79 passed in 11.18s** (incl. the licence gate's 8
  tests — redistribution stays denied, served=0 semantics unchanged).
- Novel direct probes (scratch dir, real archived bytes tampered at axes the named tests do
  NOT cover — `/home/joao/.hermes/cache/scratch/probe_ren_fix1.py` plus one diagnostic run):
  - F1: quoted `"1616"` on the SALDO_IMPORTADOR row raises `must be a number token`; quoted
    capacity token (first numeric after `Capacidade [MW]`) raises; **boolean** `type` label
    (distinct JSON primitive) raises; integer `4442`, negative and decimal `143.9` tokens
    round-trip as **plain `str`** (`type is str`, `SALDO_IMPORTADOR == '1616'` str); a 30-digit
    integer round-trips token-exact through `_Num`; the tag class never escapes (`_token`
    rejects raw str; only plain str reaches RawRow); `null` and exponent `4442e0` tampered into
    a real fixture row still raise.
  - F2/F5: interior zero-cell line and interior comma-blank row both raise; trailing blank
    suffix (bare CRLF and `,,`) tolerated (archived shape); a field-leading unclosed quote
    raises under `strict=True`. One nuance resolved by diagnosis: a MID-FIELD quote is a
    literal character to Python csv (no table reshape, no error) — the guard's job is to stop
    field-leading quotes from re-shaping the table, and that path genuinely fails closed. Not a
    defect.
  - F6: `_envelope(url, 418, b"\xff\x00raw")` round-trips exact binary bytes, the FINAL url and
    the ACTUAL status 418 — status is recorded from the received HttpResult, not implied.
- F7c fixture forensics (independent of spec review): `sha256sum
  tests/ingest/fixtures/ren/portal/mercado.body` =
  `a27cc396ff5bfc06b46feb71892077a3a170d010933900ede4ea6265b3270da2` — **byte-identical to
  MANIFEST.json `unit_evidence.market_page.sha256`**, with final URL and status 200 recorded;
  €/MWh narrative present.

## Finding-by-finding

- **F1 (Important)** — CLOSED. Tag-and-require is exactly the bounded fix recommended; all
  quoted-number surfaces (balance, PT/ES price metrics, capacity, scalars, numeric/boolean
  type labels) fail closed while genuine integers/decimals keep publisher precision and leave
  the module as plain str. Two probe-shape failures I hit during iteration (`{"Data":[...]}`
  wrapper, `y` surface, `-263` row location, `SALDO IMPORTADOR` vs `SALDO_IMPORTADOR`) were MY
  probe bugs — the code rejected nothing valid and accepted nothing invalid.
- **F2** — CLOSED. Blank analysis now precedes filtering; both interior blank shapes raise;
  archived trailing-CRLF shape still accepted.
- **F5** — CLOSED. New permanent tests cover HTML page, non-UTF-8, empty CSV, both interior
  blanks, trailing tolerance, malformed quote; the malformed-quote axis is real (field-leading
  quote fails) per my probe.
- **F6** — CLOSED. Versioned `ren-portal-evidence` v1 envelope carries exact bytes + final URL
  + actual HTTP status; only stdlib `base64`/`json` added (already allowlisted); offline
  recovery/replay and subprocess independence covered by the passing suite.
- **F7** — CLOSED. (a) docstring example now 2025-10 (13 completed months); (b) verifier
  docstring states columns 3/4 are the current-year block, validated not read; (c) market page
  body committed, hash-pinned, manifest-verified (above).
- **F3** — documented replay-by-archived-request-params contract in `parse()`'s new docstring;
  acceptable, not a new range constraint. **F4** — denied-source revision silence documented as
  deferred engine follow-up; no engine change in this diff. Both dispositions unchanged and
  correct for this round's scope.

## Boundaries checked

No licence enablement (licence-gate tests pass and unchanged; no terms/registry edit in the
diff), no shared-helper modules, no engine/collector/DGEG/ERSE edits, evidence format REN-local.
Full/live suites deliberately NOT re-run (controller owns the fresh 830-passed + live
182/50match/served0 evidence); ruff and final lint also left to the controller per scope.

## Remaining Critical/Important

**None.** Task 12 remains open on the DGEG disposition only; F4 follow-up (revision events vs
latest verified fetched vintage) tracked as a documented engine-level deferral, not a blocker.
