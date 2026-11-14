"""Task 18A scheduler tests: due/backoff cadence over its OWN persisted attempt history,
registry parsing before any network, single-instance lock, per-group isolation and honesty
(a legacy synthetic run is never a fresh success; a killed in-flight attempt still backs
off). No HTTP anywhere: runners/http are injected seams. Scratch DBs only (tmp_path).
"""
import fcntl
import json
import os
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.models import SeriesSpec, SourceSpec
from ingest.operations import DatasetGroup, GroupOutcome, group_specs
from ingest.rawstore import RawStore
from ingest.scheduler import BACKOFF, TICK, due, main, serve, tick

T0 = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)

WB = SourceSpec(name="worldbank", licence="CC BY 4.0", licence_url="http://l",
                attribution="WB", redistribution_ok=True, verifiable=True)
DGEG = SourceSpec(name="dgeg", licence="UNVERIFIED", licence_url="http://l",
                  attribution="DGEG", redistribution_ok=False, verifiable=False)


def _wb(sid: str, code: str, active: bool = True, schedule: str | None = None,
        frequency: str = "A") -> SeriesSpec:
    return SeriesSpec(id=sid, source=WB, indicator_key=f"{code}.{sid}", role="primary",
                      theme="economy", geography="PT", frequency=frequency, unit="u",
                      native_code=f"{code}:PRT", active=active, schedule=schedule)


def _dgeg(sid: str, active: bool = False) -> SeriesSpec:
    return SeriesSpec(id=sid, source=DGEG, indicator_key=f"k_{sid}", role="primary",
                      theme="energy", geography="PT", frequency="M", unit="u",
                      native_code=sid, active=active)


def _group(*specs: SeriesSpec) -> DatasetGroup:
    """The ONE group the authoritative grouping policy builds from these specs."""
    groups = group_specs(list(specs))
    assert len(groups) == 1
    return groups[0]


@pytest.fixture
def db(tmp_path):
    d = open_db(tmp_path / "prumo.db")
    yield d
    d.close()


@pytest.fixture
def store(tmp_path):
    return RawStore(tmp_path / "raw")


def _runner(outcomes: Mapping[str, object], calls: list):
    """Fake per-group runner. outcomes maps group label -> GroupOutcome or Exception."""
    def run(db, store, group, *, http_for, request, now):
        calls.append((group.specs[0].source.name, group.label, now(),
                      tuple(s.id for s in group.specs)))
        r = outcomes.get(group.label, GroupOutcome(group.specs[0].source.name, group.label,
                                                   "verified", run_id=1))
        if isinstance(r, Exception):
            raise r
        return [r]
    return run


def _clock(start: datetime):
    box = [start]
    return box, lambda: box[0]


def _sched(d, key) -> dict:
    """Readable view of one scheduler_state row (tuple order is an ingest.db detail)."""
    r = d.scheduler_state(key)
    assert r is not None
    return {"attempt_at": r[3], "attempt_state": r[4], "success_at": r[5], "streak": r[6]}


# --- due(): the healthy-cadence rule -------------------------------------------------------------


def test_due_when_never_run():
    g = _group(_wb("wb.gdp.PT", "NY.GDP.MKTP.KD"))
    assert due(g, None, T0) is True


def test_not_due_before_release_window():
    """Registry schedule ('12h') wins over the frequency default (A=30d); inside the interval
    the group is NOT due, at/after it it is. A mixed group takes the most frequent member."""
    daily = _group(_wb("wb.d.PT", "X.D", frequency="D"))  # default D = 1d
    assert due(daily, T0, T0 + timedelta(hours=23)) is False
    assert due(daily, T0, T0 + timedelta(days=1)) is True

    s12 = _group(_wb("wb.h.PT", "X.H", schedule="12h"))
    assert due(s12, T0, T0 + timedelta(hours=11)) is False
    assert due(s12, T0, T0 + timedelta(hours=12)) is True

    mixed = _group(_wb("wb.m1.PT", "X.M", schedule="7d"),
                   _wb("wb.m2.PT", "X.M", schedule="1d"))
    assert due(mixed, T0, T0 + timedelta(hours=23)) is False   # min member = 1d
    assert due(mixed, T0, T0 + timedelta(days=1)) is True
    assert due(mixed, T0, T0 + timedelta(days=6, hours=23)) is True  # min, not max


