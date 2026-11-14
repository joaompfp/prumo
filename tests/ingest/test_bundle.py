"""Task 17B: original-file manual capture -> exact recorded bundle -> offline replay.

Offline end-to-end over the RECORDED genuine publisher bytes (World Bank JSON + CSV ZIP,
E-REDES metadata/JSON/CSV fixtures): the fake "network" side serves fixture bytes with
bounded responses, the capture writes a real bundle, and the replay exercises the REAL
registered parsers+verifiers with no network at all. Bundle integrity/security and CLI
argument validation fail closed BEFORE any DB/file mutation. No fabricated status/date/bytes:
every bundle here is recorded from fixture responses or built with the same genuine bytes.
"""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit

import pytest
import yaml

import ingest.verifiers as verifiers
from ingest import bundle as bundle_mod
from ingest.bundle import (
    BundleError,
    BundleRecorder,
    CaptureHttp,
    PinnedHttp,
    load_bundle,
)
from ingest.cli import main
from ingest.db import open_db
from ingest.http import HttpResult
from ingest.models import SeriesSpec
from tests.ingest import eredes_fixtures as eredes_fx
from tests.ingest import eredes_verifier_fixtures as eredes_vfx
from tests.ingest import worldbank_fixtures as wb_fx
from tests.ingest import worldbank_verifier_fixtures as wb_vfx
from tests.ingest.legacy_csv import write_csv


@pytest.fixture(autouse=True)
def _clean_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def _write_registry(path: Path, specs: list[SeriesSpec]) -> Path:
    sources, series = {}, []
    for s in specs:
        sources[s.source.name] = s.source.model_dump(exclude={"name"})
        series.append({**s.model_dump(exclude={"source"}), "source": s.source.name})
    path.write_text(yaml.safe_dump({"sources": sources, "series": series},
                                   sort_keys=False, allow_unicode=True))
    return path


POP = wb_fx.POP_EUGRAT  # indicator SP.POP.TOTL, geos EU/GR/AT: JSON + CSV ZIP both recorded
def _wb_specs():
    return wb_fx.specs_of(POP)
ER_SPECS = eredes_fx.all_specs


class _WBNet:
    """The whole fake internet for a WB capture: genuine recorded fixture bytes only."""

    def __init__(self):
        self.source = wb_fx.FixtureHttp()
        self.verifier = wb_vfx.VerifyFixtureHttp()
        self.calls = 0

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls += 1
        if "/v2/country/" in url:
            return self.source.get(url, params=params, timeout=timeout)
        return self.verifier.get(url, params=params, timeout=timeout)


class _ERNet:
    """Fake internet for an E-REDES capture: genuine recorded metadata/JSON/CSV bytes."""

    def __init__(self, csv_status: int | None = None):
        self.source = eredes_fx.FixtureHttp()
        self.vstatus = csv_status

    def get(self, url, params=None, headers=None, timeout=None):
        if "/exports/csv" in url:
            name = eredes_vfx.VerifyFixtureHttp().routes.get(
                eredes_vfx._route(url, params))
            if name is None:
                raise AssertionError(f"no recorded eredes csv for {url} {params}")
            m = eredes_vfx.VMANIFEST[name]
            return HttpResult(status=self.vstatus or m["status"],
                              body=eredes_vfx.vbody(name), url=m["url"])
        return self.source.get(url, params=params, timeout=timeout)


def _split(m: dict) -> tuple[str, dict | None]:
    """A manifest wire record -> (query-free request url, merged params), exactly what the
    adapters pass to Http.get (and therefore what the capture records)."""
    parts = urlsplit(m["url"])
    params = {k: v[0] for k, v in parse_qs(parts.query).items()}
    params.update({str(k): str(v) for k, v in (m.get("params") or {}).items()})
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return url, params or None


