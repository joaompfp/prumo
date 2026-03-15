#!/usr/bin/env python3
"""
Create seed DuckDB database for unit tests.

Usage:
    python scripts/create_seed_db.py

Creates seed_data/seed.duckdb with ~80 realistic rows covering:
  - Sources: ine, eurostat, bdp, fred, oecd, ren
  - Periods: monthly (2020-01..2025-12), quarterly (2020-Q1..2025-Q4), annual (2020..2025)
  - Indicators from catalog.py
"""

import os
import sys
from pathlib import Path

# Resolve project root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = os.environ.get("CAE_DB_PATH", str(ROOT / "seed_data" / "seed.duckdb"))


def main():
    import duckdb

    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Drop existing file
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing {db_path}")

    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE indicators (
            source  VARCHAR,
            indicator VARCHAR,
            period  VARCHAR,
            value   DOUBLE,
            unit    VARCHAR,
            region  VARCHAR,
            detail  VARCHAR
        )
    """)

    rows = []

    # ── INE ────────────────────────────────────────────────────────────────────
    # IPI Total (monthly, 2020-01..2025-12) — 6 representative months
    ine_monthly = [
        ("2020-03", 88.2), ("2020-09", 92.1), ("2021-06", 98.5),
        ("2022-01", 103.4), ("2023-06", 105.7), ("2024-11", 107.2),
    ]
    for period, value in ine_monthly:
        rows.append(("ine", "ipi_seasonal_cae_TOT", period, value,
                      "Índice 2021=100", "PT", None))

    # IPI YoY (monthly)
    ine_yoy = [
        ("2020-03", -8.5), ("2021-06", 4.2), ("2022-01", 5.1),
        ("2023-03", 1.3), ("2024-06", -0.8), ("2025-03", 2.1),
    ]
    for period, value in ine_yoy:
        rows.append(("ine", "ipi_yoy_cae", period, value, "%", "PT", None))

    # Employment industry (monthly)
    ine_emp = [
        ("2020-06", 94.5), ("2021-06", 97.2), ("2022-06", 100.8),
        ("2023-06", 102.1), ("2024-06", 103.5), ("2025-06", 104.2),
    ]
    for period, value in ine_emp:
        rows.append(("ine", "emp_industry_cae", period, value,
                      "Índice 2021=100", "PT", None))

    # Wages industry (monthly)
    ine_wages = [
        ("2020-06", 93.1), ("2021-06", 98.4), ("2022-06", 104.2),
        ("2023-06", 110.5), ("2024-06", 116.8), ("2025-06", 122.3),
    ]
    for period, value in ine_wages:
        rows.append(("ine", "wages_industry_cae", period, value,
                      "Índice 2021=100", "PT", None))

    # HICP YoY (monthly)
    ine_hicp = [
        ("2020-06", 0.2), ("2021-06", 0.8), ("2022-06", 8.7),
        ("2023-06", 5.1), ("2024-06", 2.9), ("2025-06", 2.1),
    ]
    for period, value in ine_hicp:
        rows.append(("ine", "hicp_yoy", period, value, "%", "PT", None))

    # Manufacturing confidence (monthly)
    ine_conf = [
        ("2020-03", -25.4), ("2021-01", -8.2), ("2022-06", 3.5),
        ("2023-06", -2.1), ("2024-06", 1.8), ("2025-06", 4.2),
    ]
    for period, value in ine_conf:
        rows.append(("ine", "conf_manufacturing", period, value,
                      "Saldo de respostas", "PT", None))

    # GDP YoY (quarterly)
    ine_gdp = [
        ("2020-Q1", -2.4), ("2020-Q2", -16.5), ("2021-Q1", 4.1),
        ("2022-Q1", 11.9), ("2023-Q1", 2.5), ("2024-Q1", 1.8),
        ("2025-Q1", 2.1), ("2025-Q2", 2.4),
    ]
    for period, value in ine_gdp:
        rows.append(("ine", "gdp_yoy", period, value, "%", "PT", None))

    # Exports monthly
    ine_exports = [
        ("2020-06", 5800.0), ("2021-06", 6200.0), ("2022-06", 7800.0),
        ("2023-06", 8100.0), ("2024-06", 8450.0), ("2025-06", 8700.0),
    ]
    for period, value in ine_exports:
        rows.append(("ine", "exports_monthly", period, value, "M€", "PT", None))

    # Imports monthly
    ine_imports = [
        ("2020-06", 6200.0), ("2021-06", 7100.0), ("2022-06", 9500.0),
        ("2023-06", 9200.0), ("2024-06", 9000.0), ("2025-06", 8900.0),
    ]
    for period, value in ine_imports:
        rows.append(("ine", "imports_monthly", period, value, "M€", "PT", None))

    # ── EUROSTAT ───────────────────────────────────────────────────────────────
    # IPI Portugal (monthly)
    eurostat_ipi = [
        ("2020-03", 86.5), ("2021-06", 97.8), ("2022-01", 102.1),
        ("2023-06", 104.3), ("2024-06", 106.5), ("2025-06", 108.1),
    ]
    for period, value in eurostat_ipi:
        rows.append(("eurostat", "ipi", period, value,
                      "Índice 2021=100", "PT", None))

    # Manufacturing PT (monthly)
    for period, value in eurostat_ipi:
        rows.append(("eurostat", "manufacturing", period, value * 0.98,
                      "Índice 2021=100", "PT", None))

    # Inflation EU (monthly)
    eurostat_inf = [
        ("2020-06", 0.3), ("2021-06", 1.9), ("2022-06", 8.6),
        ("2023-06", 5.5), ("2024-06", 2.5), ("2025-06", 2.0),
    ]
    for period, value in eurostat_inf:
        rows.append(("eurostat", "inflation", period, value, "%", "EU27", None))

    # Unemployment Portugal (monthly)
    eurostat_unemp = [
        ("2020-06", 7.2), ("2021-06", 6.8), ("2022-06", 6.0),
        ("2023-06", 6.4), ("2024-06", 6.2), ("2025-06", 5.9),
    ]
    for period, value in eurostat_unemp:
        rows.append(("eurostat", "unemployment", period, value, "%", "PT", None))

    # GDP quarterly Eurostat (multi-country, use PT)
    for period, value in ine_gdp:
        rows.append(("eurostat", "gdp_quarterly", period, value * 1.02,
                      "Índice", "PT", None))

    # Gov debt (annual)
    eurostat_debt = [
        ("2020", 135.2), ("2021", 127.4), ("2022", 113.9),
        ("2023", 99.1), ("2024", 97.3), ("2025", 96.0),
    ]
    for period, value in eurostat_debt:
        rows.append(("eurostat", "gov_debt_pct_gdp", period, value, "% PIB", "PT", None))

    # Employment rate (annual)
    eurostat_emp_rate = [
        ("2020", 69.2), ("2021", 70.1), ("2022", 71.8),
        ("2023", 73.1), ("2024", 74.2), ("2025", 74.8),
    ]
    for period, value in eurostat_emp_rate:
        rows.append(("eurostat", "employment_rate", period, value, "%", "PT", None))

    # ── BDP (Banco de Portugal) ─────────────────────────────────────────────────
    # Euribor 3m (monthly)
    bdp_euribor3m = [
        ("2020-01", -0.37), ("2021-01", -0.55), ("2022-01", -0.57),
        ("2022-07", 0.24), ("2023-01", 2.16), ("2023-09", 3.96),
        ("2024-01", 3.91), ("2024-09", 3.50), ("2025-01", 2.65),
        ("2025-06", 2.10),
    ]
    for period, value in bdp_euribor3m:
        rows.append(("bdp", "euribor_3m", period, value, "%", "EA", None))

    # Euribor 12m (monthly)
    bdp_euribor12m = [
        ("2020-01", -0.25), ("2021-01", -0.50), ("2022-01", -0.48),
        ("2022-07", 0.66), ("2023-01", 3.00), ("2023-09", 4.16),
        ("2024-01", 3.61), ("2025-01", 2.41), ("2025-06", 2.05),
    ]
    for period, value in bdp_euribor12m:
        rows.append(("bdp", "euribor_12m", period, value, "%", "EA", None))

    # PT 10y yield (monthly)
    bdp_pt10y = [
        ("2020-01", 0.44), ("2021-01", 0.08), ("2022-06", 2.47),
        ("2023-01", 3.75), ("2023-09", 3.50), ("2024-01", 3.21),
        ("2025-01", 3.10), ("2025-06", 3.05),
    ]
    for period, value in bdp_pt10y:
        rows.append(("bdp", "pt_10y", period, value, "%", "PT", None))

    # EUR/USD (monthly)
    bdp_eurusd = [
        ("2020-01", 1.109), ("2021-01", 1.214), ("2022-01", 1.139),
        ("2022-09", 0.980), ("2023-01", 1.087), ("2024-01", 1.094),
        ("2025-01", 1.042), ("2025-06", 1.085),
    ]
    for period, value in bdp_eurusd:
        rows.append(("bdp", "eur_usd", period, value, "USD/EUR", "EA", None))

    # Credit housing (monthly)
    bdp_credit = [
        ("2020-06", 98500.0), ("2021-06", 97800.0), ("2022-06", 99200.0),
        ("2023-06", 101500.0), ("2024-06", 103200.0), ("2025-06", 105100.0),
    ]
    for period, value in bdp_credit:
        rows.append(("bdp", "credit_housing", period, value, "M€", "PT", None))

    # ── FRED ───────────────────────────────────────────────────────────────────
    # Brent oil (monthly)
    fred_brent = [
        ("2020-03", 32.01), ("2020-09", 41.50), ("2021-06", 73.47),
        ("2022-06", 114.76), ("2023-06", 75.12), ("2024-06", 84.70),
        ("2025-01", 79.90), ("2025-06", 82.30),
    ]
    for period, value in fred_brent:
        rows.append(("fred", "brent_oil", period, value, "USD/bbl", "GLOBAL", None))

    # Natural gas (monthly)
    fred_gas = [
        ("2020-06", 1.63), ("2021-06", 3.45), ("2022-06", 8.11),
        ("2023-06", 2.59), ("2024-06", 2.75), ("2025-06", 3.10),
    ]
    for period, value in fred_gas:
        rows.append(("fred", "natural_gas", period, value, "USD/MMBtu", "US", None))

    # Copper (monthly)
    fred_copper = [
        ("2020-06", 5845.0), ("2021-06", 9832.0), ("2022-06", 8285.0),
        ("2023-06", 8426.0), ("2024-06", 9850.0), ("2025-06", 9650.0),
    ]
    for period, value in fred_copper:
        rows.append(("fred", "copper", period, value, "USD/t", "GLOBAL", None))

    # Aluminum (monthly)
    fred_al = [
        ("2020-06", 1556.0), ("2021-06", 2490.0), ("2022-06", 2523.0),
        ("2023-06", 2205.0), ("2024-06", 2645.0), ("2025-06", 2520.0),
    ]
    for period, value in fred_al:
        rows.append(("fred", "aluminum", period, value, "USD/t", "GLOBAL", None))

    # ── OECD ───────────────────────────────────────────────────────────────────
    # CLI Portugal (monthly)
    oecd_cli = [
        ("2020-03", 96.8), ("2020-09", 98.2), ("2021-06", 101.5),
        ("2022-01", 100.2), ("2023-06", 99.8), ("2024-06", 100.9),
        ("2025-01", 101.2), ("2025-06", 101.8),
    ]
    for period, value in oecd_cli:
        rows.append(("oecd", "cli", period, value, "Índice", "PT", None))

    # Production outlook BTS (monthly)
    oecd_prod = [
        ("2020-06", -12.5), ("2021-06", 8.3), ("2022-06", 5.1),
        ("2023-06", 1.2), ("2024-06", 3.5), ("2025-06", 4.8),
    ]
    for period, value in oecd_prod:
        rows.append(("oecd", "production", period, value, "Saldo", "PT", None))

    # Order books BTS (monthly)
    oecd_orders = [
        ("2020-06", -18.2), ("2021-06", 5.5), ("2022-06", 3.8),
        ("2023-06", -1.5), ("2024-06", 2.1), ("2025-06", 3.2),
    ]
    for period, value in oecd_orders:
        rows.append(("oecd", "order_books", period, value, "Saldo", "PT", None))

    # Unemployment OECD (monthly)
    oecd_unemp = [
        ("2020-06", 7.0), ("2021-06", 6.6), ("2022-06", 5.9),
        ("2023-06", 6.3), ("2024-06", 6.1), ("2025-06", 5.8),
    ]
    for period, value in oecd_unemp:
        rows.append(("oecd", "unemp_m", period, value, "%", "PT", None))

    # ── REN ────────────────────────────────────────────────────────────────────
    # MIBEL electricity price (monthly)
    ren_mibel = [
        ("2020-06", 28.5), ("2021-06", 75.2), ("2022-06", 201.4),
        ("2023-06", 89.6), ("2024-06", 52.3), ("2025-06", 65.1),
    ]
    for period, value in ren_mibel:
        rows.append(("ren", "electricity_price_mibel", period, value,
                      "€/MWh", "PT", None))

    # Hydro production (monthly)
    ren_hydro = [
        ("2020-06", 1850.0), ("2021-06", 2100.0), ("2022-06", 980.0),
        ("2023-06", 1650.0), ("2024-06", 2200.0), ("2025-06", 1900.0),
    ]
    for period, value in ren_hydro:
        rows.append(("ren", "electricity_hydro", period, value, "GWh", "PT", None))

    # Wind production (monthly)
    ren_wind = [
        ("2020-06", 1250.0), ("2021-06", 1380.0), ("2022-06", 1100.0),
        ("2023-06", 1420.0), ("2024-06", 1580.0), ("2025-06", 1650.0),
    ]
    for period, value in ren_wind:
        rows.append(("ren", "electricity_wind", period, value, "GWh", "PT", None))

    # Solar production (monthly)
    ren_solar = [
        ("2020-06", 245.0), ("2021-06", 310.0), ("2022-06", 420.0),
        ("2023-06", 680.0), ("2024-06", 1050.0), ("2025-06", 1380.0),
    ]
    for period, value in ren_solar:
        rows.append(("ren", "electricity_solar", period, value, "GWh", "PT", None))

    # Total consumption (monthly)
    ren_cons = [
        ("2020-06", 4500.0), ("2021-06", 4650.0), ("2022-06", 4720.0),
        ("2023-06", 4680.0), ("2024-06", 4750.0), ("2025-06", 4820.0),
    ]
    for period, value in ren_cons:
        rows.append(("ren", "electricity_consumption", period, value, "GWh", "PT", None))

    # Insert all rows
    con.executemany(
        "INSERT INTO indicators VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    count = con.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
    con.close()

    print(f"✓ Created {db_path} with {count} rows")
    print(f"  Sources: {', '.join(sorted({r[0] for r in rows}))}")
    print(f"  Indicators: {len({r[1] for r in rows})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