def test_due_timezone_handling():
    """Naive datetimes are read as UTC (the repo-wide DB convention); aware equivalents in
    other offsets compare by instant."""
    g = _group(_wb("wb.tz.PT", "X.TZ", schedule="1d"))
    naive_success = datetime(2026, 11, 13, 12, 0)              # read as 12:00 UTC
    aware_now = datetime(2026, 11, 14, 12, 30, tzinfo=timezone.utc)
    assert due(g, naive_success, aware_now) is True
    assert due(g, naive_success, datetime(2026, 11, 14, 11, 30)) is False  # both naive
    lisbon = timezone(timedelta(hours=0), "WET")               # WET = UTC in November
    assert due(g, naive_success, datetime(2026, 11, 14, 12, 30, tzinfo=lisbon)) is True
    plus2 = timezone(timedelta(hours=2))
    # 15:00 at +02:00 == 13:00 UTC == after 12:00 UTC + 1d + 1h
    assert due(g, naive_success, datetime(2026, 11, 14, 15, 1, tzinfo=plus2)) is True
    assert due(g, naive_success, datetime(2026, 11, 14, 13, 29, tzinfo=plus2)) is False


def test_unparseable_schedule_fails_loudly_not_silently():
    g = _group(_wb("wb.bad.PT", "X.BAD", schedule="fortnightly"))
    with pytest.raises(ValueError, match="unparseable schedule"):
        due(g, T0, T0 + timedelta(days=30))


# --- persisted backoff / restart durability ------------------------------------------------------


def test_failed_run_retries_with_backoff(tmp_path):
    """Failures retry at +1h, +4h, then a 12h cap; success resets to the healthy cadence.
    The DB is closed and reopened mid-scenario: the schedule survives a restart."""
    spec = _wb("wb.bo.PT", "X.BO", schedule="1d")
    specs = [spec]
    group = _group(spec)
    path = tmp_path / "s.db"
    calls: list = []

    def tick_at(db, store, now):
        return tick(db, store, specs, now=lambda: now,
                    runner=_runner({"X.BO": GroupOutcome("worldbank", "X.BO",
                                                         "failed-verification", run_id=7)},
                                   calls),
                    log=lambda r: None)

    d = open_db(path)
    s = RawStore(tmp_path / "raw")
    tick_at(d, s, T0)                                  # attempt 1 fails
    st = _sched(d, group.key())
    assert st["streak"] == 1 and st["success_at"] is None     # no success minted by a failure
    tick_at(d, s, T0 + timedelta(minutes=59))
    assert len(calls) == 1                             # not yet: backoff 1h
    tick_at(d, s, T0 + timedelta(hours=1))             # attempt 2 fails -> streak 2
    assert len(calls) == 2
    assert _sched(d, group.key())["streak"] == 2

    d.close()                                          # restart: state must survive
    d = open_db(path)
    assert _sched(d, group.key())["streak"] == 2
    tick_at(d, s, T0 + timedelta(hours=4, minutes=59))
    assert len(calls) == 2                             # 4h backoff from the +1h attempt
    tick_at(d, s, T0 + timedelta(hours=5))             # attempt 3 fails -> streak 3
    assert len(calls) == 3

    tick_at(d, s, T0 + timedelta(hours=16, minutes=59))
    assert len(calls) == 3                             # 12h cap from the +5h attempt
    tick_at(d, s, T0 + timedelta(hours=17))            # attempt 4 fails -> streak 4
    assert len(calls) == 4
    assert _sched(d, group.key())["streak"] == 4
    assert BACKOFF == (timedelta(hours=1), timedelta(hours=4), timedelta(hours=12))
    tick_at(d, s, T0 + timedelta(hours=28, minutes=59))
    assert len(calls) == 4                             # streak 4 is still capped at 12h

    good = _runner({"X.BO": GroupOutcome("worldbank", "X.BO", "verified", run_id=8)}, calls)
    tick(d, s, specs, now=lambda: T0 + timedelta(hours=29), runner=good, log=lambda r: None)
    st = _sched(d, group.key())
    assert st["streak"] == 0 and st["success_at"] is not None  # success: reset + kept
    tick(d, s, specs, now=lambda: T0 + timedelta(hours=29 + 12), runner=good,
         log=lambda r: None)
    assert len(calls) == 5                             # cadence (1d), not backoff, governs now
    tick(d, s, specs, now=lambda: T0 + timedelta(hours=29 + 24), runner=good,
         log=lambda r: None)
    assert len(calls) == 6
    assert [c[2] for c in calls] == [T0, T0 + timedelta(hours=1), T0 + timedelta(hours=5),
                                     T0 + timedelta(hours=17), T0 + timedelta(hours=29),
                                     T0 + timedelta(hours=53)]
    d.close()


