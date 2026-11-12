# Task 13 - CSV recovery checkpoint

Controller checkpoint, 2026-11-12. Worktree `/home/joao/projects/prumo-pipeline`, branch `pipeline-rebuild`, implementation unchanged at `a7df6d9`. Task 13 remains BLOCKED on full independent live acceptance; Task 14 has not started. No code/channel/registry changes, deployment, main merge or precision relaxation.

## Current execution

Full controller suite `.venv-ci/bin/python -m pytest tests -q`: 909 passed, 5 live deselected, 1 warning in 159.50 s.

Fresh all-active JSON ingestion via real WorldBankSource/run_dataset: pending-verification, run 1, 45,915 written, 15,465 quarantined publisher nulls, all 930 active series. Isolated scratch DB; served=0. The actual blind WorldBankVerifier was then exercised against 16 genuine per-indicator CSV ZIP responses retrieved from f0nix today. All 822 available latest-per-series comparisons matched exactly as Decimal; no mismatches. This is a diagnostic partial comparison, NOT run_with_refetch all-source acceptance and NOT a verified run. Remaining missing export coverage: NY.GDP.MKTP.KD.ZG (54 series) and SL.UEM.TOTL.ZS (54 series).

Production-egress probes matter: the original NE.EXP.GNFS.ZS CSV export still read-times out at 12 s from f3nix, but returns HTTP 200 / 115,014 bytes in 0.22 s from f0nix. A bounded 18-request sweep from f0nix obtained 16 HTTP-200 genuine ZIPs in 19.88 s total. Growth and unemployment returned HTTP 502 in that sweep and subsequently timed out at 10 s; both also timed out at 12 s from f3nix. Availability is route/time dependent; this is not proof of a permanent publisher-wide outage.

Exact evidence, hashes and URLs are retained under `reports/evidence/task-13-csv-recovery/`. `csv-comparison.json` contains the diagnostic result; `manifest.json` records all 18 actual f0nix requests, statuses, byte counts and SHA256. HTTP-200 bodies are copied byte-for-byte into this evidence directory. Failed requests are not passed to the verifier or called missing values.

## Rejected alternatives

The official WDI homepage links `https://databank.worldbank.org/data/download/WDI_CSV.zip`, redirecting to `https://databankfiles.worldbank.org/public/ddpext_download/WDI_CSV.zip`. The canonical filename is case-sensitive: the old mixed-case `WDI_csv.zip` returned 404, uppercase `WDI_CSV.zip` returned HTTP 200. Full genuine archive downloaded: 283,089,754 bytes, SHA256 `1cbb81b7e8e656e05fe9236f201d6d59a82d62a77f96c147c1bc63940a7b0c0c`, Last-Modified 2026-10-08. Its WDICSV.csv found all 930 sampled series/periods, but only 529 values matched exactly and 401 differed. Example: API exports_pct_gdp.AO 2025 = `22.9777500640377`, bulk = `22.977750064037682`. No rounding or tolerance was introduced. The large bulk file is scratch-only, not committed or substituted into the verifier.

The original exporter also returned genuine .xls workbooks for NE.EXP.GNFS.ZS (342,016 bytes) and SP.DYN.LE00.IN (434,176 bytes). Their data cells are binary numeric Excel storage, not publisher decimal-string tokens; this is not an approved exact-token workaround. No spreadsheet-based verifier was implemented. `xlrd==2.0.2` was installed only in the existing local `.venv-ci` for this diagnostic inspection; production requirements and the verifier import allowlist were not changed.

Country-scoped NE.EXP.GNFS.ZS PRT CSV returned a genuine 2,276-byte ZIP, but grouped-country, country-wide and AGO probes returned HTTP 502. A single healthy country is not full coverage; no per-country fallback implementation was added.

## Owner assistance required

Try downloading these ORIGINAL publisher ZIPs in a browser on the owner's connection and provide the ZIP files unmodified (not Excel-resaved CSVs):

- `https://api.worldbank.org/v2/en/indicator/NY.GDP.MKTP.KD.ZG?downloadformat=csv`
- `https://api.worldbank.org/v2/en/indicator/SL.UEM.TOTL.ZS?downloadformat=csv`

The first is GDP growth (annual %); the second is unemployment, total (% of total labor force), modeled ILO estimate. If the browser also times out, report that; do not manufacture evidence. Once available, validate identity/shape/raw provenance and exercise the complete independent gate before closing Task 13. Previously approved spec/quality implementation reviews remain valid; any new code/channel change requires their scoped re-reviews. Task 14 follows Task 13 per the owner's latest sequencing instruction.
