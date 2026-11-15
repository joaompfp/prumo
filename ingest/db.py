"""The only module that touches SQL. Schema lives in versioned migrations/NNNN_*.sql."""
import json
import sqlite3
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple, TypeVar

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
T = TypeVar("T")
BUSY_TIMEOUT_S = 30.0  # scheduler and CLI can contend for the write lock
# A 'running' run older than this, with no interrupted scheduler attempt behind it, is an
# orphan (Db.close_orphan_runs). The slowest observed full dataset run (World Bank census,
# Eurostat) takes minutes; 6 h leaves a wide margin for a live manual CLI run.
ORPHAN_MIN_AGE = timedelta(hours=6)

# Errors of our own storage environment (lock contention, I/O, missing schema): callers
# record them as operational failures, never as a publisher format change.
OperationalError = sqlite3.OperationalError


class ReadOnlyOpenError(RuntimeError):
    """open_db_readonly refused: missing file, or a schema this code does not match."""


@dataclass(frozen=True)
class RunContent:
    """What a run wrote, as sorted multisets (identity of vintage content, Decision 1).
    observations: (series_id, period, value_text, status_flag, released_at);
    quarantine: (series_id, raw_period, raw_value, reason), the first three nullable."""
    observations: tuple[tuple[str, str, str, str | None, str | None], ...]
    quarantine: tuple[tuple[str | None, str | None, str | None, str], ...]

    @classmethod
    def of(cls, observations: Iterable[tuple], quarantine: Iterable[tuple]) -> "RunContent":
        """From unordered row tuples (shapes above): the one place that orders them."""
        return cls(tuple(sorted(map(tuple, observations), key=_none_safe)),
                   tuple(sorted(map(tuple, quarantine), key=_none_safe)))


def _none_safe(row: tuple) -> tuple:
    return tuple((v is not None, v if v is not None else "") for v in row)


def observation_content(o) -> tuple[str, str, str, str | None, str | None]:
    """The content columns an `ingest.models.Observation` is stored as (and RunContent
    compares): (series_id, period, value_text, status_flag, released_at ISO text)."""
    return (o.series_id, o.period, o.value_text, o.status_flag,
            o.released_at.isoformat() if o.released_at else None)


def quarantine_content(series_id: str, r) -> tuple[str, str | None, str | None, str]:
    """The content columns an `ingest.validate.Rejection` of `series_id` is stored as:
    (series_id, raw_period, raw_value, reason)."""
    return (series_id, r.period_raw, r.value_raw, r.reason)


class SchedulerState(NamedTuple):
    dataset_key: str
    source_name: str
    group_label: str
    last_attempt_at: str
    last_attempt_state: str
    last_success_at: str | None
    failure_streak: int
    last_finished_at: str | None


def _parse_utc(ts: str | None) -> datetime | None:
    """A stored ISO-8601 stamp as an aware UTC datetime (naive = UTC); None if unparseable."""
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _origin(kind: str) -> str:
    """observation.kind as the backoffice names it: 'fetched' or 'legacy'."""
    return "legacy" if kind == "legacy-unverified" else "fetched"


def _family_of(indicator_key: str) -> str:
    """The indicator family: the key without its trailing geography and frequency parts.
    `consumer_confidence.AT.M` -> `consumer_confidence`; a two-part key stays whole."""
    parts = indicator_key.split(".")
    return ".".join(parts[:-2]) if len(parts) >= 3 else indicator_key


