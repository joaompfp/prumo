# Final whole-branch review — Part C: sources + registry

Branch `pipeline-rebuild` @ 6b938fd (base `legacy-ui-final` = a18a58a). Read-only review of
`ingest/sources/*.py`, `ingest/http.py` (the contract the adapters share), `ingest/cadence.py`,
`ingest/propose_registry.py`, `ingest/flags.py`, period/number handling in `ingest/models.py` and
`ingest/validate.py`, `registry/*.yaml|md`, and the matching tests in `tests/ingest/`.
I ran a few live GETs against the Eurostat dissemination API and one against the GitHub repo API.

Test run: `.venv-ci/bin/python -m pytest tests/ingest` gave **1397 passed, 7 deselected (the live
tests)**, in 9m42s.

Registry sampled against the adapters: 1791 series, 1345 active. I checked every active
non-Eurostat/non-WB series (INE 41, BPstat 10, REN 14, OECD 6, FRED 12, E-REDES 3). I checked every
active Eurostat (dataset, key, unit) group (23 groups, 329 series) and every active World Bank
indicator group (22 groups, 930 series). Seven Eurostat datasets were confirmed live.

## Strengths

- **Numbers stay publisher tokens end to end.** Every adapter loads JSON with
  `parse_float/parse_int` set to `str` or to a tagged `_Num`. A quoted string can never pass as a
  number (REN/WB/OECD/E-REDES/BPstat). Exponent tokens are kept as they are and then quarantined;
  nothing is rescaled. INE also checks that `valor` and the published `ind_string` denote the same
  Decimal value, and raises when they disagree (`ine.py:209-229`).
- **Truncation is handled carefully, and it fails closed.** The checks are:
  - Eurostat: `_check_extent`.
  - BPstat: array size must match the product of the dimension extents.
  - World Bank: per-page `per_page/total/pages` arithmetic, with drift checked across pages.
  - FRED: `_PageLedger` with `assert_complete`.
  - E-REDES: one-day windows, contiguous offsets, and `len == total_count`.
  - INE: the `UltimoPref` guard.

  I found no path that silently drops a page.
- **The Eurostat confidentiality ruling is implemented correctly.** `|C` and `|N` cells become
  `value=None` (`eurostat.py:202-204`), and unknown confidentiality codes raise.
- **Identity is asserted from the payload, not trusted from the URL.**
  - OECD: full 9-pin key, the dimension-id sequence per dataflow, and the `UNIT_MULT=0` pin.
  - BPstat: unit, periodicity and territory labels against the registry.
  - FRED: the metadata `units` label must equal the registry unit.
  - World Bank: ISO2 and ISO3 identity, plus `sourceid=2`.
  - REN: the month name in the payload is cross-checked against the requested month.
- **FRED credential hygiene inside the pipeline is good.** The key is stripped from the archived
  URL and params, a response that echoes the key is refused, and exceptions are sanitized with
  `from None`. The `.dockerignore` deny-by-default keeps `.fred_api_key` out of the image.
- **The licence gate is conservative and lives in the SQL view** (0005/0006/0007/0009 join on
  `redistribution_ok = 1`). It is set correctly per source:
  - REN, OECD, FRED/IMF and DGEG are `false`, with the evidence quoted in YAML comments.
  - E-REDES CC BY 4.0 is re-asserted at runtime from the publisher metadata
    (`eredes.py:176-179`).
- **No two active series share a native_code** (verified with a script; the 30 duplicate groups
  are all inactive pairs). Every active series has a native_code. One primary per indicator key is
  enforced.
- **Each source has a unit-pairing test** (`test_registry_*_units.py`) that is re-run on every
  registry change.

## Issues

### Critical

**C1. A live FRED API key is committed to the public repository and is still tracked at HEAD.**
- **Where:** `.fred_api_key` (repo root).
- **What I verified:**
  - `git ls-files` lists the file.
  - It is present in `legacy-ui-final` and in three historical commits.
  - Its content is a 32-hex FRED key.
  - `github.com/joaompfp/prumo` reports `private: false`.
  - `tests/ingest/test_source_fred.py:88` even states "it exists in the repo root".
- **Why it matters:** The branch spends a great deal of code keeping the key out of the raw store,
  the DB and logs, while the key itself is world-readable in git history. Anyone can use it, and
  quota abuse or a revoked key would fail every FRED run. For a platform whose promise is trust and
  auditability, a published credential is the first thing an auditor flags. The branch did not
  introduce it, but it carries it forward as tracked content.
- **Fix:**
  1. Revoke and rotate the key at api.stlouisfed.org.
  2. `git rm --cached .fred_api_key` and add it to `.gitignore`.
  3. Supply the new key only through `FRED_API_KEY` (`deploy/prumo-ingest.yml:21` already does
     this).
  4. Optionally purge it from history. Rotation is what matters, because the key is already
     public.

