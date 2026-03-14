# CAE v10 Sprint Plan — Data Quality + Novos Dados
> Baseado em: /api/quality (95 errors, 269 warnings, 403 total) + Einstein editorial review
> Data: 2026-03-01

---

## Diagnóstico Executivo

O endpoint `/api/quality` revela 3 classes de problemas:

### 1. Séries Congeladas (freshness errors — CRÍTICO)
Collectors pararam ou têm bug — dados antigos a ser apresentados:
| Source | Indicador | Último dado | Atraso |
|--------|-----------|-------------|--------|
| EUROSTAT | ipi, manufacturing, total_industry, etc. | 2023-12 | **22 meses** |
| EUROSTAT | transport_eq | 2022-10 | **36 meses** |
| EUROSTAT | ipi_food_beverage | 2016-12 | **107 meses** |
| INE | exports_monthly, imports_monthly | 2024-12 | **11 meses** |
| DGEG | energy_dependence, renewable_share, co2 | 2023 | **11 meses** |
| ERSE | tariff_mt_* | 2021-10 | **37 meses** |
| WORLDBANK | literacy_rate | 2011 | **155 meses** |

### 2. Catalog Drift (row counts errados — catálogo desatualizado)
O catálogo declara X países mas a DB só tem PT. Exemplos:
- EUROSTAT gdp_quarterly: espera 2907 rows, tem 103 (só PT)
- EUROSTAT labour_productivity: espera 881, tem 30 (só PT)
- WORLDBANK gdp_usd: espera 65 países, tem 25

### 3. Orphan Indicators (na DB sem catalog — aparecem com código bruto na Ficha)
- ~100 indicadores DGEG sem entrada no catalog.py
- 15 commodities FRED (cotton, nickel, soybean, steel, zinc, sugar) sem catalog
- 20+ tarifas ERSE de acesso (access_mt_*, access_at_*, etc.) sem catalog

---

## Sprint v10 — Work Packages

### 🔴 Prioridade Alta (Scouts + Coder)

#### WP-D1: Reparar collectors EUROSTAT congelados
**Agente:** Coder
**Ficheiros:** `scripts/cae-collect` ou collector scripts EUROSTAT
**Tarefas:**
- Executar colecta manual para: `ipi`, `manufacturing`, `total_industry`, `metals`, `chemicals_pharma`, `machinery`, `transport_eq`, `rubber_plastics`, `construction_output`
- Verificar por que razão pararam em 2023-12 (mudança de dataset ID? autenticação?)
- Actualizar para 2025-12 (lag esperado 3m)
**Critério de sucesso:** `/api/quality` freshness errors EUROSTAT IPI desaparecem

#### WP-D2: Reparar collector INE exports/imports
**Agente:** Coder
**Tarefas:**
- `exports_monthly` e `imports_monthly` presos em 2024-12
- Verificar endpoint INE e actualizar para 2025-11 (lag 2m)
**Critério:** freshness errors INE exports desaparecem

#### WP-D3: Reparar collectors WORLDBANK multi-país
**Agente:** Coder
**Problema:** A DB tem só 25 linhas (PT only) quando devia ter 65 (multi-country)
**Tarefas:**
- Verificar script `collect_worldbank_global.py` — porque não está a correr?
- Executar colecta para todos os países nos indicadores principais: gdp_usd, gdp_growth, unemployment_wb, employment_rate, population, internet_users_pct
- Isto é pré-requisito para Comparativos funcionarem bem no PT vs Mundo

---

### 🟡 Prioridade Média

#### WP-D4: Adicionar commodities FRED ao catálogo
**Agente:** Coder (simples — só catalog.py)
**Indicadores na DB sem catalog:** cotton, nickel, soybean, steel, zinc, sugar, gold_price, iron_ore, commodity_*
**Tarefas:** Adicionar entradas ao `catalog.py` com labels PT-PT e descrições
**Valor editorial:** Permite visualizar no Explorador e embeddar em artigos sobre matérias-primas

