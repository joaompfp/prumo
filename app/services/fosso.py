from ..database import get_db


def build_fosso():
    """Build /api/fosso — 'O Fosso que Duplicou' data for the WOW section."""
    conn = get_db()
    try:
        pt = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='gdp_per_capita_eur'
            AND region='PT' AND period >= '2000' ORDER BY period
        """).fetchall()
        eu = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='gdp_per_capita_eur'
            AND region='EU27_2020' AND period >= '2000' ORDER BY period
        """).fetchall()
        unemp_pt = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='unemployment'
            AND region='PT' AND period >= '2000-01' ORDER BY period
        """).fetchall()
        unemp_eu = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='unemployment'
            AND region='EU27' AND period >= '2000-01' ORDER BY period
        """).fetchall()
        birth_pt = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='WORLDBANK' AND indicator='birth_rate'
            AND region='PT' ORDER BY period
        """).fetchall()
        birth_eu = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='WORLDBANK' AND indicator='birth_rate'
            AND region='EU' ORDER BY period
        """).fetchall()
        rnd_pt = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='WORLDBANK' AND indicator='rnd_pct_gdp'
            AND region='PT' ORDER BY period
        """).fetchall()
        # R&D EU average — compute from available countries
        rnd_eu_rows = conn.execute("""
            SELECT period, AVG(value) as avg_val FROM indicators
            WHERE source='WORLDBANK' AND indicator='rnd_pct_gdp'
            AND region NOT IN ('PT', 'EU', 'EU27', 'EU27_2020')
            GROUP BY period ORDER BY period
        """).fetchall()
    finally:
        conn.close()

    eu_dict = {r[0]: r[1] for r in eu}

    # Ratio: PT / EU27 * 100
    ratio = [
        {"period": p, "value": round(v / eu_dict[p] * 100, 1)}
        for p, v in pt if p in eu_dict and eu_dict[p]
    ]
    # Gap: EU27 - PT (absolute EUR)
    gap = [
        {"period": p, "value": round(eu_dict[p] - v, 0)}
        for p, v in pt if p in eu_dict
    ]

    return {
        "gdp_pt":         [{"period": r[0], "value": r[1]} for r in pt],
        "gdp_eu27":       [{"period": r[0], "value": r[1]} for r in eu],
        "ratio":          ratio,
        "gap":            gap,
        "gap_2000":       gap[0]["value"]  if gap  else None,
        "gap_latest":     gap[-1]["value"] if gap  else None,
        "ratio_2000":     ratio[0]["value"]  if ratio else None,
        "ratio_latest":   ratio[-1]["value"] if ratio else None,
        "unemployment_pt":  [{"period": r[0], "value": r[1]} for r in unemp_pt],
        "unemployment_eu27":[{"period": r[0], "value": r[1]} for r in unemp_eu],
        "birth_rate_pt":    [{"period": r[0], "value": r[1]} for r in birth_pt],
        "birth_rate_eu":    [{"period": r[0], "value": r[1]} for r in birth_eu],
        "rnd_pt":           [{"period": r[0], "value": r[1]} for r in rnd_pt],
        "rnd_eu_avg":       [{"period": r[0], "value": round(r[1], 2)} for r in rnd_eu_rows],
    }
