# Prumo — Public UI (project 4) — Design

Date: 2026-11-15 · Status: written by the planner from the owner's instruction "Avança então para o UI" (owner opted out of the question round; every choice is the planner's call unless marked **[owner]**).

## 1. Intent and why

Prumo's promise is trust: every number is a number an institution published, traceable to that publisher, never silently stale, never silently altered. Projects 1-3 built the store, the backoffice and the calculated layer. The public still sees "Em manutenção".

This project replaces the maintenance page with a public site whose organising principle is **provenance on screen**. Every figure carries its publisher, its receipt date, its verification and its licence; every calculated value is visibly calculated and can be recomputed from the values it used. Audience: professionals and the public, in Portuguese.

The old site (tag `legacy-ui-final`) was a JavaScript SPA with a dashboard, country comparisons, an explorer, AI commentary and political lenses. Its response shapes are deliberately not preserved (base spec §11.2). This is a rebuild around the new data layer, not a port.

## 2. What the data layer already offers (measured on a copy of production, 2026-11-15)

- `served_observation`: 172,512 rows, all `fetched`; 1,312 distinct series; columns include `series_id, period, value_text, status_flag, dataset_run_id, raw_fetch_id, fetched_at, released_at`.
- 1,344 active series; 1,308 of them are `role='primary'` with served data; 4 are served `cross_check` series (Eurostat duplicates of Portuguese INE industrial-production series). 5 sources are redistributable and publish: INE, Banco de Portugal, Eurostat, World Bank, E-REDES. REN, FRED, OECD and DGEG are collected or registered but withheld by licence and do not appear in `served_observation`.
- 85 indicator families among served primaries, 60 geographies, 27 unit strings, 5 frequencies (`A`, `S`, `Q`, `M`, `PT15M`), 4 status flags (`normal`, `estimated`, `provisional`, `break`).
- 23 derived series in `served_derived`, 6,665 values, each with formula, base series, input observation ids, `is_calculated=1`, inherited licence/attribution and a closed list of caveat codes (`sa_base`, `stock_base`).
- `verification` per dataset run: seed, sample size, pass flag, creation time, sampling procedure and design; `verification_item` records whether a given series/period was in the sample. `raw_fetch` keeps the exact receipt: URL, retrieval time, HTTP status, SHA-256, byte count.
- **No reader-facing labels exist in the data layer.** Migration 0016 moved text out; `presentation/` holds only derived titles, units, formulas and caveats. Series are identified by `indicator_key` (`family.geography.frequency`) plus `series.id`. The UI must add a reader-text catalogue; it must not push text back into SQLite.

## 3. Decisions (planner's calls)

### D1. Pages and navigation

Server-rendered, no client-side router. Navigation: Início · Economia · Demografia · Energia · Fontes · Metodologia, plus a search field in the header.

| Route | Page |
|---|---|
| `/` | Início: what Prumo is, global freshness, curated Portuguese figures, theme entry points, short verification explanation, sources strip |
| `/temas/{economy,demography,energy}` | Theme catalogue: every served primary series in the theme, grouped by family, with filters (geography group, source, frequency) and pagination |
| `/series/{series_id}` | Series page: latest value, SVG chart, table, full provenance, revisions, derived values computed from it, cross-check comparison, CSV |
| `/calculadas/{derived_key}` | Calculated series: latest value, chart, formula in Portuguese, input values with links, caveat, inherited licence |
| `/pesquisa?q=` | Search over family titles, geographies, source names and series ids |
| `/fontes` | Sources: what each publishes, licence, attribution, series count, last receipt; withheld sources named without data |
| `/metodologia` | Method: collection, validation, independent verification, vintages, precision, flags, calculated values, licences, non-goals, FAQ |
| `/healthz` | Container health (existing) |
| `/static/*` | CSS and brand images |

404 for unknown or unpublished series; a plain error page for schema/read failures (503, same rule as the backoffice).

### D2. Primary source only in navigation

The catalogue, search and theme pages list `role='primary'` series only. A `cross_check` series never appears as an entry and its URL returns 404. On the primary's page, its cross-checks are shown as such, with their latest value, source and date, labelled "verificação cruzada" and never as a replacement for the primary value. This applies the source-of-truth rule (base spec §5) to the public surface.

### D3. Provenance is a first-class block, not a tooltip

Every series page has a "Proveniência" section with:

- publisher name and attribution text (as stored in `source`), licence name and link;
- the publisher's own code/URL for the series (`series.native_code`, `series.url`) linked when `https://`;
- the exact receipt behind the served value: retrieval timestamp (UTC), HTTP status, archived payload SHA-256, byte count, dataset run id;
- the verification that covered that run: date, sample size, 100% match statement, sampling procedure, verifier channel, and whether **this particular value** was in the sample (from `verification_item`) — if it was not, the page says so;
- the number of stored vintages for the series and a link/anchor to the revisions section.

Compact figures (home cards, catalogue rows) carry a one-line provenance: source name · "recolhido a DD/MM/AAAA" plus a link to the series page. No figure is shown without a nameable source.

### D4. Revisions are visible

The series page lists every period with more than one stored version across verified runs: period, old value → new value, dates of each receipt, and a marker on the served one. Periods never revised are summarised as a count ("247 períodos sem revisões"). The rule is computed from `observation` history filtered to verified runs; failed or withdrawn runs are never shown as published history.

### D5. Calculated values are visibly calculated

Any derived value carries the badge "Calculado pelo Prumo". On its own page it shows the formula in Portuguese, the base series, the exact input periods and values with links, the computation time, the caveat sentences when present, and the inherited attribution plus "Calculado pelo Prumo". On a base series page, the derived values computed from it are listed with their latest value and a link; they are never interleaved with published values. Base values are never badged.

### D6. Reader text lives in `presentation/`, keyed by codes

Add to `presentation/catalog/pt.py` (and keep `en.py` structurally ready, not populated in v1):

- `FAMILIES`: indicator family key → Portuguese title (85 served families; includes the 24 CAE divisions by name);
- `GEOGRAPHIES`: ISO/registry code → Portuguese name (60 codes incl. `PT`, `EU27_2020`, `EA`, `WORLD`, `Continente`, `EL`/`GR`);
- `UNITS`: every unit string in the registry → Portuguese reading (`%`, `% do PIB`, `índice 2021=100`, `mil milhões de euros`, `habitantes`, `anos`, `USD por habitante`, `EUR/kWh`, …);
- `FLAGS`: `normal`/`estimated`/`provisional`/`break` → Portuguese label and meaning;
- `THEMES`, `FREQUENCIES`, `SEASONAL`: theme, frequency and adjustment codes → Portuguese text;
- `SOURCE_TITLES`: source name → institution name;
- `CURATED_HOME`: ordered series ids for the home page, with the short label to use there.

A series' visible title is composed as `FAMILIES[family] — GEOGRAPHIES[geography]` (geography omitted when the title already names it, via an explicit set of self-locating families). A missing text entry raises `MissingText` at render time; a test walks `registry/core.yaml` and asserts every active, redistributable series resolves family, geography, unit, flag, frequency and theme. No raw code may reach the HTML.

### D7. Language, dates and numbers

PT-PT only in v1. Every text helper takes a `lang` parameter and the app passes `"pt"`; `/en` is out of scope but the catalogue layout keeps `en.py` as a peer. Dates and periods are rendered in Portuguese (`Outubro de 2026`, `2026`, `1.º trimestre de 2026`, `1.º semestre de 2026`, `15/11/2026, 08:49 UTC`). Numbers keep the publisher's precision and decimal token, rendered with Portuguese separators (comma decimal, space thousands); no rounding, scaling or unit conversion happens in the UI. Axis ticks are the only rounded numbers and are visually separated from values.

### D8. No JavaScript, no third-party assets

Pages are plain HTML and CSS. Charts are inline SVG generated on the server. No script tags, no external fonts, no CDN, no trackers, no cookies. CSP: `default-src 'none'; style-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`. Range selection and filters are links/GET forms; the table under each chart is always present in `<details>` so the page works with images, CSS or SVG disabled. This keeps the trust surface inspectable and removes a whole class of dependency and privacy risk.

### D9. Withheld sources

`/fontes` names REN, FRED, OECD and DGEG in a separate "Fontes em avaliação" block: what they would contribute and that their redistribution terms are not established, so no values are shown. No observation from a withheld source is queried, rendered or counted in public totals.

### D10. Fifteen-minute series

E-REDES production series are 15-minute intervals (21,685 served rows each). Their page charts one UTC day (96 points) selected by `?dia=AAAA-MM-DD`, defaults to the latest day, and states the interval contract; the table lists that day's values. No daily/monthly aggregation is shown, because that would be a calculation without the derived layer's provenance. Other series chart their full stored history, with range links (10 anos, 25 anos, Máx) that filter server-side.