### Important

**I1. `eurostat.hicp.EU27_2020` is active on a dataset that is frozen.**
- **Where:** `registry/core.yaml:3054` (`prc_hicp_midx:...unit=I15...`).
- **What I found live (2026-11-13):** every unit of `prc_hicp_midx` (I15, I05, I96) ends at
  2025-12, last updated 2026-02-06. Eurostat moved the HICP to new datasets and a new base in 2026;
  the October 2026 HICP exists elsewhere.
- **Why it matters:** The ruling says discontinued or rebased series must be inactive. Ruling W's
  test ("last value < 2024 AND an active newer-base sibling", progress-ledger line 98) is too
  narrow to catch a dataset frozen in 2026. The series will be served as "verified" while sitting
  11 months behind the publisher. The values are not wrong, but the series looks current when it
  is not.
- **Fix:**
  - Set `active: false` and list it under "Discontinued / rebased" in `unmapped-eurostat.md`.
  - Map the successor dataset as a new series. Do not relabel: the base year changes.
  - Widen Ruling W to "the dataset's `updated` or last period lags the frequency by more than N
    periods". A cheap check is a registry test or live probe that compares the last period
    against the frequency.
- **Not checked:** I spot-checked only 7 of the 11 active Eurostat datasets.

**I2. Geography and unit vocabularies are not uniform within one indicator.**
- **What:**
  - Greece is `EL` on 13 active Eurostat series but `GR` on
    `eurostat.electricity_price_household.GR` (`core.yaml:1480`, native `geo=EL`).
  - The EU-27 aggregate is `EU27` on some series (`eurostat.unemployment.EU27` at `:9270`,
    `gdp_quarterly.EU27`, `ipi_total.EU27`, `electricity_price_household.EU27`, `STS_INPR_*.EU27`)
    and `EU27_2020` on others. All of them pin `geo=EU27_2020`.
  - Within single World Bank indicator keys, units are mixed:
    - `SP.POP.TOTL`: `hab.` ×52 and `persons` ×2.
    - `SP.DYN.CBRT.IN` / `SP.DYN.CDRT.IN`: `/1000` and `per_1000`.
    - `SP.DYN.LE00.IN`: `anos` and `years`.
  - Within Eurostat units, I21 is labelled `I21`/`index_2021`, I10 is `I10_2010`/`index_2010=100`,
    and BAL is `balance`/`balance %`. These are recorded as an owner finding in
    `test_registry_eurostat_units.py:8-10` but not fixed.
- **Why it matters:** A statistician comparing countries or filtering by geography will lose
  Greece from the electricity series and will see two "EU" codes. Any consumer that groups by
  `(indicator, unit)` will split one indicator into two. The data itself is correct; the labels
  are not canonical.
- **Fix:** Use one geography code per source (Eurostat `EL` and `EU27_2020`, matching the pinned
  `geo`) and one unit label per indicator key / unit code. Add a registry test that asserts both:
  - for Eurostat, `geography == native geo`;
  - each `(source, indicator family)` has exactly one unit label.

**I3. Seasonal adjustment is missing from registry metadata for adjusted series.**
- **What:** `seasonal_adjustment` is `None` on:
  - every active Eurostat series, although native codes pin `s_adj=SA/SCA`;
  - the 31 INE `ipi_seasonal_cae_*` series and `ine.unemployment_monthly.PT`, which INE labels as
    seasonally adjusted (see `test_registry_ine_units.py`);
  - `oecd.cli.PT`.

  Only FRED (NSA) and four OECD BTS series fill the field.
- **Why it matters:** The spec (§ series metadata) lists seasonal adjustment as served metadata.
  A served IPI or unemployment rate with no SA marker is easily misread, for example when compared
  with an NSA series of the same concept.
- **Fix:** Fill the field from the pinned codes for Eurostat (`s_adj`), from INE indicator names,
  and from OECD's `ADJUSTMENT` pin. Add a test that pins it for Eurostat from native_code.

### Minor

- **M1. The meaning of `multiplier` is ambiguous.** `core.yaml` (OECD, 6 series) stores
  `multiplier: 0`, meaning SDMX UNIT_MULT (a power-of-10 exponent). The column is a bare
  `multiplier REAL` (`0001_init.sql:19`). A consumer that reads it as a factor gets zero.
  *Fix:* rename it or document it as `unit_mult_exponent`, or store `1`.