def test_legacy_synthetic_run_never_counts_as_success(db, store):
    """A DB holding only a legacy synthetic 'verified' run + legacy rows must NOT make the
    group fresh: scheduler state is explicit, and legacy runs never seed a success."""
    from ingest.models import Observation
    spec = _wb("wb.leg.PT", "X.LEG")
    key = _group(spec).key()
    db.upsert_source_and_series([WB.model_dump()],
                                [{**spec.model_dump(exclude={"source", "schedule",
                                                             "throttle_rps"}),
                                  "source_name": "worldbank"}])
    run = db.legacy_run("worldbank", "legacy:worldbank", "2026-04-06T00:00:00+00:00")
    db.write_legacy_observations(run, [(Observation.from_raw(spec.id, "2025", "1.5"),
                                        "2026-04-06T00:00:00+00:00")])
    calls: list = []
    tick(db, store, [spec], now=lambda: T0, runner=_runner({}, calls), log=lambda r: None)
    assert [c[1] for c in calls] == ["X.LEG"]          # attempted: legacy hid nothing
    assert _sched(db, key)["success_at"] is not None   # now a REAL success is on record
    assert db.scheduler_state("legacy:worldbank") is None  # and the synthetic run got none


def test_restart_after_killed_inflight_attempt_backs_off(tmp_path):
    """The anti-hammer marker is written BEFORE any network: an attempt killed mid-flight
    (state row written, never finished) still backs the group off for 1h after a restart."""
    spec = _wb("wb.kill.PT", "X.KILL")
    group = _group(spec)
    path = tmp_path / "k.db"
    d = open_db(path)
    d.scheduler_attempt_started(group.key(), "worldbank", "X.KILL",
                                T0.isoformat())        # exactly what tick writes pre-network
    d.close()                                          # <- kill -9 before the runner returned

    d = open_db(path)
    st = d.scheduler_state(group.key())
    assert st is not None and st[6] == 1 and st[5] is None and st[3] == T0.isoformat()
    calls: list = []
    s = RawStore(tmp_path / "raw")
    tick(d, s, [spec], now=lambda: T0 + timedelta(minutes=30), runner=_runner({}, calls),
         log=lambda r: None)
    assert calls == []                                 # killed attempt still holds +1h
    tick(d, s, [spec], now=lambda: T0 + timedelta(hours=1), runner=_runner({}, calls),
         log=lambda r: None)
    assert len(calls) == 1                             # retry happens once backoff elapsed
    d.close()


