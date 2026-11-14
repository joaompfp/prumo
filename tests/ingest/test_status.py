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
        db.add_verification(run, 1, 1, verify_passed, _ts(verify_at),
                            sample_procedure="prumo-sample-v2", sample_design={},
                            input_origin="live", verifier_channel="live")
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
    assert doc["schema"] == "prumo-status" and doc["version"] == 2
    assert doc["generated_at"] == _ts(NOW)
    assert doc["staleness_policy"]["defaults_days"]["A"] == 30
    series = doc["sources"][0]["series"][0]
    assert series["availability"] == "verified" and series["last_verified"] == _ts(NOW)
    text = render_text(report)
    assert "worldbank" in text and "verified" in text and "staleness" in text


# --- Task 23 (final review part D): confirmed-current staleness, counts, windows, scheduler ---

from ingest import verifiers as _verifiers  # noqa: E402
from ingest.pipeline import run_dataset  # noqa: E402
from ingest.rawstore import RawStore  # noqa: E402
from ingest.verify import verify_run  # noqa: E402
from tests.ingest.fake_verifier import FakeVerifier  # noqa: E402
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, truth_of  # noqa: E402
from tests.ingest.fakes import spec as fake_spec  # noqa: E402

T0 = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
MONTHLY = {"m1": [["2026-08", "1.0"], ["2026-09", "1.1"]]}


@pytest.fixture
def pipe(db, tmp_path, monkeypatch):
    """Real pipeline + verification over the fake source (monthly: 1-day refresh policy)."""
    monkeypatch.setattr(_verifiers, "_REGISTRY", {})
    specs = [fake_spec("m1", frequency="M")]
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")

    def fetch(at: datetime, series=MONTHLY, verify: bool = True):
        r = run_dataset(db, store, FakeSource(), specs, FakeHttp(ok(payload(series))),
                        lambda: at)
        if verify and r.state == "pending-verification":
            assert verify_run(db, r.run_id, FakeVerifier(truth_of(series)), None,
                              specs=specs, store=store, now=lambda: at)
        return r
    return db, specs, fetch


def test_identical_refetch_30h_later_is_confirmed_current_not_stale(pipe):
    """Regression (D-I1): an identical-payload re-fetch short-circuits to 'verified' without
    writing observations. It confirms the retained data is current, so the series must not be
    flagged stale while the scheduler keeps re-checking it."""
    db, specs, fetch = pipe
    fetch(T0)
    t1 = T0 + timedelta(hours=30)
    again = fetch(t1)
    assert again.state == "verified" and again.n_written == 0      # the short-circuit
    s = _series(build_status(db, specs, now=lambda: t1 + timedelta(hours=1)), "m1")
    assert s.real_data_fetched_at == _ts(T0)          # latest observation fetched_at: unchanged
    assert s.last_confirmed_current == _ts(t1)        # the identical re-fetch confirmed it
    assert s.stale is False and s.stale_reason is None


def test_no_verified_run_within_the_policy_window_is_stale(pipe):
    db, specs, fetch = pipe
    fetch(T0)
    fetch(T0 + timedelta(hours=30))
    later = T0 + timedelta(hours=30 + 25)             # 25h since the last confirmation, 1d policy
    s = _series(build_status(db, specs, now=lambda: later), "m1")
    assert s.last_confirmed_current == _ts(T0 + timedelta(hours=30))
    assert s.stale is True


def test_a_failed_refetch_never_confirms_currency(pipe):
    db, specs, fetch = pipe
    fetch(T0)
    failed = fetch(T0 + timedelta(hours=30), series={"m1": [["bad", "1"]]})
    assert failed.state != "verified"
    s = _series(build_status(db, specs, now=lambda: T0 + timedelta(hours=31)), "m1")
    assert s.last_confirmed_current == _ts(T0) and s.stale is True


