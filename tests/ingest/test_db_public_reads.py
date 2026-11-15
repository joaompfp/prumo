"""Public site read layer (project 4): every served value, receipt and revision the pages show.

Data is written through the real Db paths used by the backoffice tests; the reads must return
plain dicts, keep publisher tokens as text, and never expose a withheld source.
"""
import json

from ingest.models import Observation, SourceSpec
from ingest.registry import sync_derived, sync_registry
from tests.ingest.derived_helpers import derived_spec
from tests.ingest.fakes import spec

T1 = "2026-11-01T00:00:00+00:00"
T2 = "2026-11-02T00:00:00+00:00"
T3 = "2026-11-03T00:00:00+00:00"
T4 = "2026-11-04T00:00:00+00:00"
CLOSED = SourceSpec(name="closed", licence="UNVERIFIED", licence_url="https://x/terms",
                    attribution="Closed Source", redistribution_ok=False)
KEY = "derived.s1_change"


def _series(sid="s1", *, source=None, role="primary", active=True, key="fam.PT.A"):
    base = spec(sid, frequency="M")
    return base.model_copy(update={"source": source or base.source, "role": role,
                                   "active": active, "indicator_key": key, "unit": "pct"})


def _verified(db, sid, period, value, fetched_at, key, *, source="fake", flag=None):
    run = db.begin_run(source, key, fetched_at)
    fid = db.record_raw_fetch(source_name=source, run_id=run, url=f"https://{source}/x",
                              params_json=None, fetched_at=fetched_at, http_status=200,
                              sha256=f"sha-{key}", path="p", n_bytes=10, ok=True)
    obs = Observation.from_raw(sid, period, value)
    if flag is not None:
        obs = obs.model_copy(update={"status_flag": flag})
    db.write_observations(run, [(obs, fid, fetched_at)])
    db.set_run_state(run, "verified")
    return run


def _verification(db, run, *, sample_size=12, item=None):
    vid = db.add_verification(run, 4242, sample_size, True, T2, sample_procedure="prumo-sample-v2",
                              sample_design={"n_items": sample_size}, input_origin="live",
                              verifier_channel="live")
    if item is not None:
        db.add_verification_item(vid, {
            **{c: None for c in (
                "expected_text", "expected_decimal", "expected_unit", "expected_flag",
                "observed_series_id", "observed_period", "observed_text", "observed_decimal",
                "observed_unit", "observed_flag", "evidence_url", "evidence_sha256", "note",
                "reason", "compared", "unit_not_compared", "flag_not_compared")},
            "series_id": item[0], "period": item[1], "match": True})
    return vid


def _setup(db):
    sync_registry(db, [_series(), _series("s2", role="cross_check"), _series("s3", source=CLOSED)])
    return _verified(db, "s1", "2026-01", "1.50", T1, "k1")


# --- counts and catalogue --------------------------------------------------------------------

def test_counts_ignore_withheld_sources(db):
    _setup(db)
    assert db.public_counts() == {"series": 1, "sources": 1, "last_fetched_at": T1}


def test_catalogue_has_primary_series_metadata_and_family(db):
    _setup(db)
    rows = db.public_catalogue()
    assert [r["id"] for r in rows] == ["s1"]
    row = rows[0]
    assert row["family"] == "fam" and row["source"] == "fake" and row["unit"] == "pct"
    assert "latest_value_text" not in row and "served_count" not in row


def test_catalogue_excludes_inactive_cross_check_and_withheld(db):
    sync_registry(db, [_series(), _series("s2", role="cross_check"),
                       _series("s4", active=False), _series("s3", source=CLOSED)])
    for sid in ("s1", "s2", "s4", "s3"):
        _verified(db, sid, "2026-01", "1", T1, f"k-{sid}",
                  source="closed" if sid == "s3" else "fake")
    assert [r["id"] for r in db.public_catalogue()] == ["s1"]


def test_latest_values_are_a_per_id_lookup(db):
    _setup(db)
    _verified(db, "s1", "2026-02", "2.00", T2, "k2")
    got = db.public_latest_values(["s1", "nope"])
    assert got == {"s1": {"period": "2026-02", "value_text": "2.00",
                          "status_flag": None, "fetched_at": T2}}
    assert db.public_latest_values([]) == {}


def test_public_series_refuses_withheld_and_unknown(db):
    _setup(db)
    row = db.public_series("s1")
    assert row["latest_value_text"] == "1.50" and "served_count" not in row
    assert row["licence"] == "CC-BY-4.0" and row["attribution"] == "Fake"
    assert db.public_series("s3") is None
    assert db.public_series("nope") is None


