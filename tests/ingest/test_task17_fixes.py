"""Task 17 independent-review FIXES (R1-R4 regressions; R5 is the manual-refresh doc).

R1 continuity: a recorded bundle whose ORIGINAL collector receipts for a dataset group are
OLDER than the verified fetched data already held for that group must be refused PER GROUP
(preflight: before sync_registry AND before any observation insertion) and guarded
ATOMICALLY inside the observation write transaction (a concurrent newer writer cannot race
the CLI precheck); healthy independent groups of the same bundle still import.
R2: pending-verification runs are attributed by their OWN source, so historical dataset keys
    and sources missing from the current registry stay visible; zero pending ids discarded.
R3: HTTP-client construction and grouping failures for one source never abort run all.
R4: the capture deadline is a REAL wall-clock bound: the per-request timeout is clamped to
    the remaining phase budget, a late response is rejected instead of returned, and a
    stalled server is killed at the deadline (killable worker subprocess), with the body cap
    enforced WHILE streaming, not after an unbounded read.

World Bank flows use the recorded genuine publisher fixtures (JSON + CSV ZIP) only; E-REDES
flows use the recorded genuine winter window. No network beyond loopback stalls (R4), and no
fabricated bytes/statuses anywhere.
"""
import json
import re
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import ingest.verifiers as verifiers
from ingest import bundle as bundle_mod
from ingest.bundle import BundleError, CaptureHttp, PinnedHttp, RecordedSource, load_bundle
from ingest.cli import main
from ingest.db import open_db
from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec
from ingest.operations import RunRequest, group_specs, run_all
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.eredes import EredesSource
from ingest.status import build_status
from tests.ingest import eredes_fixtures as eredes_fx
from tests.ingest import eredes_verifier_fixtures as eredes_vfx
from tests.ingest import worldbank_fixtures as wb_fx
from tests.ingest import worldbank_verifier_fixtures as wb_vfx

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
# the recorded genuine eredes fixtures cover one UTC day per window
WINTER_DAY, SUMMER_DAY = "2026-11-10", "2026-04-01"
WINTER_WINDOW = (f"{WINTER_DAY}T00:00:00+00:00", "2026-11-11T00:00:00+00:00")
SUMMER_WINDOW = (f"{SUMMER_DAY}T00:00:00+00:00", "2026-04-02T00:00:00+00:00")


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


def _wb_specs():
    return wb_fx.specs_of(wb_fx.GDP_PTDES + wb_fx.POP_EUGRAT)


def _pop_specs():
    return wb_fx.specs_of(wb_fx.POP_EUGRAT)


class _WBNet:
    """The whole fake internet for a WB capture/replay: genuine recorded fixture bytes."""

    def __init__(self):
        self.source = wb_fx.FixtureHttp()
        self.verifier = wb_vfx.VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "/v2/country/" in url:
            return self.source.get(url, params=params, headers=headers, timeout=timeout)
        return self.verifier.get(url, params=params, headers=headers, timeout=timeout)


class _ERNet:
    """Fake internet for E-REDES: genuine recorded metadata/JSON/CSV winter bytes."""

    def __init__(self):
        self.source = eredes_fx.FixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "/exports/csv" in url:
            name = eredes_vfx.VerifyFixtureHttp().routes.get(
                eredes_vfx._route(url, params))
            if name is None:
                raise AssertionError(f"no recorded eredes csv for {url} {params}")
            m = eredes_vfx.VMANIFEST[name]
            return HttpResult(status=m["status"], body=eredes_vfx.vbody(name),
                              url=m["url"])
        return self.source.get(url, params=params, timeout=timeout)


def _no_network(name):
    raise AssertionError(f"recorded replay must not touch the network ({name})")


def _run_bundle(db_path, raw, reg, bundle_dir, *extra):
    return main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
                 "run", "worldbank", "--bundle", str(bundle_dir), *extra],
                http_for=_no_network)


