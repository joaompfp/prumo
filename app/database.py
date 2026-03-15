import threading
import duckdb

from .config import CAE_DB_PATH, ENERGY_SOURCES


class _DBConn:
    """Thin wrapper around a DuckDB connection.
    close() is a no-op — per-thread connections must stay alive."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, *a, **kw):
        return self._conn.execute(*a, **kw)

    def close(self):
        pass  # intentionally a no-op

    def __getattr__(self, name):
        return getattr(self._conn, name)


# Per-thread connections: DuckDB connections are not thread-safe;
# each request thread gets its own read_only connection.
_thread_local = threading.local()


def get_db(source=None):
    """Return a per-thread read-only DuckDB connection."""
    if not hasattr(_thread_local, 'conn') or _thread_local.conn is None:
        _thread_local.conn = _DBConn(duckdb.connect(CAE_DB_PATH, read_only=True))
    return _thread_local.conn


def fetch_series(source, indicator, from_period=None, to_period=None, region="PT"):
    """Fetch time series data for a single source+indicator pair.

    Defaults to region='PT' to avoid mixing data from multiple countries
    in multi-region indicators (e.g. EUROSTAT unemployment has 27+ regions).
    Falls back to the sole available region if PT returns empty (e.g. FRED
    commodities stored under 'WORLD').
    """
    def _query(rgn):
        sql = "SELECT period, value, unit FROM indicators WHERE source=? AND indicator=? AND region=?"
        params = [source, indicator, rgn]
        if from_period:
            sql += " AND period >= ?"
            params.append(from_period)
        if to_period:
            sql += " AND period <= ?"
            params.append(to_period)
        sql += " ORDER BY period"
        return conn.execute(sql, params).fetchall()

    conn = get_db(source)
    try:
        rows = _query(region)
        if not rows and region == "PT":
            # Fallback: find the single region for this indicator
            alt = conn.execute(
                "SELECT DISTINCT region FROM indicators WHERE source=? AND indicator=?",
                [source, indicator],
            ).fetchall()
            if len(alt) == 1:
                rows = _query(alt[0][0])
    finally:
        conn.close()

    return [{"period": r[0], "value": r[1], "unit": r[2]} for r in rows]
