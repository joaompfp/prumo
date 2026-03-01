#!/usr/bin/env python3
"""
CAE Dashboard V4 — Data backfill script.

Fetches full historical data from INE API and stores in cae-data.db with
sector-specific indicator names to avoid UNIQUE constraint collisions.

Indicators stored:
  ipi_seasonal_cae_<SECTOR>  — Full IPI seasonal per CAE sector (2005-2025)
  gdp_yoy                    — PIB variação homóloga trimestral (2005-2025)
  imports_monthly            — Importações mundiais mensais (2005-2025)
  exports_monthly            — Exportações mundiais mensais (2005-2025)

Notes:
  - INE UNIQUE: (source, indicator, region, period) — no detail in key
  - Multi-sector IPI must use sector-specific indicator names
  - Trade data uses Dim2=MUNDO (world total), Dim3=T (all goods)
"""

import sqlite3
import sys
import json
import time
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

DB_PATH = SKILL_DIR / "data" / "cae-data.db"
INE_DATA_URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp"

# PT month name → number
_PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_PT_QUARTERS = {
    "1.º trimestre": 1, "2.º trimestre": 4,
    "3.º trimestre": 7, "4.º trimestre": 10,
}


def period_sort(period_name: str) -> str:
    """Convert Portuguese period name → sortable YYYY-MM."""
    low = period_name.lower().strip()
    for m, n in _PT_MONTHS.items():
        if low.startswith(m):
            year = low.split()[-1]
            return f"{year}-{n:02d}"
    for q, m in _PT_QUARTERS.items():
        if q in low:
            year = low.split()[-1]
            return f"{year}-{m:02d}"
    if low.isdigit() and len(low) == 4:
        return f"{low}-00"
    return period_name


def gen_monthly_codes(start_year=2005, end_year=None):
    """Generate S3A monthly codes from start_year to end_year (inclusive)."""
    if end_year is None:
        end_year = datetime.now().year
    codes = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == datetime.now().year and month > datetime.now().month:
                break
            codes.append(f"S3A{year}{month:02d}")
    return codes


def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def upsert_points(conn, points):
    """Bulk insert/replace data points."""
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO indicators
           (source, indicator, region, period, value, unit,
            category, detail, fetched_at, source_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(p["source"], p["indicator"], p["region"], p["period"],
          p["value"], p["unit"], p["category"], p["detail"],
          now, p["source_id"]) for p in points]
    )
    conn.commit()
    return len(points)


