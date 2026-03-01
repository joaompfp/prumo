CATALOG = {
  "INE": {
    "label": "INE — Instituto Nacional de Estatística",
    "description": "Estatísticas oficiais portuguesas. Produção industrial, emprego, salários e confiança empresarial.",
    "url": "https://www.ine.pt",
    "indicators": {
      "ipi_seasonal_cae": {
        "label": "IPI Indústria Transformadora (dessaz.)",
        "description": "Índice de Produção Industrial da indústria transformadora portuguesa, série dessazonalizada, base 2021=100. Mede a evolução do volume de produção das empresas industriais, eliminando variações sazonais pelo método TRAMO-SEATS. Um valor acima de 100 indica produção superior à média de 2021. Fonte: INE, Índices de Produção Industrial.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["produção", "indústria", "conjuntura"]
      },
      "ipi_yoy_cae": {
        "label": "IPI Indústria — Variação Anual",
        "description": "Variação homóloga do Índice de Produção Industrial da indústria transformadora (%). Compara o mês actual com o mesmo mês do ano anterior, eliminando efeitos sazonais naturais sem necessidade de ajustamento formal. Calculado pelo INE a partir da série bruta. Fonte: INE, Índices de Produção Industrial.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["produção", "indústria", "variação"]
      },
      "emp_industry_cae": {
        "label": "Emprego na Indústria",
        "description": "Índice de emprego nas empresas industriais da indústria transformadora, base 2021=100. Reflecte a evolução do número de trabalhadores ao serviço no sector, publicado mensalmente pelo INE com base em inquéritos às empresas. Não inclui trabalhadores independentes nem emprego na agricultura ou serviços. Fonte: INE, Índices de Produção Industrial.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["emprego", "trabalho", "indústria"]
      },
      "wages_industry_cae": {
        "label": "Salários na Indústria",
        "description": "Índice de remunerações na indústria transformadora, base 2021=100. Inclui salários base, prémios, subsídios e outros componentes remuneratórios pagos aos trabalhadores industriais. Medida nominal — não ajustada pela inflação. Para análise do poder de compra, comparar com o IHPC. Fonte: INE, Índices de Produção Industrial.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["salários", "trabalho", "indústria"]
      },
      "conf_manufacturing": {
        "label": "Confiança Indústria Transformadora",
        "description": "Indicador de confiança dos empresários da indústria transformadora, construído a partir de inquéritos mensais sobre carteira de encomendas (actual e esperada), stocks e perspectivas de produção. Expresso como saldo de respostas (% respostas positivas − % negativas). Valores positivos indicam optimismo face ao normal histórico. Publicado pelo INE em articulação com o inquérito harmonizado da Comissão Europeia. Fonte: INE, Inquérito de Conjuntura à Indústria Transformadora.",
        "unit": "Saldo de respostas",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "2000-01",
        "until": "2025-12",
        "rows": 312,
        "tags": ["confiança", "expectativas", "indústria"]
      },
      "hicp_yoy": {
        "label": "Inflação (IHPC) — Variação Anual",
        "description": "Variação homóloga do Índice Harmonizado de Preços no Consumidor (IHPC) para Portugal (%). Medida de inflação harmonizada a nível europeu segundo o regulamento (CE) n.º 2016/792, comparável entre todos os países da UE. Difere do IPC nacional em cobertura e métodos de ponderação. Usado pelo BCE para avaliação da política monetária. Fonte: INE / Eurostat, IHPC.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "1997-01",
        "until": "2025-11",
        "rows": 347,
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
        "description": "Índice de Produção Industrial de Portugal segundo a metodologia Eurostat (NACE Rev.2, secção C — indústria transformadora). Base 2021=100, série dessazonalizada. Permite comparação directa com outros países da UE devido à harmonização metodológica. Pode divergir ligeiramente da série INE por diferenças de data de extracção e revisões Eurostat. Fonte: Eurostat, tabela STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "indústria", "europa"]
      },
      "manufacturing": {
        "label": "Indústria Transformadora (PT)",
        "description": "Índice de produção da indústria transformadora portuguesa (NACE Rev.2, secção C). Base 2021=100. Inclui todos os subsectores, de alimentos e bebidas (C10-C12) a equipamentos de transporte (C29-C30), cobrindo mais de 20 grupos de actividade. Série dessazonalizada publicada mensalmente pelo Eurostat. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "indústria", "europa"]
      },
      "total_industry": {
        "label": "Total Indústria (PT)",
        "description": "Índice de produção total da indústria portuguesa, abrangendo indústrias extractivas (NACE B), transformadoras (C), energia (D) e água/resíduos (E). Base 2021=100, série dessazonalizada. Indicador mais abrangente do que o IPI da indústria transformadora isolada. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "indústria", "europa"]
      },
      "metals": {
        "label": "Metais e Produtos Metálicos (PT)",
        "description": "Índice de produção do sector de metalurgia de base e produtos metálicos (NACE Rev.2 C24-C25). Base 2021=100. Inclui siderurgia, metalurgia de metais não ferrosos, fundição e fabricação de produtos metálicos estruturais. Sector estratégico como fornecedor de inputs à indústria automóvel, construção e maquinaria. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "metais", "indústria"]
      },
      "chemicals_pharma": {
        "label": "Química e Farmacêutica (PT)",
        "description": "Índice de produção do sector químico e farmacêutico (NACE Rev.2 C20-C21). Base 2021=100. Inclui química de base, adubos, pesticidas, tintas, plásticos em forma primária e produtos farmacêuticos. Sector com elevada intensidade tecnológica e forte componente exportadora. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "química", "indústria"]
      },
      "machinery": {
        "label": "Maquinaria e Equipamento (PT)",
        "description": "Índice de produção de máquinas e equipamentos (NACE Rev.2 C28). Base 2021=100. Inclui máquinas de uso geral, máquinas agrícolas, máquinas-ferramenta e equipamentos de elevação e manuseamento. Sector com forte componente exportadora e de incorporação tecnológica relevante para a competitividade industrial. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "maquinaria", "indústria"]
      },
      "transport_eq": {
        "label": "Equipamento de Transporte (PT)",
        "description": "Índice de produção de veículos e equipamentos de transporte (NACE Rev.2 C29-C30). Base 2021=100. Inclui automóveis de passageiros, veículos comerciais e componentes. Sector dominado pela Autoeuropa (VW) e por fornecedores Tier 1 e Tier 2, altamente exposto às cadeias de valor europeias. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "automóvel", "indústria"]
      },
      "rubber_plastics": {
        "label": "Borracha e Plásticos (PT)",
        "description": "Índice de produção do sector de borracha e plásticos (NACE Rev.2 C22). Base 2021=100. Inclui artigos de borracha (pneus, correias, vedantes) e produtos de plástico (embalagens, perfis, peças técnicas). Sector com forte integração nas cadeias de valor automóvel, construção e embalagem. Fonte: Eurostat, STS_INPR_M.",
        "unit": "Índice 2021=100",
        "frequency": "monthly",
        "lag_months": 3,
        "since": "2000-01",
        "until": "2025-10",
        "rows": 310,
        "tags": ["produção", "plásticos", "indústria"]
      },
      "inflation": {
        "label": "Inflação UE (Eurostat)",
        "description": "Taxa de inflação harmonizada (IHPC) da União Europeia (EU27) em variação homóloga (%). Medida comparável entre todos os Estados-membros, calculada segundo o regulamento harmonizado europeu. Usada pelo BCE como referência para a política monetária da zona euro. Fonte: Eurostat, série PRC_HICP_MANR.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "1997-01",
        "until": "2025-11",
        "rows": 347,
        "tags": ["inflação", "macro", "europa"]
      },
      "unemployment": {
        "label": "Desemprego Portugal (Eurostat)",
        "description": "Taxa de desemprego harmonizada de Portugal segundo a metodologia Eurostat/OIT (%). Percentagem da população activa (15-74 anos) em situação de desemprego — sem emprego, disponível e à procura activa. Comparável com todos os países da UE. Série ajustada sazonalmente. Pode diferir ligeiramente da série INE por revisões e ajustamentos Eurostat. Fonte: Eurostat, série UNE_RT_M.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
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
        "description": "Preço spot mensal médio do petróleo bruto Brent no mar do Norte (USD/barril). Principal referência europeia para o preço do petróleo, determinante nos custos de combustíveis, transporte e matérias-primas petroquímicas industriais. Cotado no ICE (Intercontinental Exchange) em Londres. Fonte: FRED, série DCOILBRENTEU (EIA/ICE).",
        "unit": "USD/bbl",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1987-05",
        "until": "2025-12",
        "rows": 463,
        "tags": ["energia", "commodities", "petróleo"]
      },
      "natural_gas": {
        "label": "Gás Natural (USD/MMBtu)",
        "description": "Preço spot mensal do gás natural no Henry Hub (Louisiana, EUA), em USD por milhão de BTU. Referência global que influencia os preços europeus via mercado de GNL. Custo crítico para indústrias energointensivas como cerâmica, vidro, papel e química. A correlação com preços europeus (TTF) aumentou significativamente após 2022. Fonte: FRED, série MHHNGSP (EIA).",
        "unit": "USD/MMBtu",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1997-01",
        "until": "2025-12",
        "rows": 348,
        "tags": ["energia", "commodities", "gás"]
      },
      "copper": {
        "label": "Cobre (USD/tonelada)",
        "description": "Preço mensal médio do cobre no mercado internacional (LME — London Metal Exchange), em USD/tonelada. Considerado um barómetro da actividade económica global pela ubiquidade do metal na construção, electrónica, telecomunicações e electrificação. Relevante para a competitividade do sector metalúrgico e cabos eléctricos. Fonte: FRED, série PCOPPUSDM (FMI).",
        "unit": "USD/t",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1990-01",
        "until": "2025-12",
        "rows": 432,
        "tags": ["commodities", "metais", "indústria"]
      },
      "aluminum": {
        "label": "Alumínio (USD/tonelada)",
        "description": "Preço mensal médio do alumínio primário no LME, em USD/tonelada. Metal base essencial para indústria automóvel, embalagens de bebidas e construção. A produção de alumínio é muito energointensiva (electrólise), tornando o seu preço muito sensível aos custos de electricidade — especialmente relevante no contexto da crise energética europeia de 2022. Fonte: FRED, série PALUMUSDM (FMI).",
        "unit": "USD/t",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1990-01",
        "until": "2025-12",
        "rows": 432,
        "tags": ["commodities", "metais", "indústria"]
      },
      "wheat": {
        "label": "Trigo (USD/bushel)",
        "description": "Preço mensal médio do trigo no mercado internacional (Chicago Board of Trade), em USD/bushel (1 bushel ≈ 27,2 kg). Input crítico para a indústria moageira, padaria e alimentação animal. A invasão da Ucrânia em 2022 demonstrou a sua importância estratégica para a segurança alimentar europeia — Ucrânia e Rússia representam ~30% das exportações globais. Fonte: FRED, série PWHEAMTUSDM (FMI).",
        "unit": "USD/bushel",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1990-01",
        "until": "2025-12",
        "rows": 432,
        "tags": ["commodities", "alimentar", "agricultura"]
      },
      "corn": {
        "label": "Milho (USD/bushel)",
        "description": "Preço mensal médio do milho no mercado internacional (Chicago Board of Trade), em USD/bushel. Usado como ração animal (suinicultura, avicultura), matéria-prima na indústria alimentar e de biocombustíveis (etanol). Relevante para os custos da indústria de alimentos compostos para animais, sector significativo em Portugal. Fonte: FRED, série PMAIZMTUSDM (FMI).",
        "unit": "USD/bushel",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1990-01",
        "until": "2025-12",
        "rows": 432,
        "tags": ["commodities", "alimentar", "agricultura"]
      },
      "coffee": {
        "label": "Café (USD/lb)",
        "description": "Preço mensal médio do café arábica no mercado internacional (ICE Futures), em USD por libra (1 lb ≈ 0,454 kg). Relevante para a indústria de torrefacção, cafés e restauração em Portugal. Portugal é um dos maiores consumidores de café per capita da Europa. Fonte: FRED, série PCOFFOTMUSDM (FMI).",
        "unit": "USD/lb",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1990-01",
        "until": "2025-12",
        "rows": 432,
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
        "description": "Taxa de juro interbancária do euro a 1 mês (%), calculada diariamente pelo EMMI (European Money Markets Institute) como média das cotações dos principais bancos europeus. Referência de curtíssimo prazo para operações financeiras e contratos de derivados. Fixada desde 2014 em terreno negativo e regressou a valores positivos em 2022 com o ciclo de subida do BCE. Fonte: Banco de Portugal / EMMI.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1999-01",
        "until": "2025-12",
        "rows": 324,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "euribor_3m": {
        "label": "Euribor 3 meses",
        "description": "Taxa de juro interbancária do euro a 3 meses (%). Principal referência para contratos de crédito à habitação a taxa variável em Portugal e para financiamento empresarial de curto prazo. A sua correlação com as decisões de política monetária do BCE é muito elevada. Subiu de -0,57% (jan. 2022) para 4,16% (set. 2023), afectando fortemente o custo do crédito variável. Fonte: Banco de Portugal / EMMI.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1999-01",
        "until": "2025-12",
        "rows": 324,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "euribor_6m": {
        "label": "Euribor 6 meses",
        "description": "Taxa de juro interbancária do euro a 6 meses (%). Usada em contratos de financiamento de médio prazo e em alguns contratos de crédito à habitação. Considerada uma medida do custo do dinheiro a prazo no mercado interbancário europeu. Fonte: Banco de Portugal / EMMI.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1999-01",
        "until": "2025-12",
        "rows": 324,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "euribor_12m": {
        "label": "Euribor 12 meses",
        "description": "Taxa de juro interbancária do euro a 12 meses (%). Principal referência para crédito à habitação e empréstimos empresariais de médio e longo prazo. Tende a antecipar as expectativas do mercado sobre a evolução da política monetária do BCE ao longo do próximo ano. Fonte: Banco de Portugal / EMMI.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1999-01",
        "until": "2025-12",
        "rows": 324,
        "tags": ["financeiro", "taxas", "euribor"]
      },
      "pt_10y": {
        "label": "Yield OT Portugal 10 anos",
        "description": "Taxa de rendibilidade (yield) das Obrigações do Tesouro portuguesas a 10 anos (%). Reflecte o custo de financiamento do Estado português a longo prazo e a percepção de risco soberano pelo mercado. Série crítica durante a crise da dívida soberana (2011-2014, máx. ~17%). Fonte: Banco de Portugal / BCE.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "2000-01",
        "until": "2025-12",
        "rows": 312,
        "tags": ["financeiro", "dívida", "yield"]
      },
      "de_10y": {
        "label": "Yield Bund Alemão 10 anos",
        "description": "Taxa de rendibilidade das obrigações do tesouro alemão (Bund) a 10 anos (%). Referência de activo de menor risco da zona euro — o benchmark contra o qual todos os outros spreads soberanos são medidos. Negativa entre 2019 e 2022, regressou a território positivo com a subida das taxas do BCE. Fonte: Banco de Portugal / BCE / Deutsche Bundesbank.",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "2000-01",
        "until": "2025-12",
        "rows": 312,
        "tags": ["financeiro", "dívida", "yield", "alemanha"]
      },
      "spread_pt_de": {
        "label": "Spread Portugal-Alemanha (10 anos)",
        "description": "Diferença entre o yield da dívida soberana portuguesa e alemã a 10 anos, em pontos base (1 p.b. = 0,01%). Mede o prémio de risco que os mercados exigem para financiar Portugal face ao benchmark alemão. Um spread elevado traduz maior percepção de risco e maior custo de financiamento. Atingiu ~1.700 p.b. em 2012 no pico da crise; situa-se tipicamente entre 50-150 p.b. em períodos de estabilidade. Fonte: Banco de Portugal / BCE.",
        "unit": "p.b.",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "2000-01",
        "until": "2025-12",
        "rows": 312,
        "tags": ["financeiro", "risco", "spread", "dívida"]
      },
      "credit_housing": {
        "label": "Crédito à Habitação",
        "description": "Stock total de crédito bancário concedido a particulares para aquisição, construção e obras de habitação em Portugal (M€). Indicador da saúde do mercado imobiliário e da exposição das famílias ao crédito hipotecário. Muito sensível às variações da Euribor, dada a elevada proporção de contratos a taxa variável em Portugal (~80%). Fonte: Banco de Portugal, BPStat, série de crédito ao sector privado não financeiro.",
        "unit": "M€",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2003-01",
        "until": "2025-10",
        "rows": 274,
        "tags": ["crédito", "habitação", "banca"]
      },
      "credit_consumer": {
        "label": "Crédito ao Consumo",
        "description": "Stock total de crédito ao consumo concedido a particulares em Portugal (M€), excluindo habitação. Inclui empréstimos pessoais, crédito automóvel e cartões de crédito. Reflecte a confiança das famílias e a capacidade de endividamento para consumo. Indicador proxy da procura interna de curto prazo. Fonte: Banco de Portugal, BPStat.",
        "unit": "M€",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2003-01",
        "until": "2025-10",
        "rows": 274,
        "tags": ["crédito", "consumo", "banca"]
      },
      "deposits": {
        "label": "Depósitos Bancários",
        "description": "Stock total de depósitos bancários de particulares e empresas residentes em Portugal (M€). Inclui depósitos à ordem e a prazo no sistema bancário. Indicador da poupança das famílias e da liquidez do sistema financeiro. O crescimento dos depósitos a prazo acelerou em 2023 com a subida das taxas do BCE. Fonte: Banco de Portugal, BPStat.",
        "unit": "M€",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "2003-01",
        "until": "2025-10",
        "rows": 274,
        "tags": ["poupança", "banca", "depósitos"]
      },
      "eur_usd": {
        "label": "Câmbio EUR/USD",
        "description": "Taxa de câmbio diária do euro face ao dólar americano, média mensal. Afecta o custo de importação de commodities cotadas em dólares (petróleo, metais, cereais) e a competitividade-preço das exportações europeias nos mercados extra-UE. A paridade EUR/USD atingiu a mínima de 0,96 em setembro de 2022. Fonte: Banco de Portugal / BCE, série EXR.M.USD.EUR.SP00.A.",
        "unit": "USD/EUR",
        "frequency": "monthly",
        "lag_months": 0,
        "since": "1999-01",
        "until": "2025-12",
        "rows": 324,
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
        "description": "Preço médio mensal da electricidade no Mercado Ibérico de Electricidade (MIBEL), em €/MWh. Referência de custo para grandes consumidores industriais em regime de mercado livre e para as tarifas reguladas. Muito sensível à disponibilidade hídrica em Portugal e Espanha, ao preço do gás natural e à produção solar/eólica na península ibérica. Fonte: REN, DataHub — Dados de mercado MIBEL/OMIE.",
        "unit": "EUR/MWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-07",
        "until": "2025-11",
        "rows": 221,
        "tags": ["energia", "electricidade", "preço", "mibel"]
      },
      "electricity_hydro": {
        "label": "Produção Hídrica (GWh)",
        "description": "Produção mensal de electricidade a partir de centrais hidroeléctricas em Portugal Continental, em GWh. Fonte renovável dominante e variável por excelência — determinada pela precipitação e gestão dos aproveitamentos hidroeléctricos. Anos hidrológicos secos reduzem substancialmente esta produção, pressionando o preço MIBEL e aumentando o uso de gás natural. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "electricidade", "hídrica", "renovável"]
      },
      "electricity_wind": {
        "label": "Produção Eólica (GWh)",
        "description": "Produção mensal de electricidade a partir de parques eólicos em Portugal Continental, em GWh. Portugal tem uma das maiores capacidades instaladas de energia eólica per capita da Europa (~6 GW em 2025). Série em crescimento desde 2005 com a expansão do parque eólico nacional. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "electricidade", "eólica", "renovável"]
      },
      "electricity_solar": {
        "label": "Produção Solar FV (GWh)",
        "description": "Produção mensal de electricidade a partir de painéis fotovoltaicos em Portugal Continental, em GWh. Capacidade instalada em crescimento acelerado desde 2022 com os grandes projectos solares (leilões renováveis). Portugal beneficia de ~2.300 horas de sol por ano — das maiores irradiâncias da Europa. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2010-01",
        "until": "2025-11",
        "rows": 191,
        "tags": ["energia", "electricidade", "solar", "renovável"]
      },
      "electricity_natural_gas": {
        "label": "Produção Gás Natural (GWh)",
        "description": "Produção de electricidade em centrais termoeléctricas a gás natural de ciclo combinado em Portugal Continental, em GWh. Funciona como backup gerível às fontes renováveis variáveis. A produção termoeléctrica a gás aumenta em anos secos ou com baixa produção eólica, pressionando o preço no MIBEL e aumentando as emissões de CO₂ do sector eléctrico. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "electricidade", "gás", "térmica"]
      },
      "electricity_biomass": {
        "label": "Produção Biomassa (GWh)",
        "description": "Produção de electricidade a partir de biomassa florestal e resíduos agrícolas em Portugal Continental, em GWh. Fonte renovável gerível, importante para a regulação do sistema eléctrico em períodos de baixa hídrica e eólica. Limitada pela disponibilidade sustentável de biomassa florestal. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "electricidade", "biomassa", "renovável"]
      },
      "electricity_consumption": {
        "label": "Consumo Eléctrico Nacional (GWh)",
        "description": "Consumo total de electricidade em Portugal Continental, em GWh. Indicador proxy da actividade económica — especialmente sensível à produção industrial, temperatura (ar condicionado/aquecimento) e estrutura da economia. A electrificação crescente do transporte e aquecimento aumentará esta série nas próximas décadas. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "electricidade", "consumo"]
      },
      "electricity_production_total": {
        "label": "Produção Eléctrica Total (GWh)",
        "description": "Produção total bruta de electricidade em Portugal Continental, em GWh, somando todas as fontes (hídrica, eólica, solar, biomassa, gás natural, carvão, outros). Indicador da capacidade produtiva nacional antes do saldo de importações/exportações com Espanha. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "electricidade", "produção"]
      },
      "electricity_production_renewable": {
        "label": "Produção Renovável (GWh)",
        "description": "Produção de electricidade a partir de fontes renováveis (hídrica, eólica, solar fotovoltaico, biomassa, ondas) em Portugal Continental, em GWh. Portugal tem como meta 85% de electricidade de origem renovável em 2030, coerente com o Plano Nacional de Energia e Clima (PNEC). A quota renovável anual superou 60% em vários anos recentes. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
        "tags": ["energia", "renovável", "electricidade"]
      },
      "electricity_net_imports": {
        "label": "Importações Líquidas (GWh)",
        "description": "Saldo líquido de electricidade importada menos exportada via interligações de alta tensão com Espanha, em GWh. Positivo = Portugal é importador líquido; negativo = exportador líquido. Reflecte o grau de autossuficiência eléctrica e a integração no mercado ibérico. Em anos hidrológicos muito secos, Portugal pode ser importador líquido significativo. Fonte: REN, DataHub — Balanço de energia eléctrica.",
        "unit": "GWh",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2007-01",
        "until": "2025-11",
        "rows": 227,
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
        "description": "Composite Leading Indicator (CLI) da OCDE para Portugal. Indicador composto que antecipa as inflexões do ciclo económico com 6-9 meses de antecedência, construído a partir de várias séries (confiança empresarial, bolsa, licenças de construção, encomendas, entre outras). Normalizado com média de longo prazo = 100. Valores acima de 100 e crescentes indicam expansão acima da tendência; abaixo e decrescentes indicam abrandamento. Fonte: OCDE, MEI (Main Economic Indicators).",
        "unit": "Índice",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "1975-01",
        "until": "2025-10",
        "rows": 610,
        "tags": ["conjuntura", "avançado", "ciclo"]
      },
      "production": {
        "label": "Perspectivas de Produção (BTS)",
        "description": "Resposta dos empresários industriais portugueses sobre as perspectivas de produção nos próximos 3 meses (Business Tendency Survey — BTS). Saldo de respostas positivas menos negativas (%). Indicador avançado da actividade industrial, parte do inquérito harmonizado da Comissão Europeia. Fonte: OCDE / Comissão Europeia, BTS Portugal.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["confiança", "expectativas", "produção"]
      },
      "order_books": {
        "label": "Carteira de Encomendas (BTS)",
        "description": "Avaliação dos empresários industriais portugueses sobre a adequação da carteira de encomendas actual face ao normal sazonal, em saldo de respostas. Indicador avançado da actividade futura — uma carteira abaixo do normal antecipa redução de produção nos meses seguintes. Parte do inquérito harmonizado da Comissão Europeia. Fonte: OCDE / Comissão Europeia, BTS Portugal.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["confiança", "encomendas", "expectativas"]
      },
      "selling_prices": {
        "label": "Perspectivas de Preços de Venda (BTS)",
        "description": "Intenções dos empresários industriais portugueses quanto à evolução dos preços de venda a 3 meses, em saldo de respostas (Business Tendency Survey). Indicador avançado das pressões inflacionistas de origem industrial. Correlaciona com o índice de preços na produção (IPP). Fonte: OCDE / Comissão Europeia, BTS Portugal.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["preços", "inflação", "expectativas"]
      },
      "employment": {
        "label": "Perspectivas de Emprego (BTS)",
        "description": "Intenções dos empresários industriais portugueses quanto à evolução do emprego nos próximos 3 meses, em saldo de respostas (Business Tendency Survey). Avança tendências do mercado de trabalho industrial com 1-3 meses de antecedência. Complementa o indicador de emprego efectivo do INE. Fonte: OCDE / Comissão Europeia, BTS Portugal.",
        "unit": "Saldo",
        "frequency": "monthly",
        "lag_months": 1,
        "since": "2000-01",
        "until": "2025-11",
        "rows": 311,
        "tags": ["emprego", "expectativas", "trabalho"]
      },
      "unemp_m": {
        "label": "Taxa de Desemprego (OCDE)",
        "description": "Taxa de desemprego harmonizada da OCDE para Portugal (%), calculada segundo a metodologia OIT. Comparável com outros países membros da organização e com a série Eurostat. Pode apresentar pequenas divergências face à série INE devido a diferenças de base de dados e revisões. Fonte: OCDE, Main Economic Indicators (MEI).",
        "unit": "%",
        "frequency": "monthly",
        "lag_months": 2,
        "since": "1983-01",
        "until": "2025-10",
        "rows": 514,
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
      "gross_production_total":           {"label": "Produção Bruta Total (GWh)",                        "description": "Produção bruta total de electricidade em Portugal Continental, em GWh, incluindo todas as fontes de geração. Corresponde à electricidade gerada nos terminais dos geradores, antes da dedução do consumo nos serviços auxiliares das centrais. Fonte: DGEG, Renováveis — Estatísticas Rápidas.",                                                                                                               "unit": "GWh",       "frequency": "monthly",   "since": "2010-01", "until": "2025-11", "rows": 191, "tags": ["energia", "electricidade", "produção"]},
      "gross_production_wind":            {"label": "Produção Eólica Bruta (GWh)",                       "description": "Produção bruta de electricidade a partir de energia eólica em Portugal Continental, em GWh. Inclui toda a potência instalada em regime especial. Série em crescimento desde os leilões de capacidade renovável. Fonte: DGEG, Renováveis — Estatísticas Rápidas.",                                                                                                                                  "unit": "GWh",       "frequency": "monthly",   "since": "2010-01", "until": "2025-11", "rows": 191, "tags": ["energia", "eólica", "renovável"]},
      "gross_production_hydro":           {"label": "Produção Hídrica Bruta (GWh)",                      "description": "Produção bruta de electricidade em centrais hidroeléctricas de Portugal Continental, em GWh. Inclui grandes hídricos com e sem bombagem, e minihídrica. Série com elevada variabilidade inter-anual devido à pluviosidade. Fonte: DGEG, Renováveis — Estatísticas Rápidas.",                                                                                                                  "unit": "GWh",       "frequency": "monthly",   "since": "2010-01", "until": "2025-11", "rows": 191, "tags": ["energia", "hídrica", "renovável"]},
      "gross_production_solar_pv":        {"label": "Produção Solar FV Bruta (GWh)",                     "description": "Produção bruta de electricidade em instalações fotovoltaicas em Portugal Continental, em GWh. Inclui produção em regime especial (autoconsumo injectado na rede + produção em centrais FV). Crescimento acelerado a partir de 2022 com os grandes projectos dos leilões renováveis. Fonte: DGEG, Renováveis — Estatísticas Rápidas.",                                                            "unit": "GWh",       "frequency": "monthly",   "since": "2012-01", "until": "2025-11", "rows": 167, "tags": ["energia", "solar", "renovável"]},
      "total_consumption":                {"label": "Consumo Total Electricidade (GWh)",                  "description": "Consumo total de electricidade em Portugal Continental, em GWh, incluindo perdas na rede de transporte e distribuição. Indicador macro da actividade económica e dos padrões de consumo de energia. Fonte: DGEG, Balanço Energético.",                                                                                                                                                            "unit": "GWh",       "frequency": "monthly",   "since": "2010-01", "until": "2025-11", "rows": 191, "tags": ["energia", "electricidade", "consumo"]},
      "net_imports":                      {"label": "Importações Líquidas (GWh)",                         "description": "Saldo líquido de electricidade importada via interligações com Espanha (importações − exportações), em GWh. Positivo indica que Portugal importou mais do que exportou no período. Dado complementar da DGEG ao publicado pela REN. Fonte: DGEG, Balanço Energético.",                                                                                                                        "unit": "GWh",       "frequency": "monthly",   "since": "2010-01", "until": "2025-11", "rows": 191, "tags": ["energia", "importação"]},
      "energy_dependence":                {"label": "Dependência Energética (%)",                         "description": "Percentagem das necessidades energéticas brutas de Portugal satisfeita por importações de energia (carvão, petróleo, gás natural, nuclear). Portugal tem dependência estruturalmente elevada — tipicamente 75-80% — dada a escassez de recursos fósseis nacionais. A expansão renovável reduz esta dependência mas o petróleo para transportes mantém-na elevada. Frequência anual com desfasamento de 12-18 meses. Fonte: DGEG, Balanço Energético.",                                 "unit": "%",         "frequency": "annual",    "since": "2000-01", "until": "2024-01", "rows": 25, "tags": ["energia", "dependência", "estratégico"]},
      "renewable_share_electricity":      {"label": "Quota Renovável Electricidade (%)",                  "description": "Percentagem da electricidade produzida a partir de fontes renováveis (hídrica, eólica, solar, biomassa, ondas, geotermia) face ao total do consumo. Portugal tem como meta 85% em 2030 (PNEC). A quota superou 60% em múltiplos anos, chegando a 100% em momentos pontuais. Frequência anual. Fonte: DGEG, Balanço Energético / Renováveis Estatísticas Rápidas.",                              "unit": "%",         "frequency": "annual",    "since": "2000-01", "until": "2024-01", "rows": 25, "tags": ["energia", "renovável", "metas"]},
      "renewable_share_total":            {"label": "Quota Renovável Total (%)",                          "description": "Percentagem do consumo final bruto de energia proveniente de fontes renováveis, nos termos da Directiva (UE) 2018/2001 (RED II). Inclui electricidade renovável, calor e frio renovável, e energia renovável nos transportes. Meta nacional: 47% em 2030. Frequência anual com desfasamento de 12-18 meses. Fonte: DGEG / Eurostat, tabela NRG_IND_REN.",                                      "unit": "%",         "frequency": "annual",    "since": "2004-01", "until": "2024-01", "rows": 21, "tags": ["energia", "renovável", "metas"]},
      "energy_intensity":                 {"label": "Intensidade Energética (tep/M€)",                   "description": "Quantidade de energia primária consumida por unidade de PIB (tep por milhão de euros de PIB a preços constantes). Mede a eficiência energética da economia — quanto menor, mais eficiente. Portugal melhorou este indicador significativamente desde 2005, mas ainda se situa acima da média da UE. Frequência anual com desfasamento de 12-18 meses. Fonte: DGEG, Balanço Energético.",     "unit": "tep/M€",    "frequency": "annual",    "since": "2000-01", "until": "2024-01", "rows": 25, "tags": ["eficiência", "energia", "macro"]},
      "co2_emissions_total":              {"label": "Emissões CO₂ Totais (Mton)",                        "description": "Emissões totais de CO₂ equivalente pelo sector energético em Portugal (Mton CO₂e). Inclui emissões da combustão de combustíveis fósseis para electricidade, calor industrial e transportes. Portugal tem compromissos de redução de 55% até 2030 (face a 1990) no âmbito do Green Deal europeu. Frequência anual. Fonte: DGEG / APA, Inventário Nacional de Emissões de GEE.",           "unit": "Mton CO2e", "frequency": "annual",    "since": "2000-01", "until": "2023-01", "rows": 24, "tags": ["emissões", "clima", "ambiente"]},
      "price_diesel":                     {"label": "Preço Gasóleo (€/l)",                               "description": "Preço médio semanal do gasóleo rodoviário em Portugal (€/l), correspondente ao preço de venda ao público (PVP) incluindo todos os impostos (ISP, IVA, CSR). Custo operacional crítico para transporte rodoviário de mercadorias e logística industrial. Actualizado semanalmente pela DGEG com dados do boletim de combustíveis. Fonte: DGEG, Preços dos Combustíveis Semanais.",          "unit": "€/l",       "frequency": "weekly",    "since": "2005-01", "until": "2025-12", "rows": 1095, "tags": ["combustível", "preço", "transporte"]},
      "price_gasoline_95_pvp":            {"label": "Preço Gasolina 95 (€/l)",                           "description": "Preço médio semanal da gasolina sem chumbo 95 em Portugal (€/l), preço de venda ao público (PVP) incluindo todos os impostos (ISP, IVA, CSR). Referência para o custo dos transportes particulares e de frotas ligeiras. Actualizado semanalmente pela DGEG. Fonte: DGEG, Preços dos Combustíveis Semanais.",                                                                                  "unit": "€/l",       "frequency": "weekly",    "since": "2005-01", "until": "2025-12", "rows": 1095, "tags": ["combustível", "preço"]},
      "natgas_price_industry_€_per_MWh": {"label": "Preço Gás Natural Indústria (€/MWh)",               "description": "Preço semestral do gás natural para consumidores industriais em Portugal na banda de consumo I3 (10.000–100.000 GJ/ano), em €/MWh, incluindo todos os impostos e taxas. Comparável com as médias publicadas pelo Eurostat para os países da UE (série NRG_PC_203). Frequência semestral — dois valores por ano (S1 e S2). Fonte: DGEG, Estatísticas dos Preços da Energia.",              "unit": "€/MWh",     "frequency": "semester",  "since": "2008-01", "until": "2025-07", "rows": 36, "tags": ["gás", "energia", "indústria", "preço"]},
      "industrial_band_ic_incl_taxes":   {"label": "Preço Electricidade Industrial Banda IC (€/kWh)",   "description": "Preço da electricidade para consumidores industriais na banda IC (500–2.000 MWh/ano), em €/kWh, incluindo todos os impostos, taxas e encargos da rede. Banda mais representativa das PME industriais portuguesas. Publicado semestralmente pela DGEG em linha com o inquérito harmonizado Eurostat (série NRG_PC_205). Fonte: DGEG, Estatísticas dos Preços da Energia.",                       "unit": "€/kWh",     "frequency": "semester",  "since": "2008-01", "until": "2025-07", "rows": 36, "tags": ["electricidade", "preço", "indústria"]},
      "brent_usd":                        {"label": "Petróleo Brent (USD/barril) — DGEG",                "description": "Preço mensal do petróleo Brent em USD/barril segundo a recolha da DGEG para efeitos de cálculo de preços de combustíveis e indicadores energéticos nacionais. Comparável com a série FRED/EIA. Fonte: DGEG, Estatísticas de Energia — Preços Internacionais.",                                                                                                                             "unit": "USD/bbl",   "frequency": "monthly",   "since": "2005-01", "until": "2025-11", "rows": 251, "tags": ["petróleo", "commodities", "energia"]}
    }
  },
  "ERSE": {
    "label": "ERSE — Entidade Reguladora dos Serviços Energéticos",
    "description": "Regulador dos sectores do gás natural e da electricidade. Publica as tarifas reguladas de acesso às redes eléctricas por nível de tensão e período tarifário.",
    "url": "https://www.erse.pt",
    "note": "Tarifas semestrais (ou anuais) por nível de tensão: MAT (Muito Alta Tensão), AT (Alta Tensão), MT (Média Tensão), BTE (Baixa Tensão Especial), BTN (Baixa Tensão Normal).",
    "indicators": {
      "tariff_mt_peak":     {"label": "Tarifa MT — Ponta (€/kWh)",        "description": "Tarifa de acesso à rede eléctrica em Média Tensão (MT) no período de ponta horária, em €/kWh. Aplicável a consumidores industriais e comerciais com potência contratada superior a 41,4 kVA. A tarifa de acesso à rede é a componente regulada do preço da electricidade — aprovada anualmente pela ERSE, independente do preço de energia em mercado. Publicada anualmente antes do início do período tarifário (geralmente Janeiro). Fonte: ERSE, Tarifas e Preços para a Energia Eléctrica.", "unit": "€/kWh", "frequency": "annual", "since": "2010-01", "until": "2025-01", "rows": 16, "tags": ["electricidade", "tarifa", "indústria", "MT"]},
      "tariff_mt_off_peak": {"label": "Tarifa MT — Vazio (€/kWh)",        "description": "Tarifa de acesso à rede eléctrica em Média Tensão (MT) no período de vazio (horas de menor consumo, geralmente nocturno e fim-de-semana), em €/kWh. Tipicamente inferior à tarifa de ponta, incentivando o deslocamento de consumo industrial para períodos de menor carga no sistema eléctrico. Fonte: ERSE, Tarifas e Preços para a Energia Eléctrica.",                                                                                                                                                                                                                                              "unit": "€/kWh", "frequency": "annual", "since": "2010-01", "until": "2025-01", "rows": 16, "tags": ["electricidade", "tarifa", "indústria", "MT"]},
      "tariff_at_peak":     {"label": "Tarifa AT — Ponta (€/kWh)",        "description": "Tarifa de acesso à rede eléctrica em Alta Tensão (AT, 1-45 kV) no período de ponta, em €/kWh. Aplicável a grandes consumidores industriais com potências elevadas, como indústrias siderúrgicas, cimenteiras, refinarias e grandes complexos industriais. Tarifa regulada anualmente pela ERSE. Fonte: ERSE, Tarifas e Preços para a Energia Eléctrica.",                                                                                                                                                                                                                                                    "unit": "€/kWh", "frequency": "annual", "since": "2010-01", "until": "2025-01", "rows": 16, "tags": ["electricidade", "tarifa", "indústria", "AT"]},
      "tariff_mat_peak":    {"label": "Tarifa MAT — Ponta (€/kWh)",       "description": "Tarifa de acesso à rede eléctrica em Muito Alta Tensão (MAT, >45 kV) no período de ponta, em €/kWh. Aplicável a grandes indústrias energointensivas com ligação directa à rede de transporte nacional (RNT), como fundições, electroquímica e grandes complexos industriais. É a tarifa de rede mais baixa por kWh, dado o volume de consumo. Fonte: ERSE, Tarifas e Preços para a Energia Eléctrica.",                                                                                                                                                                                               "unit": "€/kWh", "frequency": "annual", "since": "2010-01", "until": "2025-01", "rows": 16, "tags": ["electricidade", "tarifa", "indústria", "MAT"]},
      "btn_simple":         {"label": "Tarifa BTN Simples (€/kWh)",       "description": "Tarifa de energia em Baixa Tensão Normal (BTN) para consumidores sem discriminação horária, em €/kWh. Aplicável a pequenas empresas, comércio e serviços com potência contratada ≤41,4 kVA. Referência para o custo da electricidade das PME e do sector de serviços. Publicada anualmente pela ERSE. Fonte: ERSE, Tarifas e Preços para a Energia Eléctrica.",                                                                                                                                                                                                                                         "unit": "€/kWh", "frequency": "annual", "since": "2010-01", "until": "2025-01", "rows": 16, "tags": ["electricidade", "tarifa", "PME", "BTN"]}
    }
  },
  "WORLDBANK": {
    "label": "Banco Mundial",
    "url": "https://data.worldbank.org",
    "description": "Indicadores de desenvolvimento mundial — dados anuais sobre estrutura económica, inovação e demografia.",
    "indicators": {
      "birth_rate": {
        "label": "Taxa de Natalidade",
        "unit": "nascimentos por 1.000 habitantes",
        "description": "Número de nascimentos vivos por 1.000 habitantes no ano, Portugal. Indicador demográfico fundamental para análise de tendências populacionais de longo prazo. Portugal tem uma das taxas de natalidade mais baixas da UE, com implicações para o mercado de trabalho, sustentabilidade da Segurança Social e crescimento potencial. Frequência anual com desfasamento de 12-24 meses. Fonte: Banco Mundial, indicador SP.DYN.CBRT.IN (UNDESA).",
        "frequency": "annual",
        "since": "1960-01",
        "until": "2023-01",
        "rows": 64,
        "source_url": "https://data.worldbank.org/indicator/SP.DYN.CBRT.IN",
      },
      "rnd_pct_gdp": {
        "label": "I&D (% do PIB)",
        "unit": "% do PIB",
        "description": "Despesa bruta em Investigação e Desenvolvimento (I&D) como percentagem do PIB, Portugal. Inclui I&D realizado pelo sector empresarial, ensino superior, Estado e organizações privadas sem fins lucrativos. Portugal tem como meta 3% do PIB em I&D (Agenda de Competitividade). Frequência anual com desfasamento de 18-24 meses. Fonte: Banco Mundial, indicador GB.XPD.RSDV.GD.ZS (UNESCO/OCDE).",
        "frequency": "annual",
        "since": "2000-01",
        "until": "2022-01",
        "rows": 23,
        "source_url": "https://data.worldbank.org/indicator/GB.XPD.RSDV.GD.ZS",
      },
      "fdi_inflows_pct_gdp": {
        "label": "Investimento Directo Estrangeiro — Entradas",
        "unit": "% do PIB",
        "description": "Fluxos de Investimento Directo Estrangeiro (IDE) recebidos por Portugal como percentagem do PIB. Mede a atractividade de Portugal para investidores internacionais. Indicador muito volátil ano a ano devido a operações societárias de grande dimensão. Frequência anual. Fonte: Banco Mundial, indicador BX.KLT.DINV.WD.GD.ZS (UNCTAD / Banco de Portugal).",
        "frequency": "annual",
        "since": "1970-01",
        "until": "2023-01",
        "rows": 54,
        "source_url": "https://data.worldbank.org/indicator/BX.KLT.DINV.WD.GD.ZS",
      },
      "gdp_per_capita_ppp": {
        "label": "PIB per capita (PPC)",
        "unit": "USD (2017)",
        "description": "PIB per capita de Portugal em Paridade de Poder de Compra (PPC), dólares internacionais constantes de 2017. Permite comparação real entre países eliminando diferenças de nível de preços e câmbios nominais. Em PPC, Portugal situa-se a ~80% da média da UE — divergência relevante mas menos acentuada do que em euros correntes. Frequência anual. Fonte: Banco Mundial, indicador NY.GDP.PCAP.PP.KD (ICP/FMI).",
        "frequency": "annual",
        "since": "1990-01",
        "until": "2023-01",
        "rows": 34,
        "source_url": "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD",
        "tags": ["pib", "macro", "comparação", "convergência"],
      },
    },
  },
}
