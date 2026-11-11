"""Test helper: write legacy-export CSV fixtures (same header as the real export)."""
import csv
from pathlib import Path

HEADER = ["source", "indicator", "region", "period", "value", "unit", "category", "detail",
          "fetched_at", "source_id"]
REAL_EXPORT = Path("/home/joao/projects/_legacy_export/indicators.csv")


def write_csv(path: Path, rows: list[tuple]) -> Path:
    """rows: (source, indicator, region, period, value, unit[, fetched_at])."""
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            src, ind, reg, per, val, unit = r[:6]
            fetched = r[6] if len(r) > 6 else "2026-03-15T21:35:31Z"
            w.writerow([src, ind, reg, per, val, unit, "", "", fetched, ""])
    return path