def ine_fetch(varcd, params):
    """Single INE API request, returns Dados dict or raises."""
    resp = requests.get(INE_DATA_URL, params={"op": "2", "varcd": varcd,
                                               "lang": "PT", **params},
                        timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return {}
    rec = data[0] if isinstance(data, list) else data
    sucesso = rec.get("Sucesso", {})
    if "Falso" in sucesso:
        msg = sucesso["Falso"][0].get("Msg", "Unknown error")
        raise RuntimeError(f"INE API: {msg}")
    return rec.get("Dados", {})


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: IPI Seasonal — all sectors, full history
# ─────────────────────────────────────────────────────────────────────────────

def fetch_store_ipi_all_sectors(conn):
    """Fetch IPI seasonal with Dim1=T (all periods, all sectors) and store
    per-sector with indicator name ipi_seasonal_cae_<SECTOR_CODE>."""
    print("Fetching IPI seasonal — all sectors, all periods (Dim1=T)...")
    dados = ine_fetch("0011889", {"Dim1": "T"})
    print(f"  → {len(dados)} periods in response")

    # Group observations by sector (dim_3) and period
    by_sector = {}
    for period_name, entries in dados.items():
        ps = period_sort(period_name)
        for entry in entries:
            sector = entry.get("dim_3", "UNK")
            valor = entry.get("valor")
            if valor is None or valor == "":
                continue
            try:
                value = float(valor)
            except (ValueError, TypeError):
                continue

            if sector not in by_sector:
                by_sector[sector] = []
            by_sector[sector].append({
                "period": ps,
                "value": value,
                "sector_name": entry.get("dim_3_t", ""),
            })

    # Store each sector as separate indicator
    total = 0
    for sector_code in sorted(by_sector.keys()):
        obs = by_sector[sector_code]
        indicator_name = f"ipi_seasonal_cae_{sector_code}"
        sector_label = obs[0]["sector_name"] if obs else ""

        points = [{
            "source": "INE",
            "indicator": indicator_name,
            "region": "PT",
            "period": o["period"],
            "value": o["value"],
            "unit": "index_2021=100",
            "category": "ipi",
            "detail": json.dumps({"sector": sector_code, "label": sector_label},
                                 ensure_ascii=False),
            "source_id": "0011889",
        } for o in obs]

        n = upsert_points(conn, points)
        periods = sorted(o["period"] for o in obs)
        print(f"  ✓ {sector_code:4} ({sector_label[:35]:35}) — {n:3} pts | "
              f"{periods[0]} → {periods[-1]}")
        total += n

    print(f"  Total IPI stored: {total} pts across {len(by_sector)} sectors")
    return total


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: PIB trimestral
# ─────────────────────────────────────────────────────────────────────────────

def fetch_store_gdp(conn):
    """Fetch PIB variação homóloga (0013431) — all quarters."""
    print("\nFetching PIB trimestral (0013431) — all quarters...")
    dados = ine_fetch("0013431", {"Dim1": "T"})
    print(f"  → {len(dados)} periods")

    points = []
    for period_name, entries in dados.items():
        ps = period_sort(period_name)
        for entry in entries:
            if entry.get("geocod", "PT") != "PT":
                continue
            valor = entry.get("valor")
            if valor is None or valor == "":
                continue
            try:
                value = float(valor)
            except (ValueError, TypeError):
                continue
            points.append({
                "source": "INE",
                "indicator": "gdp_yoy",
                "region": "PT",
                "period": ps,
                "value": value,
                "unit": "%",
                "category": "macro",
                "detail": "",
                "source_id": "0013431",
            })

    if points:
        points.sort(key=lambda p: p["period"])
        n = upsert_points(conn, points)
        print(f"  ✓ gdp_yoy — {n} pts | {points[0]['period']} → {points[-1]['period']}")
        return n
    print("  ✗ No data")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 & 4: Trade (imports / exports) — batched fetching
# ─────────────────────────────────────────────────────────────────────────────

def fetch_store_trade(conn, varcd, indicator_name, label,
                      start_year=2005, batch_size=24):
    """Fetch trade data (imports or exports) in batches.

    Uses Dim2=MUNDO (world total) + Dim3=T (all goods) to get aggregate.
    Batches by month to avoid API row limit.
    """
    print(f"\nFetching {label} ({varcd}) — {start_year}→present, batch={batch_size}m...")

    all_codes = gen_monthly_codes(start_year)
    batches = [all_codes[i:i+batch_size] for i in range(0, len(all_codes), batch_size)]
    print(f"  → {len(all_codes)} months in {len(batches)} batches")

    all_points = []
    errors = 0

    for i, batch in enumerate(batches):
        try:
            dados = ine_fetch(varcd, {
                "Dim1": ",".join(batch),
                "Dim2": "MUNDO",
                "Dim3": "T",
            })
            for period_name, entries in dados.items():
                ps = period_sort(period_name)
                for entry in entries:
                    valor = entry.get("valor")
                    if valor is None or valor == "":
                        continue
                    try:
                        value = float(valor)
                    except (ValueError, TypeError):
                        continue
                    if value == 0:
                        continue  # skip suppressed/zero entries
                    all_points.append({
                        "source": "INE",
                        "indicator": indicator_name,
                        "region": "PT",
                        "period": ps,
                        "value": value,
                        "unit": "EUR",
                        "category": "trade",
                        "detail": json.dumps({"cgce": "T", "origin": "MUNDO"},
                                             ensure_ascii=False),
                        "source_id": varcd,
                    })
        except Exception as e:
            errors += 1
            print(f"  ✗ Batch {i+1}/{len(batches)}: {e}")

        # Small delay between batches to be polite to the API
        if i < len(batches) - 1:
            time.sleep(0.3)

        # Progress every 5 batches
        if (i + 1) % 5 == 0 or i == len(batches) - 1:
            print(f"  Batch {i+1}/{len(batches)} done, {len(all_points)} pts so far")

    if all_points:
        # Deduplicate — keep last value per period (in case of overlapping batches)
        by_period = {}
        for p in all_points:
            by_period[p["period"]] = p
        deduped = sorted(by_period.values(), key=lambda p: p["period"])
        n = upsert_points(conn, deduped)
        print(f"  ✓ {indicator_name} — {n} pts | "
              f"{deduped[0]['period']} → {deduped[-1]['period']}")
        if errors:
            print(f"  ⚠ {errors} batch errors encountered")
        return n
    print(f"  ✗ No data (errors: {errors})")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_results(conn):
    cur = conn.cursor()
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    print("\nIPI Seasonal por sector (ipi_seasonal_cae_*):")
    cur.execute("""
        SELECT indicator, COUNT(*), MIN(period), MAX(period)
        FROM indicators
        WHERE indicator LIKE 'ipi_seasonal_cae_%'
        GROUP BY indicator
        ORDER BY indicator
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:35} | {r[1]:4} pts | {r[2]} → {r[3]}")

    print("\nNovos indicadores macro/trade:")
    for ind in ["gdp_yoy", "imports_monthly", "exports_monthly"]:
        cur.execute("""
            SELECT COUNT(*), MIN(period), MAX(period)
            FROM indicators WHERE indicator = ?
        """, (ind,))
        r = cur.fetchone()
        if r and r[0]:
            print(f"  {ind:25} | {r[0]:4} pts | {r[1]} → {r[2]}")
        else:
            print(f"  {ind:25} | NO DATA")

    # Old ipi_seasonal_cae (legacy)
    cur.execute("SELECT COUNT(*) FROM indicators WHERE indicator='ipi_seasonal_cae'")
    legacy = cur.fetchone()[0]
    print(f"\n  ipi_seasonal_cae (legacy) — {legacy} pts (will be superseded by sector-specific)")

    cur.execute("SELECT COUNT(*) FROM indicators")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in indicators table: {total}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("="*80)
    print("CAE Dashboard V4 — INE Data Backfill")
    print(f"DB: {DB_PATH}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    if not DB_PATH.exists():
        print("ERROR: DB not found!")
        sys.exit(1)

    conn = connect()

    # 1. IPI Seasonal — all sectors
    print("\n>>> STEP 1: IPI Seasonal (all sectors, full history)")
    print("-"*60)
    fetch_store_ipi_all_sectors(conn)

    # 2. PIB trimestral
    print("\n>>> STEP 2: PIB Trimestral")
    print("-"*60)
    fetch_store_gdp(conn)

    # 3. Imports
    print("\n>>> STEP 3: Importações Mensais")
    print("-"*60)
    fetch_store_trade(conn, "0001397", "imports_monthly", "Importações",
                      start_year=2005, batch_size=24)

    # 4. Exports
    print("\n>>> STEP 4: Exportações Mensais")
    print("-"*60)
    fetch_store_trade(conn, "0001400", "exports_monthly", "Exportações",
                      start_year=2005, batch_size=24)

    # 5. Verify
    verify_results(conn)
    conn.close()

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
