# 📚 Prumo Documentation Index

Central reference for all Prumo project documentation, organized by topic and use case.

---

## 🗂️ Quick Navigation

### Getting Started
- **[Prumo README](../README.md)** — Project overview, architecture, features
- **[design-guide.md](design-guide.md)** — Visual standards, KPI anatomy, design principles
- **[API Endpoints Guide](../routes/api.py)** — Backend API reference

### Operations & Deployment
- **[operations/MIGRATION_RUNBOOK.md](operations/MIGRATION_RUNBOOK.md)** — Safe cutover procedure with go/no-go gates and rollback
- **[operations/PHASE_1_SUMMARY.md](operations/PHASE_1_SUMMARY.md)** — Initial deployment checkpoints
- **[operations/PHASE_2_FRONTEND_TESTING.md](operations/PHASE_2_FRONTEND_TESTING.md)** — Validation & testing procedures
- **[operations/PHASE_3_CI_CD_AUTOMATION.md](operations/PHASE_3_CI_CD_AUTOMATION.md)** — Continuous deployment setup
- **[operations/PHASE_4_MONITORING.md](operations/PHASE_4_MONITORING.md)** — Health checks & observability

### Developer Guides
- **[planning/PLAN-V7.md](planning/PLAN-V7.md)** — Architecture & feature planning (V7 era)
- **[planning/PRUMO-ROADMAP.md](planning/PRUMO-ROADMAP.md)** — Feature roadmap & future direction
- **[data/NORMALIZATION.md](data/NORMALIZATION.md)** — Data normalization standards & procedures

### Data & Sources
- **[data/painel-indicators-audit.md](data/painel-indicators-audit.md)** — Indicator coverage & validation
- **[data/worldbank-gdp-collector-notes.md](data/worldbank-gdp-collector-notes.md)** — GDP collector specifics
- **[data/europa-coverage.md](data/europa-coverage.md)** — EU country comparison data
- **[../SOURCES.md](../SOURCES.md)** — Official source registry (in root)

### Design & UX
- **[design/](design/)** — Design inspired by *Storytelling with Data* (Cole Nussbaumer Knaflic, Wiley, 2015), with open-source implementations and project notes
- **[wp7-design-strings.md](wp7-design-strings.md)** — UI string references & localization
- **[content/narratives.md](content/narratives.md)** — How AI-generated narratives work

### Context & Reference
- **[content/pcp-estatutos.md](content/pcp-estatutos.md)** — PCP party platform reference
- **[content/pcp-programa.md](content/pcp-programa.md)** — PCP political program (for ideology lenses)
- **[research/hugo-integration-research.md](research/hugo-integration-research.md)** — Hugo CMS exploration
- **[research/historical-energy-prices-eu-us-portugal.md](research/historical-energy-prices-eu-us-portugal.md)** — Historical energy prices reference for EU/US/Portugal

### Testing
- **[testing/](testing/)** — Test fixtures, data, and test documentation

---

## 📑 Detailed Document Guide

### By Category

#### 🚀 Deployment & Operations
| Document | Purpose | Audience |
|----------|---------|----------|
| **MIGRATION_RUNBOOK.md** | Step-by-step cutover with decision gates, preconditions, rollback | DevOps, operators |
| **PHASE_1_SUMMARY.md** | Initial deployment validation checklist | Ops, testers |
| **PHASE_2_FRONTEND_TESTING.md** | UI/UX validation, browser testing procedures | QA, frontend devs |
| **PHASE_3_CI_CD_AUTOMATION.md** | GitHub Actions, automated testing, deployment pipelines | DevOps, CI/CD engineers |
| **PHASE_4_MONITORING.md** | Health checks, alerting, observability setup | Ops, SREs |

#### 🎨 Design & Frontend
| Document | Purpose | Audience |
|----------|---------|----------|
| **DESIGN.md** | Visual standards, KPI card anatomy, color/typography rules | Designers, frontend devs |
| **[design/](design/)** | SWD-inspired notes and open-source Python/R/JS chart examples | Designers, data viz developers |
| **WP7 Design Strings** | UI copy, labels, error messages | Translators, UX writers |
| **Narratives.md** | AI-generated trend analysis & interpretation | Backend/AI developers |