def _obs_stats(db_path, like):
    db = open_db(db_path)
    try:
        return db.conn.execute(
            "SELECT COUNT(*), MAX(fetched_at) FROM observation WHERE series_id LIKE ?",
            (like,)).fetchone()
    finally:
        db.close()


# --- R1: per-group stale-bundle continuity -------------------------------------------------

def test_mixed_bundle_refuses_only_the_stale_group(tmp_path, capsys):
    """A full bundle captured BEFORE a separate fresher indicator replay must not displace
    that newer verified data; the unrelated healthy group of the same bundle still imports,
    and a same-time re-import is an idempotent no-op."""
    reg = _write_registry(tmp_path / "registry.yaml", _wb_specs())
    full, pop = tmp_path / "full", tmp_path / "pop"

    def cap(out, *extra):
        return main(["--registry", str(reg), "capture", "worldbank",
                     "--output", str(out), *extra], http_for=lambda _n: _WBNet())

    assert cap(full) == 0                     # T1: BOTH indicators, genuine flow
    time.sleep(0.02)
    assert cap(pop, "--indicator", "SP.POP.TOTL") == 0   # T2: separate FRESHER capture
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "raw"
    assert _run_bundle(db_path, raw, reg, pop, "--indicator", "SP.POP.TOTL") == 0
    pop_held = _obs_stats(db_path, "worldbank.population.%")
    assert pop_held[0] > 0

    # T3: replay the OLDER full bundle: the POP group is stale (receipts T1 < held T2) and
    # is refused with a per-group diagnosis; the GDP group has nothing held and imports.
    rc = _run_bundle(db_path, raw, reg, full)
    out, err = capsys.readouterr()
    assert rc == 1
    assert "refusing an outdated bundle" in err and "SP.POP.TOTL" in err
    assert re.search(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", err)  # the diagnosis carries dates
    assert "SP.POP.TOTL: blocked" in out
    assert "NY.GDP.MKTP.CD: verified" in out
    assert _obs_stats(db_path, "worldbank.population.%") == pop_held  # never displaced
    assert _obs_stats(db_path, "worldbank.gdp_usd.%")[0] > 0          # healthy group ran

    # idempotence: replaying the SAME fresher bundle again is a verified no-op
    assert _run_bundle(db_path, raw, reg, pop, "--indicator", "SP.POP.TOTL") == 0
    assert _obs_stats(db_path, "worldbank.population.%") == pop_held


def test_fully_stale_bundle_refused_before_sync_registry(tmp_path, capsys):
    """Every selected group stale -> the whole replay is refused BEFORE sync_registry: no new
    run rows, and the registry metadata change staged in the YAML never reaches the DB."""
    reg = _write_registry(tmp_path / "registry.yaml", _wb_specs())
    full, pop, gdp = tmp_path / "full", tmp_path / "pop", tmp_path / "gdp"

    def cap(out, *extra):
        return main(["--registry", str(reg), "capture", "worldbank",
                     "--output", str(out), *extra], http_for=lambda _n: _WBNet())

    assert cap(full) == 0                                 # T1: both indicators, OLD receipts
    time.sleep(0.02)
    assert cap(pop, "--indicator", "SP.POP.TOTL") == 0    # T2
    time.sleep(0.02)
    assert cap(gdp, "--indicator", "NY.GDP.MKTP.CD") == 0  # T3
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "raw"
    assert _run_bundle(db_path, raw, reg, pop, "--indicator", "SP.POP.TOTL") == 0
    assert _run_bundle(db_path, raw, reg, gdp, "--indicator", "NY.GDP.MKTP.CD") == 0
    db = open_db(db_path)
    try:
        n_runs = db.conn.execute("SELECT COUNT(*) FROM dataset_run").fetchone()[0]
    finally:
        db.close()
    doc = yaml.safe_load(reg.read_text())
    doc["sources"]["worldbank"]["attribution"] = "CHANGED-ATTRIBUTION"
    reg.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    capsys.readouterr()  # drain the capture/replay output of the setup steps
    rc = _run_bundle(db_path, raw, reg, full)
    out, err = capsys.readouterr()
    assert rc == 1
    assert err.count("refusing an outdated bundle for dataset group") == 2
    assert "SP.POP.TOTL" in err and "NY.GDP.MKTP.CD" in err
    assert "verified" not in out
    db = open_db(db_path)
    try:
        assert db.conn.execute("SELECT COUNT(*) FROM dataset_run").fetchone()[0] == n_runs
        assert db.conn.execute("SELECT attribution FROM source WHERE name='worldbank'"
                               ).fetchone()[0] != "CHANGED-ATTRIBUTION"
    finally:
        db.close()


def test_atomic_stale_guard_inside_observation_transaction(tmp_path):
    """Below the CLI preflight (a concurrent newer writer could race it): run_dataset in
    recorded mode must refuse OLD recorded receipts INSIDE the write transaction, leaving
    held verified rows byte-identical and the run honestly terminal ('blocked-stale')."""
    # E-REDES gives two genuinely DIFFERENT payloads of the same dataset (one winter day,
    # one summer day), so the identical-payload short-circuit cannot mask the guard.
    reg = _write_registry(tmp_path / "registry.yaml", eredes_fx.all_specs())
    winter_b, summer_b = tmp_path / "winter", tmp_path / "summer"

    def cap(out, day):
        return main(["--registry", str(reg), "capture", "eredes",
                     "--output", str(out), "--from", day, "--to", day],
                    http_for=lambda _n: _ERNet())

    assert cap(winter_b, WINTER_DAY) == 0        # T1: OLDER receipts
    time.sleep(0.02)
    assert cap(summer_b, SUMMER_DAY) == 0        # T2: fresher capture, different payload
    db_path, raw = tmp_path / "p.sqlite3", tmp_path / "raw"
    assert main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
                 "run", "eredes", "--bundle", str(summer_b),
                 "--from", SUMMER_DAY, "--to", SUMMER_DAY], http_for=_no_network) == 0

    bundle = load_bundle(winter_b, source="eredes")
    pinned = PinnedHttp(bundle)  # the OLDER (T1) receipts, driven DIRECTLY (no preflight)
    specs = [s for s in eredes_fx.all_specs() if s.active]
    recorded = RecordedSource(EredesSource(*WINTER_WINDOW), pinned)
    db = open_db(db_path)
    try:
        before = db.conn.execute(
            "SELECT COUNT(*), MAX(fetched_at) FROM observation").fetchone()
        res = run_dataset(db, RawStore(raw), recorded, specs, pinned,
                          input_origin="recorded")
        assert res.state == "blocked-stale"
        assert res.n_written == 0
        assert db.run_state(res.run_id) == "blocked-stale"
        assert db.conn.execute("SELECT COUNT(*), MAX(fetched_at) FROM observation"
                               ).fetchone() == before
        kinds = [r[0] for r in db.conn.execute(
            "SELECT kind FROM event WHERE dataset_run_id = ?", (res.run_id,))]
        assert "stale_refusal" in kinds
        # the served view still serves the NEWER (T2) verified rows
        served_t = db.conn.execute(
            "SELECT DISTINCT fetched_at FROM served_observation").fetchall()
        assert len(served_t) == 1 and served_t[0][0] == before[1]
    finally:
        db.close()


