# Chart Validation Issues — 2026-03-16

## Summary
- **352/372 OK** (94.6%), 4 WARN, 16 FAIL
- Screenshots: `docs/testing/screenshots/`
- Report: `docs/testing/chart-validation-report.json`

## A) Indicadores sem dados (0 pts) — REMOVER do catálogo
- `EUROSTAT/construction_index` — 0 pts, série nunca populada
- `FRED/gold_price` — 0 pts, série nunca populada

## B) Dados fora do período de 5 anos — séries históricas paradas
Precisam de período alargado ou substituição futura.

| Indicador | Último ponto | Total pts | Acção |
|-----------|-------------|-----------|-------|
| EUROSTAT/price_level_index | 2020 | 26 | Série anual, parou |
| DGEG/price_gasoline_98_pvp | 2009-12 | 72 | Série mensal, descontinuada |
| ERSE/tariff_at_peak | 2020-04 | 8 | Série semianual, parou |
| ERSE/btn_simple_le6_9kva | 2020-04 | 9 | idem |
| ERSE/btn_simple_gt6_9kva | 2020-04 | 9 | idem |
| ERSE/tariff_at_off_peak | 2020-04 | 8 | idem |
| ERSE/tariff_at_shoulder | 2020-04 | 8 | idem |
| ERSE/tariff_at_super_off_peak | 2020-04 | 8 | idem |
| WORLDBANK/gov_debt_pct_gdp_wb | 1994 | 2 | Praticamente sem dados |
| WORLDBANK/literacy_rate | 2011 | 3 | idem |

## C) Poucos pontos no período de 5 anos (1-4 pts) — rendering esparso
Séries anuais/semianuais com cobertura recente limitada.

| Indicador | Pts (5yr) | Total pts | Frequência |
|-----------|-----------|-----------|------------|
| DGEG/energy_intensity_final | 2 | 29 | Anual |
| DGEG/capacity_hydro_10_30mw | 4 | 13 | Anual |
| DGEG/capacity_hydro_pumped | 4 | 12 | Anual |
| DGEG/capacity_geothermal | 4 | 13 | Anual |
| WORLDBANK/rnd_pct_gdp | 1 | 27 | Anual |
| EUROSTAT/earn_ses_pub2s | 1 | 5 | ~4 anos |
| DGEG/natgas_price_domestic_81.48 | 1 | 11 | Semianual |
| DGEG/natgas_price_industry_27.64 | 1 | 11 | Semianual |

## D) Bug: multi-series com frequências mistas
Quando PIB (trimestral) + Desemprego (mensal) são seleccionados juntos, a série trimestral não renderiza.
Causa: `connectNulls: false` com nulls nos meses sem dados trimestrais → pontos isolados invisíveis.

## TODO (próxima ronda de data collection)
- Procurar substitutos para EUROSTAT/construction_index e FRED/gold_price
- Actualizar séries ERSE (tarifas pararam em 2020)
- Actualizar EUROSTAT/price_level_index
- Avaliar se WORLDBANK/gov_debt_pct_gdp_wb e literacy_rate devem ser removidos (dados pré-2011)
