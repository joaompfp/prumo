# Country comparisons

The public comparison index combines the existing two-indicator pairs with curated multi-country pages. Country groups compare one statistical concept across Portugal, Spain, France, Germany and Italy, with one common scale and a common period window.

## Pages

| Public path | Measure | Interpretation |
|---|---|---|
| `/comparar/paises/eletricidade-domestica` | Eurostat household electricity price, EUR/kWh, semester | Annual consumption band 2 500 to 4 999 kWh, all taxes and levies included. This is a published retail average, not a live tariff or a bill estimate. |
| `/comparar/paises/pib-por-habitante` | GDP per inhabitant, current euros, annual | Not household income, inflation-adjusted growth or a purchasing-power-adjusted welfare comparison. |
| `/comparar/paises/divida-publica` | General-government gross consolidated debt, percentage of GDP, annual | A stock ratio, not the annual deficit. |

Both installed public mount shapes are supported: the direct domain and the `/dados` prefix. Routes become available only after installation of this candidate; repository completion does not establish live availability.

Electricity definition and source dataset:
https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Electricity_price_statistics
https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table?lang=en

Gas prices are not included. No gas dataset was added to the ingestion registry and no withheld MIBEL/REN values are exposed.

## Reading a comparison

The latest summary and legend refer to the latest period with a finite served value for every country. The chart and its complete table use the same period intersection. A later observation for one country is not combined with an older observation for another. The coverage note states exclusions; missing values are neither filled nor interpolated.

Hover, tap or use the keyboard period control to inspect values. Country line patterns supplement their colours. Portugal is Carmim. A complete value table and the named SVG remain available without JavaScript, after a blocked chart bundle and in print. Normal UI strings follow the shared [two-decimal display policy](numeric-display.md); original source precision remains in stored data, CSV and technical evidence. Provisional and other publisher statuses appear in the table and latest-country summary.

Each country has a series link and provenance for the last common period, with collection, archived file, verification context and attribution. A comparison disappears whole when a required series becomes inactive, unlicensed, withdrawn or empty. The page never silently changes its country population.

The Caderno action creates a stateless address with the five selected series. That address tracks current values; it is not a frozen historical analysis.

## Curation and boundaries

`presentation/catalog/pt.py` carries the reviewed definitions and pinned native dimensions. `app/country_comparisons.py` validates the same family, publisher, geography, unit, frequency, adjustment, multiplier, base and native dimensions (except geography) before preparing the shared chart. Every public read still requires active, primary, licensed, fetched served observations.

The ordered-series model in `app/chart_model.py` supports bounded three-to-six-series shared-axis groups using the same geometry and exact value preparation as existing pairs. Existing CMS chart documents remain single-series or pairs; this change does not add a new CMS document shape or arbitrary multi-series picker. General editorial configuration of country groups is a separate product increment.

No new source, ingestion, migration, data write or server-side dependency is required. The previous larger-type/Caderno candidate is already on the same branch, so a combined branch installation affects public web and backoffice through their existing aliases. There is no need to restart the worker, migrate the database or change Authelia/Traefik for this release. Installation still needs the owner's release authorization.

## Evidence

Design: `docs/superpowers/specs/2026-11-17-european-country-comparisons-design.md`.

Plan: `docs/superpowers/plans/2026-11-17-european-country-comparisons.md`.

Implementation, independent reviews and reproducible browser receipts: `docs/superpowers/handoff/reports/european-comparisons/`.
