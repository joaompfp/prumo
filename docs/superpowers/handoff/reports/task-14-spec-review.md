# Task 14 — FRED independent SPEC review

**Verdict: PASS** (no blocking spec gaps; 3 non-blocking observations below)
Scope: `pipeline-rebuild` `38aad8c..7b93ab8`, read-only, no fixtures/code mutated.
Reviewer: independent subagent; controller's own counts (source 45 / verifier 33 passed) noted but
everything below was re-derived from actual code, fixtures and registry, not from the
implementer reports. Probe script: `/home/joao/.hermes/cache/scratch/t14_probe.py`.

## What was verified against the authoritative requirements

### Collector (`ingest/sources/fred.py`) — compliant
- `FredSource.name='fred'`; key via explicit arg or `FRED_API_KEY` only; blank key and missing
  key fail clearly; legacy `.fred_api_key` never read (tested from an empty cwd).
- Key on the wire only (query param, FRED-required); archived `RawResponse` is key-free
  (stripped final URL + params omit `api_key`); a body echoing the key is refused **before
  yield**; network errors re-raised as `FredRequestError` (type + endpoint + series id only,
  no URL/key/body); Sentinel sweeps cover success DB/raw-store/event artifacts, HTTP-500 and
  parse-failure paths (`test_pipeline_artifacts_never_contain_the_credential`).
- Envelope fail-closed: `units=lin`, `file_type=json`, `order_by=observation_date`,
  `sort_order=asc`, `output_type==1` asserted — independently reproduced (probe 4c:
  `sort_order='desc'` raises). Count/offset/limit int≥0; page can't exceed limit;
  offset+rows ≤ count. fetch loops to `count`, raises on zero-progress, yields incrementally
  (partial evidence survives mid-fetch failure — tested).
- Values are JSON **strings** preserved verbatim as plain `str`; `.` → `value_raw=None`
  (quarantined `non_numeric`, never truncated); a JSON-number value primitive raises (tested).
  Duplicate JSON keys, HTML error pages, API error shape on 200, unknown top/row fields,
  unknown per-observation status field, non-month-first dates, duplicate dates, realtime
  drift, metadata identity/frequency/NSA/units drift — all fail closed with tests.
- `unit_raw` is the metadata's actual `units` label asserted **equal to** the registry unit
  (never relabelled); `response_index` points at the observations response; metadata responses
  archived rowless; `last_updated` shape-checked metadata only. Verified in the offline
  pipeline test: 12×417 written, 12×144 `non_numeric`, `response_index` odd indices,
  raw_fetch=24, served=0 before and after `verified`.

### Verifier (`ingest/verifiers/fred.py`) — compliant, genuinely independent
- Different host family/endpoint/format: keyless `https://fred.stlouisfed.org/data/<CODE>`
  server-rendered HTML vs keyed API JSON; own `HTMLParser` subclass, **no** collector imports
  (probe: module imports only stdlib + `ingest.http/models/verifiers`; "fredgraph" appears
  only as a rejection note). `register_verifier` allowlist test +
  `assert_verifier_independent` subprocess entry (`tests/ingest/fred_verifier_entry.py`)
  exercises real fixture checks with `ingest.sources` blocked.
- Blind: `BlindItem(series_id, period, spec)` — no expected values; `observed_flag=None`
  honest; `observed_unit` read **from the page metadata** and asserted vs registry (both
  directions of drift tested); `observed_decimal='.'`.
- Strict structural parsing: exactly 1 metadata + 1 observations table, exact metadata key
  set, Series ID/IMF Source/Release/`Global price of ` title prefix/Frequency/Seasonal/
  Units/Date-Range assertions, h1/aria binding, single DATE/VALUE header (extra status column
  raises), month-first dates, strictly ascending, duplicate period raises, declared
  Date Range == first/last row dates, only `.` accepted as missing, value tokens strict ASCII
  decimals verbatim (`N/A`, `1 234.5`, `1e3`, `1.2.3`, blank, unicode all raise — tested),
  truncated page (no closing `</table>`) and nested tables raise (tested).
