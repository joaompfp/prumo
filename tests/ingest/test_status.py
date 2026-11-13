"""Status projection tests (Task 17A): honest latest attempt / last REAL verification /
genuine retrieval date / staleness policy / blocked-vs-technical-failure, per DATASET, built
from Db fixtures written the same way the pipeline writes them (no HTTP anywhere here)."""
from datetime import datetime, timedelta, timezone

import pytest

from ingest.db import open_db
from ingest.models import Observation, SeriesSpec, SourceSpec
from ingest.operations import group_specs
from ingest.registry import sync_registry
from ingest.status import build_status, render_text

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


WB = SourceSpec(name="worldbank", licence="CC BY 4.0", licence_url="http://l",
                attribution="WB", redistribution_ok=True, verifiable=True)
FRED = SourceSpec(name="fred", licence="UNVERIFIED", licence_url="http://l",
                  attribution="FRED", redistribution_ok=False, verifiable=True)
DGEG = SourceSpec(name="dgeg", licence="UNVERIFIED", licence_url="http://l",
                  attribution="DGEG", redistribution_ok=False, verifiable=False)


def _wb(sid: str, code: str, active: bool = True, schedule: str | None = None,
        frequency: str = "A") -> SeriesSpec:
    return SeriesSpec(id=sid, source=WB, indicator_key=f"{code}.{sid}", role="primary",
                      theme="economy", geography="PT", frequency=frequency, unit="u",
                      native_code=f"{code}:PRT", active=active, schedule=schedule)


def _spec(source: SourceSpec, sid: str, active: bool = True,
          frequency: str = "M") -> SeriesSpec:
    return SeriesSpec(id=sid, source=source, indicator_key=f"k_{sid}", role="primary",
                      theme="economy", geography="PT", frequency=frequency, unit="u",
                      active=active)


def _series(report, sid):
    return next(s for src in report.sources for s in src.series if s.id == sid)


def _source(report, name):
    return next(s for s in report.sources if s.name == name)


def _fetched_run(db, key: str, rows, started: datetime, state: str = "verified",
                 verify_at: datetime | None = None, verify_passed: bool = True):
    """rows: (spec, period, token, fetched_at). Shortcut 'verified' runs pass rows=() and
    verify_at=None (no observations, no verification row: pipeline Ruling D identity)."""
    run = db.begin_run("worldbank", key, _ts(started))
    for spec, period, token, f_at in rows:
        fid = db.record_raw_fetch(source_name="worldbank", run_id=run, url="http://x",
                                  params_json=None, fetched_at=_ts(f_at), http_status=200,
                                  sha256=f"{key}-{spec.id}-{period}-{token}", path="p",
                                  n_bytes=1, ok=True)
        db.write_observations(run, [(Observation.from_raw(spec.id, period, token), fid,
                                     _ts(f_at))])
    db.set_run_state(run, state, finished_at=_ts(started))
    if verify_at is not None:
        db.add_verification(run, 1, 1, verify_passed, _ts(verify_at))
    return run


def _legacy_rows(db, spec, rows):
    run = db.legacy_run("worldbank", "legacy:worldbank", _ts(datetime(2026, 4, 6, tzinfo=timezone.utc)))
    db.write_legacy_observations(run, [(Observation.from_raw(spec.id, p, t), _ts(f))
                                       for p, t, f in rows])
    return run


@pytest.fixture
def db(tmp_path):
    d = open_db(tmp_path / "prumo.db")
    yield d
    d.close()


