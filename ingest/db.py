"""The only module that touches SQL. Schema lives in versioned migrations/NNNN_*.sql."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Db:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @contextmanager
    def transaction(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    def upsert_source_and_series(self, sources: list[dict], series: list[dict]) -> None:
        """Idempotent registry sync. `series` rows reference their source by `source_name`."""
        with self.transaction() as c:
            for s in sources:
                c.execute(
                    "INSERT INTO source(name, licence, licence_url, attribution, redistribution_ok) "
                    "VALUES (:name, :licence, :licence_url, :attribution, :redistribution_ok) "
                    "ON CONFLICT(name) DO UPDATE SET licence=excluded.licence, "
                    "licence_url=excluded.licence_url, attribution=excluded.attribution, "
                    "redistribution_ok=excluded.redistribution_ok",
                    {**s, "redistribution_ok": int(s["redistribution_ok"])})
            for r in series:
                c.execute(
                    "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
                    "frequency, unit, multiplier, seasonal_adjustment, base_year, native_code, url, active) "
                    "VALUES (:id, (SELECT id FROM source WHERE name = :source_name), :indicator_key, "
                    ":role, :theme, :geography, :frequency, :unit, :multiplier, :seasonal_adjustment, "
                    ":base_year, :native_code, :url, :active) "
                    "ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id, "
                    "indicator_key=excluded.indicator_key, role=excluded.role, theme=excluded.theme, "
                    "geography=excluded.geography, frequency=excluded.frequency, unit=excluded.unit, "
                    "multiplier=excluded.multiplier, seasonal_adjustment=excluded.seasonal_adjustment, "
                    "base_year=excluded.base_year, native_code=excluded.native_code, "
                    "url=excluded.url, active=excluded.active",
                    {**r, "active": int(r["active"])})

    def close(self) -> None:
        self.conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migration("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP) STRICT"
    )
    done = {r[0] for r in conn.execute("SELECT version FROM schema_migration")}
    for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if f.stem in done:
            continue
        record = f"INSERT INTO schema_migration(version) VALUES ('{f.stem}');"
        try:
            # executescript is required for multi-statement files (triggers contain ';')
            conn.executescript(f"BEGIN;\n{f.read_text()}\n{record}\nCOMMIT;")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise


def open_db(path: str | Path) -> Db:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _migrate(conn)
    return Db(conn)
