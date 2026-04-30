# 🗺️ Prumo Documentation & Resources Map

Quick visual guide to all Prumo documentation, guides, and resources organized by function.

---

## 📖 Documentation Structure

```
/home/joao/docker/stacks/web/images/prumo/

├── README.md                          # Main project overview
├── .github/copilot-instructions.md    # AI agent guidelines
├── CONTRIBUTING.md                    # Contribution procedures
├── SOURCES.md                         # Data source registry
│
├── docs/
│   ├── README.md                      # ⭐ Central documentation index
│   ├── design-guide.md                # Visual standards & design guide
│   ├── wp7-design-strings.md          # UI copy & labels
│   │
│   ├── operations/                    # Deployment & operations
│   │   ├── MIGRATION_RUNBOOK.md       # Deployment procedure
│   │   ├── PHASE_1_SUMMARY.md         # Initial setup
│   │   ├── PHASE_2_FRONTEND_TESTING.md
│   │   ├── PHASE_3_CI_CD_AUTOMATION.md
│   │   └── PHASE_4_MONITORING.md
│   │
│   ├── planning/                      # Architecture & roadmap
│   │   ├── PLAN-V7.md                 # Architecture & planning
│   │   └── PRUMO-ROADMAP.md           # Feature roadmap
│   │
│   ├── data/                          # Data standards & coverage
│   │   ├── NORMALIZATION.md           # Data standards
│   │   ├── painel-indicators-audit.md # Indicator coverage
│   │   ├── worldbank-gdp-collector-notes.md
│   │   └── europa-coverage.md
│   │
│   ├── content/                       # Narratives & political context
│   │   ├── narratives.md              # AI narrative generation
│   │   ├── pcp-estatutos.md           # Political context
│   │   └── pcp-programa.md
│   │
│   ├── research/                      # Exploratory research
│   │   └── hugo-integration-research.md
│   │
│   ├── design/                        # SWD-inspired design references (no copyrighted binaries)
│   │   ├── README.md                  # Attribution + design resource policy
│   │   ├── swd-python-matplotlib/     # Matplotlib chart examples
│   │   ├── swd-r-ggplot/              # R ggplot2 examples + theme
│   │   └── swd-highcharts-nextjs/     # React/Next.js components
│   │
│   ├── testing/                       # Test fixtures & data
│   └── archive/                       # Historical/deprecated docs
│
├── app/
│   ├── services/                      # Business logic (helpers, compute, analysis)
│   ├── routes/api.py                  # API endpoint reference
│   └── main.py                        # FastAPI app entry
│
├── static/js/
│   ├── api.js                         # Frontend API client
│   ├── app.js                         # Hash router
│   └── sections/                      # UI section components
│
├── collectors/                        # Data source integrations
├── scripts/
│   ├── collectors/                    # Data collection orchestration
│   │   ├── cae-collect                # Main collection orchestrator
│   │   ├── cae-v4-backfill.py         # Historical data backfill
│   │   └── collect_*.py               # Individual collector scripts
│   │
│   ├── ai/                            # AI analysis & generation
│   │   ├── batch_*.sh                 # Batch processing for AI
│   │   └── generate_*.py              # Analysis & headline generation
│   │
│   └── maintenance/                   # Data management & maintenance
│       ├── normalize_db.py            # Database normalization
│       └── merge_staging.py           # Data merge operations
│
├── venv/                              # Python environment (Playwright, deps)
│
└── .github/
    ├── copilot-instructions.md        # AI agent coding guidelines
    └── CLAUDE.md (~docker/CLAUDE.md)  # Broader workspace context
```

---

## 🗂️ Navigation Quick Links

### For Different Roles

#### 👤 Project Manager / Product Owner
Start here:
1. [Prumo README](README.md) — Feature overview
2. [PRUMO-ROADMAP.md](docs/planning/PRUMO-ROADMAP.md) — What's coming
3. [docs/README.md](docs/README.md) — Full doc index
4. [SOURCES.md](SOURCES.md) — Data coverage

#### 👨‍💻 Backend Developer
Start here:
1. [README.md](README.md) — Architecture overview
2. [.github/copilot-instructions.md](.github/copilot-instructions.md) — Code conventions
3. [docs/planning/PLAN-V7.md](docs/planning/PLAN-V7.md) — Design decisions
4. [docs/data/NORMALIZATION.md](docs/data/NORMALIZATION.md) — Data standards
5. `collectors/` — Data source implementations

#### 🎨 Frontend / UX Designer
Start here:
1. [docs/design-guide.md](docs/design-guide.md) — Visual standards
2. [docs/design/README.md](docs/design/README.md) — SWD design resources
3. [docs/wp7-design-strings.md](docs/wp7-design-strings.md) — UI copy & labels
4. `static/` — CSS, JS, components

#### 🚀 DevOps / SRE
Start here:
1. [docs/operations/MIGRATION_RUNBOOK.md](docs/operations/MIGRATION_RUNBOOK.md) — Safe deployment
2. [docs/operations/PHASE_1_SUMMARY.md](docs/operations/PHASE_1_SUMMARY.md) — Initial setup
3. [docs/operations/PHASE_3_CI_CD_AUTOMATION.md](docs/operations/PHASE_3_CI_CD_AUTOMATION.md) — Automation
4. [docs/operations/PHASE_4_MONITORING.md](docs/operations/PHASE_4_MONITORING.md) — Health checks

