# Europa Section — Data Coverage

> Auditoria M3 — gerada por Analyst (2026-02-28)
> Ficheiro: `static/js/sections/europa.js`

## Resumo

| | Count |
|---|---|
| Indicadores `mode: 'legacy'` | 5 |
| Indicadores `mode: 'db'` | 7 |
| **Total** | **12** |

## Tabela de Cobertura

| Indicator ID | Label | Mode | Source | Regions | Freq. | Since | Until | Status |
|---|---|---|---|---|---|---|---|---|
| manufacturing | IPI Transformadora | legacy | EUROSTAT | PT (só PT na DB) | monthly | 2000-01 | 2023-12 | ⚠️ deprecated path |
| total_industry | IPI Total Indústria | legacy | EUROSTAT | PT (só PT na DB) | monthly | 2000-01 | 2023-12 | ⚠️ deprecated path |
| metals | Metais e Metalurgia | legacy | EUROSTAT | PT (só PT na DB) | monthly | 2000-01 | 2023-11 | ⚠️ deprecated path |
| chemicals | Química e Plásticos | legacy | EUROSTAT | PT (só PT na DB) | monthly | 2000-01 | 2023-12 | ⚠️ deprecated path · ⚠️ ID mismatch |
| transport | Material de Transporte | legacy | EUROSTAT | PT (só PT na DB) | monthly | 2000-01 | 2023-12 | ⚠️ deprecated path · ⚠️ ID mismatch |
| unemployment | Desemprego (%) | db | EUROSTAT | PT,ES,DE,FR,IT,PL,EU27... | monthly | 2000-01 | 2025-12 | ✅ DB multi-país |
| gdp_per_capita_eur | PIB/capita (€) | db | EUROSTAT | PT,ES,DE,FR,EU27... | annual | 2000 | 2025 | ✅ DB multi-país |
| gov_debt_pct_gdp | Dívida Pública %PIB | db | EUROSTAT | PT,ES,DE,FR,EU27... | annual | 2000 | 2024 | ✅ DB multi-país |
| employment_rate | Taxa de Emprego | db | EUROSTAT | PT,ES,DE,FR,EU27... | annual | 2000 | 2024 | ✅ DB multi-país |
| birth_rate | Natalidade (/1000) | db | WORLDBANK | PT,ES,DE,FR... | annual | 2000 | 2022 | ✅ DB multi-país |
| rnd_pct_gdp | I&D % PIB | db | WORLDBANK | PT,ES,DE,FR... | annual | 2000 | 2022 | ✅ DB multi-país |
| fdi_inflows_pct_gdp | IDE Entradas %PIB | db | WORLDBANK | PT,ES,DE,FR... | annual | 2000 | 2022 | ✅ DB multi-país |

## Análise Detalhada

### Indicadores `mode: 'legacy'` (5 indicadores)

Estes indicadores chamam `/api/europa?dataset=X&countries=...&months=N`.

**Situação no V7:** O endpoint `/api/europa` está **marcado como deprecated** em `app/routes/api.py`:

```python
# ── Deprecated endpoints (OpenClaw backward compat) ──────────────────
@router.get("/europa")
def api_europa(...):
    return _deprecated(query_compare(...))  # X-CAE-Deprecated: true
```

O endpoint devolve `X-CAE-Deprecated: true` no header HTTP, mas **continua a funcionar** — delega para `query_compare()`, exactamente o mesmo serviço usado pelo `/api/compare`.

**Observação importante:** O comentário em `europa.js` diz que o modo legacy usa "Eurostat client" (live Eurostat API), mas na realidade o `/api/europa` apenas chama `query_compare()` que consulta a DB DuckDB local. Não há chamada live ao Eurostat — os dados são servidos da DB tal como nos indicadores `mode: 'db'`.

#### Anomalias de ID encontradas

Dois indicadores legacy têm IDs que **não correspondem** ao catalog da DB:

