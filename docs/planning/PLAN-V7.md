# CAE Dashboard v7 — Master Plan

**Data Platform + Embeddable Charts**
**Status**: Approved, M1 in progress
**Date**: 2026-02-28

---

## Vision

Transform the CAE Dashboard from an 11-section storytelling monolith into a **4-section data exploration platform** with **embeddable charts** for Hugo blog posts. Add visitor/usage tracking. Move DB to its own volume. Preserve all narrative content for future blog posts.

**Primary URL**: `joao.date/dados` (subpath via Traefik StripPrefix). `cae.joao.date` stays as alias.

---

## New Architecture

```
CAE Dashboard (joao.date/dados)           Hugo Site (joao.date/textos)
+-------------------------------+          +------------------------+
| Painel | Europa | Explorador | Ficha |   |  Blog posts with       |
| +-----+ +------+ +--------+ +-----+|   |  {{< cae-chart >}}     |
| |KPIs | |Clean | |WB-style| |Full ||   |  shortcodes            |
| |Spark| |compar| |multi-  | |tech ||   |                        |
| |lines| |e     | |ind.    | |sheet||   +------------------------+
| +-----+ +------+ +--------+ +-----+|             |
|                                      |   embed.js <+
|  /embed.js    /api/series            |
|  /api/track   /api/compare           |   Umami (stats.joao.date)
|  /api/stats   /api/export            |-->+------------------------+
|                                      |   |  Visitor analytics      |
|  Analytics middleware --> SQLite      |   +------------------------+
+-------------------------------+
```

---

## Sections: 4 (not 11)

| Section | Hash | Purpose |
|---------|------|---------|
| **Painel** | `#painel` | KPI cards + sparklines + "last updated" timestamp |
| **Europa** | `#europa` | Country comparison -- simplified UI |
| **Explorador** | `#explorador` | WB-style multi-indicator plotter + CSV export |
| **Ficha Tecnica** | `#ficha` | Complete technical sheet: ALL indicators listed, methodology, sources |

---

## Database Migration

**Current**: DB lives in OpenClaw's skills workspace:
`stacks/ai/appdata/openclaw/workspace/skills/cae-reports/data/cae-data.duckdb` (93MB)

**New**: Move to CAE dashboard's own appdata:
`stacks/jarbas/appdata/cae-dashboard/cae-data.duckdb`

**Changes needed:**
- Copy DuckDB file to new location
- Update compose volume mount: `${DOCKER_DIR}/stacks/jarbas/appdata/cae-dashboard:/data:rw`
- Update collectors/n8n to write to new path
- Keep a symlink in the old location temporarily for OpenClaw compatibility

---

## Work Packages

### M1 -- Skeleton App + DB Migration [Claude/Core]

**Status**: In progress
**Goal**: Strip dashboard to 4 empty sections, move DB, add analytics table. Deployable skeleton.

**Files to modify:**
- `stacks/jarbas/compose/cae-dashboard.yml` -- change volume mount
- `app/config.py` -- add `ANALYTICS_DB_PATH`
- `app/analytics.py` -- **CREATE**: SQLite analytics module (log_event, query_stats)
- `app/main.py` -- add analytics middleware, add POST to CORS
- `app/routes/api.py` -- add `/api/track`, `/api/stats`, `/api/export`; deprecate old endpoints
- `app/services/__init__.py` -- remove ficha and analysis imports
- `templates/dashboard.html` -- 4 tabs, 4 sections, stripped nav
- `static/js/app.js` -- 4 sections + legacy hash redirects
- `static/js/api.js` -- simplify to generic methods only
- `Dockerfile` -- add `ENV ANALYTICS_DB_PATH=/data/analytics.db`

**Files to delete:**
- `app/services/ficha.py`, `app/services/analysis.py`
- Old section JS files (after narrative extraction to `docs/narratives.md`)
- `analise-content.html`, `analise-metadata.json` (moved to `docs/`)

