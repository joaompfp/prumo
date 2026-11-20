# Multiseries two-scale curation - Portugal

Read-only curation. No chart, CMS, source, registry, roadmap or production change was made.
Snapshot: 2026-11-20T20:41Z. The live database can advance after this snapshot; re-run the
evidence command before publication.

## Verdict

Four configurations are data-valid candidates for the multiseries renderer from eligible
production data. Each has exactly two raw scale groups, shares one native frequency inside
the configuration, and has at least three sides. This report does not test the renderer or
the CMS; it establishes the series, scales and coverage only.

| # | Configuration | Freq | Sides | Left group | Right group | Common period | Latest common |
|---|---|---|---|---|---|---|---|
| 1 | Taxas de juro, crédito à habitação e depósitos | M | 4 | `%` | `MEUR` | 1994-01..2026-09, 393 months | 2026-09 |
| 2 | Dívida pública, saldo orçamental e PIB per capita | A | 3 | `% GDP` | `EUR per capita` | 1995..2025, 31 years | 2025 |
| 3 | Comércio externo e PIB per capita | A | 3 | `% PIB` | `EUR per capita` | 1995..2025, 31 years | 2025 |
| 4 | Produtividade e custos do trabalho | A | 3 | `I10_2010` | `index 2020=100` | 2000..2025, 26 years | 2025 |

There are 13 memberships and 12 distinct series. All are active primary series, their
publishers have `redistribution_ok=1`, and every value read is a served
`kind='fetched'` observation. No derived series, legacy-unverified row, interpolation,
resampling or new source is used.

Two raw-token traps matter for the implementation:

- `% GDP` and `% PIB` both render as `% do PIB` but are different stored tokens. They are
  kept in separate configurations. Do not merge them into one compatible group without a
  reviewed transformation.
- `I10_2010` and `index 2020=100` carry their base year in the unit token, while
  `base_year` is null for both. They are different base-year groups. Do not treat the null
  column as evidence of a shared base.

## Method and eligibility

- Registry: `ingest.registry.load_registry(Path("registry/core.yaml"))` loaded 1,791
  validated `SeriesSpec` objects.
- Database: `/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3` on `f0nix`, opened
  through Python `sqlite3` with `file:...?mode=ro`, URI true. File mtime was
  2026-11-20 11:24:40 UTC, size 258,834,432 bytes.
- Every candidate was read with one indexed per-series query:
  `SELECT period, value_text FROM served_observation WHERE series_id = ? AND kind = 'fetched' ORDER BY period`.
  No global serving-view join was run.
- Eligibility was checked per series with its metadata row: `series.active=1`,
  `series.role='primary'`, `source.redistribution_ok=1`, and the serving view's verified-run
  gate. `kind='fetched'` excludes legacy-unverified rows.
- Titles below come from `presentation.series_title("pt", family_of(indicator_key), geography)`,
  not from a hand-written label.
- Coverage uses the actual finite-value intersection on every side, not only common period
  keys. Every value in all four intersections is finite; no additional period was excluded
  for a blank, non-numeric or non-finite token.

## 1. Taxas de juro, crédito à habitação e depósitos

Suggested slug: `taxas-juro-credito-depositos`

### Copy PT-PT

Title: `Taxas de juro, crédito à habitação e depósitos`

Intro: `Taxas de juro de referência e saldos de crédito e depósitos das famílias em Portugal. As taxas estão em percentagem; os saldos, em milhões de euros.`

Caveat: `A Euribor é uma taxa de referência da área do euro (composição variável), não uma taxa portuguesa; a taxa a 10 anos é a rendibilidade de obrigações do Tesouro português. O crédito e os depósitos são saldos em fim de mês, não fluxos. A evolução conjunta não estabelece causalidade.`

### Scale signature

- Left: `unit="%"`, `multiplier=null`, `base_year=null`.
- Right: `unit="MEUR"`, `multiplier=null`, `base_year=null`.
- Frequency: `M` on every member.

Sources: Banco de Portugal (BPstat) series 13168437, 12099464, 12557378 and 12556700.

### Membership