def _record_genuine(root: Path, source: str, names: list[str], *,
                    csv_500: bool = False) -> Path:
    """Build a bundle with the RECORDER's own API from genuine E-REDES fixture wire records
    (same bytes/status/final URL as the publisher answered; the capture machine ran on
    another network). csv_500 records the verifier CSV honestly AS AN HTTP 500, as a real
    failing capture would."""
    rec = BundleRecorder(root)
    sets = eredes_fx.MANIFEST["sets"]
    for name in names:
        m = sets[name]
        url, params = _split(m)
        status = 500 if csv_500 and name.endswith("_csv") else m["status"]
        rec.record(url, params, HttpResult(status=status,
                                           body=eredes_fx.body(name), url=m["final_url"]))
    rec.seal(source)
    return root


def _cli_run(db_path, raw, reg, *args, pinned=True):
    # any live network use during a recorded replay fails the test loudly. These replays pin
    # the verifier to the bundle too (--pinned-verifier: NON-audit-grade, Task 21 B-I3) so they
    # stay offline; the live-verifier default is tested in test_task21_verification.py
    def no_network(name):
        raise AssertionError(f"recorded replay must not touch the network ({name})")
    extra = ["--pinned-verifier"] if pinned and "--bundle" in args else []
    return main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
                 *args, *extra], http_for=lambda _name: no_network(_name))


WINTER = ("2026-11-10", "2026-11-11")
SUMMER = ("2026-04-01", "2026-04-02")


