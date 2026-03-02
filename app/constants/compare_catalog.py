"""
Multi-country indicator catalog for PT vs Europa, PT vs Mundo, and Comparativos sections.
Single source of truth — changing this file is all that's needed to add/remove
indicators from the comparison charts. No JS changes required.

Entry shape:
  id          – unique key within section; used in URL hash
  source      – 'EUROSTAT' | 'WORLDBANK' | None (legacy)
  indicator   – DB indicator column name | None (legacy)
  label       – Display label (PT-PT)
  group       – optgroup label in the select
  unit_label  – short unit string shown in footnote/eyebrow
  default     – True on exactly one entry per section (initial selection)
  mode        – 'db' (default) | 'legacy' (old /api/europa Eurostat client)
  dataset     – only for mode='legacy' (legacy dataset key)
"""

EUROPA_CATALOG = [
    # ── Mercado de Trabalho ─────────────────────────────────────────────
    {"id": "unemployment",               "source": "EUROSTAT",  "indicator": "unemployment",               "label": "Desemprego (%)",               "group": "Mercado de Trabalho", "unit_label": "%",                "default": True},
    {"id": "employment_rate",            "source": "EUROSTAT",  "indicator": "employment_rate",            "label": "Taxa de Emprego (%)",           "group": "Mercado de Trabalho", "unit_label": "%"},
    {"id": "unit_labour_cost",           "source": "EUROSTAT",  "indicator": "unit_labour_cost",           "label": "Custo Unitário do Trabalho",    "group": "Mercado de Trabalho", "unit_label": "Índice 2015=100"},
    {"id": "unit_labour_cost_person",    "source": "EUROSTAT",  "indicator": "unit_labour_cost_person",    "label": "ULC por Pessoa",                "group": "Mercado de Trabalho", "unit_label": "Índice 2015=100"},
    {"id": "labour_productivity_hour_real", "source": "EUROSTAT", "indicator": "labour_productivity_hour_real", "label": "Produtividade/hora (real)", "group": "Mercado de Trabalho", "unit_label": "Índice 2015=100"},

    # ── Preços e Consumo ────────────────────────────────────────────────
    {"id": "hicp",                       "source": "EUROSTAT",  "indicator": "hicp",                       "label": "Inflação (HICP %)",             "group": "Preços e Consumo",    "unit_label": "Índice (2015=100)"},
    {"id": "consumer_confidence",        "source": "EUROSTAT",  "indicator": "consumer_confidence",        "label": "Confiança dos Consumidores",    "group": "Preços e Consumo",    "unit_label": "Índice"},

    # ── PIB e Convergência ──────────────────────────────────────────────
    {"id": "gdp_per_capita_eur",         "source": "EUROSTAT",  "indicator": "gdp_per_capita_eur",         "label": "PIB per capita (€)",            "group": "PIB e Convergência",  "unit_label": "€/hab."},
    {"id": "gdp_quarterly",              "source": "EUROSTAT",  "indicator": "gdp_quarterly",              "label": "PIB Trimestral (volume)",        "group": "PIB e Convergência",  "unit_label": "M€"},

    # ── Finanças Públicas ───────────────────────────────────────────────
    {"id": "gov_debt_pct_gdp",           "source": "EUROSTAT",  "indicator": "gov_debt_pct_gdp",           "label": "Dívida Pública % PIB",          "group": "Finanças Públicas",   "unit_label": "% PIB"},
    {"id": "gov_deficit_pct_gdp",        "source": "EUROSTAT",  "indicator": "gov_deficit_pct_gdp",        "label": "Défice Público % PIB",          "group": "Finanças Públicas",   "unit_label": "% PIB"},
    {"id": "current_account_pct_gdp",    "source": "EUROSTAT",  "indicator": "current_account_pct_gdp",    "label": "Balança Corrente % PIB",        "group": "Finanças Públicas",   "unit_label": "% PIB"},

    # ── Produção Industrial ─────────────────────────────────────────────
    {"id": "ipi_manufacturing",          "source": "EUROSTAT",  "indicator": "ipi_manufacturing",          "label": "IPI Transformadora",            "group": "Produção Industrial", "unit_label": "base 2021=100"},
    {"id": "ipi_total",                  "source": "EUROSTAT",  "indicator": "ipi_total",                  "label": "IPI Total Indústria",           "group": "Produção Industrial", "unit_label": "base 2021=100"},
    {"id": "construction_output",        "source": "EUROSTAT",  "indicator": "construction_output",        "label": "Produção na Construção",        "group": "Produção Industrial", "unit_label": "base 2015=100"},
    {"id": "ipi_food_beverage",          "source": "EUROSTAT",  "indicator": "ipi_food_beverage",          "label": "IPI Alimentar e Bebidas",       "group": "Produção Industrial", "unit_label": "base 2021=100"},
    {"id": "ipi_textiles",               "source": "EUROSTAT",  "indicator": "ipi_textiles",               "label": "IPI Têxtil e Vestuário",        "group": "Produção Industrial", "unit_label": "base 2021=100"},
    {"id": "manufacturing",              "source": None,        "indicator": None,                          "label": "IPI Transf. (série longa)",     "group": "Produção Industrial", "unit_label": "base 2021=100",  "mode": "legacy", "dataset": "manufacturing"},
    {"id": "total_industry",             "source": None,        "indicator": None,                          "label": "IPI Total (série longa)",       "group": "Produção Industrial", "unit_label": "base 2021=100",  "mode": "legacy", "dataset": "total_industry"},
    {"id": "metals",                     "source": None,        "indicator": None,                          "label": "Metais e Metalurgia",           "group": "Produção Industrial", "unit_label": "base 2021=100",  "mode": "legacy", "dataset": "metals"},
    {"id": "chemicals",                  "source": "EUROSTAT",  "indicator": "chemicals_pharma",           "label": "Química e Plásticos",           "group": "Produção Industrial", "unit_label": "base 2021=100"},
    {"id": "transport",                  "source": "EUROSTAT",  "indicator": "transport_eq",               "label": "Material de Transporte",        "group": "Produção Industrial", "unit_label": "base 2021=100"},

    # ── Estrutural ──────────────────────────────────────────────────────
    {"id": "birth_rate",                 "source": "WORLDBANK", "indicator": "birth_rate",                 "label": "Natalidade (/1000)",            "group": "Estrutural",          "unit_label": "/1000 hab."},
    {"id": "rnd_pct_gdp",                "source": "WORLDBANK", "indicator": "rnd_pct_gdp",                "label": "I&D % PIB",                    "group": "Estrutural",          "unit_label": "% PIB"},
    {"id": "fdi_inflows_pct_gdp",        "source": "WORLDBANK", "indicator": "fdi_inflows_pct_gdp",        "label": "IDE Entradas % PIB",            "group": "Estrutural",          "unit_label": "% PIB"},
]