class Db:
    def __init__(self, conn: sqlite3.Connection, *, immutable: bool = False):
        self.conn = conn
        self.immutable = immutable  # opened read-only with sqlite immutable=1 (no writer seen)
        self.immutable_stamp: tuple[int, int] | None = None  # main file (mtime_ns, size)
        # when the immutable handle was opened (open_db_readonly)

    @contextmanager
    def transaction(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            if self.conn.in_transaction:  # SQLite may have rolled back already (e.g. FULL)
                self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    def upsert_source_and_series(self, sources: list[dict], series: list[dict]) -> None:
        """Idempotent registry sync. `series` rows reference their source by `source_name`.
        `series` is the WHOLE registry: an active series absent from it is set inactive
        (its rows stay; inactive fetched rows are not served) with event(series_deactivated)."""
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
            keep = [r["id"] for r in series]
            gone = [i for (i,) in c.execute(
                "SELECT id FROM series WHERE active = 1 AND id NOT IN "
                f"({','.join('?' * len(keep))}) ORDER BY id", keep)]
            ts = datetime.now(timezone.utc).isoformat()
            for sid in gone:
                c.execute("UPDATE series SET active = 0 WHERE id = ?", (sid,))
                self.add_event(ts, "series_deactivated", None,
                               {"series_id": sid, "reason": "absent_from_registry"})

    # --- pipeline (Task 6) -------------------------------------------------------------------
    # Write methods below issue plain statements: called outside `transaction()` each statement
    # autocommits; called inside it they join that transaction.

    def begin_run(self, source_name: str, dataset_key: str, started_at: str, *,
                  input_origin: str = "live") -> int:
        """New dataset_run in state 'running'. The source must already be registered.
        input_origin: 'live' (fresh network input, the default) or 'recorded' (an exact
        validated original-file bundle, Task 17B); 'legacy' is set by legacy_run only."""
        cur = self.conn.execute(
            "INSERT INTO dataset_run(source_id, started_at, state, dataset_key, input_origin) "
            "VALUES ((SELECT id FROM source WHERE name = ?), ?, 'running', ?, ?)",
            (source_name, started_at, dataset_key, input_origin))
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

    def run_content(self, run_id: int) -> RunContent:
        """Observation and quarantine rows of the run, sorted (insertion order is irrelevant;
        a (series, period) written from two responses appears twice)."""
        obs = self.conn.execute(
            "SELECT series_id, period, value_text, status_flag, released_at FROM observation "
            "WHERE dataset_run_id = ?", (run_id,)).fetchall()
        quar = self.conn.execute(
            "SELECT series_id, raw_period, raw_value, reason FROM quarantine "
            "WHERE dataset_run_id = ?", (run_id,)).fetchall()
        return RunContent.of(obs, quar)

    def content_base_run(self, dataset_key: str, before_run_id: int) -> int | None:
        """The run whose content a new run of `dataset_key` is compared with, or None.
        Walks back from the previous run: a `verified` run holding neither observations nor
        quarantine rows is an earlier short-circuit and is skipped; the first run holding
        content is the base and must be `verified`; any other state met on the way (failed,
        blocked, pending, withdrawn, ...) means no base. The chain's end also means None.
        Neither is a base: a run verified only against its own pinned bundle (not
        audit-grade: a live fetch must get its own live verification), nor a run whose rows
        another dataset has since superseded (`_superseded_elsewhere`)."""
        cursor = before_run_id
        while (prev := self.previous_run(dataset_key, cursor)) is not None:
            run_id, state = prev
            if state != "verified":
                return None
            if self._run_has_observations(run_id) or self.conn.execute(
                    "SELECT EXISTS (SELECT 1 FROM quarantine WHERE dataset_run_id = ?)",
                    (run_id,)).fetchone()[0]:
                pinned = self.conn.execute(f"SELECT ? IN ({self._PINNED_RUNS})",
                                           (run_id,)).fetchone()[0]
                if pinned or self._superseded_elsewhere(run_id, dataset_key):
                    return None
                return run_id
            cursor = run_id
        return None

    def _superseded_elsewhere(self, run_id: int, dataset_key: str) -> bool:
        """A verified fetched row of another dataset_key, for a series this run wrote, is at
        least as recent (fetched_at) as this run's own rows of that series: the served view
        may prefer it, so a short-circuit onto this run would not re-assert its values.
        Per series, not per period (conservative). Reads only the run's rows (index
        observation_run) and those series' rows (the UNIQUE(series_id, ...) index)."""
        return self.conn.execute(
            "SELECT EXISTS (SELECT 1 FROM (SELECT series_id, MAX(fetched_at) AS at "
            "FROM observation WHERE dataset_run_id = ? GROUP BY series_id) b "
            "JOIN observation o ON o.series_id = b.series_id AND o.fetched_at >= b.at "
            "JOIN dataset_run r ON r.id = o.dataset_run_id "
            "WHERE o.kind = 'fetched' AND r.state = 'verified' AND r.dataset_key IS NOT ?)",
            (run_id, dataset_key)).fetchone()[0] == 1

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
            "INSERT INTO observation(series_id, period, value_text, status_flag, released_at, "
            "value, kind, dataset_run_id, raw_fetch_id, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'fetched', ?, ?, ?)",
            [(*observation_content(o), o.value, run_id, raw_fetch_id, fetched_at)
             for o, raw_fetch_id, fetched_at in rows])

    def write_quarantine(self, run_id: int, series_id: str, rejections: list,
                         created_at: str) -> None:
        """Insert `ingest.validate.Rejection`s for one series."""
        self.conn.executemany(
            "INSERT INTO quarantine(series_id, raw_period, raw_value, reason, dataset_run_id, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(*quarantine_content(series_id, r), run_id, created_at) for r in rejections])

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
                         created_at: str, *, sample_procedure: str, sample_design: dict,
                         input_origin: str, verifier_channel: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO verification(dataset_run_id, seed, sample_size, passed, created_at, "
            "sample_procedure, sample_design, input_origin, verifier_channel) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, seed, sample_size, int(passed), created_at, sample_procedure,
             json.dumps(sample_design, sort_keys=True), input_origin, verifier_channel))
        return cur.lastrowid

    def run_input_origin(self, run_id: int) -> str:
        return self.conn.execute("SELECT input_origin FROM dataset_run WHERE id = ?",
                                 (run_id,)).fetchone()[0]

    def latest_fetched_periods(self) -> dict[str, str]:
        """series_id -> newest period of its FETCHED rows in runs that are 'verified' or
        still 'pending-verification'. Rows of withdrawn or failed runs are ignored: a parser
        defect that invented a future period (the usual reason for a withdrawal or a failed
        verification) must not mask a frozen dataset. Legacy rows are excluded. Canonical
        periods of one frequency sort as text."""
        return dict(self.conn.execute(
            "SELECT o.series_id, MAX(o.period) FROM observation o "
            "JOIN dataset_run r ON r.id = o.dataset_run_id "
            "WHERE o.kind = 'fetched' AND r.state IN ('verified', 'pending-verification') "
            "GROUP BY o.series_id").fetchall())

    def run_changed_keys(self, run_id: int) -> set[tuple[str, str]]:
        """(series_id, period) the run revised (event 'revision') or newly added to a series
        that already had verified fetched data (event 'new_periods'): the run's changed set,
        fixed at write time so a later redraw of the sample sees the same set."""
        out: set[tuple[str, str]] = set()
        for kind, detail in self.conn.execute(
                "SELECT kind, detail_json FROM event WHERE dataset_run_id = ? "
                "AND kind IN ('revision', 'new_periods')", (run_id,)):
            d = json.loads(detail)
            if kind == "revision":
                out.add((d["series_id"], d["period"]))
            else:
                out |= {(d["series_id"], p) for p in d["periods"]}
        return out

    def previously_failed_keys(self, run_id: int) -> set[tuple[str, str]]:
        """(series_id, period) of every item that MISMATCHED in a failed verification of an
        earlier run of this run's dataset_key since that key's last 'verified' run (re-review
        2 I1: carried into the next attempt's must-check set). Only items the verifier
        actually answered count (observed_series_id set): an outage or a broken verifier
        fails every item without observing anything, and those are not defects."""
        row = self.conn.execute("SELECT dataset_key FROM dataset_run WHERE id = ?",
                                (run_id,)).fetchone()
        if row is None or row[0] is None:
            return set()
        key = row[0]
        return set(self.conn.execute(
            "SELECT DISTINCT i.series_id, i.period FROM verification_item i "
            "JOIN verification v ON v.id = i.verification_id "
            "JOIN dataset_run r ON r.id = v.dataset_run_id "
            "WHERE r.dataset_key = ? AND r.id < ? AND v.passed = 0 AND i.match = 0 "
            "AND i.observed_series_id IS NOT NULL "
            "AND r.id > COALESCE((SELECT MAX(id) FROM dataset_run WHERE dataset_key = ? "
            "AND id < ? AND state = 'verified'), 0)",
            (key, run_id, key, run_id)).fetchall())

    def add_verification_spec(self, verification_id: int, series_id: str,
                              spec_json: str) -> None:
        self.conn.execute(
            "INSERT INTO verification_spec(verification_id, series_id, spec_json) "
            "VALUES (?, ?, ?)", (verification_id, series_id, spec_json))

    def verification_item_spec(self, item_id: int) -> str | None:
        """The spec JSON the item's series was verified with (None before migration 0012)."""
        row = self.conn.execute(
            "SELECT s.spec_json FROM verification_item i JOIN verification_spec s "
            "ON s.verification_id = i.verification_id AND s.series_id = i.series_id "
            "WHERE i.id = ?", (item_id,)).fetchone()
        return row[0] if row else None

    _ITEM_COLUMNS = ("series_id", "period", "expected_text", "expected_decimal", "expected_unit",
                     "expected_flag", "observed_series_id", "observed_period", "observed_text",
                     "observed_decimal", "observed_unit", "observed_flag", "evidence_url",
                     "evidence_sha256", "match", "note", "reason", "compared",
                     "unit_not_compared", "flag_not_compared")

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

    def transition_run_state(self, run_id: int, from_state: str, to_state: str, *,
                             finished_at: str | None = None) -> bool:
        """Compare-and-set: move the run to `to_state` only if it is in `from_state`
        (finished_at, when given, is set in the same statement)."""
        cur = self.conn.execute(
            "UPDATE dataset_run SET state = ?, finished_at = COALESCE(?, finished_at) "
            "WHERE id = ? AND state = ?", (to_state, finished_at, run_id, from_state))
        return cur.rowcount == 1

    # --- legacy import (Task 8) ---------------------------------------------------------------

    def legacy_run(self, source_name: str, dataset_key: str, started_at: str) -> int:
        """The synthetic run that holds a source's legacy rows: created on first use in state
        'verified' (legacy rows are still served only when setting legacy_served = '1')."""
        row = self.conn.execute("SELECT id FROM dataset_run WHERE dataset_key = ? ORDER BY id LIMIT 1",
                                (dataset_key,)).fetchone()
        if row:
            return row[0]
        cur = self.conn.execute(
            "INSERT INTO dataset_run(source_id, started_at, finished_at, state, dataset_key, "
            "input_origin) "
            "VALUES ((SELECT id FROM source WHERE name = ?), ?, ?, 'verified', ?, 'legacy')",
            (source_name, started_at, started_at, dataset_key))
        return cur.lastrowid

    def legacy_observation_keys(self, run_id: int) -> set[tuple[str, str, str, str]]:
        """(series_id, period, value_text, fetched_at) of the run's legacy rows (import dedupe)."""
        return set(self.conn.execute(
            "SELECT series_id, period, value_text, fetched_at FROM observation "
            "WHERE dataset_run_id = ? AND kind = 'legacy-unverified'", (run_id,)))

    def quarantine_keys(self, run_id: int) -> set[tuple]:
        """(series_id, raw_period, raw_value, reason) already quarantined for the run."""
        return set(self.conn.execute(
            "SELECT series_id, raw_period, raw_value, reason FROM quarantine WHERE dataset_run_id = ?",
            (run_id,)))

    def write_legacy_observations(self, run_id: int, rows: list[tuple]) -> None:
        """Insert (`ingest.models.Observation`, fetched_at) pairs as kind 'legacy-unverified' with no
        raw payload, in order (later vintages last, so they get the higher id)."""
        self.conn.executemany(
            "INSERT INTO observation(series_id, period, value_text, value, status_flag, kind, "
            "dataset_run_id, raw_fetch_id, fetched_at, released_at) "
            "VALUES (?, ?, ?, ?, ?, 'legacy-unverified', ?, NULL, ?, NULL)",
            [(o.series_id, o.period, o.value_text, o.value, o.status_flag, run_id, fetched_at)
             for o, fetched_at in rows])

    # --- operational status / CLI verification resolution (Task 17A) -------------------------

    def source_list(self) -> list[tuple[str, int]]:
        """(name, redistribution_ok) of every registered source, by name."""
        return self.conn.execute(
            "SELECT name, redistribution_ok FROM source ORDER BY name").fetchall()

    def series_list(self) -> list[tuple[str, str, str, int]]:
        """(id, source_name, frequency, active) of every series, by id."""
        return self.conn.execute(
            "SELECT r.id, s.name, r.frequency, r.active FROM series r "
            "JOIN source s ON s.id = r.source_id ORDER BY r.id").fetchall()

    def runs_overview(self) -> list[tuple[int, str, str | None, str, str, str | None, str]]:
        """(id, source_name, dataset_key, state, started_at, finished_at, input_origin)."""
        return self.conn.execute(
            "SELECT r.id, s.name, r.dataset_key, r.state, r.started_at, r.finished_at, "
            "r.input_origin "
            "FROM dataset_run r JOIN source s ON s.id = r.source_id ORDER BY r.id").fetchall()

    def max_held_fetched_at(self, series_ids: list[str]) -> str | None:
        """Latest observation.fetched_at among HELD fetched rows of the given series: runs
        that are verified OR still pending verification (Task 17B stale-bundle refusal, Task
        20 A-I1: a recorded bundle must be strictly newer than the data already held, even
        when a newer live run has not finished verification yet). Legacy rows and runs in
        any other state (failed, withdrawn, ...) never count here."""
        if not series_ids:
            return None
        marks = ",".join("?" * len(series_ids))
        return self.conn.execute(
            "SELECT MAX(o.fetched_at) FROM observation o "
            "JOIN dataset_run r ON r.id = o.dataset_run_id "
            "WHERE o.kind = 'fetched' AND r.state IN ('verified', 'pending-verification') "
            f"AND o.series_id IN ({marks})",
            series_ids).fetchone()[0]

    def observation_stats(self) -> list[tuple[str, str, str, int, str]]:
        """(series_id, kind, run state, row count, max fetched_at) per series/kind/state."""
        return self.conn.execute(
            "SELECT o.series_id, o.kind, r.state, COUNT(*), MAX(o.fetched_at) "
            "FROM observation o JOIN dataset_run r ON r.id = o.dataset_run_id "
            "GROUP BY o.series_id, o.kind, r.state").fetchall()

    def event_totals(self, since: str | None = None) -> list[tuple[str | None, str, int]]:
        """(source_name or None, kind, count) of events over all time, or of events with
        ts >= `since` (ISO-8601 UTC; stored stamps share the +00:00 form, so text order is
        time order)."""
        where, args = ("WHERE e.ts >= ? ", (since,)) if since is not None else ("", ())
        return self.conn.execute(
            "SELECT s.name, e.kind, COUNT(*) FROM event e "
            "LEFT JOIN dataset_run r ON r.id = e.dataset_run_id "
            "LEFT JOIN source s ON s.id = r.source_id " + where +
            "GROUP BY s.name, e.kind", args).fetchall()

    _PINNED_RUNS = ("SELECT dataset_run_id FROM verification "
                    "WHERE passed = 1 AND verifier_channel = 'pinned-bundle'")

    def verified_run_receipts(self) -> list[tuple[int, str | None, str | None, int, int]]:
        """(run_id, dataset_key, latest raw_fetch.fetched_at, wrote_observations 0/1,
        pinned_bundle 0/1) of every NON-legacy run currently in state 'verified', oldest
        first. A verified run that wrote no observations is a short-circuit for identical
        bytes or identical values (pipeline Ruling D); pinned_bundle marks a run whose passing
        verification read the operator's bundle, not the publisher (not audit-grade)."""
        return self.conn.execute(
            "SELECT r.id, r.dataset_key, "
            "(SELECT MAX(f.fetched_at) FROM raw_fetch f WHERE f.dataset_run_id = r.id), "
            "r.id IN (SELECT dataset_run_id FROM observation), "
            f"r.id IN ({self._PINNED_RUNS}) "
            "FROM dataset_run r WHERE r.state = 'verified' AND r.input_origin <> 'legacy' "
            "ORDER BY r.id").fetchall()

    def audit_grade_fetched_at(self) -> dict[str, str]:
        """series_id -> latest observation fetched_at among fetched rows of 'verified' runs
        whose verification read the publisher (live channel): a run verified only against its
        own pinned bundle (verifier_channel 'pinned-bundle') never confirms currency."""
        return dict(self.conn.execute(
            "SELECT o.series_id, MAX(o.fetched_at) FROM observation o "
            "JOIN dataset_run r ON r.id = o.dataset_run_id "
            "WHERE o.kind = 'fetched' AND r.state = 'verified' "
            f"AND r.id NOT IN ({self._PINNED_RUNS}) GROUP BY o.series_id").fetchall())

    def series_of_runs(self, run_ids: list[int]) -> dict[int, set[str]]:
        """{run_id: distinct series ids with observations in that run} (one table scan)."""
        if not run_ids:
            return {}
        marks = ",".join("?" * len(run_ids))
        out: dict[int, set[str]] = {r: set() for r in run_ids}
        for run_id, sid in self.conn.execute(
                "SELECT DISTINCT dataset_run_id, series_id FROM observation "
                f"WHERE dataset_run_id IN ({marks})", list(run_ids)):
            out[run_id].add(sid)
        return out

    def verification_overview(self) -> list[tuple[int, str | None, int, str, str | None]]:
        """(run_id, dataset_key, passed, created_at, verifier_channel) of every
        verification, oldest first (channel NULL only before migration 0012)."""
        return self.conn.execute(
            "SELECT v.dataset_run_id, r.dataset_key, v.passed, v.created_at, "
            "v.verifier_channel "
            "FROM verification v JOIN dataset_run r ON r.id = v.dataset_run_id "
            "ORDER BY v.id").fetchall()

    def run_series_ids(self, run_id: int) -> list[str]:
        """Distinct series ids with observations in the run."""
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT series_id FROM observation WHERE dataset_run_id = ? "
            "ORDER BY series_id", (run_id,))]

    def run_info(self, run_id: int) -> tuple[int, str, str | None, str, str, str | None] | None:
        """(id, source_name, dataset_key, state, started_at, finished_at); None if no such run."""
        return self.conn.execute(
            "SELECT r.id, s.name, r.dataset_key, r.state, r.started_at, r.finished_at "
            "FROM dataset_run r JOIN source s ON s.id = r.source_id WHERE r.id = ?",
            (run_id,)).fetchone()

    # --- backoffice reads (backoffice v1, Task 1) ----------------------------------------------
    # Read-only: plain dicts, numbers as the stored publisher token (value_text), never floats.

    def series_observations(self, series_id: str, limit: int,
                            offset: int = 0) -> tuple[int, list[dict]]:
        """(total served rows, served rows newest period first) of one series, from the
        served_observation view. origin is 'fetched' or 'legacy'; raw_sha is the payload hash
        behind a fetched row (None for legacy rows, which have no payload)."""
        total = self.conn.execute("SELECT COUNT(*) FROM served_observation WHERE series_id = ?",
                                  (series_id,)).fetchone()[0]
        rows = self.conn.execute(
            "SELECT o.period, o.value_text, o.status_flag, o.dataset_run_id, o.fetched_at, "
            "f.sha256, o.kind FROM served_observation o "
            "LEFT JOIN raw_fetch f ON f.id = o.raw_fetch_id "
            "WHERE o.series_id = ? ORDER BY o.period DESC LIMIT ? OFFSET ?",
            (series_id, limit, offset)).fetchall()
        keys = ("period", "value_text", "status_flag", "run_id", "fetched_at", "raw_sha")
        return total, [{**dict(zip(keys, r[:6])), "origin": _origin(r[6])} for r in rows]

    def series_vintages(self, series_id: str, period: str) -> list[dict]:
        """Every stored version of one (series, period) across runs, in insertion order, with
        its run's state; served is True only for the row the served_observation view
        returns."""
        rows = self.conn.execute(
            "SELECT o.dataset_run_id, r.state, o.fetched_at, o.value_text, o.status_flag, o.kind, "
            "o.id IN (SELECT id FROM served_observation WHERE series_id = ? AND period = ?) "
            "FROM observation o JOIN dataset_run r ON r.id = o.dataset_run_id "
            "WHERE o.series_id = ? AND o.period = ? ORDER BY o.id",
            (series_id, period, series_id, period)).fetchall()
        return [{"run_id": run, "run_state": state, "fetched_at": at, "value_text": value,
                 "status_flag": flag, "origin": _origin(kind), "served": bool(served)}
                for run, state, at, value, flag, kind, served in rows]

    def series_quarantine(self, series_id: str, limit: int = 200) -> list[dict]:
        """Quarantined raw rows of one series, newest first."""
        keys = ("run_id", "period", "raw_value", "reason", "created_at")
        return [dict(zip(keys, r)) for r in self.conn.execute(
            "SELECT dataset_run_id, raw_period, raw_value, reason, created_at FROM quarantine "
            "WHERE series_id = ? ORDER BY id DESC LIMIT ?", (series_id, limit))]

    def series_verification_items(self, series_id: str, limit: int = 200) -> list[dict]:
        """Verification items that covered one series, newest first (match as bool;
        created_at is the verification's)."""
        keys = ("item_id", "verification_id", "run_id", "period", "expected_text",
                "observed_text", "evidence_url", "match", "reason", "created_at")
        rows = self.conn.execute(
            "SELECT i.id, i.verification_id, v.dataset_run_id, i.period, i.expected_text, "
            "i.observed_text, i.evidence_url, i.match, i.reason, v.created_at "
            "FROM verification_item i JOIN verification v ON v.id = i.verification_id "
            "WHERE i.series_id = ? ORDER BY i.id DESC LIMIT ?", (series_id, limit)).fetchall()
        return [{**dict(zip(keys, r)), "match": bool(r[7])} for r in rows]

    def series_raw_fetches(self, series_id: str) -> list[dict]:
        """Distinct raw payloads behind the series' fetched rows (any run state), newest
        retrieval first."""
        keys = ("sha256", "url", "fetched_at", "http_status", "run_id")
        return [dict(zip(keys, r)) for r in self.conn.execute(
            "SELECT sha256, url, fetched_at, http_status, dataset_run_id FROM raw_fetch "
            "WHERE id IN (SELECT raw_fetch_id FROM observation WHERE series_id = ? "
            "AND raw_fetch_id IS NOT NULL) ORDER BY fetched_at DESC, id DESC", (series_id,))]

    def recent_events(self, since: str | None, kinds: list[str] | None,
                      limit: int) -> list[dict]:
        """Events newest first: ts >= `since` (ISO-8601 UTC, stored stamps share the +00:00
        form so text order is time order) and kind in `kinds` (None = every kind, [] =
        none). detail is the parsed detail_json ({} when absent)."""
        if kinds is not None and not kinds:
            return []
        where, args = ["1"], []
        if since is not None:
            where.append("ts >= ?")
            args.append(since)
        if kinds is not None:
            where.append(f"kind IN ({','.join('?' * len(kinds))})")
            args.extend(kinds)
        rows = self.conn.execute(
            "SELECT id, ts, kind, dataset_run_id, detail_json FROM event "
            f"WHERE {' AND '.join(where)} ORDER BY ts DESC, id DESC LIMIT ?",
            (*args, limit)).fetchall()
        return [{"id": i, "ts": ts, "kind": kind, "run_id": run,
                 "detail": json.loads(d) if d is not None else {}}
                for i, ts, kind, run, d in rows]

    def event_counts_by_run(self, since: str | None, kind: str, *, min_count: int = 1,
                            limit: int = 1000) -> dict[int | None, int]:
        """run id -> number of `kind` events with ts >= `since` (None = all time), for runs
        with at least `min_count` of them (at most `limit` runs, largest counts first),
        counted by SQL aggregation: memory is bounded by `limit`, never by the events."""
        where, args = "kind = ?", [kind]
        if since is not None:
            where += " AND ts >= ?"
            args.append(since)
        return dict(self.conn.execute(
            f"SELECT dataset_run_id, COUNT(*) AS n FROM event WHERE {where} "
            "GROUP BY dataset_run_id HAVING n >= ? ORDER BY n DESC, dataset_run_id LIMIT ?",
            (*args, min_count, limit)).fetchall())

    def failed_fetch_streaks(self, min_streak: int) -> list[dict]:
        """Datasets whose latest finished runs are `min_streak` or more consecutive
        'failed-fetch' runs (each emitted event(fetch_failure)), by dataset key. A run still
        'running' neither extends nor breaks the streak; any other state breaks it."""
        keys = ("dataset_key", "source", "streak", "last_run_id", "last_started_at")
        return [dict(zip(keys, r)) for r in self.conn.execute(
            # bare r.started_at comes from the MAX(r.id) row (documented SQLite behaviour)
            "SELECT r.dataset_key, s.name, COUNT(*), MAX(r.id), r.started_at "
            "FROM dataset_run r JOIN source s ON s.id = r.source_id "
            "WHERE r.state = 'failed-fetch' AND r.dataset_key IS NOT NULL "
            "AND r.id > COALESCE((SELECT MAX(b.id) FROM dataset_run b "
            "WHERE b.dataset_key = r.dataset_key "
            "AND b.state NOT IN ('failed-fetch', 'running')), 0) "
            "GROUP BY r.dataset_key, s.name HAVING COUNT(*) >= ? ORDER BY r.dataset_key",
            (min_streak,))]

    def new_period_spans(self, since: str | None, limit: int) -> list[dict]:
        """new_periods events (ts >= `since`) that added two or more periods, newest first,
        summarised in SQL as (n, first, last) of their periods (canonical period text sorts
        chronologically); the period lists themselves are never loaded."""
        where, args = ["e.kind = 'new_periods'",
                       "json_array_length(e.detail_json, '$.periods') >= 2"], []
        if since is not None:
            where.append("e.ts >= ?")
            args.append(since)
        keys = ("event_id", "ts", "run_id", "series_id", "n", "first", "last")
        return [dict(zip(keys, r)) for r in self.conn.execute(
            "SELECT e.id, e.ts, e.dataset_run_id, json_extract(e.detail_json, '$.series_id'), "
            "json_array_length(e.detail_json, '$.periods'), "
            "(SELECT MIN(value) FROM json_each(e.detail_json, '$.periods')), "
            "(SELECT MAX(value) FROM json_each(e.detail_json, '$.periods')) "
            f"FROM event e WHERE {' AND '.join(where)} ORDER BY e.ts DESC, e.id DESC LIMIT ?",
            (*args, limit))]

    def quarantine_summary(self, since: str | None, limit: int) -> list[dict]:
        """Quarantined rows created at or after `since`, aggregated per (source, reason):
        rows, distinct series, distinct runs, latest created_at; by source then reason."""
        where, args = "1", []
        if since is not None:
            where, args = "q.created_at >= ?", [since]
        keys = ("source", "reason", "rows", "series", "runs", "last_created_at")
        return [dict(zip(keys, r)) for r in self.conn.execute(
            "SELECT s.name, q.reason, COUNT(*), COUNT(DISTINCT q.series_id), "
            "COUNT(DISTINCT q.dataset_run_id), MAX(q.created_at) FROM quarantine q "
            "JOIN dataset_run r ON r.id = q.dataset_run_id JOIN source s ON s.id = r.source_id "
            f"WHERE {where} GROUP BY s.name, q.reason ORDER BY s.name, q.reason LIMIT ?",
            (*args, limit))]

    def series_periods(self, series_id: str, limit: int) -> tuple[int, list[dict]]:
        """(distinct stored periods, newest `limit` of them) of one series across EVERY run
        state (served, withdrawn, failed, pending, legacy), each with its stored row count and
        whether the served view returns a row for it."""
        total = self.conn.execute("SELECT COUNT(DISTINCT period) FROM observation "
                                  "WHERE series_id = ?", (series_id,)).fetchone()[0]
        rows = self.conn.execute(
            "SELECT period, COUNT(*), period IN (SELECT period FROM served_observation "
            "WHERE series_id = ?) FROM observation WHERE series_id = ? "
            "GROUP BY period ORDER BY period DESC LIMIT ?",
            (series_id, series_id, limit)).fetchall()
        return total, [{"period": p, "rows": n, "served": bool(served)}
                       for p, n, served in rows]

    # --- reviewed withdrawal and orphan runs (Task 20) -----------------------------------------

    def withdraw_run(self, run_id: int, reason: str, at: str) -> list[int]:
        """Withdraw ONE verified fetched vintage: its rows stay in `observation` but are never
        served again ('withdrawn' is terminal). The operator's reason is recorded as
        event(withdrawal) in the same transaction; migration 0011's triggers refuse every
        other way into 'withdrawn'.

        The short-circuit for identical bytes or identical values (pipeline Ruling D) vouches
        for the run it matched without holding rows, and the next identical fetch would match
        the short-circuit (or, for values, the same base run) again. So, in the same
        transaction, every LATER run of the same dataset_key that is a verified
        short-circuit chained onto this one (the unbroken sequence of verified runs
        with no observations right after it) is withdrawn too, each with its own
        event(withdrawal, {..., cascaded_from: run_id}); the next identical fetch then follows
        a withdrawn run and is re-ingested. Returns the withdrawn run ids, this one first.

        ValueError (nothing written) on an empty reason, an unknown, legacy or non-verified
        run, or a run with no observations (a short-circuit: withdraw the run that wrote the
        rows instead)."""
        if not reason or not reason.strip():
            raise ValueError("a withdrawal needs a non-empty reason")
        with self.transaction() as c:
            row = c.execute("SELECT state, input_origin, dataset_key FROM dataset_run "
                            "WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise ValueError(f"no such run: {run_id}")
            state, origin, key = row
            if origin == "legacy":
                raise ValueError(f"run {run_id} is a legacy import run; legacy rows are "
                                 f"governed by the legacy serving settings, not withdrawal")
            if state != "verified":
                raise ValueError(f"run {run_id} is {state!r}; only verified runs can be "
                                 f"withdrawn")
            if not self._run_has_observations(run_id):
                raise ValueError(
                    f"run {run_id} has no observations (a short-circuit for identical bytes "
                    f"or identical values, which holds no rows); withdraw the run that wrote "
                    f"the rows - its short-circuits are withdrawn with it")
            cascade = []
            for later, later_state in c.execute(
                    "SELECT id, state FROM dataset_run WHERE dataset_key = ? AND id > ? "
                    "ORDER BY id", (key, run_id)).fetchall():
                if later_state != "verified" or self._run_has_observations(later):
                    break
                cascade.append(later)
            reason = reason.strip()
            for rid in [run_id, *cascade]:
                detail = {"reason": reason, "previous_state": "verified"}
                if rid != run_id:
                    detail["cascaded_from"] = run_id
                self.add_event(at, "withdrawal", rid, detail)
                if not self.transition_run_state(rid, "verified", "withdrawn"):
                    raise ValueError(f"run {rid} left 'verified' concurrently")
        return [run_id, *cascade]

    def _run_has_observations(self, run_id: int) -> bool:
        return self.conn.execute("SELECT EXISTS (SELECT 1 FROM observation "
                                 "WHERE dataset_run_id = ?)", (run_id,)).fetchone()[0] == 1

    def close_orphan_runs(self, at: str, *,
                          min_age: timedelta = ORPHAN_MIN_AGE) -> list[int]:
        """Close runs still 'running' whose process is gone, as 'failed-operational' with
        event(operational_failure, {stage: orphaned, swept_because}). The scheduler calls it
        at start, under its instance lock. A run is swept only when
        - the scheduler itself started it: its dataset_key has a scheduler attempt marker
          still 'running' (scheduler_attempt_started) from no later than the run's start.
          Under the instance lock no scheduler is mid-attempt, so that run is orphaned
          (`swept_because: scheduler_attempt_interrupted`); or
        - it started at least `min_age` (ORPHAN_MIN_AGE, 6 h) before `at`: no dataset run
          takes that long, so its process died (`older_than_min_age`).
        A younger run without a scheduler marker may be a live manual CLI run (in the web
        container) and is left alone; if it is swept later anyway, the pipeline's
        compare-and-set state writes notice and abort it instead of resurrecting it."""
        now = _parse_utc(at)
        markers = {s.dataset_key: _parse_utc(s.last_attempt_at)
                   for s in self.scheduler_states() if s.last_attempt_state == "running"}
        with self.transaction() as c:
            running = c.execute("SELECT id, dataset_key, started_at FROM dataset_run "
                                "WHERE state = 'running' ORDER BY id").fetchall()
            swept = []
            for run_id, key, started_at in running:
                started = _parse_utc(started_at)
                marker = markers.get(key)
                if marker is not None and started is not None and marker <= started:
                    why = "scheduler_attempt_interrupted"
                elif started is None or now - started >= min_age:
                    why = "older_than_min_age"
                else:
                    continue
                if self.transition_run_state(run_id, "running", "failed-operational",
                                             finished_at=at):
                    self.add_event(at, "operational_failure", run_id, {
                        "stage": "orphaned", "swept_because": why,
                        "error": "run left 'running' by an interrupted process "
                                 "(closed at scheduler start)"})
                    swept.append(run_id)
        return swept

    # --- scheduler-owned attempts (Task 18A) ------------------------------------------------

    def scheduler_state(self, dataset_key: str) -> SchedulerState | None:
        """Last scheduler attempt only; never infer freshness from synthetic legacy runs."""
        row = self.conn.execute(
            "SELECT dataset_key, source_name, group_label, last_attempt_at, "
            "last_attempt_state, last_success_at, failure_streak, last_finished_at "
            "FROM scheduler_state WHERE dataset_key = ?", (dataset_key,)).fetchone()
        return SchedulerState(*row) if row is not None else None

    def scheduler_states(self) -> list[SchedulerState]:
        """Every persisted scheduler_state row (read-only status view), by dataset key."""
        return [SchedulerState(*row) for row in self.conn.execute(
            "SELECT dataset_key, source_name, group_label, last_attempt_at, "
            "last_attempt_state, last_success_at, failure_streak, last_finished_at "
            "FROM scheduler_state ORDER BY dataset_key")]

    def scheduler_attempt_started(self, dataset_key: str, source_name: str,
                                  group_label: str, at: str) -> None:
        """Pessimistic, atomic marker BEFORE external work. A killed attempt consumes a
        backoff step but retains any last success. Call outside a transaction to persist
        before network; the scheduler CLI's file lock provides exclusive ownership."""
        self.conn.execute(
            "INSERT INTO scheduler_state(dataset_key, source_name, group_label, "
            "last_attempt_at, last_attempt_state, failure_streak) "
            "VALUES (?, ?, ?, ?, 'running', 1) "
            "ON CONFLICT(dataset_key) DO UPDATE SET source_name=excluded.source_name, "
            "group_label=excluded.group_label, last_attempt_at=excluded.last_attempt_at, "
            "last_attempt_state='running', last_finished_at=NULL, "
            "failure_streak=scheduler_state.failure_streak + 1",
            (dataset_key, source_name, group_label, at))

    def scheduler_attempt_finished(self, dataset_key: str, state: str, at: str) -> None:
        """Finish an in-flight attempt; ONLY verified resets backoff and advances success.
        last_finished_at anchors retries after slow failures, without losing start time."""
        cur = self.conn.execute(
            "UPDATE scheduler_state SET last_attempt_state=?, last_finished_at=?, "
            "last_success_at=CASE WHEN ?='verified' THEN ? ELSE last_success_at END, "
            "failure_streak=CASE WHEN ?='verified' THEN 0 ELSE failure_streak END "
            "WHERE dataset_key=? AND last_attempt_state='running'",
            (state, at, state, at, state, dataset_key))
        if cur.rowcount != 1:
            raise ValueError(f"no in-flight scheduler attempt for {dataset_key!r}")

    # --- derived layer (project 3) ---------------------------------------------------------------
    # Inputs are served *fetched* rows only (never legacy); values are text, never REAL.

    def upsert_derived_series(self, rows: list[dict]) -> None:
        """Idempotent sync of the WHOLE derived registry (`rows` keys: key, formula,
        base_series_id, params_json, unit, caveats_json, active; unit is a DERIVED_UNITS code,
        caveats_json a JSON array of DERIVED_CAVEATS codes). An active key
        absent from `rows` is set inactive (its rows stay, unserved). ValueError (nothing
        written) when a row redefines an existing key's formula, base or params: rows computed
        under the old definition must never be relabelled; declare a new key instead."""
        with self.transaction() as c:
            for r in rows:
                old = c.execute("SELECT formula, base_series_id, params_json FROM derived_series "
                                "WHERE key = ?", (r["key"],)).fetchone()
                if old is not None and (old[0], old[1], json.loads(old[2])) != (
                        r["formula"], r["base_series_id"], json.loads(r["params_json"])):
                    raise ValueError(f"{r['key']}: formula/base/params of an existing derived "
                                     f"key cannot change; declare a new key")
                # update in place (migration 0014 refuses REPLACE/upsert-style re-inserts)
                c.execute(
                    "UPDATE derived_series SET unit = :unit, caveats_json = :caveats_json, "
                    "active = :active "
                    "WHERE key = :key" if old is not None else
                    "INSERT INTO derived_series(key, formula, base_series_id, params_json, unit, "
                    "caveats_json, active) VALUES (:key, :formula, :base_series_id, "
                    ":params_json, :unit, :caveats_json, :active)",
                    {**r, "active": int(r["active"])})
            keep = [r["key"] for r in rows]
            c.execute("UPDATE derived_series SET active = 0 WHERE active = 1 AND key NOT IN "
                      "(SELECT value FROM json_each(?))", (json.dumps(keep),))

    def derived_series_rows(self, *, active_only: bool = True) -> list[dict]:
        """Every (active) derived series with its base frequency, ordered by key."""
        rows = self.conn.execute(
            "SELECT d.id, d.key, d.formula, d.base_series_id, s.frequency, d.params_json, "
            "d.unit, d.active, d.caveats_json FROM derived_series d "
            "JOIN series s ON s.id = d.base_series_id "
            f"{'WHERE d.active = 1 ' if active_only else ''}ORDER BY d.key").fetchall()
        keys = ("id", "key", "formula", "base_series_id", "frequency", "params", "unit", "active",
                "caveats")
        return [dict(zip(keys, (*r[:5], json.loads(r[5]), r[6], bool(r[7]), json.loads(r[8]))))
                for r in rows]

    def served_fetched_inputs(self, series_id: str) -> dict[str, tuple[int, str]]:
        """period -> (observation id, value_text) of the served *fetched* rows of a series."""
        return {p: (i, v) for p, i, v in self.conn.execute(
            "SELECT period, id, value_text FROM served_observation "
            "WHERE series_id = ? AND kind = 'fetched'", (series_id,))}

    def begin_derived_run(self, started_at: str, trigger: str, scope: list[str]) -> int:
        """New derived_run in state 'computing'; scope = the derived keys it evaluates."""
        return self.conn.execute(
            "INSERT INTO derived_run(started_at, state, trigger, scope_json) "
            "VALUES (?, 'computing', ?, ?)", (started_at, trigger, json.dumps(scope))).lastrowid

    def derived_known_inputs(self, derived_series_id: int) -> set[tuple[str, str]]:
        """(period, input_obs_ids_json) of the series' serving candidate per period: the
        newest (highest id) 'match' row of a verified run - the same row served_derived
        considers. Older versions never count: after a base withdrawal back to an older
        vintage, derive writes a new version on those inputs (the old row is not revived)."""
        return set(self.conn.execute(
            "SELECT d.period, d.input_obs_ids_json FROM derived_observation d "
            "WHERE d.derived_series_id = ? AND d.id = (SELECT c.id FROM derived_observation c "
            "JOIN derived_run r ON r.id = c.run_id AND r.state = 'verified' "
            "WHERE c.derived_series_id = d.derived_series_id AND c.period = d.period "
            "AND c.state = 'match' ORDER BY c.id DESC LIMIT 1)", (derived_series_id,)))

    def derived_known_skips(self, derived_series_id: int
                            ) -> set[tuple[str | None, str, tuple[int, ...]]]:
        """(period, kind, input ids) of the series' zero_denominator / missing_base_period
        events in verified runs (input ids from detail_json, () when absent)."""
        return {(p, k, tuple(json.loads(d or "{}").get("input_ids", [])))
                for p, k, d in self.conn.execute(
                    "SELECT e.period, e.kind, e.detail_json FROM derived_event e "
                    "JOIN derived_run r ON r.id = e.run_id AND r.state = 'verified' "
                    "WHERE e.derived_series_id = ? "
                    "AND e.kind IN ('zero_denominator', 'missing_base_period')",
                    (derived_series_id,))}

    def series_ids(self) -> set[str]:
        """Every series id in the database (active or not)."""
        return {i for (i,) in self.conn.execute("SELECT id FROM series")}

    def write_derived_observations(self, run_id: int, computed_at: str,
                                   rows: list[tuple[int, str, str, int, str]]) -> None:
        """Insert (derived_series_id, period, value_text, scale, input_obs_ids_json) rows,
        state 'pending'."""
        self.conn.executemany(
            "INSERT INTO derived_observation(derived_series_id, period, value_text, scale, "
            "input_obs_ids_json, computed_at, run_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(*r, computed_at, run_id) for r in rows])

    def add_derived_event(self, ts: str, run_id: int, derived_series_id: int | None,
                          period: str | None, kind: str, detail: dict | None = None) -> None:
        self.conn.execute(
            "INSERT INTO derived_event(ts, run_id, derived_series_id, period, kind, detail_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts, run_id, derived_series_id, period, kind,
             json.dumps(detail) if detail is not None else None))

    def derived_observations_of_run(self, run_id: int) -> list[dict]:
        """The run's derived rows with their series definition, by id."""
        keys = ("id", "derived_series_id", "key", "formula", "params", "base_series_id",
                "frequency", "period", "value_text", "scale", "input_ids")
        rows = self.conn.execute(
            "SELECT d.id, d.derived_series_id, ds.key, ds.formula, ds.params_json, "
            "ds.base_series_id, s.frequency, d.period, d.value_text, d.scale, "
            "d.input_obs_ids_json FROM derived_observation d "
            "JOIN derived_series ds ON ds.id = d.derived_series_id "
            "JOIN series s ON s.id = ds.base_series_id WHERE d.run_id = ? ORDER BY d.id",
            (run_id,)).fetchall()
        return [dict(zip(keys, (*r[:4], json.loads(r[4]), *r[5:10], json.loads(r[10]))))
                for r in rows]

    def observations_by_ids(self, ids: list[int]) -> dict[int, dict]:
        """id -> {series_id, period, value_text, kind, served} for the known ids; `served` is
        True iff the id is currently in served_observation as a fetched row."""
        rows = self.conn.execute(
            "SELECT o.id, o.series_id, o.period, o.value_text, o.kind, "
            "o.id IN (SELECT id FROM served_observation WHERE kind = 'fetched' "
            "AND id IN (SELECT value FROM json_each(?))) "
            "FROM observation o WHERE o.id IN (SELECT value FROM json_each(?))",
            (json.dumps(list(ids)),) * 2).fetchall()
        return {i: {"series_id": s, "period": p, "value_text": v, "kind": k,
                    "served": bool(served)} for i, s, p, v, k, served in rows}

    def set_derived_row_states(self, states: list[tuple[int, str]]) -> None:
        """(derived_observation id, 'match' | 'mismatch'); each row's state is set once."""
        self.conn.executemany("UPDATE derived_observation SET state = ? WHERE id = ?",
                              [(s, i) for i, s in states])

    def finish_derived_run(self, run_id: int, state: str, finished_at: str, *, n_written: int,
                           n_checked: int, n_mismatch: int) -> None:
        """Compare-and-set 'computing' -> 'verified' | 'failed'; ValueError otherwise.
        'verified' also needs every row of the run already 'match' (set_derived_row_states
        records each verdict BEFORE finishing); a pending or mismatched row refuses it."""
        if state not in ("verified", "failed"):
            raise ValueError(f"a derived run finishes verified or failed, not {state!r}")
        if state == "verified":
            open_rows = [st for (st,) in self.conn.execute(
                "SELECT DISTINCT state FROM derived_observation WHERE run_id = ? "
                "AND state <> 'match' ORDER BY state", (run_id,))]
            if open_rows:
                raise ValueError(f"derived run {run_id} has {'/'.join(open_rows)} rows; "
                                 f"it cannot be verified")
        cur = self.conn.execute(
            "UPDATE derived_run SET state = ?, finished_at = ?, n_written = ?, n_checked = ?, "
            "n_mismatch = ? WHERE id = ? AND state = 'computing'",
            (state, finished_at, n_written, n_checked, n_mismatch, run_id))
        if cur.rowcount != 1:
            raise ValueError(f"derived run {run_id} is not computing")

    _SERVED_DERIVED_COLUMNS = (
        "derived_key", "period", "value_text", "scale", "unit", "is_calculated", "formula",
        "base_series_id", "inputs", "licence", "licence_url",
        "attribution", "computed_at", "derived_run_id", "derived_observation_id", "input_ids",
        "caveats")

    def served_derived_rows(self, key: str, limit: int,
                            offset: int = 0) -> tuple[int, list[dict]]:
        """(served row count, one page newest period first) of a derived key; `inputs` and
        `input_ids` decoded, `inputs` in input_ids (formula) order - the view's aggregate
        order is not guaranteed by SQLite."""
        total = self.conn.execute("SELECT COUNT(*) FROM served_derived WHERE derived_key = ?",
                                  (key,)).fetchone()[0]
        rows = self.conn.execute(
            f"SELECT {', '.join(self._SERVED_DERIVED_COLUMNS)} FROM served_derived "
            "WHERE derived_key = ? ORDER BY period DESC LIMIT ? OFFSET ?",
            (key, limit, offset)).fetchall()
        out = [dict(zip(self._SERVED_DERIVED_COLUMNS, r)) for r in rows]
        for r in out:
            r["input_ids"] = json.loads(r["input_ids"])
            r["caveats"] = json.loads(r["caveats"])
            pos = {i: n for n, i in enumerate(r["input_ids"])}
            r["inputs"] = sorted(json.loads(r["inputs"]), key=lambda x: pos[x["observation_id"]])
        return total, out

    def derived_rows_of_series(self, key: str, limit: int) -> list[dict]:
        """Every stored version of a derived key (newest period, then newest id, first) with
        its run state and whether served_derived serves it."""
        keys = ("id", "period", "value_text", "scale", "state", "run_id", "run_state",
                "computed_at", "input_ids", "served")
        rows = self.conn.execute(
            "SELECT d.id, d.period, d.value_text, d.scale, d.state, d.run_id, r.state, "
            "d.computed_at, d.input_obs_ids_json, d.id IN (SELECT derived_observation_id "
            "FROM served_derived WHERE derived_key = ?) FROM derived_observation d "
            "JOIN derived_series ds ON ds.id = d.derived_series_id "
            "JOIN derived_run r ON r.id = d.run_id WHERE ds.key = ? "
            "ORDER BY d.period DESC, d.id DESC LIMIT ?", (key, key, limit)).fetchall()
        return [dict(zip(keys, (*r[:8], json.loads(r[8]), bool(r[9])))) for r in rows]

    def derived_status_rows(self) -> list[dict]:
        """Per ACTIVE derived series: served value count, the latest verified run whose scope
        covered it, and the newest fetched_at of its served fetched base rows."""
        keys = ("key", "base_series_id", "served_values", "last_covered_run_id",
                "last_covered_at", "base_latest_fetched_at")
        rows = self.conn.execute(
            "WITH served AS (SELECT derived_key, COUNT(*) AS n FROM served_derived "
            "GROUP BY derived_key), "
            # Newest fetched_at among a base's served fetched rows: walk its fetched rows
            # newest first and stop at the first one served_observation serves (same answer
            # as MAX over the view; the whole-series view scan costs O(vintages^2) per base).
            # `LIMIT -1` keeps the ordered subquery from being flattened into the outer
            # WHERE, which would test every row before sorting.
            "base AS (SELECT b.base_series_id AS series_id, (SELECT n.fetched_at FROM "
            "(SELECT o.id, o.fetched_at FROM observation o WHERE o.series_id = "
            "b.base_series_id AND o.kind = 'fetched' ORDER BY o.fetched_at DESC, o.id DESC "
            "LIMIT -1) n WHERE EXISTS (SELECT 1 FROM served_observation so WHERE so.id = n.id) "
            "LIMIT 1) AS latest "
            "FROM (SELECT DISTINCT base_series_id FROM derived_series WHERE active = 1) b), "
            "covered AS (SELECT ds.id AS dsid, (SELECT r.id FROM derived_run r "
            "WHERE r.state = 'verified' AND EXISTS (SELECT 1 FROM json_each(r.scope_json) j "
            "WHERE j.value = ds.key) ORDER BY r.id DESC LIMIT 1) AS run_id "
            "FROM derived_series ds WHERE ds.active = 1) "
            "SELECT ds.key, ds.base_series_id, COALESCE(sv.n, 0), c.run_id, r.started_at, "
            "b.latest FROM derived_series ds JOIN covered c ON c.dsid = ds.id "
            "LEFT JOIN derived_run r ON r.id = c.run_id "
            "LEFT JOIN served sv ON sv.derived_key = ds.key "
            "LEFT JOIN base b ON b.series_id = ds.base_series_id "
            "WHERE ds.active = 1 ORDER BY ds.key").fetchall()
        return [dict(zip(keys, r)) for r in rows]

    def derived_runs(self, limit: int) -> list[dict]:
        """The newest `limit` derived runs, scope decoded."""
        keys = ("id", "started_at", "finished_at", "state", "trigger", "scope", "n_written",
                "n_checked", "n_mismatch")
        rows = self.conn.execute(
            "SELECT id, started_at, finished_at, state, trigger, scope_json, n_written, "
            "n_checked, n_mismatch FROM derived_run ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(zip(keys, (*r[:5], json.loads(r[5]), *r[6:]))) for r in rows]

    def derived_run_counts(self, since: str) -> dict[str, int]:
        """state -> number of derived runs started at or after `since` (ISO-8601 UTC; stored
        stamps share the +00:00 form, so text order is time order, as in event_totals)."""
        return dict(self.conn.execute(
            "SELECT state, COUNT(*) FROM derived_run WHERE started_at >= ? GROUP BY state",
            (since,)).fetchall())

    def close(self) -> None:
        self.conn.close()

    # --- public site reads (project 4) ---------------------------------------------------------
    # Read-only, plain dicts, numbers exactly as stored (value_text). Only redistributable
    # sources appear: served_observation and served_derived already gate the licence.

    def public_counts(self) -> dict:
        """Headline counts for the home page: served primary series, publishing sources and the
        newest verified receipt. Built from small aggregates (series, dataset_run, raw_fetch);
        a global COUNT over the serving view costs seconds and is never used here."""
        per_source = dict(self.conn.execute(
            "SELECT s.source_id, COUNT(*) FROM series s JOIN source p ON p.id = s.source_id "
            "WHERE s.active = 1 AND s.role = 'primary' AND p.redistribution_ok = 1 "
            "AND EXISTS (SELECT 1 FROM observation o JOIN dataset_run r "
            "            ON r.id = o.dataset_run_id WHERE o.series_id = s.id "
            "            AND o.kind = 'fetched' AND r.state = 'verified') GROUP BY s.source_id"
        ).fetchall())
        last = self.conn.execute(
            "SELECT MAX(f.fetched_at) FROM raw_fetch f JOIN dataset_run r "
            "ON r.id = f.dataset_run_id WHERE r.state = 'verified'").fetchone()[0]
        return {"series": sum(per_source.values()),
                "sources": len(per_source),
                "last_fetched_at": last}

    def public_catalogue(self) -> list[dict]:
        """Every served primary series (metadata only, no value), ordered by series id.
        Latest values are fetched for the visible rows through `public_latest_values`: a
        global join over the serving view costs seconds, a 50-id loop costs milliseconds."""
        keys = ("id", "indicator_key", "geography", "theme", "frequency", "unit", "multiplier",
                "seasonal_adjustment", "base_year", "native_code", "url", "role", "source")
        rows = self.conn.execute(
            "SELECT s.id, s.indicator_key, s.geography, s.theme, s.frequency, s.unit, "
            "s.multiplier, s.seasonal_adjustment, s.base_year, s.native_code, s.url, s.role, "
            "p.name FROM series s JOIN source p ON p.id = s.source_id "
            "WHERE s.active = 1 AND s.role = 'primary' AND p.redistribution_ok = 1 "
            "AND EXISTS (SELECT 1 FROM observation o JOIN dataset_run r "
            "            ON r.id = o.dataset_run_id WHERE o.series_id = s.id "
            "            AND o.kind = 'fetched' AND r.state = 'verified') ORDER BY s.id").fetchall()
        return [dict(zip(keys, r)) | {"family": _family_of(r[1])} for r in rows]

    def public_latest_values(self, series_ids: list[str]) -> dict[str, dict]:
        """Newest served row of each requested series (id -> period/value/flag/fetched_at).
        One indexed lookup per id: the IN-list form makes SQLite evaluate the view per row and
        is two orders of magnitude slower. Missing ids are absent from the result."""
        sql = ("SELECT period, value_text, status_flag, fetched_at FROM served_observation "
               "WHERE series_id = ? AND id = (SELECT w.id FROM served_observation w "
               "WHERE w.series_id = ? ORDER BY w.period DESC LIMIT 1)")
        keys = ("period", "value_text", "status_flag", "fetched_at")
        out: dict[str, dict] = {}
        for sid in series_ids:
            row = self.conn.execute(sql, (sid, sid)).fetchone()
            if row is not None:
                out[sid] = dict(zip(keys, row))
        return out

    def public_series(self, series_id: str) -> dict | None:
        """One series with source text and its newest served value; None when the series does
        not exist, is inactive, or its source is not redistributable. `role` is returned so the
        caller can refuse a cross-check entry."""
        keys = ("id", "indicator_key", "geography", "theme", "frequency", "unit", "multiplier",
                "base_year", "seasonal_adjustment", "native_code", "url", "role", "source",
                "latest_period", "latest_value_text", "latest_status_flag", "latest_fetched_at",
                "attribution", "licence", "licence_url")
        sql = ("SELECT s.id, s.indicator_key, s.geography, s.theme, s.frequency, s.unit, "
               "s.multiplier, s.base_year, s.seasonal_adjustment, s.native_code, s.url, s.role, "
               "p.name, o.period, o.value_text, o.status_flag, o.fetched_at, "
               "p.attribution, p.licence, p.licence_url "
               "FROM series s JOIN source p ON p.id = s.source_id "
               "JOIN served_observation o ON o.id = (SELECT w.id FROM served_observation w "
               "WHERE w.series_id = s.id ORDER BY w.period DESC LIMIT 1) "
               "WHERE s.id = ? AND s.active = 1 AND p.redistribution_ok = 1")
        row = self.conn.execute(sql, (series_id,)).fetchone()
        return dict(zip(keys, row)) | {"family": _family_of(row[1])} if row else None

    def public_series_values(self, series_id: str) -> list[dict]:
        """All served values of one series, oldest period first, with the payload hash of each
        fetched row. No cap here: the caller slices a window for display."""
        keys = ("period", "value_text", "status_flag", "fetched_at", "run_id", "raw_sha")
        rows = self.conn.execute(
            "SELECT o.period, o.value_text, o.status_flag, o.fetched_at, o.dataset_run_id, "
            "f.sha256 FROM served_observation o LEFT JOIN raw_fetch f ON f.id = o.raw_fetch_id "
            "WHERE o.series_id = ? ORDER BY o.period", (series_id,)).fetchall()
        return [dict(zip(keys, r)) for r in rows]

    def public_recent_values(self, series_id: str, limit: int) -> list[dict]:
        """The newest `limit` served values, oldest period first (card sparklines). Reads the
        tail through the period index instead of materialising the whole history."""
        keys = ("period", "value_text", "status_flag", "fetched_at", "run_id", "raw_sha")
        rows = self.conn.execute(
            "SELECT o.period, o.value_text, o.status_flag, o.fetched_at, o.dataset_run_id, "
            "f.sha256 FROM served_observation o LEFT JOIN raw_fetch f ON f.id = o.raw_fetch_id "
            "WHERE o.series_id = ? ORDER BY o.period DESC LIMIT ?", (series_id, limit)).fetchall()
        return [dict(zip(keys, r)) for r in reversed(rows)]

    def public_values_between(self, series_id: str, start: str,
                              end: str | None = None) -> list[dict]:
        """Served values from `start` (inclusive) to `end` (inclusive), oldest first. One index
        range instead of the whole history, so a 15-minute series reads a day, not 65k rows."""
        keys = ("period", "value_text", "status_flag", "fetched_at", "run_id", "raw_sha")
        sql = ("SELECT o.period, o.value_text, o.status_flag, o.fetched_at, o.dataset_run_id, "
               "f.sha256 FROM served_observation o LEFT JOIN raw_fetch f ON f.id = o.raw_fetch_id "
               "WHERE o.series_id = ? AND o.period >= ?")
        params: list[str] = [series_id, start]
        if end is not None:
            sql += " AND o.period <= ?"
            params.append(end)
        rows = self.conn.execute(sql + " ORDER BY o.period", params).fetchall()
        return [dict(zip(keys, r)) for r in rows]

    def public_day_counts(self, series_id: str) -> tuple[tuple[str, int], ...]:
        """Each UTC day a series publishes with its interval count, newest first. The picker of
        a 15-minute series needs the counts: the newest day is often partial."""
        rows = self.conn.execute(
            "SELECT substr(period, 1, 10) AS day, COUNT(*) FROM served_observation "
            "WHERE series_id = ? GROUP BY day ORDER BY day DESC", (series_id,)).fetchall()
        return tuple((r[0], r[1]) for r in rows)

    def public_provenance(self, series_id: str) -> dict | None:
        """The receipt, run and verification behind one series' newest served value. `sampled`
        says whether THIS value was one of the independently checked items (not whether the
        dataset was verified)."""
        keys = ("period", "value_text", "fetched_at", "run_id", "run_started_at",
                "run_finished_at", "run_state", "raw_url", "raw_fetched_at", "http_status",
                "sha256", "bytes", "verification_id", "verification_created_at", "sample_size",
                "verification_passed", "sample_procedure", "verifier_channel", "sampled",
                "native_code", "series_url", "licence", "licence_url", "attribution")
        row = self.conn.execute(
            "SELECT o.period, o.value_text, o.fetched_at, o.dataset_run_id, r.started_at, "
            "r.finished_at, r.state, f.url, f.fetched_at, f.http_status, f.sha256, f.bytes, "
            "v.id, v.created_at, v.sample_size, v.passed, v.sample_procedure, v.verifier_channel, "
            "EXISTS (SELECT 1 FROM verification_item i WHERE i.verification_id = v.id "
            "        AND i.series_id = o.series_id AND i.period = o.period), "
            "s.native_code, s.url, p.licence, p.licence_url, p.attribution "
            "FROM served_observation o JOIN dataset_run r ON r.id = o.dataset_run_id "
            "LEFT JOIN raw_fetch f ON f.id = o.raw_fetch_id "
            "LEFT JOIN verification v ON v.dataset_run_id = o.dataset_run_id "
            "JOIN series s ON s.id = o.series_id JOIN source p ON p.id = s.source_id "
            "WHERE o.series_id = ? ORDER BY o.period DESC LIMIT 1", (series_id,)).fetchone()
        return dict(zip(keys, row)) if row else None

    def public_revisions(self, series_id: str) -> tuple[list[dict], int]:
        """(periods whose published value or flag changed at least once, count of periods with
        no change). Re-fetches of an unchanged value are not revisions: only a different
        value_text or status_flag counts, and consecutive identical vintages collapse to the
        first. The last kept version of a changed period is marked `served` when the site
        serves that period. Failed, pending and withdrawn runs are never published history."""
        rows = self.conn.execute(
            "WITH verified AS (SELECT o.id, o.period, o.value_text, o.status_flag, o.fetched_at, "
            "                         o.dataset_run_id "
            "                  FROM observation o JOIN dataset_run r ON r.id = o.dataset_run_id "
            "                  WHERE o.series_id = ? AND o.kind = 'fetched' "
            "                    AND r.state = 'verified'), "
            "     changed AS (SELECT period FROM verified GROUP BY period "
            "                 HAVING COUNT(DISTINCT value_text || char(31) || "
            "                                COALESCE(status_flag, '')) > 1) "
            "SELECT period, value_text, status_flag, fetched_at, dataset_run_id, "
            "       EXISTS (SELECT 1 FROM served_observation so WHERE so.id = verified.id) "
            "FROM verified WHERE period IN (SELECT period FROM changed) "
            "ORDER BY period DESC, fetched_at, id", (series_id,)).fetchall()
        grouped: dict[str, list[dict]] = {}
        served: set[str] = set()
        for period, value, flag, fetched_at, run_id, is_served in rows:
            versions = grouped.setdefault(period, [])
            if not versions or (versions[-1]["value_text"], versions[-1]["status_flag"]) != (value, flag):
                versions.append({"value_text": value, "status_flag": flag,
                                 "fetched_at": fetched_at, "run_id": run_id, "served": False})
            if is_served:
                served.add(period)
        for period, versions in grouped.items():
            if period in served:
                versions[-1]["served"] = True
        total = self.conn.execute(
            "SELECT COUNT(DISTINCT o.period) FROM observation o "
            "JOIN dataset_run r ON r.id = o.dataset_run_id "
            "WHERE o.series_id = ? AND o.kind = 'fetched' AND r.state = 'verified'",
            (series_id,)).fetchone()[0]
        return ([{"period": p, "versions": grouped[p]} for p in grouped], total - len(grouped))

    def public_derived_for_base(self, series_id: str) -> list[dict]:
        """Active calculated series computed from this base, with their newest served value
        (None when a declared series has no served value yet)."""
        keys = ("key", "formula", "unit", "caveats", "latest_period", "latest_value_text")
        rows = self.conn.execute(
            "SELECT ds.key, ds.formula, ds.unit, ds.caveats_json, "
            "(SELECT sd.period FROM served_derived sd WHERE sd.derived_key = ds.key "
            " ORDER BY sd.period DESC LIMIT 1), "
            "(SELECT sd.value_text FROM served_derived sd WHERE sd.derived_key = ds.key "
            " ORDER BY sd.period DESC LIMIT 1) "
            "FROM derived_series ds WHERE ds.base_series_id = ? AND ds.active = 1 "
            "ORDER BY ds.key", (series_id,)).fetchall()
        return [dict(zip(keys, r)) | {"caveats": json.loads(r[3])} for r in rows]

    def public_derived(self, key: str) -> dict | None:
        """One calculated series' definition and its newest served value."""
        keys = ("key", "formula", "base_series_id", "params", "unit", "caveats", "active",
                "served_count", "latest_period", "latest_value_text", "base_indicator_key",
                "base_geography", "base_source", "base_attribution")
        row = self.conn.execute(
            "SELECT ds.key, ds.formula, ds.base_series_id, ds.params_json, ds.unit, "
            "ds.caveats_json, ds.active, "
            "(SELECT COUNT(*) FROM served_derived sd WHERE sd.derived_key = ds.key), "
            "(SELECT sd.period FROM served_derived sd WHERE sd.derived_key = ds.key "
            " ORDER BY sd.period DESC LIMIT 1), "
            "(SELECT sd.value_text FROM served_derived sd WHERE sd.derived_key = ds.key "
            " ORDER BY sd.period DESC LIMIT 1), "
            "b.indicator_key, b.geography, p.name, p.attribution "
            "FROM derived_series ds JOIN series b ON b.id = ds.base_series_id "
            "JOIN source p ON p.id = b.source_id WHERE ds.key = ? AND ds.active = 1",
            (key,)).fetchone()
        if row is None:
            return None
        out = dict(zip(keys[:7], row[:7]))
        out["params"] = json.loads(row[3])
        out["caveats"] = json.loads(row[5])
        for name, value in zip(keys[7:], row[7:]):
            out[name] = value
        return out

    def public_derived_values(self, key: str) -> list[dict]:
        """All served values of one calculated series, oldest period first."""
        keys = ("period", "value_text", "computed_at", "run_id", "scale")
        rows = self.conn.execute(
            "SELECT period, value_text, computed_at, derived_run_id, scale FROM served_derived "
            "WHERE derived_key = ? ORDER BY period", (key,)).fetchall()
        return [dict(zip(keys, r)) for r in rows]

    def public_cross_checks(self, series_id: str) -> list[dict]:
        """Other publishers' series with the same indicator key, served and active, shown as
        cross-checks and never as catalogue entries."""
        keys = ("id", "source", "attribution", "unit", "latest_period", "latest_value_text",
                "latest_status_flag", "latest_fetched_at")
        rows = self.conn.execute(
            "SELECT s2.id, p.name, p.attribution, s2.unit, o.period, o.value_text, "
            "o.status_flag, o.fetched_at "
            "FROM series s1 JOIN series s2 ON s2.indicator_key = s1.indicator_key "
            "AND s2.id <> s1.id AND s2.active = 1 AND s2.role = 'cross_check' "
            "JOIN source p ON p.id = s2.source_id AND p.redistribution_ok = 1 "
            "JOIN served_observation o ON o.id = (SELECT w.id FROM served_observation w "
            "WHERE w.series_id = s2.id ORDER BY w.period DESC LIMIT 1) "
            "WHERE s1.id = ? ORDER BY s2.id", (series_id,)).fetchall()
        return [dict(zip(keys, r)) for r in rows]

    def public_sources(self) -> list[dict]:
        """Every source with its licence and counts. Withheld sources have series 0 and no
        last receipt: the site names them without publishing a value. Two small aggregates
        over series/dataset_run/raw_fetch replace per-source scans of the serving view."""
        sources = self.conn.execute(
            "SELECT id, name, licence, licence_url, attribution, redistribution_ok "
            "FROM source ORDER BY redistribution_ok DESC, name").fetchall()
        counts = dict(self.conn.execute(
            "SELECT s.source_id, COUNT(*) FROM series s JOIN source p ON p.id = s.source_id "
            "WHERE s.active = 1 AND s.role = 'primary' AND p.redistribution_ok = 1 "
            "AND EXISTS (SELECT 1 FROM observation o JOIN dataset_run r "
            "            ON r.id = o.dataset_run_id WHERE o.series_id = s.id "
            "            AND o.kind = 'fetched' AND r.state = 'verified') GROUP BY s.source_id"
        ).fetchall())
        last = dict(self.conn.execute(
            "SELECT r.source_id, MAX(f.fetched_at) FROM raw_fetch f "
            "JOIN dataset_run r ON r.id = f.dataset_run_id "
            "WHERE r.state = 'verified' GROUP BY r.source_id").fetchall())
        return [{"name": name, "licence": licence, "licence_url": url,
                 "attribution": attribution, "redistribution_ok": bool(ok),
                 "series": counts.get(sid, 0), "last_fetched_at": last.get(sid)}
                for sid, name, licence, url, attribution, ok in sources]


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migration("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP) STRICT"
    )
    done = {r[0] for r in conn.execute("SELECT version FROM schema_migration")}
    pending = [f for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"))
               if f.stem not in done]
    # A migration that rebuilds a referenced table (0006 rebuilds `series` to extend its
    # frequency CHECK) needs foreign_keys OFF at statement time: with FK ON, SQLite fails
    # the DROP on immediate child references and silently rewrites child REFERENCES clauses
    # during RENAME. The pragma is a transaction no-op, so it is toggled here, outside the
    # per-file transaction; integrity of the result is verified with foreign_key_check.
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        for f in pending:
            record = f"INSERT INTO schema_migration(version) VALUES ('{f.stem}');"
            try:
                # executescript is required for multi-statement files (triggers contain ';').
                # The script opens its transaction but does NOT commit it: foreign_key_check
                # runs next, INSIDE it, so a violation rolls the migration AND its
                # schema_migration record back together (no corrupt applied version; a later
                # open retries the file rather than skipping it); COMMIT only on a clean check.
                conn.executescript(f"BEGIN;\n{f.read_text()}\n{record}")
                bad = conn.execute("PRAGMA foreign_key_check").fetchall()
                if bad:
                    raise RuntimeError(
                        f"foreign key violations after migration {f.stem}: {bad[:5]}")
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        # Run on every open, even with nothing pending: corruption committed by an older
        # non-atomic migrator (bad row + recorded version) is never silently accepted.
        bad = conn.execute("PRAGMA foreign_key_check").fetchall()
        if bad:
            raise RuntimeError(f"foreign key violations in database: {bad[:5]}")
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def open_db(path: str | Path) -> Db:
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=BUSY_TIMEOUT_S)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        _migrate(conn)
    except BaseException:
        conn.close()  # do not leak the open (WAL) handle when migration fails
        raise
    return Db(conn)


def _expected_migrations() -> set[str]:
    return {f.stem for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")}


def _file_stamp(p: Path) -> tuple[int, int]:
    st = p.stat()
    return st.st_mtime_ns, st.st_size


def _wal(p: Path) -> Path:
    return Path(str(p) + "-wal")


def _open_refusal(p: Path, e: sqlite3.DatabaseError) -> ReadOnlyOpenError:
    """The refusal for a failed schema read, naming the real cause (review Minor 3)."""
    if "no such table" in str(e):
        return ReadOnlyOpenError(f"{p}: no schema_migration table, not a Prumo database ({e})")
    hint = ""
    if _wal(p).exists() and not Path(str(p) + "-shm").exists():
        hint = ("; a -wal file without its -shm cannot be read from a read-only mount: the "
                "writer (scheduler) recovers it on its next start")
    return ReadOnlyOpenError(f"{p}: cannot open the database read-only "
                             f"({type(e).__module__}.{type(e).__name__}: {e}){hint}")


def open_db_readonly(path: str | Path, *, immutable: bool | None = None) -> Db:
    """Open an EXISTING database strictly read-only for reports (status, lag): sqlite URI
    `mode=ro`, `query_only`, no migration, no journal-mode change, never a new file.

    Refuses (ReadOnlyOpenError) a missing file, a file it cannot read (the sqlite error is
    named) and a schema whose applied migrations differ from this code's: older means the
    writer (scheduler) has not migrated it yet, newer means this code is older than the
    database. Neither is ever "fixed" from here.

    A WAL database with no -wal file has no open writer; it is then opened `immutable=1`
    (unless `immutable=False`), because a plain read-only WAL open would create -wal/-shm
    files that a read-only handle cannot remove. With a writer running (the -wal file exists)
    the normal `mode=ro` open reads its committed state. The -wal test is not atomic: a
    writer that starts meanwhile can make an immutable read fail with sqlite3.DatabaseError
    (the schema read here then retries once with plain `mode=ro`) or silently return wrong
    results; `read_db_readonly` detects the writer afterwards and redoes the read."""
    p = Path(path)
    if not p.is_file():
        raise ReadOnlyOpenError(f"database not found: {p} (read-only reports never create one;"
                                " check --db / PRUMO_DB_PATH)")
    if immutable is None:
        immutable = not _wal(p).exists()
    stamp = _file_stamp(p) if immutable else None  # taken BEFORE the immutable open
    uri = p.resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    conn = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=BUSY_TIMEOUT_S)
    try:
        try:
            conn.execute("PRAGMA query_only=ON")
            applied = {r[0] for r in conn.execute("SELECT version FROM schema_migration")}
        except sqlite3.DatabaseError as e:
            if immutable:  # possibly a concurrent writer: one plain read-only retry
                conn.close()
                return open_db_readonly(p, immutable=False)
            raise _open_refusal(p, e) from None
        expected = _expected_migrations()
        if applied - expected:
            raise ReadOnlyOpenError(
                f"{p}: schema is newer than this code (unknown migrations "
                f"{sorted(applied - expected)}); use the matching code version")
        if expected - applied:
            raise ReadOnlyOpenError(
                f"{p}: schema is older than this code (missing migrations "
                f"{sorted(expected - applied)}); the writer (scheduler) applies migrations "
                "first - a read-only report never migrates")
    except BaseException:
        conn.close()
        raise
    db = Db(conn, immutable=immutable)
    db.immutable_stamp = stamp
    return db


def _read_snapshot(db: Db, read: Callable[[Db], T]) -> T:
    """`read(db)` inside ONE deferred read transaction: every statement sees the same
    snapshot, so a multi-statement report is never torn by a writer committing between two
    of its SELECTs (review Minor 2). Works on mode=ro and immutable handles."""
    db.conn.execute("BEGIN")
    try:
        result = read(db)
    except BaseException:
        if db.conn.in_transaction:
            try:
                db.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass  # the read's own error is the one to report
        raise
    db.conn.execute("COMMIT")
    return result


def _writer_appeared(db: Db, p: Path) -> bool:
    """Did a writer touch the file while an immutable handle read it? (-wal now exists, or
    the main file's mtime/size moved: a writer that checkpointed and exited.)"""
    return _wal(p).exists() or _file_stamp(p) != db.immutable_stamp


def read_db_readonly(path: str | Path, read: Callable[[Db], T]) -> T:
    """`read(db)` on a read-only handle (open_db_readonly) in one read transaction, closed
    afterwards. When the handle was opened `immutable=1`, its result is trusted only if no
    writer appeared meanwhile: SQLite documents wrong results or SQLITE_CORRUPT for an
    immutable reader whose file changes. So on sqlite3.DatabaseError, or when a -wal file
    now exists or the main file changed, the result is discarded and the whole read is redone
    ONCE with plain `mode=ro`, which sees the writer's committed state. Any other failure
    propagates."""
    p = Path(path)
    db = open_db_readonly(p)
    if not db.immutable:
        try:
            return _read_snapshot(db, read)
        finally:
            db.close()
    try:
        result = _read_snapshot(db, read)
        trusted = not _writer_appeared(db, p)
    except sqlite3.DatabaseError:
        trusted = False
    finally:
        db.close()
    if trusted:
        return result
    db = open_db_readonly(p, immutable=False)
    try:
        return _read_snapshot(db, read)
    finally:
        db.close()
