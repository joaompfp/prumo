#!/usr/bin/env python3
"""
backfill_full.py — Full data collection for PT, EU27, PALOPs.
Uses existing collector clients. Writes to staging DuckDB.

Run from host (cd stacks/jarbas/images/prumo):
    python3 scripts/backfill_full.py [--eurostat] [--worldbank] [--oecd] [--all]
"""

import sys, json, time, duckdb
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
STAGING_DB = PROJECT_DIR.parent.parent / "appdata/prumo/cae-data-staging.duckdb"
FETCHED_AT = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

sys.path.insert(0, str(PROJECT_DIR / "collectors"))

# ===== Country lists =====
EU27 = ["AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","EL","HU","IE",
        "IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"]
EU27_AGG = "EU27_2020"
PALOP = ["AO","MZ","CV","GW","ST","TL"]
BRICS_PLUS = ["BR","US","CN","IN","JP","KR","GB","CA","CH","TR","MX","ZA",
              "AR","CL","NG","EG","ID","TH","MY","NO"]
ALL_WB_COUNTRIES = sorted(set(EU27 + PALOP + BRICS_PLUS))

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


# ==================== EUROSTAT ====================
# Indicators needing EU27 coverage (currently only PT or 6 countries)

EUROSTAT_MONTHLY_IPI = [
    # (indicator_name, nace_code, dataset)
    ("ipi_total", "B-D", "sts_inpr_m"),
    ("ipi_manufacturing", "C", "sts_inpr_m"),
    ("ipi_food_beverage", "C10-C12", "sts_inpr_m"),
    ("ipi_textiles", "C13-C15", "sts_inpr_m"),
    ("ipi_wood_paper", "C16-C18", "sts_inpr_m"),
    ("ipi_chemicals_pharma", "C20_C21", "sts_inpr_m"),
    ("ipi_rubber_plastics", "C22", "sts_inpr_m"),
    ("ipi_nonmetallic", "C23", "sts_inpr_m"),
    ("ipi_metals", "C24_C25", "sts_inpr_m"),
    ("ipi_electronics", "C26_C27", "sts_inpr_m"),
    ("ipi_machinery", "C28", "sts_inpr_m"),
    ("ipi_transport_eq", "C29_C30", "sts_inpr_m"),
    ("construction_output", "F", "sts_copr_m"),
]

EUROSTAT_ANNUAL = [
    # (indicator, dataset, dim_filters, unit)
    ("gdp_per_capita_pps", "nama_10_pc", {"unit": "CP_PPS_HAB", "na_item": "B1GQ"}, "PPS per capita"),
    ("gdp_per_capita_eur", "nama_10_pc", {"unit": "CP_EUR_HAB", "na_item": "B1GQ"}, "EUR per capita"),
    ("gov_debt_pct_gdp", "gov_10dd_edpt1", {"unit": "PC_GDP", "sector": "S13", "na_item": "GD"}, "% PIB"),
    ("gov_deficit_pct_gdp", "gov_10dd_edpt1", {"unit": "PC_GDP", "sector": "S13", "na_item": "B9"}, "% PIB"),
    ("employment_rate", "lfsi_emp_a", {"unit": "PC", "age": "Y20-64", "sex": "T"}, "%"),
    ("current_account_pct_gdp", "tipsbp20", {}, "% PIB"),
]

EUROSTAT_QUARTERLY = [
    ("gdp_quarterly", "namq_10_gdp", {"unit": "CLV_PCH_PRE", "na_item": "B1GQ", "s_adj": "SCA"}, "% QoQ"),
    ("hourly_labour_cost_index", "lc_lci_r2_q", {"unit": "I20", "nace_r2": "B-S", "lcstruct": "D1_D4_MD5"}, "Index 2020=100"),
]

