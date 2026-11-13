# Task 15 Part B - OECD independent verifier implementation report

Date: 2026-11-12. Author: implementer subagent (kimi-k3). Base 212cd17 (Part A report commit),
branch pipeline-rebuild, /home/joao/projects/prumo-pipeline. Scope: Part B ONLY per dispatch -
the verifier (`ingest/verifiers/oecd.py`), original CSV fixtures (separate manifest), verifier
tests + fixture helper, this report. Source module, registry, Part A tests/files, handoff/
ledger/vault, live acceptance and reviews are explicitly out of scope and untouched; the
concurrent read-only source-spec reviewer's report was not staged.

## Delivered

| path | what |
|---|---|
| ingest/verifiers/oecd.py | `OecdVerifier` (source_name 'oecd') - csvfilewithlabels SDMX-CSV channel, 333 LOC |
| tests/ingest/fixtures/oecd/verify/ | 6 genuine publisher CSV bodies + own MANIFEST.json (sha256 pins; byte-identical to discovery items 2,4,6,8,10,12; hashes re-verified at copy time against the discovery manifest, whose own sha256 09dad8d1...11c1 is pinned in the notes - same pin Part A used) |
| tests/ingest/oecd_verifier_fixtures.py | verify-channel accessors, window-bounded CsvFixtureHttp double, test-only token extractor, independence entrypoint `run()` |
| tests/ingest/test_verifier_oecd.py | 32 offline tests + 1 `@pytest.mark.live` (deselected by default) |
| this file | evidence, red/green, limitations |

## TDD record

- RED: `ModuleNotFoundError: No module named 'ingest.verifiers.oecd'` at collection
  (fixtures+tests landed first; full failing-run output captured).
- Iteration, all against evidence not guesses: (a) test helpers mixed str/bytes on mutation
  anchors - real failure caught by tests, fixed in-test only; (b) CLI carries UNIT_MEASURE=IX
  AND TRANSFORMATION=IX with the same label 'Index', so a coordinate-consistent publisher-side
  unit failure is exercised via the label cell (a code mutation trips the pinned-coordinate
  guard first, which is the designed fail-closed order).
- GREEN: `32 passed, 1 deselected` for tests/ingest/test_verifier_oecd.py; neighbouring
  suites test_independence.py + test_source_oecd.py pass (`56 passed`). Ruff clean on all new
  files. Full-suite run deliberately left to the controller per dispatch.

## Contract coverage (mandatory points)

- Tokens: OBS_VALUE cells preserved VERBATIM, plain-ASCII-decimal regex enforced; no float,
  no rounding, no truncation. CSV trims trailing '.0' vs the JSON channel (e.g. '-6.0'->'-6',
  '12.0'->'12', '5.80'->'5.8' in evidence); exact-Decimal comparison absorbs it (already
  engine policy) - a dedicated test pins the difference on the real cells.
- Identity: native_code parsed independently ('<agency>,<dataflow>/<9 dot pins>', duplicated
  shape rule on purpose - no parse_native_code import); STRUCTURE='DATAFLOW', ACTION='I',
  STRUCTURE_ID '<agency>:<dataflow>(<version>)' pinned to the request, all 9 dimension code
  cells equal the registry key pins in header order (evidence: both families), labels for
  pinned codes non-empty. BCICP/LI trap exercised; a REF_AREA mutation (foreign series) fails.
- Header-name parsing: column positions never assumed (item 12 puts BASE_PER before
  OBS_STATUS); duplicate header names, unknown columns and width drift fail closed.
  TIME_PERIOD/OBS_VALUE label cells must stay blank (reviewed shape).
- Status: OBS_STATUS 'A' ('Normal value') -> observed_flag 'normal'; ANY other code fails
  closed (full codelist never enumerated, discovery item 13 404). No synthetic success maps.
- Units/multiplier/base: UNIT_MEASURE narrow evidence-backed map IX->'index (100=trend)',
  PB->'balance %', PT_LF_SUB->'%' (labels pinned) asserted AGAINST the registry unit - never
  echoed from it; registry-side drift raises too ('!= registry unit'). UNIT_MULT must be
  '0'/'Units' with registry multiplier 0; BASE_PER code+label blank, no invented base year;
  DECIMALS shape-pinned display metadata, never used. FREQ 'M'/'Monthly' vs spec.frequency and
  ADJUSTMENT AA->unset / Y->'Calendar and seasonally adjusted' vs spec.seasonal_adjustment
  asserted the same way.
