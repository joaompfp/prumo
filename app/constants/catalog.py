CATALOG = {
  "INE": {
    "label": "INE — Instituto Nacional de Estatística",
    "description": "Estatísticas oficiais portuguesas. Produção industrial, emprego, salários e confiança empresarial.",
    "url": "https://www.ine.pt",
    "indicators": {
      "ipi_seasonal_cae": {
        "label": "IPI Indústria Transformadora (dessaz.)",
        "description": "Índice de Produção Industrial da indústria transformadora, com ajustamento sazonal. Mede a evolução do volume de produção das empresas industriais. Um valor acima de 100 indica produção superior à média de 2021.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["produção", "indústria", "conjuntura"]
      },
      "ipi_yoy_cae": {
        "label": "IPI Indústria — Variação Anual",
        "description": "Variação homóloga do Índice de Produção Industrial. Compara o mês actual com o mesmo mês do ano anterior, eliminando efeitos sazonais naturais.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["produção", "indústria", "variação"]
      },
      "emp_industry_cae": {
        "label": "Emprego na Indústria",
        "description": "Índice de emprego nas empresas industriais (indústria transformadora). Reflecte a evolução do número de trabalhadores ao serviço no sector.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["emprego", "trabalho", "indústria"]
      },
      "wages_industry_cae": {
        "label": "Salários na Indústria",
        "description": "Índice de remunerações na indústria transformadora. Inclui salários base e outros componentes remuneratórios pagos aos trabalhadores industriais.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["salários", "trabalho", "indústria"]
      },
      "conf_manufacturing": {
        "label": "Confiança Indústria Transformadora",
        "description": "Indicador de confiança dos empresários industriais, baseado em inquéritos sobre carteira de encomendas, stocks e perspectivas de produção. Valores positivos indicam optimismo.",
        "unit": "Saldo de respostas",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["confiança", "expectativas", "indústria"]
      },
      "hicp_yoy": {
        "label": "Inflação (IHPC) — Variação Anual",
        "description": "Variação homóloga do Índice Harmonizado de Preços no Consumidor (IHPC). Medida de inflação harmonizada a nível europeu, comparável entre países da UE.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["inflação", "preços", "macro"]
      }
    }
  },
  "EUROSTAT": {
    "label": "Eurostat",
    "description": "Gabinete de estatísticas da União Europeia. Dados de produção industrial por sector NACE e indicadores macro comparáveis entre países.",
    "url": "https://ec.europa.eu/eurostat",
    "indicators": {
      "ipi": {
        "label": "IPI Portugal (Eurostat)",
        "description": "Índice de Produção Industrial de Portugal segundo a metodologia Eurostat (NACE Rev.2, secção C). Permite comparação directa com outros países da UE.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "indústria", "europa"]
      },
      "manufacturing": {
        "label": "Indústria Transformadora (PT)",
        "description": "Produção da indústria transformadora portuguesa (NACE C). Inclui todos os subsectores, de alimentos a equipamentos de transporte.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "indústria", "europa"]
      },
      "total_industry": {
        "label": "Total Indústria (PT)",
        "description": "Índice de produção total da indústria portuguesa (NACE B+C+D+E). Inclui indústrias extractivas, transformadoras, energia e água.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "indústria", "europa"]
      },
      "metals": {
        "label": "Metais e Produtos Metálicos (PT)",
        "description": "Produção do sector de metalurgia de base e produtos metálicos (NACE C24-C25). Sector estratégico para fornecimento de inputs à indústria transformadora.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "metais", "indústria"]
      },
      "chemicals_pharma": {
        "label": "Química e Farmacêutica (PT)",
        "description": "Produção do sector químico e farmacêutico (NACE C20-C21). Inclui indústria química de base, plásticos e produtos farmacêuticos.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "química", "indústria"]
      },
      "machinery": {
        "label": "Maquinaria e Equipamento (PT)",
        "description": "Produção de máquinas e equipamentos (NACE C28). Sector com forte componente exportadora e de incorporação tecnológica.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "maquinaria", "indústria"]
      },
      "transport_eq": {
        "label": "Equipamento de Transporte (PT)",
        "description": "Produção de veículos e equipamentos de transporte (NACE C29-C30). Inclui automóveis e componentes, sector relevante para exportações portuguesas.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "automóvel", "indústria"]
      },
      "rubber_plastics": {
        "label": "Borracha e Plásticos (PT)",
        "description": "Produção do sector de borracha e plásticos (NACE C22). Sector com forte integração nas cadeias de valor automóvel e construção.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "tags": ["produção", "plásticos", "indústria"]
      },
      "inflation": {
        "label": "Inflação UE (Eurostat)",
        "description": "Inflação harmonizada da zona euro (IHPC). Medida comparável entre todos os Estados-membros, usada pelo BCE para política monetária.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["inflação", "macro", "europa"]
      },
      "unemployment": {
        "label": "Desemprego Portugal (Eurostat)",
        "description": "Taxa de desemprego em Portugal segundo a metodologia harmonizada Eurostat. Percentagem da população activa em situação de desemprego.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["desemprego", "emprego", "macro"]
      }
    }
  },
  "FRED": {
    "label": "FRED — Federal Reserve Bank of St. Louis",
    "description": "Base de dados económicos da Reserva Federal dos EUA. Preços de commodities, câmbios e indicadores financeiros globais.",
    "url": "https://fred.stlouisfed.org",
    "indicators": {
      "brent_oil": {
        "label": "Petróleo Brent (USD/barril)",
        "description": "Preço spot do petróleo bruto Brent no mar do Norte. Principal referência europeia para o preço do petróleo. Afecta directamente custos de transporte e matérias-primas industriais.",
        "unit": "USD/bbl",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["energia", "commodities", "petróleo"]
      },
      "natural_gas": {
        "label": "Gás Natural (USD/MMBtu)",
        "description": "Preço do gás natural (Henry Hub, EUA). Referência global que influencia os preços europeus via mercado GNL. Custo crítico para indústrias energointensivas.",
        "unit": "USD/MMBtu",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["energia", "commodities", "gás"]
      },
      "copper": {
        "label": "Cobre (USD/tonelada)",
        "description": "Preço do cobre no mercado internacional. Considerado um 'barómetro da economia global' pela sua presença em construção, electrónica e electrificação. Afecta directamente o sector metalúrgico.",
        "unit": "USD/t",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["commodities", "metais", "indústria"]
      },
      "aluminum": {
        "label": "Alumínio (USD/tonelada)",
        "description": "Preço do alumínio primário. Metal base para indústria automóvel, embalagens e construção. A produção de alumínio é muito energointensiva, tornando o seu preço sensível aos custos de energia.",
        "unit": "USD/t",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["commodities", "metais", "indústria"]
      },
      "wheat": {
        "label": "Trigo (USD/bushel)",
        "description": "Preço do trigo no mercado internacional. Input crítico para a indústria alimentar. A guerra na Ucrânia ilustrou a sua importância estratégica para a segurança alimentar europeia.",
        "unit": "USD/bushel",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["commodities", "alimentar", "agricultura"]
      },
      "corn": {
        "label": "Milho (USD/bushel)",
        "description": "Preço do milho no mercado internacional. Usado como ração animal e matéria-prima na indústria alimentar e de biocombustíveis.",
        "unit": "USD/bushel",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["commodities", "alimentar", "agricultura"]
      },
      "coffee": {
        "label": "Café (USD/lb)",
        "description": "Preço do café arábica no mercado internacional. Relevante para a indústria de torrefacção e alimentar em Portugal.",
        "unit": "USD/lb",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["commodities", "alimentar"]
      }
    }
  },
  "BPORTUGAL": {
    "label": "Banco de Portugal",
    "description": "Autoridade monetária nacional e membro do Sistema Europeu de Bancos Centrais. Publica estatísticas sobre taxas de juro, crédito, depósitos e yields de dívida soberana.",
    "url": "https://bpstat.bportugal.pt",
    "indicators": {
      "euribor_1m": {
        "label": "Euribor 1 mês",
        "description": "Taxa de juro interbancária do euro a 1 mês. Referência de curtíssimo prazo para operações financeiras.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "euribor_3m": {
        "label": "Euribor 3 meses",
        "description": "Taxa de juro interbancária do euro a 3 meses. Principal referência para crédito à habitação a taxa variável e financiamento empresarial de curto prazo.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "euribor_6m": {
        "label": "Euribor 6 meses",
        "description": "Taxa de juro interbancária do euro a 6 meses. Usada em contratos de financiamento de médio prazo.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "euribor_12m": {
        "label": "Euribor 12 meses",
        "description": "Taxa de juro interbancária do euro a 12 meses. Referência para crédito à habitação e empréstimos de longo prazo.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "pt_10y": {
        "label": "Yield OT Portugal 10 anos",
        "description": "Taxa de rendibilidade das Obrigações do Tesouro portuguesas a 10 anos. Reflecte o custo de financiamento do Estado e a percepção de risco do mercado sobre Portugal.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "dívida", "yield"]
      },
      "de_10y": {
        "label": "Yield Bund Alemão 10 anos",
        "description": "Taxa de rendibilidade das obrigações do tesouro alemão a 10 anos. Referência de activo 'sem risco' da zona euro. Usada como base para calcular spreads de outros países.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "dívida", "yield", "alemanha"]
      },
      "spread_pt_de": {
        "label": "Spread Portugal-Alemanha (10 anos)",
        "description": "Diferença entre o yield da dívida portuguesa e alemã a 10 anos. Mede o prémio de risco de Portugal face ao benchmark europeu. Um spread elevado indica maior percepção de risco e maior custo de financiamento.",
        "unit": "p.b.",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["financeiro", "risco", "spread", "dívida"]
      },
      "credit_housing": {
        "label": "Crédito à Habitação",
        "description": "Stock total de crédito bancário concedido para aquisição de habitação em Portugal. Indicador da saúde do mercado imobiliário e da exposição das famílias ao crédito.",
        "unit": "M€",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["crédito", "habitação", "banca"]
      },
      "credit_consumer": {
        "label": "Crédito ao Consumo",
        "description": "Stock total de crédito ao consumo concedido a particulares. Reflecte a confiança das famílias e a capacidade de endividamento para consumo.",
        "unit": "M€",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["crédito", "consumo", "banca"]
      },
      "deposits": {
        "label": "Depósitos Bancários",
        "description": "Stock total de depósitos bancários de particulares e empresas em Portugal. Indicador da poupança e liquidez no sistema financeiro.",
        "unit": "M€",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["poupança", "banca", "depósitos"]
      },
      "eur_usd": {
        "label": "Câmbio EUR/USD",
        "description": "Taxa de câmbio euro/dólar americano. Afecta o custo de importação de commodities cotadas em dólares e a competitividade das exportações europeias.",
        "unit": "USD/EUR",
        "frequency": "monthly",
        "lag_months": 0,
        "tags": ["câmbio", "financeiro", "dólar"]
      }
    }
  },
  "REN": {
    "label": "REN — Redes Energéticas Nacionais",
    "description": "Operador da Rede de Transporte de electricidade e do sistema de gás natural em Portugal. Publica dados sobre produção, consumo e preços no mercado ibérico de electricidade (MIBEL).",
    "url": "https://datahub.ren.pt",
    "indicators": {
      "electricity_price_mibel": {
        "label": "Preço MIBEL (EUR/MWh)",
        "description": "Preço médio mensal da electricidade no Mercado Ibérico de Electricidade (MIBEL). Referência de custo para grandes consumidores industriais e para as tarifas reguladas. Muito sensível à disponibilidade hídrica e ao preço do gás.",
        "unit": "EUR/MWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "preço", "mibel"]
      },
      "electricity_hydro": {
        "label": "Produção Hídrica (GWh)",
        "description": "Produção mensal de electricidade a partir de centrais hidroeléctricas. Fonte renovável dominante em Portugal, muito variável com a pluviosidade. Determina em grande medida o preço da electricidade.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "hídrica", "renovável"]
      },
      "electricity_wind": {
        "label": "Produção Eólica (GWh)",
        "description": "Produção mensal de electricidade a partir de parques eólicos. Portugal tem uma das maiores capacidades eólicas per capita da Europa.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "eólica", "renovável"]
      },
      "electricity_solar": {
        "label": "Produção Solar FV (GWh)",
        "description": "Produção mensal de electricidade a partir de painéis fotovoltaicos. Capacidade instalada em crescimento acelerado desde 2022 com os grandes projectos solares.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "solar", "renovável"]
      },
      "electricity_natural_gas": {
        "label": "Produção Gás Natural (GWh)",
        "description": "Produção de electricidade em centrais a gás natural (ciclo combinado). Funciona como backup às renováveis. Aumenta quando a produção hídrica é baixa, pressionando os preços MIBEL.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "gás", "térmica"]
      },
      "electricity_biomass": {
        "label": "Produção Biomassa (GWh)",
        "description": "Produção de electricidade a partir de biomassa florestal e resíduos. Fonte renovável gerível, importante para a regulação do sistema eléctrico.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "biomassa", "renovável"]
      },
      "electricity_consumption": {
        "label": "Consumo Eléctrico Nacional (GWh)",
        "description": "Consumo total de electricidade em Portugal Continental. Indicador proxy da actividade económica, especialmente industrial.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "consumo"]
      },
      "electricity_production_total": {
        "label": "Produção Eléctrica Total (GWh)",
        "description": "Produção total bruta de electricidade em Portugal Continental, somando todas as fontes (renováveis e não renováveis).",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "produção"]
      },
      "electricity_production_renewable": {
        "label": "Produção Renovável (GWh)",
        "description": "Produção de electricidade a partir de fontes renováveis (hídrica, eólica, solar, biomassa). Portugal tem como meta 85% de electricidade renovável em 2030.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "renovável", "electricidade"]
      },
      "electricity_net_imports": {
        "label": "Importações Líquidas (GWh)",
        "description": "Saldo líquido de electricidade importada menos exportada via interligações com Espanha. Positivo = importador líquido. Reflecte o grau de autossuficiência eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["energia", "electricidade", "importação"]
      }
    }
  },
  "OECD": {
    "label": "OCDE",
    "description": "Organização para a Cooperação e Desenvolvimento Económico. Indicadores de conjuntura industrial baseados em inquéritos aos empresários e indicadores avançados do ciclo económico.",
    "url": "https://stats.oecd.org",
    "indicators": {
      "cli": {
        "label": "CLI — Indicador Composto Avançado",
        "description": "Composite Leading Indicator da OCDE para Portugal. Indicador avançado que antecipa as inflexões do ciclo económico com 6-9 meses de antecedência. Valores acima de 100 indicam expansão acima da tendência.",
        "unit": "Índice",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["conjuntura", "avançado", "ciclo"]
      },
      "production": {
        "label": "Perspectivas de Produção (BTS)",
        "description": "Resposta dos empresários industriais sobre as perspectivas de produção a 3 meses (Business Tendency Survey). Saldo de respostas positivas menos negativas.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["confiança", "expectativas", "produção"]
      },
      "order_books": {
        "label": "Carteira de Encomendas (BTS)",
        "description": "Avaliação dos empresários sobre a adequação da carteira de encomendas actual face ao normal. Indicador avançado da actividade futura.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["confiança", "encomendas", "expectativas"]
      },
      "selling_prices": {
        "label": "Perspectivas de Preços de Venda (BTS)",
        "description": "Intenções dos empresários industriais quanto à evolução dos preços de venda a 3 meses. Indicador avançado da inflação industrial.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["preços", "inflação", "expectativas"]
      },
      "employment": {
        "label": "Perspectivas de Emprego (BTS)",
        "description": "Intenções dos empresários quanto à evolução do emprego nos próximos 3 meses. Avança tendências do mercado de trabalho industrial.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "tags": ["emprego", "expectativas", "trabalho"]
      },
      "unemp_m": {
        "label": "Taxa de Desemprego (OCDE)",
        "description": "Taxa de desemprego harmonizada da OCDE para Portugal. Comparável com outros países membros da organização.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 2,
        "tags": ["desemprego", "macro"]
      }
    }
  },
  "DGEG": {
    "label": "DGEG — Direção-Geral de Energia e Geologia",
    "description": "Autoridade nacional de energia. Publica estatísticas sobre produção e consumo de electricidade, preços de combustíveis, capacidade instalada e indicadores de eficiência energética.",
    "url": "https://www.dgeg.gov.pt",
    "note": "Dados disponíveis na base de dados de energia (energy-data.db). Periodicidade variável: mensal, semestral e anual.",
    "indicators": {
      "gross_production_total":            {"label": "Produção Bruta Total (GWh)",                   "description": "Produção bruta total de electricidade em Portugal, incluindo todas as fontes.",                                                                                                                                           "unit": "GWh",       "frequency": "monthly",   "tags": ["energia", "electricidade", "produção"]},
      "gross_production_wind":             {"label": "Produção Eólica Bruta (GWh)",                  "description": "Produção bruta de electricidade a partir de energia eólica.",                                                                                                                                                          "unit": "GWh",       "frequency": "monthly",   "tags": ["energia", "eólica", "renovável"]},
      "gross_production_hydro":            {"label": "Produção Hídrica Bruta (GWh)",                 "description": "Produção bruta de electricidade em centrais hidroeléctricas.",                                                                                                                                                          "unit": "GWh",       "frequency": "monthly",   "tags": ["energia", "hídrica", "renovável"]},
      "gross_production_solar_pv":         {"label": "Produção Solar FV Bruta (GWh)",                "description": "Produção bruta de electricidade em painéis fotovoltaicos.",                                                                                                                                                             "unit": "GWh",       "frequency": "monthly",   "tags": ["energia", "solar", "renovável"]},
      "total_consumption":                 {"label": "Consumo Total Electricidade (GWh)",            "description": "Consumo total de electricidade em Portugal, incluindo perdas.",                                                                                                                                                          "unit": "GWh",       "frequency": "monthly",   "tags": ["energia", "electricidade", "consumo"]},
      "net_imports":                       {"label": "Importações Líquidas (GWh)",                   "description": "Saldo líquido de electricidade importada via interligações.",                                                                                                                                                            "unit": "GWh",       "frequency": "monthly",   "tags": ["energia", "importação"]},
      "energy_dependence":                 {"label": "Dependência Energética (%)",                   "description": "Percentagem das necessidades energéticas do país satisfeita por importações. Portugal tem dependência estruturalmente elevada dada a escassez de recursos fósseis nacionais.",                                          "unit": "%",         "frequency": "annual",    "tags": ["energia", "dependência", "estratégico"]},
      "renewable_share_electricity":       {"label": "Quota Renovável Electricidade (%)",            "description": "Percentagem da electricidade produzida a partir de fontes renováveis. Portugal tem como meta 85% em 2030.",                                                                                                              "unit": "%",         "frequency": "annual",    "tags": ["energia", "renovável", "metas"]},
      "renewable_share_total":             {"label": "Quota Renovável Total (%)",                    "description": "Percentagem do consumo final de energia proveniente de fontes renováveis (directiva UE). Inclui electricidade, calor e transporte.",                                                                                    "unit": "%",         "frequency": "annual",    "tags": ["energia", "renovável", "metas"]},
      "energy_intensity":                  {"label": "Intensidade Energética (tep/M€)",              "description": "Quantidade de energia consumida por unidade de PIB. Mede a eficiência energética da economia. Redução implica crescimento económico com menor consumo energético.",                                                     "unit": "tep/M€",    "frequency": "annual",    "tags": ["eficiência", "energia", "macro"]},
      "co2_emissions_total":               {"label": "Emissões CO₂ Totais (Mton)",                  "description": "Emissões totais de CO₂ equivalente pelo sector energético. Portugal tem compromissos de redução no âmbito do Green Deal europeu.",                                                                                       "unit": "Mton CO2e", "frequency": "annual",    "tags": ["emissões", "clima", "ambiente"]},
      "price_diesel":                      {"label": "Preço Gasóleo (€/l)",                         "description": "Preço médio semanal do gasóleo rodoviário em Portugal. Custo operacional crítico para transporte e logística industrial.",                                                                                               "unit": "€/l",       "frequency": "weekly",    "tags": ["combustível", "preço", "transporte"]},
      "price_gasoline_95_pvp":             {"label": "Preço Gasolina 95 (€/l)",                     "description": "Preço médio semanal da gasolina 95 em Portugal (preço de venda ao público).",                                                                                                                                            "unit": "€/l",       "frequency": "weekly",    "tags": ["combustível", "preço"]},
      "natgas_price_industry_€_per_MWh":  {"label": "Preço Gás Natural Indústria (€/MWh)",         "description": "Preço semestral do gás natural para consumidores industriais em Portugal (bandas de consumo I). Comparável com médias da UE.",                                                                                          "unit": "€/MWh",     "frequency": "semester",  "tags": ["gás", "energia", "indústria", "preço"]},
      "industrial_band_ic_incl_taxes":     {"label": "Preço Electricidade Industrial Banda IC (€/kWh)", "description": "Preço da electricidade para consumidores industriais na banda IC (500 MWh a 2.000 MWh/ano), incluindo todos os impostos e taxas. Banda mais representativa das PME industriais.", "unit": "€/kWh",     "frequency": "semester",  "tags": ["electricidade", "preço", "indústria"]},
      "brent_usd":                         {"label": "Petróleo Brent (USD/barril) — DGEG",           "description": "Preço do petróleo Brent segundo a DGEG. Comparável com dados FRED.",                                                                                                                                                    "unit": "USD/bbl",   "frequency": "monthly",   "tags": ["petróleo", "commodities", "energia"]}
    }
  },
  "ERSE": {
    "label": "ERSE — Entidade Reguladora dos Serviços Energéticos",
    "description": "Regulador dos sectores do gás natural e da electricidade. Publica as tarifas reguladas de acesso às redes eléctricas por nível de tensão e período tarifário.",
    "url": "https://www.erse.pt",
    "note": "Tarifas semestrais (ou anuais) por nível de tensão: MAT (Muito Alta Tensão), AT (Alta Tensão), MT (Média Tensão), BTE (Baixa Tensão Especial), BTN (Baixa Tensão Normal).",
    "indicators": {
      "tariff_mt_peak":      {"label": "Tarifa MT — Ponta (€/kWh)",       "description": "Tarifa de acesso à rede eléctrica em Média Tensão no período de ponta. Aplicável a empresas industriais com contrato MT (tipicamente >41,4 kVA de potência contratada).", "unit": "€/kWh", "frequency": "annual", "tags": ["electricidade", "tarifa", "indústria", "MT"]},
      "tariff_mt_off_peak":  {"label": "Tarifa MT — Vazio (€/kWh)",       "description": "Tarifa de acesso à rede eléctrica em Média Tensão no período de cheias.",                                                                                                      "unit": "€/kWh", "frequency": "annual", "tags": ["electricidade", "tarifa", "indústria", "MT"]},
      "tariff_at_peak":      {"label": "Tarifa AT — Ponta (€/kWh)",       "description": "Tarifa de acesso à rede em Alta Tensão no período de ponta. Aplicável a grandes consumidores industriais.",                                                                      "unit": "€/kWh", "frequency": "annual", "tags": ["electricidade", "tarifa", "indústria", "AT"]},
      "tariff_mat_peak":     {"label": "Tarifa MAT — Ponta (€/kWh)",      "description": "Tarifa de acesso à rede em Muito Alta Tensão no período de ponta. Aplicável a grandes indústrias com ligação directa à rede de transporte.",                                    "unit": "€/kWh", "frequency": "annual", "tags": ["electricidade", "tarifa", "indústria", "MAT"]},
      "btn_simple":          {"label": "Tarifa BTN Simples (€/kWh)",      "description": "Tarifa de energia em Baixa Tensão Normal para consumidores sem discriminação horária. Referência para pequenas empresas e comércio.",                                           "unit": "€/kWh", "frequency": "annual", "tags": ["electricidade", "tarifa", "PME", "BTN"]}
    }
  },
  "WORLDBANK": {
    "label": "Banco Mundial",
    "url": "https://data.worldbank.org",
    "description": "Indicadores de desenvolvimento mundial — dados anuais",
    "indicators": {
      "birth_rate": {
        "label": "Taxa de Natalidade",
        "unit": "nascimentos por 1.000 habitantes",
        "description": "Número de nascimentos vivos por 1.000 habitantes",
        "frequency": "annual",
        "source_url": "https://data.worldbank.org/indicator/SP.DYN.CBRT.IN",
      },
      "rnd_pct_gdp": {
        "label": "I&D (% do PIB)",
        "unit": "% do PIB",
        "description": "Despesa bruta em investigação e desenvolvimento como % do PIB",
        "frequency": "annual",
        "source_url": "https://data.worldbank.org/indicator/GB.XPD.RSDV.GD.ZS",
      },
      "fdi_inflows_pct_gdp": {
        "label": "Investimento Directo Estrangeiro — Entradas",
        "unit": "% do PIB",
        "description": "Fluxos de IDE recebidos como % do PIB",
        "frequency": "annual",
        "source_url": "https://data.worldbank.org/indicator/BX.KLT.DINV.WD.GD.ZS",
      },
      "gdp_per_capita_ppp": {
        "label": "PIB per capita (PPC)",
        "unit": "USD (2017)",
        "description": "PIB per capita em paridade de poder de compra, dólares internacionais constantes de 2017. Permite comparação real entre países eliminando diferenças de nível de preços.",
        "frequency": "annual",
        "source_url": "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD",
        "tags": ["pib", "macro", "comparação", "convergência"],
      },
    },
  },
}
