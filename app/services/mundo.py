"""mundo.py — PT vs Mundo data service.

Exposes get_mundo_data() using query_compare() from series.py.
Supports all EUROSTAT and WORLDBANK indicators with >=20 country coverage.
"""

from .series import query_compare

# Available indicators with >=20 countries confirmed
MUNDO_INDICATORS = {
    "EUROSTAT/unemployment": {
        "label": "Taxa de Desemprego (%)",
        "source": "EUROSTAT",
        "indicator": "unemployment",
        "unit": "%",
    },
    "EUROSTAT/gdp_per_capita_eur": {
        "label": "PIB per capita (EUR)",
        "source": "EUROSTAT",
        "indicator": "gdp_per_capita_eur",
        "unit": "EUR",
    },
    "EUROSTAT/hicp": {
        "label": "Inflaçao (HICP %)",
        "source": "EUROSTAT",
        "indicator": "hicp",
        "unit": "%",
    },
    "EUROSTAT/employment_rate": {
        "label": "Taxa de Emprego (%)",
        "source": "EUROSTAT",
        "indicator": "employment_rate",
        "unit": "%",
    },
    "EUROSTAT/gov_debt_pct_gdp": {
        "label": "Divida Publica (% PIB)",
        "source": "EUROSTAT",
        "indicator": "gov_debt_pct_gdp",
        "unit": "% PIB",
    },
    "EUROSTAT/labour_productivity_person_real": {
        "label": "Produtividade Laboral",
        "source": "EUROSTAT",
        "indicator": "labour_productivity_person_real",
        "unit": "indice",
    },
    "WORLDBANK/gdp_growth": {
        "label": "Crescimento PIB (%)",
        "source": "WORLDBANK",
        "indicator": "gdp_growth",
        "unit": "%",
    },
    "WORLDBANK/gdp_usd": {
        "label": "PIB (USD mil M)",
        "source": "WORLDBANK",
        "indicator": "gdp_usd",
        "unit": "USD",
    },
    "WORLDBANK/employment_rate": {
        "label": "Taxa de Emprego (BM %)",
        "source": "WORLDBANK",
        "indicator": "employment_rate",
        "unit": "%",
    },
    "WORLDBANK/internet_users_pct": {
        "label": "Utilizadores Internet (%)",
        "source": "WORLDBANK",
        "indicator": "internet_users_pct",
        "unit": "% pop.",
    },
}

# Preset country groups
COUNTRY_GROUPS_MUNDO = {
    "Semelhantes": ["PT", "ES", "GR", "CZ", "HU", "PL", "RO", "SK"],
    "OCDE Sul":    ["PT", "ES", "GR", "IT", "TR"],
    "Iberica":     ["PT", "ES"],
    "G7":          ["US", "GB", "FR", "DE", "IT", "JP", "CA"],
    "BRICS":       ["BR", "IN", "CN", "ZA", "RU"],
}


def get_mundo_data(indicator: str, source: str, countries: str, since: str = None, to: str = None):
    """Fetch comparison data for mundo section.

    Args:
        indicator: indicator name (e.g. 'unemployment')
        source: source name (e.g. 'EUROSTAT')
        countries: comma-separated country codes (e.g. 'PT,ES,GR')
        since: minimum period filter (e.g. '2015') or None
        to: maximum period filter (e.g. '2025') or None

    Returns:
        dict with series, countries, indicator metadata
    """
    payload = query_compare(
        dataset=indicator,
        countries=countries,
        months=0,          # not used in V5 (indicator) mode
        indicator=indicator,
        source=source,
        since_yr=since,
    )

    # Apply 'to' filter if provided (query_compare only supports since_yr)
    if to and payload.get("series"):
        for s in payload["series"]:
            s["data"] = [d for d in s["data"] if d.get("period", "") <= to]

    # Enrich with metadata
    key = f"{source}/{indicator}"
    meta = MUNDO_INDICATORS.get(key, {})
    payload["unit"] = meta.get("unit", "")
    payload["label"] = meta.get("label", indicator)

    return payload
