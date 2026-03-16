#!/usr/bin/env python3
"""
merge_staging.py — Merge staging DuckDB into production DuckDB.

Run ONLY after stopping the container:
  ssh f3nix dc-jarbas-down cae-dashboard
  python3 scripts/merge_staging.py
  ssh f3nix dc-jarbas-up cae-dashboard

The production DB must NOT be locked (container stopped).
"""
import sys, duckdb
from pathlib import Path
from datetime import datetime

APPDATA = Path(__file__).resolve().parent.parent.parent.parent.parent / "appdata/prumo"
PROD_DB    = APPDATA / "cae-data.duckdb"
STAGING_DB = APPDATA / "cae-data-staging.duckdb"

def main():
    if not STAGING_DB.exists():
        print(f"ERROR: Staging DB not found: {STAGING_DB}")
        sys.exit(1)
    if not PROD_DB.exists():
        print(f"ERROR: Production DB not found: {PROD_DB}")
        sys.exit(1)

    print("="*60)
    print(f"Merging {STAGING_DB}")
    print(f"     → {PROD_DB}")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("="*60)

    # Try to open production in write mode
    try:
        prod = duckdb.connect(str(PROD_DB), read_only=False)
    except Exception as e:
        print(f"ERROR opening production DB: {e}")
        print("Is the container still running? Stop it first: dc-jarbas-down cae-dashboard")
        sys.exit(1)

    staging = duckdb.connect(str(STAGING_DB), read_only=True)

    # Get staging data
    rows = staging.execute("SELECT * FROM indicators").fetchall()
    print(f"  Staging rows to merge: {len(rows)}")

    if not rows:
        print("  Nothing to merge.")
        prod.close(); staging.close()
        return

    # Merge into production
    # Count before
    before = prod.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]

    prod.executemany("""
        INSERT OR REPLACE INTO indicators
          (source, indicator, region, period, value, unit, category, detail, fetched_at, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9]) for r in rows])
    prod.commit()

    after = prod.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
    net_new = after - before

    print(f"  Before: {before} rows")
    print(f"  After:  {after} rows")
    print(f"  Net new: {net_new} rows")

    # Show summary by source
    summary = prod.execute("""
        SELECT source, indicator, MAX(period) as last
        FROM indicators
        WHERE source IN ('EUROSTAT','INE','WORLDBANK')
        AND indicator IN ('ipi','manufacturing','total_industry','metals','chemicals_pharma',
                          'machinery','transport_eq','rubber_plastics','construction_output',
                          'ipi_electronics','ipi_food_beverage','ipi_nonmetallic','ipi_textiles',
                          'ipi_wood_paper','exports_monthly','imports_monthly')
        GROUP BY source, indicator
        ORDER BY source, indicator
    """).fetchall()

    print("\n  Updated indicators:")
    for r in summary:
        print(f"    {r[0]:12} {r[1]:30} → {r[2]}")

    prod.close()
    staging.close()
    print(f"\nDone. {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("Now restart: ssh f3nix dc-jarbas-up cae-dashboard")

if __name__ == "__main__":
    main()
