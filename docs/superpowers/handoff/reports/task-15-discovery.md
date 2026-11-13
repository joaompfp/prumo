# Task 15 - OECD discovery report (read-only research)

Date: 2026-11-12. Researcher: subagent (kimi-k3), read-only discovery scope. No code, registry, handoff or
ledger changes were made. All network evidence archived under
`docs/superpowers/handoff/evidence/task-15-oecd/discovery/` with `manifest.json`
(sha256 `09dad8d1f5d082712aaa30309e13de0f4b52195eaa8b508836fa517c735211c1`) recording per item: request
timestamp, requested/final URL, actual HTTP status, byte length, sha256, body file.

Scope covered: 6 active core monthly PT series - `oecd.cli.PT` (DF_CLI), `oecd.employment.PT`,
`oecd.order_books.PT`, `oecd.production.PT`, `oecd.selling_prices.PT` (DF_BTS), `oecd.unemp_m.PT`
(DF_IALFS_UNE_M, cross_check of `unemployment_rate.PT.M`, INE primary). Registry ids/keys/roles preserved;
active flags untouched.

## 0. Network budget and limits of the record

- Requested limits: <=30 requests, <=360 s for the whole network phase, <=12 s/request,
  no automatic retries, <=15 data-API requests/min.
- The manifest archives 20 items: 17 original HTTP response captures (12 data responses,
  one codelist 404, one f0nix data probe, three CMS challenge responses) and three derived
  web-extraction documents. A web-extraction document is not an original HTTP response;
  its publisher HTTP status and exact request time were not exposed by the tool.
- Archived direct-request timestamps run from 2026-11-12T14:16:24.767769Z to
  14:20:02Z. The later web-extraction windows are approximate. These timestamps do not
  establish an end-to-end <=360 s phase, so compliance with that total deadline is not claimed.
- The researcher reported additional requests not separately archived, including the failed
  local f0nix capture and a CMS probe from f0nix. The earlier headline of 21 direct requests
  is not reconstructable from this manifest and must not be treated as an audited total.
  The tool trace records two search calls and two extraction calls; these tool-call counts
  are distinct from publisher HTTP request counts. Complete wire-attempt accounting is unavailable.
- All 12 original data responses, the codelist negative and the representative f0nix data
  response retain their actual status, URL, length and hash. The controller independently
  rehashed all 20 archived items and re-compared all 77 JSON/CSV observations successfully.
- sdmx.oecd.org was reachable from both egresses. The archived CMS responses from f3nix
  are Cloudflare challenges (403 "Just a moment..."); the reported f0nix CMS challenge was
  not separately archived. None of this weakens the original data bytes or supplies missing
  metadata for the derived web text.

## 1. What legacy `cli`/`bts`/`unemp_m` actually were (from repo code, not names)

`collectors/oecd.py` + orchestration `scripts/backfill_full.py:307-363` and
`scripts/backfill_missing.py:116-161` (sole OECD writers of the legacy export; `collect_scheduled.py` lists
no OECD methods). Verified against `/home/joao/projects/_legacy_export/indicators.csv` (fetched
2026-03-15):

| legacy indicator | legacy call | resolved SDMX key (hypothesis from brief, all confirmed live) | rows |
|---|---|---|---|
| `cli` | `get_cli("PRT", measure="business_confidence", months=620)` | `OECD.SDD.STES,DSD_STES@DF_CLI` key `PRT.M.BCICP.IX._Z.AA.IX._Z.H` | 470, 1987-01.. |
| `employment` | `get_bts("PRT","employment")` default horizon FT | `OECD.SDD.STES,DSD_STES@DF_BTS` key `PRT.M.EM.PB.C.Y._Z.FT.N` | 326 |
| `order_books` | `get_bts("PRT","order_books")` default horizon C | key `PRT.M.OB.PB.C.Y._Z.C.N` | 326 |
| `production` | `get_bts("PRT","production")` default horizon T | key `PRT.M.PR.PB.C.Y._Z.T.N` | 326 |
| `selling_prices` | `get_bts("PRT","selling_prices")` default horizon FT | key `PRT.M.SP.PB.C.Y._Z.FT.N` | 326 |
| `unemp_m` | `get_unemployment("PRT")` args age=Y_GE15 sex=_T | `OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M` key `PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M` | 517, 1983-.. |