---

### M2 -- Painel Section [Criativo]

**Goal**: Clean KPI overview with sparklines. Data-driven, no narratives.

**Instructions for Criativo:**

Rewrite `static/js/sections/painel.js` (currently `resumo.js`). Register as `App.registerSection('painel', init)`.

**Keep**: KPI cards with sparklines, YoY arrows, trend indicators, sentiment coloring. All of this comes from `/api/resumo` -- the backend service is unchanged.

**Remove**: The hardcoded narrative block ("Portugal em 30 Segundos"), the fosso CTA button, and the 3 mini-charts that called `/api/compare`.

**Add**:
- Prominent "Dados atualizados: {data.updated}" timestamp at the top
- Clean grid layout: 2x3 or 3x2 KPI cards
- Each card: indicator name, value with unit, sparkline (12 months), YoY change with arrow, sentiment color bar

**Design reference**: Current resumo section works well for the KPI cards. Just remove the narrative and mini-charts.

**API**: `GET /api/resumo` returns `{updated, kpis: [{id, label, value, unit, period, yoy, trend, sentiment, context, spark}]}`

**CSS**: Rename `#resumo` selectors to `#painel` in `static/css/sections.css`.

---

### M3 -- Europa Section (Simplified UI) [Criativo + Analyst]

**Goal**: Cleaner country comparison interface.

**Instructions for Criativo (UI design):**

Redesign the Europa section UI in `static/js/sections/europa.js`. The data layer and chart rendering stay the same -- only the control panel changes.

**Current problems**: Too many controls visible simultaneously. 27 country pills in a grid, 6 preset buttons, indicator dropdown, year selector, view toggle -- cognitive overload for a visitor.

**New UI approach** -- progressive disclosure:
1. **Top bar**: Indicator dropdown (keep) + View toggle (Lines/Snapshot, keep)
2. **Smart presets** as the primary selection: "PT vs Iberica", "PT vs Vizinhos", "Mediterraneo", "Nordicos", "Leste", "Todos" -- these are tabs/chips, not extra buttons alongside individual pills
3. **Custom selection**: A "Personalizar" option in the presets that expands the full country picker (hidden by default)
4. **Year range**: Compact selector, not 6 separate buttons -- a `<select>` or a small "Desde: [2015 v]" dropdown

The key insight: most visitors want a preset comparison. Only power users need individual country selection. Hide complexity behind progressive disclosure.

**Add URL state persistence**: After each chart load, update hash: `#europa?ind=X&countries=PT,ES,DE&since=2015&view=lines`. On init, restore from hash.

**Add share button**: Copy permalink to clipboard with toast.

**Instructions for Analyst (data validation):**

Review the Europa section's data sources. Currently it has a dual path:
- Legacy: Eurostat IPI datasets via `stats_lib.sources.eurostat` (live API calls)
- V5: Direct DB queries via `/api/compare?indicator=X&source=Y`

Verify: Which indicators work via direct DB? Which still need the legacy Eurostat path? Document the coverage in a table format so we know what's available.

---

### M4 -- Explorador Section (WB-style) [Coder + Criativo]

**Goal**: Multi-indicator data explorer with search, overlay, dual-axis, CSV export, permalink.

**Instructions for Coder (logic + data):**

Rewrite `static/js/sections/explorador.js`. This is the biggest frontend piece.

**Data source**: `/api/catalog` returns the full indicator catalog with metadata (label, unit, source, frequency, coverage dates). `/api/series?source=X&indicator=Y&from=...&to=...` returns time series data.

**Core features:**
1. **Catalog search**: Fetch `/api/catalog` on init. Build searchable list -- filter by `includes()` on label, source, tags. Group by source.
2. **Multi-indicator selection**: Up to 5 indicators as removable chips with source-colored badges.
3. **Smart Y-axis logic**:
   - 1 unit type -> shared Y-axis
   - 2 unit types -> dual Y-axis (left/right)
   - >2 unit types -> normalize all to index 100 (first value = 100)