def test_legacy_only_series_is_availability_legacy_unverified_never_verified_evidence(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    legacy_date = datetime(2026, 3, 1, tzinfo=timezone.utc)
    _legacy_rows(db, spec, [("2024", "9.0", legacy_date)])
    report = build_status(db, [spec], now=lambda: NOW)
    s = _series(report, "worldbank.gdp.PT")
    assert s.availability == "legacy-unverified"
    assert s.last_verified is None           # the synthetic 'verified' legacy run is NOT evidence
    assert s.latest_attempt is None          # legacy imports are not attempts
    assert s.real_data_fetched_at == _ts(legacy_date)  # the honest ORIGINAL retrieval date
    assert s.legacy_rows == 1
    assert s.stale is True                   # ~8 months old vs the 30d annual refresh policy
    src = _source(report, "worldbank")
    assert src.last_verified is None and src.latest_attempt is None


def test_fetch_verify_then_idempotent_shortcut_keeps_the_old_verification_and_data_date(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    key = group_specs([spec])[0].key()
    t_fetch = datetime(2026, 11, 1, tzinfo=timezone.utc)
    _fetched_run(db, key, [(spec, "2025", "2.0", t_fetch)], t_fetch,
                 verify_at=t_fetch + timedelta(minutes=5), verify_passed=True)
    # the Ruling D idempotent shortcut: a later run, state 'verified', NO observations and
    # NO verification row of its own
    _fetched_run(db, key, [], t_fetch + timedelta(days=3), state="verified")
    report = build_status(db, [spec], now=lambda: NOW)
    s = _series(report, "worldbank.gdp.PT")
    assert s.availability == "verified"
    assert s.last_verified == _ts(t_fetch + timedelta(minutes=5))  # did NOT advance to day 3
    assert s.latest_attempt == _ts(t_fetch + timedelta(days=3))    # the attempt is visible
    assert s.real_data_fetched_at == _ts(t_fetch)  # stored observations keep the old date


def test_never_fetched_vs_never_verified_are_explicit_null_reasons(db):
    a = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    b = _wb("worldbank.pop.PT", "SP.POP.TOTL")
    sync_registry(db, [a, b])
    key = group_specs([b])[0].key()
    _fetched_run(db, key, [(b, "2025", "1", NOW)], NOW - timedelta(days=1),
                 state="failed-verification", verify_at=NOW - timedelta(days=1),
                 verify_passed=False)
    report = build_status(db, [a, b], now=lambda: NOW)
    assert (_series(report, a.id).availability, _series(report, a.id).stale,
            _series(report, a.id).stale_reason) == ("none", None, "never_fetched")
    sb = _series(report, b.id)
    assert (sb.availability, sb.stale, sb.stale_reason) == ("none", None, "never_verified")
    assert sb.latest_attempt_state == "failed-verification"


def test_per_dataset_latest_state_a_healthy_group_cannot_hide_a_failed_one(db):
    gdp, pop = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG"), _wb("worldbank.pop.PT", "SP.POP.TOTL")
    sync_registry(db, [gdp, pop])
    keys = {g.label: g.key() for g in group_specs([gdp, pop])}
    t_early, t_late = NOW - timedelta(days=2), NOW - timedelta(days=1)
    _fetched_run(db, keys["NY.GDP.MKTP.KD.ZG"], [], t_early, state="failed-fetch")
    _fetched_run(db, keys["SP.POP.TOTL"], [(pop, "2025", "1", t_late)], t_late,
                 verify_at=t_late, verify_passed=True)
    report = build_status(db, [gdp, pop], now=lambda: NOW)
    assert _series(report, gdp.id).dataset_label == "NY.GDP.MKTP.KD.ZG"
    assert _series(report, gdp.id).latest_attempt == _ts(t_early)
    assert _series(report, gdp.id).latest_attempt_state == "failed-fetch"
    assert _series(report, pop.id).latest_attempt_state == "verified"
    src = _source(report, "worldbank")
    # the failed dataset is a first-class entry; the verified one does not conceal it
    by_key = {d.label: d for d in src.datasets}
    assert by_key["NY.GDP.MKTP.KD.ZG"].latest_state == "failed-fetch"
    assert by_key["SP.POP.TOTL"].latest_state == "verified"


def test_source_latest_attempt_is_the_latest_dataset_attempt_even_when_failed(db):
    gdp, pop = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG"), _wb("worldbank.pop.PT", "SP.POP.TOTL")
    sync_registry(db, [gdp, pop])
    keys = {g.label: g.key() for g in group_specs([gdp, pop])}
    _fetched_run(db, keys["SP.POP.TOTL"], [(pop, "2025", "1", NOW - timedelta(days=2))],
                 NOW - timedelta(days=2), verify_at=NOW - timedelta(days=2))
    _fetched_run(db, keys["NY.GDP.MKTP.KD.ZG"], [], NOW - timedelta(hours=1),
                 state="failed-fetch")
    src = _source(build_status(db, [gdp, pop], now=lambda: NOW), "worldbank")
    assert src.latest_attempt == _ts(NOW - timedelta(hours=1))
    assert src.latest_attempt_state == "failed-fetch"


def test_pending_runs_are_listed_with_staleness(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    key = group_specs([spec])[0].key()
    stale_run = _fetched_run(db, key, [(spec, "2024", "1", NOW)], NOW - timedelta(hours=30),
                             state="pending-verification")
    fresh_run = _fetched_run(db, key, [(spec, "2025", "2", NOW)], NOW - timedelta(hours=1),
                             state="pending-verification")
    src = _source(build_status(db, [spec], now=lambda: NOW), "worldbank")
    got = {p.run_id: p for p in src.pending_runs}
    assert got[stale_run].stale is True and got[fresh_run].stale is False
    assert got[stale_run].started_at == _ts(NOW - timedelta(hours=30))
    assert got[fresh_run].dataset == "NY.GDP.MKTP.KD.ZG"


def test_events_are_total_counts_per_kind(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    key = group_specs([spec])[0].key()
    run = _fetched_run(db, key, [], NOW, state="failed-fetch")
    db.add_event(_ts(NOW), "fetch_failure", run, {"e": 1})
    db.add_event(_ts(NOW), "fetch_failure", run, {"e": 2})
    db.add_event(_ts(NOW), "revision", run, {"x": 1})
    src = _source(build_status(db, [spec], now=lambda: NOW), "worldbank")
    assert src.events == {"fetch_failure": 2, "revision": 1}


def test_staleness_policy_schedule_overrides_frequency_default(db):
    fast = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG", schedule="1d", frequency="A")
    annual = _wb("worldbank.pop.PT", "SP.POP.TOTL", frequency="A")
    sync_registry(db, [fast, annual])
    ten_days_ago = NOW - timedelta(days=10)
    for spec, key in [(fast, group_specs([fast])[0].key()),
                      (annual, group_specs([annual])[0].key())]:
        _fetched_run(db, key, [(spec, "2025", "1", ten_days_ago)], ten_days_ago,
                     verify_at=ten_days_ago)
    report = build_status(db, [fast, annual], now=lambda: NOW)
    assert _series(report, fast.id).stale is True     # 10d > 1d schedule
    assert _series(report, annual.id).stale is False  # 10d < 30d annual default


def test_blocked_is_separate_from_technical_failure(db):
    fred = _spec(FRED, "fred.zinc.WORLD", active=True)
    dgeg = _spec(DGEG, "dgeg.diesel.PT", active=False)
    sync_registry(db, [fred, dgeg])
    report = build_status(db, [fred, dgeg], now=lambda: NOW)
    assert _source(report, "fred").blockers == ("licence_withheld",)
    assert _source(report, "dgeg").blockers == ("not_verifiable", "licence_withheld")
    assert _source(report, "dgeg").blocked and _source(report, "dgeg").active_series == 0


def test_typed_json_schema_and_readable_text(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    _fetched_run(db, group_specs([spec])[0].key(), [(spec, "2025", "2.0", NOW)], NOW,
                 verify_at=NOW)
    report = build_status(db, [spec], now=lambda: NOW)
    doc = report.to_dict()
    assert doc["schema"] == "prumo-status" and doc["version"] == 1
    assert doc["generated_at"] == _ts(NOW)
    assert doc["staleness_policy"]["defaults_days"]["A"] == 30
    series = doc["sources"][0]["series"][0]
    assert series["availability"] == "verified" and series["last_verified"] == _ts(NOW)
    text = render_text(report)
    assert "worldbank" in text and "verified" in text and "staleness" in text
