"""The only module that touches SQL. Schema lives in versioned migrations/NNNN_*.sql."""
import json
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

    # --- pipeline (Task 6) -------------------------------------------------------------------
    # Write methods below issue plain statements: called outside `transaction()` each statement
    # autocommits; called inside it they join that transaction.

    def begin_run(self, source_name: str, dataset_key: str, started_at: str) -> int:
        """New dataset_run in state 'running'. The source must already be registered."""
        cur = self.conn.execute(
            "INSERT INTO dataset_run(source_id, started_at, state, dataset_key) "
            "VALUES ((SELECT id FROM source WHERE name = ?), ?, 'running', ?)",
            (source_name, started_at, dataset_key))
        return cur.lastrowid

    def set_run_state(self, run_id: int, state: str, finished_at: str | None = None) -> None:
        self.conn.execute(
            "UPDATE dataset_run SET state = ?, finished_at = COALESCE(?, finished_at) WHERE id = ?",
            (state, finished_at, run_id))

    def run_state(self, run_id: int) -> str:
        return self.conn.execute("SELECT state FROM dataset_run WHERE id = ?", (run_id,)).fetchone()[0]

    def previous_run(self, dataset_key: str, before_run_id: int) -> tuple[int, str] | None:
        """(id, state) of the latest dataset_run with this key and id < before_run_id."""
        return self.conn.execute(
            "SELECT id, state FROM dataset_run WHERE dataset_key = ? AND id < ? "
            "ORDER BY id DESC LIMIT 1", (dataset_key, before_run_id)).fetchone()

    def record_raw_fetch(self, *, source_name: str, run_id: int, url: str, params_json: str | None,
                         fetched_at: str, http_status: int | None, sha256: str, path: str,
                         n_bytes: int, ok: bool) -> int:
        cur = self.conn.execute(
            "INSERT INTO raw_fetch(source_id, dataset_run_id, url, params_json, fetched_at, "
            "http_status, sha256, path, bytes, ok) "
            "VALUES ((SELECT id FROM source WHERE name = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (source_name, run_id, url, params_json, fetched_at, http_status, sha256, path,
             n_bytes, int(ok)))
        return cur.lastrowid

    def raw_fetch_shas(self, run_id: int) -> list[str]:
        """sha256 of every raw payload fetched by the run, sorted."""
        return [r[0] for r in self.conn.execute(
            "SELECT sha256 FROM raw_fetch WHERE dataset_run_id = ? ORDER BY sha256", (run_id,))]

    def served_fetched_values(self, series_id: str) -> dict[str, str]:
        """period -> value_text currently served from verified *fetched* data (legacy excluded)."""
        return dict(self.conn.execute(
            "SELECT period, value_text FROM served_observation "
            "WHERE series_id = ? AND kind = 'fetched'", (series_id,)))

    def write_observations(self, run_id: int, rows: list[tuple]) -> None:
        """Insert (`ingest.models.Observation`, raw_fetch_id, fetched_at) triples in order
        (order = vintage: highest id is latest); raw_fetch_id is the payload the row came from."""
        self.conn.executemany(
            "INSERT INTO observation(series_id, period, value_text, value, status_flag, kind, "
            "dataset_run_id, raw_fetch_id, fetched_at, released_at) "
            "VALUES (?, ?, ?, ?, ?, 'fetched', ?, ?, ?, ?)",
            [(o.series_id, o.period, o.value_text, o.value, o.status_flag, run_id, raw_fetch_id,
              fetched_at, o.released_at.isoformat() if o.released_at else None)
             for o, raw_fetch_id, fetched_at in rows])

    def write_quarantine(self, run_id: int, series_id: str, rejections: list,
                         created_at: str) -> None:
        """Insert `ingest.validate.Rejection`s for one series."""
        self.conn.executemany(
            "INSERT INTO quarantine(dataset_run_id, series_id, raw_period, raw_value, reason, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(run_id, series_id, r.period_raw, r.value_raw, r.reason, created_at)
             for r in rejections])

    def add_event(self, ts: str, kind: str, run_id: int | None, detail: dict | None = None) -> None:
        self.conn.execute(
            "INSERT INTO event(ts, dataset_run_id, kind, detail_json) VALUES (?, ?, ?, ?)",
            (ts, run_id, kind, json.dumps(detail, sort_keys=True) if detail is not None else None))

    # --- verification (Task 7) ---------------------------------------------------------------

    def observations_of_run(self, run_id: int) -> list[tuple[str, str, str, str | None]]:
        """(series_id, period, value_text, status_flag) written by the run, ordered by
        series_id, period, id (deterministic: sampling relies on it)."""
        return self.conn.execute(
            "SELECT series_id, period, value_text, status_flag FROM observation "
            "WHERE dataset_run_id = ? ORDER BY series_id, period, id", (run_id,)).fetchall()

    def add_verification(self, run_id: int, seed: int, sample_size: int, passed: bool,
                         created_at: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO verification(dataset_run_id, seed, sample_size, passed, created_at) "
            "VALUES (?, ?, ?, ?, ?)", (run_id, seed, sample_size, int(passed), created_at))
        return cur.lastrowid

    _ITEM_COLUMNS = ("series_id", "period", "expected_text", "expected_decimal", "expected_unit",
                     "expected_flag", "observed_series_id", "observed_period", "observed_text",
                     "observed_decimal", "observed_unit", "observed_flag", "evidence_url",
                     "evidence_sha256", "match", "note")

    def add_verification_item(self, verification_id: int, item: dict) -> None:
        """`item` has exactly the keys of _ITEM_COLUMNS (match as bool)."""
        cols = self._ITEM_COLUMNS
        if set(item) != set(cols):
            raise ValueError(f"verification item keys {sorted(item)} != {sorted(cols)}")
        self.conn.execute(
            f"INSERT INTO verification_item(verification_id, {', '.join(cols)}) "
            f"VALUES (?, {', '.join('?' * len(cols))})",
            (verification_id, *[int(item[c]) if c == "match" else item[c] for c in cols]))

    def verification_item(self, item_id: int) -> dict:
        """The stored verification_item (all _ITEM_COLUMNS, match as bool); KeyError if absent."""
        row = self.conn.execute(
            f"SELECT {', '.join(self._ITEM_COLUMNS)} FROM verification_item WHERE id = ?",
            (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        item = dict(zip(self._ITEM_COLUMNS, row))
        item["match"] = bool(item["match"])
        return item

    def verification_item_source(self, item_id: int) -> str:
        """Name of the source whose run the verification_item belongs to."""
        return self.conn.execute(
            "SELECT s.name FROM verification_item i JOIN verification v ON v.id = i.verification_id "
            "JOIN dataset_run r ON r.id = v.dataset_run_id JOIN source s ON s.id = r.source_id "
            "WHERE i.id = ?", (item_id,)).fetchone()[0]

    def transition_run_state(self, run_id: int, from_state: str, to_state: str) -> bool:
        """Compare-and-set: move the run to `to_state` only if it is in `from_state`."""
        cur = self.conn.execute("UPDATE dataset_run SET state = ? WHERE id = ? AND state = ?",
                                (to_state, run_id, from_state))
        return cur.rowcount == 1

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
