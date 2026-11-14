"""Backoffice v1 review, Minors 1, 5, 6 and 7: bounded item ids, the cached report's age on
every page that uses it, the vintage view reachable for any stored period, and Host-header
allow-listing plus a Content-Security-Policy."""
import re
from datetime import timedelta

from fastapi.testclient import TestClient

from backoffice.app import create_app
from backoffice.deps import DEFAULT_ALLOWED_HOSTS, allowed_hosts_from_env
from ingest.models import Observation
from tests.backoffice.conftest import NOW
from tests.ingest.test_task20_serving import _direct_verified

NOV01 = "2026-11-01T00:00:00+00:00"
NOV13 = "2026-11-13T00:00:00+00:00"
CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"


# --- Minor 1 ---------------------------------------------------------------------------------

def test_item_id_beyond_sqlite_integer_range_is_422_not_500(env):
    c = env.client()
    assert c.get("/verification/item/99999999999999999999").status_code == 422
    assert c.get(f"/verification/item/{2**63}").status_code == 422
    assert c.get("/verification/item/0").status_code == 422
    assert c.get(f"/verification/item/{2**63 - 1}").status_code == 404


# --- Minor 5 ---------------------------------------------------------------------------------

def test_queue_and_overview_show_the_cached_report_age(env):
    clock = [NOW]
    c = TestClient(create_app(env.db_path, env.registry, now=lambda: clock[0],
                              monotonic=lambda: 0.0), base_url="http://localhost")
    assert "(0 s ago" in c.get("/").text
    clock[0] = NOW + timedelta(seconds=20)
    for page in ("/", "/queue"):
        html = c.get(page).text
        assert f"status report generated {NOW.isoformat()} (20 s ago" in html, page
    assert f"Derived at read time ({clock[0].isoformat()})" in c.get("/queue").text


# --- Minor 6 ---------------------------------------------------------------------------------

def test_every_stored_period_links_to_its_vintages_with_its_state(env):
    db = env.db()
    _direct_verified(db, "s1", "2022", "1", NOV01, "k1")
    bad = _direct_verified(db, "s1", "2023", "9", "2026-11-05T00:00:00+00:00", "k2")
    db.withdraw_run(bad, "unit defect", "2026-11-06T00:00:00+00:00")
    db.close()
    html = env.client().get("/series/s1").text
    periods = re.search(r'<h2 id="periods">.*?</table>', html, re.S).group(0)
    assert 'href="?period=2023#vintages"' in periods  # withdrawn only: not in served rows
    assert re.search(r"2023</a></td>\s*<td[^>]*>1</td>\s*<td[^>]*>not served", periods)
    assert re.search(r"2022</a></td>\s*<td[^>]*>1</td>\s*<td[^>]*>served", periods)
    vint = env.client().get("/series/s1?period=2023").text
    assert "withdrawn" in vint


def test_licence_withheld_series_periods_are_reachable(env):
    db = env.db()
    run = db.begin_run("other", "ko", NOV13)
    fid = db.record_raw_fetch(source_name="other", run_id=run, url="https://o/x",
                              params_json=None, fetched_at=NOV13, http_status=200,
                              sha256="sha-o", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw("o1", "2024", "5"), fid, NOV13)])
    db.set_run_state(run, "verified")
    db.close()
    html = env.client().get("/series/o1").text
    assert 'href="?period=2024#vintages"' in html
    assert '<form method="get" action="#vintages"' in html and 'name="period"' in html


def test_period_box_is_shown_even_without_stored_rows(env):
    html = env.client().get("/series/s1").text
    assert 'name="period"' in html and "No stored rows" in html


# --- Minor 7 ---------------------------------------------------------------------------------

def test_unlisted_host_header_is_refused(env):
    c = TestClient(create_app(env.db_path, env.registry, now=lambda: NOW),
                   base_url="http://evil.example")
    assert c.get("/").status_code == 400
    for host in ("100.118.19.6", "localhost", "127.0.0.1"):
        ok = TestClient(create_app(env.db_path, env.registry, now=lambda: NOW),
                        base_url=f"http://{host}:8089")
        assert ok.get("/healthz").status_code == 200, host


def test_allowed_hosts_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("PRUMO_BACKOFFICE_ALLOWED_HOSTS", raising=False)
    assert allowed_hosts_from_env() == DEFAULT_ALLOWED_HOSTS
    assert DEFAULT_ALLOWED_HOSTS == ["100.118.19.6", "localhost", "127.0.0.1"]
    monkeypatch.setenv("PRUMO_BACKOFFICE_ALLOWED_HOSTS", " f0nix.tail.ts.net , 100.118.19.6,")
    assert allowed_hosts_from_env() == ["f0nix.tail.ts.net", "100.118.19.6"]


def test_every_response_carries_a_restrictive_csp(env):
    c = env.client()
    for path in ("/", "/queue", "/series", "/series/s1", "/healthz", "/series/nope"):
        r = c.get(path)
        assert r.headers["content-security-policy"] == CSP, path
        assert r.headers["x-content-type-options"] == "nosniff"
    assert "<script" not in c.get("/").text  # the CSP allows no script at all
