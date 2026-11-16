"""The editorial editor: eligibility, version stamps, origin check and the audit trail.

The fixture uses real source names and real indicator families on purpose: the editor resolves
reader text from the presentation catalogue, so a synthetic family name would make every
candidate ineligible for a reason unrelated to the test.
"""

import sqlite3

import pytest
import yaml
from fastapi.testclient import TestClient

from backoffice.app import create_app
from ingest.db import open_db
from ingest.models import Observation
from ingest.registry import load_derived, load_registry, sync_derived, sync_registry
from presentation.catalog import pt
from tests.backoffice.conftest import NOW, series_row

FETCHED = "2026-11-13T00:00:00+00:00"
DERIVED_KEY = "derived.hicp_yoy.PT.yoy_change_pct"
SLUG = "inicio"
ORIGIN = {"Origin": "http://localhost"}

SOURCES = {
    "ine": {"licence": "CC-BY-4.0", "licence_url": "https://ine.example/licence",
            "attribution": "INE", "redistribution_ok": True},
    "bportugal": {"licence": "CC-BY-4.0", "licence_url": "https://bportugal.example/l",
                  "attribution": "Banco de Portugal", "redistribution_ok": True},
    "ren": {"licence": "restricted", "licence_url": "https://ren.example/terms",
            "attribution": "REN", "redistribution_ok": False},
}

SERIES = [
    series_row("ine.hicp_yoy.PT", source="ine", indicator_key="hicp_yoy.PT.M",
               frequency="M", unit="%"),
    series_row("ine.unemployment_rate.PT", source="ine",
               indicator_key="unemployment_rate.PT.M", frequency="M", unit="%"),
    series_row("bportugal.credit_consumer.PT", source="bportugal",
               indicator_key="credit_consumer.PT.M", frequency="M", unit="%"),
    # same family and geography as the first, different frequency: the registry accepts it and
    # it renders the SAME title, which is the duplicate guard's case
    series_row("ine.hicp_yoy_sa.PT", source="ine", indicator_key="hicp_yoy.PT.Q",
               frequency="Q", unit="%"),
    series_row("ine.no_values.PT", source="ine", indicator_key="hicp_yoy.PT.A",
               frequency="A", unit="%"),
    series_row("ren.mibel.PT", source="ren", indicator_key="mibel_price.PT.M",
               frequency="M", unit="%", geography="PT"),
]

DERIVED = [{"key": DERIVED_KEY, "base": "ine.hicp_yoy.PT", "formula": "yoy_change_pct",
            "unit": "pct"}]

SERVED = [("ine.hicp_yoy.PT", "ine"), ("ine.unemployment_rate.PT", "ine"),
          ("bportugal.credit_consumer.PT", "bportugal"), ("ine.hicp_yoy_sa.PT", "ine"),
          ("ren.mibel.PT", "ren")]
PERIODS = {"ine.hicp_yoy.PT": "2026-01", "ine.unemployment_rate.PT": "2026-01",
           "bportugal.credit_consumer.PT": "2026-01", "ine.hicp_yoy_sa.PT": "2026-Q1",
           "ren.mibel.PT": "2026-01"}


@pytest.fixture(autouse=True)
def _derived_title(monkeypatch):
    monkeypatch.setitem(pt.TITLES, DERIVED_KEY, "IHPC, variação homóloga (%)")


def _served(db, sid, source, period="2026-01"):
    run = db.begin_run(source, f"k-{sid}", FETCHED)
    fid = db.record_raw_fetch(source_name=source, run_id=run, url="https://x",
                              params_json=None, fetched_at=FETCHED, http_status=200,
                              sha256=f"sha-{sid}", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, period, "1.5"), fid, FETCHED)])
    db.set_run_state(run, "verified")


class Env:
    def __init__(self, tmp_path):
        self.registry = tmp_path / "core.yaml"
        self.registry.write_text(yaml.safe_dump(
            {"sources": SOURCES, "series": SERIES, "derived": DERIVED}, sort_keys=False))
        self.db_path = tmp_path / "prumo.sqlite3"
        specs = load_registry(self.registry)
        db = open_db(self.db_path)
        try:
            sync_registry(db, specs)
            sync_derived(db, load_derived(self.registry, specs))
            for sid, source in SERVED:
                _served(db, sid, source, PERIODS[sid])
        finally:
            db.close()

    def client(self, *, editorial=True):
        return TestClient(
            create_app(self.db_path, self.registry, now=lambda: NOW,
                       editorial_db_path=self.db_path if editorial else None),
            base_url="http://localhost", follow_redirects=False)

    def slots(self, state="draft"):
        db = open_db(self.db_path)
        try:
            return [s["series_id"] for s in db.editorial_slots(SLUG, state)]
        finally:
            db.close()

    def events(self):
        db = open_db(self.db_path)
        try:
            return db.editorial_events(SLUG, limit=100)
        finally:
            db.close()

    def version(self):
        db = open_db(self.db_path)
        try:
            page = db.editorial_page(SLUG)
            return page["version"] if page else 0
        finally:
            db.close()

    def add(self, series_id, *, derived=None, version=None):
        """Add through the service (the route needs a client); returns the new version."""
        from backoffice.editorial import Editorial
        return Editorial(self.db_path, self.db_path).add(
            SLUG, series_id, derived, self.version() if version is None else version,
            f"add {series_id}")


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