4. **Time range**: From/To date inputs (YYYY-MM format) with quick presets (1yr, 2yr, 5yr, 10yr, All)
5. **Data table**: Toggle between chart and table views. Table: periods as rows, indicators as columns.
6. **CSV export**: Call `/api/export?sources=...&indicators=...&from=...&to=...` (server-side CSV generation)
7. **URL state**: `#explorador?s=INE/ipi_seasonal_cae_TOT,FRED/brent_oil&from=2020-01&to=2026-02`
8. **Share button**: Copy permalink to clipboard.

**API contract:**
- `GET /api/catalog` -> `{SOURCE: {label, indicators: {IND: {label, unit, description, since, until, rows}}}}`
- `GET /api/series?source=INE&indicator=ipi&from=2020-01` -> `[{source, indicator, label, unit, data: [{period, value, unit}]}]`
- `GET /api/export?sources=INE,FRED&indicators=ipi,brent&from=2020-01` -> CSV file download

**Chart library**: Use `SWD.createSWDChart()`, `SWD.baseOptions()`, `SWD.timeAxis()`, `SWD.valueAxis()`, `SWD.lineSeries()` from `swd-charts.js`.

**Instructions for Criativo (UI):**

Design the Explorador UI layout:
```
+--------------------------------------------------+
| [Search indicators...         ] [Source v]        |
|                                                   |
| Selected: [INE - IPI x] [FRED - Brent x] [+]     |
|                                                   |
| From: [2020-01] To: [2026-02]                     |
| [1Y] [2Y] [5Y] [10Y] [All]                       |
|                                                   |
| +-----------------------------------------------+ |
| |              ECharts graph                    | |
| |         (multi-series, smart axes)            | |
| +-----------------------------------------------+ |
|                                                   |
| [Chart] [Table] [CSV] [Share]                     |
+--------------------------------------------------+
```
The search panel should feel like the World Bank Data portal: type to filter, click to add, chips to remove.

---

### M5 -- Ficha Tecnica Section [Analyst + Einstein]

**Goal**: Complete technical reference. Every indicator in the DB listed, explained, with source links.

**Instructions for Analyst:**

Build a comprehensive Ficha Tecnica section in `static/js/sections/ficha.js`. This must be the most complete section -- it's the reference document.

**Data source**: `GET /api/catalog` returns enriched catalog with DB stats. `GET /api/resumo` has the `updated` field.

**Content structure:**

1. **Header**: "Ficha Tecnica -- {N} fontes, {N} indicadores monitorizados"
   - Last data update: {date}
   - Total observations: {N}
   - DB coverage: {earliest} -- {latest}

2. **Source cards** (one per source, expandable):
   - Source name + official label + link to official website
   - Number of indicators
   - **Full indicator table** (always visible, not collapsed):
     - Indicator ID | Label | Unit | Frequency | Coverage (since -> until) | Observations
     - Each row links to Explorador with that indicator pre-selected: `<a href="#explorador?s=SOURCE/indicator">`

3. **Methodology section** (text preserved in `docs/narratives.md` section 5):
   - Seasonality (X-13ARIMA-SEATS)
   - Base temporal (2015=100 / 2021=100)
   - European comparability
   - Spread calculation
   - Euribor methodology
   - Electricity band definition
   - EU aggregate definition
   - Update frequency

4. **Dashboard info**:
   - Version: 7.0
   - Stack: FastAPI + DuckDB + ECharts 5.5.0
   - Design: Storytelling with Data
   - Data sources: list with official URLs
   - Embed system: how to use `embed.js`

5. **Footer disclaimer**: "Nao substitui publicacoes oficiais..."