def test_public_series_returns_cross_check_role_for_the_caller_to_refuse(db):
    _setup(db)
    _verified(db, "s2", "2026-01", "1.50", T1, "k-cross")
    assert db.public_series("s2")["role"] == "cross_check"


def test_series_values_are_oldest_first_and_keep_tokens(db):
    _setup(db)
    _verified(db, "s1", "2026-02", "2.00", T2, "k2")
    rows = db.public_series_values("s1")
    assert [(r["period"], r["value_text"]) for r in rows] == [("2026-01", "1.50"),
                                                              ("2026-02", "2.00")]
    assert rows[0]["raw_sha"] == "sha-k1"


# --- provenance ------------------------------------------------------------------------------

def test_provenance_carries_receipt_run_and_verification(db):
    run = _setup(db)
    _verification(db, run, sample_size=12, item=("s1", "2026-01"))
    p = db.public_provenance("s1")
    assert (p["period"], p["value_text"], p["run_id"]) == ("2026-01", "1.50", run)
    assert (p["raw_url"], p["http_status"], p["sha256"], p["bytes"]) == \
        ("https://fake/x", 200, "sha-k1", 10)
    assert (p["verification_created_at"], p["sample_size"], p["verification_passed"]) == \
        (T2, 12, 1)
    assert p["sampled"] == 1 and p["licence"] == "CC-BY-4.0"
    assert db.public_provenance("nope") is None


def test_provenance_says_when_this_value_was_not_sampled(db):
    run = _setup(db)
    _verification(db, run, item=("s1", "1999-01"))
    assert db.public_provenance("s1")["sampled"] == 0


# --- revisions -------------------------------------------------------------------------------

def test_revisions_report_only_changed_values_and_mark_served(db):
    _setup(db)
    _verified(db, "s1", "2026-01", "1.50", T2, "k2")   # identical re-fetch: not a revision
    _verified(db, "s1", "2026-01", "2.00", T3, "k3")   # a real revision
    revised, unchanged = db.public_revisions("s1")
    assert unchanged == 0
    assert [r["period"] for r in revised] == ["2026-01"]
    versions = revised[0]["versions"]
    assert [(v["value_text"], v["served"]) for v in versions] == [("1.50", False), ("2.00", True)]


def test_revisions_ignore_failed_runs_and_collapse_repeats(db):
    _setup(db)
    _verified(db, "s1", "2026-01", "1.50", T2, "k2")   # same value again
    bad = _verified(db, "s1", "2026-01", "9.99", T3, "k3")
    db.set_run_state(bad, "failed-verification")
    revised, _ = db.public_revisions("s1")
    assert revised == []
    assert db.public_revisions("s1")[1] == 1


def test_revisions_keep_every_distinct_value_including_reverts(db):
    _setup(db)
    _verified(db, "s1", "2026-01", "2.00", T2, "k2")
    _verified(db, "s1", "2026-01", "1.50", T3, "k3")   # a revert is a revision too
    _verified(db, "s1", "2026-01", "3.00", T4, "k4")
    versions = db.public_revisions("s1")[0][0]["versions"]
    assert [v["value_text"] for v in versions] == ["1.50", "2.00", "1.50", "3.00"]
    assert [v["fetched_at"] for v in versions] == [T1, T2, T3, T4]
    assert [v["served"] for v in versions] == [False, False, False, True]


# --- derived ---------------------------------------------------------------------------------

def _derived(db):
    sync_derived(db, [derived_spec(KEY, "s1", "period_change")])
    inputs = db.served_fetched_inputs("s1")
    ids = [inputs["2026-01"][0]]
    dsid = next(r["id"] for r in db.derived_series_rows(active_only=False) if r["key"] == KEY)
    run = db.begin_derived_run(T3, "cli", [KEY])
    db.write_derived_observations(run, T3, [(dsid, "2026-02", "0.5", 1, json.dumps(ids))])
    oid = db.derived_observations_of_run(run)[-1]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.finish_derived_run(run, "verified", T3, n_written=1, n_checked=1, n_mismatch=0)
    return run