# --- R2: pending runs keep their own source -------------------------------------------------

WB_SRC = SourceSpec(name="worldbank", licence="CC BY 4.0", licence_url="http://l",
                    attribution="WB", redistribution_ok=True, verifiable=True)


def _wb(sid: str, code: str) -> SeriesSpec:
    return SeriesSpec(id=sid, source=WB_SRC, indicator_key=f"{code}.{sid}", role="primary",
                      theme="economy", geography="PT", frequency="A", unit="u",
                      native_code=f"{code}:PRT", active=True)


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def test_pending_runs_stay_visible_under_their_own_source(db):
    spec = _wb("worldbank.gdp.PT", "NY.GDP.MKTP.KD.ZG")
    sync_registry(db, [spec])
    current_key = group_specs([spec])[0].key()
    mapped = db.begin_run("worldbank", current_key, _ts(NOW - timedelta(hours=2)),
                          input_origin="live")
    # a pre-17A source-wide key NOT derivable from today's per-indicator grouping
    unmapped = db.begin_run("worldbank", "worldbank:0ldgr0up", _ts(NOW - timedelta(hours=25)),
                            input_origin="recorded")
    # a source present only in DB rows, absent from the current registry
    db.upsert_source_and_series(
        [{"name": "oldschool", "licence": "L", "licence_url": "", "attribution": "",
          "redistribution_ok": False}], [])
    foreign = db.begin_run("oldschool", "oldschool:k", _ts(NOW - timedelta(hours=26)))
    for run in (mapped, unmapped, foreign):
        db.set_run_state(run, "pending-verification")

    report = build_status(db, [spec], now=lambda: NOW)
    seen = [(s.name, p.run_id) for s in report.sources for p in s.pending_runs]
    assert sorted(run for _n, run in seen) == sorted([mapped, unmapped, foreign])
    assert len(seen) == len({r for _n, r in seen})  # every pending run appears exactly once
    wb = next(s for s in report.sources if s.name == "worldbank")
    got = {p.run_id: p for p in wb.pending_runs}
    assert got[mapped].dataset == "NY.GDP.MKTP.KD.ZG" and got[mapped].stale is False
    assert got[unmapped].dataset == "worldbank:0ldgr0up"  # the historical key stays listed
    assert got[unmapped].stale is True and got[unmapped].input_origin == "recorded"
    assert got[unmapped].source == "worldbank" == got[mapped].source
    old = next(s for s in report.sources if s.name == "oldschool")
    assert [p.run_id for p in old.pending_runs] == [foreign]
    doc = json.loads(report.to_json())  # JSON v1: additive 'source' field on pending runs
    pending_docs = [p for s in doc["sources"] for p in s["pending_runs"]]
    assert {p["source"] for p in pending_docs} == {"worldbank", "oldschool"}