def test_healthy_group_not_rerun_after_sibling_failure(db, store):
    """World Bank schedules per INDICATOR: a healthy sibling group keeps its own cadence and
    is never rerun early because another group failed."""
    a = _wb("wb.gdp.PT", "NY.GDP.A")
    b = _wb("wb.uem.PT", "SL.UEM.B")
    specs = [a, b]
    ga, gb = group_specs([a, b])[0], group_specs([a, b])[1]
    assert ga.label != gb.label
    outcomes = {ga.label: GroupOutcome("worldbank", ga.label, "verified", run_id=1),
                gb.label: GroupOutcome("worldbank", gb.label, "failed-verification", run_id=2)}
    calls: list = []
    tick(db, store, specs, now=lambda: T0, runner=_runner(outcomes, calls),
         log=lambda r: None)
    assert sorted(c[1] for c in calls) == [ga.label, gb.label]
    calls.clear()
    tick(db, store, specs, now=lambda: T0 + timedelta(hours=2), runner=_runner(outcomes, calls),
         log=lambda r: None)
    assert [c[1] for c in calls] == [gb.label]         # only the failed group retries
    assert _sched(db, ga.key())["streak"] == 0         # sibling's success untouched
    assert _sched(db, gb.key())["streak"] == 2


def test_scheduler_survives_source_exception(db, store):
    """One runner raising (a source-level operational bug) is logged as an 'error' line,
    recorded as a failed attempt that backs the group off, and never stops other groups."""
    a = _wb("wb.ok.PT", "X.OK")
    b = _wb("wb.bad.PT", "X.ERR")
    c = _wb("wb.alsook.PT", "X.OK2")
    group_b = _group(b)
    lines: list = []
    calls: list = []
    runner = _runner({"X.ERR": RuntimeError("boom")}, calls)
    tick(db, store, [a, b, c], now=lambda: T0, runner=runner, log=lines.append)
    assert [c[1] for c in calls] == ["X.ERR", "X.OK", "X.OK2"]  # all three still attempted
    err = [line for line in lines if line["group"] == "X.ERR"]
    assert len(err) == 1 and err[0]["state"] == "error" and "boom" in err[0]["detail"]
    assert _sched(db, group_b.key())["streak"] == 1    # poisoned group backs off...
    calls.clear()
    tick(db, store, [a, b, c], now=lambda: T0 + timedelta(minutes=30), runner=runner,
         log=lambda r: None)
    assert calls == []                                 # ...and healthy ones are on cadence
    d0 = _sched(db, _group(a).key())
    assert d0["streak"] == 0 and d0["success_at"] is not None  # healthy success kept


# --- loop, logging, blocked sources ---------------------------------------------------------------


def test_loop_ticks_every_15_minutes(db, store):
    spec = _wb("wb.loop.PT", "X.LOOP", schedule="1d")
    box, now = _clock(T0)
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        box[0] += timedelta(seconds=seconds)

    calls: list = []
    serve(db, store, [spec], now=now, sleep=fake_sleep, runner=_runner({}, calls),
          log=lambda r: None, max_ticks=3)
    assert sleeps == [900.0, 900.0] and TICK == timedelta(minutes=15)
    assert len(calls) == 1                             # 1d cadence: ticks 2/3 not due
    assert box[0] == T0 + timedelta(minutes=30)


def test_tick_emits_only_attempts_and_inactive_never_scheduled(db, store, capsys):
    """tick() never repeats the DGEG (verifiable: false) blocked notice: that is reported once
    per process start by main() (D-M1). Inactive series of other sources are never scheduled.
    Default log target is one JSON line per stdout."""
    live = _wb("wb.act.PT", "X.ACT")
    dead = _wb("wb.dead.PT", "X.DEA", active=False)
    specs = [_dgeg("dgeg.a", active=False), _dgeg("dgeg.b", active=False), live, dead]
    calls: list = []
    tick(db, store, specs, now=lambda: T0, runner=_runner({}, calls))
    out = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert [line["event"] for line in out] == ["attempt"]
    assert [line["source"] for line in out] == ["worldbank"]
    assert all(line["schema"] == "prumo-scheduler" and line["version"] == 1 and line["ts"]
               for line in out)
    assert [c[1] for c in calls] == ["X.ACT"]          # native indicator label, not source
    assert calls[0][3] == ("wb.act.PT",)               # only active series reached the runner
    again = tick(db, store, specs, now=lambda: T0 + timedelta(minutes=15),
                 runner=_runner({}, calls))
    assert again == []                                 # nothing due, and no blocked repeat


