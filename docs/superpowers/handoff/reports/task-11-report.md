# Task 11 report — Banco de Portugal (BPstat) adapter + independent verifier

Status: **implementation complete; every acceptance item verified with real evidence.** Baseline
e382ecd → commits `0737a44` (registry), `f6ea108` (source), `b1660e1` (verifier), plus this
report commit. Suite: **735 passed, 3 live deselected** (was 660+2); Ruff 0.17.4 clean on every
touched file (pre-existing I001 in untouched ingest/verifiers/independence.py left alone, as in
Task 10). GitNexus: flags.py impact LOW (2 importers), detect-changes risk LOW, no HIGH/CRITICAL.
No push / merge / deploy / shared-file edits.

## Publisher interfaces (all discovered live 2026-11-11, f3nix; RequestsHttp <=1 req/s, 50 s timeout)

### Collector channel — public documented API (JSON-stat 2.0)
`GET https://bpstat.bportugal.pt/data/v1/domains/<domain>/datasets/<dataset>/?lang=EN&series_ids=<ids>&decimal=true`
- OpenAPI at /data/docs (`?format=openapi`): endpoints series/domains/datasets/dimensions only.
- **`decimal=true`** (documented) returns values as the publisher's fixed-point **strings**
  ("the exact same number of decimal places as displayed in the BPstat website"): '7.1200',
  '1.1608', '42179.6'. Collector hands these over verbatim; registry `decimal: '.'`.
- Throttling: documented `X-Throttle` header (observed 1000) and HTTP 429 when it hits 0; never
  hit at <=1 req/s (f3nix recording+live run, f0nix probe).