EUROSTAT_LABOUR_ANNUAL = [
    ("labour_productivity_hour", "nama_10_lp_ulc", {"unit": "EUR_HW", "na_item": "NLPR"}, "EUR/hour"),
    ("labour_productivity_hour_real", "nama_10_lp_ulc", {"unit": "I15_HW", "na_item": "NLPR"}, "Index 2015=100"),
    ("labour_productivity_person_real", "nama_10_lp_ulc", {"unit": "I15_PER", "na_item": "NLPR"}, "Index 2015=100"),
    ("labour_productivity_per_hour", "nama_10_lp_ulc", {"unit": "EUR_HW", "na_item": "NLPR"}, "EUR/hour"),
    ("unit_labour_cost", "nama_10_lp_ulc", {"unit": "I15", "na_item": "NULC"}, "Index 2015=100"),
    ("unit_labour_cost_hour", "nama_10_lp_ulc", {"unit": "I15_HW", "na_item": "NULC"}, "Index 2015=100"),
    ("unit_labour_cost_person", "nama_10_lp_ulc", {"unit": "I15_PER", "na_item": "NULC"}, "Index 2015=100"),
]


def collect_eurostat(conn):
    from eurostat import EurostatClient
    eu = EurostatClient()
    total = 0
    countries = EU27 + [EU27_AGG]

    # Monthly IPI for all EU27
    print("\n=== EUROSTAT Monthly IPI (EU27) ===")
    for ind_name, nace, dataset in EUROSTAT_MONTHLY_IPI:
        print(f"  {ind_name}...", end=" ", flush=True)
        count = 0
        for geo in countries:
            try:
                result = eu.get_data(dataset, geo=geo, months=300,
                    nace_r2=nace, s_adj="SCA", unit="I21", indic_bt="PRD", freq="M")
                data = result.get("data", [])
                rows = [{"source": "EUROSTAT", "indicator": ind_name, "region": geo,
                         "period": d["period"], "value": d["value"], "unit": "I21",
                         "category": "ipi", "source_id": dataset,
                         "detail": json.dumps({"nace": nace})}
                        for d in data if d.get("value") is not None]
                count += upsert(conn, rows)
            except Exception:
                pass
            time.sleep(0.15)
        print(f"{count} rows")
        total += count
        conn.commit()

    # Unemployment monthly (all EU27)
    print("\n=== EUROSTAT Unemployment (EU27) ===")
    print("  unemployment...", end=" ", flush=True)
    count = 0
    for geo in countries:
        try:
            result = eu.get_unemployment_portugal(months=300, geo=geo)
            data = result.get("data", [])
            rows = [{"source": "EUROSTAT", "indicator": "unemployment", "region": geo,
                     "period": d["period"], "value": d["value"], "unit": "%",
                     "category": "labour", "source_id": "une_rt_m"}
                    for d in data if d.get("value") is not None]
            count += upsert(conn, rows)
        except Exception:
            pass
        time.sleep(0.15)
    print(f"{count} rows")
    total += count
    conn.commit()

    # HICP monthly (all EU27)
    print("  hicp...", end=" ", flush=True)
    count = 0
    for geo in countries:
        try:
            result = eu.get_hicp_portugal(months=300, geo=geo)
            data = result.get("data", [])
            rows = [{"source": "EUROSTAT", "indicator": "hicp", "region": geo,
                     "period": d["period"], "value": d["value"], "unit": "Index (2015=100)",
                     "category": "prices", "source_id": "prc_hicp_midx"}
                    for d in data if d.get("value") is not None]
            count += upsert(conn, rows)
        except Exception:
            pass
        time.sleep(0.15)
    print(f"{count} rows")
    total += count
    conn.commit()

    # Consumer confidence monthly
    print("  consumer_confidence...", end=" ", flush=True)
    count = 0
    for geo in countries:
        try:
            result = eu.get_consumer_confidence(months=300, geo=geo)
            data = result.get("data", [])
            rows = [{"source": "EUROSTAT", "indicator": "consumer_confidence", "region": geo,
                     "period": d["period"], "value": d["value"], "unit": "balance %",
                     "category": "confidence", "source_id": "ei_bsco_m"}
                    for d in data if d.get("value") is not None]
            count += upsert(conn, rows)
        except Exception:
            pass
        time.sleep(0.15)
    print(f"{count} rows")
    total += count
    conn.commit()

    # Annual indicators (EU27)
    print("\n=== EUROSTAT Annual (EU27) ===")
    for ind_name, dataset, filters, unit in EUROSTAT_ANNUAL:
        print(f"  {ind_name}...", end=" ", flush=True)
        count = 0
        for geo in countries:
            try:
                result = eu.get_data(dataset, geo=geo, years=30, **filters)
                data = result.get("data", [])
                rows = [{"source": "EUROSTAT", "indicator": ind_name, "region": geo,
                         "period": d["period"], "value": d["value"], "unit": unit,
                         "category": "macro", "source_id": dataset}
                        for d in data if d.get("value") is not None]
                count += upsert(conn, rows)
            except Exception:
                pass
            time.sleep(0.15)
        print(f"{count} rows")
        total += count
        conn.commit()

    # Quarterly GDP (EU27)
    print("\n=== EUROSTAT Quarterly (EU27) ===")
    for ind_name, dataset, filters, unit in EUROSTAT_QUARTERLY:
        print(f"  {ind_name}...", end=" ", flush=True)
        count = 0
        for geo in countries:
            try:
                result = eu.get_data(dataset, geo=geo, years=25, **filters)
                data = result.get("data", [])
                rows = [{"source": "EUROSTAT", "indicator": ind_name, "region": geo,
                         "period": d["period"], "value": d["value"], "unit": unit,
                         "category": "macro", "source_id": dataset}
                        for d in data if d.get("value") is not None]
                count += upsert(conn, rows)
            except Exception:
                pass
            time.sleep(0.15)
        print(f"{count} rows")
        total += count
        conn.commit()

    # Labour productivity annual (EU27)
    print("\n=== EUROSTAT Labour Productivity (EU27) ===")
    for ind_name, dataset, filters, unit in EUROSTAT_LABOUR_ANNUAL:
        print(f"  {ind_name}...", end=" ", flush=True)
        count = 0
        for geo in countries:
            try:
                result = eu.get_data(dataset, geo=geo, years=30, **filters)
                data = result.get("data", [])
                rows = [{"source": "EUROSTAT", "indicator": ind_name, "region": geo,
                         "period": d["period"], "value": d["value"], "unit": unit,
                         "category": "labour", "source_id": dataset}
                        for d in data if d.get("value") is not None]
                count += upsert(conn, rows)
            except Exception:
                pass
            time.sleep(0.15)
        print(f"{count} rows")
        total += count
        conn.commit()

    print(f"\n  EUROSTAT TOTAL: {total}")
    return total