- Evidence: `fred-table-evidence` v1 envelope — full page bytes (base64) + actual status +
  final URL; one fetch per series per `check()`; offline replay via `read_table_page` tested
  on all 50 sampled items' persisted blobs; tamper test drives a genuine
  `failed-verification` through `verify_run` (served stays 0), `run_with_refetch` registered
  flow verified all 12.
- Live test (`test_live_fred.py`) deselected by default, owner's `FRED_API_KEY` from env only,
  all 12 active registry series, bounded (1 req/s, 120 s timeout, `max_attempts=1`, sample
  120), asserts 417/series `1992-01..2026-09`, `non_numeric`×1728, served=0, and offline
  replay of all 120 envelopes.

### Fixtures / evidence — compliant
- 48 manifest entries, sha256 re-verified, every fixture ≤ 200 KB. Probe re-parsed all 12
  table pages with an **independent** throwaway parser: 417 numeric rows each; API obs bodies:
  561 rows/series with exactly 144 `.`; **0 Decimal mismatches** API-vs-table across all
  5004 values; HTML/API `Units` labels byte-match the registry strings.
- Rejected CSV channel kept only as evidence (`fredgraph-*.csv` fixtures +
  `csv-decimal-mismatches.json`); the verifier reads no CSV. WPU101/MHHNGSP pages/metadata and
  authentic FRED terms archived under `docs/superpowers/handoff/evidence/task-14-fred/`.

### Registry — compliant
- 20 FRED entries; `core.proposed.yaml` mirror content **identical** for all 20 (probe). 12
  active: exact IMF publisher units (verified byte-for-byte against fixtures), `NSA`, `M`,
  `WORLD`, canonical series URL, `active: true`. 8 inactive with original
  unit/fields preserved (incl. `commodity_steel` uncoded; `steel`=WPU101 US index 1982;
  `natural_gas`=MHHNGSP Henry Hub — inactivated, not substituted); the 5 coded twins keep
  primary roles; all ids/indicator_keys/roles/geography unchanged vs base (probe).
- `redistribution_ok: false`, `verifiable: true`, licence UNVERIFIED with the sourced
  rights-not-confirmed comment; legacy bare-USD rows are rejected `unit_mismatch` by the
  existing importer (tested, no importer change); `commodity_cotton` orphan stays
  `not_in_registry` (tested).
- Diff touches only FRED modules/tests/fixtures/registry/docs — no core/HTTP/importer/
  model/dependency changes, no deploy/main interference, no new US concept.

## non-blocking observations (no action required for Task 14)
1. **parse() doesn't assert total completeness against declared `count`.** Each page checks
   `offset+rows ≤ count` and pages must be contiguous, but the per-page `count` is dropped
   (`ingest/sources/fred.py:374-375`) and `expected_offset == count` is never asserted at the
   end. Reproduced: parse accepted a 300-row archive of a `count=561` series and returned 300
   rows silently. `fetch()` guarantees completeness live (loop-to-count + zero-progress
   raise), and the brief's explicit parse-reject list doesn't include count totals — flagging
   as hardening for raw-store replay only, not a spec breach.
2. Verifier `check()` passes no explicit timeout to `http.get` (relies on the injected
   client's default; the live test injects `RequestsHttp(timeout=120)`). Cosmetic.
3. The evidence envelope repeats the full ~94 KB page body per `ItemResult` (one fetch, N
   envelopes). Storage-heavy but exactly what the evidence contract specifies.

## Residual gates (not closeable by this review or any child)
Controller-owned and still OPEN: fresh f0nix-egress full-12 live acceptance with owner key
(`test_live_fred.py -m live`), final full-suite regression, separate quality review, and
Task 17 registration/production SOPS key provisioning.