# --- R3: run all continues past per-source setup failures ------------------------------------

def test_run_all_continues_when_http_client_construction_fails(db, tmp_path):
    specs = [*_wb_specs(), *eredes_fx.all_specs()]
    sync_registry(db, specs)

    def factory(name):  # 'eredes' sorts first: its failure must not abort 'worldbank'
        if name == "eredes":
            raise RuntimeError("boom:eredes")
        return _WBNet()

    report = run_all(db, RawStore(tmp_path / "raw"), specs, http_for=factory,
                     request=RunRequest(window=WINTER_WINDOW))
    by_source = report.by_source()
    er = by_source["eredes"][0]
    assert er.state == "blocked" and "boom:eredes" in er.detail
    assert [o.state for o in by_source["worldbank"]] == ["verified", "verified"]
    assert report.exit_code() == 1


def test_run_all_continues_when_one_sources_grouping_is_broken(db, tmp_path):
    bad = SeriesSpec(id="worldbank.broken.PT", source=WB_SRC, indicator_key="broken.PT.A",
                     role="primary", theme="economy", geography="PT", frequency="A",
                     unit="u", native_code="NO-COLON-HERE", active=True)
    specs = [bad, *eredes_fx.all_specs()]
    sync_registry(db, specs)
    report = run_all(db, RawStore(tmp_path / "raw"), specs,
                     http_for=lambda _n: _ERNet(),
                     request=RunRequest(window=WINTER_WINDOW))
    wb = report.by_source()["worldbank"][0]
    assert wb.state == "blocked" and "grouping" in wb.detail
    assert all(o.state == "verified" for o in report.by_source()["eredes"])


