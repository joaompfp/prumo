#!/usr/bin/env python3
"""
collect_scheduled.py — Scheduled data collection with per-source frequencies.

Checks collection_log in DuckDB to determine which sources are due,
runs the appropriate collectors, writes Parquet to staging, and calls
ingest.py to UPSERT into production.

Usage:
  python scripts/collect_scheduled.py              # run due collections
  python scripts/collect_scheduled.py --force      # ignore schedule, run all
  python scripts/collect_scheduled.py --status     # show last collection times
  python scripts/collect_scheduled.py --source INE # run only INE

Cron (replaces audit-only cron):
  0 3 * * * cd /app && python scripts/collect_scheduled.py && python scripts/audit_nightly.py
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "collectors"))

DEFAULT_DB = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
FETCHED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

FREQ_HOURS = {
    "hourly": 1,
    "daily": 24,
    "weekly": 168,
    "monthly": 720,
}

# ── Collection schedule ──────────────────────────────────────────────
# Each source has freq + a collect_fn name (defined below) that wraps
# the existing collector APIs into flat DB-schema rows.

SCHEDULE = {
    "INE":       {"freq": "daily",   "description": "INE — IPC, emprego, construção, habitação"},
    "BPORTUGAL": {"freq": "daily",   "description": "BdP — Euribor, yields, crédito"},
    "EUROSTAT":  {"freq": "weekly",  "description": "Eurostat — IPI, desemprego, PIB, HICP"},
    "FRED":      {"freq": "weekly",  "description": "FRED — Brent, cobre, gás, EUR/USD"},
    "WORLDBANK": {"freq": "monthly", "description": "World Bank — PIB, I&D, Gini, emprego"},
    "REN":       {"freq": "daily",   "description": "REN — Eólica, solar, hídrica, consumo"},
    "DGEG":      {"freq": "daily",   "description": "DGEG — Combustíveis (gasóleo, gasolina)"},
    "EREDES":    {"freq": "weekly",  "description": "E-REDES — Distribuição eléctrica"},
}


# ── Collector wrappers ───────────────────────────────────────────────
# Each wrapper calls the actual collector methods (get_financial_dashboard,
# get_monthly_balance, etc.) and flattens the result into DB-schema rows.
# This is the glue between the scheduler and the heterogeneous collector APIs.

def _flatten_dashboard(dashboard: dict, source: str, default_unit: str = "") -> list:
    """Flatten a dashboard dict {indicator: {data: [{period,value,...}]}} into rows."""
    rows = []
    for key, section in dashboard.items():
        if key.startswith("_"):
            continue
        if isinstance(section, dict) and "data" in section:
            indicator = section.get("indicator", key)
            unit = section.get("unit", default_unit)
            for obs in section["data"]:
                if obs.get("value") is None:
                    continue
                rows.append({
                    "source": source, "indicator": indicator,
                    "region": obs.get("region", "PT"), "period": obs["period"],
                    "value": float(obs["value"]), "unit": obs.get("unit", unit),
                    "category": None, "detail": obs.get("detail"),
                    "fetched_at": FETCHED_AT, "source_id": None,
                })
    return rows


def _flatten_ine_result(result: dict, source: str = "INE") -> list:
    """Flatten INE indicator result into DB rows.

    INE returns: {indicator, data: [{period_sort, value, geo, geo_name, ...}]}
    or dashboard: {key: {indicator, data: [...]}} — handle both.
    """
    rows = []
    # If it's a dashboard (outer keys map to indicator dicts)
    if result and not result.get("data") and not result.get("indicator"):
        for key, section in result.items():
            if key.startswith("_") or not isinstance(section, dict):
                continue
            rows.extend(_flatten_ine_result(section, source))
        return rows

    # Single indicator result
    indicator = result.get("indicator", "unknown")
    for obs in result.get("data", []):
        if obs.get("value") is None:
            continue
        # Use period_sort (YYYY-MM) if available, else period string
        period = obs.get("period_sort") or obs.get("period", "")
        region = obs.get("geo_name", obs.get("geo", "PT"))
        if not period:
            continue
        rows.append({
            "source": source, "indicator": indicator,
            "region": region, "period": period,
            "value": float(obs["value"]), "unit": result.get("unit", "%"),
            "category": None, "detail": obs.get("dim_3_t"),
            "fetched_at": FETCHED_AT, "source_id": result.get("varcd"),
        })
    return rows


def collect_ine() -> list:
    from ine import INEClient
    client = INEClient()
    rows = []
    for method in ["get_ipc", "get_hicp", "get_unemployment", "get_employment",
                    "get_gdp", "get_ipi", "get_confidence"]:
        try:
            result = getattr(client, method)()
            rows.extend(_flatten_ine_result(result, "INE"))
            print(f"    ine.{method}: {len(rows)} rows so far")
        except Exception as e:
            print(f"    ine.{method}: {e}")
    return rows


def collect_bportugal() -> list:
    from bportugal import BPortugalClient
    client = BPortugalClient()
    result = client.get_financial_dashboard()
    return _flatten_dashboard(result, "BPORTUGAL")


def collect_eurostat() -> list:
    from eurostat import EurostatClient
    client = EurostatClient()
    rows = []
    for method in ["get_industrial_dashboard", "get_hicp_portugal",
                    "get_unemployment_portugal", "get_gdp_portugal",
                    "get_electricity_prices"]:
        try:
            result = getattr(client, method)()
            rows.extend(_flatten_dashboard(result, "EUROSTAT"))
        except Exception as e:
            print(f"    eurostat.{method}: {e}")
    return rows


def collect_fred() -> list:
    from fred import FREDClient
    client = FREDClient()
    dashboard = client.get_commodity_dashboard()
    rows = []
    for key, section in dashboard.items():
        if key.startswith("_") or "error" in section:
            continue
        if isinstance(section, dict) and "data" in section:
            for obs in section["data"]:
                if obs.get("value") is None:
                    continue
                # FRED uses "date" (YYYY-MM-DD), convert to YYYY-MM period
                date = obs.get("date", "")
                period = date[:7] if date else None
                if not period:
                    continue
                rows.append({
                    "source": "FRED", "indicator": key,
                    "region": "WORLD", "period": period,
                    "value": float(obs["value"]), "unit": section.get("unit", ""),
                    "category": "Commodities", "detail": section.get("series"),
                    "fetched_at": FETCHED_AT, "source_id": obs.get("series_id"),
                })
    return rows


def collect_worldbank() -> list:
    from worldbank import WorldBankClient
    client = WorldBankClient()
    rows = []
    for ind_key in list(client.INDICATORS.keys())[:15]:
        try:
            result = client.get_indicator("PT", ind_key, start_year=2010)
            if isinstance(result, dict) and "data" in result:
                for obs in result["data"]:
                    if obs.get("value") is None:
                        continue
                    # WorldBank uses "year" (int), convert to YYYY period string
                    year = obs.get("year") or obs.get("period")
                    if not year:
                        continue
                    rows.append({
                        "source": "WORLDBANK", "indicator": ind_key,
                        "region": "PT", "period": str(year),
                        "value": float(obs["value"]), "unit": result.get("unit", ""),
                        "category": None, "detail": None,
                        "fetched_at": FETCHED_AT, "source_id": None,
                    })
        except Exception as e:
            print(f"    worldbank.{ind_key}: {e}")
    return rows


def collect_ren() -> list:
    from ren import RENClient
    client = RENClient()
    rows = []
    # Monthly balance (production by source)
    balance = client.get_monthly_balance(months=3)
    rows.extend(_flatten_dashboard(balance, "REN", default_unit="GWh"))
    # Market prices
    try:
        prices = client.get_market_prices(months=3)
        rows.extend(_flatten_dashboard(prices, "REN", default_unit="€/MWh"))
    except Exception as e:
        print(f"    ren.get_market_prices: {e}")
    return rows


def collect_dgeg() -> list:
    from dgeg_fuel_api import DGEGFuelPricesClient, FUEL_DIESEL, FUEL_GASOLINE_95
    client = DGEGFuelPricesClient()
    rows = []
    today = datetime.now(timezone.utc).strftime("%Y-%m")
    # Use known fuel type constants — DGEG API filter is broken (always returns GPL Auto)
    # so we use the direct cheapest_stations endpoint with known IDs
    for fid, fname in [(FUEL_DIESEL, "gasóleo"), (FUEL_GASOLINE_95, "gasolina_95")]:
        try:
            result = client.search_stations(fuel_type_id=fid, sort=1, limit=1)
            # Returns {"source":..., "count":..., "data": [{...}]}
            data = result.get("data", []) if isinstance(result, dict) else result
            if data:
                station = data[0]
                raw_price = (station.get("Preco") or station.get("price") or
                             station.get("preco") or station.get("Price") or "")
                # Price comes as "0,829 €" — strip non-numeric, replace comma
                price_str = str(raw_price).replace(",", ".").replace("€", "").replace(" ", "")
                try:
                    price = float(price_str)
                    rows.append({
                        "source": "DGEG", "indicator": f"fuel_{fname}",
                        "region": "PT", "period": today,
                        "value": price, "unit": "€/litro",
                        "category": "Combustíveis", "detail": fname,
                        "fetched_at": FETCHED_AT, "source_id": None,
                    })
                except ValueError:
                    print(f"    dgeg.{fname}: could not parse price '{raw_price}'")
        except Exception as e:
            print(f"    dgeg.{fname}: {e}")
    return rows


def collect_eredes() -> list:
    from eredes import EREDESClient
    client = EREDESClient()
    rows = []
    now = datetime.now(timezone.utc)
    try:
        result = client.get_national_production(year=now.year, month=now.month)
        rows.extend(_flatten_dashboard(result, "EREDES", default_unit="GWh"))
    except Exception as e:
        print(f"    eredes.get_national_production: {e}")
    return rows


# Map source name → wrapper function
COLLECTORS = {
    "INE": collect_ine,
    "BPORTUGAL": collect_bportugal,
    "EUROSTAT": collect_eurostat,
    "FRED": collect_fred,
    "WORLDBANK": collect_worldbank,
    "REN": collect_ren,
    "DGEG": collect_dgeg,
    "EREDES": collect_eredes,
}


# ── Scheduling logic ────────────────────────────────────────────────

def get_last_collection(conn, source: str) -> datetime | None:
    """Get the most recent successful collection timestamp for a source."""
    try:
        row = conn.execute(
            "SELECT MAX(ts) FROM collection_log WHERE source=? AND status='ok'",
            [source],
        ).fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0].replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def is_due(conn, source: str, freq: str) -> bool:
    """Check if a source is due for collection based on its frequency."""
    last = get_last_collection(conn, source)
    if last is None:
        return True
    hours = FREQ_HOURS.get(freq, 24)
    return datetime.now(timezone.utc) - last > timedelta(hours=hours)


def show_status(conn):
    """Print last collection times for all scheduled sources."""
    print(f"{'Source':<12} {'Freq':<8} {'Last Collection':<24} {'Status'}")
    print("-" * 65)
    for source, config in sorted(SCHEDULE.items()):
        last = get_last_collection(conn, source)
        freq = config["freq"]
        due = is_due(conn, source, freq)
        last_str = last.strftime("%Y-%m-%d %H:%M UTC") if last else "never"
        status = "DUE" if due else "ok"
        print(f"{source:<12} {freq:<8} {last_str:<24} {status}")


def main():
    parser = argparse.ArgumentParser(description="Scheduled data collection")
    parser.add_argument("--db", default=DEFAULT_DB, help="DuckDB path")
    parser.add_argument("--force", action="store_true", help="Ignore schedule, run all")
    parser.add_argument("--status", action="store_true", help="Show collection status")
    parser.add_argument("--source", help="Run only this source")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    args = parser.parse_args()

    import duckdb
    conn = duckdb.connect(str(args.db))

    # Ensure collection_log table exists
    conn.execute("""CREATE TABLE IF NOT EXISTS collection_log (
        ts VARCHAR, source VARCHAR, indicator VARCHAR,
        rows_added INTEGER, status VARCHAR, duration_ms INTEGER,
        parquet_file VARCHAR)""")

    if args.status:
        show_status(conn)
        conn.close()
        return

    # Determine which sources to run
    sources_to_run = {}
    for source, config in SCHEDULE.items():
        if args.source and source != args.source.upper():
            continue
        if args.force or is_due(conn, source, config["freq"]):
            sources_to_run[source] = config

    if not sources_to_run:
        print("[scheduler] all sources up to date, nothing to do")
        conn.close()
        return

    print(f"[scheduler] {len(sources_to_run)} source(s) due: "
          f"{', '.join(sources_to_run.keys())}")

    if args.dry_run:
        for src, cfg in sources_to_run.items():
            print(f"  would run: {src} ({cfg['description']})")
        conn.close()
        return

    # Run collectors and write Parquet
    from base import write_parquet
    total_rows = 0

    for source, config in sources_to_run.items():
        print(f"\n  {source}: {config['description']}", flush=True)
        collect_fn = COLLECTORS.get(source)
        if not collect_fn:
            print(f"    no collector wrapper for {source}")
            continue

        t0 = time.time()
        try:
            rows = collect_fn()
        except Exception as e:
            print(f"    error: {e}", flush=True)
            rows = []
        duration_ms = round((time.time() - t0) * 1000)

        if rows:
            try:
                write_parquet(rows, source=source)
                total_rows += len(rows)
                print(f"    {len(rows)} rows -> staging ({duration_ms}ms)")
            except Exception as e:
                print(f"    parquet write error: {e}")
        else:
            print(f"    no data returned ({duration_ms}ms)")

    conn.close()

    # Run ingestion pipeline
    if total_rows > 0:
        print(f"\n[scheduler] running ingest.py for {total_rows} staged rows...")
        os.system(f"{sys.executable} {SCRIPT_DIR / 'ingest.py'} --db {args.db}")

    print(f"\n[scheduler] done — {total_rows} total rows collected")


if __name__ == "__main__":
    main()
