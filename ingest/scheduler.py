"""Serial, restart-safe base-data scheduler: python -m ingest.scheduler [--once].

Only scheduler-owned, live attempts drive cadence; old dataset_run rows (especially legacy
synthetic runs) never seed freshness. Commit an in-flight failure marker before the runner,
then reset the streak only on 'verified'. Failed/interrupted attempts retry after 1h, 4h,
then 12h; a completed failure waits from completion, an interrupted one from its start.

The CLI holds an advisory file lock for its whole lifetime. Embedded tick/serve callers must
provide equivalent exclusive ownership. There is a 15-minute pause AFTER each serial pass,
so slow sources delay later groups and the next pass. No catch-up windows, push alerts,
health server, whole-pass deadline or automatic data/licence changes are implemented here.
"""
import argparse
import fcntl
import json
import os
import signal
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from ingest import operations
from ingest.cadence import BACKOFF, group_interval, next_eligible_at, series_interval
from ingest.db import Db, SchedulerState, open_db
from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.operations import DatasetGroup, GroupOutcome, RunRequest
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry

TICK = timedelta(minutes=15)
__all__ = ["BACKOFF", "TICK", "due", "main", "serve", "tick"]  # BACKOFF lives in ingest.cadence
DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "registry" / "core.yaml"

Clock = Callable[[], datetime]
Log = Callable[[dict], None]
HttpFor = Callable[[str], Http]


class GroupRunner(Protocol):
    def __call__(self, db: Db, store: RawStore, group: DatasetGroup, *,
                 http_for: Callable[[], Http], request: RunRequest,
                 now: Clock) -> list[GroupOutcome]: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    # Legacy DB timestamps use naive UTC, never the host's local timezone.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def due(spec_group: DatasetGroup, last_success: datetime | None, now: datetime) -> bool:
    """Healthy refresh cadence of one authoritative group; inclusive interval boundary."""
    interval = group_interval(spec_group.specs)  # validate even a never-run group
    return last_success is None or _utc(now) >= _utc(last_success) + interval


def _plan(specs: list[SeriesSpec]) -> tuple[list[DatasetGroup], list[str]]:
    """Validate all schedules/group identities before any group can open an HTTP client."""
    by_source: dict[str, list[SeriesSpec]] = {}
    for spec in specs:
        series_interval(spec)
        by_source.setdefault(spec.source.name, []).append(spec)
    groups: list[DatasetGroup] = []
    blocked: list[str] = []
    for name, source_specs in sorted(by_source.items()):
        if not source_specs[0].source.verifiable:
            blocked.append(name)  # DGEG stays visible even with no active series
            continue
        active = [spec for spec in source_specs if spec.active]
        if active:
            groups.extend(operations.group_specs(active))
    return groups, blocked


def _ready(group: DatasetGroup, state: SchedulerState | None, now: datetime) -> bool:
    if state is None:
        return due(group, None, now)
    eligible = next_eligible_at(group_interval(group.specs), failure_streak=state.failure_streak,
                                last_attempt_at=state.last_attempt_at,
                                last_finished_at=state.last_finished_at,
                                last_success_at=state.last_success_at)
    return eligible is None or _utc(now) >= eligible


def _run_group(db: Db, store: RawStore, group: DatasetGroup, *,
               http_for: Callable[[], Http], request: RunRequest,
               now: Clock) -> list[GroupOutcome]:
    # Exactly ONE full group, never all of a source when only one sibling is due.
    return operations.run_source(db, store, group.specs[0].source.name, list(group.specs),
                                 http_for=http_for, request=request, now=now)


def _polite_clients(specs: list[SeriesSpec]) -> HttpFor:
    """One lazy client per source, retaining its throttle across indicator groups/passes."""
    clients: dict[str, Http] = {}

    def get(name: str) -> Http:
        if name not in clients:
            clients[name] = operations.polite_http(specs, name)
        return clients[name]

    return get


def _stdout(record: dict) -> None:
    print(json.dumps(record, sort_keys=True), flush=True)


def _record(at: datetime, event: str, outcome: GroupOutcome, group: str) -> dict:
    return {"schema": "prumo-scheduler", "version": 1, "ts": _utc(at).isoformat(),
            "event": event, "source": outcome.source, "group": group,
            "state": outcome.state, "run_id": outcome.run_id,
            "n_written": outcome.n_written, "n_quarantined": outcome.n_quarantined,
            "detail": outcome.detail}