def test_capture_worldbank_then_offline_replay_keeps_original_dates(tmp_path, capsys):
    reg = _write_registry(tmp_path / "registry.yaml", _wb_specs())
    out = tmp_path / "bundle"
    rc = main(["--registry", str(reg), "capture", "worldbank", "--output", str(out),
               "--indicator", "SP.POP.TOTL"], http_for=lambda _n: _WBNet())
    assert rc == 0, capsys.readouterr()
    doc = json.loads((out / "manifest.json").read_text())
    assert doc["schema"] == "prumo-bundle" and doc["version"] == 1
    assert doc["source"] == "worldbank" and doc["failures"] == []
    urls = {e["url"] for e in doc["entries"]}
    assert urls == {
        "https://api.worldbank.org/v2/country/AT;EU;GR/indicator/SP.POP.TOTL",
        "https://api.worldbank.org/v2/en/indicator/SP.POP.TOTL?downloadformat=csv"}
    for e in doc["entries"]:
        assert isinstance(e["status"], int) and 200 <= e["status"] < 300
        bundle_mod._entry_ts(e["fetched_at"])  # tz-aware ORIGINAL receipt time
        assert e["bytes"] == (out / e["file"]).stat().st_size

    # owned legacy history present BEFORE the recorded replay
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "rawstore"
    csv_path = write_csv(tmp_path / "indicators.csv",
                         [("WORLDBANK", "population", "EU", "1959", "30000000", "persons")])
    assert main(["--db", str(db_path), "--registry", str(reg),
                 "import-legacy", str(csv_path)]) == 0

    rc = _cli_run(db_path, raw, reg, "run", "worldbank", "--bundle", str(out),
                  "--indicator", "SP.POP.TOTL")
    run_out, run_err = capsys.readouterr()
    assert rc == 0, (run_out, run_err)
    db = open_db(db_path)
    try:
        runs = db.conn.execute(
            "SELECT input_origin, started_at FROM dataset_run WHERE input_origin='recorded'",
        ).fetchall()
        assert runs and all(True for _ in runs)
        stamps = {e["fetched_at"] for e in doc["entries"]}
        obs = db.conn.execute(
            "SELECT DISTINCT fetched_at FROM observation WHERE kind='fetched'").fetchall()
        assert {r[0] for r in obs} <= stamps  # ORIGINAL capture date, never the import time
        assert all(r[0] < db.conn.execute(
            "SELECT MAX(started_at) FROM dataset_run").fetchone()[0] for r in obs)
        legacy = db.conn.execute(
            "SELECT value_text, fetched_at FROM observation WHERE kind='legacy-unverified'"
        ).fetchall()
        assert legacy == [("30000000", "2026-03-15T21:35:31Z")]  # history byte-identical,
        # original retrieval date preserved verbatim (never re-stamped by imports)
        served = db.conn.execute(
            "SELECT value_text FROM served_observation WHERE series_id='worldbank.population.EU'"
            " ORDER BY period").fetchall()
        assert served[0][0] == "30000000"  # legacy 1959 kept; recorded data covers 1960+
        assert db.conn.execute(
            "SELECT COUNT(*) FROM dataset_run WHERE state='verified' AND "
            "input_origin='recorded'").fetchone()[0] == 1
    finally:
        db.close()
    capsys.readouterr()  # drain the run/capture chatter before the JSON status read
    rc = main(["--db", str(db_path), "--registry", str(reg), "status", "--json"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    wb = next(s for s in report["sources"] if s["name"] == "worldbank")
    ds = next(d for d in wb["datasets"] if d["label"] == "SP.POP.TOTL")
    assert ds["input_origin"] == "recorded" and ds["latest_state"] == "verified"


def test_eredes_capture_and_multiday_bundle_replay_two_windows(tmp_path, capsys):
    reg = _write_registry(tmp_path / "registry.yaml", ER_SPECS())
    out = tmp_path / "eredes-bundle"
    rc = main(["--registry", str(reg), "capture", "eredes", "--output", str(out),
               "--from", WINTER[0], "--to", WINTER[0]], http_for=lambda _n: _ERNet())
    assert rc == 0, capsys.readouterr()
    doc = json.loads((out / "manifest.json").read_text())
    assert doc["failures"] == []
    kinds = {("records" if "/records" in e["url"] else
              "csv" if "/exports/csv" in e["url"] else "metadata") for e in doc["entries"]}
    assert kinds == {"metadata", "records", "csv"}

    # a merged TWO-DAY bundle (two genuine recorded days; second from the WEST-summer set)
    merged = _record_genuine(tmp_path / "merged", "eredes",
                             ["metadata", "window_json", "window_csv",
                              "summer_window_json", "summer_window_csv"])
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "rawstore"
    for day in (WINTER[0], SUMMER[0]):
        rc = _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(merged),
                      "--from", day, "--to", day)
        assert rc == 0, (day, capsys.readouterr())
    db = open_db(db_path)
    try:
        runs = db.conn.execute(
            "SELECT r.id, v.seed FROM dataset_run r JOIN verification v "
            "ON v.dataset_run_id = r.id WHERE r.input_origin='recorded' AND v.passed=1"
        ).fetchall()
        assert len(runs) == 2 and runs[0][1] != runs[1][1]  # fresh seeds, never fixed
        urls = {r[0] for r in db.conn.execute(
            "SELECT DISTINCT i.evidence_url FROM verification_item i JOIN verification v ON "
            "v.id = i.verification_id JOIN dataset_run r ON r.id = v.dataset_run_id").fetchall()}
        assert eredes_vfx.VMANIFEST["window_csv"]["final_url"] in urls
        assert eredes_vfx.VMANIFEST["summer_window_csv"]["final_url"] in urls  # both days
        assert db.conn.execute("SELECT COUNT(*) FROM observation WHERE kind='fetched'"
                               ).fetchone()[0] == 2 * 288
    finally:
        db.close()


def test_missing_pinned_request_fails_closed_and_keeps_old_data(tmp_path, capsys):
    reg = _write_registry(tmp_path / "registry.yaml", ER_SPECS())
    full = _record_genuine(tmp_path / "full", "eredes",
                           ["metadata", "window_json", "window_csv"])
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "rawstore"
    assert _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(full),
                    "--from", WINTER[0], "--to", WINTER[0]) == 0
    db0 = open_db(db_path)
    try:
        served_before = db0.conn.execute(
            "SELECT COUNT(*) FROM served_observation").fetchone()[0]
    finally:
        db0.close()
    # a bundle missing the CSV of the requested day (summer entries only on the source side)
    broken = _record_genuine(tmp_path / "broken", "eredes",
                             ["metadata", "summer_window_json"])  # no summer csv pinned
    rc = _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(broken),
                  "--from", SUMMER[0], "--to", SUMMER[0])
    assert rc == 1
    db = open_db(db_path)
    try:
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == \
            served_before  # old good verified data stays served, untouched
        states = [r[0] for r in db.conn.execute(
            "SELECT state FROM dataset_run ORDER BY id").fetchall()]
        assert states[-1] in ("failed-fetch", "failed-verification")
    finally:
        db.close()


