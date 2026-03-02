#!/usr/bin/env python3
"""
normalize_db.py — Normalize indicator values to canonical units.

Reads the `indicators` table in cae-data.duckdb and applies a set of
unit-conversion rules defined in RULES below.  Safe by default: runs in
dry-run mode unless --apply is passed.

Rules are intentionally kept as a flat list so the Analyst can add new
entries after the full unit audit is complete.

Usage:
    python3 scripts/normalize_db.py               # dry-run (no DB changes)
    python3 scripts/normalize_db.py --apply       # write changes to DB
    python3 scripts/normalize_db.py --source DGEG # limit to one source
    python3 scripts/normalize_db.py --indicator aviation_jet_fuel --apply

Rules format:
    (source, indicator, operation, factor, old_unit, new_unit, reason)

    operation:
      'divide'   -> value = value / factor
      'multiply' -> value = value * factor
      'offset'   -> value = value + factor
"""

import argparse
import sys
import os
from pathlib import Path

# --- Paths ------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR   = SCRIPT_DIR.parent
# Respect CAE_DB_PATH env var (matches app/config.py)
DB_PATH = Path(os.environ.get("CAE_DB_PATH", str(BASE_DIR / "data" / "cae-data.duckdb")))


# --- Normalisation rules -----------------------------------------------------
# Each tuple: (source, indicator, operation, factor, old_unit, new_unit, reason)
#
# Add new rules here after the Analyst completes the unit audit.
# Commented-out entries are kept for audit trail only.
#
RULES = [
    # -- DGEG -----------------------------------------------------------------
    # aviation_jet_fuel was originally stored in EUR/m3; divided by 1000 to
    # get EUR/l.  The conversion was applied directly in the DB during the
    # import pipeline -- this rule is kept here for audit trail only.
    # Status: ALREADY_DONE -- values in DB are already in kt (volume metric)
    # ('DGEG', 'aviation_jet_fuel', 'divide', 1000, 'EUR/m3', 'EUR/l',
    #  'EUR/m3 -> EUR/l  [ALREADY_DONE in DB]'),

    # -- Placeholder: add rules here after Analyst unit audit -----------------
    # Example format (do not uncomment without verifying DB values first):
    # ('DGEG', 'some_indicator', 'divide', 1000, 'old_unit', 'new_unit', 'reason'),
    # ('EUROSTAT', 'some_indicator', 'multiply', 0.001, 'EUR', 'kEUR', 'reason'),
]


# --- WP-E4 PROPOSAL: raw/normalized architecture ----------------------------
#
# Current schema (single table):
#   indicators(source, indicator, region, period, value, unit,
#              category, detail, fetched_at, source_id)
#   ~185k rows | no explicit indexes (DuckDB columnar scan)
#   schema_version: 1 (meta table)
#
# Proposed separation (DO NOT implement yet -- Analyst review pending):
#
#   indicators_raw    -- unchanged values as fetched from the source
#     Same columns as current `indicators`.
#     Implicit PK: (source, indicator, region, period)
#     Suggested indexes: (source, indicator), (period)
#
#   indicators        -- canonical normalised values (repurposed from current)
#     Same columns +
#       norm_applied  BOOLEAN  DEFAULT FALSE  -- was a rule applied?
#       norm_version  INTEGER  DEFAULT NULL   -- RULES list version when normalised
#     POPULATED by: normalize_db.py --apply  (re-runs from raw = idempotent)
#     VIEW: indicators_v  (union raw + normalised, always canonical)
#
# Migration steps (pending Analyst sign-off):
#   1. RENAME TABLE indicators TO indicators_raw
#   2. CREATE TABLE indicators AS SELECT *, FALSE, NULL FROM indicators_raw
#   3. ALTER TABLE indicators ADD COLUMN norm_applied BOOLEAN DEFAULT FALSE
#   4. ALTER TABLE indicators ADD COLUMN norm_version INTEGER
#   5. python3 scripts/normalize_db.py --apply
#
# Benefit: raw data preserved; normalize_db.py is idempotent (re-derives
# canonical values from raw on each run, never compounds factors).
# ---------------------------------------------------------------------------