Critical identity finding: legacy `cli` is **not** the OECD headline CLI. It is the OECD **Business
Confidence Index (BCI, MEASURE=BCICP, "Composite business confidence")**, amplitude adjusted, long-term
average = 100, living in the DF_CLI ("Composite leading indicators") dataflow. The dataflow's DEFAULT
annotation (item 1 body) is `MEASURE=LI,ADJUSTMENT=AA,FREQ=M,METHODOLOGY=H` - a different measure (`LI`,
the headline composite leading indicator) exists; keys must be pinned explicitly, never defaulted. The
registry unit prose "index (100=trend)" matches the publisher definition ("amplitude adjusted index,
long-term average = 100", item 20) and the amplitude-adjusted pin `ADJUSTMENT=AA`. Legacy id names are kept
as-is per briefing; only the semantic note matters.

Legacy stored values are **float-reformatted artifacts**, not publisher tokens: the old parser did
`float(value_str)` and DuckDB re-serialised (`-12` became legacy `-12.0`). Legacy values belong to the
2026-03-15 vintage and must never be used as expected test values (see §6 revisions).

## 2. Live-confirmed coordinates (all 6 unique keys checked, all HTTP 200)

All requests bounded `startPeriod=2025-10`. Evidence items: JSON=1,3,5,7,9,11; CSV=2,4,6,8,10,12.

| series | dataset (structure version) | dimension order (keyPosition) and pinned values |
|---|---|---|
| oecd.cli.PT | OECD.SDD.STES:DSD_STES@DF_CLI (4.1) | 0 REF_AREA=PRT Portugal, 1 FREQ=M Monthly, 2 MEASURE=BCICP Composite business confidence, 3 UNIT_MEASURE=IX Index, 4 ACTIVITY=_Z Not applicable, 5 ADJUSTMENT=AA Amplitude adjusted, 6 TRANSFORMATION=IX Index, 7 TIME_HORIZ=_Z Not applicable, 8 METHODOLOGY=H OECD harmonised |
| oecd.employment.PT | OECD.SDD.STES:DSD_STES@DF_BTS (4.0) | REF_AREA=PRT, FREQ=M, MEASURE=EM Employment, UNIT_MEASURE=PB Percentage balance, ACTIVITY=C Manufacturing, ADJUSTMENT=Y Calendar and seasonally adjusted, TRANSFORMATION=_Z, TIME_HORIZ=FT Future tendency, METHODOLOGY=N National |
| oecd.order_books.PT | DF_BTS (4.0) | same but MEASURE=OB Order books, TIME_HORIZ=C Current |
| oecd.production.PT | DF_BTS (4.0) | same but MEASURE=PR Production, TIME_HORIZ=T Tendency |
| oecd.selling_prices.PT | DF_BTS (4.0) | same but MEASURE=SP Selling prices, TIME_HORIZ=FT Future tendency |
| oecd.unemp_m.PT | OECD.SDD.TPS:DSD_LFS@DF_IALFS_UNE_M (1.0) | 0 REF_AREA=PRT, 1 MEASURE=UNE_LF_M Monthly unemployment rate, 2 UNIT_MEASURE=PT_LF_SUB Percentage of labour force in the same subgroup, 3 TRANSFORMATION=_Z, 4 ADJUSTMENT=Y Calendar and seasonally adjusted, 5 SEX=_T Total, 6 AGE=Y_GE15 15 years or over, 7 ACTIVITY=_Z, 8 FREQ=M Monthly |

Publisher UI cross-validation (item 20): OECD indicator page's own Data Explorer deep link is
`df[ds]=dsDisseminateFinalDMZ, df[id]=DSD_STES@DF_CLI, df[ag]=OECD.SDD.STES, dq=.M.BCICP...AA...H` -
identical agency/dataflow/key-pin to the discovered CLI coordinates.

Series-level attributes (both channels): `UNIT_MULT=0` ("Units") and `DECIMALS=2` (CLI, all BTS) /
`DECIMALS=1` (unemp_m). `BASE_PER` column exists in CSV and is **empty** on every row. Dataset `action=I`
(Information). Structure annotation `NonProductionDataflow=true` on these dataflows (OECD internal flag;
recorded, no action). Sender id `Disseminate_Final_DMZ`.

## 3. The two independent channels (genuinely different formats - requirement met)

### A. Collector channel: SDMX-JSON data 2.0 (recommended collector)

- Request: `GET https://sdmx.oecd.org/public/rest/data/<agency>,<DSD>@<dataflow>/<key>?startPeriod=2025-10`
  with header `Accept: application/vnd.sdmx.data+json;version=2.0`. Response content-type
  `application/vnd.sdmx.data+json; version=2.0; charset=utf-8`. No auth, no redirect (final URL == requested).
- Shape: `data.structures[0].dimensions.series` (9 dims, keyPosition 0..8) + one observation dimension
  TIME_PERIOD (keyPosition 9); `data.dataSets[0].series` with a single series keyed `0:0:...:0`;
  observations as `"<index>": [<value>, <obs_status_attr_index>]`.
- **Observation values are genuine JSON number primitives** in the body text (e.g. `99.83678`, `-12.0`,
  `100.321`), never quoted strings. Collector must parse with token preservation
  (`json.loads(parse_float=str, parse_int=str)` style per Ruling on typed-tagged tokens), rejecting quoted
  numerics per the pipeline rule.
- **TIME_PERIOD values list is NOT sorted** (order observed e.g. 2026-02, 2026-03, …, 2025-10, 2025-11 on
  CLI). The parser MUST map each observation index to `dimensions.observation[0].values[i].id`; never
  assume ordering, never zip sorted.
- Missing observations = absent keys (sparse). None in window.
- OBS_STATUS exposed as observation attribute with values table; only `A` ("Normal value") occurred
  (77/77 observations).
- `meta.prepared` echoes request time; `meta.schema` = sdmx-json-data-schema 2.0.0.

### B. Verifier channel: labelled SDMX CSV, different format family (recommended verifier)

- Request: same path, query `?startPeriod=2025-10&format=csvfilewithlabels&dimensionAtObservation=AllDimensions`.
  Response `application/vnd.sdmx.data+csv; charset=utf-8; labels=name; version=2.0`.
- One header row, then one row per observation: every dimension as code column + label column
  (e.g. `MEASURE`,`Measure`), then `TIME_PERIOD`, `OBS_VALUE`, `OBS_STATUS`+label, `UNIT_MULT`, `DECIMALS`,
  `BASE_PER` (+ `ACTION`, `STRUCTURE*` housekeeping). Unemp CSV orders BASE_PER/OBS_STATUS differently -
  parse by header name, not column position.
- OBS_VALUE tokens are unquoted plain text. Empty value = missing (none observed).
- **csvfilewithlabels trims trailing `.0` from integer-valued observations**: publisher pairs
  JSON↔CSV observed raw-byte-level: `employment 2026-05` `-6.0`↔`-6`; `order_books` `-9.0`↔`-9` (2025-11),
  `-12.0`↔`-12` (2026-01), `-10.0`↔`-10` (2026-08), `-14.0`↔`-14` (2026-09); `selling_prices 2026-01`
  `12.0`↔`12`; `unemp_m 2026-02` `6.0`↔`6`. Every such pair is Decimal-equal. The JSON channel preserves the
  publisher's DISPLAY precision (consistent with DECIMALS attr) - another reason it must be the collector.
- No shared parser code between channels is needed or allowed: JSON parser (structure/indices) and CSV
  parser (header-name row mapping) share nothing. Independence guard compatible.

## 4. Cross-channel exact comparison (all archived bodies, offline-computable)

| series | obs | periods | token-identical pairs | Decimal-identical pairs |
|---|---|---|---|---|
| cli | 13 | 2025-10..2026-10 | 13/13 | 13/13 |
| employment | 13 | 2025-10..2026-10 | 12/13 | 13/13 |
| order_books | 13 | 2025-10..2026-10 | 9/13 | 13/13 |
| production | 13 | 2025-10..2026-10 | 13/13 | 13/13 |
| selling_prices | 13 | 2025-10..2026-10 | 12/13 | 13/13 |
| unemp_m | 12 | 2025-10..2026-09 | 11/12 | 12/12 |

Sample named values (period: CSV token / JSON token - status A unless noted):

- cli: 2025-10 `99.94156`/`99.94156`; 2025-11 `100.2412`/`100.2412`; 2025-12 `100.321`/`100.321`;
  2026-01 `100.2026`/`100.2026`; 2026-10 `99.80521`/`99.80521`; 2026-04 `99.83678`/`99.83678` (5 dp).
- employment: 2026-01 `4.1`/`4.1`; 2026-02 `3.4`/`3.4`; 2026-05 `-6`/`-6.0` ← string differs, Decimal equal;
  2026-08 `-4.4`/`-4.4`; 2026-10 `-5.7`/`-5.7`; UNIT PB.
- order_books: 2025-10 `-12.5`/`-12.5`; 2026-01 `-12`/`-12.0` ←; 2026-09 `-14`/`-14.0` ←; 2026-03
  `-13.4`/`-13.4`; 2026-08 `-10`/`-10.0` ←.
- production: 2025-10 `1.4`/`1.4`; 2026-01 `3.8`/`3.8`; 2026-02 `-7.9`/`-7.9`; 2026-04 `-1.1`/`-1.1`;
  2026-10 `-2.2`/`-2.2`.
- selling_prices: 2025-10 `5.1`/`5.1`; 2025-12 `10.7`/`10.7`; 2026-01 `12`/`12.0` ←; 2026-05 `28.4`/`28.4`;
  2026-09 `22.4`/`22.4`.
- unemp_m: 2025-10 `5.8`/`5.8`; 2026-01 `5.8`/`5.8`; 2026-02 `6`/`6.0` ←; 2026-07 `5.7`/`5.7`;
  2026-09 `5.6`/`5.6`. DECIMALS=1.

Verdict: the CSV verifier channel achieves **exact Decimal match** against JSON-collected tokens for all 77
observations with zero tolerance - no blocker. It must NOT assert raw-token string equality (7 cells would
fail by publisher-side formatting only). Status/unit surfaces: CSV gives OBS_STATUS code+label, UNIT_MULT,
DECIMALS, BASE_PER (empty); JSON gives OBS_STATUS index→code and the same series attributes.

## 5. Units, multiplier, adjustment, flags (publisher-confirmed)

- Units: CLI `UNIT_MEASURE=IX Index` with `TRANSFORMATION=IX`, `ADJUSTMENT=AA Amplitude adjusted`; publisher
  prose (item 20): "amplitude adjusted index, long-term average = 100" → registry unit
  `index (100=trend)` is the correct prose; keep it. BTS `PB Percentage balance` → registry `balance %`
  correct. Unemp `PT_LF_SUB Percentage of labour force in the same subgroup` → registry `%` correct.
- UNIT_MULT=0 ("Units") everywhere → **no scaling ever**; fail closed if any other value appears.
- DECIMALS=2/1 is a display hint only - CLI publishes 4-5 dp tokens (`99.83678`); never round/truncate.
- BASE_PER empty everywhere in window.
- OBS_STATUS: only `A` ("Normal value") observed. Full OBS_STATUS codelist NOT enumerable within budget
  (agency codelist probe returned 404 "No Results Found", item 13 - do not trust my guessed id; the JSON
  response embeds only the used value). Policy per obligations: map `A`→verified-normal; **any other code
  fails closed** (quarantine + report), do not pre-map unseen codes.
- Flag surface exists on both channels → verifier reports observed_flag honestly.

## 6. Revisions / vintage (material finding)

Overlapping periods vs the 2026-03-15 legacy vintage: 20 of 29 cells differ (cli 5/5, production 5/5,
selling_prices 5/5, employment 3/5, unemp_m 2/4, order_books 0/5). E.g. cli 2026-01: legacy `100.2085` →
current `100.2026`; unemp_m 2026-01: legacy `5.6` → current `5.8`. BTS balance series and the
amplitude-adjusted CLI are routinely revised; unemployment revised too. Consequences: (a) never freeze
expected live values in tests - pin tests to archived fixtures; (b) revision events at ingest are normal
behaviour, not anomalies; (c) legacy rows stay as first-vintage history per spec.

Coverage/lag observed 2026-11-12: business survey series published through 2026-10; monthly unemployment
through 2026-09 (~2-month publication lag). Both respect `startPeriod` bounds.

## 7. Licence research (official current terms)

Evidence: items 15-17 are the archived f3nix CMS challenge bodies. The researcher also
reported a f0nix challenge, but no original body of that CMS request was archived. The
earlier 403 note in `registry/licences-todo.md` reflects a bot-wall, not absence of the page.
Items 18/19 are derived extraction text, and item 20 is the extracted indicator definition.

Canonical pages: `https://www.oecd.org/en/about/terms-conditions.html` ("Last updated on 1 July 2024"),
Open Access policy `https://www.oecd.org/en/about/oecd-open-by-default-policy.html`. Registry
`licence_url` `https://www.oecd.org/termsandconditions/` still resolves (403 for curl; same Cloudflare
behaviour) - recommend updating the registry note to the canonical `/en/about/terms-conditions.html` at
implementation time (no registry edit made here).

Exact grants relevant to statistical data - T&C §3 "Data" (quoted verbatim from item 18):

> "The OECD makes data (the “Data”) available for use and consultation by the public. Data may be subject
> to restrictions beyond the scope of these Terms and Conditions, either because specific terms apply to
> those Data or because third parties may have ownership interests. It is the user’s responsibility to
> verify, either directly in the metadata or, if available, by clicking on the icon and then referring to
> the \"source\" tab, whether the Data is fully or partially owned by third parties and/or whether
> additional restrictions may apply, and to contact the owner of the Data before incorporating it in your
> work in order to secure the necessary permissions."

> Permitted Use: "Except where additional restrictions apply as stated above, you can extract from,
> download, copy, adapt, print, distribute, share and embed Data for any purpose, even for commercial use.
> You must give appropriate credit to the OECD by using the citation associated with the relevant Data, or,
> if no specific citation is available, you must cite the source information using the following format:
> OECD (year), (dataset name),(data source) DOI or URL (accessed on (date)). When sharing or licensing work
> created using the Data, you agree to include the same acknowledgment requirement in any sub-licenses that
> you grant, along with the requirement that any further sub-licensees do the same."

Caveats quoted verbatim: §3 "Availability of Data" reserves rights "to modify the amount of Data you may
request in a single query, to modify the number of queries you may make over a specified time, to remove
certain Data and to alter the file formats"; §3 APIs: APIs are "as-is", may be suspended, users must not
reverse engineer APIs; T&C §1.1: "most OECD written content published as of 1 July 2024 is licensed under a
Creative Commons Attribution BY 4.0 licence (CC BY 4.0)" (written content, with attribution
"[OECD (year), Title, URL]"; logo/branding excluded); Open Access policy: "The default licence applied by
the OECD is Creative Commons Attribution 4.0 (CC BY 4.0), but others might apply in exceptional cases."

