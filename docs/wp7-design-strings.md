# WP-7 Design Strings — Painel CAE Dashboard v8
# Criativo — 2026-03-01
# Para implementação pelo Coder (painel.py)

---

## 1. Ordem das Secções (definitiva)

| # | Label | Estado |
|---|-------|--------|
| 1 | Custo de Vida | existente |
| 2 | Indústria | ⭐ NOVA — secção headline |
| 3 | Emprego | existente |
| 4 | Conjuntura | existente |
| 5 | Energia | existente |
| 6 | Externo | existente |
| 7 | Competitividade | ⭐ NOVA |

**Nota**: Títulos limpos, sem emoji, sem subtítulo. "Indústria" é secção de destaque — colocar imediatamente após Custo de Vida.

---

## 2. Nova Secção: Indústria

### Context strings para KPI cards

```python
INDUSTRIA_CONTEXTS = {
    "ipi_seasonal_cae_TOT": "Barómetro geral da produção industrial nacional. Base 2021=100. Série dessazonalizada pelo INE.",
    "ipi_seasonal_cae_24":  "Metalurgia de Base (CAE 24) — Base para construção e indústria transformadora.",
    "ipi_seasonal_cae_25":  "Produtos Metálicos (CAE 25) — Estruturas, embalagens, ferramentas e componentes metálicos fabricados.",
    "ipi_seasonal_cae_28":  "Máquinas e Equipamentos (CAE 28) — Bens de capital para a indústria; indicador da capacidade de investimento produtivo.",
    "ipi_seasonal_cae_29":  "Veículos Automóveis (CAE 29) — Sector exportador-chave — Autoeuropa, Caetano Bus.",
    "copper_usd":           "Cobre — Barómetro da economia global — construção, electrónica, electrificação.",
    "aluminium_usd":        "Alumínio — Metal estrutural transversal: automóvel, embalagem, construção. Indicador de procura industrial.",
}
```

---

## 3. Nova Secção: Competitividade

### Context strings para KPI cards

```python
COMPETITIVIDADE_CONTEXTS = {
    "gdp_per_capita_eur": "Riqueza média por habitante. PT: ~23.500€ vs UE27: ~34.000€ — gap estrutural de convergência.",
    "rnd_pct_gdp":        "Intensidade de inovação. PT: 1,7% vs UE27: 2,3% (meta Horizonte Europa: 3%). Desvantagem competitiva a longo prazo.",
    "employment_rate":    "Taxa de emprego (% pop. 20-64 anos com emprego). Medida ampla do mercado de trabalho — complementa a taxa de desemprego.",
}
```

---

## 4. Adições a Secções Existentes

### Custo de Vida — novos KPIs

```python
CUSTO_DE_VIDA_ADDITIONS = {
    "gasoline_95_eur":  "Gasolina 95 no posto — par com o gasóleo para leitura completa dos combustíveis.",
    "euribor_3m":       "Euribor 3 meses — taxa de curto prazo; determinante das prestações de crédito habitação a taxa variável.",
}
```

### Energia — novo KPI

```python
ENERGIA_ADDITIONS = {
    "natural_gas_eur": "Gás Natural — Crítico para indústrias energo-intensivas — vidro, cerâmica, metalurgia.",
}
```

---

## 5. kpiPhrase() HEADLINE_BLACKLIST — adições

Os seguintes indicadores NÃO devem aparecer nas manchetes automáticas geradas por `kpiPhrase()`.
São indicadores estruturais/de longo prazo que não lêem bem como notícia conjuntural.

```python
HEADLINE_BLACKLIST_ADDITIONS = [
    "gdp_per_capita_eur",    # estrutural, não ciclico
    "rnd_pct_gdp",           # estrutural
    "employment_rate",       # muito próximo do desemprego já presente
    "ipi_seasonal_cae_TOT",  # verificar se já existe como 'production' — se sim, evitar duplicação
]
```

**Nota para Coder**: Verificar se `ipi_seasonal_cae_TOT` já está representado na blacklist como `production` ou similar antes de adicionar.

---

## 6. Notas de Implementação

- Todos os títulos de secção: sem emoji, sem subtítulo, capitalização normal (não ALL CAPS).
- "Indústria" é secção de destaque: se o layout suportar, dar-lhe maior destaque visual (header bold, ou separador visual antes dela).
- Os context strings são PT-PT, factuais, concisos (máx. 2 linhas visíveis num card).
- Separar visualmente as duas novas secções das existentes para facilitar leitura linear do dashboard.
