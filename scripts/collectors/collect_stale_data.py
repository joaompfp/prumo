#!/usr/bin/env python3
"""
collect_stale_data.py — Collect stale EUROSTAT + INE + WorldBank data.
Run from HOST. Writes to staging DuckDB (production is locked by container).

Fixes:
- EUROSTAT: unit changed I15→I21, NACE codes corrected (underscores not hyphens)
- INE: only fetches 2025 onwards (2024 data already present)
- WorldBank: new countries added

Usage: python3 scripts/collect_stale_data.py [--eurostat] [--ine] [--worldbank]
       (no args = all)
"""

import sys, json, time, urllib.request, duckdb, requests
from datetime import datetime
from pathlib import Path

STAGING_DB = Path(__file__).resolve().parent.parent.parent.parent.parent / "appdata/prumo/cae-data-staging.duckdb"
FETCHED_AT = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

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
    for r in rows:
        conn.execute(
            "INSERT OR REPLACE INTO indicators (source,indicator,region,period,value,unit,category,detail,fetched_at,source_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r.get("source"),r.get("indicator"),r.get("region"),r.get("period"),
             r.get("value"),r.get("unit"),r.get("category"),r.get("detail"),
             FETCHED_AT,r.get("source_id"))
        )
    return len(rows)

# ===== EUROSTAT =====
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0"

# FIXED: underscore-separated NACE codes, unit=I21
EUROSTAT_IPI_SECTORS = [
    # (indicator_name, nace_code, dataset, category)
    ("ipi",             "B-D",     "sts_inpr_m", "ipi"),
    ("manufacturing",   "C",       "sts_inpr_m", "ipi"),
    ("total_industry",  "B-D",     "sts_inpr_m", "ipi"),
    ("metals",          "C24_C25", "sts_inpr_m", "ipi"),
    ("chemicals_pharma","C20_C21", "sts_inpr_m", "ipi"),
    ("machinery",       "C28",     "sts_inpr_m", "ipi"),
    ("transport_eq",    "C29_C30", "sts_inpr_m", "ipi"),
    ("rubber_plastics", "C22",     "sts_inpr_m", "ipi"),
    ("ipi_electronics", "C26_C27", "sts_inpr_m", "ipi"),   # FIXED: underscore
    ("ipi_food_beverage","C10-C12","sts_inpr_m", "ipi"),   # hyphen OK with I21
    ("ipi_nonmetallic", "C23",     "sts_inpr_m", "ipi"),
    ("ipi_textiles",    "C13-C15", "sts_inpr_m", "ipi"),
    ("ipi_wood_paper",  "C16-C18", "sts_inpr_m", "ipi"),
    ("construction_output","F",    "sts_copr_m", "construction"),
]

def parse_eurostat_jsonstat(data):
    values = data.get("value", {})
    dim_ids = data.get("id", [])
    dim_sizes = data.get("size", [])
    time_dim = data.get("dimension",{}).get("time",{}).get("category",{})
    time_index = time_dim.get("index", {})
    time_dim_pos = dim_ids.index("time") if "time" in dim_ids else -1
    if time_dim_pos < 0:
        return []
    stride = 1
    for i in range(time_dim_pos + 1, len(dim_sizes)):
        stride *= dim_sizes[i]
    idx_to_period = {v: k for k, v in time_index.items()}
    obs = []
    for key, val in values.items():
        idx = int(key)
        period_pos = idx // stride
        period = idx_to_period.get(period_pos)
        if period and val is not None:
            obs.append({"period": period, "value": float(val)})
    return sorted(obs, key=lambda x: x["period"])

def fetch_eurostat(dataset, nace_code, geo="PT", since="2018-01"):
    """Fetch Eurostat IPI with correct I21 unit."""
    params = {
        "geo": geo, "freq": "M", "indic_bt": "PRD",
        "nace_r2": nace_code, "s_adj": "SCA",
        "unit": "I21",  # FIXED: was I15, now I21 (Base 2021=100)
        "sinceTimePeriod": since,
    }
    try:
        r = requests.get(f"{EUROSTAT_BASE}/data/{dataset}", params=params, timeout=60)
        r.raise_for_status()
        return parse_eurostat_jsonstat(r.json())
    except Exception as e:
        print(f"    ERROR: {e}", file=sys.stderr)
        return []

