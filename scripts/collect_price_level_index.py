#!/usr/bin/env python3
"""
Collect Price Level Index (PLI) from Eurostat prc_ppp_ind.
PLI shows the relative price level of each country vs EU27=100.
PT ~75 means Portugal is ~25% cheaper than EU average.

Stores under source=EUROSTAT, indicator=price_level_index

Usage:
    python3 scripts/collect_price_level_index.py [--staging] [--dry-run]
"""

import sys, duckdb, requests
from datetime import date
from pathlib import Path

INDICATOR_NAME = "price_level_index"
SOURCE = "EUROSTAT"
UNIT = "EU27=100"
CATEGORY = "prices"
DATASET_CODE = "prc_ppp_ind"
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

COUNTRIES = [
    "AT","BE","BG","CY","CZ","DE","DK","EE","EL","ES",
    "FI","FR","HR","HU","IE","IT","LT","LU","LV","MT",
    "NL","PL","PT","RO","SE","SI","SK","EU27_2020",
]

GEO_MAP = {"EU27_2020": "EU27", "EL": "GR"}

DB_BASE = Path(__file__).resolve().parent.parent.parent.parent / "appdata" / "cae-dashboard"
PROD_DB = DB_BASE / "cae-data.duckdb"
STAGING_DB = DB_BASE / "cae-data-staging.duckdb"


def fetch_pli():
    """Fetch PLI for all consumption (CP00) from Eurostat."""
    url = (
        f"{EUROSTAT_BASE}/{DATASET_CODE}"
        f"?na_item=PLI_EU28&ppp_cat=CP00&format=JSON&lang=EN"
        f"&geo={'&geo='.join(COUNTRIES)}"
    )
    print(f"  Fetching {url[:100]}...")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    dims = data.get("dimension", {})
    ids = data.get("id", [])
    sizes = data.get("size", [])
    values = data.get("value", {})

    geo_idx  = dims["geo"]["category"]["index"]
    time_idx = dims["time"]["category"]["index"]

    times_sorted = sorted(time_idx.items(), key=lambda x: x[1])

    geo_dim_i  = ids.index("geo")
    time_dim_i = ids.index("time")

    strides = [1] * len(ids)
    for i in range(len(ids)-2, -1, -1):
        strides[i] = strides[i+1] * sizes[i+1]

    result = {}
    for geo_code, geo_pos in geo_idx.items():
        country = GEO_MAP.get(geo_code, geo_code)
        pts = []
        for period, t_pos in times_sorted:
            flat_idx = geo_pos * strides[geo_dim_i] + t_pos * strides[time_dim_i]
            v = values.get(str(flat_idx))
            if v is not None:
                pts.append((period, float(v)))
        if pts:
            result[country] = pts
    return result


def upsert(conn, rows):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            source TEXT, indicator TEXT, region TEXT, period TEXT,
            value DOUBLE, unit TEXT, category TEXT, detail TEXT,
            fetched_at TEXT, source_id TEXT
        )
    """)
    today = date.today().isoformat()
    for (region, period, value) in rows:
        conn.execute("""
            DELETE FROM indicators
            WHERE source=? AND indicator=? AND region=? AND period=?
        """, [SOURCE, INDICATOR_NAME, region, period])
        conn.execute("""
            INSERT INTO indicators (source, indicator, region, period, value, unit, category, fetched_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, [SOURCE, INDICATOR_NAME, region, period, value, UNIT, CATEGORY, today])


def main():
    staging = "--staging" in sys.argv
    dry_run = "--dry-run" in sys.argv
    db_path = STAGING_DB if staging else PROD_DB

    print(f"[PLI] DB: {db_path} {'(staging)' if staging else '(prod)'}")

    data = fetch_pli()
    rows = [(country, period, value) for country, pts in data.items() for period, value in pts]
    print(f"[PLI] Fetched {len(rows)} datapoints across {len(data)} countries")

    if dry_run:
        for country, pts in sorted(data.items()):
            if pts:
                print(f"  {country}: {pts[-1]}")
        return

    conn = duckdb.connect(str(db_path))
    upsert(conn, rows)
    conn.close()
    print(f"[PLI] Done — {len(rows)} rows written")

    # Show PT vs EU27
    if "PT" in data and "EU27" in data:
        pt_last = data["PT"][-1]
        eu_last = data["EU27"][-1]
        print(f"  PT ({pt_last[0]}): {pt_last[1]:.1f} | EU27 ({eu_last[0]}): {eu_last[1]:.1f}")


if __name__ == "__main__":
    main()
