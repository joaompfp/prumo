# Prumo

Economic indicators dashboard built with **FastAPI** + **DuckDB** + **ECharts**, serving 11 interactive sections with data from 9 official statistical sources.

<img width="1471" height="1082" alt="image" src="https://github.com/user-attachments/assets/a2a779d1-a2ec-40c8-8e38-a47f040a7600" />


## Architecture

```
prumo/
├── app/                          # FastAPI application
│   ├── main.py                   # App entrypoint, CORS, static mount, healthcheck
│   ├── config.py                 # Environment variables and paths
│   ├── database.py               # Thread-safe DuckDB connection pool
│   ├── constants/                # Static data (catalog, events, country lists)
│   │   ├── catalog.py            # CATALOG — 8 sources, ~60 indicators
│   │   ├── events.py             # CHART_EVENTS, BRIEFING/SUMMARY indicator lists
│   │   ├── countries.py          # COMPARE_COUNTRIES, COMPARE_DATASETS
│   │   └── mappings.py           # USED_IN, FRED_SERIES, WB_CODES, SOURCE_META
│   ├── routes/
│   │   ├── api.py                # /api/* endpoints (thin handlers → services)
│   │   └── pages.py              # GET / — serves dashboard via Jinja2
│   └── services/                 # Business logic, one module per section
│       ├── helpers.py            # Shared: YoY, trend, sparkline, period utils
│       ├── resumo.py             # Resumo KPIs
│       ├── industria.py          # Industrial production (IPI)
│       ├── energia.py            # Energy (REN, E-REDES, DGEG)
│       ├── emprego.py            # Employment (IEFP, INE)
│       ├── macro.py              # Macro indicators (GDP, inflation, trade)
│       ├── ficha.py              # Data sheet / DB stats
│       ├── fosso.py              # EU convergence gap
│       ├── produtividade.py      # Productivity metrics
│       ├── analysis.py           # Automated trend analysis
│       ├── explorador.py         # Data explorer catalog
│       ├── series.py             # Generic time series queries + country compare
│       └── briefing.py           # Auto-generated briefing + summary
├── templates/
│   └── dashboard.html            # SPA shell (Jinja2, hash router, ECharts)
├── static/
│   ├── css/
│   │   ├── swd-theme.css         # Storytelling with Data theme
│   │   └── sections.css          # Section-specific styles
│   └── js/
│       ├── app.js                # Hash router + lazy section loading
│       ├── api.js                # Fetch wrappers with 5-min cache
│       ├── swd-charts.js         # SWD chart factory (ECharts)
│       └── sections/             # 11 section initializers (one per tab)
├── collectors/                   # Data source clients (CLI tools)
│   ├── ine.py                    # INE — Instituto Nacional de Estatística
│   ├── eurostat.py               # Eurostat
│   ├── fred.py                   # FRED — Federal Reserve Economic Data
│   ├── oecd.py                   # OECD
│   ├── bportugal.py              # Banco de Portugal
│   ├── ren.py                    # REN — Rede Energética Nacional
│   ├── eredes.py                 # E-REDES — electricity distribution
│   ├── dgeg_fuel_api.py          # DGEG — fuel prices
│   └── worldbank.py              # World Bank
├── stats_lib/                    # Shared data layer for collectors
├── scripts/
│   ├── cae-collect               # Main collection orchestrator
│   └── cae-v4-backfill.py        # Historical data backfill
├── analise-content.html          # Pre-rendered analysis content
├── analise-metadata.json         # Analysis metadata
├── requirements.txt              # Python dependencies
└── Dockerfile                    # Python 3.12 + uvicorn
```

## Data Sources

| Source | Provider | Data |
|--------|----------|------|
| INE | Instituto Nacional de Estatística | Industrial production, employment, GDP, trade |
| Eurostat | European Commission | Cross-country comparisons (manufacturing, GDP, unemployment) |
| FRED | Federal Reserve Bank of St. Louis | US interest rates, global benchmarks |
| OECD | Organisation for Economic Co-operation | Composite leading indicators, productivity |
| BdP | Banco de Portugal | Monetary/financial indicators |
| REN | Rede Energética Nacional | Electricity consumption/production |
| E-REDES | Electricity distribution | Grid distribution data |
| DGEG | Direcção-Geral de Energia e Geologia | Fuel prices |
| World Bank | World Bank Group | Long-term development indicators |

## Dashboard Sections