- Window: one request per distinct series with startPeriod/endPeriod = the sampled items'
  min/max (never full-history on the verifier); decoded periods must be canonical, unique,
  inside the requested window (out-of-window rows raise). A requested period absent from the
  response yields observed_text=None - an honest mismatch, never invented data; nothing
  assumes all periods are present.
- Envelope: oecd-csv-evidence v1, {csv: {url, status, body_b64}} exact bytes; offline replay
  via read_csv_evidence recovers values AND unit AND flag from the stored body alone, tested
  per sampled item through verify_run's raw store (40/40 envelopes in the combined test).
- Transport: non-2xx, HTML and blank bodies all fail closed before parsing. No headers are
  sent on this channel (no copy of the collector's SDMX-JSON Accept header; asserted).
- Independence: register_verifier static allowlist passes (stdlib-only imports from the
  reviewed VERIFIER lists; closure shares nothing outside SHARED_ALLOWED with
  ingest/sources/oecd.py); assert_verifier_independent subprocess passes with
  ingest.sources/ingest.flags/collectors blocked. No registration-file edit was needed.
- Combined: clean run over the REAL registry (77 obs, 0 quarantined) verifies via
  run_with_refetch (registered verifier, shared Http dispatched by params): state 'verified',
  served=0 under redistribution_ok=false, every verification_item carries observed unit/flag
  and evidence sha256. Registry unit drift on one series fails verification closed, serves 0.

## Live test (controller-run, NOT executed here)

`test_live_run_with_refetch_all_six_verified_and_served_zero` (@pytest.mark.live): real
RequestsHttp, all 6 active series, temp db, rolling collector window (start 14 months back from
runtime date - nothing frozen), verifier requests driven by the fresh sample. Bounds: throttle
0.25 rps (<=15 req/min), 30 s per-request timeout, retries=0, max_attempts=1, asserted <=18
requests and <=150 s whole-phase deadline around the run. Expectations are non-stale: per-series
counts/ranges re-derived from THIS run's archived JSON bytes re-parsed offline; verifier
expectations re-read from the freshly archived CSV envelopes (values+units+flags, no HTTP);
served==0 asserted under the licence gate. The production verifier carries no timeout/rate
policy of its own - those live only in the controller's test/Http client, per contract.

## Tooling compliance

GitNexus detect-changes on this worktree before the commit: LOW, 0 affected processes (new
module/classes only, zero pre-existing callers; no existing symbol modified, so no impact run
was required). No network used at implementation time. Scratch only; no DuckDB. Plain hyphens
in all authored files (checked). Truthful authorship, no AI trailers.

## Commit

- `ccaa0ed` feat(ingest): OECD csvfilewithlabels verifier + evidence envelope (Task 15 Part B)
  - 10 files (verifier + 7 fixture files + helper + tests).
- report commit follows as its own commit (this file), same convention as Task 12-15 reports.

## Limitations (explicit, carried forward from the brief)

1. OBS_STATUS full codelist remains unenumerated (publisher 404 on the probed codelist id,
   discovery item 13): fail-closed on any non-'A' code stands until official codelist evidence
   is supplied and independently reviewed. Unknown status is a format_change-style failure,
   never automatic source inactivation. Fixtures contain no P/E/R/B cells; none are invented.
2. The native-code shape rule is a deliberate DUPLICATE of the collector's (independence
   ruling); the JSON-side dimension-id pinning gap noted in the Part A review is not repeated
   here either - CSV identity is pinned through the 9 key code cells (header order per the
   reviewed families), not through dimension ids. A publisher column-order change across those
   dimensions fails closed rather than mis-pinning.
3. CsvFixtureHttp serves request windows bounded by the archived row extent only (row-level
   TIME_PERIOD filter = publisher window semantics; full-extent requests are served
   byte-identical to the pinned originals, sha256-asserted in-test). Mutations are explicit
   in-test overrides; no mutated bytes are presented as originals.
4. Live acceptance (fresh f0nix egress archive, evidence replay, promotion) remains the
   controller's separate gate; the deselected live test is ready but was not run here.
5. Per-dataset third-party rights clearance (DF_CLI/DF_BTS/DF_IALFS_UNE_M) is still the owner's
   outstanding duty before any serving; redistribution_ok stays false.