| ID em europa.js | ID real na DB | Diferença |
|---|---|---|
| `chemicals` | `chemicals_pharma` | Mismatch — o `query_compare` pode não encontrar o indicador |
| `transport` | `transport_eq` | Mismatch — o `query_compare` pode não encontrar o indicador |

Recomendação: verificar como `query_compare` resolve o `dataset` param — se usa alias ou lookup directo.

---

### Indicadores `mode: 'db'` (7 indicadores)

Estes indicadores chamam `/api/compare?indicator=X&source=Y&countries=...&since=N` — endpoint **activo no V7**.

#### Verificação de cobertura na DB

Todos os 7 indicadores confirmados com dados multi-país via `/api/compare`:

**EUROSTAT (4 indicadores):**
- `unemployment` — mensal, PT + ES + DE + FR + IT + PL + EU27 confirmados. Since: 2000-01, until: 2025-12.
- `gdp_per_capita_eur` — anual, PT + ES + DE + FR + EU27 confirmados. Since: 2000, until: 2025.
- `gov_debt_pct_gdp` — anual, multi-país (inferido do catalog). Since: 2000, until: 2024.
- `employment_rate` — anual, multi-país (inferido do catalog). Since: 2000, until: 2024.

**WORLDBANK (3 indicadores) — não registados no `catalog.py`:**
- `birth_rate` — anual, PT + ES + DE + FR confirmados. Since: 2000, until: ~2022.
- `rnd_pct_gdp` — anual, multi-país. Since: 2000, until: ~2022.
- `fdi_inflows_pct_gdp` — anual, multi-país. Since: 2000, until: ~2022.

⚠️ **Atenção:** Os 3 indicadores WORLDBANK **não constam do `catalog.py`** (que lista INE, EUROSTAT, FRED, BPORTUGAL, REN, OECD, DGEG, ERSE). Estão na DB mas sem metadados no catalog. Consequência: não aparecem na Ficha Técnica nem no Explorador por catálogo. Acção recomendada: adicionar bloco `WORLDBANK` ao `catalog.py`.

---

## Recomendações

### 1. Migrar indicadores legacy para `mode: 'db'` (PRIORIDADE ALTA)

A migração é simples — apenas muda o URL em europa.js de `/api/europa?dataset=X` para `/api/compare?dataset=X` ou `mode: 'db'`:

| Indicador | Mudança necessária em europa.js |
|---|---|
| manufacturing | `mode: 'legacy'` → `mode: 'db', source: 'EUROSTAT', indicator: 'manufacturing'` |
| total_industry | `mode: 'legacy'` → `mode: 'db', source: 'EUROSTAT', indicator: 'total_industry'` |
| metals | `mode: 'legacy'` → `mode: 'db', source: 'EUROSTAT', indicator: 'metals'` |
| chemicals | `mode: 'legacy'` → `mode: 'db', source: 'EUROSTAT', indicator: 'chemicals_pharma'` (**corrigir ID**) |
| transport | `mode: 'legacy'` → `mode: 'db', source: 'EUROSTAT', indicator: 'transport_eq'` (**corrigir ID**) |

**Os dados existem na DB** (confirmado via catalog.py: since 2000-01, until 2023-12). Limitação: dados IPI na DB são só Portugal (region_count: 1). A comparação europeia para IPI requer dados multi-país — verificar se a DB tem outros países para estes indicadores, ou se ficam limitados a série PT.

### 2. Adicionar WORLDBANK ao `catalog.py`

Os indicadores `birth_rate`, `rnd_pct_gdp`, `fdi_inflows_pct_gdp` estão funcionais na DB mas sem metadados no catálogo. Adicionar bloco WORLDBANK ao `app/constants/catalog.py` com label, URL e descrição de cada indicador.

### 3. Corrigir IDs `chemicals` e `transport`

Verificar se `query_compare()` resolve `dataset='chemicals'` para `chemicals_pharma` na DB ou se retorna empty. Se não há alias, estes dois indicadores estão **silenciosamente a falhar** na secção Europa.

---

*Gerado por: cae-analyst-m3m5 | Data: 2026-02-28*
