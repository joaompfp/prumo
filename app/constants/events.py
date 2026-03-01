CHART_EVENTS = [
    {"date": "2020-03", "label": "COVID-19",        "color": "#dc2626", "short": "COVID"},
    {"date": "2021-09", "label": "Crise Energia",   "color": "#d97706", "short": "Energia"},
    {"date": "2022-02", "label": "Invasão Ucrânia", "color": "#7c3aed", "short": "Ucrânia"},
    {"date": "2022-10", "label": "Pico Inflação UE","color": "#d97706", "short": "Inflação"},
    {"date": "2023-07", "label": "BCE para juros",  "color": "#1d4ed8", "short": "BCE↑"},
    {"date": "2024-09", "label": "BCE corta juros", "color": "#16a34a", "short": "BCE↓"},
]

BRIEFING_INDICATORS = [
    ("INE",       "ipi_seasonal_cae"),
    ("INE",       "emp_industry_cae"),
    ("INE",       "hicp_yoy"),
    ("INE",       "conf_manufacturing"),
    ("REN",       "electricity_price_mibel"),
    ("REN",       "electricity_consumption"),
    ("FRED",      "brent_oil"),
    ("FRED",      "natural_gas"),
    ("FRED",      "copper"),
    ("BPORTUGAL", "euribor_3m"),
    ("BPORTUGAL", "spread_pt_de"),
    ("EUROSTAT",  "manufacturing"),
    ("EUROSTAT",  "unemployment"),
    ("OECD",      "cli"),
    ("OECD",      "order_books"),
]

SUMMARY_INDICATORS = [
    ("INE",       "ipi_seasonal_cae",      "Produção Industrial",     "IPI da Indústria Transformadora"),
    ("REN",       "electricity_price_mibel","Preço MIBEL",            "Electricidade no mercado ibérico"),
    ("FRED",      "brent_oil",             "Petróleo Brent",          "Preço do Brent"),
    ("BPORTUGAL", "euribor_3m",            "Euribor 3M",              "Euribor 3 meses"),
    ("INE",       "hicp_yoy",              "Inflação",                "Inflação (IHPC)"),
]
