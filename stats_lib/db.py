import os
import duckdb
from datetime import date
from typing import List, Optional

from .models import DataPoint

DB_PATH = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")


def _conn(readonly=False):
    # DuckDB is always opened read_only for dashboard reads
    return duckdb.connect(DB_PATH, read_only=readonly)


def db_get(indicator: str, regions: List[str], since: str,
           source: str = None) -> List[DataPoint]:
    """Lê pontos da BD para indicator + regions + period >= since."""
    conn = _conn(readonly=True)
    placeholders = ",".join("?" for _ in regions)
    query = f"""
        SELECT source, indicator, region, period, value, unit, category, fetched_at
        FROM indicators
        WHERE indicator = ? AND region IN ({placeholders}) AND period >= ?
    """
    params = [indicator] + list(regions) + [since]
    if source:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY region, period"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        DataPoint(
            source=r[0],
            indicator=r[1],
            region=r[2],
            period=r[3],
            value=r[4],
            unit=r[5] or "",
            category=r[6] or "",
            fetched_at=r[7] or "",
        )
        for r in rows
    ]


def db_write(points: List[DataPoint]) -> int:
    """INSERT OR REPLACE. Retorna nº de rows escritas."""
    if not points:
        return 0
    conn = _conn(readonly=False)
    today = date.today().isoformat()
    count = 0
    for p in points:
        conn.execute(
            """
            INSERT OR REPLACE INTO indicators
              (source, indicator, region, period, value, unit, category, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p.source,
                p.indicator,
                p.region,
                p.period,
                p.value,
                p.unit or "I21",
                p.category or "compare",
                p.fetched_at or today,
            ),
        )
        count += 1
    conn.close()
    return count


def db_get_periods(indicator: str, region: str, since: str) -> set:
    """Retorna set de períodos já na BD para indicator+region."""
    conn = _conn(readonly=True)
    rows = conn.execute(
        "SELECT period FROM indicators WHERE indicator=? AND region=? AND period>=?",
        (indicator, region, since),
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}
