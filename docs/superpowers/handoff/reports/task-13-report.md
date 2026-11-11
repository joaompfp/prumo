# Task 13 — World Bank source + independent verifier (implementer report)

Date: 2026-11-11. Implementer: fresh Task13 agent. Branch `pipeline-rebuild`, worktree
`/home/joao/projects/prumo-pipeline`, base dcec55d. Commits: `0a4458f` (registry
dispositions), `173638c` (source + verifier + tests + fixtures), report commit follows.

## What was built

- `ingest/sources/worldbank.py` — `WorldBankSource` for the keyless API v2 JSON channel:
  one request per indicator carrying that indicator's full registry geography set
  (`/v2/country/<geo;…>/indicator/<CODE>?format=json&per_page=20000`, geos sorted), pagination
  followed with cross-checked page/pages/per_page/total; 18 responses for the 930 active
  series. Exact publisher number tokens via `_Num` tagging (quoted numerics rejected even when
  numeric-shaped, exponent tokens preserved for the validator to quarantine), genuine-string
  identity labels, countryiso3code == native ISO3 AND country.id == registry geography asserted
  per row, non-empty unit/obs_status fail closed (both surfaces empty in all evidence →
  unit_raw=None, flag_raw='normal'), nulls → value_raw=None (never zero-filled), duplicates/
  truncation/shape/HTML/error-JSON/non-2xx fail closed, per-row response_index provenance.
- `ingest/verifiers/worldbank.py` — `WorldBankVerifier` on the genuinely different publisher
  bulk CSV ZIP channel (`/v2/en/indicator/<CODE>?downloadformat=csv`), one ZIP per indicator
  cached inside check() only; in-memory bounded reads (≤3 members, per-member 64 MiB and
  128 MiB total caps, realized-length == declared-size integrity, path/name/member guards);
  year/identity read from the table itself; empty cell ⇒ not-found (never zero); no unit/
  status surface in this channel ⇒ observed_unit=observed_flag=None honestly; evidence =
  versioned `worldbank-csv-evidence` v1 envelope with the exact deciding ZIP bytes, final URL
  and actual HTTP status (offline-recoverable, replay_item-verified). Blind: no expected
  values, no collector imports; passes register_verifier's static allowlist and the
  assert_verifier_independent subprocess guard (entrypoint exercises real fixtures).

## Registry dispositions (truthful, mirrored to core.proposed.yaml)

- All 982 worldbank series gained canonical `native_code: <indicator>:<publisher ISO3>`
  (unique per active series) and `url: /v2/country/<ISO3>/indicator/<CODE>`.
  ISO3 codes derive from the publisher's own `/v2/country?format=json&per_page=400` bytes
  (controller-pinned sha256 c9acf393…44bce, archived as a test fixture): all 54 registry
  geographies map 1:1 via iso2Code→id (EU→EUU, GR→GRC, PT→PRT, AT→AUT spot-verified on payload
  bytes). The 22 series lacking native_code were filled from the reviewed 1:1 concept→indicator
  table that is consistent across all 960 pre-existing codes. **The researcher's "all EU/GR"
  claim was wrong**: the set includes `worldbank.unemployment_wb.AT` (AT) plus 21 EU/GR rows.
- **Unit-definition conflict: ALL 52 `gdp_per_capita_ppp` series set `active: false`**, listed
  individually in `registry/unmapped-worldbank.md`. Publisher metadata for NY.GDP.PCAP.PP.CD
  (controller-pinned sha256 a95c4834…a1a8d, archived): "GDP per capita, PPP (current
  international $)" with sourceNote explicitly "expressed in current prices"; registry units
  `USD (2017 PPC)`/`USD (2017)` declare constant 2017. No swap/substitute was made
  (NY.GDP.PCAP.PP.KD is a *different* 2021-base indicator, verified live).
