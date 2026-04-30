#!/usr/bin/env python3
"""
ingest.py — Parquet → DuckDB ingestion pipeline.

Reads all .parquet files from data/staging/, UPSERTs into the production
DuckDB, logs results to collection_log table, and archives processed files.

Usage:
  python scripts/ingest.py                   # ingest all staged files
  python scripts/ingest.py --dry-run         # show what would be ingested
  python scripts/ingest.py --staging /path   # custom staging dir
"""
import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "collectors"))

DEFAULT_DB = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
DEFAULT_STAGING = Path(os.environ.get("PRUMO_STAGING_DIR", "/data/staging"))
DEFAULT_ARCHIVE = Path(os.environ.get("PRUMO_ARCHIVE_DIR", "/data/archive"))


def ensure_tables(conn):
    """Create indicators + collection_log tables if missing."""
    conn.execute("""CREATE TABLE IF NOT EXISTS indicators (
        source VARCHAR, indicator VARCHAR, region VARCHAR, period VARCHAR,
        value DOUBLE, unit VARCHAR, category VARCHAR, detail VARCHAR,
        fetched_at VARCHAR, source_id VARCHAR,
        PRIMARY KEY (source, indicator, region, period))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS collection_log (
        ts VARCHAR, source VARCHAR, indicator VARCHAR,
        rows_added INTEGER, status VARCHAR, duration_ms INTEGER,
        parquet_file VARCHAR)""")


def ingest_file(conn, filepath: Path, dry_run: bool = False) -> dict:
    """Ingest a single Parquet file into DuckDB.

    Returns summary dict with rows_added, source, indicators, duration_ms.
    """
    t0 = time.time()
    fname = filepath.name

    # DuckDB can read Parquet natively
    try:
        rows = conn.execute(
            f"SELECT * FROM read_parquet('{filepath}')"
        ).fetchall()
    except Exception as e:
        return {"file": fname, "error": str(e), "rows_added": 0}

    if not rows:
        return {"file": fname, "rows_added": 0, "skipped": "empty"}

    # Get column names from Parquet schema
    cols = conn.execute(
        f"SELECT * FROM read_parquet('{filepath}') LIMIT 0"
    ).description
    col_names = [c[0] for c in cols]

    # Discover target table columns
    db_cols_info = conn.execute("DESCRIBE indicators").fetchall()
    db_cols = [c[0] for c in db_cols_info]

    sources = set()
    indicators = set()
    n_upserted = 0

    for row in rows:
        rd = dict(zip(col_names, row))
        sources.add(rd.get("source", "?"))
        indicators.add(rd.get("indicator", "?"))

        if dry_run:
            n_upserted += 1
            continue

        # Map Parquet row to DB columns (only insert columns that exist in target)
        values = [rd.get(c) for c in db_cols]
        placeholders = ",".join(["?" for _ in db_cols])
        col_list = ",".join(db_cols)

        # DELETE existing row by natural key, then INSERT
        conn.execute(
            "DELETE FROM indicators WHERE source=? AND indicator=? AND region=? AND period=?",
            (rd.get("source"), rd.get("indicator"), rd.get("region", "PT"), rd.get("period")))
        conn.execute(f"INSERT INTO indicators ({col_list}) VALUES ({placeholders})", values)
        n_upserted += 1

    duration_ms = round((time.time() - t0) * 1000)

    # Log each source/indicator combo
    if not dry_run:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for src in sources:
            for ind in indicators:
                conn.execute(
                    "INSERT INTO collection_log VALUES (?,?,?,?,?,?,?)",
                    (ts, src, ind, n_upserted, "ok", duration_ms, fname),
                )

    return {
        "file": fname,
        "rows_added": n_upserted,
        "sources": sorted(sources),
        "indicators": sorted(indicators),
        "duration_ms": duration_ms,
    }


def archive_file(filepath: Path, archive_dir: Path):
    """Move processed Parquet file to archive directory."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    # Add date prefix for organization
    date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    dest = archive_dir / f"{date_prefix}_{filepath.name}"
    shutil.move(str(filepath), str(dest))
    return dest


def main():
    parser = argparse.ArgumentParser(description="Ingest Parquet files into DuckDB")
    parser.add_argument("--db", default=DEFAULT_DB, help="DuckDB path")
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested")
    args = parser.parse_args()

    import duckdb
    staging = args.staging
    if not staging.exists():
        print(f"[ingest] staging dir {staging} does not exist, nothing to do")
        return

    parquet_files = sorted(staging.glob("*.parquet"))
    if not parquet_files:
        print("[ingest] no .parquet files in staging, nothing to do")
        return

    print(f"[ingest] found {len(parquet_files)} file(s) in {staging}")

    conn = duckdb.connect(str(args.db))
    ensure_tables(conn)

    total_rows = 0
    results = []
    for pf in parquet_files:
        result = ingest_file(conn, pf, dry_run=args.dry_run)
        results.append(result)
        total_rows += result.get("rows_added", 0)

        if result.get("error"):
            print(f"  ✗ {pf.name}: {result['error']}")
        else:
            print(f"  ✓ {pf.name}: {result['rows_added']} rows "
                  f"({result.get('duration_ms', 0)}ms)")

        # Archive processed file (unless dry-run or error)
        if not args.dry_run and not result.get("error"):
            dest = archive_file(pf, args.archive)
            print(f"    → archived to {dest.name}")

    conn.close()
    action = "would ingest" if args.dry_run else "ingested"
    print(f"\n[ingest] {action} {total_rows} total rows from {len(parquet_files)} file(s)")


if __name__ == "__main__":
    main()