- `format=csv` probed and **rejected as verifier channel**: it is a single-row flattened dump of
  the SAME JSON-stat object (columns `value.0..2`, `status.0..2`, `dimension.70.category.label…`)
  — a cosmetic parameter on the same view (brief's forbidden pattern).

### Independent verifier channel — portal internal API (drives the SPA)
Discovered from the live SPA network trace (headless Chromium on f3nix), reproduced by plain
curl AND a 40 s live pipeline run — no JS/auth/cookies/Referer needed:
- `GET /api/observations/?series_ids=<id>&start_date=<m-01>&end_date=<m-eom>` → flat rows
  `{id, version_id, series_id, privacy_code, value(str), reference_date, pub_date, description}`.
  One reference_date can carry **publication vintages**: live revision evidence
  12099464 @2023-08-31 = '3.30' (pub 2023-09-04) → '3.31' (pub 2023-10-03); JSON-stat answers
  '3.31' = latest pub_date. Verifier takes the latest-pub_date row; ties/foreign rows/out-of-window
  dates/non-public codes/non-empty descriptions raise (fail-closed).
- `GET /api/series/?view_full=true&page_size=1&series_ids=<id>` → membercombination with the
  series' own Unit of measure ('Percentage'/'Millions of euros'/'Currency'), Reference territory
  (Portugal/Germany/Euro Area - Changing composition; the EUR/USD series has none and is pinned by
  its currency pair reference EUR + counterparty USD), Periodicity Monthly + recurrence 'M'
  (both surfaces must agree). observed_flag=None: the portal exposes no observation status —
  honestly None, never echoed from the spec, and ingest.verify therefore skips the flag
  comparison (asserted: observed_flag IS NULL for every stored item).
- **Evidence envelope (fix round 1, commit 4d7107e):** an item's decision reads BOTH responses,
  so ItemResult.evidence is a versioned JSON envelope (schema 'bportugal-portal-evidence', v1)
  carrying metadata + observations wire records — final URL, HTTP status, raw body
  base64-encoded, byte-for-byte recoverable from the raw store with no HTTP (Ruling R/G7).
  evidence_url stays the observations URL; request counts unchanged (metadata once per series).

### Identity proof of the two channels
Flattening order of the JSON-stat arrays (last dimension fastest) was adjudicated BY the portal:
Euribor 3m@1994-01 = value[394] = '6.9100' per strides — the portal window answers exactly
'6.9100' (value[1] = '6.9900' belongs to 1m@1994-02). The naive same-block read would have
mis-attributed every multi-series cell.

## Registry (core.yaml; core.proposed.yaml mirrored per the byte-identity invariant test)
- 10 series, all primary, all active, frequency M, decimal '.': bportugal.euribor_{1,3,6,12}m.EA,
  bportugal.eur_usd.EA, bportugal.pt_10y.PT, bportugal.de_10y.DE, bportugal.credit_housing.PT,
  bportugal.credit_consumer.PT, bportugal.deposits_households.PT. native_code
  `<series id>:<domain>/<32-hex dataset>`; url = the series' portal page.
- Units from BPstat metadata only: '%' (Percentage), 'USD/EUR' (unit 'Currency' + pair), 'MEUR'
  ('Millions of euros'); multiplier null (never rescale publisher values — M€ stays publisher M€).
- **Geography corrections vs the legacy PT default** (publisher metadata): Euribor = EA
  ('Euro Area - Changing composition'), eur_usd = EA (no territory dim; euro external reference
  rate convention), de_10y = DE. Legacy BPORTUGAL rows stay quarantined (Ruling V, blank units)
  under their old `.PT` unclassified ids; spread_pt_de excluded (computed, out of scope).

## Licence (bpstat.bportugal.pt/avisos-legais, "Direitos de autor", rendered live 2026-11-11)
"A utilização da informação obtida diretamente no BPstat é livre, mas está sujeita às seguintes
condições: A distribuição ou reprodução da informação deve efetuar-se com exatidão e referir o
Banco de Portugal como a fonte; Se a informação for modificada pelo utilizador, tal facto deve
ser explicitamente mencionado." → free use + attribution; redistribution_ok: true, attribution
'Fonte: Banco de Portugal', terms quoted verbatim in the YAML source block. No named public
licence (no CC) exists; recorded as custom terms.

## Status/flags
Observed vocabulary across all 10 series' full history (~33,400 valued cells) + a domain-31
quarterly national-accounts probe: only 'F' on valued cells, `null` beside `null` values.
BPstat publishes no code legend (OpenAPI: nullable string). map_bportugal_flag (flags.py,
additive): 'F'→normal; any other code / status on a valueless cell / missing status on a valued
cell raise (fail-closed; first sighting forces a review). Valueless cells (de_10y 1993-07..
1999-12, 78 cells) → value-None rows → non_numeric quarantine.

## Tests (TDD: flags RED import-error; source RED module-missing 26 failed; then GREEN; fix
round 1 below RED first as well)
- 48 source tests: 18 named cells (exact token/period/flag, ALL cross-checked live through the
  portal channel at fixture recording, 27/27 agree), trailing-zero tokens, status battery,
  html/JSON/error-body rejection, truncated/duplicate-period/double-mapped/wrong-series/
  wrong-unit/wrong-frequency/wrong-territory payloads, native-code parser, fetch grouping/params,
  legacy 3-param Http doubles, recorded pipeline run (4,318 written + 78 quarantined
  non_numeric). **Sparse cell columns (real coverage — the earlier draft listed "sparse" here
  with no actual test):** dense↔canonical-sparse fixture equivalence parses IDENTICALLY (values
  AND statuses, the 78 DE value-None cells included), non-canonical alias keys
  ('00', '01', '+1', ' 1', '٣', '1_0') raise fail-closed before any row is written
  (pipeline-level failed-validation, 0 observation/quarantine rows), out-of-bounds keys raise.
- 22 verifier tests: every recorded case, vintage rule, empty-month not-found, per-series unit
  surfaces {'%','MEUR','USD/EUR'}, tamper/misroute/privacy/description/recurrence/markup
  batteries, register_verifier allowlist, **subprocess independence** (collector+flags blocked),
  recorded end-to-end verified (seed=7, size=16) with served=4,318, and tamper detection
  (pt_10y 2026-10 '3.92'→'3.93' → failed-verification, exactly `value differs`, 0 served).
  **Evidence envelope:** each item's evidence decodes offline to BOTH recorded portal wire
  records (metadata + observations, exact URL/status/body vs fixtures); cached metadata shared
  across a series' items while each envelope carries its own observations body; the pipeline's
  archived evidence_sha256 reloads from the raw store (integrity-checked, no HTTP) into both
  responses for all 16 sampled items.