- Remaining 18 indicators audited against all 19 archived indicator-metadata responses: no
  further genuine unit/definition conflicts. English/PT label aliases (`% PIB`='% of GDP',
  `hab.`='persons', `/1000`='per_1000', `anos`='years', `0-100`=Gini) codified with sourceNote
  justification in `tests/ingest/test_registry_worldbank_units.py`; registry units NOT
  normalized. No series inactivated for slow publication (latest-period distribution reported
  below).
- Licence: CC BY 4.0 re-confirmed (sourceOrganization is provenance, not a licence exception);
  `redistribution_ok: true`, attribution 'Source: World Bank', `verifiable: true` recorded.
- `unemployment_wb` keeps its `unemployment_rate.<geo>.A` indicator_keys (shared namespace
  intentional; keys are not unique series identity — native_code/series_id are).

## Evidence

28 real publisher fixtures ≤200 KB each under `tests/ingest/fixtures/worldbank/`
(sha256-pinned MANIFEST.json; the 6 intake files are byte-identical to the
controller-reverified bundle — hashes recomputed here; PPP/country metadata byte-identical to
the controller pins; the 5 PT-GDP-2021..2025 cross-channel pins re-derived: 5/5 exact token
matches). The GDP CSV ZIP is the full 142 909-byte archive (main CSV 297 580 bytes
uncompressed inside the ZIP), never a truncated substitute. Additional implementer probes
(19-indicator metadata sweep, POP/UEM ZIPs, EU;GR;AT page) logged with status/bytes/sha256 in
`/home/joao/.hermes/cache/scratch/prumo-task13-impl/fetch-manifest.json`.

## TDD log (actual outputs)

- RED: tests written first; collection error (module missing) on all three new test files.
- GREEN (local runs):
  - `test_source_worldbank.py`: 39 passed
  - `test_verifier_worldbank.py`: 25 passed (incl. register_verifier, subprocess independence,
    tamper-through-verify_run "value differs", tampered geography "not found", offline evidence
    recovery + replay_item)
  - `test_registry_worldbank_units.py`: 9 passed
- Full suite: `.venv-ci/bin/python -m pytest tests -q` → **909 passed, 5 deselected,
  1 warning in 157.88s** (baseline was 836/4-deselected; +73 new tests).
- `.venv-ci/bin/ruff check` on all touched Python: **All checks passed!** (a pre-existing I001
  in ingest/verifiers/independence.py predates this task and was left untouched.)

## Live runs (real network, ≤1 req/s, UA prumo-ingest/1.0, scratch DBs)

### A. Full all-active scope (930 series) — fetch+parse OK, verification FAILED CLOSED on a
publisher-side outage of the CSV export endpoint
- run_dataset: `pending-verification`, **18 raw JSON responses (one per active indicator,
  single page each)**, **45 915 observations written**, **15 465 quarantined** (all
  `non_numeric` = publisher null cells preserved, never zero-filled), **0 empty series**
  (all 930 populated). Latest period distribution: 2025×624, 2024×194, 2023×64, 2022×9,
  2021×6, 2020×3, 2018×2, 2015×2, 1994×11 (gov_debt), 1960×3 (gini ST/CV/…), plus single
  1990/1992/1993/2000/2007/2009/2014/2017 stragglers — slow official releases, NOT
  discontinued/rebased; left active as ruled.
- verify_run: drew a **930-item sample** (latest per populated series → larger than 50, as
  designed) and failed closed: the CSV export endpoint `…/en/indicator/NE.EXP.GNFS.ZS
  ?downloadformat=csv` answered **HTTP 400 (ASP.NET "Request Error" page, ~150 s server-side,
  read from a real `requests` probe)**; run state `failed-verification`, served=0 for that
  run. verifier note recorded: "answered HTTP 400 (fail closed on every non-2xx)".