def test_shortcut_confirming_a_withdrawn_vintage_confirms_nothing(pipe):
    """The identical re-fetch vouches for the bytes of the run it matched. Once that run is
    withdrawn, the re-fetch no longer confirms anything; an older verified vintage keeps its
    own (old) confirmation time."""
    db, specs, fetch = pipe
    fetch(T0)
    newer = {"m1": [*MONTHLY["m1"], ["2026-10", "1.2"]]}
    base = fetch(T0 + timedelta(hours=2), series=newer)
    fetch(T0 + timedelta(hours=30), series=newer)     # short-circuit onto `base`
    db.withdraw_run(base.run_id, "test: wrong vintage", _ts(T0 + timedelta(hours=31)))
    s = _series(build_status(db, specs, now=lambda: T0 + timedelta(hours=32)), "m1")
    assert s.availability == "verified"
    assert s.last_confirmed_current == _ts(T0) and s.stale is True


def test_legacy_rows_never_count_as_confirmed_current_even_when_recent(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    _legacy_rows(db, spec, [("2024", "9.0", NOW - timedelta(hours=1))])
    s = _series(build_status(db, [spec], now=lambda: NOW), spec.id)
    assert s.availability == "legacy-unverified"
    assert s.last_confirmed_current is None
    assert (s.stale, s.stale_reason) == (True, "legacy_unverified")


def test_source_and_total_counts_of_stale_never_fetched_and_never_verified(db):
    fresh = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    old = _wb("worldbank.pop.PT", "SP.POP.TOTL")
    never = _wb("worldbank.co2.PT", "EN.CO2")
    unverified = _wb("worldbank.gni.PT", "NY.GNI")
    gone = _wb("worldbank.dead.PT", "X.DEAD", active=False)
    specs = [fresh, old, never, unverified, gone]
    sync_registry(db, specs)
    keys = {g.label: g.key() for g in group_specs([fresh, old, never, unverified])}
    _fetched_run(db, keys["NY.GDP.MKTP.KD.ZG"], [(fresh, "2025", "1", NOW)], NOW,
                 verify_at=NOW)
    _fetched_run(db, keys["SP.POP.TOTL"], [(old, "2025", "1", NOW - timedelta(days=40))],
                 NOW - timedelta(days=40), verify_at=NOW - timedelta(days=40))
    _fetched_run(db, keys["NY.GNI"], [(unverified, "2025", "1", NOW)], NOW,
                 state="failed-verification", verify_at=NOW, verify_passed=False)
    report = build_status(db, specs, now=lambda: NOW)
    src = _source(report, "worldbank")
    assert (src.stale, src.never_fetched, src.never_verified) == (1, 1, 1)
    assert src.stale_series == ("worldbank.pop.PT",)
    assert report.totals == {"active_series": 4, "stale": 1, "never_fetched": 1,
                             "never_verified": 1}
    text = render_text(report)
    assert "stale 1 / never fetched 1 / never verified 1" in text
    assert "STALE worldbank.pop.PT" in text
    assert "all sources: 4 active series; stale 1 / never fetched 1 / never verified 1" in text


def test_stale_series_list_in_text_is_capped(db):
    specs = [_wb(f"worldbank.s{i:02d}.PT", f"X.S{i:02d}") for i in range(12)]
    sync_registry(db, specs)
    for s in specs:
        _fetched_run(db, group_specs([s])[0].key(), [(s, "2025", "1", NOW - timedelta(days=40))],
                     NOW - timedelta(days=40), verify_at=NOW - timedelta(days=40))
    text = render_text(build_status(db, specs, now=lambda: NOW))
    assert text.count("STALE worldbank.") == 1
    assert "(+2 more)" in text


def test_events_are_counted_per_window_and_lifetime(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    run = _fetched_run(db, group_specs([spec])[0].key(), [], NOW, state="failed-fetch")
    db.add_event(_ts(NOW - timedelta(days=10)), "fetch_failure", run, {"e": 1})
    db.add_event(_ts(NOW - timedelta(days=3)), "fetch_failure", run, {"e": 2})
    db.add_event(_ts(NOW - timedelta(hours=2)), "fetch_failure", run, {"e": 3})
    src = _source(build_status(db, [spec], now=lambda: NOW), "worldbank")
    assert src.events == {"fetch_failure": 3}
    assert src.events_24h == {"fetch_failure": 1}
    assert src.events_7d == {"fetch_failure": 2}
    text = render_text(build_status(db, [spec], now=lambda: NOW))
    assert "events 24h {'fetch_failure': 1}; 7d {'fetch_failure': 2}; " \
           "lifetime {'fetch_failure': 3}" in text


def test_scheduler_retry_streaks_and_interrupted_attempts_are_reported(db):
    gdp, pop, co2 = (_wb("worldbank.gdp.PT", "NY.GDP"), _wb("worldbank.pop.PT", "SP.POP"),
                     _wb("worldbank.co2.PT", "EN.CO2"))
    specs = [gdp, pop, co2]
    sync_registry(db, specs)
    keys = {g.label: g.key() for g in group_specs(specs)}
    # failed twice: streak 2, waits BACKOFF[1] = 4h from its finish
    for at in (NOW - timedelta(hours=3), NOW - timedelta(hours=2)):
        db.scheduler_attempt_started(keys["NY.GDP"], "worldbank", "NY.GDP", _ts(at))
        db.scheduler_attempt_finished(keys["NY.GDP"], "failed-fetch",
                                      _ts(at + timedelta(minutes=1)))
    # interrupted: 'running' marker, no finish (process killed mid-attempt)
    db.scheduler_attempt_started(keys["SP.POP"], "worldbank", "SP.POP",
                                 _ts(NOW - timedelta(minutes=30)))
    # healthy: verified 1h ago, annual 30d policy
    db.scheduler_attempt_started(keys["EN.CO2"], "worldbank", "EN.CO2",
                                 _ts(NOW - timedelta(hours=1)))
    db.scheduler_attempt_finished(keys["EN.CO2"], "verified", _ts(NOW - timedelta(hours=1)))
    report = build_status(db, specs, now=lambda: NOW)
    src = _source(report, "worldbank")
    by = {d.label: d.scheduler for d in src.datasets}
    assert by["NY.GDP"].last_attempt_state == "failed-fetch"
    assert by["NY.GDP"].failure_streak == 2
    assert by["NY.GDP"].next_eligible_at == _ts(NOW - timedelta(hours=2, minutes=-1)
                                                + timedelta(hours=4))
    assert by["SP.POP"].last_attempt_state == "running" and by["SP.POP"].failure_streak == 1
    assert by["SP.POP"].next_eligible_at == _ts(NOW + timedelta(minutes=30))  # 1h from start
    assert by["EN.CO2"].failure_streak == 0
    assert by["EN.CO2"].next_eligible_at == _ts(NOW - timedelta(hours=1) + timedelta(days=30))
    assert (src.scheduler_retrying, src.scheduler_running) == (2, 1)
    text = render_text(report)
    assert "scheduler: 2 retrying (max streak 2), 1 running or interrupted" in text
    assert "scheduler failed-fetch, streak 2, next eligible" in text
    assert "scheduler running (in flight, or interrupted if the worker is not mid-attempt)" \
        in text


def test_datasets_are_sorted_by_label_and_pending_policy_hours_is_24(db):
    specs = [_wb("worldbank.z.PT", "ZZ.LAST"), _wb("worldbank.a.PT", "AA.FIRST"),
             _wb("worldbank.m.PT", "MM.MID")]
    sync_registry(db, specs)
    for g in group_specs(specs):
        _fetched_run(db, g.key(), [], NOW, state="failed-fetch")
    report = build_status(db, specs, now=lambda: NOW)
    assert [d.label for d in _source(report, "worldbank").datasets] == [
        "AA.FIRST", "MM.MID", "ZZ.LAST"]
    assert report.to_dict()["staleness_policy"]["pending_stale_after_hours"] == 24