# ==================== WORLDBANK ====================

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
    print("\n=== WORLDBANK (all countries, 1960→present) ===")
    total = 0
    for ind_name, (wb_code, unit) in sorted(WB_INDICATORS.items()):
        print(f"  {ind_name}...", end=" ", flush=True)
        count = 0
        for country in ALL_WB_COUNTRIES:
            try:
                result = wb.get_indicator(country, wb_code, start_year=1960)
                data = result.get("data", [])
                rows = [{"source": "WORLDBANK", "indicator": ind_name, "region": country,
                         "period": str(d["year"]), "value": d["value"],
                         "unit": unit, "source_id": wb_code}
                        for d in data if d.get("value") is not None]
                count += upsert(conn, rows)
            except Exception:
                pass
            time.sleep(0.1)
        print(f"{count} rows ({len(ALL_WB_COUNTRIES)} countries)")
        total += count
        conn.commit()
    print(f"\n  WORLDBANK TOTAL: {total}")
    return total


# ==================== OECD ====================

def collect_oecd(conn):
    from oecd import OECDClient
    oecd = OECDClient()
    print("\n=== OECD PT (extended history) ===")
    total = 0

    # CLI — full history
    print("  cli...", end=" ", flush=True)
    try:
        result = oecd.get_cli(country="PRT", measure="business_confidence", months=620)
        data = result.get("data", [])
        rows = [{"source": "OECD", "indicator": "cli", "region": "PT",
                 "period": d["period"], "value": d["value"],
                 "unit": "index (100=trend)", "category": "confidence",
                 "source_id": "DF_CLI"}
                for d in data if d.get("value") is not None]
        n = upsert(conn, rows)
        total += n
        print(f"{n} rows")
    except Exception as e:
        print(f"ERROR: {e}")

    # Unemployment — full history
    print("  unemp_m...", end=" ", flush=True)
    try:
        result = oecd.get_unemployment(country="PRT", months=520)
        data = result.get("data", [])
        rows = [{"source": "OECD", "indicator": "unemp_m", "region": "PT",
                 "period": d["period"], "value": d["value"],
                 "unit": "%", "category": "labour", "source_id": "DF_IALFS_UNE_M"}
                for d in data if d.get("value") is not None]
        n = upsert(conn, rows)
        total += n
        print(f"{n} rows")
    except Exception as e:
        print(f"ERROR: {e}")

    # BTS indicators — full history
    for measure in ["production", "order_books", "employment", "selling_prices"]:
        print(f"  {measure}...", end=" ", flush=True)
        try:
            result = oecd.get_bts(country="PRT", measure=measure, months=320)
            data = result.get("data", [])
            rows = [{"source": "OECD", "indicator": measure, "region": "PT",
                     "period": d["period"], "value": d["value"],
                     "unit": "balance %", "category": "bts", "source_id": "DF_BTS"}
                    for d in data if d.get("value") is not None]
            n = upsert(conn, rows)
            total += n
            print(f"{n} rows")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.3)

    conn.commit()
    print(f"\n  OECD TOTAL: {total}")
    return total