| Section | Route | API | Description |
|---------|-------|-----|-------------|
| Resumo | `#resumo` | `/api/resumo` | Overview KPIs with sparklines and trends |
| Indústria | `#industria` | `/api/industria` | Industrial Production Index (IPI) by sector |
| Europa | `#europa` | `/api/europa` | PT vs EU country comparisons |
| Energia | `#energia` | `/api/energia` | Energy consumption and production |
| Emprego | `#emprego` | `/api/emprego` | Employment, unemployment, job offers |
| Macro | `#macro` | `/api/macro` | GDP, inflation, trade balance |
| Análise | `#analise` | `/api/analysis` | Automated trend analysis |
| Fosso | `#fosso` | `/api/fosso` | EU convergence gap |
| Produtividade | `#produtividade` | `/api/produtividade` | Labour productivity metrics |
| Explorador | `#explorador` | `/api/explorador` | Data explorer (all indicators) |
| Ficha Técnica | `#ficha` | `/api/ficha` | Data sheet, DB stats, sources |

## API Endpoints

All endpoints are under `/api/` and return JSON.

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/api/resumo` | GET | — | Summary KPIs |
| `/api/industria` | GET | `period` (int, default 5) | IPI sectors data |
| `/api/europa` | GET | `dataset`, `countries`, `months`, `indicator`, `source`, `since` | Country comparison |
| `/api/energia` | GET | — | Energy data |
| `/api/emprego` | GET | — | Employment data |
| `/api/macro` | GET | — | Macro indicators |
| `/api/ficha` | GET | — | DB stats and source metadata |
| `/api/fosso` | GET | — | EU convergence gap |
| `/api/produtividade` | GET | — | Productivity metrics |
| `/api/analysis` | GET | — | Automated trend analysis |
| `/api/explorador` | GET | — | Full indicator catalog |
| `/api/briefing` | GET | — | Auto-generated briefing |
| `/api/summary` | GET | — | Executive summary |
| `/api/series` | GET | `source`, `indicator`, `from`, `to` | Raw time series query |
| `/api/compare` | GET | `dataset`, `countries`, `months`, `indicator`, `source`, `since` | Country comparison (alias for europa) |
| `/api/data` | GET | — | Full dataset dump |
| `/api/kpis` | GET | — | Latest value per indicator |
| `/api/catalog` | GET | — | CATALOG enriched with DB stats |
| `/api/events` | GET | — | Historical event markers |
| `/healthz` | GET | — | Health check |
| `/docs` | GET | — | Swagger UI (auto-generated) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAE_DB_PATH` | `/data/cae-data.duckdb` | Path to main DuckDB database |
| `CAE_PORT` | `8080` | Server port |
| `CAE_BASE_PATH` | `""` | URL base path (for subpath serving) |
| `SKILLS_DIR` | `/home/node/.openclaw/workspace/skills/cae-reports` | Path to OpenClaw skills directory |
| `TZ` | — | Timezone (from compose) |

## Deployment

The dashboard runs as a Docker container behind Traefik reverse proxy.

### Build and deploy

```bash
dc-jarbas-up cae-dashboard
```

### Routes

- **Primary**: `https://cae.joao.date` — direct access
- **Subpath**: `https://joao.date/dados` — served under subpath with Traefik StripPrefix

The subpath route uses Traefik's `StripPrefix` middleware which sets `X-Forwarded-Prefix: /dados`. The app reads this header to inject the correct `BASE_PATH` into the template, so all static asset and API URLs resolve correctly.

### Collect data

```bash
docker exec cae-dashboard ./scripts/cae-collect
```

## Run standalone (without Docker)

You can run Prumo directly on your machine with Python:

```bash
./scripts/run-standalone
```

This launcher will:
- create `.venv` automatically (if missing),
- install `requirements.txt`,
- default data paths to `./data` when `/data` is not available.

Optional overrides:

```bash
CAE_DATA_DIR=./data \
CAE_DB_PATH=./data/cae-data.duckdb \
ANALYTICS_DB_PATH=./data/analytics.db \
CAE_PORT=8080 \
./scripts/run-standalone
```

## Technical Notes

- **Single worker**: Uvicorn runs with `--workers 1` because DuckDB connections are not thread-safe. FastAPI's thread pool handles concurrent requests via per-thread connection reuse.
- **No auth**: Dashboard is public (`chain-no-auth@file` middleware in Traefik).
- **SPA routing**: The frontend uses hash-based routing (`#section`). All navigation is client-side; the server only serves the single HTML shell.
- **Chart library**: ECharts 5.5.0 (CDN) with a custom SWD (Storytelling with Data) theme.
- **Caching**: `api.js` caches API responses in memory for 5 minutes to reduce DB load during tab switching.
- **Database**: DuckDB in read-only mode. Data is collected externally by the `cae-collect` script and written to the database separately.