#### 📊 Data & Indicators
| Document | Purpose | Audience |
|----------|---------|----------|
| **painel-indicators-audit.md** | Coverage audit for all 500+ indicators | Data engineers, analysts |
| **worldbank-gdp-collector-notes.md** | GDP collector implementation details | Collector developers |
| **europa-coverage.md** | EU country comparison metadata & gaps | Analytics, data team |
| **NORMALIZATION.md** | Period handling, unit conversion, data cleaning standards | Data engineers |
| **../SOURCES.md** | Official source registry (INE, Eurostat, FRED, etc) | Everyone |

#### 📈 Architecture & Planning
| Document | Purpose | Audience |
|----------|---------|----------|
| **PLAN-V7.md** | V7 architecture decisions, service layer design | Architects, lead developers |
| **PRUMO-ROADMAP.md** | Upcoming features, priorities, timeline | PMs, stakeholders |
| **../README.md** | Full project architecture, services, endpoints | All developers |

#### 🔗 Context & References
| Document | Purpose | Audience |
|----------|---------|----------|
| **pcp-estatutos.md** | PCP party constitution (for ideology lens) | Political context researchers |
| **pcp-programa.md** | PCP political program (for ideology lens) | Political context researchers |
| **hugo-integration-research.md** | Exploration of Hugo CMS static site integration | Architects, interested devs |

#### 🧪 Testing
| Document | Purpose | Audience |
|----------|---------|----------|
| **testing/** | Test fixtures, sample data, testing docs | QA, test developers |

#### 📦 Archive
| Document | Purpose | Status |
|----------|---------|--------|
| **archive/** | Pre-migration files, deprecated configs, old analyses | Reference only |

---

## 🎯 Use Cases

### "I'm deploying Prumo for the first time"
1. Read **MIGRATION_RUNBOOK.md** (preconditions → cutover → validation)
2. Reference **PHASE_1_SUMMARY.md** for checklist
3. Review **PHASE_3_CI_CD_AUTOMATION.md** to set up automated testing

### "I'm designing a new KPI card"
1. Review **DESIGN.md** for standards
2. Check **[design/README.md](design/README.md)** for SWD examples
3. Reference **painel-indicators-audit.md** for available indicators

### "I'm adding a new data source"
1. Check **../SOURCES.md** for structure
2. Review **NORMALIZATION.md** for data standards
3. Study collector in `collectors/` directory
4. Document updates in a collector-specific doc (like **worldbank-gdp-collector-notes.md**)

### "I'm troubleshooting an issue"
1. Check **PHASE_4_MONITORING.md** for health checks
2. Review **MIGRATION_RUNBOOK.md** section 7 for rollback
3. Look in **testing/** for test data to reproduce

### "I need to understand how narratives work"
1. Read **Narratives.md** for overview
2. Check `app/services/interpret.py` for implementation
3. Reference `app/services/ideology_lenses.py` for lens system

### "I want to add political context to an analysis"
1. Review **pcp-estatutos.md** and **pcp-programa.md**
2. Check `app/services/ideology_lenses.py` for how lenses work
3. Read **Narratives.md** for integration points

---

## 📋 Status Legend

| Status | Meaning |
|--------|---------|
| ✅ Current | Active, regularly updated |
| 🔄 In Progress | Under development |
| ⚠️ Legacy | Outdated but preserved for reference |
| 📦 Archive | Historical, no longer actively used |

---

## 🔗 Related Documentation

**Outside this folder:**
- [**../README.md**](../README.md) — Main project README
- [**../.github/copilot-instructions.md**](../.github/copilot-instructions.md) — AI agent guidelines
- [**../SOURCES.md**](../SOURCES.md) — Data source registry
- [**../CONTRIBUTING.md**](../CONTRIBUTING.md) — Contribution guidelines
- [**~/docker/md/browser-automation.md**](/docker/md/browser-automation.md) — Playwright testing guide

---

## 📝 How to Add Documentation

When adding new docs:
1. **Name clearly:** `topic-purpose.md` (e.g., `email-service-integration.md`)
2. **Add to this index** in appropriate category above
3. **Include a one-liner** describing purpose & audience
4. **Link internally** to related docs
5. **Archive** old versions when superseded (move to `archive/`)

---

## 🗣️ Questions?

- Architecture questions → Read **PLAN-V7.md** + **../README.md**
- Deployment questions → Read **MIGRATION_RUNBOOK.md**
- Data questions → Read **SOURCES.md** + **NORMALIZATION.md**
- Design questions → Read **DESIGN.md** + **[design/README.md](design/README.md)**
- Testing questions → Read **PHASE_2_FRONTEND_TESTING.md** + **testing/**

---

**Last Updated:** March 5, 2026  
**Maintainer:** Prumo team  
**Version:** 1.0
