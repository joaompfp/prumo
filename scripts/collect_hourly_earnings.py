#!/usr/bin/env python3
"""
Collect median hourly earnings (earn_ses_pub2s) from Eurostat SES.
Stores under source=EUROSTAT, indicator=earn_ses_pub2s

Dataset: earn_ses_pub2s — Structure of Earnings Survey
Filters: sizeclas=GE10, sex=T (total), unit=EUR
Frequency: 4-yearly (2006, 2010, 2014, 2018, 2022)

Usage:
    python3 scripts/collect_hourly_earnings.py [--staging] [--dry-run]
"""

import sys, duckdb, requests
from datetime import date
from pathlib import Path

INDICATOR_NAME = "earn_ses_pub2s"
SOURCE = "EUROSTAT"
UNIT = "EUR/h"
CATEGORY = "labour"
DATASET_CODE = "earn_ses_pub2s"
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
    values = data.get("value", {})
    dims   = data.get("dimension", {})
    ids    = data.get("id", [])
    sizes  = data.get("size", [])

    if "geo" not in dims or "time" not in dims:
        return {}

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
        pts = []
        for period, time_pos in times_sorted:
            flat = geo_pos * strides[geo_dim_i] + time_pos * strides[time_dim_i]
            val  = values.get(str(flat))
            if val is not None:
                pts.append((period, float(val)))
        if pts:
            result[geo_code] = pts
    return result


def fetch_data():
    geo_params = "&".join(f"geo={c}" for c in COUNTRIES)
    url = (f"{EUROSTAT_BASE}/{DATASET_CODE}"
           f"?format=JSON&lang=EN"
           f"&sizeclas=GE10"   # enterprises ≥10 employees
           f"&sex=T"           # total (all)
           f"&unit=EUR"        # euros
           f"&{geo_params}")
    print(f"  Fetching {DATASET_CODE} (SES median hourly, EUR)...", file=sys.stderr)
    r = requests.get(url, timeout=60, headers={"User-Agent": "OpenClaw/1.0"})
    r.raise_for_status()
    return parse_jsonstat(r.json())


def store(conn, raw):
    today = date.today().isoformat()
    count = 0
    for geo, pts in raw.items():
        region = GEO_MAP.get(geo, geo)
        for period, value in pts:
            # SES periods are annual (e.g., "2018") — store as YYYY-00
            period_db = f"{period}-00" if len(period) == 4 else period
            conn.execute(
                "INSERT OR REPLACE INTO indicators (source, indicator, region, period, value, unit, category, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
                (SOURCE, INDICATOR_NAME, region, period_db, value, UNIT, CATEGORY, today)
            )
            count += 1
    return count


def main():
    dry_run = "--dry-run" in sys.argv
    use_stg = "--staging" in sys.argv
    db_path = STAGING_DB if (use_stg or dry_run) else PROD_DB

    print(f"💶 {INDICATOR_NAME} (Eurostat SES)")
    print(f"   DB: {db_path}")

    try:
        raw = fetch_data()
    except Exception as e:
        print(f"❌ Fetch error: {e}", file=sys.stderr); sys.exit(1)

    if not raw:
        print("❌ No data returned.", file=sys.stderr); sys.exit(1)

    total = sum(len(v) for v in raw.values())
    print(f"  ✓ {total} points, {len(raw)} countries")
    for geo in ["PT", "EU27_2020"]:
        if geo in raw:
            last = raw[geo][-1]
            print(f"  {GEO_MAP.get(geo,geo)}: {last[0]} → {last[1]:.2f} EUR/h")

    if dry_run:
        # Print all countries for context
        all_last = sorted([(GEO_MAP.get(g,g), pts[-1][1]) for g,pts in raw.items()], key=lambda x: x[1])
        print("\n  Country ranking (lowest to highest):")
        for i, (c, v) in enumerate(all_last):
            print(f"    {i+1:2}. {c}: {v:.2f} EUR/h")
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
