"""Db.content_base_run / Db.run_content: per-run content reads for the vintage short-circuit."""
import pytest

from ingest.db import RunContent

T = "2026-11-01T00:00:00+00:00"
KEY = "ine:x"


def _setup(db):
    c = db.conn
    c.execute("INSERT INTO source(id,name,licence,licence_url,attribution,redistribution_ok)"
              " VALUES (1,'ine','CC-BY','http://l','INE',1)")
    for sid in ("s1", "s2"):
        c.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
                  "unit,active) VALUES (?,1,'gdp','primary','economy','PT','A','EUR',1)", (sid,))


def _run(db, state, *, obs=(), quarantine=(), key=KEY):
    """A run in `state` holding observation rows (series, period, value, released_at) and
    quarantine rows (series, raw_period, raw_value, reason)."""
    rid = db.begin_run("ine", key, T)
    raw = db.conn.execute(
        "INSERT INTO raw_fetch(source_id,dataset_run_id,url,fetched_at,http_status,sha256,path,"
        "bytes,ok) VALUES (1,?,'http://x',?,200,'a','p',1,1)", (rid, T)).lastrowid
    for i, (s, p, v, rel) in enumerate(obs):
        db.conn.execute(
            "INSERT INTO observation(series_id,period,value_text,value,kind,dataset_run_id,"
            "raw_fetch_id,fetched_at,released_at) VALUES (?,?,?,?, 'fetched',?,?,?,?)",
            (s, p, v, float(v), rid, raw if i == 0 else _raw(db, rid, i), T, rel))
    for q in quarantine:
        db.conn.execute("INSERT INTO quarantine(dataset_run_id,series_id,raw_period,raw_value,"
                        "reason,created_at) VALUES (?,?,?,?,?,?)", (rid, *q, T))
    _to_state(db, rid, state)
    return rid


def _raw(db, rid, i):
    return db.conn.execute(
        "INSERT INTO raw_fetch(source_id,dataset_run_id,url,fetched_at,http_status,sha256,path,"
        "bytes,ok) VALUES (1,?,?,?,200,?,'p',1,1)", (rid, f"http://x/{i}", T, f"h{i}")).lastrowid


def _to_state(db, rid, state):
    if state == "withdrawn":
        db.set_run_state(rid, "verified")
        db.withdraw_run(rid, "bad", T)
    else:
        db.set_run_state(rid, state)


NON_VERIFIED = ["failed-verification", "withdrawn", "blocked-stale", "pending-verification",
                "failed-fetch"]
OBS = [("s1", "2025", "1", None)]


def test_a_previous_verified_writer_is_the_base(db):
    _setup(db)
    a = _run(db, "verified", obs=OBS)
    b = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, b) == a


def test_b_skips_verified_runs_without_observations(db):
    _setup(db)
    a = _run(db, "verified", obs=OBS)
    _run(db, "verified")
    _run(db, "verified")
    c = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, c) == a


@pytest.mark.parametrize("state", NON_VERIFIED)
def test_c_first_content_run_not_verified_gives_none(db, state):
    _setup(db)
    _run(db, state, obs=OBS)
    _run(db, "verified")
    c = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, c) is None


@pytest.mark.parametrize("state", NON_VERIFIED)
def test_d_non_verified_previous_run_blocks_older_writer(db, state):
    _setup(db)
    _run(db, "verified", obs=OBS)
    _run(db, state, obs=OBS if state == "withdrawn" else ())  # withdraw needs rows
    c = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, c) is None


def test_e_first_run_of_a_key_has_no_base(db):
    _setup(db)
    _run(db, "verified", obs=OBS, key="other")  # another key does not count
    a = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, a) is None


def test_f_verified_without_content_and_no_earlier_writer_gives_none(db):
    _setup(db)
    _run(db, "verified")
    b = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, b) is None


def test_verified_run_with_only_quarantine_rows_is_the_base(db):
    _setup(db)
    a = _run(db, "verified", quarantine=[("s1", "2025", "x", "bad value")])
    b = db.begin_run("ine", KEY, T)
    assert db.content_base_run(KEY, b) == a


def test_run_content_keeps_duplicates_sorted_with_released_at(db):
    _setup(db)
    rid = _run(db, "verified",
               obs=[("s2", "2025", "2", "2026-01-01"), ("s1", "2025", "1", None),
                    ("s1", "2025", "1", None)],
               quarantine=[(None, None, "z", "r2"), ("s1", "2024", None, "r1")])
    assert db.run_content(rid) == RunContent(
        observations=(("s1", "2025", "1", None, None), ("s1", "2025", "1", None, None),
                      ("s2", "2025", "2", None, "2026-01-01")),
        quarantine=((None, None, "z", "r2"), ("s1", "2024", None, "r1")))


def test_run_content_order_independent_of_insertion(db):
    _setup(db)
    rows = [("s1", "2025", "1", None), ("s2", "2025", "2", "2026-01-01")]
    a = _run(db, "verified", obs=rows, quarantine=[("s1", "p", "v", "r1"), ("s2", "p", "v", "r2")])
    b = _run(db, "verified", obs=rows[::-1],
             quarantine=[("s2", "p", "v", "r2"), ("s1", "p", "v", "r1")])
    assert db.run_content(a) == db.run_content(b)
