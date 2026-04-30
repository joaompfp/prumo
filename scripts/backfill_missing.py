#!/usr/bin/env python3
"""
backfill_missing.py — Backfill missing data detected by quality audit.
Uses existing collector clients. Writes to staging DuckDB.

Targets:
1. WorldBank PT: extend history back to 1960 (catalog expects full series)
2. OECD PT: extend CLI back to 1975, unemp_m back to 1983
3. INE ipi_yoy_cae: fill missing months

Run from host:
    cd stacks/web/images/prumo
    python3 scripts/backfill_missing.py [--worldbank] [--oecd] [--ine] (no args = all)

Then merge:
    docker stop prumo
    python3 scripts/merge_staging.py
    dc-jarbas-up
"""

import sys
import json
import time
import duckdb
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
STAGING_DB = PROJECT_DIR.parent.parent / "appdata/prumo/cae-data-staging.duckdb"
FETCHED_AT = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

sys.path.insert(0, str(PROJECT_DIR / "collectors"))


def ensure_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            source VARCHAR, indicator VARCHAR, region VARCHAR, period VARCHAR,
            value DOUBLE, unit VARCHAR, category VARCHAR, detail VARCHAR,
            fetched_at VARCHAR, source_id VARCHAR,
            PRIMARY KEY (source, indicator, region, period)
        )
    """)


def upsert_rows(conn, rows):
    n = 0
    for r in rows:
        conn.execute(
            "INSERT OR REPLACE INTO indicators VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r["source"], r["indicator"], r["region"], r["period"],
             r["value"], r["unit"], r.get("category"), r.get("detail"),
             FETCHED_AT, r.get("source_id"))
        )
        n += 1
    return n


# ===== WorldBank PT backfill (using existing WorldBankClient) =====

WB_INDICATORS = {
    "birth_rate": ("SP.DYN.CBRT.IN", "/1000"),
    "death_rate": ("SP.DYN.CDRT.IN", "/1000"),
    "employment_rate": ("SL.EMP.TOTL.SP.ZS", "%"),
    "exports_pct_gdp": ("NE.EXP.GNFS.ZS", "% PIB"),
    "fdi_inflows_pct_gdp": ("BX.KLT.DINV.WD.GD.ZS", "% PIB"),
    "female_labor_participation": ("SL.TLF.CACT.FE.ZS", "%"),
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "%"),
    "gdp_per_capita": ("NY.GDP.PCAP.CD", "USD"),
    "gdp_per_capita_ppp": ("NY.GDP.PCAP.PP.CD", "USD (2017 PPC)"),
    "gdp_usd": ("NY.GDP.MKTP.CD", "USD"),
    "gini": ("SI.POV.GINI", "0-100"),
    "gov_debt_pct_gdp_wb": ("GC.DOD.TOTL.GD.ZS", "% PIB"),
    "health_expenditure": ("SH.XPD.CHEX.GD.ZS", "% PIB"),
    "imports_pct_gdp": ("NE.IMP.GNFS.ZS", "% PIB"),
    "internet_users_pct": ("IT.NET.USER.ZS", "%"),
    "life_expectancy": ("SP.DYN.LE00.IN", "anos"),
    "literacy_rate": ("SE.ADT.LITR.ZS", "%"),
    "population": ("SP.POP.TOTL", "hab."),
    "rnd_pct_gdp": ("GB.XPD.RSDV.GD.ZS", "% PIB"),
    "school_enrollment_secondary": ("SE.SEC.ENRR", "%"),
    "tertiary_enrollment": ("SE.TER.ENRR", "%"),
    "trade_balance_pct_gdp": ("NE.RSB.GNFS.ZS", "% PIB"),
    "unemployment_wb": ("SL.UEM.TOTL.ZS", "%"),
    "urbanization": ("SP.URB.TOTL.IN.ZS", "%"),
}


def collect_worldbank(conn):
    from worldbank import WorldBankClient
    wb = WorldBankClient()
    print("\n=== WORLDBANK PT backfill (1960→present) ===")
    total = 0
    for ind_name, (wb_code, unit) in sorted(WB_INDICATORS.items()):
        result = wb.get_indicator("PT", wb_code, start_year=1960)
        if "error" in result or not result.get("data"):
            print(f"  {ind_name}: NO DATA — {result.get('error','empty')}")
            continue
        rows = [{
            "source": "WORLDBANK", "indicator": ind_name, "region": "PT",
            "period": str(d["year"]), "value": d["value"],
            "unit": unit, "source_id": wb_code,
        } for d in result["data"]]
        n = upsert_rows(conn, rows)
        total += n
        print(f"  {ind_name}: {n} rows ({rows[0]['period']}→{rows[-1]['period']})")
        time.sleep(0.3)
    conn.commit()
    print(f"  WORLDBANK total: {total}")
    return total


# ===== OECD backfill (using existing OECDClient) =====

def collect_oecd(conn):
    from oecd import OECDClient
    oecd = OECDClient()
    print("\n=== OECD PT backfill (extended history) ===")
    total = 0

    # CLI from 1975 — use get_cli with large months window
    # 1975-01 to 2026-03 = ~614 months
    print("  cli (1975→present)...", end=" ", flush=True)
    try:
        result = oecd.get_cli(country="PRT", measure="business_confidence", months=620)
        data = result.get("data", [])
        rows = [{
            "source": "OECD", "indicator": "cli", "region": "PT",
            "period": d["period"], "value": d["value"],
            "unit": "index (100=trend)", "category": "confidence",
            "detail": json.dumps({"measure": "BCICP"}),
            "source_id": "DF_CLI",
        } for d in data if d.get("value") is not None]
        n = upsert_rows(conn, rows)
        total += n
        print(f"{n} rows")
    except Exception as e:
        print(f"ERROR: {e}")

    # Unemployment from 1983
    print("  unemp_m (1983→present)...", end=" ", flush=True)
    try:
        result = oecd.get_unemployment(country="PRT", months=520)
        data = result.get("data", [])
        rows = [{
            "source": "OECD", "indicator": "unemp_m", "region": "PT",
            "period": d["period"], "value": d["value"],
            "unit": "%", "category": "labour",
            "detail": json.dumps({"measure": "UR"}),
            "source_id": "DF_IALFS_UNE_M",
        } for d in data if d.get("value") is not None]
        n = upsert_rows(conn, rows)
        total += n
        print(f"{n} rows")
    except Exception as e:
        print(f"ERROR: {e}")

    conn.commit()
    print(f"  OECD total: {total}")
    return total


# ===== INE ipi_yoy_cae backfill (using existing INEClient) =====

def collect_ine(conn):
    from ine import INEClient
    ine = INEClient()
    print("\n=== INE ipi_yoy_cae backfill ===")
    total = 0

    # Fetch with large months window to get full history
    print("  ipi_yoy_cae...", end=" ", flush=True)
    try:
        result = ine.get_ipi_yoy(months=260)  # ~21 years from 2005
        data = result.get("data", [])
        rows = [{
            "source": "INE", "indicator": "ipi_yoy_cae", "region": "PT",
            "period": d["period"], "value": d["value"],
            "unit": "%", "category": "ipi",
            "source_id": result.get("varcd", ""),
        } for d in data if d.get("value") is not None]
        n = upsert_rows(conn, rows)
        total += n
        print(f"{n} rows")
    except Exception as e:
        print(f"ERROR: {e}")

    conn.commit()
    print(f"  INE total: {total}")
    return total


# ===== MAIN =====

def main():
    args = sys.argv[1:]
    run_all = not args or "--all" in args
    do_wb = run_all or "--worldbank" in args
    do_oecd = run_all or "--oecd" in args
    do_ine = run_all or "--ine" in args

    print("=" * 60)
    print("Prumo — Backfill Missing Data (using existing collectors)")
    print(f"Staging DB: {STAGING_DB}")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    conn = duckdb.connect(str(STAGING_DB), read_only=False)
    ensure_db(conn)
    totals = {}

    if do_wb:
        totals["worldbank"] = collect_worldbank(conn)
    if do_oecd:
        totals["oecd"] = collect_oecd(conn)
    if do_ine:
        totals["ine"] = collect_ine(conn)

    staging_count = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print("RESULTS")
    for src, n in totals.items():
        print(f"  {src:20} → {n} rows")
    print(f"  {'TOTAL':20} → {sum(totals.values())} rows")
    print(f"\nStaging DB now has {staging_count} total rows.")
    print(f"\nTo merge into production:")
    print(f"  docker stop prumo")
    print(f"  python3 scripts/merge_staging.py   (or manual duckdb merge)")
    print(f"  dc-jarbas-up")
    print("=" * 60)


if __name__ == "__main__":
    main()