def collect_eurostat(conn):
    print("\n=== EUROSTAT IPI (unit=I21, corrected NACE codes) ===")
    total = 0
    for ind, nace, dataset, category in EUROSTAT_IPI_SECTORS:
        print(f"  {ind} ({dataset} NACE={nace})...", end=" ", flush=True)
        obs = fetch_eurostat(dataset, nace)
        if not obs:
            print("NO DATA"); continue
        rows = [{
            "source": "EUROSTAT", "indicator": ind, "region": "PT",
            "period": o["period"], "value": o["value"],
            "unit": "I21", "category": category,
            "detail": json.dumps({"nace": nace, "s_adj": "SCA", "dataset": dataset}),
            "source_id": dataset,
        } for o in obs]
        n = upsert_rows(conn, rows)
        total += n
        print(f"{n} rows | {obs[0]['period']} → {obs[-1]['period']}")
        time.sleep(0.5)
    print(f"  EUROSTAT total: {total}")
    return total

# ===== INE =====
INE_URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
_PT_MONTHS = {
    "janeiro":1,"fevereiro":2,"março":3,"abril":4,"maio":5,"junho":6,
    "julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12
}

def period_sort(name):
    low = name.lower().strip()
    for m, n in _PT_MONTHS.items():
        if low.startswith(m):
            return f"{low.split()[-1]}-{n:02d}"
    return name

def gen_monthly_codes(start_year, end_year=None):
    end_year = end_year or datetime.now().year
    codes = []
    for y in range(start_year, end_year+1):
        for m in range(1, 13):
            if y == datetime.now().year and m > datetime.now().month:
                break
            codes.append(f"S3A{y}{m:02d}")
    return codes

def ine_fetch(varcd, params):
    resp = requests.get(INE_URL, params={"op":"2","varcd":varcd,"lang":"PT",**params}, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if not data: return {}
    rec = data[0] if isinstance(data, list) else data
    sucesso = rec.get("Sucesso", {})
    if "Falso" in sucesso:
        raise RuntimeError(f"INE: {sucesso['Falso'][0].get('Msg','error')}")
    return rec.get("Dados", {})

def fetch_store_trade(conn, varcd, ind_name, label, start_year=2025):
    """Fetch INE trade (exports/imports) from start_year to present."""
    print(f"\n  {label} ({varcd}) — {start_year}→present")
    codes = gen_monthly_codes(start_year)
    if not codes:
        print("    No codes to fetch"); return 0
    batches = [codes[i:i+15] for i in range(0, len(codes), 15)]
    pts = []
    for i, batch in enumerate(batches):
        try:
            dados = ine_fetch(varcd, {"Dim1":",".join(batch),"Dim2":"MUNDO","Dim3":"T"})
            for period_name, entries in dados.items():
                ps = period_sort(period_name)
                for e in entries:
                    v = e.get("valor")
                    if v is None or v == "": continue
                    try: val = float(v)
                    except: continue
                    if val == 0: continue
                    pts.append({
                        "source":"INE","indicator":ind_name,"region":"PT","period":ps,
                        "value":val,"unit":"EUR","category":"trade",
                        "detail":json.dumps({"origin":"MUNDO"}),"source_id":varcd
                    })
        except Exception as ex:
            print(f"    batch {i+1}/{len(batches)} error: {ex}")
        time.sleep(0.3)
    if pts:
        by_p = {p["period"]:p for p in pts}
        deduped = sorted(by_p.values(), key=lambda p:p["period"])
        n = upsert_rows(conn, deduped)
        print(f"    ✓ {n} pts | {deduped[0]['period']} → {deduped[-1]['period']}")
        return n
    print("    ✗ No data"); return 0

def collect_ine(conn):
    print("\n=== INE Trade (2025 only — 2024 already present) ===")
    total = 0
    total += fetch_store_trade(conn, "0001397", "imports_monthly", "Importações", start_year=2025)
    time.sleep(0.5)
    total += fetch_store_trade(conn, "0001400", "exports_monthly", "Exportações", start_year=2025)
    print(f"  INE total: {total}")
    return total

# ===== WORLDBANK =====
WB_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG":("gdp_growth","%"),"NY.GDP.PCAP.CD":("gdp_per_capita","USD"),
    "NY.GDP.PCAP.PP.CD":("gdp_per_capita_ppp","USD (2017 PPC)"),"NY.GDP.MKTP.CD":("gdp_usd","USD"),
    "SL.UEM.TOTL.ZS":("unemployment_wb","%"),"SL.EMP.TOTL.SP.ZS":("employment_rate","%"),
    "SL.TLF.CACT.FE.ZS":("female_labor_participation","%"),"SP.DYN.CBRT.IN":("birth_rate","/1000"),
    "SP.DYN.CDRT.IN":("death_rate","/1000"),"SP.DYN.LE00.IN":("life_expectancy","anos"),
    "SI.POV.GINI":("gini","0-100"),"SH.XPD.CHEX.GD.ZS":("health_expenditure","% PIB"),
    "GB.XPD.RSDV.GD.ZS":("rnd_pct_gdp","% PIB"),"BX.KLT.DINV.WD.GD.ZS":("fdi_inflows_pct_gdp","% PIB"),
    "NE.EXP.GNFS.ZS":("exports_pct_gdp","% PIB"),"NE.IMP.GNFS.ZS":("imports_pct_gdp","% PIB"),
    "NE.RSB.GNFS.ZS":("trade_balance_pct_gdp","% PIB"),"GC.DOD.TOTL.GD.ZS":("gov_debt_pct_gdp_wb","% PIB"),
    "IT.NET.USER.ZS":("internet_users_pct","%"),"SE.TER.ENRR":("tertiary_enrollment","%"),
    "SE.SEC.ENRR":("school_enrollment_secondary","%"),"SE.ADT.LITR.ZS":("literacy_rate","%"),
    "SP.POP.TOTL":("population","hab."),"SP.URB.TOTL.IN.ZS":("urbanization","%"),
}
NEW_COUNTRIES = ["AO","MZ","CV","GW","ST","BR","US","JP","CA","GB","CN","IN","ZA","MX","KR","TR","NO","CH","AR","CL","NG","EG","ID","TH","MY"]

