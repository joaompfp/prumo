from ..database import get_db, fetch_series


def build_macro():
    """Build /api/macro response."""
    result = {}

    # Euribor
    euribor = {}
    for tenor in ["1m", "3m", "6m", "12m"]:
        rows = fetch_series("BPORTUGAL", f"euribor_{tenor}")
        if rows:
            euribor[tenor] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["euribor"] = euribor

    # Spread PT-DE
    rows = fetch_series("BPORTUGAL", "spread_pt_de")
    if rows:
        result["spread_pt_de"] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # Credit
    for ind in ["credit_housing", "credit_consumer", "deposits"]:
        rows = fetch_series("BPORTUGAL", ind)
        if rows:
            result[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # EUR/USD
    rows = fetch_series("BPORTUGAL", "eur_usd")
    if rows:
        result["eur_usd"] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # OECD indicators
    for ind in ["cli", "order_books", "selling_prices", "production"]:
        rows = fetch_series("OECD", ind)
        if rows:
            result[f"oecd_{ind}"] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # Yield 10Y
    for ind in ["pt_10y", "de_10y"]:
        rows = fetch_series("BPORTUGAL", ind)
        if rows:
            result[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # ── V5: New macro indicators ──────────────────────────────────────────────
    NEW_MACRO = [
        ("EUROSTAT", "gov_debt_pct_gdp",    "gov_debt"),
        ("EUROSTAT", "gov_deficit_pct_gdp", "gov_deficit"),
        ("EUROSTAT", "employment_rate",     "employment_rate"),
        ("EUROSTAT", "gdp_per_capita_eur",  "gdp_per_capita"),
        ("WORLDBANK","rnd_pct_gdp",         "rnd_pct_gdp"),
        ("WORLDBANK","fdi_inflows_pct_gdp", "fdi_inflows"),
    ]
    for src, ind, key in NEW_MACRO:
        try:
            conn = get_db()
            try:
                rows2 = conn.execute(
                    "SELECT period, value FROM indicators WHERE source=? AND indicator=? AND region='PT' ORDER BY period",
                    [src, ind]
                ).fetchall()
            finally:
                conn.close()
            if rows2 and len(rows2) >= 3:
                result[key] = [{"period": r[0], "value": r[1]} for r in rows2]
        except Exception:
            pass

    return result