- **M2. Eurostat flag mapping is lossy and the raw flag is not stored** (`flags.py:30-41`).
  `f` (forecast), `u` (low reliability) and `n` (not significant) all become "estimated", and `d`
  (definition differs) becomes "break". This is known (Task 9 M2, deferred). A statistician will
  ask for the raw OBS_FLAG. *Fix:* persist `flag_raw` alongside the mapped flag.
- **M3. INE serves `valor` ('2.4') rather than the published rendering ('2,40').** The numeric
  value is the same, but the publisher's displayed precision is lost (`ine.py:26-31`). This was
  documented and decided; flag it to the owner because "exactly what was published" is the brand
  promise.
- **M4. A partial bounded window can leave permanent holes.** The scheduler always uses the
  default bounded windows: E-REDES last 3 UTC days (`eredes.py:242-246`) and REN last 13 completed
  months (`ren.py:99`), both via `operations.py:162,171`. An outage longer than the window leaves a
  hole that nothing back-fills automatically. *Fix:* derive the window from the last stored period,
  or alert on gaps. The status-side gap detection is out of my scope.
- **M5. Rate limits are not handled.** `RequestsHttp` (`http.py:79-92`) retries only on 5xx and
  network errors. A 429 is not retried and `Retry-After` is ignored, so it becomes a failed run.
  This fails safe, but a burst on FRED or OECD costs a whole cycle. *Fix:* treat 429 like 5xx and
  honour `Retry-After`.
- **M6. Duplicate active native_codes are not enforced by the loader.**
  `ingest/registry.py:_validate` does not check them; they are unique today only by curation.
  OECD, WB, REN and E-REDES `parse()` raise on duplicates, but Eurostat, INE and BPstat would
  silently give two specs identical rows. *Fix:* add a uniqueness check in `_validate` scoped to
  `active` series.
- **M7. The registry file is still marked provisional and duplicated.** `registry/core.yaml:1`
  still says `# PROVISIONAL — owner review pending`. `core.proposed.yaml` is byte-identical to the
  curated `core.yaml` (two copies of the authoritative knowledge). *Fix:* after sign-off, drop the
  header and delete or regenerate the proposed copy. `propose_registry.py:317-320` correctly refuses
  to overwrite without `force`.
- **M8. Attribution strings contain unfilled placeholders.**
  - INE (`core.yaml` `ine.attribution`): "(identificação da informação estatística referida,
    período de referência da informação)".
  - OECD: "(year), (dataset name) ... (accessed on YYYY-MM-DD)".

  If shown verbatim they read as template text. *Fix:* render them per series, or store a filled
  form. OECD is withheld today.
- **M9. Misleading identifier for the OECD series.** `oecd.cli.PT` / `oecd_cli.PT.M`
  (`core.yaml:8636`) is MEASURE=BCICP (business confidence), not the CLI. Its unit
  `index (100=trend)` is the CLI wording (BCI is "amplitude adjusted, long-term average = 100").
  The trap is documented, but the id and key will mislead users. *Fix:* rename to
  `oecd.bci.PT` and adjust the unit prose.
- **M10. BPstat does not check that dates are month-end.** `_period` (`bportugal.py:351-357`)
  truncates any ISO date to `YYYY-MM` without checking it is month-end, despite the docstring.
  Low risk; assert `day == monthrange()`.
- **M11. The period parser accepts non-ASCII digits.** `normalize_period` (`models.py:23-31`) uses
  Unicode `\d` for A/S/Q/M/D, so non-ASCII digit aliases are folded silently. FRED and OECD already
  guard against this; the shared parser does not. *Fix:* use `[0-9]`.

## Declined to judge

- **BPstat time-axis pagination.** I could not confirm from documentation that the data API never
  pages the `reference_date` axis. The size check would not detect a consistently truncated axis.
  The Task 11 report claims a full-history match against the portal; I did not re-probe.
- **Whether the OECD T&C §3 grant already covers DF_CLI/DF_BTS/DF_IALFS_UNE_M.** This is a legal
  call. Keeping `false` is the safe default.
- **IMF Primary Commodity Prices redistribution terms.** The IMF terms page was not checked; `false`
  is correct pending that.
- **World Bank per-indicator third-party licence exceptions.** I relied on the registry note; I did
  not re-read the 19 indicator metadata pages.
- **Status, scheduler, gap detection and verifier independence.** These are Parts A/B/D.
- **Whether HICP successor mapping should be Eurostat or INE for EU27.** That is an owner choice.

## Assessment

**Ready to merge: With fixes.** The adapters are unusually rigorous. I found no parser path that
silently changes a value, drops a page or lets withheld data through the licence gate. But the
publicly committed FRED key (C1) must be rotated and untracked. The frozen-but-active HICP series
(I1) and the non-canonical geography and unit labels (I2) should be corrected before a
statistician audits the served catalogue. I3 should follow shortly after.