#### 🧪 QA / Test Engineer
Start here:
1. [docs/operations/PHASE_2_FRONTEND_TESTING.md](docs/operations/PHASE_2_FRONTEND_TESTING.md) — Test procedures
2. [docs/testing/](docs/testing/) — Test fixtures & data
3. [~docker/md/browser-automation.md](/docker/md/browser-automation.md) — Playwright notes
4. `tests/` — Your test code

#### 🔍 Data Analyst
Start here:
1. [SOURCES.md](SOURCES.md) — Data sources & coverage
2. [docs/data/painel-indicators-audit.md](docs/data/painel-indicators-audit.md) — All 500+ indicators
3. [docs/data/NORMALIZATION.md](docs/data/NORMALIZATION.md) — Data standards
4. [docs/data/europa-coverage.md](docs/data/europa-coverage.md) — EU comparison data
5. [docs/data/worldbank-gdp-collector-notes.md](docs/data/worldbank-gdp-collector-notes.md) — GDP specifics

#### 🤖 AI / ML Developer
Start here:
1. [docs/content/narratives.md](docs/content/narratives.md) — AI narrative generation
2. `app/services/interpret.py` — LLM integration
3. `app/services/ideology_lenses.py` — Political context lenses
4. [docs/content/pcp-*.md](docs/content/) — Political program context

---

## 🛠️ Tools & Utilities

### Browser Automation
- **Location:** `venv/bin/python` (Playwright installed)
- **Bash aliases:** `pw*` commands in `~/.bash_aliases`
- **Guide:** `/docker/md/browser-automation.md`
- **Usage:** `pw https://joao.date/dados`, `pw-test`, `pw-snap <url>`

### Testing
- **Framework:** pytest
- **Config:** `pytest.ini`
- **Test code:** `tests/` folder
- **Run:** `pytest -v` or `py-test` alias

### Code Quality
- **Python style:** Per [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Linting:** pytest with coverage
- **Type hints:** Explicit in helpers/services

### Data Collection
- **Collectors:** `scripts/collectors/` Python modules and orchestrator
- **Main script:** `scripts/collectors/cae-collect` bash orchestrator
- **Backfill:** `scripts/collectors/cae-v4-backfill.py`
- **Individual collectors:** `scripts/collectors/collect_*.py` (by source)

---

## 📊 Key Concepts

| Concept | Definition | Reference |
|---------|-----------|-----------|
| **KPI Card** | Atomic unit (metric + trend + YoY + sparkline) | [design-guide.md](docs/design-guide.md) |
| **Service** | Business logic module returning structured JSON | [PLAN-V7.md](docs/planning/PLAN-V7.md) |
| **Collector** | Data source client (INE, Eurostat, etc) | `collectors/`  |
| **Period** | Time unit (YYYY-MM, YYYY-Q{N}, YYYY) | [NORMALIZATION.md](docs/data/NORMALIZATION.md) |
| **Sentiment** | Good/neutral/bad indicator classification | [design-guide.md](docs/design-guide.md) |
| **Lens** | Political perspective filter for narratives | [narratives.md](docs/content/narratives.md) |
| **Sparkline** | Tiny 60px chart showing recent trend | [design-guide.md](docs/design-guide.md) |

---

## 🔗 External Links

### Official Sources
- **INE** (Portugal) — [www.ine.pt](https://www.ine.pt)
- **Eurostat** (EU) — [ec.europa.eu/eurostat](https://ec.europa.eu/eurostat/)
- **FRED** (Fed Reserve) — [fred.stlouisfed.org](https://fred.stlouisfed.org)
- **OECD** — [oecd.org](https://www.oecd.org)
- **World Bank** — [worldbank.org](https://www.worldbank.org)

### Related Projects
- **Storytelling with Data** — [storytellingwithdata.com](https://www.storytellingwithdata.com/)
- **FastAPI** — [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **DuckDB** — [duckdb.org](https://duckdb.org/)
- **ECharts** — [echarts.apache.org](https://echarts.apache.org/)
- **Playwright** — [playwright.dev](https://playwright.dev/)

---

## 📱 Common Tasks

### "I need to deploy Prumo"
→ Read `docs/operations/MIGRATION_RUNBOOK.md` (6-section procedure + rollback)

### "I need to add a new KPI"
→ Read `docs/design-guide.md` + `app/services/painel.py`

### "I need to add a new data source"
→ Read `SOURCES.md` + `collectors/ine.py` (template) + `docs/data/NORMALIZATION.md`

### "I need to troubleshoot a deployment"
→ Read `docs/operations/PHASE_4_MONITORING.md` + `docs/operations/MIGRATION_RUNBOOK.md` section 6

### "I need to design a new visualization"
→ Read `docs/design-guide.md` + `docs/design/README.md`

### "I need to understand the data flow"
→ Read `README.md` "Data Sources" + `SOURCES.md` + `docs/data/NORMALIZATION.md`

### "I need to add political context"
→ Read `docs/content/narratives.md` + `docs/content/pcp-*.md` + `app/services/ideology_lenses.py`

---

## ✅ Organization Checklist

- [x] Central docs index: `docs/README.md`
- [x] Design guide: `docs/design-guide.md`
- [x] Design resources: `docs/design/` (SWD-inspired notes + open implementations only)
- [x] Deployment runbook: `docs/operations/MIGRATION_RUNBOOK.md`
- [x] AI agent guidelines: `.github/copilot-instructions.md`
- [x] Browser automation: `docker/md/browser-automation.md`
- [x] Bash aliases: `~/.bash_aliases` (pw*, pwenv)
- [x] Docker workspace docs: `docker/CLAUDE.md`

---

**Last Updated:** March 5, 2026  
**Purpose:** Quick navigation and role-based guidance  
**Audience:** All Prumo contributors