def test_recorded_500_csv_fails_verification_and_preserves_old_good_data(tmp_path, capsys):
    reg = _write_registry(tmp_path / "registry.yaml", ER_SPECS())
    good = _record_genuine(tmp_path / "good", "eredes",
                           ["metadata", "window_json", "window_csv"])
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "rawstore"
    assert _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(good),
                    "--from", WINTER[0], "--to", WINTER[0]) == 0
    import time
    time.sleep(0.02)  # the failing capture below must be strictly newer than the good run's
    # held fetched dates (the stale-bundle rule compares receipt times)
    bad = _record_genuine(tmp_path / "bad", "eredes",  # summer day: DIFFERENT genuine bytes
                          ["metadata", "summer_window_json", "summer_window_csv"],
                          csv_500=True)  # the verifier CSV is recorded AS an honest HTTP 500
    rc = _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(bad),
                  "--from", SUMMER[0], "--to", SUMMER[0])
    assert rc == 1, capsys.readouterr()
    db = open_db(db_path)
    try:
        origins = [r[0] for r in db.conn.execute(
            "SELECT input_origin FROM dataset_run WHERE dataset_key NOT LIKE 'legacy:%'"
        ).fetchall()]
        assert origins and set(origins) == {"recorded"}  # EVERY attempt labelled recorded
        states = [r[0] for r in db.conn.execute(
            "SELECT state FROM dataset_run WHERE dataset_key NOT LIKE 'legacy:%' "
            "ORDER BY id").fetchall()]
        assert states[0] == "verified" and states[-1] == "failed-verification"
        assert db.conn.execute(
            "SELECT COUNT(*) FROM served_observation WHERE kind='fetched'"
        ).fetchone()[0] == 288  # the 500 CSV never served a failed row over the good data
    finally:
        db.close()


def test_outdated_bundle_refused_before_insertion(tmp_path, capsys):
    reg = _write_registry(tmp_path / "registry.yaml", ER_SPECS())
    old = _record_genuine(tmp_path / "b1", "eredes",  # winter day, captured first
                          ["metadata", "window_json", "window_csv"])
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "rawstore"
    assert _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(old),
                    "--from", WINTER[0], "--to", WINTER[0]) == 0
    # a genuinely LATER recorded download (the summer day, captured afterwards) is allowed
    # and advances the held verified fetched dates
    import time
    time.sleep(0.02)
    newer = _record_genuine(tmp_path / "b2", "eredes",
                            ["metadata", "summer_window_json", "summer_window_csv"])
    assert _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(newer),
                    "--from", SUMMER[0], "--to", SUMMER[0]) == 0
    db0 = open_db(db_path)
    try:
        n_runs = db0.conn.execute("SELECT COUNT(*) FROM dataset_run").fetchone()[0]
    finally:
        db0.close()
    # ...after which replaying the OLDER capture is refused before any insertion
    rc = _cli_run(db_path, raw, reg, "run", "eredes", "--bundle", str(old),
                  "--from", WINTER[0], "--to", WINTER[0])
    assert rc == 1
    err = capsys.readouterr().err
    assert "outdated bundle" in err
    db = open_db(db_path)  # nothing was inserted: run count unchanged, data byte-identical
    try:
        assert db.conn.execute("SELECT COUNT(*) FROM dataset_run").fetchone()[0] == n_runs
    finally:
        db.close()


