"""The only module that touches SQL. Schema lives in versioned migrations/NNNN_*.sql."""
import json
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
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


class Db:
    def __init__(self, conn: sqlite3.Connection, *, immutable: bool = False):
        self.conn = conn
        self.immutable = immutable  # opened read-only with sqlite immutable=1 (no writer seen)

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
        first. A verified run that wrote no observations is the identical-payload
        short-circuit (pipeline Ruling D); pinned_bundle marks a run whose passing
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

    # --- reviewed withdrawal and orphan runs (Task 20) -----------------------------------------

    def withdraw_run(self, run_id: int, reason: str, at: str) -> list[int]:
        """Withdraw ONE verified fetched vintage: its rows stay in `observation` but are never
        served again ('withdrawn' is terminal). The operator's reason is recorded as
        event(withdrawal) in the same transaction; migration 0011's triggers refuse every
        other way into 'withdrawn'.

        The identical-payload short-circuit (pipeline Ruling D) vouches for the run it matched
        without holding rows, and the next identical fetch would match the short-circuit
        again. So, in the same transaction, every LATER run of the same dataset_key that is a
        verified short-circuit chained onto this one (the unbroken sequence of verified runs
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
                    f"run {run_id} has no observations (an identical-payload short-circuit "
                    f"that holds no rows); withdraw the run that wrote the rows - its "
                    f"short-circuits are withdrawn with it")
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

    def close(self) -> None:
        self.conn.close()


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


def open_db_readonly(path: str | Path, *, immutable: bool | None = None) -> Db:
    """Open an EXISTING database strictly read-only for reports (status, lag): sqlite URI
    `mode=ro`, `query_only`, no migration, no journal-mode change, never a new file.

    Refuses (ReadOnlyOpenError) a missing file and a schema whose applied migrations differ
    from this code's: older means the writer (scheduler) has not migrated it yet, newer means
    this code is older than the database. Neither is ever "fixed" from here.

    A WAL database with no -wal file has no open writer; it is then opened `immutable=1`
    (unless `immutable=False`), because a plain read-only WAL open would create -wal/-shm
    files that a read-only handle cannot remove. With a writer running (the -wal file exists)
    the normal `mode=ro` open reads its committed state. The -wal test is not atomic: a
    writer that starts meanwhile (a scheduler restart migrating, a manual CLI write) can make
    an immutable read fail with sqlite3.DatabaseError; the schema read here then retries once
    with plain `mode=ro`, and `read_db_readonly` does the same for the whole report."""
    p = Path(path)
    if not p.is_file():
        raise ReadOnlyOpenError(f"database not found: {p} (read-only reports never create one;"
                                " check --db / PRUMO_DB_PATH)")
    if immutable is None:
        immutable = not Path(str(p) + "-wal").exists()
    uri = p.resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    conn = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=BUSY_TIMEOUT_S)
    try:
        conn.execute("PRAGMA query_only=ON")
        try:
            applied = {r[0] for r in conn.execute("SELECT version FROM schema_migration")}
        except sqlite3.DatabaseError as e:
            if immutable:  # possibly a concurrent writer: one plain read-only retry
                conn.close()
                return open_db_readonly(p, immutable=False)
            raise ReadOnlyOpenError(f"{p}: no schema_migration table, not a Prumo database "
                                    f"({e})") from None
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
    return Db(conn, immutable=immutable)


def read_db_readonly(path: str | Path, read: Callable[[Db], T]) -> T:
    """`read(db)` on a read-only handle (open_db_readonly), closed afterwards. When the handle
    was opened `immutable=1` and the read fails with sqlite3.DatabaseError (a writer started
    or migrated during the read: SQLite documents wrong results or SQLITE_CORRUPT for an
    immutable reader then), the whole read is retried ONCE with plain `mode=ro`, which sees
    the writer's committed state. Any other failure propagates."""
    db = open_db_readonly(path)
    try:
        return read(db)
    except sqlite3.DatabaseError:
        if not db.immutable:
            raise
    finally:
        db.close()
    db = open_db_readonly(path, immutable=False)
    try:
        return read(db)
    finally:
        db.close()
