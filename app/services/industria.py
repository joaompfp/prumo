from datetime import date

from ..database import get_db
from ..constants import CHART_EVENTS
from .helpers import compute_yoy


def build_industria(period_years=10):
    """Build /api/industria response with sectoral IPI data.
    Bug 5: use sector-specific indicators (ipi_seasonal_cae_20, etc.) instead of detail filters."""
    today = date.today()
    from_year = today.year - period_years
    from_period = f"{from_year}-01"

    sector_map = {
        "chemicals":      {"cae": "20",  "name": "Químicos", "indicator": "ipi_seasonal_cae_20"},
        "metals_base":    {"cae": "24",  "name": "Metalurgia de Base", "indicator": "ipi_seasonal_cae_24"},
        "metal_products": {"cae": "25",  "name": "Produtos Metálicos", "indicator": "ipi_seasonal_cae_25"},
        "machinery":      {"cae": "28",  "name": "Máquinas e Equipamentos", "indicator": "ipi_seasonal_cae_28"},
        "total":          {"cae": "TOT", "name": "Total Indústria", "indicator": "ipi_seasonal_cae_TOT"},
    }

    sectors = []
    conn = get_db("INE")
    try:
        for sid, info in sector_map.items():
            # Bug 5: use sector-specific indicator directly (complete data, no gaps)
            full_sql = """SELECT period, value FROM indicators
                         WHERE source='INE' AND indicator=? ORDER BY period"""
            full_rows = conn.execute(full_sql, [info["indicator"]]).fetchall()

            if not full_rows:
                continue

            full_series = [{"period": r[0], "value": r[1]} for r in full_rows]

            # Window to requested period
            series = [p for p in full_series if p["period"] >= from_period]
            if not series:
                series = full_series  # fallback: show all available data

            latest_val = series[-1]["value"] if series else None

            # Compute vs 2019 baseline
            baseline_pts = [p for p in full_series if p["period"].startswith("2019")]
            baseline_avg = None
            if baseline_pts:
                vals = [p["value"] for p in baseline_pts if p["value"] is not None]
                if vals:
                    baseline_avg = sum(vals) / len(vals)

            yoy = compute_yoy(full_series)

            vs_baseline = None
            if baseline_avg and latest_val:
                vs_baseline = round((latest_val - baseline_avg) / baseline_avg * 100, 1)

            sectors.append({
                "id": sid,
                "cae": info["cae"],
                "name": info["name"],
                "data": series,
                "latest": latest_val,
                "yoy": yoy,
                "vs_baseline_2019": vs_baseline,
            })
    finally:
        conn.close()

    # V5: EUROSTAT additional sectors
    NEW_SECTORS_EUROSTAT = [
        ("ipi_food_beverage", "\U0001f377 Alimentar & Bebidas"),
        ("ipi_textiles",      "\U0001f9f5 Têxteis & Vestuário"),
        ("ipi_wood_paper",    "\U0001fab5 Madeira & Papel"),
        ("ipi_nonmetallic",   "\U0001f9f1 Min. Não Metálicos"),
        ("ipi_electronics",   "\U0001f4a1 Electrónica"),
    ]
    eurostat_sectors = []
    conn_eu = get_db("EUROSTAT")
    try:
        for ind, name in NEW_SECTORS_EUROSTAT:
            rows_eu = conn_eu.execute(
                "SELECT period, value FROM indicators WHERE source='EUROSTAT' AND indicator=? AND region='PT' AND period >= ? ORDER BY period",
                [ind, from_period]
            ).fetchall()
            if len(rows_eu) >= 13:
                series_eu = [{"period": r[0], "value": r[1]} for r in rows_eu]
                eurostat_sectors.append({
                    "id":     ind,
                    "name":   name,
                    "source": "EUROSTAT",
                    "data":   series_eu,
                    "latest": series_eu[-1]["value"] if series_eu else None,
                    "yoy":    compute_yoy(series_eu),
                })
    finally:
        conn_eu.close()

    return {
        "from_period":       from_period,
        "sectors":           sectors,
        "eurostat_sectors":  eurostat_sectors,
        "annotations":       CHART_EVENTS,
    }