def test_derived_reads_for_base_and_detail(db):
    _setup(db)
    _derived(db)
    rows = db.public_derived_for_base("s1")
    assert [(r["key"], r["unit"], r["latest_period"], r["latest_value_text"]) for r in rows] == \
        [(KEY, "pp", "2026-02", "0.5")]
    assert rows[0]["caveats"] == []
    detail = db.public_derived(KEY)
    assert detail["formula"] == "period_change" and detail["base_series_id"] == "s1"
    assert detail["served_count"] == 1 and detail["base_source"] == "fake"
    assert db.public_derived_values(KEY)[0]["value_text"] == "0.5"
    assert db.public_derived("nope") is None


# --- cross-checks and sources ----------------------------------------------------------------

def test_cross_checks_share_the_indicator_key(db):
    _setup(db)
    _verified(db, "s2", "2026-01", "1.50", T1, "k-cross")
    rows = db.public_cross_checks("s1")
    assert [(r["id"], r["source"], r["latest_value_text"]) for r in rows] == \
        [("s2", "fake", "1.50")]
    assert db.public_cross_checks("s2") == []


def test_sources_expose_licence_counts_and_withheld_state(db):
    _setup(db)
    rows = {r["name"]: r for r in db.public_sources()}
    assert rows["fake"]["redistribution_ok"] is True
    assert rows["fake"]["series"] == 1 and rows["fake"]["last_fetched_at"] == T1
    assert rows["closed"]["redistribution_ok"] is False
    assert rows["closed"]["series"] == 0 and rows["closed"]["last_fetched_at"] is None


def test_empty_database_is_quiet(db):
    assert db.public_counts() == {"series": 0, "sources": 0, "last_fetched_at": None}
    assert db.public_catalogue() == []
    assert db.public_latest_values(["s1"]) == {}
    assert db.public_series("s1") is None
    assert db.public_provenance("s1") is None
    assert db.public_revisions("s1") == ([], 0)
    assert db.public_derived("k") is None
    assert db.public_cross_checks("s1") == []


def test_recent_values_reads_the_tail_oldest_first(db):
    _setup(db)
    _verified(db, "s1", "2026-02", "2.0", T2, "k2026-02")
    _verified(db, "s1", "2026-03", "3.0", T3, "k2026-03")
    assert [(r["period"], r["value_text"]) for r in db.public_recent_values("s1", 2)] == \
        [("2026-02", "2.0"), ("2026-03", "3.0")]
    assert len(db.public_recent_values("s1", 1)) == 1
    assert db.public_recent_values("nope", 5) == []


def test_a_withdrawn_execution_never_publishes_legacy_rows(db):
    """`served_observation` lets legacy rows through when their source is scoped-allowed and no
    fetched row shadows them. Withdrawing the only execution would therefore put an unverified
    value on the site, so every public read filters `kind = 'fetched'` itself."""
    sync_registry(db, [_series(), _series("s2", role="cross_check")])
    db.conn.execute("INSERT OR REPLACE INTO setting(key, value) VALUES (?, '1')",
                    ("legacy_served_source:fake",))
    legacy = db.legacy_run("fake", "legacy:fake", T1)
    db.write_legacy_observations(legacy, [
        (Observation.from_raw("s1", "2026-01", "9.99"), T1),
        (Observation.from_raw("s2", "2026-01", "9.99"), T1),
    ])
    run = _verified(db, "s1", "2026-01", "1.50", T2, "k1")
    assert [r["value_text"] for r in db.public_series_values("s1")] == ["1.50"]

    db.withdraw_run(run, "test withdrawal", T3)
    # the view does serve the legacy rows now; the public layer must not
    assert [r[0] for r in db.conn.execute(
        "SELECT kind FROM served_observation WHERE series_id = 's1'")] == ["legacy-unverified"]
    assert db.public_series("s1") is None
    assert db.public_series_values("s1") == []
    assert db.public_recent_values("s1", 10) == []
    assert db.public_values_between("s1", "2026-01") == []
    assert db.public_day_counts("s1") == ()
    assert db.public_provenance("s1") is None
    assert db.public_latest_values(["s1"]) == {}
    assert db.public_catalogue() == []
    assert db.public_cross_checks("s1") == []
    assert db.public_counts()["series"] == 0
    assert db.public_revisions("s1") == ([], 0)


def test_a_calculated_series_on_a_withheld_base_is_refused(db):
    sync_registry(db, [_series("s3", source=CLOSED)])
    sync_derived(db, [derived_spec(KEY, "s3", "yoy_change")])
    _verified(db, "s3", "2026-01", "1.00", T1, "kc", source="closed")
    assert db.public_derived(KEY) is None
    assert db.public_derived_for_base("s3") == []