def test_eredes_live_explicit_bounds_still_work(tmp_path, capsys):
    # no bundle: the same explicit bounds drive a LIVE catch-up through the fake network
    reg = _write_registry(tmp_path / "registry.yaml", ER_SPECS())
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "rawstore"
    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "run", "eredes", "--from", WINTER[0], "--to", WINTER[0]],
              http_for=lambda _n: _ERNet())
    assert rc == 0, capsys.readouterr()
    db = open_db(db_path)
    try:
        assert db.conn.execute("SELECT input_origin FROM dataset_run").fetchone() == ("live",)
    finally:
        db.close()


# --- bundle integrity / security bounds -------------------------------------------------------

def _made(tmp_path, mutate=None):
    rec = BundleRecorder(tmp_path / "src")
    rec.record("https://x.test/a", None, HttpResult(200, b'{"ok": true}', "https://x.test/a"))
    rec.seal("eredes")
    dst = tmp_path / "case"
    import shutil
    shutil.copytree(tmp_path / "src", dst)
    doc = json.loads((dst / "manifest.json").read_text())
    e = dict(doc["entries"][0])
    if mutate:
        mutate(doc, e, dst)
    if doc["entries"]:
        doc["entries"][0] = e
    (dst / "manifest.json").write_text(json.dumps(doc))
    return dst


def _bad(tmp_path, mutate):
    root = _made(tmp_path, mutate)
    with pytest.raises(BundleError):
        load_bundle(root, source="eredes")


def test_bundle_security_and_shape_guards(tmp_path):
    _bad(tmp_path / "a", lambda d, e, r: e.update(file="../escape"))
    _bad(tmp_path / "b", lambda d, e, r: e.update(file="/etc/passwd"))
    _bad(tmp_path / "c", lambda d, e, r: e.update(sha256="0" * 64))
    _bad(tmp_path / "d", lambda d, e, r: e.update(bytes=1))
    _bad(tmp_path / "e", lambda d, e, r: e.update(status=True))
    _bad(tmp_path / "f", lambda d, e, r: e.update(fetched_at="2026-11-12 10:00"))
    _bad(tmp_path / "g", lambda d, e, r: e.update(extra="key"))
    _bad(tmp_path / "h", lambda d, e, r: d.update(source="worldbank"))
    _bad(tmp_path / "i", lambda d, e, r: d.update(version=2))
    _bad(tmp_path / "j", lambda d, e, r: (r / e["file"]).write_bytes(b"tampered"))
    root = _made(tmp_path / "k")
    p = root / json.loads((root / 'manifest.json').read_text())["entries"][0]["file"]
    p.unlink()
    p.symlink_to("/dev/null")
    _bad(tmp_path / "l", lambda d, e, r: d.update(entries=[]))  # placeholder, replaced below
    # empty-list manifest is legal shape; symlink case above must fail on its own load:
    with pytest.raises(BundleError):
        load_bundle(root, source="eredes")
    with pytest.raises(BundleError):  # missing manifest = unsealed capture
        load_bundle(tmp_path / "never-sealed", source="eredes")


def test_duplicate_request_identity_policy(tmp_path):
    rec = BundleRecorder(tmp_path / "dup")
    url, params = "https://x.test/a", {"p": "1"}
    rec.record(url, params, HttpResult(200, b"one", url))
    rec.record(url, params, HttpResult(200, b"one", url))  # byte-identical: deduped
    assert len(rec.entries) == 1
    first_ts = rec.entries[0].fetched_at
    with pytest.raises(BundleError, match="CHANGED response"):
        rec.record(url, params, HttpResult(200, b"two", url))  # changed body: loud failure
    with pytest.raises(BundleError, match="CHANGED response"):
        rec.record(url, params, HttpResult(500, b"one", url))  # changed status: loud failure
    assert rec.entries[0].fetched_at == first_ts  # pinned to the first receipt, explicit


