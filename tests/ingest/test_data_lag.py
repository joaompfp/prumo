"""Data-time lag check (final review C-I1): an ACTIVE series whose newest fetched period lags
today by more than the documented per-frequency allowance is flagged as possibly frozen."""
from datetime import date

import pytest

from ingest.cli import main
from ingest.data_lag import MAX_LAG, lagging_series, period_lag
from ingest.db import open_db
from ingest.models import SeriesSpec, SourceSpec

SRC = SourceSpec(name="toy", licence="L", licence_url="u", attribution="a", redistribution_ok=True)
TODAY = date(2026, 11, 14)


def _spec(sid, freq, active=True):
    return SeriesSpec(id=sid, source=SRC, indicator_key=sid, role="primary", theme="economy",
                      geography="PT", frequency=freq, unit="u", active=active)


@pytest.mark.parametrize("freq,period,lag", [
    ("A", "2026", 0), ("A", "2023", 3), ("A", "2022", 4),
    ("S", "2026-S2", 0), ("S", "2025-S1", 3),
    ("Q", "2026-Q4", 0), ("Q", "2025-Q3", 5),
    ("M", "2026-11", 0), ("M", "2025-12", 11), ("M", "2026-05", 6),
    ("D", "2026-11-13", 1), ("D", "2026-10-14", 31),
    ("PT15M", "2026-11-10T23:45:00+00:00", 4),
])
def test_period_lag_counts_whole_periods_back_from_today(freq, period, lag):
    assert period_lag(freq, period, TODAY) == lag


def test_allowance_is_documented_for_every_frequency():
    assert set(MAX_LAG) == {"A", "S", "Q", "M", "D", "PT15M"}
    assert MAX_LAG["M"] == 6 and MAX_LAG["A"] == 3


def test_frozen_hicp_shape_is_flagged_and_healthy_or_inactive_are_not():
    specs = [_spec("frozen", "M"), _spec("fresh", "M"), _spec("annual", "A"),
             _spec("off", "M", active=False), _spec("never", "Q")]
    latest = {"frozen": "2025-12", "fresh": "2026-09", "annual": "2024", "off": "2020-01"}
    found = lagging_series(specs, latest, TODAY)
    assert [(f.series_id, f.latest_period, f.lag, f.max_lag) for f in found] == \
        [("frozen", "2025-12", 11, 6)]


def test_unknown_period_shape_fails_loudly():
    with pytest.raises(ValueError):
        period_lag("M", "2025-13", TODAY)