| Side | Exact ID | Actual title | Native concept | First finite | Latest finite | n |
|---|---|---|---|---|---|---|
| Left | `bportugal.euribor_12m.EA` | Taxa Euribor a 12 meses - Área do euro | Euribor a 12 meses (1 ano), média mensal, área do euro (composição variável) | 1994-01 | 2026-10 | 394 |
| Left | `bportugal.pt_10y.PT` | Taxa de juro da dívida pública a 10 anos - Portugal | Rendibilidade de obrigações do Tesouro com taxa fixa e maturidade residual de 10 anos, média mensal | 1993-07 | 2026-10 | 400 |
| Right | `bportugal.credit_housing.PT` | Crédito à habitação - Portugal | Empréstimos à habitação dos bancos aos particulares, saldo em fim de mês, milhões de euros (OMFI, não consolidado) | 1979-12 | 2026-09 | 562 |
| Right | `bportugal.deposits_households.PT` | Depósitos das famílias - Portugal | Depósitos dos particulares nos bancos, saldo em fim de mês, milhões de euros (OMFI, não consolidado) | 1979-12 | 2026-09 | 562 |

Coverage: union 1979-12..2026-10, 563 months, no missing month in the union; intersection
1994-01..2026-09, 393 months. The earlier stock history is not drawn because both rates
start later. The latest common period is 2026-09 because the stocks end there; both rates
already have 2026-10.

Spot check at 2026-09, exact stored tokens: Euribor 12m `3.2470`; 10-year yield `3.85`;
housing credit `120179.0`; household deposits `203204.0`. In 2026-10 the rates are
`3.2386` and `3.92`; the stock side has no 2026-10 value.

## 2. Dívida pública, saldo orçamental e PIB per capita

Suggested slug: `divida-saldo-pib-per-capita`

### Copy PT-PT

Title: `Dívida pública, saldo orçamental e PIB per capita`

Intro: `O peso da dívida pública bruta e do saldo orçamental no PIB e o PIB per capita de Portugal, em valores anuais.`

Caveat: `A dívida é um stock bruto e o saldo orçamental é um fluxo anual; ambos são rácios do PIB. No saldo, valores positivos indicam capacidade líquida de financiamento e valores negativos indicam défice. O PIB per capita é uma média por habitante, não o rendimento disponível das famílias. A comparação não estabelece causalidade.`

### Scale signature

- Left: `unit="% GDP"`, `multiplier=null`, `base_year=null`.
- Right: `unit="EUR per capita"`, `multiplier=null`, `base_year=null`.
- Frequency: `A` on every member.

Sources: Eurostat gov_10dd_edpt1 (GD, B9) and nama_10_pc (B1GQ).

### Membership

| Side | Exact ID | Actual title | Native concept | First finite | Latest finite | n |
|---|---|---|---|---|---|---|
| Left | `eurostat.gov_debt_pct_gdp.PT` | Dívida pública - Portugal | Dívida bruta das administrações públicas (S13), percentagem do PIB (gov_10dd_edpt1, GD, PC_GDP) | 1995 | 2025 | 31 |
| Left | `eurostat.gov_deficit_pct_gdp.PT` | Défice público - Portugal | Capacidade/necessidade líquida de financiamento das administrações públicas (S13), percentagem do PIB (B9, PC_GDP) | 1995 | 2025 | 31 |
| Right | `eurostat.gdp_per_capita_eur.PT` | PIB per capita - Portugal | PIB a preços correntes de mercado por habitante (nama_10_pc, B1GQ, CP_EUR_HAB) | 1995 | 2025 | 31 |

Coverage: union and intersection are both 1995..2025, 31 years. The panel is rectangular:
every member has a finite value in every year. Latest common is 2025.

Spot check at 2025, exact stored tokens: debt `89.2`; net lending/borrowing `0.7`;
GDP per capita `28560`. The `0.7` is positive, so the series titled `Défice público` is in
capacity territory in that year; the copy explains the sign instead of calling it a deficit.

## 3. Comércio externo e PIB per capita

Suggested slug: `comercio-externo-pib-per-capita`

### Copy PT-PT

Title: `Comércio externo e PIB per capita`

Intro: `Exportações e importações de bens e serviços em percentagem do PIB e PIB per capita de Portugal.`

Caveat: `As exportações e importações são fluxos brutos de bens e serviços, não valor acrescentado; ambos usam o PIB como denominador. O PIB per capita é uma média por habitante. A comparação não estabelece causalidade.`

### Scale signature

- Left: `unit="% PIB"`, `multiplier=null`, `base_year=null`.
- Right: `unit="EUR per capita"`, `multiplier=null`, `base_year=null`.
- Frequency: `A` on every member.

Sources: World Bank WDI NE.EXP.GNFS.ZS and NE.IMP.GNFS.ZS; Eurostat nama_10_pc.

### Membership

