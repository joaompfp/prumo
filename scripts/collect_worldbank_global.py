#!/usr/bin/env python3
"""
collect_worldbank_global.py — Fetch WorldBank data for global countries.

Adds PALOPs, Brazil, and major economies to the indicators DB.
Uses the same indicator codes already present for EU countries.
Safe to run multiple times (upserts by source+indicator+region+period).
"""

import sys
import time
import json
import urllib.request
import urllib.parse
import duckdb
from datetime import datetime

DB_PATH = "/data/cae-data.duckdb"

# WorldBank indicator codes → DB indicator name + unit
WB_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG":  ("gdp_growth",              "%"),
    "NY.GDP.PCAP.CD":     ("gdp_per_capita",           "USD"),
    "NY.GDP.PCAP.PP.CD":  ("gdp_per_capita_ppp",       "USD (2017 PPC)"),
    "NY.GDP.MKTP.CD":     ("gdp_usd",                  "USD"),
    "SL.UEM.TOTL.ZS":    ("unemployment_wb",           "%"),
    "SL.EMP.TOTL.SP.ZS": ("employment_rate",           "%"),
    "SL.TLF.CACT.FE.ZS": ("female_labor_participation","%"),
    "SP.DYN.CBRT.IN":    ("birth_rate",                "/1000"),
    "SP.DYN.CDRT.IN":    ("death_rate",                "/1000"),
    "SP.DYN.LE00.IN":    ("life_expectancy",           "anos"),
    "SI.POV.GINI":       ("gini",                      "0–100"),
    "SH.XPD.CHEX.GD.ZS": ("health_expenditure",        "% PIB"),
    "GB.XPD.RSDV.GD.ZS": ("rnd_pct_gdp",               "% PIB"),
    "BX.KLT.DINV.WD.GD.ZS":("fdi_inflows_pct_gdp",    "% PIB"),
    "NE.EXP.GNFS.ZS":    ("exports_pct_gdp",           "% PIB"),
    "NE.IMP.GNFS.ZS":    ("imports_pct_gdp",           "% PIB"),
    "NE.RSB.GNFS.ZS":    ("trade_balance_pct_gdp",     "% PIB"),
    "GC.DOD.TOTL.GD.ZS": ("gov_debt_pct_gdp_wb",       "% PIB"),
    "IT.NET.USER.ZS":    ("internet_users_pct",         "%"),
    "SE.TER.ENRR":       ("tertiary_enrollment",        "%"),
    "SE.SEC.ENRR":       ("school_enrollment_secondary","%"),
    "SE.ADT.LITR.ZS":    ("literacy_rate",              "%"),
    "SP.POP.TOTL":       ("population",                 "hab."),
    "SP.URB.TOTL.IN.ZS": ("urbanization",               "%"),
}

# Countries to add (ISO2 codes WorldBank accepts)
NEW_COUNTRIES = [
    # PALOPs
    "AO", "MZ", "CV", "GW", "ST",
    # Brazil
    "BR",
    # G7 (not already in EU)
    "US", "JP", "CA", "GB",
    # Major emerging
    "CN", "IN", "ZA", "MX", "KR",
    # Other relevant
    "TR", "NO", "CH", "AR", "CL", "NG", "EG", "ID", "TH", "MY",
]

BASE_URL = "https://api.worldbank.org/v2"
SINCE_YEAR = 1990
FETCHED_AT = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_wb(wb_code: str, countries: list[str]) -> list[dict]:
    """Fetch all years for one indicator across all countries at once."""
    # WorldBank supports semicolon-separated country lists
    country_str = ";".join(c.lower() for c in countries)
    url = f"{BASE_URL}/country/{country_str}/indicator/{wb_code}"
    params = f"?format=json&per_page=32500&date={SINCE_YEAR}:2030"
    full_url = url + params

    try:
        with urllib.request.urlopen(full_url, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR fetching {wb_code}: {e}", file=sys.stderr)
        return []

    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return []

    rows = []
    for item in data[1]:
        if item.get("value") is None:
            continue
        country_code = item.get("countryiso3code") or item.get("country", {}).get("id", "")
        # WorldBank returns ISO3 in countryiso3code; we want ISO2
        # The 'id' field in country dict is ISO2
        country_iso2 = item.get("country", {}).get("id", "").upper()
        if not country_iso2:
            continue
        rows.append({
            "country": country_iso2,
            "year": str(item["date"]),
            "value": float(item["value"]),
        })
    return rows


def upsert_rows(conn, rows_by_indicator: dict[str, list]):
    """Insert or replace rows. DuckDB doesn't have ON CONFLICT, so delete+insert."""
    total = 0
    for (ind_name, unit), rows in rows_by_indicator.items():
        if not rows:
            continue
        # Build tuples
        tuples = [
            ("WORLDBANK", ind_name, r["country"], r["year"], r["value"], unit, None, None, FETCHED_AT, None)
            for r in rows
        ]
        # Delete existing
        countries = list({r["country"] for r in rows})
        years     = list({r["year"] for r in rows})
        country_ph = ",".join(f"'{c}'" for c in countries)
        year_ph    = ",".join(f"'{y}'" for y in years)
        conn.execute(f"""
            DELETE FROM indicators
            WHERE source='WORLDBANK' AND indicator='{ind_name}'
            AND region IN ({country_ph}) AND period IN ({year_ph})
        """)
        conn.executemany("""
            INSERT INTO indicators
              (source, indicator, region, period, value, unit, category, detail, fetched_at, source_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, tuples)
        total += len(tuples)
    return total


def main():
    print(f"[collect_worldbank_global] Start — {len(NEW_COUNTRIES)} countries, {len(WB_INDICATORS)} indicators", flush=True)
    conn = duckdb.connect(DB_PATH, read_only=False)

    grand_total = 0
    for wb_code, (ind_name, unit) in WB_INDICATORS.items():
        print(f"  [{ind_name}] fetching...", end=" ", flush=True)
        rows = fetch_wb(wb_code, NEW_COUNTRIES)
        # Filter to only new countries (avoid touching EU rows)
        rows = [r for r in rows if r["country"] in set(NEW_COUNTRIES)]
        print(f"{len(rows)} obs", flush=True)
        if rows:
            n = upsert_rows(conn, {(ind_name, unit): rows})
            grand_total += n
        time.sleep(0.3)  # polite rate limiting

    conn.close()
    print(f"\n[collect_worldbank_global] Done — {grand_total} rows written.", flush=True)


if __name__ == "__main__":
    main()
