COMPARE_DATASETS = {
    "manufacturing": {"label": "Indústria Transformadora", "nace": "C",        "indicator": "manufacturing"},
    "metals":        {"label": "Metais e Prod. Metálicos",  "nace": "C24_C25",  "indicator": "metals"},
    "chemicals":     {"label": "Química e Farmacêutica",    "nace": "C20_C21",  "indicator": "chemicals_pharma"},
    "transport":     {"label": "Equipamento Transporte",    "nace": "C29_C30",  "indicator": "transport_eq"},
    "total_industry":{"label": "Índice Total Indústria",     "nace": "B-D",      "indicator": "STS_BD_M"},
}

COMPARE_COUNTRIES = {
    # Fundadores / grandes economias
    "DE": "Alemanha",
    "FR": "França",
    "IT": "Itália",
    "ES": "Espanha",
    "NL": "Países Baixos",
    "BE": "Bélgica",
    "AT": "Áustria",
    "LU": "Luxemburgo",
    # Nórdicos
    "SE": "Suécia",
    "DK": "Dinamarca",
    "FI": "Finlândia",
    # Ibérica / Mediterrâneo
    "PT": "Portugal",
    "EL": "Grécia",          # código Eurostat para Grécia (não GR)
    "IE": "Irlanda",
    "CY": "Chipre",
    "MT": "Malta",
    # Alargamento 2004 (Leste)
    "PL": "Polónia",
    "CZ": "República Checa",
    "SK": "Eslováquia",
    "HU": "Hungria",
    "SI": "Eslovénia",
    "EE": "Estónia",
    "LV": "Letónia",
    "LT": "Lituânia",
    # Alargamento 2007
    "RO": "Roménia",
    "BG": "Bulgária",
    # Alargamento 2013
    "HR": "Croácia",
    # Agregado UE
    "EU27_2020": "UE-27",
    "EU27": "UE-27",
}
