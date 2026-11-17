# European country comparisons

## Scope authorized by the owner

Extend /comparar with useful, actual comparisons between European countries, starting with household electricity prices. Implementation is authorized; merge and installation are separate. Preserve the previous legibility/Caderno candidate and the installed production baseline.

Deliver three curated comparisons for the same ordered countries Portugal, Spain, France, Germany and Italy:

| Slug | Existing family | Meaning |
|---|---|---|
| eletricidade-domestica | eurostat.electricity_price_household | Semester household retail electricity price, EUR/kWh, annual consumption 2 500 to 4 999 kWh, all taxes and levies included |
| pib-por-habitante | eurostat.gdp_per_capita_eur | Annual GDP per inhabitant, current euros; neither household income nor purchasing-power-adjusted welfare |
| divida-publica | eurostat.gov_debt_pct_gdp | Annual general-government gross consolidated debt as percentage of GDP; a stock ratio, not annual deficit |

The actual registry pins the same native dimensions except geo within each group. The isolated production snapshot confirms all fifteen selected series are active, primary, redistributable and have fetched verified served data. No new ingestion, registry change, calculation, schema migration, free pair selector or CMS document shape is authorized here. Gas prices are not currently ingested and are not included under an electricity label. Energy wholesale/MIBEL prices remain withheld and must not leak.

Official electricity definition: https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Electricity_price_statistics and dataset nrg_pc_204. Stored key: freq=S,siec=E7000,nrg_cons=KWH2500-4999,unit=KWH,tax=I_TAX,currency=EUR,geo=COUNTRY. This is a published semester average for the band, not a live tariff, a bill quote or a measure of affordability.

## Architecture and statistical contract

Refactor shared comparison preparation FIRST, preserving existing pairs, SVG geometry, chart payloads and CMS behavior. Generalize the same model to a bounded three-to-six-series shared-axis chart. Keep pair and CMS APIs as thin existing consumers; no separate country-only scale or precision implementation. Country presentation uses the shared engine, with short country labels, one common axis, explicit dash/pattern distinctions and Carmim for Portugal. Keep existing pair styling and dual axes unchanged.

All chart values, SVG, interactive payload, full table, latest-country summary and provenance come from one read-only database transaction. Require primary, active, legally redistributable, fetched served observations on EVERY side. Country groups must match family, source, frequency, unit, adjustment, multiplier, base year and pinned native dimensions excluding geo; country identities must match their registry geography. A missing, withheld, withdrawn, mismatched or empty side makes the complete group unavailable. Never silently drop a country.

Use the intersection of canonical periods with finite values on every side. Missing periods are counted per country; nonnumeric common periods are separately counted. Never interpolate, carry forward, resample, rebase, round publisher tokens or convert to purchasing power. Temporal gaps remain visual breaks in both renderers. Resolve provenance at the latest common period actually drawn, including status flags such as provisional. The latest summary must not mix years/semesters.

Public routes: /comparar/paises/{slug}, discoverable as a country-comparison section in /comparar. Keep the existing /comparar/{slug} pairs and all old pages working. Unknown slug 404, missing authored catalogue text generic logged503. No arbitrary id-list comparison endpoint, POST or new account state.

ECharts uses the pinned local bundle with same-snapshot inert JSON. Exact tooltip/range readout for all countries, short labels, keyboard/pointer/touch, no external requests or CSP weakening. SVG, complete numeric table and source links work without JS, on failed enhancement and in print. Do not shrink the approved enlarged typography to fit; suppress crowded final-point labels and wrap the five-country legend. Mobile table may have a labelled horizontal scroller, not whole-page overflow.

## Acceptance

First run existing pair/chart/CMS tests against the refactor, without refreshing goldens. Add tests for N-way intersection, empty/nonfinite/gap/single-point behavior, precise tokens and flags, compatibility mismatch, country order and duplicate validation, per-period provenance, withheld/withdrawn/legacy refusal, catalogue failure, both prefixes and route read-only/CSP behavior. Rebuild and verify the exact chart asset/manifest with pinned tools.

Exercise the complete new pages on a consistent production snapshot, with integrity/FK checks and before/after fingerprints proving all tables unchanged. Measure actual point/table counts and coverage. Browser widths320/390/768/1440, pointer/touch/keyboard exact values, styles, no-JS/blocked-bundle/print, local fonts, legible legend and complete tooltip; retain screenshots and machine-readable receipts. Human screen-reader acceptance remains separate.

Independent specification review followed by quality review, then controller full offline suite and lint. Verify new files/imports/assets from a detached committed checkout before authorized branch push, and read back exact remote SHA. Update HANDOFF and the owner's roadmap with implemented versus installed states. No production mutation or new installation in this scope.