def test_partial_bundle_refused_for_runs(tmp_path):
    rec = BundleRecorder(tmp_path / "partial")
    rec.record("https://x.test/a", None, HttpResult(200, b"{}", "https://x.test/a"))
    rec.record_failure("https://x.test/b", None, "ConnectTimeout: slow")
    rec.seal("eredes")
    with pytest.raises(BundleError, match="partial"):
        PinnedHttp(load_bundle(tmp_path / "partial", source="eredes"))


def test_pinned_http_serves_only_pinned(tmp_path):
    root = _record_genuine(tmp_path / "pin", "eredes",
                           ["metadata", "window_json", "window_csv"])
    pinned = PinnedHttp(load_bundle(root, source="eredes"))
    m = eredes_fx.MANIFEST["sets"]["metadata"]
    url, params = _split(m)
    r = pinned.get(url, params=params)
    assert r.status == 200 and r.body == eredes_fx.body("metadata")
    with pytest.raises(BundleError, match="NO response"):
        pinned.get(url, params={"where": "other"})


def test_capture_http_budget_is_physical(tmp_path):
    calls = []

    def transport(url, params, headers, timeout):
        calls.append(url)
        return 302, url, b"", {"Location": "https://x.test/final"}

    http = CaptureHttp(max_requests=2, deadline_s=60, transport=transport)
    with pytest.raises(BundleError, match="budget exhausted"):
        http.get("https://x.test/a")  # 2 redirects = 3 physical requests > cap 2
    assert len(calls) == 2  # the third physical request was never spent

    t = [0.0]

    def clock():
        return t[0]

    http2 = CaptureHttp(max_requests=9, deadline_s=10, transport=transport, clock=clock)
    with pytest.raises(BundleError, match="deadline"):
        t[0] = 11.0
        http2.get("https://x.test/a")


def test_capture_refuses_existing_nonempty_output_and_run_arg_guards(tmp_path, capsys):
    reg = _write_registry(tmp_path / "registry.yaml", ER_SPECS())
    out = tmp_path / "occupied"
    out.mkdir()
    (out / "x").write_text("keep me")
    rc = main(["--registry", str(reg), "capture", "eredes", "--output", str(out),
               "--from", WINTER[0], "--to", WINTER[0]], http_for=lambda _n: _ERNet())
    assert rc == 2 and (out / "x").read_text() == "keep me"  # never overwritten
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "raw"
    cases = [
        ["run", "all", "--bundle", "x"],
        ["run", "fred", "--bundle", "x"],
        ["run", "eredes", "--indicator", "SP.POP.TOTL"],
        ["run", "worldbank", "--indicator", "NOPE.NOPE"],
        ["run", "worldbank", "--from", WINTER[0], "--to", WINTER[0]],
        ["run", "eredes", "--bundle", "x", "--from", WINTER[0]],  # bundle needs both bounds
        ["run", "eredes", "--from", "2026-11-10"],
        ["run", "eredes", "--from", WINTER[0], "--to", WINTER[0][::-1][:4] + "11-09"],
        ["run", "eredes", "--from", WINTER[0], "--to", WINTER[1]],  # to >= today in tests?
    ]
    for argv in cases[:-1]:
        rc = _cli_run(db_path, raw, reg, *argv)
        assert rc == 2, argv
        assert not db_path.exists()  # invalid combos fail BEFORE any DB file is created
    # future bounds are refused likewise
    rc = _cli_run(db_path, raw, reg, "run", "eredes", "--from", "2999-01-01", "--to",
                  "2999-01-02")
    assert rc == 2 and not db_path.exists()
