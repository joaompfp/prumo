# FRED — unmapped / inactivated series (Task 14, 2026-11-12)

Truthful dispositions for `source: fred`. `registry/core.yaml` stays authoritative; this file is
the documented list the registry changes refer to. No ids, indicator keys, roles, geographies or
legacy rows were rewritten.

## Active set — 12 unique IMF global commodity series

All 12 active series are IMF Primary Commodity Prices globals (monthly, NSA, decimal '.',
geography WORLD), each with its exact publisher unit label copied from the archived FRED metadata
(`tests/ingest/fixtures/fred/meta-<CODE>.json`, sha256-pinned by MANIFEST.json) and the canonical
series URL `https://fred.stlouisfed.org/series/<CODE>`:

| registry id | native_code | publisher unit |
|---|---|---|
| fred.aluminum.WORLD | PALUMUSDM | U.S. Dollars per Metric Ton |
| fred.brent_oil.WORLD | POILBREUSDM | U.S. Dollars per Barrel |
| fred.coffee.WORLD | PCOFFOTMUSDM | U.S. Cents per Pound |
| fred.copper.WORLD | PCOPPUSDM | U.S. Dollars per Metric Ton |
| fred.corn.WORLD | PMAIZMTUSDM | U.S. Dollars per Metric Ton |
| fred.cotton.WORLD | PCOTTINDUSDM | U.S. Cents per Pound |
| fred.wheat.WORLD | PWHEAMTUSDM | U.S. Dollars per Metric Ton |
| fred.commodity_iron_ore.WORLD | PIORECRUSDM | U.S. Dollars per Metric Ton |
| fred.commodity_nickel.WORLD | PNICKUSDM | U.S. Dollars per Metric Ton |
| fred.commodity_soybean.WORLD | PSOYBUSDM | U.S. Dollars per Metric Ton |
| fred.commodity_sugar.WORLD | PSUGAISAUSDM | U.S. Cents per Pound |
| fred.commodity_zinc.WORLD | PZINCUSDM | U.S. Dollars per Metric Ton |

The 5 `fred.commodity_*` PRIMARY entries previously carried no `native_code`; the exact same-source
code was filled from the proven twin mapping below (no role swap). This unit/metadata correction
applies ONLY to freshly fetched publisher data: legacy rows filed under the old bare `USD` unit
label are NOT relabelled and are rejected by the existing `unit_mismatch` validation (tested in
`tests/ingest/test_source_fred.py`).

## Inactivated — exact same-source coded twins (5)

Each of these cross_check series carries the SAME FRED code as its PRIMARY commodity_* twin and
is therefore not an independent cross-check (identical source, identical code, identical
publisher): fred.iron_ore.WORLD = fred.commodity_iron_ore.WORLD (PIORECRUSDM, 133 identical legacy
periods), fred.nickel.WORLD = fred.commodity_nickel.WORLD (PNICKUSDM, 277),
fred.soybean.WORLD = fred.commodity_soybean.WORLD (PSOYBUSDM, 277),
fred.sugar.WORLD = fred.commodity_sugar.WORLD (PSUGAISAUSDM, 179),
fred.zinc.WORLD = fred.commodity_zinc.WORLD (PZINCUSDM, 277).
All 5 are `active: false`; ids, roles, original units and codes preserved. No primary swap.

## Inactivated — wrong concept at the publisher (3)

- **fred.steel.WORLD** (native_code WPU101): WPU101 is "Producer Price Index by Commodity: Metals
  and Metal Products: Iron and Steel", units **"Index 1982=100"** — a US BLS index, NOT a WORLD
  steel price in USD. Evidence: `docs/superpowers/handoff/evidence/task-14-fred/meta-WPU101.json`
  (HTTP 200, sha256 e023fdb92897f7d0…, plus page-WPU101.html). No substitution or conversion.
- **fred.commodity_steel.WORLD**: legacy rows are an exact 313-period subset duplicate of WPU101,
  with the same wrong USD/WORLD price concept stacked on top. `active: false`, no code added.
- **fred.natural_gas.WORLD** (native_code MHHNGSP): MHHNGSP is the US **Henry Hub** Natural Gas
  Spot Price, "Dollars per Million BTU" — a US benchmark, not a global benchmark matching the
  current `fred_natural_gas.WORLD.M` definition. Evidence:
  `docs/superpowers/handoff/evidence/task-14-fred/meta-MHHNGSP.json` (HTTP 200, sha256
  b91a06e3121915ab…, plus page-MHHNGSP.html). No new US series is added in this task.

## Not mapped

- **Legacy `commodity_cotton` orphan**: the legacy export's orphan cotton rows are the C-coded
  series at 0.01× scale; they stay `not_in_registry` and are NEVER mapped to PCOTTINDUSDM
  (different scale base).
- No new US-indicator series (WPU101, MHHNGSP as US concepts) is created in this task.

## Licence

`redistribution_ok: false`, `verifiable: true`. FRED's API terms were read 2026-11-12
(`docs/superpowers/handoff/evidence/task-14-fred/fred-api-terms.html`, HTTP 200, sha256
8f18f5706e0fbe8a…): FRED grants API access but defers third-party rights to each series' owner ("making the data
series available through the FRED API does not constitute such permission").
The 12 active series are IMF data ("Reprinted with permission" per FRED metadata); IMF
redistribution terms were NOT obtained (imf.org terms page unreachable at intake, 2 attempts).
Nothing is served until an IMF grant is confirmed.
