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
        'Índice de produção industrial, total - variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_TOT.PT.period_change_pct": (
        'Índice de produção industrial, total - variação face ao período anterior (%)'
    ),
    "derived.ipi_seasonal_cae_B.PT.yoy_change_pct": (
        'Índice de produção industrial, indústrias extrativas - variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_C.PT.yoy_change_pct": (
        'Índice de produção industrial, indústrias transformadoras - variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_D.PT.yoy_change_pct": (
        'Índice de produção industrial, eletricidade, gás e vapor - variação homóloga (%)'
    ),
    "derived.ipi_seasonal_cae_E.PT.yoy_change_pct": (
        'Índice de produção industrial, água, saneamento e resíduos - variação homóloga (%)'
    ),
    "derived.exports_monthly.PT.yoy_change_pct": (
        'Exportações de bens - variação homóloga (%)'
    ),
    "derived.imports_monthly.PT.yoy_change_pct": (
        'Importações de bens - variação homóloga (%)'
    ),
    "derived.credit_housing.PT.yoy_change_pct": (
        'Crédito à habitação - variação homóloga (%)'
    ),
    "derived.credit_consumer.PT.yoy_change_pct": (
        'Crédito ao consumo - variação homóloga (%)'
    ),
    "derived.deposits_households.PT.yoy_change_pct": (
        'Depósitos das famílias - variação homóloga (%)'
    ),
    "derived.metals.PT.yoy_change_pct": (
        'Produção industrial, metalurgia e produtos metálicos - variação homóloga (%)'
    ),
    "derived.chemicals_pharma.PT.yoy_change_pct": (
        'Produção industrial, química e farmacêutica - variação homóloga (%)'
    ),
    "derived.population.PT.yoy_change_pct": (
        'População residente - variação homóloga (%)'
    ),
    "derived.live_births.PT.yoy_change_pct": (
        'Nados-vivos - variação homóloga (%)'
    ),
    "derived.deaths.PT.yoy_change_pct": (
        'Óbitos - variação homóloga (%)'
    ),
    "derived.gdp_per_capita_eur.PT.yoy_change_pct": (
        'PIB per capita - variação homóloga (%)'
    ),
    "derived.unemployment_monthly.PT.period_change": (
        'Taxa de desemprego - variação face ao período anterior (p.p.)'
    ),
    "derived.unemployment_monthly.PT.yoy_change": (
        'Taxa de desemprego - variação homóloga (p.p.)'
    ),
    "derived.pt_10y.PT.period_change": (
        'Taxa de juro das obrigações do Tesouro a 10 anos - variação face ao período anterior (p.p.)'
    ),
    "derived.pt_10y.PT.yoy_change": (
        'Taxa de juro das obrigações do Tesouro a 10 anos - variação homóloga (p.p.)'
    ),
    "derived.cci.PT.period_change": (
        'Indicador de confiança dos consumidores - variação face ao período anterior (saldo)'
    ),
    "derived.unit_labour_cost_hour.PT.rebase_100": (
        'Custo unitário do trabalho por hora - índice rebaseado (2015 = 100)'
    ),
}

# --- base-series catalogue (project 4) -------------------------------------------------------
# Keyed by codes stored in the data layer: indicator family (the indicator_key without its
# geography and frequency), geography code, unit string, status flag, theme, frequency and
# seasonal-adjustment code. A missing key raises MissingText: no raw code reaches a page.