def _toy_registry(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text(
        "sources:\n  toy:\n    licence: L\n    licence_url: u\n    attribution: a\n"
        "    redistribution_ok: true\n"
        "series:\n"
        "- {id: toy.frozen.PT, source: toy, indicator_key: k1, role: primary, theme: economy,"
        " geography: PT, frequency: M, unit: u}\n"
        "- {id: toy.fresh.PT, source: toy, indicator_key: k2, role: primary, theme: economy,"
        " geography: PT, frequency: A, unit: u}\n"
        "- {id: toy.never.PT, source: toy, indicator_key: k3, role: primary, theme: economy,"
        " geography: PT, frequency: Q, unit: u}\n")
    return p


def _seed(db_path, rows, state="verified"):
    from ingest.registry import load_registry, sync_registry
    db = open_db(db_path)
    try:
        sync_registry(db, load_registry(db_path.parent / "r.yaml"))
        run = db.begin_run("toy", "toy:k", "2026-11-01T00:00:00+00:00")
        raw = db.conn.execute(
            "INSERT INTO raw_fetch(source_id, url, fetched_at, ok) SELECT id, 'u', "
            "'2026-11-01T00:00:00+00:00', 1 FROM source WHERE name = 'toy'").lastrowid
        for sid, period, kind in rows:
            db.conn.execute(
                "INSERT INTO observation(series_id, period, value_text, value, kind, "
                "dataset_run_id, raw_fetch_id, fetched_at) VALUES (?, ?, '1', 1.0, ?, ?, ?, "
                "'2026-11-01T00:00:00+00:00')",
                (sid, period, kind, run, None if kind != "fetched" else raw))
        db.set_run_state(run, state)
        db.conn.commit()
    finally:
        db.close()


def test_db_latest_fetched_period_ignores_legacy_rows(tmp_path):
    _toy_registry(tmp_path)
    _seed(tmp_path / "p.sqlite3", [("toy.frozen.PT", "2025-11", "fetched"),
                                   ("toy.frozen.PT", "2025-12", "fetched"),
                                   ("toy.frozen.PT", "2026-10", "legacy-unverified")])
    db = open_db(tmp_path / "p.sqlite3")
    try:
        assert db.latest_fetched_periods() == {"toy.frozen.PT": "2025-12"}
    finally:
        db.close()


def test_db_latest_fetched_period_ignores_withdrawn_and_failed_runs(tmp_path):
    """Re-review 2 M4: a withdrawn or failed run's (possibly invented future) period must not
    mask a frozen dataset; verified and pending-verification runs count."""
    _toy_registry(tmp_path)
    p = tmp_path / "p.sqlite3"
    _seed(p, [("toy.frozen.PT", "2025-12", "fetched")])
    _seed(p, [("toy.frozen.PT", "2099-01", "fetched")], state="failed-verification")
    db = open_db(p)
    try:
        assert db.latest_fetched_periods() == {"toy.frozen.PT": "2025-12"}
        wrong = db.begin_run("toy", "toy:k", "2026-11-02T00:00:00+00:00")
        fid = db.record_raw_fetch(source_name="toy", run_id=wrong, url="u", params_json=None,
                                  fetched_at="2026-11-02T00:00:00+00:00", http_status=200,
                                  sha256="x", path="p", n_bytes=1, ok=True)
        db.conn.execute(
            "INSERT INTO observation(series_id, period, value_text, value, kind, "
            "dataset_run_id, raw_fetch_id, fetched_at) VALUES ('toy.frozen.PT', '2098-01', "
            "'1', 1.0, 'fetched', ?, ?, '2026-11-02T00:00:00+00:00')", (wrong, fid))
        db.set_run_state(wrong, "pending-verification")
        assert db.latest_fetched_periods() == {"toy.frozen.PT": "2098-01"}
        db.set_run_state(wrong, "verified")
        db.withdraw_run(wrong, "invented future period", "2026-11-03T00:00:00+00:00")
        assert db.latest_fetched_periods() == {"toy.frozen.PT": "2025-12"}
    finally:
        db.close()


def test_cli_lag_reports_frozen_and_never_fetched_and_exits_1(tmp_path, capsys):
    reg = _toy_registry(tmp_path)
    _seed(tmp_path / "p.sqlite3", [("toy.frozen.PT", "2020-01", "fetched"),
                                   ("toy.fresh.PT", str(date.today().year), "fetched")])
    rc = main(["--db", str(tmp_path / "p.sqlite3"), "--raw-dir", str(tmp_path / "raw"),
               "--registry", str(reg), "lag"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "LAGGING toy.frozen.PT M latest=2020-01" in out
    assert "NO-FETCHED-DATA toy.never.PT" in out
    assert "toy.fresh.PT" not in out


def test_cli_lag_exits_0_when_nothing_lags(tmp_path, capsys):
    reg = _toy_registry(tmp_path)
    today = date.today()
    _seed(tmp_path / "p.sqlite3", [("toy.frozen.PT", f"{today.year}-{today.month:02d}", "fetched"),
                                   ("toy.fresh.PT", str(today.year), "fetched"),
                                   ("toy.never.PT", f"{today.year}-Q{(today.month - 1) // 3 + 1}",
                                    "fetched")])
    rc = main(["--db", str(tmp_path / "p.sqlite3"), "--raw-dir", str(tmp_path / "raw"),
               "--registry", str(reg), "lag"])
    assert rc == 0
    assert "0 lagging" in capsys.readouterr().out