# --- pages ----------------------------------------------------------------------------------


def test_the_list_names_the_code_page_and_what_is_in_force(env):
    html = env.client().get("/editorial").text
    assert "Editorial composition" in html
    assert "Início" in html and "inicio" in html
    assert "code list" in html


def test_the_editor_lists_only_eligible_candidates(env):
    html = env.client().get(f"/editorial/{SLUG}").text
    assert "Taxa de variação homóloga do IHPC" in html
    # no served values
    assert "ine.no_values.PT" not in html
    # withheld source: the candidate list never offers it
    assert "MIBEL" not in html and "ren.mibel.PT" not in html


def test_the_editor_does_not_claim_the_mount_is_missing_when_it_is_writable(env):
    """The banner is driven by `available`; the route must pass it. It did not, so every
    /editorial/{slug} page told the operator the write path was unconfigured while the POSTs
    next to it wrote successfully - a warning that reads as a broken deploy.

    Caught on production after the 0018 install, with the page answering 200 and the banner
    visible. A GET-only smoke test cannot tell this apart from a correct page."""
    html = env.client().get(f"/editorial/{SLUG}").text
    assert "The writable mount is not configured" not in html


def test_the_editor_says_the_mount_is_missing_when_it_is(env):
    """The same banner must still appear when there is no writable path: the other direction
    of the same flag."""
    html = env.client(editorial=False).get(f"/editorial/{SLUG}").text
    assert "The writable mount is not configured" in html


def test_the_editor_filters_candidates_by_source(env):
    c = env.client()
    assert "Taxa de variação homóloga do IHPC" in c.get(
        f"/editorial/{SLUG}?fonte=ine").text
    assert "Taxa de variação homóloga do IHPC" not in c.get(
        f"/editorial/{SLUG}?fonte=bportugal").text


def test_an_unknown_slug_is_404(env):
    assert env.client().get("/editorial/nao-existe").status_code == 404


# --- mutations ------------------------------------------------------------------------------


def test_add_and_remove_through_the_routes(env):
    c = env.client()
    r = c.post(f"/editorial/{SLUG}/add", headers=ORIGIN,
               data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 303
    assert env.slots() == ["ine.hicp_yoy.PT"]
    assert env.version() == 1
    assert len(env.events()) == 1

    r = c.post(f"/editorial/{SLUG}/move", headers=ORIGIN,
               data={"version": "1", "series_id": "ine.hicp_yoy.PT", "to_position": "0"})
    assert r.status_code == 303
    r = c.post(f"/editorial/{SLUG}/remove", headers=ORIGIN,
               data={"version": "2", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 303
    assert env.slots() == []


def test_the_draft_row_carries_the_version_and_both_actions(env):
    env.add("ine.hicp_yoy.PT")
    html = env.client().get(f"/editorial/{SLUG}").text
    assert 'name="version" value="1"' in html
    assert f'action="/editorial/{SLUG}/remove"' in html
    assert f'action="/editorial/{SLUG}/move"' in html


def test_a_stale_version_is_409_and_writes_nothing(env):
    env.add("ine.hicp_yoy.PT")
    r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                          data={"version": "0", "series_id": "ine.unemployment_rate.PT"})
    assert r.status_code == 409
    assert env.slots() == ["ine.hicp_yoy.PT"]
    assert env.version() == 1
    assert len(env.events()) == 1


def test_publish_copies_the_draft_and_keeps_the_reason(env):
    env.add("ine.hicp_yoy.PT")
    r = env.client().post(f"/editorial/{SLUG}/publish", headers=ORIGIN,
                          data={"version": "1", "note": "nova ordem para o início"})
    assert r.status_code == 303
    assert env.slots("published") == ["ine.hicp_yoy.PT"]
    published = [e for e in env.events() if e["action"] == "published"]
    assert published and published[0]["note"] == "nova ordem para o início"
    assert "ine.hicp_yoy.PT" in published[0]["detail_json"]


def test_publish_without_a_reason_is_refused(env):
    env.add("ine.hicp_yoy.PT")
    r = env.client().post(f"/editorial/{SLUG}/publish", headers=ORIGIN,
                          data={"version": "1", "note": "   "})
    assert r.status_code == 422
    assert env.slots("published") == []


def test_publishing_an_empty_draft_is_refused(env):
    env.add("ine.hicp_yoy.PT")
    env.client().post(f"/editorial/{SLUG}/remove", headers=ORIGIN,
                      data={"version": "1", "series_id": "ine.hicp_yoy.PT"})
    r = env.client().post(f"/editorial/{SLUG}/publish", headers=ORIGIN,
                          data={"version": "2", "note": "publicar"})
    assert r.status_code == 422
    assert "reset" in r.text


def test_the_duplicate_title_guard_refuses_the_second_variant(env):
    env.add("ine.hicp_yoy.PT")
    r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                          data={"version": "1", "series_id": "ine.hicp_yoy_sa.PT"})
    assert r.status_code == 422
    assert "duplicate_title" in r.text
    assert env.slots() == ["ine.hicp_yoy.PT"]


def test_a_withheld_series_cannot_be_added_even_by_a_crafted_post(env):
    r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                          data={"version": "0", "series_id": "ren.mibel.PT"})
    assert r.status_code == 422
    assert "withheld" in r.text
    assert env.slots() == []


