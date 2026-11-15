"""Portuguese reader text. Titles are keyed by derived series key."""

FORMULAS = {
    "period_change": "Variação face ao período anterior (diferença), calculada pelo Prumo "
                     "a partir de {base}",
    "period_change_pct": "Variação face ao período anterior (%), calculada pelo Prumo "
                         "a partir de {base}",
    "yoy_change": "Variação homóloga (diferença), calculada pelo Prumo a partir de {base}",
    "yoy_change_pct": "Variação homóloga (%), calculada pelo Prumo a partir de {base}",
    "rebase_100": "Índice rebaseado ({base_period} = 100), calculado pelo Prumo "
                  "a partir de {base}",
}

UNITS = {
    "pct": "%",
    "pp": "p.p.",
    "balance": "saldo",
    "index_2015_100": "índice 2015=100",
}

CAVEATS = {
    "sa_base": "Calculado pelo Prumo sobre a série ajustada de sazonalidade; "
               "não é a taxa oficial do editor.",
    "stock_base": "Calculado pelo Prumo sobre montantes em saldo (stocks); "
                  "não é a taxa oficial do editor.",
}

ATTRIBUTION_SUFFIX = "Calculado pelo Prumo"

TITLES = {
    "derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct": (
        'Índice de produção industrial, total — variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_TOT.PT.period_change_pct": (
        'Índice de produção industrial, total — variação face ao período anterior (%)'
    ),
    "derived.ipi_seasonal_cae_B.PT.yoy_change_pct": (
        'Índice de produção industrial, indústrias extrativas — variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_C.PT.yoy_change_pct": (
        'Índice de produção industrial, indústrias transformadoras — variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_D.PT.yoy_change_pct": (
        'Índice de produção industrial, eletricidade, gás e vapor — variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_E.PT.yoy_change_pct": (
        'Índice de produção industrial, água, saneamento e resíduos — variação homóloga (%)'
    ),
    "derived.exports_monthly.PT.yoy_change_pct": (
        'Exportações de bens — variação homóloga (%)'
    ),
    "derived.imports_monthly.PT.yoy_change_pct": (
        'Importações de bens — variação homóloga (%)'
    ),
    "derived.credit_housing.PT.yoy_change_pct": (
        'Crédito à habitação — variação homóloga (%)'
    ),
    "derived.credit_consumer.PT.yoy_change_pct": (
        'Crédito ao consumo — variação homóloga (%)'
    ),
    "derived.deposits_households.PT.yoy_change_pct": (
        'Depósitos das famílias — variação homóloga (%)'
    ),
    "derived.metals.PT.yoy_change_pct": (
        'Produção industrial, metalurgia e produtos metálicos — variação homóloga (%)'
    ),
    "derived.chemicals_pharma.PT.yoy_change_pct": (
        'Produção industrial, química e farmacêutica — variação homóloga (%)'
    ),
    "derived.population.PT.yoy_change_pct": (
        'População residente — variação homóloga (%)'
    ),
    "derived.live_births.PT.yoy_change_pct": (
        'Nados-vivos — variação homóloga (%)'
    ),
    "derived.deaths.PT.yoy_change_pct": (
        'Óbitos — variação homóloga (%)'
    ),
    "derived.gdp_per_capita_eur.PT.yoy_change_pct": (
        'PIB per capita — variação homóloga (%)'
    ),
    "derived.unemployment_monthly.PT.period_change": (
        'Taxa de desemprego — variação face ao período anterior (p.p.)'
    ),
    "derived.unemployment_monthly.PT.yoy_change": (
        'Taxa de desemprego — variação homóloga (p.p.)'
    ),
    "derived.pt_10y.PT.period_change": (
        'Taxa de juro das obrigações do Tesouro a 10 anos — variação face ao período anterior (p.p.)'
    ),
    "derived.pt_10y.PT.yoy_change": (
        'Taxa de juro das obrigações do Tesouro a 10 anos — variação homóloga (p.p.)'
    ),
    "derived.cci.PT.period_change": (
        'Indicador de confiança dos consumidores — variação face ao período anterior (saldo)'
    ),
    "derived.unit_labour_cost_hour.PT.rebase_100": (
        'Custo unitário do trabalho por hora — índice rebaseado (2015 = 100)'
    ),
}