# ══════════════════════════════════════════════════════════════════════════════
# COMPARATIVOS_CATALOG — unified catalog for the merged "Comparativos" section.
# Covers all countries: EU27 (Eurostat), global (WorldBank), composites.
#
# source:
#   "COMPOSITE" — blends Eurostat EU27 (high freq.) + WorldBank (global, annual)
#   "WORLDBANK"  — global coverage (53 countries), annual data
#   "EUROSTAT"   — EU27 only, higher freq. (monthly/quarterly)
#   None         — legacy Eurostat IPI client (mode="legacy")
# ══════════════════════════════════════════════════════════════════════════════
COMPARATIVOS_CATALOG = [
    # ── COMPOSITE: blended Eurostat EU27 + WorldBank global ─────────────────
    {"id": "cmp_unemployment",    "source": "COMPOSITE", "indicator": "unemployment",
     "label": "Desemprego (%)",         "group": "Mercado de Trabalho", "unit_label": "%",
     "default": True,
     "note": "Eurostat EU27 (mensal) · Banco Mundial restante (anual)"},
    {"id": "cmp_employment_rate", "source": "COMPOSITE", "indicator": "employment_rate",
     "label": "Taxa de Emprego (%)",    "group": "Mercado de Trabalho", "unit_label": "%",
     "note": "Eurostat EU27 (trimestral) · Banco Mundial restante (anual)"},

    # ── WORLDBANK: global coverage (~53 países) ──────────────────────────────
    {"id": "wb_gdp_growth",        "source": "WORLDBANK", "indicator": "gdp_growth",
     "label": "Crescimento PIB (%)",        "group": "PIB e Crescimento",      "unit_label": "%"},
    {"id": "wb_gdp_per_capita",    "source": "WORLDBANK", "indicator": "gdp_per_capita",
     "label": "PIB per capita (USD)",        "group": "PIB e Crescimento",      "unit_label": "USD"},
    {"id": "wb_gdp_usd",           "source": "WORLDBANK", "indicator": "gdp_usd",
     "label": "PIB total (USD mil M)",       "group": "PIB e Crescimento",      "unit_label": "USD mil M"},
    {"id": "wb_gini",              "source": "WORLDBANK", "indicator": "gini",
     "label": "Desigualdade (Gini)",         "group": "Social e Desigualdade",  "unit_label": "0–100"},
    {"id": "wb_life_expectancy",   "source": "WORLDBANK", "indicator": "life_expectancy",
     "label": "Esperança de Vida (anos)",    "group": "Social e Desigualdade",  "unit_label": "anos"},
    {"id": "wb_health_exp",        "source": "WORLDBANK", "indicator": "health_expenditure",
     "label": "Despesa em Saúde (% PIB)",   "group": "Social e Desigualdade",  "unit_label": "% PIB"},
    {"id": "wb_death_rate",        "source": "WORLDBANK", "indicator": "death_rate",
     "label": "Taxa de Mortalidade (/1000)", "group": "Social e Desigualdade",  "unit_label": "/1000 hab."},
    {"id": "wb_birth_rate",        "source": "WORLDBANK", "indicator": "birth_rate",
     "label": "Taxa de Natalidade (/1000)", "group": "Social e Desigualdade",  "unit_label": "/1000 hab."},
    {"id": "wb_exports_pct",       "source": "WORLDBANK", "indicator": "exports_pct_gdp",
     "label": "Exportações (% PIB)",        "group": "Comércio e Abertura",    "unit_label": "% PIB"},
    {"id": "wb_trade_balance",     "source": "WORLDBANK", "indicator": "trade_balance_pct_gdp",
     "label": "Balança Comercial (% PIB)",  "group": "Comércio e Abertura",    "unit_label": "% PIB"},
    {"id": "wb_internet",          "source": "WORLDBANK", "indicator": "internet_users_pct",
     "label": "Utilizadores Internet (%)",  "group": "Educação e Inovação",    "unit_label": "%"},
    {"id": "wb_rnd",               "source": "WORLDBANK", "indicator": "rnd_pct_gdp",
     "label": "I&D (% PIB)",               "group": "Educação e Inovação",    "unit_label": "% PIB"},
    {"id": "wb_female_labor",      "source": "WORLDBANK", "indicator": "female_labor_participation",
     "label": "Emprego Feminino (%)",       "group": "Mercado de Trabalho",    "unit_label": "%"},
    {"id": "wb_urbanization",      "source": "WORLDBANK", "indicator": "urbanization",
     "label": "Taxa de Urbanização (%)",   "group": "Social e Desigualdade",  "unit_label": "%"},
    {"id": "wb_fdi",               "source": "WORLDBANK", "indicator": "fdi_inflows_pct_gdp",
     "label": "IDE Entradas (% PIB)",       "group": "Comércio e Abertura",    "unit_label": "% PIB"},

    # ── EUROSTAT: EU27 only (alta freq.) ────────────────────────────────────
    {"id": "eu_hicp",              "source": "EUROSTAT",  "indicator": "hicp",
     "label": "Inflação (HICP %)",          "group": "Preços e Consumo",       "unit_label": "Índice (2015=100)"},
    {"id": "eu_consumer_conf",     "source": "EUROSTAT",  "indicator": "consumer_confidence",
     "label": "Confiança dos Consumidores", "group": "Preços e Consumo",       "unit_label": "Índice"},
    {"id": "eu_gdp_eur",           "source": "EUROSTAT",  "indicator": "gdp_per_capita_eur",
     "label": "PIB per capita (€)",         "group": "PIB e Convergência",     "unit_label": "€/hab."},
    {"id": "eu_gdp_quarterly",     "source": "EUROSTAT",  "indicator": "gdp_quarterly",
     "label": "PIB Trimestral (volume)",     "group": "PIB e Convergência",     "unit_label": "M€"},
    {"id": "eu_gdp_pps",           "source": "EUROSTAT",  "indicator": "gdp_per_capita_pps",
     "label": "PIB per capita (PPS EU=100)","group": "PIB e Convergência",     "unit_label": "PPS"},
    {"id": "eu_gov_debt",          "source": "EUROSTAT",  "indicator": "gov_debt_pct_gdp",
     "label": "Dívida Pública (% PIB)",    "group": "Finanças Públicas",      "unit_label": "% PIB"},
    {"id": "eu_gov_deficit",       "source": "EUROSTAT",  "indicator": "gov_deficit_pct_gdp",
     "label": "Défice Público (% PIB)",    "group": "Finanças Públicas",      "unit_label": "% PIB"},
    {"id": "eu_current_account",   "source": "EUROSTAT",  "indicator": "current_account_pct_gdp",
     "label": "Balança Corrente (% PIB)",  "group": "Finanças Públicas",      "unit_label": "% PIB"},
    {"id": "eu_ipi_manuf",         "source": "EUROSTAT",  "indicator": "ipi_manufacturing",
     "label": "IPI Transformadora",        "group": "Produção Industrial",    "unit_label": "base 2021=100"},
    {"id": "eu_ipi_total",         "source": "EUROSTAT",  "indicator": "ipi_total",
     "label": "IPI Total Indústria",       "group": "Produção Industrial",    "unit_label": "base 2021=100"},
    {"id": "eu_ipi_food",          "source": "EUROSTAT",  "indicator": "ipi_food_beverage",
     "label": "IPI Alimentar e Bebidas",   "group": "Produção Industrial",    "unit_label": "base 2021=100"},
    {"id": "eu_ipi_textiles",      "source": "EUROSTAT",  "indicator": "ipi_textiles",
     "label": "IPI Têxtil e Vestuário",   "group": "Produção Industrial",    "unit_label": "base 2021=100"},
    {"id": "eu_ipi_nonmetallic",   "source": "EUROSTAT",  "indicator": "ipi_nonmetallic",
     "label": "IPI Minerais Não-Metálicos","group": "Produção Industrial",    "unit_label": "base 2021=100"},
    {"id": "eu_ipi_electronics",   "source": "EUROSTAT",  "indicator": "ipi_electronics",
     "label": "IPI Electrónica",           "group": "Produção Industrial",    "unit_label": "base 2021=100"},
    {"id": "eu_construction",      "source": "EUROSTAT",  "indicator": "construction_output",
     "label": "Produção na Construção",    "group": "Produção Industrial",    "unit_label": "base 2015=100"},
    {"id": "eu_ulc",               "source": "EUROSTAT",  "indicator": "unit_labour_cost",
     "label": "Custo Unitário do Trabalho","group": "Mercado de Trabalho",    "unit_label": "Índice 2015=100"},
    {"id": "eu_ulc_person",        "source": "EUROSTAT",  "indicator": "unit_labour_cost_person",
     "label": "ULC por Pessoa",            "group": "Mercado de Trabalho",    "unit_label": "Índice 2015=100"},
    {"id": "eu_productivity",      "source": "EUROSTAT",  "indicator": "labour_productivity_hour_real",
     "label": "Produtividade/hora (real)", "group": "Mercado de Trabalho",    "unit_label": "Índice 2015=100"},
    {"id": "eu_productivity_person","source": "EUROSTAT", "indicator": "labour_productivity_person_real",
     "label": "Produtividade/pessoa (real)","group": "Mercado de Trabalho",   "unit_label": "Índice 2015=100"},
    {"id": "eu_hourly_labour_cost","source": "EUROSTAT",  "indicator": "hourly_labour_cost_index",
     "label": "Custo Horário do Trabalho", "group": "Mercado de Trabalho",    "unit_label": "Índice"},

    # ── WORLDBANK: extra indicators with global coverage ─────────────────
    {"id": "wb_gdp_per_capita_ppp","source": "WORLDBANK", "indicator": "gdp_per_capita_ppp",
     "label": "PIB per capita (PPP USD)",  "group": "PIB e Crescimento",      "unit_label": "USD (PPP)"},
    {"id": "wb_imports_pct",       "source": "WORLDBANK", "indicator": "imports_pct_gdp",
     "label": "Importações (% PIB)",       "group": "Comércio e Abertura",    "unit_label": "% PIB"},
    {"id": "wb_school_secondary",  "source": "WORLDBANK", "indicator": "school_enrollment_secondary",
     "label": "Ensino Secundário (% matrícula)","group": "Educação e Inovação","unit_label": "%"},
    {"id": "wb_tertiary",          "source": "WORLDBANK", "indicator": "tertiary_enrollment",
     "label": "Ensino Superior (% matrícula)","group": "Educação e Inovação", "unit_label": "%"},
    {"id": "wb_literacy",          "source": "WORLDBANK", "indicator": "literacy_rate",
     "label": "Taxa de Literacia (%)",     "group": "Educação e Inovação",    "unit_label": "%"},
    {"id": "wb_gov_debt_wb",       "source": "WORLDBANK", "indicator": "gov_debt_pct_gdp_wb",
     "label": "Dívida Pública % PIB (BM)", "group": "Finanças Públicas",      "unit_label": "% PIB"},
    {"id": "wb_population",        "source": "WORLDBANK", "indicator": "population",
     "label": "População (mil hab.)",      "group": "Social e Desigualdade",  "unit_label": "mil hab."},
]