def test_a_series_without_served_values_cannot_be_added(env):
    r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                          data={"version": "0", "series_id": "ine.no_values.PT"})
    assert r.status_code == 422
    assert "no_served_value" in r.text


def test_a_companion_of_another_series_is_refused(env):
    r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                          data={"version": "0", "series_id": "ine.unemployment_rate.PT",
                                "derived_key": DERIVED_KEY})
    assert r.status_code == 422
    assert "derived_base_mismatch" in r.text


def test_a_valid_companion_is_accepted_and_shown(env):
    r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                          data={"version": "0", "series_id": "ine.hicp_yoy.PT",
                                "derived_key": DERIVED_KEY})
    assert r.status_code == 303
    html = env.client().get(f"/editorial/{SLUG}").text
    assert "IHPC, variação homóloga (%)" in html


def test_discard_returns_the_draft_to_the_published_list(env):
    env.add("ine.hicp_yoy.PT")
    c = env.client()
    c.post(f"/editorial/{SLUG}/publish", headers=ORIGIN,
           data={"version": "1", "note": "publica"})
    c.post(f"/editorial/{SLUG}/add", headers=ORIGIN,
           data={"version": "2", "series_id": "ine.unemployment_rate.PT"})
    assert len(env.slots()) == 2
    r = c.post(f"/editorial/{SLUG}/discard", headers=ORIGIN, data={"version": "3"})
    assert r.status_code == 303
    assert env.slots() == ["ine.hicp_yoy.PT"]


def test_reset_returns_the_page_to_the_code_list(env):
    env.add("ine.hicp_yoy.PT")
    c = env.client()
    c.post(f"/editorial/{SLUG}/publish", headers=ORIGIN, data={"version": "1", "note": "p"})
    r = c.post(f"/editorial/{SLUG}/reset", headers=ORIGIN,
               data={"version": "2", "note": "volta ao código"})
    assert r.status_code == 303
    assert env.slots() == [] and env.slots("published") == []
    assert "code list" in c.get("/editorial").text


# --- CSRF -----------------------------------------------------------------------------------


def test_publish_is_refused_when_a_draft_slot_stopped_qualifying(env):
    """D6's case: the draft was fine when it was built, the series changed underneath it."""
    env.add("ine.hicp_yoy.PT")
    db = open_db(env.db_path)
    try:
        db.conn.execute("UPDATE series SET active = 0 WHERE id = ?", ("ine.hicp_yoy.PT",))
    finally:
        db.close()
    r = env.client().post(f"/editorial/{SLUG}/publish", headers=ORIGIN,
                          data={"version": "1", "note": "publica"})
    assert r.status_code == 422
    assert "inactive" in r.text
    assert env.slots("published") == []
    assert [e["action"] for e in env.events()] == ["slot_added"]


def test_the_publish_preview_draws_the_real_card(env):
    """The operator sees the card the home will draw: value token, unit and provenance."""
    env.add("ine.hicp_yoy.PT")
    html = env.client().get(f"/editorial/{SLUG}").text
    assert 'class="card"' in html
    assert "1,5" in html
    assert "Série e proveniência" in html


