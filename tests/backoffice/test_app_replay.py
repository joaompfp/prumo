"""Backoffice v1, Task 5: replay one stored verification item from the browser.

Uses a real recorded Banco de Portugal run (tests/ingest/bportugal_fixtures) verified by the
real BPortugalVerifier, and the app's production verifier wiring
(ingest.operations.ensure_verifier / VERIFIER_OPS, the same path `ingest verify` uses)."""
import hashlib
import os
import re
import stat
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import ingest.verifiers as verifiers
from backoffice.app import create_app
from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sampling import SamplingPolicy
from ingest.sources.bportugal import BPortugalSource
from ingest.verifiers.bportugal import BPortugalVerifier
from ingest.verify import verify_run
from tests.ingest.bportugal_fixtures import FixtureHttp, all_specs
from tests.ingest.bportugal_verifier_fixtures import VerifyFixtureHttp

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
LATEST_ONLY = SamplingPolicy(confidence=Fraction(0), history_per_series=0)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


@pytest.fixture(scope="module")
def verified(tmp_path_factory):
    """A DB + raw store holding one verified BPstat run (10 items with archived evidence)."""
    root = tmp_path_factory.mktemp("bpstat")
    db = open_db(root / "prumo.sqlite3")
    try:
        specs = all_specs()
        sync_registry(db, specs)
        store = RawStore(root / "raw")
        clock = Clock()
        r = run_dataset(db, store, BPortugalSource(), specs, FixtureHttp(), clock)
        assert verify_run(db, r.run_id, BPortugalVerifier(), VerifyFixtureHttp(), seed=7,
                          specs=specs, store=store, now=clock, policy=LATEST_ONLY)
        ids = [i for (i,) in db.conn.execute("SELECT id FROM verification_item ORDER BY id")]
    finally:
        db.close()
    return root, ids


@pytest.fixture
def env(verified, tmp_path):
    """A private copy of the verified DB + raw store, so tests may damage it."""
    src, ids = verified
    dst = tmp_path / "data"
    for p in src.rglob("*"):
        if p.is_file():
            q = dst / p.relative_to(src)
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_bytes(p.read_bytes())
    return dst, ids


def _client(data: Path) -> TestClient:
    return TestClient(create_app(data / "prumo.sqlite3", REGISTRY, raw_dir=data / "raw"))


def _outcome(html: str) -> str:
    return re.search(r'<span class="badge[^"]*" id="replay-outcome">([^<]*)</span>', html)[1]


def _evidence_path(data: Path, item_id: int) -> Path:
    db = open_db(data / "prumo.sqlite3")
    try:
        sha = db.verification_item(item_id)["evidence_sha256"]
    finally:
        db.close()
    return data / "raw" / "verify-bportugal" / sha[:2] / sha


def _snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(),
                                       p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_replay_matches_for_genuine_item(env):
    data, ids = env
    r = _client(data).get(f"/verification/item/{ids[0]}")
    assert r.status_code == 200
    assert _outcome(r.text) == "match"
    assert "bportugal" in r.text
    db = open_db(data / "prumo.sqlite3")
    try:
        item = db.verification_item(ids[0])
    finally:
        db.close()
    # the stored claim is shown verbatim
    assert item["expected_text"] in r.text and item["series_id"] in r.text


def test_replay_is_read_only(env):
    """No byte or mtime of the DB or raw store changes, no -wal/-shm appears, and the replay
    still succeeds when the whole data directory is not writable."""
    data, ids = env
    before = _snapshot(data)
    dirs = [data, *[p for p in data.rglob("*") if p.is_dir()]]
    files = [p for p in data.rglob("*") if p.is_file()]
    for p in files:
        p.chmod(stat.S_IRUSR)
    for d in dirs:
        d.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        c = _client(data)
        for item_id in ids:
            assert _outcome(c.get(f"/verification/item/{item_id}").text) == "match"
    finally:
        for d in dirs:
            d.chmod(stat.S_IRWXU)
        for p in files:
            p.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert _snapshot(data) == before
    assert not any(n.endswith(("-wal", "-shm", "-journal")) for n in os.listdir(data))


def test_replay_reports_corrupt_evidence(env):
    data, ids = env
    _evidence_path(data, ids[0]).write_bytes(b"tampered")
    r = _client(data).get(f"/verification/item/{ids[0]}")
    assert r.status_code == 200
    assert _outcome(r.text) == "evidence corrupt"
    assert "sha256 mismatch" in r.text


def test_replay_reports_missing_evidence(env):
    data, ids = env
    _evidence_path(data, ids[0]).unlink()
    r = _client(data).get(f"/verification/item/{ids[0]}")
    assert r.status_code == 200
    assert _outcome(r.text) == "evidence missing"


def test_replay_reports_item_without_archived_evidence(env):
    data, ids = env
    db = open_db(data / "prumo.sqlite3")
    try:
        db.conn.execute("UPDATE verification_item SET evidence_sha256 = NULL WHERE id = ?",
                        (ids[0],))
    finally:
        db.close()
    r = _client(data).get(f"/verification/item/{ids[0]}")
    assert _outcome(r.text) == "evidence missing"
    assert "no evidence archived for this item" in r.text


def test_replay_reports_mismatch_with_reason(env):
    """A stored claim the archived evidence does not support is a mismatch, with the reason."""
    data, ids = env
    db = open_db(data / "prumo.sqlite3")
    try:
        db.conn.execute("UPDATE verification_item SET observed_text = observed_text || '9' "
                        "WHERE id = ?", (ids[0],))
    finally:
        db.close()
    r = _client(data).get(f"/verification/item/{ids[0]}")
    assert _outcome(r.text) == "mismatch"
    assert "disagrees with the stored claim" in r.text


def test_replay_without_a_configured_raw_store_says_so(env):
    data, ids = env
    c = TestClient(create_app(data / "prumo.sqlite3", REGISTRY))
    r = c.get(f"/verification/item/{ids[0]}")
    assert r.status_code == 200
    assert _outcome(r.text) == "cannot replay"
    assert "raw store" in r.text


def test_unknown_item_404(env):
    data, _ = env
    c = _client(data)
    assert c.get("/verification/item/999999").status_code == 404
    assert c.get("/verification/item/abc").status_code == 422


def test_replay_refuses_missing_db_with_503(tmp_path):
    c = TestClient(create_app(tmp_path / "nope.sqlite3", REGISTRY, raw_dir=tmp_path / "raw"))
    r = c.get("/verification/item/1")
    assert r.status_code == 503
    assert not (tmp_path / "nope.sqlite3").exists()


def test_series_page_links_items_to_replay(env):
    data, ids = env
    db = open_db(data / "prumo.sqlite3")
    try:
        sid = db.verification_item(ids[0])["series_id"]
    finally:
        db.close()
    html = _client(data).get(f"/series/{sid}").text
    assert f'href="/verification/item/{ids[0]}"' in html