| Side | Exact ID | Actual title | Native concept | First finite | Latest finite | n |
|---|---|---|---|---|---|---|
| Left | `worldbank.exports_pct_gdp.PT` | Exportações - Portugal | Exportações de bens e serviços, percentagem do PIB (NE.EXP.GNFS.ZS, PRT) | 1970 | 2025 | 56 |
| Left | `worldbank.imports_pct_gdp.PT` | Importações - Portugal | Importações de bens e serviços, percentagem do PIB (NE.IMP.GNFS.ZS, PRT) | 1970 | 2025 | 56 |
| Right | `eurostat.gdp_per_capita_eur.PT` | PIB per capita - Portugal | PIB a preços correntes de mercado por habitante (nama_10_pc, B1GQ, CP_EUR_HAB) | 1995 | 2025 | 31 |

Coverage: union 1970..2025, 56 years, no gap; intersection 1995..2025, 31 years, because
the Eurostat GDP per capita series starts in 1995. The trade ratios have a longer history
but are not drawn before 1995. Latest common is 2025.

Spot check at 2025, exact stored tokens: exports `43.6580888492067`; imports
`42.7407881300597`; GDP per capita `28560`. The long trade tokens are the stored World Bank
precision, not a display choice.

## 4. Produtividade e custos do trabalho

Suggested slug: `produtividade-custos-trabalho`

### Copy PT-PT

Title: `Produtividade e custos do trabalho`

Intro: `Produtividade real por hora, custo unitário do trabalho por hora e índice de custo do trabalho por hora em Portugal. Os dois primeiros usam 2010=100; o terceiro usa 2020=100.`

Caveat: `A produtividade real e o custo unitário do trabalho usam 2010=100; o índice de custo do trabalho por hora usa 2020=100. Os níveis não são comparáveis entre eixos, apenas a variação. A produtividade é real e os custos são nominais. A comparação não estabelece causalidade.`

### Scale signature

- Left: `unit="I10_2010"`, `multiplier=null`, `base_year=null`; the base is encoded in the unit token.
- Right: `unit="index 2020=100"`, `multiplier=null`, `base_year=null`; the base is encoded in the unit token.
- Frequency: `A` on every member.

Sources: Eurostat nama_10_lp_ulc (RLPR_HW, NULC_HW) and lc_lci_r2_a (I20).

### Membership

| Side | Exact ID | Actual title | Native concept | First finite | Latest finite | n |
|---|---|---|---|---|---|---|
| Left | `eurostat.labour_productivity_hour_real.PT` | Produtividade real por hora trabalhada - Portugal | Produtividade real do trabalho por hora trabalhada, índice 2010=100 (nama_10_lp_ulc, RLPR_HW) | 1995 | 2025 | 31 |
| Left | `eurostat.unit_labour_cost_hour.PT` | Custo unitário do trabalho por hora - Portugal | Custo unitário do trabalho por hora trabalhada, índice 2010=100 (nama_10_lp_ulc, NULC_HW) | 1995 | 2025 | 31 |
| Right | `eurostat.hourly_labour_cost_index.PT` | Índice de custo do trabalho por hora - Portugal | Índice de custo do trabalho por hora, 2020=100, NACE B-N (lc_lci_r2_a, I20) | 2000 | 2025 | 26 |

Coverage: union 1995..2025, 31 years, no gap; intersection 2000..2025, 26 years, because the
labour cost index starts in 2000. Latest common is 2025.

Spot check at 2025, exact stored tokens: productivity `106.436`; unit labour cost
`141.801`; hourly labour cost index `128.7`. The first two are on one axis because they share
`I10_2010`; the third is deliberately on the other axis because its base is `2020=100`.

## Considered and not selected

### Five-series household conditions panel

`bportugal.euribor_12m.EA`, `ine.hicp_yoy.PT`, `ine.unemployment_monthly.PT` on the left
(`%`) and `bportugal.credit_housing.PT`, `bportugal.deposits_households.PT` on the right
(`MEUR`) is drawable: intersection 1998-02..2026-09, 344 months, all finite. It was not
selected as a primary comparison because the left axis mixes an interest-rate level, a
year-on-year price change and a labour-force share. They share `%` but not one statistical
meaning. If the section wants a household-conditions dashboard, use it only with an explicit
caveat such as: `As três séries em percentagem medem coisas diferentes: a Euribor é uma taxa de juro, o IHPC é uma variação homóloga e a taxa de desemprego é uma percentagem da força de trabalho. A escala comum serve para leitura de direções, não para somar ou comparar grandezas.`

### Active population counts against unemployment

No active-population count series is present in the eligible Portuguese registry. The
Portuguese `N.º` series are resident population, live births and deaths; the World Bank
labour series are unemployment and employment rates, not labour-force levels. A comparison
of active population counts with an unemployment rate would require a new source or a
declared transformation. It is not proposed here.

### HICP year-on-year and IPC year-on-year

