#!/usr/bin/env python3
"""Base collector utilities with Parquet output support.

Provides write_parquet() and standardize_rows() for all collectors.
Collectors can either inherit BaseCollector or use the functions standalone.

Schema matches the DuckDB `indicators` table:
  (source, indicator, region, period, value, unit, category, detail, fetched_at, source_id)
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

STAGING_DIR = Path(os.environ.get("PRUMO_STAGING_DIR",
                                   os.path.join(os.path.dirname(__file__), "..", "data", "staging")))
ARCHIVE_DIR = Path(os.environ.get("PRUMO_ARCHIVE_DIR",
                                   os.path.join(os.path.dirname(__file__), "..", "data", "archive")))
SCHEMA_COLUMNS = [
    "source", "indicator", "region", "period",
    "value", "unit", "category", "detail",
    "fetched_at", "source_id",
]


def standardize_rows(raw_data: List[Dict], source: str, indicator: str,
                     region: str = "PT", unit: str = "",
                     category: str = None, source_id: str = None) -> List[Dict]:
    """Convert raw collector output (period+value dicts) into DB-schema rows.

    Filters out rows where value is None.
    """
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [{
        "source": source,
        "indicator": indicator,
        "region": region,
        "period": d["period"],
        "value": float(d["value"]),
        "unit": d.get("unit", unit),
        "category": category,
        "detail": d.get("detail"),
        "fetched_at": fetched_at,
        "source_id": source_id,
    } for d in raw_data if d.get("value") is not None]


def write_parquet(rows: List[Dict], source: str, indicator: str = "mixed",
                  staging_dir: Optional[Path] = None) -> Path:
    """Write rows to a Parquet file in the staging directory.

    Returns the path of the written file.
    Requires pyarrow (listed in requirements.txt).
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_dir = staging_dir or STAGING_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    filepath = out_dir / f"{source.lower()}_{indicator}_{ts}.parquet"

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    normalized = []
    for r in rows:
        normalized.append({
            "source": r.get("source", source),
            "indicator": r.get("indicator", ""),
            "region": r.get("region", "PT"),
            "period": r.get("period", ""),
            "value": float(r["value"]) if r.get("value") is not None else None,
            "unit": r.get("unit", ""),
            "category": r.get("category"),
            "detail": r.get("detail"),
            "fetched_at": r.get("fetched_at", fetched_at),
            "source_id": r.get("source_id"),
        })

    schema = pa.schema([
        ("source", pa.string()), ("indicator", pa.string()),
        ("region", pa.string()), ("period", pa.string()),
        ("value", pa.float64()), ("unit", pa.string()),
        ("category", pa.string()), ("detail", pa.string()),
        ("fetched_at", pa.string()), ("source_id", pa.string()),
    ])
    arrays = {col: [r[col] for r in normalized] for col in SCHEMA_COLUMNS}
    table = pa.table(arrays, schema=schema)
    pq.write_table(table, filepath, compression="snappy")
    print(f"[base] wrote {len(normalized)} rows → {filepath.name} "
          f"({filepath.stat().st_size / 1024:.1f} KB)", flush=True)
    return filepath


class BaseCollector:
    """Optional base class for collectors that want write_parquet built in."""

    SOURCE = "UNKNOWN"  # Override in subclass

    def collect(self) -> List[Dict]:
        """Override: return list of DB-schema rows."""
        raise NotImplementedError

    def run(self, to_parquet: bool = True, staging_dir: Optional[Path] = None) -> List[Dict]:
        """Run collection and optionally write Parquet."""
        rows = self.collect()
        if to_parquet and rows:
            write_parquet(rows, source=self.SOURCE, staging_dir=staging_dir)
        return rows