def _check_deps():
    """Ensure duckdb is available."""
    try:
        import duckdb  # noqa: F401
        return True
    except ImportError:
        print("ERROR: duckdb not installed. Run: pip install duckdb", file=sys.stderr)
        return False


def preview_rules(db_path, source_filter, indicator_filter):
    """Show what RULES would change without touching the DB."""
    import duckdb

    applicable = [
        r for r in RULES
        if (source_filter is None or r[0] == source_filter)
        and (indicator_filter is None or r[1] == indicator_filter)
    ]

    if not applicable:
        print("No applicable rules (all rules are commented out or filtered).")
        print("Pending rules will be added to RULES after Analyst unit audit.")
        return

    print("=" * 72)
    print(f"DRY-RUN -- {len(applicable)} rule(s) would be applied")
    print(f"DB: {db_path}")
    print("=" * 72)
    print()

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        for src, ind, op, factor, old_unit, new_unit, reason in applicable:
            rows = con.execute(
                "SELECT COUNT(*) FROM indicators WHERE source=? AND indicator=? AND unit=?",
                [src, ind, old_unit]
            ).fetchone()[0]
            print(f"  Rule:      {src} / {ind}")
            print(f"  Operation: {op} by {factor}  ({old_unit} -> {new_unit})")
            print(f"  Reason:    {reason}")
            print(f"  Rows:      {rows} rows would be updated")
            print()
    finally:
        con.close()


def apply_rules(db_path, source_filter, indicator_filter):
    """Apply RULES to the DB (write mode)."""
    import duckdb

    applicable = [
        r for r in RULES
        if (source_filter is None or r[0] == source_filter)
        and (indicator_filter is None or r[1] == indicator_filter)
    ]

    if not applicable:
        print("No applicable rules. Nothing to apply.")
        return

    print("=" * 72)
    print(f"APPLY -- {len(applicable)} rule(s)")
    print(f"DB: {db_path}")
    print("=" * 72)
    print()

    con = duckdb.connect(str(db_path))
    try:
        for src, ind, op, factor, old_unit, new_unit, reason in applicable:
            rows_before = con.execute(
                "SELECT COUNT(*) FROM indicators WHERE source=? AND indicator=? AND unit=?",
                [src, ind, old_unit]
            ).fetchone()[0]

            if rows_before == 0:
                print(f"  SKIP  {src}/{ind}: no rows matching unit='{old_unit}'")
                continue

            if op == 'divide':
                expr = f"value / {factor}"
            elif op == 'multiply':
                expr = f"value * {factor}"
            elif op == 'offset':
                expr = f"value + {factor}"
            else:
                print(f"  ERROR {src}/{ind}: unknown operation '{op}'", file=sys.stderr)
                continue

            con.execute(
                f"UPDATE indicators SET value = {expr}, unit = ? "
                f"WHERE source = ? AND indicator = ? AND unit = ?",
                [new_unit, src, ind, old_unit]
            )

            rows_after = con.execute(
                "SELECT COUNT(*) FROM indicators WHERE source=? AND indicator=? AND unit=?",
                [src, ind, new_unit]
            ).fetchone()[0]

            print(f"  OK    {src}/{ind}: {rows_before} rows  {old_unit} -> {new_unit}  ({reason})")
            if rows_after != rows_before:
                print(f"        WARNING: expected {rows_before} rows with new unit, got {rows_after}")

    except Exception as e:
        con.close()
        print(f"\nERROR during apply: {e}", file=sys.stderr)
        sys.exit(1)

    con.close()
    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize CAE indicator values to canonical units."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Apply rules to DB (default: dry-run only)")
    parser.add_argument("--source", default=None,
                        help="Limit to a specific source (e.g. DGEG)")
    parser.add_argument("--indicator", default=None,
                        help="Limit to a specific indicator")
    parser.add_argument("--db", default=None,
                        help=f"DB path (default: {DB_PATH})")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else DB_PATH

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        print("Set CAE_DB_PATH env var or use --db <path>", file=sys.stderr)
        sys.exit(1)

    if not _check_deps():
        sys.exit(1)

    if args.apply:
        apply_rules(db_path, args.source, args.indicator)
    else:
        preview_rules(db_path, args.source, args.indicator)
        print("--- This was a dry-run. Use --apply to write changes. ---")


if __name__ == "__main__":
    main()
