"""
painel.py — /api/painel: KPIs organized into 7 thematic sections.

V8 changes:
  - New "Indústria" section (7 cards) after Custo de Vida
  - New "Competitividade" section (3 cards) at end
  - Custo de Vida: +Gasolina 95 +Euribor 3m
  - Energia: +Gás Natural
  - Section order: Custo de Vida → Indústria → Emprego → Conjuntura → Energia → Externo → Competitividade
  - Every KPI includes source + indicator fields for Explorador deep-link (WP-9)
  - Conjuntura: removes Produção Industrial (now in Indústria section)
"""

from .resumo import resumo_kpi


def painel_kpi(kpi_id, label, source, indicator, description=None, **kwargs):
    """Wrap resumo_kpi and inject source/indicator/description fields.
    description: static one-liner explaining the indicator (shown on card, separate from trend).
    Gracefully handles missing data — frontend tolerates None values.
    """
    kpi = resumo_kpi(kpi_id, label, source, indicator, **kwargs)
    # Always set source/indicator even on error — needed for WP-9 deep-link
    kpi["source"] = source
    kpi["indicator"] = indicator
    # description is separate from context (trend phrase) — both shown on card
    if description is not None:
        kpi["description"] = description
    return kpi


def build_painel():
    """Build /api/painel response with 7 thematic sections and 24+ KPIs."""

    # ── Descriptions and source labels ───────────────────────────────

    DESC = {
        # Custo de Vida
        "inflation":       "Variação dos preços ao consumidor (IHPC). Mede a erosão do poder de compra de salários e poupanças.",
        "diesel":          "Preço médio de venda ao público. Principal combustível do transporte de mercadorias e da agricultura.",
        "gasoline_95":     "Gasolina 95 no posto — par com o gasóleo para leitura completa dos custos de mobilidade.",
        "electricity_btn": "Tarifa simples em Baixa Tensão Normal — referência para habitações e pequenos comércios.",
        "electricity_mt":  "Tarifa de acesso à rede em Média Tensão (hora de ponta) — referência para PMEs industriais.",
        "electricity_at":  "Tarifa de acesso à rede em Alta Tensão (hora de ponta) — referência para grandes indústrias.",
        "euribor_3m":      "Euribor 3 meses — determinante das prestações de crédito habitação a taxa variável de revisão trimestral.",
        "euribor_6m":      "Euribor 6 meses — referência para créditos habitação com revisão semestral.",
        "euribor_12m":     "Euribor 12 meses — taxa usada em contratos de crédito com revisão anual.",
        # Indústria
        "ipi_total":       "Barómetro geral da produção industrial nacional. Base 2021=100. Série dessazonalizada pelo INE.",
        "ipi_cae_10":      "Indústria Alimentar (CAE 10) — maior sector industrial português; inclui lacticínios, conservas, pastelaria industrial.",
        "ipi_cae_20":      "Química (CAE 20) — fertilizantes, plásticos, tintas, produtos farmacêuticos de base. Indicador de inputs industriais.",
        "ipi_cae_24":      "Metalurgia de Base (CAE 24) — aço, alumínio, cobre e ligas. Base para construção e indústria transformadora.",
        "ipi_cae_25":      "Produtos Metálicos (CAE 25) — estruturas, embalagens, ferramentas e componentes metálicos fabricados.",
        "ipi_cae_28":      "Máquinas e Equipamentos (CAE 28) — bens de capital para a indústria; indicador da capacidade de investimento produtivo.",
        "ipi_cae_29":      "Veículos Automóveis (CAE 29) — sector exportador-chave de Portugal (Autoeuropa, Caetano Bus).",
        "copper":          "Cobre — barómetro da economia global; essencial para construção, electrónica e electrificação.",
        "aluminum":        "Alumínio — metal estrutural transversal: automóvel, embalagem, construção. Indicador de procura industrial.",
        # Emprego
        "unemployment":           "Taxa de desemprego harmonizada (OCDE). Percentagem da população activa sem emprego e à procura de trabalho.",
        "industrial_employment":  "Índice de volume de emprego na indústria transformadora (CAE C). Base 2021=100, série dessazonalizada.",
        "wages_industry":         "Índice de remunerações nominais na indústria. Não corrigido de inflação — para salário real, comparar com IHPC.",
        # Conjuntura
        "cli":         "Indicador avançado composto da OCDE. Antecipa viragens do ciclo económico com ~6 meses de antecedência.",
        "confidence":  "Saldo de respostas positivas vs negativas dos industriais (INE). Abaixo de zero indica pessimismo predominante.",
        "order_books": "Saldo de encomendas das empresas industriais (BTS/OCDE). Indica procura futura de produção.",
        # Energia
        "energy_cost":       "Preço MIBEL no mercado grossista ibérico. Referência para tarifas industriais e contratos de longo prazo.",
        "renewable_share":   "Quota de renováveis na produção eléctrica (DGEG). Portugal tem um dos melhores perfis da Europa.",
        "energy_dependence": "Percentagem do consumo energético total importado. Alta dependência significa vulnerabilidade a preços externos.",
        "natural_gas":       "Gás Natural — crítico para indústrias energo-intensivas (vidro, cerâmica, metalurgia) e produção eléctrica.",
        "solar":             "Produção fotovoltaica injectada na rede (REN). Indicador de transição energética e da capacidade instalada solar.",
        "wind":              "Produção eólica injectada na rede (REN). Portugal entre os líderes europeus em capacidade eólica per capita.",
        # Externo
        "eur_usd":      "Taxa de câmbio euro/dólar. Influencia competitividade de exportações e preço de importações denominadas em USD.",
        "spread_pt_de": "Diferencial de juro PT-DE a 10 anos. Mede o risco soberano percebido pelos mercados face à Alemanha.",
        "brent":        "Crude de referência europeu. Influencia directamente gasóleo, gasolina, petroquímica e transportes.",
        # Competitividade
        "gdp_per_capita":  "Riqueza média por habitante. PT: ~23.500€ vs UE27: ~34.000€ — gap estrutural de convergência.",
        "rnd_pct_gdp":     "Intensidade de I&D (% PIB). PT: 1,7% vs UE27: 2,3% (meta Horizonte Europa: 3%). Desvantagem a longo prazo.",
        "employment_rate": "Taxa de emprego (% pop. 20-64 anos com emprego). Medida ampla do mercado de trabalho.",
    }

    D = DESC  # shorthand

    sections = [
        # ── 1. Custo de Vida ─────────────────────────────────────────
        {
            "id": "custo_de_vida",
            "label": "Custo de Vida",
            "kpis": [
                painel_kpi("inflation",       "Inflação",             "INE",       "hicp_yoy",              invert_sentiment=True,  unit_override="%",             description=D["inflation"]),
                painel_kpi("diesel",          "Gasóleo",              "DGEG",      "price_diesel",          invert_sentiment=True,                                 description=D["diesel"]),
                painel_kpi("gasoline_95",     "Gasolina 95",          "DGEG",      "price_gasoline_95_pvp", invert_sentiment=True,                                 description=D["gasoline_95"]),
                painel_kpi("electricity_btn", "Electricidade BTN",    "ERSE",      "btn_simple",            invert_sentiment=True,                                 description=D["electricity_btn"]),
                painel_kpi("electricity_mt",  "Electricidade MT",     "ERSE",      "access_mt_peak",        invert_sentiment=True,                                 description=D["electricity_mt"]),
                painel_kpi("electricity_at",  "Electricidade AT",     "ERSE",      "access_at_peak",        invert_sentiment=True,                                 description=D["electricity_at"]),
                painel_kpi("euribor_3m",      "Euribor 3m",           "BPORTUGAL", "euribor_3m",            invert_sentiment=True,  unit_override="%",             description=D["euribor_3m"]),
                painel_kpi("euribor_6m",      "Euribor 6m",           "BPORTUGAL", "euribor_6m",            invert_sentiment=True,  unit_override="%",             description=D["euribor_6m"]),
                painel_kpi("euribor_12m",     "Euribor 12m",          "BPORTUGAL", "euribor_12m",           invert_sentiment=True,  unit_override="%",             description=D["euribor_12m"]),
            ],
        },
        # ── 2. Indústria ─────────────────────────────────────────────
        {
            "id": "industria",
            "label": "Indústria",
            "kpis": [
                painel_kpi("ipi_total",   "Produção Industrial",  "INE",  "ipi_seasonal_cae_TOT", invert_sentiment=False,                                description=D["ipi_total"]),
                painel_kpi("ipi_cae_10",  "Indústria Alimentar",  "INE",  "ipi_seasonal_cae_10",  invert_sentiment=False,                                description=D["ipi_cae_10"]),
                painel_kpi("ipi_cae_20",  "Química",              "INE",  "ipi_seasonal_cae_20",  invert_sentiment=False,                                description=D["ipi_cae_20"]),
                painel_kpi("ipi_cae_24",  "Metalurgia de Base",   "INE",  "ipi_seasonal_cae_24",  invert_sentiment=False,                                description=D["ipi_cae_24"]),
                painel_kpi("ipi_cae_25",  "Produtos Metálicos",   "INE",  "ipi_seasonal_cae_25",  invert_sentiment=False,                                description=D["ipi_cae_25"]),
                painel_kpi("ipi_cae_28",  "Máquinas e Equipam.",  "INE",  "ipi_seasonal_cae_28",  invert_sentiment=False,                                description=D["ipi_cae_28"]),
                painel_kpi("ipi_cae_29",  "Veículos Automóveis",  "INE",  "ipi_seasonal_cae_29",  invert_sentiment=False,                                description=D["ipi_cae_29"]),
                painel_kpi("copper",      "Cobre",                "FRED", "copper",               invert_sentiment=False, unit_override="USD/ton",       description=D["copper"]),
                painel_kpi("aluminum",    "Alumínio",             "FRED", "aluminum",             invert_sentiment=False, unit_override="USD/ton",       description=D["aluminum"]),
            ],
        },
        # ── 3. Emprego ───────────────────────────────────────────────
        {
            "id": "emprego",
            "label": "Emprego",
            "kpis": [
                painel_kpi("unemployment",          "Desemprego",           "OECD", "unemp_m",           invert_sentiment=True,                                description=D["unemployment"]),
                painel_kpi("industrial_employment", "Emprego Industrial",   "INE",  "emp_industry_cae",  detail_filter='"dim_3": "C"', invert_sentiment=False, unit_override="Índice (2021=100)", description=D["industrial_employment"]),
                painel_kpi("wages_industry",        "Salários Indústria",   "INE",  "wages_industry_cae",detail_filter='"dim_3": "C"', invert_sentiment=False, unit_override="Índice (2021=100)", description=D["wages_industry"]),
            ],
        },
        # ── 4. Conjuntura ─────────────────────────────────────────────
        {
            "id": "conjuntura",
            "label": "Conjuntura",
            "kpis": [
                painel_kpi("cli",        "Indicador Avançado",   "OECD", "cli",               invert_sentiment=False,                  description=D["cli"]),
                painel_kpi("confidence", "Confiança Industrial", "INE",  "conf_manufacturing", invert_sentiment=False, unit_override="saldo", description=D["confidence"]),
                painel_kpi("order_books","Carteira Encomendas",  "OECD", "order_books",        invert_sentiment=False, unit_override="saldo", description=D["order_books"]),
            ],
        },
        # ── 5. Energia ───────────────────────────────────────────────
        {
            "id": "energia",
            "label": "Energia",
            "kpis": [
                painel_kpi("energy_cost",       "Electricidade Grossista", "REN",  "electricity_price_mibel",     invert_sentiment=True,                              description=D["energy_cost"]),
                painel_kpi("renewable_share",   "% Energia Renovável",     "DGEG", "renewable_share_electricity", invert_sentiment=False, unit_override="%", description=D["renewable_share"]),
                painel_kpi("energy_dependence", "Dependência Energética",  "DGEG", "energy_dependence",           invert_sentiment=True,  unit_override="%", description=D["energy_dependence"]),
                painel_kpi("natural_gas",       "Gás Natural",             "FRED", "natural_gas",                 invert_sentiment=True,  unit_override="USD/MMBtu",  description=D["natural_gas"]),
                painel_kpi("solar",             "Solar",                   "REN",  "electricity_solar",           invert_sentiment=False, unit_override="GWh",         description=D["solar"]),
                painel_kpi("wind",              "Eólica",                  "REN",  "electricity_wind",            invert_sentiment=False, unit_override="GWh",         description=D["wind"]),
            ],
        },
        # ── 6. Externo ───────────────────────────────────────────────
        {
            "id": "externo",
            "label": "Externo",
            "kpis": [
                painel_kpi("eur_usd",      "EUR/USD",        "BPORTUGAL", "eur_usd",      invert_sentiment=False,                    description=D["eur_usd"]),
                painel_kpi("spread_pt_de", "Spread PT/DE",   "BPORTUGAL", "spread_pt_de", invert_sentiment=True,  unit_override="pp",     description=D["spread_pt_de"]),
                painel_kpi("brent",        "Petróleo Brent", "FRED",      "brent_oil",    invert_sentiment=True,  unit_override="USD/bbl",description=D["brent"]),
            ],
        },
        # ── 7. Competitividade ────────────────────────────────────────
        {
            "id": "competitividade",
            "label": "Competitividade",
            "kpis": [
                painel_kpi("gdp_per_capita",  "PIB per capita", "EUROSTAT",  "gdp_per_capita_eur", invert_sentiment=False, unit_override="€/hab", region="PT", description=D["gdp_per_capita"]),
                painel_kpi("rnd_pct_gdp",     "I&D % PIB",      "WORLDBANK", "rnd_pct_gdp",        invert_sentiment=False, unit_override="%",     region="PT", description=D["rnd_pct_gdp"]),
                painel_kpi("employment_rate", "Taxa de Emprego", "EUROSTAT",  "employment_rate",    invert_sentiment=False, unit_override="%",     region="PT", description=D["employment_rate"]),
            ],
        },
    ]

    # updated = most recent period across all KPIs (ignoring error-only entries)
    all_periods = [
        k.get("period", "")
        for s in sections
        for k in s["kpis"]
        if k.get("period")
    ]
    updated = max(all_periods) if all_periods else ""

    return {"updated": updated, "sections": sections}