**Source metadata** lives in `app/constants/catalog.py` (CATALOG dict) and `app/constants/mappings.py` (SOURCE_META). The `/api/catalog` endpoint enriches these with DB stats.

**Instructions for Einstein:**

Review and improve the methodology descriptions. Check:
- Are the statistical methodology descriptions accurate?
- Are the Eurostat dataset references correct?
- Is the seasonality explanation clear for a non-expert?
- Add any missing methodology notes for indicators not currently documented

---

### M6 -- Embed System [Coder]

**Goal**: JS embed script that renders CAE charts in any website.

**Instructions for Coder:**

Create `static/js/embed.js` -- a self-contained IIFE (~250 lines).

**Behavior:**
1. Load ECharts 5.5.0 from CDN if not present on page
2. Scan for all `.cae-embed` elements
3. For each: read `data-*` attributes, fetch from CAE API, render ECharts chart
4. Include SWD colors/fonts inline (don't depend on swd-charts.js)
5. Add "Dados: CAE Dashboard" attribution link at chart bottom
6. On click -> open Explorador with same indicators pre-selected
7. Fire POST `/api/track` with `{event: "embed_load", host, path, extra}` (fire-and-forget)
8. Use `ResizeObserver` for responsive resize
9. Show fallback on error: "Dados indisponiveis -- ver no dashboard"

**Supported `data-*` attributes:**
- `data-indicators` (required) -- comma-separated `SOURCE/indicator` pairs
- `data-countries` (optional) -- triggers `/api/compare` mode
- `data-from`, `data-to` (optional) -- time range
- `data-height` (default 400) -- chart height in px
- `data-title` (optional) -- chart title

**API endpoints used:**
- `GET /api/series?source=X&indicator=Y&from=...` (multi-indicator mode)
- `GET /api/compare?indicator=X&source=Y&countries=...&since=...` (country mode)
- `POST /api/track` (analytics)

**Important**: The default base URL must be `https://joao.date/dados` (not cae.joao.date).
Set `const CAE_BASE = document.currentScript?.dataset?.base || 'https://joao.date/dados';` so it can be overridden.

**Add route** in `app/routes/pages.py`: `GET /embed.js` serving the file with `Cache-Control: public, max-age=3600` and `Access-Control-Allow-Origin: *`.

---

### M7 -- Hugo Integration [Scout + Coder]

**Goal**: Hugo shortcode + conditional loading + sample blog post.

**Instructions for Scout:**

Research Hugo shortcode best practices for embedding external charts. Check:
- How other Hugo sites embed Plotly, Chart.js, or D3 charts
- Best practices for async script loading in Hugo
- How to handle responsive iframes vs JS embeds in Hugo
- The existing Mermaid shortcode pattern in our site (`layouts/shortcodes/mermaid.html`)

Report findings for Coder to implement.

**Instructions for Coder:**

Create Hugo integration files at `/home/joao/docker/stacks/web/hugo-site/`:

1. **Shortcode** `layouts/shortcodes/cae-chart.html`:
   ```html
   {{ $indicators := .Get "indicators" }}
   <div class="cae-embed"
        data-indicators="{{ $indicators }}"
        {{ with .Get "countries" }}data-countries="{{ . }}"{{ end }}
        {{ with .Get "from" }}data-from="{{ . }}"{{ end }}
        {{ with .Get "to" }}data-to="{{ . }}"{{ end }}
        data-height="{{ .Get "height" | default "400" }}"
        {{ with .Get "title" }}data-title="{{ . }}"{{ end }}"
        style="margin: 1.5rem 0;">
   </div>
   ```

2. **Conditional loading** -- modify `layouts/textos/single.html`, add to `{{ define "scripts" }}`:
   ```html
   {{ if findRE "class=\"cae-embed\"" .Content }}
   <script src="https://joao.date/dados/embed.js" async></script>
   {{ end }}
   ```

3. **CSS** -- add to `assets/css/custom.css`:
   ```css
   .cae-embed { text-align: center; margin: 1.5rem 0; border-radius: 4px; }
   ```

4. **Test post** -- create `content/textos/teste-dados/index.md`:
   ```markdown
   ---
   title: "Teste de Graficos CAE"
   date: 2026-02-28
   tags: ["dados", "teste"]
   draft: true
   ---
   Teste de incorporacao de graficos do CAE Dashboard.
   {{< cae-chart indicators="INE/ipi_seasonal_cae_TOT" from="2020-01" title="Producao Industrial" >}}
   ```

**Note**: Hugo nginx has `X-Frame-Options: SAMEORIGIN`. Since we use JS embed (not iframe), this is not a problem. CORS on the CAE API already allows `*`.

---

### M8 -- Umami Analytics [Coder/Sysadmin]

**Goal**: Self-hosted visitor analytics for the dashboard and Hugo site.

**Instructions:**

Deploy Umami in the web stack.

1. **Create** `stacks/web/compose/umami.yml`:
   - `umami` container: `ghcr.io/umami-software/umami:postgresql-latest`
   - `umami-db` container: `postgres:16-alpine`
   - Network: `umami_net` (internal) + `t2_proxy` (Traefik)
   - Traefik: `stats.joao.date` with `chain-authelia@file` (admin-only UI)
   - Volume: `stacks/web/appdata/umami-db` for PostgreSQL

2. **Update** `stacks/web/compose.yml` -- add `compose/umami.yml` to includes

3. **Infisical secrets** under `/web`: `UMAMI_DB_PASSWORD`, `UMAMI_APP_SECRET`

4. **Cloudflare DNS**: add `stats` CNAME

5. **Tracking scripts**:
   - CAE dashboard `templates/dashboard.html`: `<script async src="https://stats.joao.date/script.js" data-website-id="ID"></script>`
   - Hugo `layouts/partials/head.html`: same script tag

---

## Execution Order

Build progressively -- each module adds functionality to the skeleton:

```
M1 (Skeleton + DB migration)     <-- Claude/Core -- do first, deployable
 +-- M2 (Painel)                 <-- Criativo -- can start immediately after M1
 +-- M3 (Europa simplified)      <-- Criativo + Analyst -- parallel with M2
 +-- M5 (Ficha Tecnica)          <-- Analyst + Einstein -- parallel with M2
 |
 +-- M4 (Explorador WB-style)    <-- Coder + Criativo -- largest piece, start early
 |
 +-- M6 (Embed system)           <-- Coder -- after M4 (shares chart logic)
 +-- M7 (Hugo integration)       <-- Scout + Coder -- after M6
 |
 +-- M8 (Umami)                  <-- Coder/Sysadmin -- independent, any time
```

**Deployment increments:**
1. After M1: Empty 4-tab skeleton with analytics, old APIs still work
2. After M1+M2: Painel section live
3. After M1+M2+M3: Europa section live
4. After M1+M2+M3+M5: Ficha Tecnica live (dashboard is usable at this point)
5. After M4: Explorador live (full data platform)
6. After M6+M7: Embed system working, charts in Hugo posts
7. After M8: Full analytics

---

## Backend API -- Final Endpoint Map

| Endpoint | Method | Status | Used By |
|----------|--------|--------|---------|
| `/api/resumo` | GET | **Active** | Painel |
| `/api/series` | GET | **Active** | Explorador, Embed |
| `/api/compare` | GET | **Active** | Europa, Embed |
| `/api/catalog` | GET | **Active** | Explorador, Ficha |
| `/api/explorador` | GET | **Active** | Explorador |
| `/api/events` | GET | **Active** | Charts |
| `/api/export` | GET | **NEW** | Explorador CSV |
| `/api/track` | POST | **NEW** | Embed analytics |
| `/api/stats` | GET | **NEW** | Admin analytics |
| `/api/data` | GET | **Active** | Generic dump |
| `/api/kpis` | GET | **Active** | Generic |
| `/api/industria` | GET | Deprecated | OpenClaw compat |
| `/api/energia` | GET | Deprecated | OpenClaw compat |
| `/api/emprego` | GET | Deprecated | OpenClaw compat |
| `/api/macro` | GET | Deprecated | OpenClaw compat |
| `/api/fosso` | GET | Deprecated | OpenClaw compat |
| `/api/produtividade` | GET | Deprecated | OpenClaw compat |
| `/api/briefing` | GET | Deprecated | OpenClaw compat |
| `/api/summary` | GET | Deprecated | OpenClaw compat |
| `/api/europa` | GET | Deprecated | Use /api/compare |
| `/healthz` | GET | **Active** | Docker healthcheck |
| `/docs` | GET | **Active** | Swagger UI |
| `/embed.js` | GET | **NEW** | Embed script |

---

## Key Design Decisions

1. **4 sections, not 3** -- Ficha Tecnica is a full section, not a footer. It must list ALL 376 indicators with metadata and links.
2. **Primary URL is `joao.date/dados`** -- embed.js defaults to this. `cae.joao.date` stays as alias.
3. **DB moves to `stacks/jarbas/appdata/cae-dashboard/`** -- decoupled from OpenClaw. Symlink for backward compat.
4. **DuckDB read-only, analytics in SQLite** -- separate concerns, no write contention.
5. **Old API endpoints deprecated, not deleted** -- OpenClaw agent may consume them. `X-CAE-Deprecated` header signals deprecation.
6. **Narratives preserved in `docs/narratives.md`** -- version-controlled reference for future Hugo blog posts.
7. **Europa simplified via progressive disclosure** -- presets first, custom picker hidden behind "Personalizar".
8. **JS embed (not iframe)** -- Hugo nginx has `X-Frame-Options: SAMEORIGIN`; JS embed avoids this entirely.
9. **Work packages for Jarbas team** -- each module has clear instructions and can be built independently.

---

## Verification Checklist

### M1 (Skeleton)
- [ ] `dc-jarbas-up cae-dashboard` builds and starts
- [ ] `curl https://joao.date/dados/healthz` returns `{"status":"ok"}`
- [ ] Dashboard shows 4 empty tabs
- [ ] `POST /api/track` returns `{"ok":true}`
- [ ] `GET /api/stats` returns event counts
- [ ] Old APIs still work with deprecation header
- [ ] DB at new location: `ls stacks/jarbas/appdata/cae-dashboard/cae-data.duckdb`

### M2-M5 (Sections)
- [ ] Painel: KPI cards with sparklines, no narratives
- [ ] Europa: simplified controls, URL state persists on reload, share copies link
- [ ] Explorador: search indicators, select multiple, overlay chart, CSV export, permalink
- [ ] Ficha: all 376 indicators listed with metadata, links to Explorador

### M6-M7 (Embed)
- [ ] Test HTML with `.cae-embed` div + embed.js renders chart
- [ ] Hugo post with `{{< cae-chart >}}` renders chart
- [ ] `/api/stats?event_type=embed_load` shows tracking

### M8 (Umami)
- [ ] `https://stats.joao.date` shows Umami login (behind Authelia)
- [ ] Visit dashboard shows page view in Umami

---

## Reference Files

| File | Purpose |
|------|---------|
| `docs/narratives.md` | All extracted narrative text from deleted sections |
| `docs/analise-content.html` | Original Jan 2025 analysis article (HTML) |
| `docs/analise-metadata.json` | Metadata for Jan 2025 analysis |
| `app/constants/catalog.py` | Indicator catalog with metadata |
| `app/constants/mappings.py` | Source metadata, unit overrides |
| `app/constants/countries.py` | EU country list and comparison datasets |
| `static/js/swd-charts.js` | SWD chart factory (unchanged) |
