# Task 12B — DGEG safe disposition report (implementer)

Date: 2026-11-11 · Branch pipeline-rebuild @ 869ba6d base · Implementer-owned; controller owns
HANDOFF/ledger/briefs/reviews.

## Outcome

**Task 12 DGEG ingestion remains BLOCKED and is not complete.** What landed is the bounded safe
disposition only: all 17 DGEG annual PT series are retained with original
ids/units/frequencies/geographies/roles/indicator_keys and marked `active: false`; the `dgeg`
source gained `redistribution_ok: false` (unchanged) + a scoped `verifiable: false` marker whose
comment states its exact meaning. No adapter, no verifier, no collector, no conversions or
display-rounding policy, no REN/engine/models changes, no main merge/deploy/outbound. ERSE
untouched (zero core series, as required).

## RED → GREEN (actual commands)

- RED: `.venv-ci/bin/python -m pytest tests/ingest/test_registry_dgeg_disposition.py -q`
  → **4 failed, 2 passed** in 10.81 s (failures: 17-series inactive/identity, source flags,
  refuse-before-network, evidence bundle — the two policy-pin tests passed pre-change because the
  licence gate already withholds `redistribution_ok: false` sources).
- GREEN: same command → **6 passed** in 10.58 s.
- Lint: `.venv-ci/bin/ruff check tests/ingest/test_registry_dgeg_disposition.py tests/ingest/test_registry.py` → All checks passed.
- Full suite: `.venv-ci/bin/python -m pytest tests -q` → **836 passed, 4 deselected (live), 1
  warning** in 136.22 s (controller baseline 830 + 6 new).
- GitNexus: index refreshed at 869ba6d; `gitnexus detect-changes --scope all -r prumo-pipeline` →
  5 files, 6 symbols, 0 affected processes, risk low. Impact analysis: no production Python symbol
  modified (tests/docs/YAML only); the single existing-test edit is the stale "nothing
  unverifiable" assertion in `test_source_verifiable_marker_defaults_true_and_is_preserved`
  (test-only, now asserts exactly `{dgeg}` is flagged).

## Registry changes (`core.yaml` == `core.proposed.yaml`, byte-identical)

- `sources.dgeg`: + `verifiable: false` with an in-file comment declaring it a SCOPED
  current-core-definitions eligibility flag (blocks a normal run before any fetch), explicitly not
  a no-channel-ever claim; licence wording/URL/attribution/`redistribution_ok: false` untouched.
- 17 DGEG series: + `active: false` appended after `native_code` — the only per-series change.
  Series identities byte-preserved (diff: +25 lines per file, zero deletions, zero edits).
- No other source or series modified. One-primary-per-indicator_key invariant intact (load test
  green).

## Docs

- `registry/unmapped-dgeg.md` (new): exact 17-id matrix — workbook sheet/row coordinate, native
  unit, reason category (unit/concept conflict incl. final_energy_consumption Mtep-vs-ktep with
  its genuine APN 10/10 ktep channel and electricity_consumption TWh-vs-ktep; primary_energy_
  consumption legacy domestic-production-%-misassignment; energy_intensity duplicate; precision/
  coverage, base-year mismatch, vintage/coverage, representation policy, weak-independence),
  evidence URLs, per-row resumption criteria. States plainly: partial channels exist; APN is a
  genuine channel for consumption_primary_total (8/10, 2021/22 vintage drift) — "blocked", not
  "no channel", and the fraction-vs-percent relabelling recommendation was REJECTED as unresolved
  scale policy.
- `registry/unverifiable.md`: rewritten — DGEG has no adapter, no verifier, no collected data;
  SourceNotVerifiable/NoVerifierRegistered refuse before any network; inactive series excluded
  from T17/T18 scheduling. Stale universal "adapter exists / data is still collected" wording
  corrected. REN reclassified: verifiable but licence-withheld (≠ unverifiable); INE verified.
- `registry/licences-todo.md`: DGEG row replaced — terms shell ("about us" only), site footer
  "All Rights Reserved", AEN "Todos os direitos reservados", LADA statute citation ≠ grant,
  dados.gov.pt CC BY = geology datasets only (NOT the energy workbook). Unresolved unconfirmed
  grant; no invented permission, no categorical illegality claim.

## Evidence (durable, `docs/superpowers/handoff/evidence/task-12-dgeg/` + MANIFEST.json)

Raw (byte-identical to the research archive): the original 119,336-byte workbook
(sha256 5f31904a…837be), terms page HTML, LADA page HTML, indicadores collector page HTML,
dados.gov.pt DGEG-org datasets JSON (each ≤200 KB). Derived, first line labelled DERIVED and never
presented as raw response evidence: APN full text layer and AEN ficha-técnica rights excerpt, both
naming source PDF URL/sha256/bytes (APN d4490a8e…07a7 2.4 MB, AEN 9486137e…c4db1 13 MB — PDFs
deliberately NOT committed). Manifest records raw-vs-derived, final URL/status/hash/bytes per
file; the disposition docs stand without the expiring scratch paths.

## Test coverage added (tests/ingest/test_registry_dgeg_disposition.py, 6 tests)

Exact 17-id set all inactive with identity/unit/role/key/geography/frequency/native_code pinned;
core==proposed + invariant + no ERSE; scoped source flags + no verifier registered for dgeg;
`run_with_refetch` raises SourceNotVerifiable BEFORE any fetch/parse/verifier call/HTTP against
explicit standalone dgeg-labelled test doubles (zero http.calls, zero dataset_run/raw_fetch rows);
sync + 0005 licence gate withholds synthetic `verified` fetched AND legacy DGEG rows with
legacy_served='1' (clearly labelled synthetic policy test, NOT a live DGEG verification); evidence
workbook byte/hash pin + manifest validation (paths exist, hashes match, ≤200 KB, derived files
carry DERIVED header + pinned source-PDF sha256).

## Precisely blocked / excluded

DGEG adapter + verifier implementation; any live DGEG fetch or verification claim; unit
corrections (Mtep/TWh — owner decisions); fraction-percent representation policy; duplicate and
misassignment reconciliation; AEN/APN display-precision policies; licence resolution
(`redistribution_ok` stays false; served=0 for any DGEG row regardless of adapter work). Sources
not covered by same-publisher bar (Eurostat/INE/ApC) were not proposed. Completion of Task 12
itself remains with the controller after independent spec + quality reviews of this disposition.