- Registry unit/territory/frequency tables cover all 10 active series keyed by native id;
  native-code uniqueness/completeness tests included.

## Live smoke (real, 2026-11-11, f3nix, deselected by default)
`.venv-ci/bin/python -m pytest tests/ingest/test_live_bportugal.py -m live -s` → **PASSED in 40.6 s**:
run_with_refetch over all 10 active series → **verified**; 4,318 written, 78 quarantined,
**served = 4,318**; verification sample 24 items passed 100% on the live portal channel.
Per series: euribor×4 394 (1994-01..2026-10), eur_usd 334 (1999-01..2026-10), pt_10y 400
(1993-07..2026-10), de_10y 322 (2000-01..2026-10), credit×2 + deposits 562 (1979-12..2026-09).
No empty/failed series; no 429; quarantines exactly the 78 DE pre-start empty cells.
f0nix probe (ssh f0nix, no deploy, no infra changes): both channels HTTP 200,
x-throttle: 1000 — public access confirmed from the edge host.

## Notes for the controller / T17-18
- Scheduler: register BPortugalVerifier; bportugal carries no timeout_s (sub-second API);
  RequestsHttp default 30 s is ample; keep <=1 rps pacing.
- Evidence tooling (replay/audit): since commit 4d7107e the archived verify-bportugal evidence is
  the 'bportugal-portal-evidence' v1 JSON envelope, not the bare observations body — decode
  {metadata, observations}[].body_b64 to recover the exact publisher bytes.
- Portal rows expose `pub_date` per vintage — a future revision-history task can mine
  /api/observations/ wide windows (61 months = 61 rows + vintages seen).
- 'Currency' unit + EA geography for eur_usd are reviewed conventions (documented in both code
  and test tables); a different currency pair fails closed, forcing review.
- flags.py got one additive block (gitnexus risk LOW); no other shared-framework edits.

## Fix round 1 (2026-11-11, independent-review follow-up; commits cc094b9 + 4d7107e + this one)

Two tightly scoped findings, both implemented TDD (regression tests RED first, then GREEN):

- **I1 — audit evidence gap (verifier).** The metadata cache kept only the parsed unit string and
  ItemResult.evidence held only the /api/observations/ body, so the unit verification was not
  auditable from the archived bytes. Now: cache keeps (unit, exact HttpResult); evidence is the
  versioned envelope described above (stdlib json+base64 only — base64 was already in
  VERIFIER_STDLIB_IMPORTS, no allowlist/schema change; ItemResult.evidence stays arbitrary
  bytes). No expected values echoed, no parser helpers shared; compare/tamper semantics
  unchanged (tamper batteries green). Request counts unchanged.
- **I2 — actual data corruption (source).** _cells_column accepted sparse aliases: '0' and '00'
  int()-fold onto the same cell and the later key silently overwrote the earlier
  (repro: {'0':'1.10','00':'2.20'} → ['2.20', None, None]). Now every sparse key must be the
  canonical ASCII decimal str(int(k))==k; '00', '01', '+1', ' 1', Unicode digit aliases
  ('٣'), '1_0' all raise before any row is written. Also makes the report's sparse-coverage
  claim true (it previously described no real test).

Verification: full suite **751 passed, 3 live deselected** (739 at 8c31802 + 12 new tests);
Ruff 0.17.4 clean on the four touched files; verifier allowlist and subprocess-independence
tests still pass. GitNexus detect-changes on the diff: affected processes exactly
`BPortugalVerifier.check` and `parse → _cells_column`, nothing else. Fixture-based only; no new
endpoint research or live calls. Deferred minors untouched (naive/aware pub_date diagnostic,
raw-missing pin-category diagnostic). No shared files, no push/merge.
