"""Task 17 fix 2 (quality F1): a receipt stamped in the FUTURE is refused at BOTH
boundaries under ONE clock-skew policy (ingest.receipts.MAX_CLOCK_SKEW = 5 minutes).

Historical and equal-to-now receipts keep being accepted and normalized as before; a
receipt more than 5 minutes ahead of the actual import-time clock is rejected:
  (a) by load_bundle BEFORE any DB open (a future bundle creates no DB at all), and
  (b) independently by run_dataset at the write boundary for a direct recorded RawResponse
      (no observations, no raw provenance written) - the pipeline never trusts the loader
      for its own invariant.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from ingest.bundle import BundleError, load_bundle
from ingest.cli import main
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from tests.ingest import worldbank_fixtures as wb_fx
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec

BASE = {"s1": [["2023", "1.5"], ["2024", "2.0"]], "s2": [["2024", "10"]]}
FIXED = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
SKEW = timedelta(minutes=5)  # pinned by test_skew_policy_is_five_minutes to the module constant
FUTURE_365 = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()


def _bundle(root, fetched_at):
    body = b'{"ok": true}'
    sha = hashlib.sha256(body).hexdigest()
    d = root / "responses" / sha[:2]
    d.mkdir(parents=True)
    (d / sha).write_bytes(body)
    entry = {
        "url": "https://api.example.com/x",
        "params": None,
        "final_url": "https://api.example.com/x",
        "status": 200,
        "fetched_at": fetched_at,
        "sha256": sha,
        "bytes": len(body),
        "file": f"responses/{sha[:2]}/{sha}",
    }
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "prumo-bundle",
                "version": 1,
                "source": "worldbank",
                "entries": [entry],
                "failures": [],
            }
        )
    )
    return root


def _load(tmp_path, name, fetched_at, **kw):
    return load_bundle(_bundle(tmp_path / name, fetched_at), source="worldbank", **kw)


class _Recorded(FakeSource):
    """One recorded response pinned to a fixed receipt, like bundle.RecordedSource."""

    def __init__(self, fetched_at):
        super().__init__(pages=1)
        self._fetched_at = fetched_at

    def fetch(self, specs, http):
        for r in super().fetch(specs, http):
            yield RawResponse(
                url=r.url,
                params=r.params,
                status=r.status,
                body=r.body,
                fetched_at=self._fetched_at,
            )


def _run_recorded(db, tmp_path, fetched_at, **kw):
    specs = [spec("s1"), spec("s2")]
    sync_registry(db, specs)
    r = run_dataset(
        db,
        RawStore(tmp_path / "raw"),
        _Recorded(fetched_at),
        specs,
        FakeHttp(ok(payload(BASE))),
        **kw,
    )
    n_obs = db.conn.execute("SELECT COUNT(*) FROM observation").fetchone()[0]
    n_raw = db.conn.execute("SELECT COUNT(*) FROM raw_fetch").fetchone()[0]
    return r, n_obs, n_raw


def test_skew_policy_is_five_minutes():
    from ingest.receipts import MAX_CLOCK_SKEW

    assert MAX_CLOCK_SKEW == timedelta(minutes=5)


# --- loader boundary (before any DB open) --------------------------------------------------


def test_loader_rejects_future_365_days(tmp_path):
    with pytest.raises(BundleError, match="future"):
        _load(tmp_path, "future", FUTURE_365)


def test_loader_rejects_just_beyond_skew(tmp_path):
    with pytest.raises(BundleError, match="future"):
        _load(tmp_path, "beyond", (FIXED + SKEW + timedelta(seconds=1)).isoformat(), now=FIXED)


def test_loader_accepts_equal_now_and_skew_edge(tmp_path):
    edge = (FIXED + SKEW).isoformat()
    assert _load(tmp_path, "edge", edge, now=FIXED).entries[0].fetched_at == edge
    now_iso = FIXED.isoformat()
    assert _load(tmp_path, "equal", now_iso, now=FIXED).entries[0].fetched_at == now_iso


def test_loader_accepts_historical_and_normalizes_offset_tz(tmp_path):
    b = _load(tmp_path, "hist", "2020-06-30T12:30:00+02:00", now=FIXED)
    assert b.entries[0].fetched_at == "2020-06-30T10:30:00+00:00"


def test_future_bundle_creates_no_db(tmp_path):
    root = _bundle(tmp_path / "b", FUTURE_365)
    db_path, raw = tmp_path / "prumo.db", tmp_path / "raw"
    specs = wb_fx.specs_of(wb_fx.POP_EUGRAT)
    sources = {s.source.name: s.source.model_dump(exclude={"name"}) for s in specs}
    series = [{**s.model_dump(exclude={"source"}), "source": s.source.name} for s in specs]
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        yaml.safe_dump({"sources": sources, "series": series}, sort_keys=False, allow_unicode=True)
    )
    rc = main(
        [
            "--db",
            str(db_path),
            "--raw-dir",
            str(raw),
            "--registry",
            str(reg),
            "run",
            "worldbank",
            "--bundle",
            str(root),
        ]
    )
    assert rc == 2
    assert not db_path.exists()


# --- pipeline write boundary (direct RawResponse replay, loader bypassed) -------------------


def test_pipeline_rejects_future_365_days_no_write(db, tmp_path):
    r, n_obs, n_raw = _run_recorded(db, tmp_path, FUTURE_365)
    assert r.state == "failed-validation"
    assert (n_obs, n_raw) == (0, 0)  # no observations, no future raw_fetch provenance
    detail = db.conn.execute("SELECT detail_json FROM event WHERE kind='format_change'").fetchone()[
        0
    ]
    assert "future" in detail


def test_pipeline_receipt_checked_against_injected_run_clock(db, tmp_path):
    past = datetime(2025, 1, 1, tzinfo=timezone.utc)
    r, n_obs, n_raw = _run_recorded(
        db, tmp_path, datetime.now(timezone.utc).isoformat(), now=lambda: past
    )
    assert r.state == "failed-validation"
    assert (n_obs, n_raw) == (0, 0)


def test_pipeline_accepts_receipt_at_skew_edge_of_run_clock(db, tmp_path):
    fixed = datetime.now(timezone.utc)
    r, n_obs, n_raw = _run_recorded(db, tmp_path, (fixed + SKEW).isoformat(), now=lambda: fixed)
    assert r.state == "pending-verification"
    assert n_obs == 3 and n_raw == 1


def test_pipeline_accepts_historical_receipt_and_keeps_it(db, tmp_path):
    past = (datetime.now(timezone.utc) - timedelta(days=30)).astimezone(timezone.utc)
    r, n_obs, n_raw = _run_recorded(db, tmp_path, past.isoformat())
    assert r.state == "pending-verification"
    assert (n_obs, n_raw) == (3, 1)
    assert db.conn.execute("SELECT DISTINCT fetched_at FROM raw_fetch").fetchall() == [
        (past.isoformat(),)
    ]