FAMILIES = {
    "consumer_confidence": "Confiança dos consumidores",
    "credit_consumer": "Crédito ao consumo",
    "credit_housing": "Crédito à habitação",
    "de_10y": "Taxa de juro da dívida pública a 10 anos",
    "deposits_households": "Depósitos das famílias",
    "eredes_production_market": "Produção de eletricidade, regime de mercado",
    "eredes_production_special": "Produção de eletricidade, regime especial",
    "eredes_production_total": "Produção total de eletricidade",
    "eur_usd": "Taxa de câmbio euro-dólar",
    "euribor_12m": "Taxa Euribor a 12 meses",
    "euribor_1m": "Taxa Euribor a 1 mês",
    "euribor_3m": "Taxa Euribor a 3 meses",
    "euribor_6m": "Taxa Euribor a 6 meses",
    "eurostat_electricity_price_household": "Preço da eletricidade para uso doméstico",
    "eurostat_gdp_per_capita_eur": "PIB per capita",
    "eurostat_gdp_quarterly": "Produto interno bruto",
    "eurostat_gov_debt_pct_gdp": "Dívida pública",
    "eurostat_gov_deficit_pct_gdp": "Défice público",
    "eurostat_hourly_labour_cost_index": "Índice de custo do trabalho por hora",
    "eurostat_ipi_total": "Índice de produção industrial, total",
    "eurostat_labour_productivity_hour_real": "Produtividade real por hora trabalhada",
    "eurostat_labour_productivity_person_real": "Produtividade real por pessoa empregada",
    "eurostat_metals": "Produção industrial, metalurgia",
    "eurostat_unit_labour_cost_hour": "Custo unitário do trabalho por hora",
    "eurostat_unit_labour_cost_person": "Custo unitário do trabalho por pessoa",
    "hicp_yoy": "Taxa de variação homóloga do IHPC",
    "ine_conf_manufacturing": "Confiança da indústria transformadora",
    "ine_deaths": "Óbitos",
    "ine_exports_monthly": "Exportações de bens",
    "ine_imports_monthly": "Importações de bens",
    "ine_ipc_yoy": "Taxa de variação homóloga do IPC",
    "ine_ipi_seasonal_cae_08": "Produção industrial, outras indústrias extrativas (CAE 08)",
    "ine_ipi_seasonal_cae_10": "Produção industrial, indústrias alimentares (CAE 10)",
    "ine_ipi_seasonal_cae_11": "Produção industrial, indústria das bebidas (CAE 11)",
    "ine_ipi_seasonal_cae_13": "Produção industrial, indústria têxtil (CAE 13)",
    "ine_ipi_seasonal_cae_14": "Produção industrial, indústria do vestuário (CAE 14)",
    "ine_ipi_seasonal_cae_15": "Produção industrial, couro e produtos de couro (CAE 15)",
    "ine_ipi_seasonal_cae_16": "Produção industrial, madeira e cortiça (CAE 16)",
    "ine_ipi_seasonal_cae_17": "Produção industrial, papel e cartão (CAE 17)",
    "ine_ipi_seasonal_cae_18": "Produção industrial, impressão e reprodução (CAE 18)",
    "ine_ipi_seasonal_cae_20": "Produção industrial, produtos químicos (CAE 20)",
    "ine_ipi_seasonal_cae_21": "Produção industrial, produtos farmacêuticos (CAE 21)",
    "ine_ipi_seasonal_cae_23": "Produção industrial, minerais não metálicos (CAE 23)",
    "ine_ipi_seasonal_cae_24": "Produção industrial, metalurgia de base (CAE 24)",
    "ine_ipi_seasonal_cae_25": "Produção industrial, produtos metálicos (CAE 25)",
    "ine_ipi_seasonal_cae_26": "Produção industrial, equipamento informático e eletrónico (CAE 26)",
    "ine_ipi_seasonal_cae_27": "Produção industrial, equipamento elétrico (CAE 27)",
    "ine_ipi_seasonal_cae_29": "Produção industrial, veículos automóveis (CAE 29)",
    "ine_ipi_seasonal_cae_30": "Produção industrial, outro equipamento de transporte (CAE 30)",
    "ine_ipi_seasonal_cae_31": "Produção industrial, mobiliário (CAE 31)",
    "ine_ipi_seasonal_cae_32": "Produção industrial, outras indústrias transformadoras (CAE 32)",
    "ine_ipi_seasonal_cae_33": "Produção industrial, reparação e instalação de máquinas (CAE 33)",
    "ine_ipi_seasonal_cae_35": "Produção industrial, eletricidade, gás e vapor (CAE 35)",
    "ine_ipi_seasonal_cae_38": "Produção industrial, resíduos e saneamento (CAE 38)",
    "ine_ipi_seasonal_cae_B": "Produção industrial, indústrias extrativas (CAE B)",
    "ine_ipi_seasonal_cae_D": "Produção industrial, eletricidade, gás e vapor (CAE D)",
    "ine_ipi_seasonal_cae_E": "Produção industrial, água, saneamento e resíduos (CAE E)",
    "ine_ipi_yoy_cae": "Produção industrial, variação homóloga",
    "ine_live_births": "Nados-vivos",
    "ine_population": "População residente",
    "ipi_c20_c21": "Produção industrial, química e farmacêutica",
    "ipi_c22": "Produção industrial, borracha e plásticos",
    "ipi_c28": "Produção industrial, máquinas e equipamentos",
    "ipi_c29_c30": "Produção industrial, veículos e outro equipamento de transporte",
    "ipi_manufacturing": "Produção industrial, indústrias transformadoras",
    "ipi_total": "Produção industrial, total",
    "pt_10y": "Taxa de juro da dívida pública a 10 anos",
    "unemployment_rate": "Taxa de desemprego",
    "worldbank_birth_rate": "Taxa de natalidade",
    "worldbank_death_rate": "Taxa de mortalidade",
    "worldbank_employment_rate": "Taxa de emprego",
    "worldbank_exports_pct_gdp": "Exportações",
    "worldbank_fdi_inflows_pct_gdp": "Investimento direto estrangeiro",
    "worldbank_female_labor_participation": "Participação feminina no mercado de trabalho",
    "worldbank_gdp_growth": "Crescimento do PIB",
    "worldbank_gdp_per_capita": "PIB per capita",
    "worldbank_gdp_usd": "Produto interno bruto",
    "worldbank_gini": "Coeficiente de Gini",
    "worldbank_gov_debt_pct_gdp_wb": "Dívida pública (série do Banco Mundial)",
    "worldbank_imports_pct_gdp": "Importações",
    "worldbank_life_expectancy": "Esperança média de vida",
    "worldbank_population": "População",
    "worldbank_rnd_pct_gdp": "Despesa em investigação e desenvolvimento",
    "worldbank_trade_balance_pct_gdp": "Balança comercial",
    "worldbank_urbanization": "População urbana",
}