def test_the_diff_reports_one_moved_card_not_eleven():
    from types import SimpleNamespace

    from backoffice.editorial import Editorial

    slots = tuple(SimpleNamespace(series_id=f"s{i:02d}") for i in range(12))
    after = (slots[-1],) + slots[:-1]
    diff = Editorial._diff(after, slots)
    assert diff.added == () and diff.removed == ()
    assert diff.moved == ("s11",)


def test_a_locked_database_is_409_and_writes_nothing(env, monkeypatch):
    """D8: a write that cannot get the lock says so and changes nothing, instead of a 500
    after a 30-second wait."""
    from ingest import db as db_module

    monkeypatch.setattr(db_module, "BUSY_TIMEOUT_S", 0.05)
    holder = sqlite3.connect(str(env.db_path), isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        r = env.client().post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                              data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert r.status_code == 409
    assert "worker is writing" in r.text
    assert env.slots() == []


def test_a_post_without_origin_is_403(env):
    r = env.client().post(f"/editorial/{SLUG}/add",
                          data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 403
    assert env.slots() == []


def test_a_cross_origin_post_is_403(env):
    r = env.client().post(f"/editorial/{SLUG}/add",
                          headers={"Origin": "https://evil.example"},
                          data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 403
    assert env.slots() == []


def test_a_cross_site_fetch_is_403_even_with_a_good_origin(env):
    r = env.client().post(f"/editorial/{SLUG}/add",
                          headers={"Origin": "http://localhost",
                                   "Sec-Fetch-Site": "cross-site"},
                          data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 403


@pytest.mark.parametrize("origin", [
    "http://localhost:9999",     # another local port on an allowed host
    "https://localhost",         # another scheme
    "http://localhost/other",    # a path, not a bare origin
    "http://user:pass@localhost",  # credentials
    "http://localhost/?x=1",     # a query
])
def test_an_origin_that_is_not_this_request_s_own_origin_is_403(env, origin):
    """Origin matching is exact: scheme, host and port must be the ones the request arrived
    on. Matching the hostname alone accepted any port, and `localhost`/`127.0.0.1` are in the
    allowed-host list for the healthcheck, so a page on any other local port could drive the
    editor."""
    r = env.client().post(f"/editorial/{SLUG}/add", headers={"Origin": origin},
                          data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 403
    assert env.slots() == []


def test_the_preview_distinguishes_an_empty_draft_from_one_whose_cards_all_dropped(env):
    """Two different states, two different sentences: an empty draft has nothing to preview,
    while a non-empty draft whose slots all stopped qualifying would really draw no cards."""
    c = env.client()
    empty = c.get(f"/editorial/{SLUG}").text
    assert "Nothing to preview: the draft is empty." in empty
    assert "dropped at render" not in empty
    assert c.post(f"/editorial/{SLUG}/add", headers=ORIGIN,
                  data={"version": "0", "series_id": "ine.hicp_yoy.PT"}).status_code == 303
    db = open_db(env.db_path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'ine'")
    finally:
        db.close()
    dropped = c.get(f"/editorial/{SLUG}").text
    assert "Every slot in this draft is dropped at render" in dropped
    assert "Nothing to preview" not in dropped


# --- availability ---------------------------------------------------------------------------


def test_without_the_writable_mount_reads_work_and_writes_refuse(env):
    c = env.client(editorial=False)
    assert c.get(f"/editorial/{SLUG}").status_code == 200
    assert "not configured" in c.get("/editorial").text
    r = c.post(f"/editorial/{SLUG}/add", headers=ORIGIN,
               data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 503
    assert c.get("/healthz").status_code == 200


def test_a_schema_mismatch_on_the_writable_mount_is_503(tmp_path, env):
    """A writable mount at a schema this code does not know must fail closed, not write."""
    other = tmp_path / "older.sqlite3"
    conn = sqlite3.connect(str(other))
    conn.execute("CREATE TABLE schema_migration(version TEXT PRIMARY KEY, "
                 "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP) STRICT")
    conn.execute("INSERT INTO schema_migration(version) VALUES ('0001_init')")
    conn.commit()
    conn.close()
    c = TestClient(create_app(env.db_path, env.registry, now=lambda: NOW,
                              editorial_db_path=other), base_url="http://localhost")
    r = c.post(f"/editorial/{SLUG}/add", headers=ORIGIN,
               data={"version": "0", "series_id": "ine.hicp_yoy.PT"})
    assert r.status_code == 503


def test_no_template_carries_javascript(env):
    c = env.client()
    for url in ("/editorial", f"/editorial/{SLUG}"):
        html = c.get(url).text
        assert "<script" not in html.lower()
        assert "javascript:" not in html.lower()
        assert "style=" not in html.lower()