# --- R4: the capture deadline is a real wall-clock bound --------------------------------------

def test_capture_timeout_is_clamped_to_the_remaining_deadline():
    seen = []
    t = [0.0]

    def transport(url, params, headers, timeout):
        seen.append(timeout)
        return 200, url, b"ok", {}

    http = CaptureHttp(timeout=30.0, max_requests=9, deadline_s=12.0, transport=transport,
                       clock=lambda: t[0])
    http.get("https://x.test/a")
    assert seen == [12.0]            # the transport only ever gets the remaining budget
    t[0] = 5.0
    http.get("https://x.test/b")
    assert seen[-1] == 7.0


def test_capture_rejects_a_response_arriving_past_the_deadline():
    t = [0.0]

    def transport(url, params, headers, timeout):
        t[0] = 31.0                  # consumed past the phase deadline (fake clock)
        return 200, url, b"late", {}

    http = CaptureHttp(timeout=30.0, max_requests=9, deadline_s=12.0, transport=transport,
                       clock=lambda: t[0])
    with pytest.raises(BundleError, match="deadline"):
        http.get("https://x.test/a")
    assert http.n_requests == 1      # spent, but the late body was never returned


def _socket_server(handler):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    thread = threading.Thread(target=handler, args=(srv,), daemon=True)
    thread.start()
    return srv


def test_capture_kills_a_stalled_server_at_the_real_deadline():
    """Wall-clock bound on the physical request: a server that accepts and never answers is
    KILLED near the deadline instead of holding the phase for the full client timeout."""

    def stall(srv):
        conn, _ = srv.accept()
        try:
            conn.recv(4096)
            time.sleep(60)  # never answers
        finally:
            conn.close()

    srv = _socket_server(stall)
    try:
        http = CaptureHttp(timeout=30.0, max_requests=4, deadline_s=1.5)
        t0 = time.monotonic()
        with pytest.raises(BundleError, match="deadline"):
            http.get(f"http://127.0.0.1:{srv.getsockname()[1]}/x")
        assert time.monotonic() - t0 < 20  # genuinely killed, not a 30s client timeout
    finally:
        srv.close()


def test_capture_body_cap_is_enforced_while_streaming(monkeypatch):
    monkeypatch.setattr(bundle_mod, "MAX_ENTRY_BYTES", 4096)

    def big(srv):
        conn, _ = srv.accept()
        try:
            conn.recv(4096)
            body = b"x" * (8192 + 1)
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode()
                         + b"\r\nConnection: close\r\n\r\n" + body)
            time.sleep(0.1)
        finally:
            conn.close()

    srv = _socket_server(big)
    try:
        http = CaptureHttp(timeout=10.0, max_requests=4, deadline_s=30.0)
        with pytest.raises(BundleError, match="cap"):
            http.get(f"http://127.0.0.1:{srv.getsockname()[1]}/x")
    finally:
        srv.close()


def test_capture_with_every_request_failing_still_seals_an_honest_manifest(tmp_path, capsys):
    """A fully failed capture (e.g. the deadline kills the first request) must STILL seal the
    honest failure receipts: no traceback, rc 1, manifest on disk, entries empty."""
    reg = _write_registry(tmp_path / "registry.yaml", eredes_fx.all_specs())
    out = tmp_path / "eredes-dead"

    class DeadNet:
        def get(self, *args, **kwargs):
            raise OSError("no route to host")

    rc = main(["--registry", str(reg), "capture", "eredes", "--output", str(out),
               "--from", WINTER_DAY, "--to", WINTER_DAY], http_for=lambda _n: DeadNet())
    assert rc == 1
    err = capsys.readouterr().err
    assert "capture INCOMPLETE" in err
    doc = json.loads((out / "manifest.json").read_text())
    assert doc["entries"] == [] and doc["failures"]  # the failure receipts are not lost
    assert "OSError" in doc["failures"][0]["error"]