def _registry_with_blocked_dgeg(tmp_path: Path) -> Path:
    p = _tiny_registry(tmp_path)
    p.write_text(p.read_text().replace(
        "series:\n",
        "  dgeg:\n"
        "    licence: UNVERIFIED\n"
        "    licence_url: https://example.org/d\n"
        "    attribution: DGEG\n"
        "    redistribution_ok: false\n"
        "    verifiable: false\n"
        "series:\n"
        "  - id: dgeg.a\n"
        "    source: dgeg\n"
        "    indicator_key: diesel\n"
        "    role: primary\n"
        "    theme: energy\n"
        "    geography: PT\n"
        "    frequency: M\n"
        "    unit: u\n"
        "    native_code: 'dgeg.a'\n"
        "    active: false\n", 1))
    return p


def test_blocked_source_reported_once_per_process_start_not_per_pass(tmp_path):
    """serve mode: three passes, ONE blocked record (from main, before the first pass)."""
    reg = _registry_with_blocked_dgeg(tmp_path)
    records: list = []
    sleeps: list = []

    def stop_after_three(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 3:
            raise KeyboardInterrupt

    box, now = _clock(T0)
    assert main(["--db", str(tmp_path / "s.db"), "--raw-dir", str(tmp_path / "raw"),
                 "--registry", str(reg)], now=now, sleep=stop_after_three,
                runner=_runner({}, []), log=records.append) == 130
    blocked = [r for r in records if r["event"] == "blocked"]
    assert [(r["source"], r["state"]) for r in blocked] == [("dgeg", "blocked")]
    assert "verifiable: false" in blocked[0]["detail"]
    assert records[0]["event"] == "blocked"            # reported at start, before attempts
    assert [r["event"] for r in records[1:]] == ["attempt"]  # 1d cadence: one attempt only


def test_failed_group_json_line_is_honest(db, store):
    spec = _wb("wb.fail.PT", "X.FAIL")
    lines: list = []
    out = GroupOutcome("worldbank", "X.FAIL", "failed-verification", run_id=42,
                       n_written=10, n_quarantined=1)
    tick(db, store, [spec], now=lambda: T0, runner=_runner({"X.FAIL": out}, []),
         log=lines.append)
    assert lines == [{"schema": "prumo-scheduler", "version": 1,
                      "ts": T0.isoformat(), "event": "attempt", "source": "worldbank",
                      "group": "X.FAIL", "state": "failed-verification", "run_id": 42,
                      "n_written": 10, "n_quarantined": 1, "detail": None}]


# --- main(): parsing order, lock, wiring ----------------------------------------------------------


def _tiny_registry(tmp_path: Path) -> Path:
    p = tmp_path / "core.yaml"
    p.write_text(
        "sources:\n"
        "  worldbank:\n"
        "    licence: CC BY 4.0\n"
        "    licence_url: https://example.org/l\n"
        "    attribution: WB\n"
        "    redistribution_ok: true\n"
        "series:\n"
        "  - id: wb.one.PT\n"
        "    source: worldbank\n"
        "    indicator_key: gdp\n"
        "    role: primary\n"
        "    theme: economy\n"
        "    geography: PT\n"
        "    frequency: M\n"
        "    unit: u\n"
        "    native_code: 'X.ONE:PRT'\n")
    return p


def test_registry_failure_before_any_db_or_network(tmp_path):
    """A broken registry must abort BEFORE the DB is opened or any Http client exists."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("series:\n- id: x\n  source: ghost\n  indicator_key: k\n  role: primary\n"
                   "  theme: economy\n  geography: PT\n  frequency: M\n  unit: u\n")
    dbp = tmp_path / "none.db"
    with pytest.raises(ValueError, match="unknown source"):
        main(["--once", "--db", str(dbp), "--raw-dir", str(tmp_path / "raw"),
              "--registry", str(bad)])
    assert not dbp.exists()                            # open_db never ran
    assert not (tmp_path / "raw").exists()             # RawStore never built


def test_help_exits_zero_without_touching_anything(tmp_path, capsys):
    dbp = tmp_path / "h.db"
    with pytest.raises(SystemExit) as e:
        main(["--help", "--db", str(dbp)])
    assert e.value.code == 0
    assert "--once" in capsys.readouterr().out
    assert not dbp.exists()


def test_lock_collision_refuses_second_instance(tmp_path):
    reg = _tiny_registry(tmp_path)
    dbp = tmp_path / "l.db"
    open_db(dbp).close()
    lock = Path(str(dbp) + ".scheduler.lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(SystemExit) as e:
            main(["--once", "--db", str(dbp), "--raw-dir", str(tmp_path / "raw"),
                  "--registry", str(reg)])
        assert e.value.code != 0
    finally:
        os.close(fd)
    # and once the holder exits, the lock is acquirable again
    calls: list = []
    assert main(["--once", "--db", str(dbp), "--raw-dir", str(tmp_path / "raw"),
                 "--registry", str(reg)], runner=_runner({}, calls),
                log=lambda r: None) == 0


def test_main_once_end_to_end_persists_state(tmp_path, capsys):
    """--once wiring: registry -> db (+sync) -> one tick -> success persisted -> not due."""
    reg = _tiny_registry(tmp_path)
    dbp = tmp_path / "m.db"
    calls: list = []
    rc = main(["--once", "--db", str(dbp), "--raw-dir", str(tmp_path / "raw"),
               "--registry", str(reg)], now=lambda: T0, runner=_runner({}, calls))
    assert rc == 0
    assert len(calls) == 1
    out = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert [line["state"] for line in out] == ["verified"] and out[0]["group"] == "X.ONE"
    d = open_db(dbp)
    assert d.conn.execute("SELECT COUNT(*) FROM source WHERE name='worldbank'"
                          ).fetchone()[0] == 1     # registry was synced
    calls.clear()
    rc = main(["--once", "--db", str(dbp), "--raw-dir", str(tmp_path / "raw"),
               "--registry", str(reg)], now=lambda: T0 + timedelta(minutes=15),
               runner=_runner({}, calls), log=lambda r: None)
    assert rc == 0 and calls == []                   # success persisted across processes
    d.close()


# --- migration 0010 --------------------------------------------------------------------------


def test_0010_fresh_db_scheduler_state_is_strict(db):
    assert any(v.startswith("0010") for (v,) in
               db.conn.execute("SELECT version FROM schema_migration").fetchall())
    db.conn.execute("INSERT INTO scheduler_state(dataset_key, source_name, group_label,"
                    " last_attempt_at, last_attempt_state, last_success_at, failure_streak)"
                    " VALUES ('k','s','g','t','running',NULL,0)")
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        db.conn.execute("INSERT INTO scheduler_state(dataset_key, source_name, group_label,"
                        " last_attempt_at, last_attempt_state, failure_streak)"
                        " VALUES ('k2','s','g','t','running',-1)")
    with pytest.raises(sqlite3.IntegrityError, match="INTEGER"):
        db.conn.execute("INSERT INTO scheduler_state(dataset_key, source_name, group_label,"
                        " last_attempt_at, last_attempt_state, failure_streak)"
                        " VALUES ('k3','s','g','t','running','x')")
    # SQLite STRICT permits lossless integer-to-TEXT coercion; a BLOB must be rejected.
    with pytest.raises(sqlite3.IntegrityError, match="TEXT"):
        db.conn.execute("INSERT INTO scheduler_state(dataset_key, source_name, group_label,"
                        " last_attempt_at, last_attempt_state, failure_streak)"
                        " VALUES ('k4',x'33','g','t','running',0)")


def _migrations_up_to_0009(tmp_path):
    mig = tmp_path / "mig9"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem < "0010":
            (mig / f.name).write_bytes(f.read_bytes())
    return mig


def test_0010_upgrades_populated_0009_and_preserves_everything(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _migrations_up_to_0009(tmp_path))
    p = tmp_path / "old.db"
    d = open_db(p)
    assert not [v for (v,) in d.conn.execute("SELECT version FROM schema_migration")
                if v.startswith("0010")]
    with pytest.raises(sqlite3.OperationalError):      # table does not exist yet
        d.conn.execute("SELECT * FROM scheduler_state").fetchall()
    d.conn.execute("INSERT INTO source(id,name,licence,licence_url,attribution,"
                   "redistribution_ok) VALUES (1,'ine','CC-BY','http://l','INE',1)")
    d.conn.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,"
                   "frequency,unit,active) VALUES ('ine.gdp.PT',1,'gdp','primary','economy',"
                   "'PT','A','EUR',1)")
    rid = d.conn.execute("INSERT INTO dataset_run(source_id,started_at,finished_at,state,"
                         "dataset_key) VALUES (1,'2026-01-01','2026-01-01','verified','k1')"
                         ).lastrowid
    d.close()

    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)  # real set incl. 0010
    d = open_db(p)
    assert any(v.startswith("0010") for (v,) in
               d.conn.execute("SELECT version FROM schema_migration"))
    assert d.conn.execute("SELECT id, state FROM dataset_run").fetchall() == [(rid, "verified")]
    d.scheduler_attempt_started("k1", "ine", "ine", T0.isoformat())
    assert d.scheduler_state("k1")[6] == 1
    # foreign keys still enforced on the migrated database
    assert d.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        d.conn.execute("INSERT INTO observation(series_id,period,value_text,value,kind,"
                       "dataset_run_id,raw_fetch_id,fetched_at) VALUES ('ghost','2025','1',1,"
                       "'legacy-unverified',1,NULL,'t')")
    d.close()
    d = open_db(p)                                     # repeated open idempotent
    assert d.scheduler_state("k1")[6] == 1
    d.close()


def test_0010_migration_rolls_back_atomically(tmp_path, monkeypatch):
    """A broken 0010 (here: an FK-violating statement appended to a copy) must roll back
    WITH its schema_migration record - no corrupt applied version, reopen retries cleanly."""
    mig = tmp_path / "migbad"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        (mig / f.name).write_bytes(f.read_bytes())
    bad = mig / "0010_scheduler_state.sql"
    bad.write_text(bad.read_text() +
                   "INSERT INTO series(id,source_id,indicator_key,role,theme,geography,"
                   "frequency,unit,active) VALUES ('ghost.PT',999,'x','primary','economy',"
                   "'PT','A','n',1);\n")
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", mig)
    p = tmp_path / "probe.db"
    with pytest.raises(RuntimeError, match="foreign key violations"):
        open_db(p)
    raw = sqlite3.connect(p)
    try:
        assert "0010" not in {v.split("_")[0]
                              for (v,) in raw.execute("SELECT version FROM schema_migration")}
        assert raw.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 0
    finally:
        raw.close()
    with pytest.raises(RuntimeError, match="foreign key violations"):
        open_db(p)                                     # repeatable, not one-shot
    bad.write_bytes((MIGRATIONS_DIR / "0010_scheduler_state.sql").read_bytes())
    d = open_db(p)                                     # fixed file retries and succeeds
    assert any(v.startswith("0010") for (v,) in
               d.conn.execute("SELECT version FROM schema_migration"))
    d.close()