MUNDO_CATALOG = [
    # ── Mercado de Trabalho ─────────────────────────────────────────────
    {"id": "unemployment",               "source": "EUROSTAT",  "indicator": "unemployment",               "label": "Desemprego (%)",                "group": "Mercado de Trabalho", "unit_label": "%",               "default": True},
    {"id": "unit_labour_cost",           "source": "EUROSTAT",  "indicator": "unit_labour_cost",           "label": "Custo Unitário do Trabalho",    "group": "Mercado de Trabalho", "unit_label": "Índice 2015=100"},
    {"id": "employment_rate",            "source": "EUROSTAT",  "indicator": "employment_rate",            "label": "Taxa de Emprego (%)",           "group": "Mercado de Trabalho", "unit_label": "%"},
    {"id": "labour_productivity",        "source": "EUROSTAT",  "indicator": "labour_productivity_person_real", "label": "Produtividade Laboral",   "group": "Mercado de Trabalho", "unit_label": "Índice 2015=100"},
    {"id": "unemployment_wb",            "source": "WORLDBANK", "indicator": "unemployment_wb",            "label": "Desemprego (Banco Mundial)",    "group": "Mercado de Trabalho", "unit_label": "%"},
    {"id": "female_labor_participation", "source": "WORLDBANK", "indicator": "female_labor_participation", "label": "Emprego Feminino (%)",          "group": "Mercado de Trabalho", "unit_label": "%"},

    # ── PIB e Crescimento ───────────────────────────────────────────────
    {"id": "gdp_growth",                 "source": "WORLDBANK", "indicator": "gdp_growth",                 "label": "Crescimento PIB (%)",           "group": "PIB e Crescimento",   "unit_label": "%"},
    {"id": "gdp_per_capita_eur",         "source": "EUROSTAT",  "indicator": "gdp_per_capita_eur",         "label": "PIB per capita (€)",            "group": "PIB e Crescimento",   "unit_label": "€/hab."},
    {"id": "gdp_per_capita",             "source": "WORLDBANK", "indicator": "gdp_per_capita",             "label": "PIB per capita (USD)",          "group": "PIB e Crescimento",   "unit_label": "USD"},
    {"id": "gdp_usd",                    "source": "WORLDBANK", "indicator": "gdp_usd",                    "label": "PIB (USD mil M)",               "group": "PIB e Crescimento",   "unit_label": "USD mil M"},

    # ── Social e Desigualdade ───────────────────────────────────────────
    {"id": "gini",                       "source": "WORLDBANK", "indicator": "gini",                       "label": "Índice de Gini (desigualdade)", "group": "Social e Desigualdade","unit_label": "0–100"},
    {"id": "life_expectancy",            "source": "WORLDBANK", "indicator": "life_expectancy",            "label": "Esperança de Vida (anos)",      "group": "Social e Desigualdade","unit_label": "anos"},
    {"id": "health_expenditure",         "source": "WORLDBANK", "indicator": "health_expenditure",         "label": "Despesa em Saúde % PIB",        "group": "Social e Desigualdade","unit_label": "% PIB"},
    {"id": "death_rate",                 "source": "WORLDBANK", "indicator": "death_rate",                 "label": "Taxa de Mortalidade (/1000)",   "group": "Social e Desigualdade","unit_label": "/1000 hab."},

    # ── Comércio e Abertura ─────────────────────────────────────────────
    {"id": "trade_balance_pct_gdp",      "source": "WORLDBANK", "indicator": "trade_balance_pct_gdp",      "label": "Balança Comercial % PIB",       "group": "Comércio e Abertura", "unit_label": "% PIB"},
    {"id": "exports_pct_gdp",            "source": "WORLDBANK", "indicator": "exports_pct_gdp",            "label": "Exportações % PIB",             "group": "Comércio e Abertura", "unit_label": "% PIB"},

    # ── Finanças Públicas ───────────────────────────────────────────────
    {"id": "gov_debt_pct_gdp",           "source": "EUROSTAT",  "indicator": "gov_debt_pct_gdp",           "label": "Dívida Pública % PIB",          "group": "Finanças Públicas",   "unit_label": "% PIB"},
    {"id": "hicp",                       "source": "EUROSTAT",  "indicator": "hicp",                       "label": "Inflação (HICP %)",             "group": "Finanças Públicas",   "unit_label": "Índice (2015=100)"},

    # ── Educação e Inovação ─────────────────────────────────────────────
    {"id": "internet_users_pct",         "source": "WORLDBANK", "indicator": "internet_users_pct",         "label": "Utilizadores Internet (%)",     "group": "Educação e Inovação", "unit_label": "%"},
    {"id": "tertiary_enrollment",        "source": "WORLDBANK", "indicator": "tertiary_enrollment",        "label": "Ensino Superior (% matrícula)", "group": "Educação e Inovação", "unit_label": "%"},
]
