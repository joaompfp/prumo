#!/usr/bin/env python3
"""
Collect GDP per capita PPP (NY.GDP.PCAP.PP.CD) from World Bank API.
Stores into cae-data.duckdb under source=WORLDBANK, indicator=gdp_per_capita_ppp.

Usage:
    CAE_DB_PATH=/path/to/cae-data.duckdb python3 scripts/collect_gdp_per_capita_ppp.py
"""

import os
import sys
import duckdb
import requests
from datetime import date
from pathlib import Path

# --- Config ---
INDICATOR_CODE = "NY.GDP.PCAP.PP.CD"
INDICATOR_NAME = "gdp_per_capita_ppp"
UNIT = "USD (2017)"
SOURCE = "WORLDBANK"
COUNTRIES = ["PT", "ES", "DE", "FR", "EU"]  # EU = EU27+UK approximation via WB code "EU"
WB_COUNTRIES = {
    "PT": "PT",
    "ES": "ES",
    "DE": "DE",
    "FR": "FR",
    "EU": "EU",  # World Bank uses "EU" for European Union aggregate
}
START_YEAR = 2000

# DB path
DB_PATH = os.environ.get("CAE_DB_PATH", str(Path(__file__).parent.parent / "../../appdata/cae-dashboard/cae-data.duckdb"))


def fetch_wb(country_code: str, indicator: str, start_year: int):
    """Fetch World Bank indicator data for a country."""
    url = f"https://api.worldbank.org/v2/country/{country_code.lower()}/indicator/{indicator}"
    params = {
        "format": "json",
        "per_page": 100,
        "date": f"{start_year}:2025",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if len(data) < 2 or not data[1]:
            return []
        points = []
        for item in data[1]:
            if item.get("value") is not None:
                points.append({
                    "year": int(item["date"]),
                    "value": float(item["value"]),
                })
        points.sort(key=lambda x: x["year"])
        return points
    except Exception as e:
        print(f"  ❌ Error fetching {country_code}: {e}", file=sys.stderr)
        return []


def store_points(conn, points_by_country):
    """INSERT OR REPLACE into indicators table."""
    today = date.today().isoformat()
    count = 0
    for region, points in points_by_country.items():
        for p in points:
            period = f"{p['year']}-00"  # Annual: YYYY-00
            conn.execute(
                """
                INSERT OR REPLACE INTO indicators
                  (source, indicator, region, period, value, unit, category, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (SOURCE, INDICATOR_NAME, region, period, p["value"], UNIT, "macro", today),
            )
            count += 1
    return count


def main():
    print(f"🌍 Collecting {INDICATOR_NAME} ({INDICATOR_CODE}) from World Bank...")
    print(f"   DB: {DB_PATH}")

    all_data = {}
    for label, wb_code in WB_COUNTRIES.items():
        print(f"  📡 Fetching {label} ({wb_code})...")
        pts = fetch_wb(wb_code, INDICATOR_CODE, START_YEAR)
        if pts:
            all_data[label] = pts
            latest = pts[-1]
            print(f"     ✓ {len(pts)} points — latest: {latest['year']}: {latest['value']:,.0f} {UNIT}")
        else:
            print(f"     ⚠️  No data for {label}")

    if not all_data:
        print("❌ No data fetched. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Connect to DuckDB and write
    try:
        conn = duckdb.connect(DB_PATH, read_only=False)
        count = store_points(conn, all_data)
        conn.close()
        print(f"\n✅ Stored {count} data points for {INDICATOR_NAME}")
    except Exception as e:
        print(f"❌ DB error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