# Families whose title already names the geography: series_title does not append the suffix.
SELF_LOCATING_FAMILIES = frozenset({"eur_usd"})

GEOGRAPHIES = {
    "AO": "Angola", "AR": "Argentina", "AT": "Áustria", "BE": "Bélgica", "BG": "Bulgária",
    "BR": "Brasil", "CA": "Canadá", "CH": "Suíça", "CL": "Chile", "CN": "China",
    "CV": "Cabo Verde", "CY": "Chipre", "CZ": "Chéquia", "Continente": "Portugal continental",
    "DE": "Alemanha", "DK": "Dinamarca", "EA": "Área do euro", "EE": "Estónia", "EG": "Egito",
    "EL": "Grécia", "ES": "Espanha", "EU": "União Europeia", "EU27_2020": "União Europeia (27)",
    "FI": "Finlândia", "FR": "França", "GB": "Reino Unido", "GR": "Grécia",
    "GW": "Guiné-Bissau", "HR": "Croácia", "HU": "Hungria", "ID": "Indonésia", "IE": "Irlanda",
    "IN": "Índia", "IT": "Itália", "JP": "Japão", "KR": "Coreia do Sul", "LT": "Lituânia",
    "LU": "Luxemburgo", "LV": "Letónia", "MT": "Malta", "MX": "México", "MY": "Malásia",
    "MZ": "Moçambique", "NG": "Nigéria", "NL": "Países Baixos", "NO": "Noruega",
    "PL": "Polónia", "PT": "Portugal", "RO": "Roménia", "SE": "Suécia", "SI": "Eslovénia",
    "SK": "Eslováquia", "ST": "São Tomé e Príncipe", "TH": "Tailândia", "TL": "Timor-Leste",
    "TR": "Turquia", "US": "Estados Unidos", "WORLD": "Mundo", "ZA": "África do Sul",
}

BASE_UNITS = {
    "%": "%",
    "% GDP": "% do PIB",
    "% PIB": "% do PIB",
    "/1000": "por mil habitantes",
    "0-100": "escala de 0 a 100",
    "EUR": "euros",
    "EUR per capita": "euros por habitante",
    "EUR/kWh": "euros por kWh",
    "EUR/MWh": "euros por MWh",
    "GWh": "GWh",
    "I10_2010": "índice 2010=100",
    "I21": "índice 2021=100",
    "MEUR": "milhões de euros",
    "M_EUR_2010": "milhões de euros, preços de 2010",
    "N.º": "número",
    "USD": "dólares dos EUA",
    "USD per capita": "dólares dos EUA por habitante",
    "USD/EUR": "dólares dos EUA por euro",
    "U.S. Cents per Pound": "cêntimos dos EUA por libra",
    "U.S. Dollars per Barrel": "dólares dos EUA por barril",
    "U.S. Dollars per Metric Ton": "dólares dos EUA por tonelada",
    "anos": "anos",
    "balance": "saldo",
    "balance %": "saldo (%)",
    "hab.": "habitantes",
    "index (100=trend)": "índice tendência=100",
    "index 2020=100": "índice 2020=100",
    "index_2021=100": "índice 2021=100",
    "kWh": "kWh",
}