def fetch_wb(wb_code, countries, since=1990):
    country_str = ";".join(c.lower() for c in countries)
    url = f"https://api.worldbank.org/v2/country/{country_str}/indicator/{wb_code}?format=json&per_page=32500&date={since}:2030"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR {wb_code}: {e}", file=sys.stderr); return []
    if not isinstance(data, list) or len(data) < 2 or not data[1]: return []
    rows = []
    for item in data[1]:
        if item.get("value") is None: continue
        c = item.get("country",{}).get("id","").upper()
        if c: rows.append({"country":c,"year":str(item["date"]),"value":float(item["value"])})
    return rows

def collect_worldbank(conn):
    print("\n=== WorldBank Multi-Country ===")
    country_set = set(NEW_COUNTRIES)
    total = 0
    for wb_code, (ind_name, unit) in WB_INDICATORS.items():
        print(f"  [{ind_name}]...", end=" ", flush=True)
        rows = [r for r in fetch_wb(wb_code, NEW_COUNTRIES) if r["country"] in country_set]
        print(f"{len(rows)} obs")
        if rows:
            db_rows = [{
                "source":"WORLDBANK","indicator":ind_name,"region":r["country"],
                "period":r["year"],"value":r["value"],"unit":unit,
                "category":None,"detail":None,"source_id":wb_code
            } for r in rows]
            total += upsert_rows(conn, db_rows)
        time.sleep(0.3)
    print(f"  WorldBank total: {total}")
    return total

# ===== MAIN =====
def main():
    args = sys.argv[1:]
    run_all = not args or "--all" in args
    do_eurostat = run_all or "--eurostat" in args
    do_ine      = run_all or "--ine" in args
    do_wb       = run_all or "--worldbank" in args

    print("="*60)
    print(f"Staging DB: {STAGING_DB}")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("="*60)

    conn = duckdb.connect(str(STAGING_DB), read_only=False)
    ensure_db(conn)
    totals = {}

    if do_eurostat:
        totals["eurostat"] = collect_eurostat(conn)
        conn.commit()
    if do_ine:
        totals["ine"] = collect_ine(conn)
        conn.commit()
    if do_wb:
        totals["worldbank"] = collect_worldbank(conn)
        conn.commit()

    conn.close()
    print("\n"+"="*60)
    print("DONE")
    for src, n in totals.items():
        print(f"  {src:12} → {n} rows")
    print(f"\nStaging: {STAGING_DB}")
    print("Next: python3 scripts/merge_staging.py (after dc-jarbas-down cae-dashboard)")
    print("="*60)

if __name__ == "__main__":
    main()