- Outage map (probed 2026-11-11 ~20:30–21:30 UTC, throttled singles, archived terminal logs in
  scratch): the bulk CSV export currently works for 10 of 18 active indicators
  (NY.GDP.MKTP.CD, NY.GDP.PCAP.CD, SP.POP.TOTL, SL.UEM.TOTL.ZS, GC.DOD.TOTL.GD.ZS,
  SI.POV.GINI, SL.EMP.TOTL.SP.ZS, SP.DYN.CBRT.IN, SP.DYN.CDRT.IN, SP.URB.TOTL.IN.ZS — all
  200 application/zip in ≤0.3 s, several re-downloaded byte-identical) and is **broken
  server-side** for 8 (NE.EXP/NE.IMP/NE.RSB.GNFS.ZS, BX.KLT.DINV.WD.GD.ZS, GB.XPD.RSDV.GD.ZS,
  NY.GDP.MKTP.KD.ZG, SL.TLF.CACT.FE.ZS, SP.DYN.LE00.IN — read timeouts at 75 s, NE.EXP also
  twice HTTP 400 after ~151 s; a country-scoped variant answered once after 62.5 s then timed
  out: flaky generation backend, not request shape). Re-probed after ~50 min: still broken.
  The JSON channel remained healthy for all 18 indicators throughout.

### B. Healthy-channel subset (516 series, the 10 working indicators) — fully VERIFIED
  via `run_with_refetch` (real registered verifier):
- `state=verified`, written=25 853, quarantined=8 203 (all nulls), raw=10 responses,
  **served=25 853** (CC BY 4.0 redistribution_ok=1), sample=516 (latest per populated series),
  passed=1; **all 516 evidence envelopes recovered offline** (integrity-checked, exact deciding
  ZIP bytes + final URL + actual status).

### C. Committed `@pytest.mark.live` test
`test_live_worldbank.py` encodes the healthy-state contract (930 series, `verified`, 18 raw
responses, sample = populated-series count) and prints full diagnostics (state, per-series
latest, quarantine, flags, events, failing verification items) when the publisher channel is
degraded. Actual output of
`.venv-ci/bin/python -m pytest tests/ingest/test_live_worldbank.py -m live -s` on
2026-11-11: <see "Live output" appended below>.

## Live output (actual, 2026-11-11)

### `.venv-ci/bin/python -m pytest tests/ingest/test_live_worldbank.py -m live -s -q`
(exit 1; 818 s; run_with_refetch max_attempts=3, identical fetch outcomes all three attempts)

```
active worldbank series: 930 over 18 indicators
final state: failed-verification  run_id=3  written=45915  quarantined=15465  served=0  raw_responses=18
populated series: 930; empty series (0): []
latest-period distribution (top): [('2025', 624), ('2024', 194), ('2023', 64), ('1994', 11), ('2022', 9), ('2021', 6), ('1960', 3), ('2020', 3)]
quarantine by reason: [('non_numeric', 15465)]  flags: [('normal', 45915)]
verification rows (seed, sample_size, passed): [(510353760942248674, 930, 0)]
  event verification_failure: None
first failing verification items:
  ('worldbank.birth_rate.AO', '2024', 'verifier raised: ReadTimeout(ReadTimeoutError("HTTPSConnectionPool(host='api.worldbank.org', port=443): Read timed out. (read timeout=60.0)"))')
  ... (the whole 930-item sample marked failed by the verifier raise; the CSV export for
       SP.DYN.CBRT.IN, which answered 200 in 0.2 s an hour earlier, now read-timed out after
       the client's bounded retries — the publisher export backend degraded further mid-run)
======================== 1 failed in 818.02s (0:13:38) =========================
```

Fetch/parse/validate side of the live run is fully healthy and REPRODUCIBLE across the three
attempts (same 18 raw JSON responses, 45 915 written, 15 465 null-quarantines, 930/930 series
populated). Failure is exclusively the independent CSV-ZIP channel's publisher-side outage
(HTTP 400 after ~150 s for NE.EXP.GNFS.ZS on the first attempts; read timeouts on the last),
failing closed exactly as designed; nothing from those runs is served.

