#!/usr/bin/env python3
"""
backfill_eu27.py — Collect EUROSTAT data for all EU27 + EU27 aggregate.
Uses the dedicated EurostatClient methods that are known to work.
Writes to staging DuckDB.
"""

import sys, json, time, duckdb
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
STAGING_DB = PROJECT_DIR.parent.parent / "appdata/prumo/cae-data-staging.duckdb"
FETCHED_AT = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

sys.path.insert(0, str(PROJECT_DIR / "collectors"))

EU27 = ["AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","EL","HU","IE",
        "IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"]
EU27_AGG = "EU27_2020"
ALL_GEOS = EU27 + [EU27_AGG]


def ensure_db(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS indicators (
        source VARCHAR, indicator VARCHAR, region VARCHAR, period VARCHAR,
        value DOUBLE, unit VARCHAR, category VARCHAR, detail VARCHAR,
        fetched_at VARCHAR, source_id VARCHAR,
        PRIMARY KEY (source, indicator, region, period))""")


def upsert(conn, rows):
    n = 0
    for r in rows:
        conn.execute("INSERT OR REPLACE INTO indicators VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r["source"], r["indicator"], r["region"], r["period"],
             r["value"], r["unit"], r.get("category"), r.get("detail"),
             FETCHED_AT, r.get("source_id")))
        n += 1
    return n


def collect_indicator(conn, eu, method_name, indicator_name, unit, category,
                      source_id, geos=None, **kwargs):
    """Generic collector: call eu.<method_name>(geo=geo, **kwargs) for each country."""
    if geos is None:
        geos = ALL_GEOS
    method = getattr(eu, method_name)
    print(f"  {indicator_name} ({method_name})...", end=" ", flush=True)
    count = 0
    for geo in geos:
        try:
            result = method(geo=geo, **kwargs)
            data = result.get("data", [])
            rows = [{"source": "EUROSTAT", "indicator": indicator_name, "region": geo,
                     "period": d["period"], "value": d["value"], "unit": unit,
                     "category": category, "source_id": source_id}
                    for d in data if d.get("value") is not None]
            count += upsert(conn, rows)
        except Exception:
            pass
        time.sleep(0.15)
    print(f"{count} rows")
    conn.commit()
    return count


def main():
    from eurostat import EurostatClient
    eu = EurostatClient()

    print("=" * 60)
    print("Prumo — EUROSTAT EU27 Full Collection")
    print(f"Staging DB: {STAGING_DB}")
    print(f"Countries: {len(ALL_GEOS)}")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    conn = duckdb.connect(str(STAGING_DB), read_only=False)
    ensure_db(conn)
    total = 0

    # === Monthly indicators ===
    print("\n--- Monthly (300 months) ---")

    # IPI by NACE sector
    nace_sectors = {
        "ipi_total": ("B-D", "sts_inpr_m"),
        "ipi_manufacturing": ("C", "sts_inpr_m"),
        "ipi_food_beverage": ("C10-C12", "sts_inpr_m"),
        "ipi_textiles": ("C13-C15", "sts_inpr_m"),
        "ipi_wood_paper": ("C16-C18", "sts_inpr_m"),
        "ipi_chemicals_pharma": ("C20_C21", "sts_inpr_m"),
        "ipi_rubber_plastics": ("C22", "sts_inpr_m"),
        "ipi_nonmetallic": ("C23", "sts_inpr_m"),
        "ipi_metals": ("C24_C25", "sts_inpr_m"),
        "ipi_electronics": ("C26_C27", "sts_inpr_m"),
        "ipi_machinery": ("C28", "sts_inpr_m"),
        "ipi_transport_eq": ("C29_C30", "sts_inpr_m"),
    }
    for ind_name, (nace, dataset) in nace_sectors.items():
        total += collect_indicator(conn, eu, "get_ipi_portugal", ind_name,
                                   "I15", "ipi", dataset,
                                   nace_code=nace, months=300)

    # Construction output
    total += collect_indicator(conn, eu, "get_ipi_portugal", "construction_output",
                               "I15", "construction", "sts_copr_m",
                               nace_code="F", months=300)

    # Unemployment
    total += collect_indicator(conn, eu, "get_unemployment_portugal", "unemployment",
                               "%", "labour", "une_rt_m", months=300)

    # HICP
    total += collect_indicator(conn, eu, "get_hicp_portugal", "hicp",
                               "Index (2015=100)", "prices", "prc_hicp_midx",
                               months=300)

    # Consumer confidence
    total += collect_indicator(conn, eu, "get_consumer_confidence", "consumer_confidence",
                               "balance %", "confidence", "ei_bsco_m",
                               months=300)

    # === Annual indicators ===
    print("\n--- Annual (30 years) ---")

    # GDP (uses get_gdp_portugal which does nama_10_gdp)
    total += collect_indicator(conn, eu, "get_gdp_portugal", "gdp_quarterly",
                               "EUR million", "macro", "nama_10_gdp",
                               years=30)

    # Electricity prices (semester)
    total += collect_indicator(conn, eu, "get_electricity_prices", "electricity_price_household",
                               "EUR/kWh", "energy", "nrg_pc_204")

    conn.close()
    print(f"\n{'='*60}")
    print(f"EUROSTAT EU27 TOTAL: {total} rows")
    print(f"Finished: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)


if __name__ == "__main__":
    main()
