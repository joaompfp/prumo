from ..database import get_db


def build_produtividade():
    """Build /api/produtividade — 'O Preco de Uma Hora' productivity data (v2).

    Returns 3 datasets as top-level keys:
      - productivity:      labour_productivity_per_hour (EUROSTAT, index 2010=100)
      - labour_cost:       hourly_labour_cost_index     (EUROSTAT, index 2020=100)
      - purchasing_power:  gdp_per_capita_pps           (EUROSTAT, EU27=100)

    All series cover PT, EU27_2020, DE, ES, FR, PL.
    """
    COUNTRIES = ['PT', 'EU27_2020', 'DE', 'ES', 'FR', 'PL']

    INDICATORS = {
        "productivity": {
            "indicator": "labour_productivity_per_hour",
            "period_min": "1995",
            "unit":  "index 2010=100",
            "label": "Produtividade por hora trabalhada",
        },
        "labour_cost": {
            "indicator": "hourly_labour_cost_index",
            "period_min": "2000",
            "unit":  "index 2020=100",
            "label": "Custo horário de trabalho",
        },
        "purchasing_power": {
            "indicator": "gdp_per_capita_pps",
            "period_min": "1995",
            "unit":  "EU27=100",
            "label": "Poder de compra (PPS)",
        },
    }

    conn = get_db()
    try:
        all_rows = conn.execute("""
            SELECT indicator, region, period, value FROM indicators
            WHERE source='EUROSTAT'
              AND indicator IN ('labour_productivity_per_hour','hourly_labour_cost_index','gdp_per_capita_pps')
              AND region IN ('PT','EU27_2020','DE','ES','FR','PL')
            ORDER BY indicator, region, period
        """).fetchall()
    finally:
        conn.close()

    # Group rows by indicator -> region -> list of {period, value}
    grouped = {}
    for ind_name, region, period, value in all_rows:
        grouped.setdefault(ind_name, {}).setdefault(region, []).append(
            {"period": period, "value": round(value, 2) if value is not None else None}
        )

    # Build result for each dataset key
    def _build_dataset(key):
        cfg      = INDICATORS[key]
        ind_name = cfg["indicator"]
        ind_data = grouped.get(ind_name, {})
        countries_result = {}
        latest_year_val  = None
        for country in COUNTRIES:
            series = ind_data.get(country, [])
            latest = series[-1]["value"] if series else None
            if series and latest_year_val is None:
                try:
                    latest_year_val = int(series[-1]["period"][:4])
                except Exception:
                    pass
            countries_result[country] = {
                "data":   series,
                "latest": latest,
            }
        return {
            "countries": countries_result,
            "unit":      cfg["unit"],
            "label":     cfg["label"],
        }, latest_year_val

    prod_ds,  latest_year_prod  = _build_dataset("productivity")
    labour_ds, latest_year_lc  = _build_dataset("labour_cost")
    pps_ds,   latest_year_pps  = _build_dataset("purchasing_power")

    latest_year = latest_year_prod or latest_year_lc or latest_year_pps or 2024

    return {
        "productivity":    prod_ds,
        "labour_cost":     labour_ds,
        "purchasing_power": pps_ds,
        "latest_year":     latest_year,
        "note":            "direct",
    }