### Healthy-channel subset driver (real run_with_refetch, 10 working indicators, 516 series)
```
  22.8s state=verified run=1 written=25853 quarantined=8203 raw=10 served=25853
  populated=516 empty=0 []
  quarantine={'non_numeric': 8203} flags={'normal': 25853}
  latest periods: [('1990', 1), ('1992', 1), ('1993', 1), ('1994', 11), ('2000', 1),
   ('2007', 1), ('2009', 1), ('2014', 1), ('2015', 1), ('2017', 2), ('2018', 2), ('2020', 1),
   ('2021', 6), ('2022', 6), ('2023', 27), ('2024', 128), ('2025', 325)]
  VERIFICATION: [(1828779194848775209, 516, 1)]
  evidence items recovered offline: 516/516
```

### Endpoint health timeline (single throttled probes, ~20:30–22:00 UTC)
- 20:30–21:05: 10 indicators' exports 200 OK ≤0.3 s; 8 indicators broken (75 s read timeouts;
  NE.EXP.GNFS.ZS twice HTTP 400 after ~151 s, ASP.NET 'Request Error' page behind Cloudflare).
- ~21:45: during the pytest run, even the previously-healthy SP.DYN.CBRT.IN export
  read-timed out mid-run (further degradation).
- ~21:55: previously-healthy indicators fast again (SP.DYN.CBRT.IN/NY.GDP.MKTP.CD/SP.POP.TOTL
  all 200 in 0.1 s); the chronic 8 STILL broken (NE.EXP, NY.GDP.MKTP.KD.ZG, SL.TLF.CACT.FE.ZS,
  SP.DYN.LE00.IN and per earlier probes also NE.IMP, NE.RSB, BX.KLT.DINV.WD.GD.ZS,
  GB.XPD.RSDV.GD.ZS).
- Conclusion: partial, time-varying, per-indicator publisher backend outage; JSON channel
  unaffected throughout. No client-side defect found (UA documented, ≤1 req/s, bounded
  timeouts; failures are server statuses/timeouts, reproducible with plain `requests`).

## Honest current state and blockers

- Adapter + verifier + registry dispositions are COMPLETE and fully tested offline; the live
  verification passed end-to-end on every indicator whose publisher CSV export endpoint was
  functional at run time (516-series run: verified, sample 516, served under CC BY 4.0).
- **Partial channel outage (publisher-side)**: 8 of 18 indicators' bulk CSV ZIP exports were
  persistently broken tonight, and intermittent degradation briefly hit others. The 414 series
  of those 8 indicators fetched+parsed+validated fine on the JSON channel but could not reach
  `verified` today because the independent channel correctly fails closed. Not an adapter
  defect, not a registry conflict; no series was inactivated for it (an outage is not a
  definition conflict). If the outage persists, this needs a controller decision
  (wait-and-retry tomorrow vs a reviewed alternate channel); I deliberately did NOT switch the
  verifier to another serialization/scope (would be an unreviewed channel change) and did NOT
  fabricate a green full-scope verification.
- Everything else asked by the brief is done: TDD (RED→GREEN), registry dispositions with
  individual listings, evidence archive + offline recovery/replay tests, allowlist +
  subprocess independence, tamper-through-verify_run, full suite 909 passed + ruff clean,
  scoped commits (code never touched by others; controller files untouched).
- REN and DGEG scopes untouched; no CLI registration (Task 17), no legacy collector edits.

## Files touched (committed)

- `0a4458f` registry/core.yaml, registry/core.proposed.yaml, registry/unmapped-worldbank.md
- `173638c` ingest/sources/worldbank.py, ingest/verifiers/worldbank.py, tests/ingest/
  {worldbank_fixtures.py, worldbank_verifier_fixtures.py, worldbank_verifier_entry.py,
  test_source_worldbank.py, test_verifier_worldbank.py, test_registry_worldbank_units.py,
  test_live_worldbank.py, fixtures/worldbank/**} (28 fixture files, sha256-pinned)
- report commit: this file + test_live_worldbank.py diagnostics fix (event.kind/detail_json
  columns; n_raw 18=active-indicator responses)
