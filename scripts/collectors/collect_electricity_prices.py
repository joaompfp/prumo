#!/usr/bin/env python3
"""
Collect electricity prices for household consumers (nrg_pc_204) from Eurostat.
Stores under source=EUROSTAT, indicator=electricity_price_household

Band DC (KWH2500-4999): 2500-4999 kWh/year, all taxes included, EUR/kWh, bi-annual (S1/S2)

Usage:
    python3 scripts/collect_electricity_prices.py [--staging] [--dry-run]
"""

import sys, duckdb, requests
from datetime import date
from pathlib import Path

INDICATOR_NAME = "electricity_price_household"
SOURCE = "EUROSTAT"
UNIT = "EUR/kWh"
CATEGORY = "energy"
DATASET_CODE = "nrg_pc_204"
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


def parse_jsonstat(data):
    """Parse Eurostat JSON-stat, return {geo_code: [(period, value), ...]}"""
    values = data.get("value", {})
    dims = data.get("dimension", {})
    ids = data.get("id", [])
    sizes = data.get("size", [])

    if "geo" not in dims or "time" not in dims:
        return {}

    geo_idx  = dims["geo"]["category"]["index"]   # geo_code → pos
    time_idx = dims["time"]["category"]["index"]  # period → pos

    times_sorted = sorted(time_idx.items(), key=lambda x: x[1])

    geo_dim_i  = ids.index("geo")
    time_dim_i = ids.index("time")

    # Precompute strides for each dimension
    strides = [1] * len(ids)
    for i in range(len(ids)-2, -1, -1):
        strides[i] = strides[i+1] * sizes[i+1]

    result = {}
    for geo_code, geo_pos in geo_idx.items():
        pts = []
        for period, time_pos in times_sorted:
            flat = geo_pos * strides[geo_dim_i] + time_pos * strides[time_dim_i]
            val = values.get(str(flat))
            if val is not None:
                pts.append((period, float(val)))
        if pts:
            result[geo_code] = pts
    return result


def fetch_data(since="2008"):
    geo_params = "&".join(f"geo={c}" for c in COUNTRIES)
    url = (f"{EUROSTAT_BASE}/{DATASET_CODE}"
           f"?format=JSON&lang=EN"
           f"&nrg_cons=KWH2500-4999"   # Band DC
           f"&tax=I_TAX"               # All taxes included
           f"&currency=EUR"
           f"&unit=KWH"                # EUR per kWh
           f"&{geo_params}"
           f"&sinceTimePeriod={since}")
    print(f"  Fetching {DATASET_CODE} (band DC, all taxes, EUR/kWh)...", file=sys.stderr)
    r = requests.get(url, timeout=60, headers={"User-Agent": "OpenClaw/1.0"})
    r.raise_for_status()
    return parse_jsonstat(r.json())


def store(conn, raw):
    today = date.today().isoformat()
    count = 0
    for geo, pts in raw.items():
        region = GEO_MAP.get(geo, geo)
        for period, value in pts:
            conn.execute(
                "INSERT OR REPLACE INTO indicators (source, indicator, region, period, value, unit, category, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
                (SOURCE, INDICATOR_NAME, region, period, value, UNIT, CATEGORY, today)
            )
            count += 1
    return count


def main():
    dry_run   = "--dry-run" in sys.argv
    use_stg   = "--staging" in sys.argv
    db_path   = STAGING_DB if (use_stg or dry_run) else PROD_DB

    print(f"🔌 {INDICATOR_NAME} (Eurostat {DATASET_CODE})")
    print(f"   DB: {db_path}")

    try:
        raw = fetch_data()
    except Exception as e:
        print(f"❌ Fetch error: {e}", file=sys.stderr); sys.exit(1)

    total = sum(len(v) for v in raw.values())
    print(f"  ✓ {total} points, {len(raw)} countries")
    for geo in ["PT", "EU27_2020"]:
        if geo in raw:
            last = raw[geo][-1]
            print(f"  {GEO_MAP.get(geo,geo)}: {last[0]} → {last[1]:.4f} EUR/kWh")

    if dry_run:
        print("⚠️  Dry-run: not writing."); return

    try:
        conn = duckdb.connect(str(db_path), read_only=False)
    except duckdb.IOException:
        print("  Prod locked → staging", file=sys.stderr)
        conn = duckdb.connect(str(STAGING_DB), read_only=False)

    count = store(conn, raw)
    conn.close()
    print(f"✅ Stored {count} rows → {INDICATOR_NAME}")


if __name__ == "__main__":
    main()