### D11. Read path and caching

The app reads through `ingest.db.Db` only (SQL stays in `ingest/db.py`, as the backoffice already does), opened with `read_db_readonly` (mode=ro, never migrates, retries once on a concurrent writer, 503 on schema mismatch). New read methods are added to `Db`; `app/reads.py` composes page data and owns no SQL. A small in-process TTL cache (30 s) holds the catalogue and counts; series pages are computed per request (measured 26 ms for the full catalogue on the production copy). CSV export streams the served rows of one series with the same columns shown, `;` separator, UTF-8 BOM for Excel compatibility, and a final line naming source, licence and retrieval date.

### D12. Accessibility and performance

Semantic landmarks, one `h1` per page, skip link, visible focus, AA contrast, no colour-only meaning, table fallback for every chart, `lang="pt-PT"`, descriptive `alt`. Targets: home and series page under 150 ms server time on the production copy; HTML under 250 KB for the largest page; no request to any origin other than the site itself.

### D13. Deployment

Same `prumo` container and entrypoint; `app/main.py` stops serving the maintenance page and serves the new app. Both public URLs keep working: `cae.joao.date` at root and `joao.date/dados` behind Traefik `StripPrefix`; links and static asset URLs are built from `X-Forwarded-Prefix` (relative where possible). Deploy follows the standing rule: tests and independent review first, owner authorises merge and deploy; the backoffice is untouched.

## 4. Non-goals (v1)

AI commentary or headlines; political/ideology lenses; editorial narratives; share cards and embeds; accounts, saved views or alerts; writing actions of any kind; English UI; dark mode; cross-country comparison pages (the primary/cross-check data is there, the comparison product is v1.1); ranking or composite scores; daily aggregation of 15-minute data; any new migration.

## 5. Anti-goals

A number on screen that cannot be traced to a receipt; a calculated value indistinguishable from a published one; a withheld source's value rendered by accident; a raw code (`estimated`, `sa_base`, `worldbank_gdp_growth`) shown as reader text; a chart that rounds a value the table shows exactly; a page that needs JavaScript to show its content.

## 6. Visual language

Carry the brand forward, not the old layout: warm paper (`#F6F4F1`), ink (`#1A1A1A`), muted (`#5A5550`), rule (`#E2DED9`), Portuguese red (`#CC0000`) used only for emphasis and the flag/last-point marker; white surfaces for data blocks; generous type scale (17-19 px body, 32-48 px figures); tabular numerals; hairline rules instead of cards with shadows. Typeface: the system UI stack (no webfont request). Charts: thin ink lines, red last point, no grid noise, direct labels, footnote naming the source and the last receipt.

## 7. Parts (build order)

1. Presentation catalogue (families, geographies, units, flags, themes, frequencies, sources, curated list) + completeness test against the registry.
2. `Db` public reads + `app/reads.py` (catalogue with latest values, series header, provenance, revisions, derived siblings/cross-checks, sources, counts) + tests on a synthetic DB.
3. App skeleton: FastAPI factory, prefix handling, base template, CSS, headers, 404/503, static; route tests.
4. SVG chart and PT formatting modules + tests (ticks, domains, negatives, period labels, 15-minute day).
5. Series page (base) with provenance, revisions, cross-check, derived list, CSV.
6. Calculated page.
7. Home with curated cards and sparklines.
8. Theme catalogue with filters and pagination; search.
9. Sources and methodology pages.
10. Browser verification against a copy of production (screenshots at 1440/390 px, no-JS and no-CSS checks, link audit, timing), independent review, docs/handoff.

## 8. Constraints

All standing rulings hold: numbers as stored text (never float), SQL only in `ingest/db.py`, nothing invented, no push alerts, protected `AGENTS.md`/`CLAUDE.md` untouched, no raw docker commands, no merge to `main` or deploy without the owner. The UI may not add writes, migrations or background jobs. Tests run with `.venv-ci/bin/python -m pytest tests -q`; network is forbidden in tests.

## 9. Open questions for the owner (non-blocking, v1.1)

Which comparison view matters first (Portugal vs EU27 vs a chosen country)? Should the English edition follow, and is a dark theme wanted? Which derived series should lead the home page once more are declared? Should withheld-source coverage be described publicly in more detail?