`ine.hicp_yoy.PT` and `ine.ipc_yoy.PT` are both monthly Portuguese percentages with long
overlap, but they are alternative inflation measures rather than two complementary
dimensions. They are near-duplicates for a curated comparison and were not selected.

### Monthly trade values against the industrial production index

`ine.exports_monthly.PT` and `ine.imports_monthly.PT` (`EUR`, 1993-01..2026-09) against
`ine.ipi_seasonal_cae_TOT.PT` (`index_2021=100`, 2005-01..2026-09) would form two groups and
261 common months. The trade values are nominal and not seasonally adjusted; the production
index is seasonally and calendar adjusted. The mixed adjustment and strong monthly
seasonality make this a lower-quality public comparison despite being technically drawable.

### Population in the births and deaths panel

`ine.population.PT` shares `N.º` with `ine.live_births.PT` and `ine.deaths.PT`, but its
values are around 11 million against roughly 80,000 to 125,000 for the flows. A shared count
axis would flatten the births and deaths lines. The population series is therefore excluded
from a count panel. A demographic panel could use birth and death rates if one is wanted, but
that changes the concept and was not part of this selection.

## Evidence command

The following reproduces the metadata, finite coverage and intersection used above. It is a
small per-series inventory, not a global serving-view join. It only reads.

```bash
ssh -o BatchMode=yes f0nix "python3 - <<'PY'
import math, sqlite3

DB = 'file:/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3?mode=ro'
CONFIGS = {
    '1': ['bportugal.euribor_12m.EA', 'bportugal.pt_10y.PT',
          'bportugal.credit_housing.PT', 'bportugal.deposits_households.PT'],
    '2': ['eurostat.gov_debt_pct_gdp.PT', 'eurostat.gov_deficit_pct_gdp.PT',
          'eurostat.gdp_per_capita_eur.PT'],
    '3': ['worldbank.exports_pct_gdp.PT', 'worldbank.imports_pct_gdp.PT',
          'eurostat.gdp_per_capita_eur.PT'],
    '4': ['eurostat.labour_productivity_hour_real.PT',
          'eurostat.unit_labour_cost_hour.PT',
          'eurostat.hourly_labour_cost_index.PT'],
}

c = sqlite3.connect(DB, uri=True)
for name, ids in CONFIGS.items():
    sets = {}
    for sid in ids:
        meta = c.execute(
            'SELECT s.unit, s.multiplier, s.base_year, s.frequency, s.active, '
            'p.redistribution_ok FROM series s JOIN source p ON p.id = s.source_id '
            'WHERE s.id = ?', (sid,)).fetchone()
        rows = c.execute(
            \"SELECT period, value_text FROM served_observation \"
            \"WHERE series_id = ? AND kind = 'fetched' ORDER BY period\", (sid,)).fetchall()
        finite = [(p, v) for p, v in rows
                  if v is not None and v.strip() and math.isfinite(float(v))]
        sets[sid] = {p for p, _ in finite}
        print(name, sid, meta, len(finite), finite[0], finite[-1])
    inter = sorted(set.intersection(*sets.values()))
    print(name, 'intersection', len(inter), inter[0], inter[-1])
PY"
```

Registry and title checks used in the repository checkout:

```bash
cd /home/joao/projects/prumo-pipeline
.venv-ci/bin/python -c 'from pathlib import Path; from ingest.registry import load_registry; print(len(load_registry(Path("registry/core.yaml"))))'
.venv-ci/bin/python -c 'from presentation import family_of, series_title; print(series_title("pt", family_of("euribor_12m.EA.M"), "EA"))'
```

## Residual risks

- This is a live production snapshot, not a frozen copy. A later run can move the latest
  common period or revise a value. Recompute before publishing.
- The Euribor series is `Euro Area - Changing composition`, not a fixed euro-area aggregate.
  The copy says `área do euro (composição variável)` and must not be shortened to `Portugal`.
- BPstat credit and deposit series are non-consolidated OMFI balance-sheet stocks at
  end-of-month. They are not household survey data, loan approvals or monthly flows.
- The Eurostat deficit series is net lending/borrowing. A positive value is not a deficit;
  the copy explains the sign convention.
- World Bank trade ratios are compiled estimates, and Eurostat GDP per capita is at current
  prices. They are used as published, without deflation or purchasing-power adjustment.
- `% GDP` and `% PIB` render identically but are distinct raw tokens; `I10_2010` and
  `index 2020=100` carry different bases in the unit token while `base_year` is null. Both
  distinctions must survive the compatibility check.
- No causal reading is offered in any title, intro or caveat. The comparisons show joint
  movement and different dimensions, not mechanisms.
