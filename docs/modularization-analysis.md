# Análise de Modularização — Prumo

**Data**: 2026-03-16

## Resumo

Análise dos ficheiros da aplicação Prumo (dashboard de indicadores económicos para Portugal) com foco em oportunidades de modularização. A aplicação usa FastAPI + DuckDB + ECharts.

## Métricas dos Ficheiros

### Python (20,132 linhas total)

| Ficheiro | Linhas | Notas |
|----------|--------|-------|
| `app/constants/catalog.py` | 2,897 | Catálogo de ~380 indicadores como dicionário Python |
| `collectors/ine.py` | 776 | Client API do INE |
| `app/routes/api.py` | 738 | 20+ endpoints REST |
| `app/services/quality.py` | 484 | 5 checks de qualidade de dados |
| `collectors/eurostat.py` | 488 | Client API Eurostat |
| `collectors/oecd.py` | 453 | Client API OECD |
| `collectors/eredes.py` | 441 | Client API E-REDES |
| `scripts/backfill_full.py` | 447 | Backfill histórico |
| `app/services/painel_analysis.py` | 414 | Análise AI + cache + parsing |
| `app/services/ideology_lenses.py` | 367 | Definições de lentes ideológicas |

### JavaScript (6,117 linhas total)

| Ficheiro | Linhas | Notas |
|----------|--------|-------|
| `static/js/sections/painel.js` | 1,225 | Cards KPI + sparklines + headlines |
| `static/js/sections/analise.js` | 1,180 | Painel de análise + gráficos + interpretação |
| `static/js/sections/explorador.js` | 667 | Explorador de dados multi-select |
| `static/js/app.js` | 591 | Router hash + theme toggle |
| `static/js/sections/comparativos.js` | 526 | Comparações entre países |
| `static/js/search.js` | 460 | Pesquisa global |
| `static/js/swd-charts.js` | 399 | Factory ECharts |
| `static/js/embed.js` | 367 | Embedding de gráficos |

### CSS (4,806 linhas total)

| Ficheiro | Linhas | Notas |
|----------|--------|-------|
| `static/css/sections.css` | 3,315 | CSS monolítico para todas as secções |
| `static/css/swd-theme.css` | 852 | Design system tokens |
| `static/css/mobile.css` | 333 | Breakpoints responsivos |
| `static/css/nav-brand.css` | 298 | Navegação e branding |

## Oportunidades de Modularização

### Prioridade 1 — Quick Wins (1-2 dias)

#### 1.1 `catalog.py` (2,897 linhas) → JSON externo

- **Problema**: Metadata estática armazenada como código Python
- **Solução**: Exportar para `data/catalog.json`, criar loader de ~50 linhas
- **Benefício**: Ficheiro de configuração editável sem tocar em código; diffs mais limpos

#### 1.2 `sections.css` (3,315 linhas) → Dividir por componente

- **Problema**: CSS monolítico impossível de navegar
- **Solução**: Dividir em ficheiros por componente:
  - `css/components/search-bar.css` (~100 linhas)
  - `css/components/kpi-cards.css` (~400 linhas)
  - `css/components/charts.css` (~300 linhas)
  - `css/components/explorer.css` (~200 linhas)
  - `css/components/analysis.css` (~300 linhas)
  - etc.
- **Benefício**: Facilita manutenção e localização de estilos

#### 1.3 `quality.py` (484 linhas) → 5 módulos separados

- **Problema**: 5 checks completamente independentes num só ficheiro
- **Solução**: Criar `services/quality/` com:
  - `check_drift.py` — Catalog drift
  - `check_freshness.py` — Data recency
  - `check_flatline.py` — Valores idênticos
  - `check_orphan.py` — Indicadores órfãos
  - `check_coverage.py` — Cobertura regional
- **Benefício**: Cada check testável e mantível independentemente

#### 1.4 `api.py` (738 linhas) → Extrair lógica inline

- **Problema**: Endpoint `/link-title` tem 157 linhas de scraping HTML + cache inline
- **Solução**: Mover para `services/link_scraper.py`
- **Benefício**: Endpoint fica thin; lógica de scraping reutilizável e testável

### Prioridade 2 — Refactoring Médio (3-5 dias)

#### 2.1 `painel.js` (1,225 linhas) → 3 módulos

- **Problema**: Mistura rendering de cards, fetching de headlines, sparklines, cálculos YoY
- **Solução**:
  - `sections/painel/kpi-card.js` — Rendering e layout dos cards
  - `sections/painel/headline.js` — Lógica de headlines AI
  - `sections/painel/sparkline.js` — Mini-gráficos
  - `sections/painel/index.js` — Orquestrador
- **Benefício**: Componentes reutilizáveis e testáveis

#### 2.2 `analise.js` (1,180 linhas) → 3 módulos

- **Problema**: Painel de análise + rendering de gráficos + UI de interpretação
- **Solução**:
  - `sections/analise/panel.js` — Painel principal
  - `sections/analise/chart.js` — Gráficos ECharts
  - `sections/analise/interpretation.js` — UI de interpretação AI
  - `sections/analise/index.js` — Orquestrador

#### 2.3 `painel_analysis.py` (414 linhas) → 3 módulos

- **Problema**: Mistura orquestração AI, cache em disco, parsing de respostas
- **Solução**:
  - `services/analysis/engine.py` — Chamadas Claude API + prompts
  - `services/analysis/cache.py` — Cache em disco com TTL
  - `services/analysis/parser.py` — Extração de JSON de texto
  - `services/analysis/__init__.py` — Re-exports

#### 2.4 `ideology_lenses.py` (367 linhas) → Externalizar configuração

- **Problema**: Definições de lentes ideológicas hardcoded em Python
- **Solução**: Mover definições para `data/ideology_lenses.json`, manter apenas lógica de carregamento

### Prioridade 3 — Longo Prazo (1-2 semanas)

#### 3.1 Eliminar duplicação de normalização de períodos

- **Localizações**: `collectors/ine.py`, `static/js/sections/explorador.js`, `static/js/api.js`
- **Solução**: Criar módulo `services/formatters.py` partilhado + endpoint API para JS

#### 3.2 Extrair rendering de gráficos partilhado

- **Localizações**: `painel.js`, `analise.js`, `explorador.js`, `comparativos.js`
- **Solução**: Criar `js/lib/chart-renderer.js` com factory pattern

#### 3.3 `explorador.js` (667 linhas) → Componentes separados

- **Solução**: Separar catálogo search, multi-select, time picker, chart rendering

## Pontos Positivos da Arquitectura Actual

- Boa separação routes → services → database
- Caching inteligente (5 min browser, disco para AI)
- Collectors bem focados (1 por fonte de dados)
- Testes browser abrangentes (Playwright)
- Thread safety com DuckDB connections por thread
- FastAPI async handlers para operações não-bloqueantes

## Riscos a Considerar

- Modularização do frontend sem bundler (atualmente servido como ficheiros estáticos)
- O `catalog.py` → JSON requer actualizar todos os imports
- Separar CSS pode criar problemas de especificidade se não usar BEM ou CSS modules
- Refactoring do JS requer atenção ao scope de variáveis globais