def tick(db: Db, store: RawStore, specs: list[SeriesSpec], *, now: Clock = _utc_now,
         runner: GroupRunner = _run_group, log: Log = _stdout,
         http_for: HttpFor | None = None) -> list[dict]:
    """One pass. Source failures are isolated; persistence/logging failures remain fatal.

    Returned records are the same records sent to log: one per attempted group. Blocked
    sources are reported once per process start by main() (report_blocked), not per pass.
    There are no synthetic success heartbeats.
    """
    groups = _plan(specs)[0]
    http_for = http_for if http_for is not None else _polite_clients(specs)
    records: list[dict] = []

    def emit(record: dict) -> None:
        records.append(record)
        log(record)

    for group in groups:
        key, name = group.key(), group.specs[0].source.name
        started = _utc(now())
        if not _ready(group, db.scheduler_state(key), started):
            continue
        # An autocommitted, pessimistic failure also covers process death in the runner.
        db.scheduler_attempt_started(key, name, group.label, started.isoformat())
        try:
            outcomes = runner(db, store, group, http_for=lambda: http_for(name),
                              request=RunRequest(), now=lambda: _utc(now()))
            if len(outcomes) != 1 or outcomes[0].source != name:
                raise ValueError("group runner must return exactly one outcome for its source")
            outcome = outcomes[0]
            # Source setup failures use the source name; all real runs use the group label.
            if outcome.group != group.label and not (
                    outcome.state == "blocked" and outcome.group == name):
                raise ValueError("group runner returned an outcome for a different group")
        except Exception as exc:
            outcome = GroupOutcome(name, group.label, "error",
                                   detail=f"{type(exc).__name__}: {exc}")
        finished = _utc(now())
        db.scheduler_attempt_finished(key, outcome.state, finished.isoformat())
        emit(_record(finished, "attempt", outcome, group.label))
    return records


def report_blocked(specs: list[SeriesSpec], *, now: Clock = _utc_now,
                   log: Log = _stdout) -> list[dict]:
    """One 'blocked' log record per registry source marked 'verifiable: false' (DGEG). Called
    once per process start: the state comes from the registry, so repeating it every pass
    would only be log noise (D-M1). Log only; nothing is written to the database."""
    records = []
    for name in _plan(specs)[1]:
        outcome = GroupOutcome(name, name, "blocked", exit_relevant=False,
                               detail="registry marks the source 'verifiable: false'; "
                                      "not fetched or served")
        records.append(_record(now(), "blocked", outcome, name))
        log(records[-1])
    return records


def serve(db: Db, store: RawStore, specs: list[SeriesSpec], *, now: Clock = _utc_now,
          sleep: Callable[[float], None] = time.sleep, runner: GroupRunner = _run_group,
          log: Log = _stdout, http_for: HttpFor | None = None,
          max_ticks: int | None = None) -> None:
    """Serial passes with an injectable wait; max_ticks is an offline test seam only."""
    if max_ticks is not None and max_ticks < 1:
        raise ValueError("max_ticks must be positive or None")
    http_for = http_for if http_for is not None else _polite_clients(specs)
    count = 0
    while True:
        tick(db, store, specs, now=now, runner=runner, log=log, http_for=http_for)
        count += 1
        if max_ticks is not None and count >= max_ticks:
            return
        sleep(TICK.total_seconds())


@contextmanager
def _instance_lock(db_path: Path) -> Iterator[None]:
    # Canonical DB path makes relative paths/symlinks share a lock. Never unlink the file:
    # replacing its inode could let a new process lock a different file while we still run.
    path = Path(str(db_path) + ".scheduler.lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"scheduler already running for {db_path}") from None
        yield
    finally:
        os.close(fd)


def main(argv: list[str] | None = None, *, now: Clock = _utc_now,
         sleep: Callable[[float], None] = time.sleep, runner: GroupRunner = _run_group,
         log: Log = _stdout, http_for: HttpFor | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.scheduler",
        description="Serial base-data refresh scheduler; 15-minute pause between passes.")
    parser.add_argument("--once", action="store_true", help="one pass, then exit (1 on an attempt failure)")
    parser.add_argument("--db", default=os.environ.get("PRUMO_DB_PATH", "/data/prumo.sqlite3"),
                        help="SQLite database (default: $PRUMO_DB_PATH or /data/prumo.sqlite3)")
    parser.add_argument("--raw-dir", default=os.environ.get("PRUMO_RAW_DIR", "/data/raw"),
                        help="raw evidence store (default: $PRUMO_RAW_DIR or /data/raw)")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY,
                        help="registry YAML (default: packaged registry/core.yaml)")
    args = parser.parse_args(argv)  # help exits before registry/files/clients/credentials
    specs = load_registry(args.registry)
    _plan(specs)  # also fail on schedule/grouping errors before DB, lock or network
    db_path = Path(args.db).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    previous_sigterm = signal.signal(signal.SIGTERM, _on_sigterm)
    try:
        with _instance_lock(db_path):
            return _locked_main(args, db_path, specs, now=now, sleep=sleep, runner=runner,
                                log=log, http_for=http_for)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)


def _on_sigterm(signum, _frame):
    """`docker stop` sends SIGTERM: raise SystemExit so finally paths run (an in-flight
    dataset run is closed as failed-operational, the DB is closed) instead of dying mid-run."""
    raise SystemExit(128 + signum)


def _locked_main(args, db_path: Path, specs, *, now: Clock, sleep, runner, log, http_for) -> int:
    db = open_db(db_path)
    try:
        # Under the instance lock no other scheduler is mid-run: any 'running' run was left by
        # a killed process (OOM, SIGKILL) and is closed honestly before new work starts.
        db.close_orphan_runs(now().astimezone(timezone.utc).isoformat())
        sync_registry(db, specs)
        report_blocked(specs, now=now, log=log)
        store = RawStore(Path(args.raw_dir))
        if args.once:
            records = tick(db, store, specs, now=now, runner=runner, log=log,
                           http_for=http_for)
            return int(any(r["event"] == "attempt" and r["state"] != "verified"
                           for r in records))
        serve(db, store, specs, now=now, sleep=sleep, runner=runner, log=log,
              http_for=http_for)
    except KeyboardInterrupt:
        return 130
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