FLAGS = {
    "normal": "",
    "estimated": "estimado",
    "provisional": "provisório",
    "revised": "revisto",
    "break": "quebra de série",
}

THEMES = {
    "economy": "Economia",
    "demography": "Demografia",
    "energy": "Energia",
}

THEME_BLURBS = {
    "economy": "Atividade, preços, emprego, crédito e finanças públicas.",
    "demography": "População, natalidade, mortalidade e esperança de vida.",
    "energy": "Produção e preços de eletricidade.",
}

FREQUENCIES = {
    "A": "Anual",
    "S": "Semestral",
    "Q": "Trimestral",
    "M": "Mensal",
    "D": "Diária",
    "PT15M": "Intervalos de 15 minutos",
}

SEASONAL = {
    "SA": "ajustada de sazonalidade",
    "SCA": "ajustada de sazonalidade e de calendário",
    "NSA": "não ajustada de sazonalidade",
    "Calendar and seasonally adjusted": "ajustada de sazonalidade e de calendário",
}

SOURCE_TITLES = {
    "ine": "INE - Instituto Nacional de Estatística",
    "bportugal": "Banco de Portugal",
    "eurostat": "Eurostat",
    "worldbank": "Banco Mundial",
    "eredes": "E-REDES - Distribuição de Eletricidade",
    "ren": "REN - Redes Energéticas Nacionais",
    "fred": "FRED - Federal Reserve Bank of St. Louis",
    "oecd": "OCDE",
    "dgeg": "DGEG - Direção-Geral de Energia e Geologia",
}

# What a withheld institution would contribute and why no value is shown. The stored licence
# string is an operator's note; readers get this text instead.
WITHHELD_NOTES = {
    "ren": "Preços e produção de eletricidade em Portugal. Os termos de reutilização não "
           "permitem publicar os valores, que ficam retidos.",
    "fred": "Preços internacionais de matérias-primas, publicados pelo FMI. Os direitos de "
            "redistribuição não estão confirmados, por isso os valores ficam retidos.",
    "oecd": "Indicadores económicos comparáveis entre países. Os direitos de cada conjunto de "
            "dados não estão confirmados, por isso os valores ficam retidos.",
    "dgeg": "Estatísticas de energia e geologia. Os termos de reutilização não estão "
            "confirmados e não existe ainda um canal independente que permita verificar os "
            "valores, por isso ficam retidos.",
}

# The home page's figures, in reading order. `derived` names the calculated series whose latest
# value is shown as the change badge; None means the figure has no declared calculated companion.
# Words readers actually type, per family: the title alone misses the common name.
SEARCH_ALIASES = {
    "hicp_yoy": "inflação ipc",
    "unemployment_rate": "desemprego desempregados",
    "worldbank_gdp_growth": "pib economia crescimento económico",
    "consumer_confidence": "confiança dos consumidores",
    "credit_consumer": "crédito ao consumo",
    "credit_housing": "crédito à habitação",
    "ine_population": "população habitantes residentes",
    "eur_usd": "câmbio euro dólar",
}

CURATED_HOME = [
    {"series": "ine.hicp_yoy.PT", "label": "Inflação (IHPC)", "derived": None},
    {"series": "ine.unemployment_monthly.PT", "label": "Desemprego",
     "derived": "derived.unemployment_monthly.PT.yoy_change"},
    {"series": "ine.ipi_seasonal_cae_TOT.PT", "label": "Produção industrial",
     "derived": "derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct"},
    {"series": "eurostat.cci.PT", "label": "Confiança dos consumidores",
     "derived": "derived.cci.PT.period_change"},
    {"series": "ine.conf_manufacturing.PT", "label": "Confiança da indústria", "derived": None},
    {"series": "bportugal.credit_consumer.PT", "label": "Crédito ao consumo",
     "derived": "derived.credit_consumer.PT.yoy_change_pct"},
    {"series": "bportugal.deposits_households.PT", "label": "Depósitos das famílias",
     "derived": "derived.deposits_households.PT.yoy_change_pct"},
    {"series": "bportugal.pt_10y.PT", "label": "Dívida pública a 10 anos",
     "derived": "derived.pt_10y.PT.yoy_change"},
    {"series": "ine.population.PT", "label": "População residente",
     "derived": "derived.population.PT.yoy_change_pct"},
    {"series": "ine.live_births.PT", "label": "Nados-vivos",
     "derived": "derived.live_births.PT.yoy_change_pct"},
    {"series": "ine.exports_monthly.PT", "label": "Exportações de bens",
     "derived": "derived.exports_monthly.PT.yoy_change_pct"},
    {"series": "eurostat.electricity_price_household.PT", "label": "Preço da eletricidade",
     "derived": None},
]


