"""run_dataset against a real SQLite file and a real RawStore on tmp_path."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
import requests

from ingest.pipeline import DatasetRunResult, dataset_key, run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec

BASE = {"s1": [["2023", "1.5"], ["2024", "2.0"]], "s2": [["2024", "10"]]}


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture
def env(db, tmp_path):
    specs = [spec("s1"), spec("s2")]
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    clock = Clock()

    def run(*script, source=None):
        return run_dataset(db, store, source or FakeSource(), specs, FakeHttp(*script), clock)

    return db, specs, run


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def n_obs(db):
    return q(db, "SELECT count(*) FROM observation")[0][0]


def served(db):
    return dict(((s, p), v) for s, p, v in
                q(db, "SELECT series_id, period, value_text FROM served_observation"))


def events(db, kind=None):
    rows = q(db, "SELECT kind, dataset_run_id, detail_json FROM event ORDER BY id")
    return [r for r in rows if kind is None or r[0] == kind]


def verify(db, run_id):
    """Stand-in for Task 7: mark a run verified."""
    db.set_run_state(run_id, "verified")


def verified_baseline(db, run):
    r = run(ok(payload(BASE)))
    verify(db, r.run_id)
    return r


SERVED_BASE = {("s1", "2023"): "1.5", ("s1", "2024"): "2.0", ("s2", "2024"): "10"}


# --- brief tests -------------------------------------------------------------------------------

def test_happy_path_pending_verification(env):
    db, specs, run = env
    r = run(ok(payload(BASE)))
    assert r == DatasetRunResult(state="pending-verification", run_id=r.run_id, n_written=3,
                                 n_quarantined=0)
    assert db.run_state(r.run_id) == "pending-verification"
    rows = q(db, "SELECT series_id, period, value_text, value, kind, dataset_run_id, fetched_at "
                 "FROM observation ORDER BY id")
    assert rows == [("s1", "2023", "1.5", 1.5, "fetched", r.run_id, "2026-11-10T12:00:02+00:00"),
                    ("s1", "2024", "2.0", 2.0, "fetched", r.run_id, "2026-11-10T12:00:02+00:00"),
                    ("s2", "2024", "10", 10.0, "fetched", r.run_id, "2026-11-10T12:00:02+00:00")]
    started, finished, key = q(db, "SELECT started_at, finished_at, dataset_key FROM dataset_run")[0]
    assert started == "2026-11-10T12:00:01+00:00" and finished is not None
    assert key == dataset_key("fake", ["s2", "s1"])
    # raw evidence: one ok raw_fetch row, file on disk is the exact body
    (rf_id, sha, path, ok_, status, params), = q(
        db, "SELECT id, sha256, path, ok, http_status, params_json FROM raw_fetch")
    assert (ok_, status, json.loads(params)) == (1, 200, {"page": 1})
    assert open(path, "rb").read() == payload(BASE)
    assert sha == hashlib.sha256(payload(BASE)).hexdigest()
    assert {r_[0] for r_ in q(db, "SELECT raw_fetch_id FROM observation")} == {rf_id}
    assert served(db) == {}  # not verified yet
    assert events(db) == []


def test_html_200_body_is_failed_fetch_and_serves_previous(env):
    db, _, run = env
    verified_baseline(db, run)
    n = n_obs(db)
    r = run(ok(b"<!DOCTYPE html>\n<html><body>Service unavailable</body></html>"))
    assert (r.state, r.n_written) == ("failed-fetch", 0)
    assert db.run_state(r.run_id) == "failed-fetch"
    assert n_obs(db) == n
    (kind, run_id, detail), = events(db)
    assert (kind, run_id) == ("fetch_failure", r.run_id)
    assert json.loads(detail)["problems"][0]["reason"] == "html_body"
    # the bad body is still kept as audit evidence, flagged not ok
    assert q(db, "SELECT ok, http_status FROM raw_fetch WHERE dataset_run_id = ?", r.run_id) == [(0, 200)]
    assert served(db) == SERVED_BASE


def test_empty_body_is_failed_fetch(env):
    db, _, run = env
    r = run(ok(b""))
    assert (r.state, r.n_written) == ("failed-fetch", 0)
    assert n_obs(db) == 0
    assert [e[0] for e in events(db)] == ["fetch_failure"]
    assert json.loads(events(db)[0][2])["problems"][0]["reason"] == "empty_body"
    assert q(db, "SELECT ok FROM raw_fetch") == [(0,)]


def test_non_2xx_is_failed_fetch(env):
    db, _, run = env
    r = run(ok(b'{"error": "nope"}', status=503))
    assert r.state == "failed-fetch"
    assert json.loads(events(db)[0][2])["problems"][0] == {
        "url": "http://fake/data", "status": 503, "reason": "http_status"}


def test_truncated_json_is_failed_validation(env):
    db, _, run = env
    r = run(ok(b'{"series": {"s1": [["2023", 1.5], ["2024", 2.'))
    assert (r.state, r.n_written, r.n_quarantined) == ("failed-validation", 0, 0)
    assert db.run_state(r.run_id) == "failed-validation"
    assert n_obs(db) == 0
    assert [e[0] for e in events(db)] == ["format_change"]
    assert q(db, "SELECT ok FROM raw_fetch") == [(1,)]  # the fetch itself was fine


def test_series_without_rows_is_failed_validation(env):
    db, _, run = env
    r = run(ok(payload({"s1": BASE["s1"]})))  # s2 missing from the payload
    assert r.state == "failed-validation"
    assert n_obs(db) == 0
    assert json.loads(events(db, "format_change")[0][2])["series_without_rows"] == ["s2"]


def test_identical_payload_is_idempotent(env):
    db, _, run = env
    first = verified_baseline(db, run)
    n = n_obs(db)
    r = run(ok(payload(BASE)))
    assert r == DatasetRunResult(state="verified", run_id=r.run_id, n_written=0, n_quarantined=0)
    assert r.run_id != first.run_id
    assert db.run_state(r.run_id) == "verified"
    assert n_obs(db) == n
    assert q(db, "SELECT count(*) FROM observation WHERE dataset_run_id = ?", r.run_id) == [(0,)]
    assert served(db) == SERVED_BASE
    assert events(db) == []
    # a third identical fetch after a short-circuit run is also short-circuited
    assert run(ok(payload(BASE))).state == "verified"
    assert n_obs(db) == n


@pytest.mark.parametrize("prev_state", ["failed-verification", "pending-verification",
                                        "failed-validation"])
def test_identical_payload_after_failed_verification_is_reprocessed(env, prev_state):
    db, _, run = env
    first = run(ok(payload(BASE)))
    db.set_run_state(first.run_id, prev_state)
    r = run(ok(payload(BASE)))
    assert (r.state, r.n_written) == ("pending-verification", 3)
    assert n_obs(db) == 6


def test_identical_payload_is_reprocessed_when_previous_verified_run_was_another_dataset(env, tmp_path):
    db, specs, run = env
    verified_baseline(db, run)
    # same bytes, but a different dataset (only s1): its own previous run does not exist
    r = run_dataset(db, RawStore(tmp_path / "raw2"), FakeSource(), specs[:1],
                    FakeHttp(ok(payload({"s1": BASE["s1"]}))), Clock())
    assert r.state == "pending-verification"


def test_revision_creates_new_vintage_and_event(env):
    db, _, run = env
    verified_baseline(db, run)
    revised = {"s1": [["2023", "1.5"], ["2024", "2.10"]], "s2": [["2024", "10"]]}
    r = run(ok(payload(revised)))
    assert (r.state, r.n_written) == ("pending-verification", 3)
    (kind, run_id, detail), = events(db)
    assert (kind, run_id) == ("revision", r.run_id)
    assert json.loads(detail) == {"series_id": "s1", "period": "2024", "old": "2.0", "new": "2.10"}
    vintages = q(db, "SELECT value_text FROM observation WHERE series_id='s1' AND period='2024' "
                     "ORDER BY id")
    assert vintages == [("2.0",), ("2.10",)]
    assert served(db)[("s1", "2024")] == "2.0"  # until the new run is verified
    verify(db, r.run_id)
    assert served(db)[("s1", "2024")] == "2.10"


def test_no_revision_event_against_unverified_data(env):
    db, _, run = env
    run(ok(payload(BASE)))  # pending-verification, never verified
    run(ok(payload({"s1": [["2023", "1.5"], ["2024", "9"]], "s2": [["2024", "10"]]})))
    assert events(db, "revision") == []


def test_midway_failure_commits_nothing(env):
    db, _, run = env
    page1 = payload({"s1": BASE["s1"]})
    r = run(ok(page1), requests.ConnectionError("connection reset on page 2"),
            source=FakeSource(pages=2))
    assert (r.state, r.n_written) == ("failed-fetch", 0)
    assert db.run_state(r.run_id) == "failed-fetch"
    assert n_obs(db) == 0
    assert q(db, "SELECT count(*) FROM quarantine") == [(0,)]
    (kind, _, detail), = events(db)
    assert kind == "fetch_failure" and "page 2" in json.loads(detail)["error"]


def test_failure_inside_write_transaction_commits_nothing(env, monkeypatch):
    db, _, run = env
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError("disk on fire")
    # s1 observations are inserted first, then quarantine writing explodes
    monkeypatch.setattr(db, "write_quarantine", boom)
    r = run(ok(payload({"s1": [["2023", "1.5"], ["2024", ":"]], "s2": [["2024", "10"]]})))
    assert calls, "the failure must happen inside the write phase"
    assert (r.state, r.n_written, r.n_quarantined) == ("failed-validation", 0, 0)
    assert db.run_state(r.run_id) == "failed-validation"
    assert n_obs(db) == 0
    assert q(db, "SELECT count(*) FROM quarantine") == [(0,)]
    assert [e[0] for e in events(db)] == ["format_change"]


def test_bad_rows_are_quarantined_not_written(env):
    db, _, run = env
    body = payload({"s1": [["2023", "1.5"], ["2024", ":"], ["Setembro de 2025", "3"]],
                    "s2": [["2024", "10"], ["2025", ".."]]})
    r = run(ok(body))
    assert (r.state, r.n_written, r.n_quarantined) == ("pending-verification", 2, 3)
    assert q(db, "SELECT series_id, period FROM observation ORDER BY id") == [
        ("s1", "2023"), ("s2", "2024")]
    assert q(db, "SELECT series_id, raw_period, raw_value, reason, dataset_run_id FROM quarantine "
                 "ORDER BY id") == [
        ("s1", "2024", ":", "non_numeric", r.run_id),
        ("s1", "Setembro de 2025", "3", "bad_period", r.run_id),
        ("s2", "2025", "..", "non_numeric", r.run_id)]
    verify(db, r.run_id)
    assert set(served(db)) == {("s1", "2023"), ("s2", "2024")}


# --- extra rulings -----------------------------------------------------------------------------

FAILURES = {
    "html_200": (ok(b"  <html><head><title>Erro</title></head></html>"),),
    "empty": (ok(b""),),
    "http_500": (ok(b"oops", status=500),),
    "truncated_json": (ok(b'{"series": {"s1": [['),),
    "http_raises": (requests.Timeout("read timed out"),),
}


@pytest.mark.parametrize("kind", list(FAILURES))
def test_previously_verified_data_still_served_after_each_failure_kind(env, kind):
    db, _, run = env
    verified_baseline(db, run)
    r = run(*FAILURES[kind])
    assert r.state in ("failed-fetch", "failed-validation")
    assert r.n_written == 0
    assert served(db) == SERVED_BASE


def test_previously_verified_data_still_served_after_write_failure(env, monkeypatch):
    db, _, run = env
    verified_baseline(db, run)
    monkeypatch.setattr(db, "write_observations", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("x")))
    assert run(ok(payload({"s1": [["2024", "7"]], "s2": [["2024", "8"]]}))).state == \
        "failed-validation"
    assert served(db) == SERVED_BASE


def test_each_fetch_gets_its_own_raw_fetch_row(env):
    db, _, run = env
    a = verified_baseline(db, run)
    b = run(ok(payload(BASE)))  # identical bytes
    c = run(ok(payload(BASE)), ok(payload({"s1": [], "s2": []})), source=FakeSource(pages=2))
    rows = q(db, "SELECT id, dataset_run_id, sha256 FROM raw_fetch ORDER BY id")
    assert [r[1] for r in rows] == [a.run_id, b.run_id, c.run_id, c.run_id]
    assert len({r[0] for r in rows}) == 4
    assert rows[0][2] == rows[1][2] == rows[2][2]  # same content, separate audit rows


def test_paginated_dataset_writes_rows_from_every_page(env):
    db, _, run = env
    r = run(ok(payload({"s1": BASE["s1"]})), ok(payload({"s2": BASE["s2"]})),
            source=FakeSource(pages=2))
    assert (r.state, r.n_written) == ("pending-verification", 3)


def test_dataset_key_is_order_independent():
    k = dataset_key("ine", ["b", "a"])
    assert k == dataset_key("ine", ["a", "b"])
    assert k == "ine:" + hashlib.sha256(b"a\nb").hexdigest()


def test_rejects_naive_clock_and_foreign_specs(env, db, tmp_path):
    _, specs, _ = env
    store = RawStore(tmp_path / "r")
    with pytest.raises(ValueError, match="timezone"):
        run_dataset(db, store, FakeSource(), specs, FakeHttp(ok(payload(BASE))),
                    lambda: datetime(2026, 1, 1))

    class Other(FakeSource):
        name = "other"
    with pytest.raises(ValueError, match="source"):
        run_dataset(db, store, Other(), specs, FakeHttp(), Clock())
    with pytest.raises(ValueError, match="specs"):
        run_dataset(db, store, FakeSource(), [], FakeHttp(), Clock())
