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

V9 changes:
  - EXPLAIN dict: plain-language "what this means for you" for all 36 KPIs
  - _contextual_annotation(): value-range annotations for ~20 key indicators
  - painel_kpi() passes explain + auto-computes annotation
"""

from .resumo import resumo_kpi

# ── Plain-language explanations for citizens ──────────────────────────
# Written for a Portuguese citizen with no economics training.
# Each entry: 1-2 sentences, concrete examples, relatable language.

EXPLAIN = {
    # Custo de Vida
    "inflation":       "Quando a inflação sobe, o mesmo salário compra menos. Se está em 2.3%, um cabaz de 500\u20ac em janeiro custa agora 511.50\u20ac em dezembro.",
    "diesel":          "O preço do gasóleo afecta tudo \u2014 do pão ao transporte. Quando sobe, os preços de quase tudo sobem também.",
    "gasoline_95":     "A gasolina que abastece no posto. Se gasta 50\u20ac por depósito, uma subida de 10% são mais 5\u20ac por semana.",
    "electricity_btn": "A tarifa da sua conta da luz em casa. Se sobe, paga mais no final do mês mesmo gastando o mesmo.",
    "electricity_mt":  "Tarifa para fábricas e comércios médios. Quando sobe, os custos de produção aumentam e os preços podem subir para o consumidor.",
    "electricity_at":  "Tarifa para as maiores indústrias do país. Afecta o custo de produção de aço, vidro, cerâmica e outros sectores pesados.",
    "euribor_3m":      "A Euribor 3 meses é a taxa que os bancos usam para calcular a prestação da casa. Se tem crédito a taxa variável, quando esta sobe, a sua prestação mensal sobe.",
    "euribor_6m":      "Semelhante à Euribor 3m, mas para créditos com revisão semestral. Muda a cada 6 meses \u2014 se tem este tipo de crédito, a sua prestação ajusta duas vezes por ano.",
    "euribor_12m":     "Para créditos com revisão anual. A sua prestação só muda uma vez por ano, mas a variação pode ser maior de cada vez.",
    # Indústria
    "ipi_total":       "Mede se as fábricas portuguesas estão a produzir mais ou menos. Quando sobe, há mais actividade, mais emprego e mais exportações.",
    "ipi_cae_10":      "A indústria alimentar é o maior sector industrial de Portugal. Se cai, pode significar menos oferta e preços mais altos no supermercado.",
    "ipi_cae_20":      "A indústria química faz tintas, plásticos e fertilizantes. É um termómetro da saúde de outras indústrias que dependem destes materiais.",
    "ipi_cae_24":      "Metalurgia de base \u2014 o aço e alumínio usados na construção civil e na indústria. Se cai, pode sinalizar menos obras e menos investimento.",
    "ipi_cae_25":      "Estruturas metálicas, ferramentas e componentes. É o que transforma o metal bruto em peças úteis para a construção e a indústria.",
    "ipi_cae_28":      "Máquinas e equipamentos para fábricas. Se as empresas compram mais máquinas, estão a investir no futuro \u2014 bom sinal para a economia.",
    "ipi_cae_29":      "A produção de automóveis (Autoeuropa, Caetano Bus) é uma das maiores exportações de Portugal. Quando sobe, entra mais dinheiro no país.",
    "copper":          "O cobre é usado em tudo, de cabos eléctricos a telemóveis. O seu preço é considerado um barómetro da economia mundial.",
    "aluminum":        "O alumínio está em latas, janelas, carros e aviões. Quando o preço sobe, os produtos que o usam ficam mais caros.",
    # Emprego
    "unemployment":           "A percentagem de pessoas que querem trabalhar mas não encontram emprego. Quanto mais baixa, melhor para as famílias.",
    "industrial_employment":  "Quantas pessoas trabalham nas fábricas portuguesas. Se sobe, a indústria está a contratar; se desce, está a cortar postos.",
    "wages_industry":         "Quanto ganham em média os trabalhadores da indústria. Note que este valor não desconta a inflação \u2014 se os preços sobem mais que os salários, perde-se poder de compra.",
    # Conjuntura
    "cli":         "Um indicador que tenta prever se a economia vai melhorar ou piorar nos próximos 6 meses. Acima de 100 sugere crescimento à frente.",
    "confidence":  "Pergunta-se aos donos de fábricas se estão optimistas ou pessimistas. Abaixo de zero, a maioria está pessimista \u2014 mau sinal para investimento e emprego.",
    "order_books": "As encomendas que as fábricas têm em carteira. Mais encomendas hoje significam mais produção e mais emprego nos próximos meses.",
    # Energia
    "energy_cost":       "O preço grossista da electricidade no mercado ibérico. Quando sobe, as tarifas industriais e eventualmente as domésticas tendem a seguir.",
    "renewable_share":   "Que parte da electricidade vem do sol, vento e água. Quanto mais alta, menos dependemos de combustíveis importados e menos CO2 emitimos.",
    "energy_dependence": "Que percentagem da energia que consumimos vem do estrangeiro. Quanto maior, mais vulneráveis ficamos a crises de preços internacionais.",
    "natural_gas":       "O gás natural aquece casas, alimenta fábricas de vidro e cerâmica, e produz electricidade. Quando o preço sobe, toda a cadeia de custos sobe.",
    "solar":             "Quanta electricidade solar entrou na rede. Mais solar significa menos importação de gás e petróleo, e contas de luz potencialmente mais baixas.",
    "wind":              "Quanta electricidade os parques eólicos injectaram na rede. Portugal é um dos países europeus com mais vento aproveitável.",
    # Externo
    "eur_usd":      "Quando o euro sobe face ao dólar, as importações dos EUA ficam mais baratas, mas as nossas exportações ficam mais caras para americanos.",
    "spread_pt_de": "Mede quanto mais Portugal paga de juros que a Alemanha. Quanto maior, mais os mercados consideram Portugal um risco \u2014 e mais cara fica a dívida pública.",
    "brent":        "O preço do barril de petróleo. Afecta directamente o que paga no gasóleo, na gasolina e no transporte de tudo o que compra.",
    # Competitividade
    "gdp_per_capita":  "A riqueza média produzida por cada habitante. Portugal está ainda abaixo da média europeia \u2014 fechar este fosso é o grande desafio de longo prazo.",
    "rnd_pct_gdp":     "Quanto o país investe em investigação e inovação. Mais investimento hoje significa melhores empregos e produtos mais competitivos amanhã.",
    "employment_rate": "A percentagem de adultos (20-64) que têm emprego. Quanto mais alta, mais pessoas contribuem para a economia e para a Segurança Social.",
}


def _contextual_annotation(kpi_id, value, sentiment):
    """Generate contextual annotation based on value ranges.

    Returns a short, plain-language note about what the current value means,
    or None if no annotation applies.
    """
    if value is None:
        return None

    # ── Custo de Vida ──────────────────────────────────────────────
    if kpi_id == "inflation":
        if value < 0:
            return "Deflação \u2014 os preços estão a descer (raro e nem sempre bom)."
        if value < 1:
            return "Preços praticamente estáveis."
        if value < 2:
            return "Dentro da meta do BCE (2%)."
        if value < 4:
            return "Acima da meta \u2014 poder de compra a descer."
        return "Inflação alta \u2014 pressão significativa nas famílias."

    if kpi_id == "diesel":
        if value < 1.30:
            return "Gasóleo barato \u2014 abaixo de 1.30\u20ac/L."
        if value < 1.55:
            return "Gasóleo em zona moderada."
        if value < 1.80:
            return "Gasóleo caro \u2014 pesa no transporte e nos preços."
        return "Gasóleo muito caro \u2014 impacto forte nos custos."

    if kpi_id == "gasoline_95":
        if value < 1.40:
            return "Gasolina barata \u2014 abaixo de 1.40\u20ac/L."
        if value < 1.65:
            return "Gasolina em zona moderada."
        if value < 1.90:
            return "Gasolina cara \u2014 cada depósito pesa mais."
        return "Gasolina muito cara \u2014 impacto forte na mobilidade."

    if kpi_id == "euribor_3m":
        if value < 0:
            return "Taxa negativa \u2014 cenário raro, bom para quem tem crédito."
        if value < 1:
            return "Taxa baixa \u2014 prestações da casa em mínimos."
        if value < 2.5:
            return "Taxa moderada \u2014 prestações a subir para muitas famílias."
        if value < 4:
            return "Taxa elevada \u2014 prestações da casa pesam no orçamento."
        return "Taxa muito elevada \u2014 pressão forte sobre devedores."

    # ── Emprego ────────────────────────────────────────────────────
    if kpi_id == "unemployment":
        if value < 5:
            return "Pleno emprego \u2014 mercado de trabalho muito apertado."
        if value < 7:
            return "Desemprego baixo \u2014 bom para os trabalhadores."
        if value < 10:
            return "Desemprego moderado \u2014 ainda há margem de melhoria."
        return "Desemprego alto \u2014 muitas famílias afectadas."

    if kpi_id == "employment_rate":
        if value > 78:
            return "Taxa elevada \u2014 acima da média da UE."
        if value > 73:
            return "Taxa razoável \u2014 próxima da média europeia."
        if value > 68:
            return "Taxa abaixo da média da UE \u2014 margem para melhorar."
        return "Taxa baixa \u2014 muitos adultos fora do mercado de trabalho."

    # ── Conjuntura ─────────────────────────────────────────────────
    if kpi_id == "cli":
        if value > 101:
            return "Acima de 101 \u2014 forte sinal de expansão económica à frente."
        if value > 100:
            return "Acima de 100 \u2014 expansão económica provável."
        if value > 99:
            return "Ligeiramente abaixo de 100 \u2014 abrandamento possível."
        return "Abaixo de 99 \u2014 sinal de contracção económica à frente."

    if kpi_id == "confidence":
        if value > 5:
            return "Confiança elevada \u2014 industriais optimistas."
        if value > 0:
            return "Confiança ligeiramente positiva."
        if value > -10:
            return "Pessimismo ligeiro entre os industriais."
        return "Pessimismo acentuado \u2014 empresas retraem investimento."

    if kpi_id == "order_books":
        if value > 0:
            return "Encomendas acima do normal \u2014 produção futura assegurada."
        if value > -15:
            return "Encomendas ligeiramente abaixo do normal."
        if value > -30:
            return "Carteira fraca \u2014 produção pode abrandar."
        return "Encomendas muito fracas \u2014 sinal de recessão industrial."

    # ── Energia ────────────────────────────────────────────────────
    if kpi_id == "renewable_share":
        if value > 70:
            return "Excelente \u2014 mais de 70% renovável, entre os melhores da Europa."
        if value > 50:
            return "Boa quota renovável \u2014 acima de metade da produção."
        if value > 30:
            return "Quota moderada \u2014 ainda muito dependente de fósseis."
        return "Quota baixa de renováveis \u2014 forte dependência de importações."

    if kpi_id == "energy_dependence":
        if value < 60:
            return "Dependência relativamente baixa para Portugal."
        if value < 75:
            return "Dependência moderada \u2014 nível típico de Portugal."
        if value < 85:
            return "Dependência elevada \u2014 vulnerável a choques de preços."
        return "Dependência muito elevada \u2014 risco estratégico."

    if kpi_id == "natural_gas":
        if value < 2:
            return "Gás barato \u2014 bom para indústrias energo-intensivas."
        if value < 4:
            return "Gás em zona moderada."
        if value < 7:
            return "Gás caro \u2014 pressão nos custos industriais."
        return "Gás muito caro \u2014 impacto severo nas fábricas de vidro, cerâmica e metalurgia."

    # ── Externo ────────────────────────────────────────────────────
    if kpi_id == "spread_pt_de":
        if value < 0.5:
            return "Spread muito baixo \u2014 mercados confiam em Portugal."
        if value < 1.0:
            return "Spread contido \u2014 percepção de risco baixa."
        if value < 2.0:
            return "Spread moderado \u2014 alguma cautela dos mercados."
        return "Spread elevado \u2014 custo de financiamento do Estado a subir."

    if kpi_id == "brent":
        if value < 50:
            return "Petróleo barato \u2014 bom para importadores como Portugal."
        if value < 75:
            return "Petróleo em zona moderada."
        if value < 100:
            return "Petróleo caro \u2014 pressão nos combustíveis e transportes."
        return "Petróleo muito caro \u2014 impacto generalizado nos preços."

    if kpi_id == "eur_usd":
        if value > 1.20:
            return "Euro forte \u2014 importações mais baratas, exportações menos competitivas."
        if value > 1.05:
            return "Euro/Dólar em zona de equilíbrio."
        if value > 0.95:
            return "Euro fraco \u2014 exportações mais competitivas, importações mais caras."
        return "Euro muito fraco \u2014 energia e matérias-primas (cotadas em USD) ficam caras."

    # ── Indústria ──────────────────────────────────────────────────
    if kpi_id == "ipi_total":
        if value > 105:
            return "Produção acima da base (2021) \u2014 indústria em expansão."
        if value > 95:
            return "Produção próxima da base \u2014 indústria estável."
        if value > 85:
            return "Produção abaixo da base \u2014 contracção moderada."
        return "Produção muito abaixo da base \u2014 contracção industrial forte."

    # ── Competitividade ────────────────────────────────────────────
    if kpi_id == "gdp_per_capita":
        if value > 30000:
            return "Acima de 30.000\u20ac \u2014 a aproximar-se da média da UE."
        if value > 23000:
            return "Entre 23\u201330 mil\u20ac \u2014 abaixo da média da UE, mas a convergir."
        return "Abaixo de 23.000\u20ac \u2014 fosso significativo face à média europeia."

    if kpi_id == "rnd_pct_gdp":
        if value > 2.5:
            return "Investimento em I&D forte \u2014 acima da média da UE."
        if value > 1.5:
            return "Investimento moderado em I&D \u2014 abaixo da meta europeia de 3%."
        return "Investimento baixo em I&D \u2014 risco de perda de competitividade a prazo."

    return None


def painel_kpi(kpi_id, label, source, indicator, description=None, explain=None, **kwargs):
    """Wrap resumo_kpi and inject source/indicator/description/explain fields.
    description: static one-liner explaining the indicator (shown on card, separate from trend).
    explain: plain-language "what this means for you" text for citizens.
    Gracefully handles missing data — frontend tolerates None values.
    """
    kpi = resumo_kpi(kpi_id, label, source, indicator, **kwargs)
    # Always set source/indicator even on error — needed for WP-9 deep-link
    kpi["source"] = source
    kpi["indicator"] = indicator
    # description is separate from context (trend phrase) — both shown on card
    if description is not None:
        kpi["description"] = description
    if explain is not None:
        kpi["explain"] = explain
    # Auto-compute contextual annotation based on value range
    ann = _contextual_annotation(kpi_id, kpi.get("value"), kpi.get("sentiment"))
    if ann:
        kpi["annotation"] = ann
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
    E = EXPLAIN  # shorthand

    sections = [
        # ── 1. Custo de Vida ─────────────────────────────────────────
        {
            "id": "custo_de_vida",
            "name": "Custo de Vida",
            "label": "Custo de Vida",
            "kpis": [
                painel_kpi("inflation",       "Inflação",             "INE",       "hicp_yoy",              invert_sentiment=True,  unit_override="%",             description=D["inflation"],       explain=E["inflation"]),
                painel_kpi("diesel",          "Gasóleo",              "DGEG",      "price_diesel",          invert_sentiment=True,                                 description=D["diesel"],          explain=E["diesel"]),
                painel_kpi("gasoline_95",     "Gasolina 95",          "DGEG",      "price_gasoline_95_pvp", invert_sentiment=True,                                 description=D["gasoline_95"],     explain=E["gasoline_95"]),
                painel_kpi("electricity_btn", "Electricidade BTN",    "ERSE",      "btn_simple",            invert_sentiment=True,                                 description=D["electricity_btn"], explain=E["electricity_btn"]),
                painel_kpi("electricity_mt",  "Electricidade MT",     "ERSE",      "access_mt_peak",        invert_sentiment=True,                                 description=D["electricity_mt"],  explain=E["electricity_mt"]),
                painel_kpi("electricity_at",  "Electricidade AT",     "ERSE",      "access_at_peak",        invert_sentiment=True,                                 description=D["electricity_at"],  explain=E["electricity_at"]),
                painel_kpi("euribor_3m",      "Euribor 3m",           "BPORTUGAL", "euribor_3m",            invert_sentiment=True,  unit_override="%",             description=D["euribor_3m"],      explain=E["euribor_3m"]),
                painel_kpi("euribor_6m",      "Euribor 6m",           "BPORTUGAL", "euribor_6m",            invert_sentiment=True,  unit_override="%",             description=D["euribor_6m"],      explain=E["euribor_6m"]),
                painel_kpi("euribor_12m",     "Euribor 12m",          "BPORTUGAL", "euribor_12m",           invert_sentiment=True,  unit_override="%",             description=D["euribor_12m"],     explain=E["euribor_12m"]),
            ],
        },
        # ── 2. Indústria ─────────────────────────────────────────────
        {
            "id": "industria",
            "name": "Indústria",
            "label": "Indústria",
            "kpis": [
                painel_kpi("ipi_total",   "Produção Industrial",  "INE",  "ipi_seasonal_cae_TOT", invert_sentiment=False,                                description=D["ipi_total"],   explain=E["ipi_total"]),
                painel_kpi("ipi_cae_10",  "Indústria Alimentar",  "INE",  "ipi_seasonal_cae_10",  invert_sentiment=False,                                description=D["ipi_cae_10"],  explain=E["ipi_cae_10"]),
                painel_kpi("ipi_cae_20",  "Química",              "INE",  "ipi_seasonal_cae_20",  invert_sentiment=False,                                description=D["ipi_cae_20"],  explain=E["ipi_cae_20"]),
                painel_kpi("ipi_cae_24",  "Metalurgia de Base",   "INE",  "ipi_seasonal_cae_24",  invert_sentiment=False,                                description=D["ipi_cae_24"],  explain=E["ipi_cae_24"]),
                painel_kpi("ipi_cae_25",  "Produtos Metálicos",   "INE",  "ipi_seasonal_cae_25",  invert_sentiment=False,                                description=D["ipi_cae_25"],  explain=E["ipi_cae_25"]),
                painel_kpi("ipi_cae_28",  "Máquinas e Equipam.",  "INE",  "ipi_seasonal_cae_28",  invert_sentiment=False,                                description=D["ipi_cae_28"],  explain=E["ipi_cae_28"]),
                painel_kpi("ipi_cae_29",  "Veículos Automóveis",  "INE",  "ipi_seasonal_cae_29",  invert_sentiment=False,                                description=D["ipi_cae_29"],  explain=E["ipi_cae_29"]),
                painel_kpi("copper",      "Cobre",                "FRED", "copper",               invert_sentiment=False, unit_override="USD/ton",       description=D["copper"],      explain=E["copper"]),
                painel_kpi("aluminum",    "Alumínio",             "FRED", "aluminum",             invert_sentiment=False, unit_override="USD/ton",       description=D["aluminum"],    explain=E["aluminum"]),
            ],
        },
        # ── 3. Emprego ───────────────────────────────────────────────
        {
            "id": "emprego",
            "name": "Emprego",
            "label": "Emprego",
            "kpis": [
                painel_kpi("unemployment",          "Desemprego",           "OECD", "unemp_m",           invert_sentiment=True,                                description=D["unemployment"],          explain=E["unemployment"]),
                painel_kpi("industrial_employment", "Emprego Industrial",   "INE",  "emp_industry_cae",  detail_filter='"dim_3": "C"', invert_sentiment=False, unit_override="Índice (2021=100)", description=D["industrial_employment"],  explain=E["industrial_employment"]),
                painel_kpi("wages_industry",        "Salários Indústria",   "INE",  "wages_industry_cae",detail_filter='"dim_3": "C"', invert_sentiment=False, unit_override="Índice (2021=100)", description=D["wages_industry"],         explain=E["wages_industry"]),
            ],
        },
        # ── 4. Conjuntura ─────────────────────────────────────────────
        {
            "id": "conjuntura",
            "name": "Conjuntura",
            "label": "Conjuntura",
            "kpis": [
                painel_kpi("cli",        "Indicador Avançado",   "OECD", "cli",               invert_sentiment=False,                  description=D["cli"],        explain=E["cli"]),
                painel_kpi("confidence", "Confiança Industrial", "INE",  "conf_manufacturing", invert_sentiment=False, unit_override="saldo", description=D["confidence"], explain=E["confidence"]),
                painel_kpi("order_books","Carteira Encomendas",  "OECD", "order_books",        invert_sentiment=False, unit_override="saldo", description=D["order_books"], explain=E["order_books"]),
            ],
        },
        # ── 5. Energia ───────────────────────────────────────────────
        {
            "id": "energia",
            "name": "Energia",
            "label": "Energia",
            "kpis": [
                painel_kpi("energy_cost",       "Electricidade Grossista", "REN",  "electricity_price_mibel",     invert_sentiment=True,                              description=D["energy_cost"],       explain=E["energy_cost"]),
                painel_kpi("renewable_share",   "% Energia Renovável",     "DGEG", "renewable_share_electricity", invert_sentiment=False, unit_override="%", description=D["renewable_share"],   explain=E["renewable_share"]),
                painel_kpi("energy_dependence", "Dependência Energética",  "DGEG", "energy_dependence",           invert_sentiment=True,  unit_override="%", description=D["energy_dependence"], explain=E["energy_dependence"]),
                painel_kpi("natural_gas",       "Gás Natural",             "FRED", "natural_gas",                 invert_sentiment=True,  unit_override="USD/MMBtu",  description=D["natural_gas"],       explain=E["natural_gas"]),
                painel_kpi("solar",             "Solar",                   "REN",  "electricity_solar",           invert_sentiment=False, unit_override="GWh",         description=D["solar"],             explain=E["solar"]),
                painel_kpi("wind",              "Eólica",                  "REN",  "electricity_wind",            invert_sentiment=False, unit_override="GWh",         description=D["wind"],              explain=E["wind"]),
            ],
        },
        # ── 6. Externo ───────────────────────────────────────────────
        {
            "id": "externo",
            "name": "Externo",
            "label": "Externo",
            "kpis": [
                painel_kpi("eur_usd",      "EUR/USD",        "BPORTUGAL", "eur_usd",      invert_sentiment=False,                    description=D["eur_usd"],      explain=E["eur_usd"]),
                painel_kpi("spread_pt_de", "Spread PT/DE",   "BPORTUGAL", "spread_pt_de", invert_sentiment=True,  unit_override="pp",     description=D["spread_pt_de"], explain=E["spread_pt_de"]),
                painel_kpi("brent",        "Petróleo Brent", "FRED",      "brent_oil",    invert_sentiment=True,  unit_override="USD/bbl",description=D["brent"],        explain=E["brent"]),
            ],
        },
        # ── 7. Competitividade ────────────────────────────────────────
        {
            "id": "competitividade",
            "name": "Competitividade",
            "label": "Competitividade",
            "kpis": [
                painel_kpi("gdp_per_capita",  "PIB per capita", "EUROSTAT",  "gdp_per_capita_eur", invert_sentiment=False, unit_override="€/hab", region="PT", description=D["gdp_per_capita"],  explain=E["gdp_per_capita"]),
                painel_kpi("rnd_pct_gdp",     "I&D % PIB",      "WORLDBANK", "rnd_pct_gdp",        invert_sentiment=False, unit_override="%",     region="PT", description=D["rnd_pct_gdp"],     explain=E["rnd_pct_gdp"]),
                painel_kpi("employment_rate", "Taxa de Emprego", "EUROSTAT",  "employment_rate",    invert_sentiment=False, unit_override="%",     region="PT", description=D["employment_rate"], explain=E["employment_rate"]),
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