# Public pages whose composition the backoffice may edit. The page itself (route, title,
# section copy) stays in code: only the ordered series list is data. `note_all_pt` is
# rendered when every visible card is Portuguese, `note_mixed` when any card is not.
PAGES: dict[str, dict[str, str]] = {
    "inicio": {
        "title": "Início",
        "section_title": "Números em destaque",
        "note_all_pt": "Portugal. Valores publicados tal como a fonte os publica.",
        "note_mixed": "Cada número indica a instituição e a data da recolha.",
    },
}


# --- two-series comparisons (project 4, extension) --------------------------------------------
# Curated pairs only: the route takes a slug, never two series ids, because most of the base is
# one indicator across many countries and two-of-anything turns coincidences into pages with the
# site's authority behind them. `scale` is a property of the pair: `one_axis` needs the same unit
# token on both sides and two comparable percentages (a year-on-year rate against a rate is fine,
# a level against its own year-on-year rate is not); `dual_axis` needs two labelled axes and a note
# saying the magnitudes are not comparable.
COMPARISONS_INTRO = (
    "Dois indicadores no mesmo gráfico, apenas nos pares que a redação escolheu e consegue "
    "explicar. Não há escolha livre: dois valores quaisquer produzem coincidências vistosas "
    "sem significado."
)

# Text around the interactive chart controls. The chart itself carries data, never operator
# instructions; these are the only words the enhancement adds to the page.
CHART_UI: dict[str, str] = {
    "range": "Período no gráfico",
    "hint": "Use as setas, Início e Fim para percorrer os períodos. Os valores são os publicados.",
    "calculated": "Calculado pelo Prumo",
}

COMPARISONS: dict[str, dict[str, str]] = {
    "inflacao-e-desemprego": {
        "series_a": "ine.hicp_yoy.PT",
        "series_b": "ine.unemployment_monthly.PT",
        "title": "Inflação e desemprego",
        "subtitle": "Os dois lados do ciclo, mês a mês, desde 1998.",
        "mechanism": "Quando o desemprego desce, a inflação tende a subir. O gráfico mostra o "
                     "movimento conjunto ao longo de quase três décadas; não estabelece uma "
                     "relação de causa.",
        "scale": "one_axis",
        "caption_note": "As duas séries são mensais e em percentagem, publicadas pelo INE.",
    },
    "euribor-e-inflacao": {
        "series_a": "bportugal.euribor_3m.EA",
        "series_b": "ine.hicp_yoy.PT",
        "title": "Euribor e inflação",
        "subtitle": "O preço do dinheiro na área do euro e a inflação portuguesa.",
        "mechanism": "A Euribor a 3 meses é a taxa a que os bancos se financiam entre si na área "
                     "do euro; a inflação é portuguesa. A transmissão de uma para a outra não é "
                     "imediata, e é essa distância que o gráfico deixa ver.",
        "scale": "one_axis",
        "caption_note": "A Euribor diz respeito à área do euro e o IHPC a Portugal. Ambas "
                        "mensais e em percentagem.",
    },
    "credito-e-taxa": {
        "series_a": "bportugal.euribor_12m.EA",
        "series_b": "bportugal.credit_housing.PT",
        "title": "Taxa e crédito à habitação",
        "subtitle": "O que uma família paga e quanto está emprestado em crédito à habitação.",
        "mechanism": "A Euribor a 12 meses é um dos indexantes usados no crédito à habitação; o "
                     "stock diz quanto está emprestado. Uma é preço e o outro é quantidade, e "
                     "por isso sobem e descem em alturas diferentes.",
        "scale": "dual_axis",
        "caption_note": "Percentagem à esquerda, milhões de euros à direita. As escalas são "
                        "independentes: o gráfico compara direções, não grandezas.",
    },
}