#### WP-D5: Atualizar metadados catalog.py (catalog drift INFO)
**Agente:** Coder
**Tarefas:** Corrigir `rows`/`since`/`until` para indicadores com +/- pequenos desvios:
- BPORTUGAL euribor_*: +11 rows — update catalog
- REN indicators: -35 rows — update catalog  
- FRED natural_gas: -36 rows — update catalog
- INE hicp_yoy: -35 rows — update catalog

#### WP-D6: Adicionar tarifas ERSE de acesso ao catálogo
**Agente:** Coder
**Indicadores orphan de interesse:** `access_mt_peak`, `access_at_peak`, `access_mat_peak`, `access_bte_*`, `access_btn_*`
**Estes existem na DB com dados 2013-2026 mas sem descrição** — estão acessíveis na Ficha como "código bruto"
**Tarefas:** Adicionar entradas ao catalog.py com labels PT-PT (ex: "Tarifa de Acesso MT — Ponta")

---

### 🟢 Prioridade Nova Cobertura (Einstein editorial)

#### WP-N1: Habitação — novo domínio
**Agente:** Scout + Coder
**Gap identificado pelo Einstein como CRÍTICO (15% do PIB PT)**
**Dados a colectar:**
- INE: IPH (Índice de Preços da Habitação) — `https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0009264`
- INE: Licenças de construção
- INE: Número de transações imobiliárias
**Scout:** verifica disponibilidade e formato das séries
**Coder:** script collector + inserção DB + catalog.py

#### WP-N2: Turismo — novo domínio
**Agente:** Scout + Coder
**Turismo = 15% do PIB PT, completamente ausente**
**Dados:**
- INE: Hóspedes e dormidas (mensal)
- INE: Proveitos totais de alojamento
- Banco de Portugal: Receitas turísticas (balança de pagamentos)
**Scout:** verifica endpoints INE turismo
**Coder:** collector + DB + catalog

#### WP-N3: Exposição de indicadores já na DB mas não no Painel
**Agente:** Coder (rápido — só painel.py)
**O Einstein identificou dados ricos já presentes, só não expostos:**
- Dívida pública % PIB (EUROSTAT/gov_debt_pct_gdp) — faltou no Painel de Finanças Públicas
- Défice % PIB (EUROSTAT/gov_deficit_pct_gdp)
- Balança corrente % PIB (EUROSTAT/current_account_pct_gdp)
- Exportações % PIB (WORLDBANK/exports_pct_gdp)
- Gini (WORLDBANK/gini) — só 21 rows PT atualmente, pouco útil
**Acção:** Adicionar nova secção "Finanças Públicas" ou "Externo" ao Painel com estes KPIs

---

## Plano de Execução Recomendado

### Fase 1 (urgente — 1 sprint, ~4h):
```
Scout:  Verificar endpoints INE habitação + turismo
Coder A: WP-D1 (EUROSTAT freshness) + WP-D2 (INE exports)
Coder B: WP-D3 (WORLDBANK multi-país) + WP-D5 (catalog metadata)
```

### Fase 2 (após dados chegarem):
```
Coder: WP-D4 (FRED catalog) + WP-D6 (ERSE access catalog) + WP-N3 (novo Painel)
Coder: WP-N1 (habitação collector + DB) + WP-N2 (turismo collector + DB)
```

### Fase 3 (polish):
```
Einstein: nova auditoria após Fase 1+2
Coder: ajustes de UX com novos dados
```

---

## Notas para o Sprint Briefing

1. **`cae-collect` vs scripts individuais:** verificar se há um script central de orquestração — todos os collectors devem passar por ele
2. **SQLite vs DuckDB:** inserções devem ir para AMBAS as DBs (já foi problema antes)
3. **Após cada batch de inserções:** rebuild com `ssh f3nix dc-jarbas-up cae-dashboard` e verificar `/api/quality` novamente
4. **Catalog.py é fonte de verdade** para labels PT-PT e descrições — qualquer novo indicador precisa entrada aqui primeiro