Assessment for the owner (decision not taken here): OECD **data** reuse is governed by the §3 bespoke grant
(redistribution OK for any purpose incl. commercial, with attribution and sub-licence acknowledgment
propagation), NOT literally CC BY 4.0 (that covers written content; the `licences-todo.md` "believed CC BY
4.0" note should be corrected to this wording). The material caveat is the **per-dataset third-party
ownership check duty** - BTS inputs are national survey data and CLI is computed from national components.
Until the owner confirms the three dataflows carry no third-party restriction (metadata/source-tab check)
and accepts the attribution wording, `redistribution_ok: false` / `UNVERIFIED` must stand. Suggested
attribution if accepted: `Source: OECD (year), Business tendency surveys / Composite leading indicators /
Monthly unemployment rates, sdmx.oecd.org (accessed YYYY-MM-DD)`.

## 8. Egress results

- f3nix: all 13 sdmx.oecd.org requests 200/expected-404 quickly (<1.1 s). Content-type headers as in §3.
- f0nix (read-only ssh probe, no remote persistence): unemployment CSV 200 in 0.069 s, body
  **byte-identical** (sha256 c46c6c33… == item 12). Representative format confirmed from production egress.
- www.oecd.org CMS: 403 Cloudflare challenge from both egresses with curl (plain and browser UA); content
  obtained via the defuddle tool egress instead. If a future task needs raw CMS bytes, use a real browser.

## 9. Errors and anomalies (observed, honest)

1. Item 13: `GET …/rest/codelist/OECD.SDD.STES/CL_OBS_STATUS` → HTTP 404, body `No Results Found` (16 B).
   Publisher-side negative; full OBS_STATUS codelist not enumerated (see §5).
2. f0nix probe first attempt: local capture plumbing failed (`curl 23` writing to `/dev/stdout` over ssh);
   publisher request itself returned, retry captured body and proved byte-identity. Not a publisher failure.
3. Items 15–17: HTTP 403 Cloudflare challenge pages for www.oecd.org (not the data API).
4. No 429 rate limiting, no truncation, no missing observations, no HTML error pages from the data API in
   this window.

## 10. Implementation guidance (offline-ready, no network needed)

Fixtures: use the 12 data bodies (items 1–12; 3.9–23.3 KB each, all ≤200 KB) exactly as archived plus
`manifest.json`; they replay both channels without HTTP, including index→period ordering, trailing-zero and
token cases. Webtext items 18–20 are licence/unit documentation, not parser fixtures.

Collector (`ingest/sources/oecd.py`): SDMX-JSON v2.0 per §3A; one RawResponse per series key;
`RawRow.value_text` = raw JSON token (str-subclass tagging per pipeline rule; values are JSON numbers);
`response_index` per response; never reorder by assuming TIME_PERIOD sort; derive unit/flags from embedded
structure (UNIT_MEASURE/UNIT_MULT/DECIMALS/OBS_STATUS); fail closed on UNIT_MULT≠0, BASE_PER non-empty,
OBS_STATUS≠A, extra series keys, non-number values. `decimal: '.'` stands.

Verifier (`ingest/verifiers/oecd.py`): csvfilewithlabels+AllDimensions per §3B; header-name column mapping;
Decimal-exact comparison (NOT token-exact, per §4); observed_unit from `Unit of measure`,
observed_flag from `Observation status`; enforce structure label identity (unit label strings above).
URL evidence: the exact CSV URLs in manifest.

Registry metadata (already correct per §5; no edits made): keep ids, `native_code`s, roles; attribution
string candidate in §7 pending owner licence sign-off.

Known limitations: OBS_STATUS full codelist not enumerated (fail-closed policy is the mitigation);
per-dataset third-party licence check unperformed (owner duty before serving); BTS/CLI/unemp revisability
means smoke-test counts must be recomputed at acceptance time, not frozen from this report.
