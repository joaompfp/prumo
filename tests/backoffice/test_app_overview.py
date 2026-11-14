"""Backoffice v1, Task 3: app skeleton, overview and queue pages (read-only, GET/HEAD only)."""
from fastapi.routing import APIRoute
from starlette.routing import Route

from backoffice.app import create_app
from ingest.db import read_db_readonly
from ingest.status import build_status
from tests.backoffice.conftest import NOW
from tests.ingest.test_task20_serving import _direct_verified

RECENT = "2026-11-14T00:00:00+00:00"


def test_healthz(env):
    c = env.client()
    assert c.get("/healthz").json() == {"status": "ok", "db": "ready"}
    assert c.head("/healthz").status_code == 200


def test_healthz_stays_200_when_the_db_is_not_ready(env, tmp_path):
    """Liveness is the app; DB readiness is a flag in the body, so a missing DB or a schema
    mismatch never makes the container restart-loop."""
    from fastapi.testclient import TestClient

    from backoffice.app import create_app
    missing = tmp_path / "missing.sqlite3"
    r = TestClient(create_app(missing, env.registry), base_url="http://localhost").get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["db"] == "unavailable"
    assert "database not found" in body["db_detail"]
    assert not missing.exists()
    db = env.db()
    db.conn.execute("INSERT INTO schema_migration(version) VALUES ('9999_future')")
    db.close()
    r = env.client().get("/healthz")
    assert r.status_code == 200 and r.json()["db"] == "unavailable"


def test_overview_shows_totals_matching_build_status(env):
    db = env.db()
    _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    db.close()
    report = read_db_readonly(env.db_path, lambda d: build_status(d, env.specs,
                                                                 now=lambda: NOW))
    r = env.client().get("/")
    assert r.status_code == 200
    for key, value in report.totals.items():
        assert f'id="t-{key}">{value}<' in r.text
    for s in report.sources:
        assert f'id="src-{s.name}"' in r.text
    assert "licence_withheld" in r.text  # 'other' source blocker is shown


def test_overview_empty_db_renders(env):
    r = env.client().get("/")
    assert r.status_code == 200
    assert 'id="t-active_series">2<' in r.text
    assert 'id="t-never_fetched">2<' in r.text


def test_head_on_pages(env):
    c = env.client()
    assert c.head("/").status_code == 200
    assert c.head("/queue").status_code == 200


def test_missing_db_returns_503_with_message(env, tmp_path):
    app = create_app(tmp_path / "absent.sqlite3", env.registry, now=lambda: NOW)
    from fastapi.testclient import TestClient
    c = TestClient(app, base_url="http://localhost")
    for path in ("/", "/queue"):
        r = c.get(path)
        assert r.status_code == 503
        assert "database not found" in r.text
        assert "Traceback" not in r.text
    assert not (tmp_path / "absent.sqlite3").exists()  # never created


def test_schema_mismatch_returns_503(env):
    db = env.db()
    db.conn.execute("INSERT INTO schema_migration(version) VALUES ('9999_future')")
    db.close()
    r = env.client().get("/")
    assert r.status_code == 503
    assert "schema is newer than this code" in r.text


def test_queue_page_lists_items_by_severity(env):
    db = env.db()
    run = _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    db.add_event(RECENT, "verification_failure", run, {"mismatches": 1})
    db.close()
    r = env.client().get("/queue")
    assert r.status_code == 200
    high = r.text.index("verification_failed")
    info = r.text.index("blocked_source")  # 'other' has licence_withheld
    assert high < info
    assert 'class="sev-high"' in r.text and 'class="sev-info"' in r.text


def test_queue_counts_revision_burst_beyond_default_page_sizes(env):
    db = env.db()
    run = _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    for i in range(150):  # one Eurostat run emitted ~150 revision events
        db.add_event(RECENT, "revision", run, {"series_id": "s1", "period": str(1900 + i)})
    db.close()
    r = env.client().get("/queue")
    assert "revision_burst" in r.text and "150 revisions in one run" in r.text


def test_queue_shows_stuck_pending_with_remedy(env):
    db = env.db()
    run = db.begin_run("fake", "kp", "2026-11-12T00:00:00+00:00")
    db.set_run_state(run, "pending-verification")
    db.close()
    r = env.client().get("/queue")
    assert "stuck_pending" in r.text and f"python -m ingest verify {run}" in r.text


def test_all_routes_are_get_or_head_only(env):
    app = create_app(env.db_path, env.registry, now=lambda: NOW)
    routes = [r for r in app.routes if isinstance(r, (APIRoute, Route))]
    assert routes
    for r in routes:
        assert r.methods <= {"GET", "HEAD"}, (r.path, r.methods)


def test_html_in_event_detail_is_escaped(env):
    db = env.db()
    run = _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    db.add_event(RECENT, "verification_failure", run,
                 {"note": "<script>alert(1)</script>", "url": "javascript:alert(2)"})
    db.close()
    r = env.client().get("/queue")
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text
    assert 'href="javascript:' not in r.text


# --- Task 6: the full status report is cached in-process for STATUS_TTL_S -----------------------

def test_status_report_is_cached_for_the_ttl(env):
    """build_status scans the whole DB (~3 s at production size), so its report is reused for
    30 s across pages; afterwards it is recomputed."""
    from fastapi.testclient import TestClient
    tick = [1000.0]
    c = TestClient(create_app(env.db_path, env.registry, now=lambda: NOW,
                              status_ttl_s=30, monotonic=lambda: tick[0]), base_url="http://localhost")

    def never_fetched(html):
        import re
        return re.search(r'id="t-never_fetched">\s*(\d+)', html)[1]

    assert never_fetched(c.get("/").text) == "2"
    db = env.db()
    _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    db.close()
    tick[0] += 29
    assert never_fetched(c.get("/").text) == "2"  # still the cached report
    tick[0] += 2
    assert never_fetched(c.get("/").text) == "1"


def test_db_refusal_is_not_cached(env, tmp_path):
    from fastapi.testclient import TestClient
    path = tmp_path / "later.sqlite3"
    c = TestClient(create_app(path, env.registry, now=lambda: NOW, status_ttl_s=30,
                              monotonic=lambda: 0.0), base_url="http://localhost")
    assert c.get("/").status_code == 503
    path.write_bytes(env.db_path.read_bytes())
    assert c.get("/").status_code == 200