# ==================== FRED ====================

FRED_COMMODITIES = [
    "brent_oil", "natural_gas", "copper", "aluminum", "wheat", "corn",
    "coffee", "iron_ore", "steel", "zinc", "nickel", "soybean",
    "sugar", "cotton",
]


def collect_fred(conn):
    from fred import FREDClient
    fred = FREDClient()
    print("\n=== FRED Commodities (full history) ===")
    total = 0
    for commodity in FRED_COMMODITIES:
        series_id = fred.COMMODITIES.get(commodity)
        if not series_id:
            print(f"  {commodity}: no series ID")
            continue
        print(f"  {commodity} ({series_id})...", end=" ", flush=True)
        try:
            result = fred.get_series(series_id, frequency="m")
            data = result.get("data", [])
            rows = [{"source": "FRED", "indicator": commodity, "region": "GLOBAL",
                     "period": d["date"][:7], "value": d["value"],
                     "unit": "USD", "category": "commodities",
                     "source_id": series_id}
                    for d in data if d.get("value") is not None]
            n = upsert(conn, rows)
            total += n
            print(f"{n} rows")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.3)
    conn.commit()
    print(f"\n  FRED TOTAL: {total}")
    return total


# ==================== MAIN ====================

def main():
    args = sys.argv[1:]
    run_all = not args or "--all" in args
    do_eu = run_all or "--eurostat" in args
    do_wb = run_all or "--worldbank" in args
    do_oecd = run_all or "--oecd" in args
    do_fred = run_all or "--fred" in args

    print("=" * 60)
    print("Prumo — Full Data Collection")
    print(f"Staging DB: {STAGING_DB}")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"Targets: EU27 ({len(EU27)}), PALOPs ({len(PALOP)}), global ({len(ALL_WB_COUNTRIES)} total)")
    print("=" * 60)

    conn = duckdb.connect(str(STAGING_DB), read_only=False)
    ensure_db(conn)
    totals = {}

    if do_eu:
        totals["eurostat"] = collect_eurostat(conn)
    if do_wb:
        totals["worldbank"] = collect_worldbank(conn)
    if do_oecd:
        totals["oecd"] = collect_oecd(conn)
    if do_fred:
        totals["fred"] = collect_fred(conn)

    staging_count = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print("RESULTS")
    for src, n in totals.items():
        print(f"  {src:20} → {n} rows")
    print(f"  {'TOTAL':20} → {sum(totals.values())} rows")
    print(f"\nStaging DB: {staging_count} total rows")
    print("=" * 60)

if __name__ == "__main__":
    main()
