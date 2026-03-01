"""
painel.py — /api/painel: KPIs organized into 5 thematic sections.

Replaces /api/resumo as the primary KPI endpoint (resumo kept for compat).
Reuses resumo_kpi() for all KPI computation; special cases for confidence
and cli (yoy = absolute pp difference) are handled in resumo_kpi().
"""

from .resumo import resumo_kpi


def build_painel():
    """Build /api/painel response with 5 thematic sections and 17 KPIs."""
    sections = [
        {
            "id": "custo_de_vida",
            "label": "Custo de Vida",
            "kpis": [
                resumo_kpi("inflation",       "Inflação",             "INE",       "hicp_yoy",                invert_sentiment=True,  unit_override="%"),
                resumo_kpi("diesel",          "Gasóleo",              "DGEG",      "price_diesel",            invert_sentiment=True),
                resumo_kpi("electricity_btn", "Electricidade (casa)", "ERSE",      "btn_simple",              invert_sentiment=True),
                resumo_kpi("euribor_12m",     "Euribor 12 meses",     "BPORTUGAL", "euribor_12m",             invert_sentiment=True,  unit_override="%"),
            ],
        },
        {
            "id": "emprego",
            "label": "Emprego",
            "kpis": [
                resumo_kpi("unemployment",           "Desemprego",         "OECD", "unemp_m",          invert_sentiment=True),
                resumo_kpi("industrial_employment",  "Emprego Industrial", "INE",  "emp_industry_cae",
                           detail_filter='"dim_3": "C"', invert_sentiment=False, unit_override="Índice (2021=100)"),
                resumo_kpi("wages_industry",         "Salários Indústria (nominal)", "INE",  "wages_industry_cae",
                           detail_filter='"dim_3": "C"', invert_sentiment=False, unit_override="Índice (2021=100)"),
            ],
        },
        {
            "id": "conjuntura",
            "label": "Conjuntura",
            "kpis": [
                # industrial_production: special context in resumo_kpi (vs 2021=100 base)
                resumo_kpi("industrial_production", "Produção Industrial", "INE",  "ipi_seasonal_cae_TOT", invert_sentiment=False),
                # cli: yoy in pp (absolute diff) — handled in resumo_kpi via kpi_id == "cli"
                resumo_kpi("cli",                   "Indicador Avançado", "OECD", "cli",                  invert_sentiment=False),
                # confidence: yoy in pp (absolute diff) — handled in resumo_kpi
                resumo_kpi("confidence",            "Confiança Industrial","INE",  "conf_manufacturing",   invert_sentiment=False, unit_override="saldo"),
                resumo_kpi("order_books",           "Carteira Encomendas","OECD", "order_books",          invert_sentiment=False, unit_override="saldo"),
            ],
        },
        {
            "id": "energia",
            "label": "Energia",
            "kpis": [
                resumo_kpi("energy_cost",       "Electricidade Grossista", "REN",  "electricity_price_mibel",     invert_sentiment=True),
                # DB stores ratio (0.63), display as % (63) — multiply by 100
                resumo_kpi("renewable_share",   "% Energia Renovável",     "DGEG", "renewable_share_electricity", invert_sentiment=False, scale_factor=100, unit_override="%"),
                resumo_kpi("energy_dependence", "Dependência Energética",  "DGEG", "energy_dependence",          invert_sentiment=True,  scale_factor=100, unit_override="%"),
            ],
        },
        {
            "id": "externo",
            "label": "Externo",
            "kpis": [
                resumo_kpi("eur_usd",      "EUR/USD",       "BPORTUGAL", "eur_usd",     invert_sentiment=False),
                resumo_kpi("spread_pt_de", "Spread PT/DE",  "BPORTUGAL", "spread_pt_de",invert_sentiment=True,  unit_override="pp"),
                resumo_kpi("brent",        "Petróleo Brent","FRED",      "brent_oil",   invert_sentiment=True,  unit_override="USD/bbl"),
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
