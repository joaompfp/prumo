"""Backoffice v1, Task 4: series list (registry filters + status) and the per-series
provenance page (spec, status, served rows, raw fetches, quarantine, verification items,
vintages of one period)."""
import re

from ingest.models import Observation
from ingest.validate import Rejection
from tests.backoffice.conftest import series_row
from tests.ingest.test_task20_serving import _direct_verified

NOV01 = "2026-11-01T00:00:00+00:00"
NOV13 = "2026-11-13T00:00:00+00:00"


def _ids(html: str) -> list[str]:
    return re.findall(r'<tr class="series-row" id="row-([^"]+)"', html)


def _verified_many(db, sid, rows, fetched_at, key):
    run = db.begin_run("fake", key, fetched_at)
    fid = db.record_raw_fetch(source_name="fake", run_id=run, url=f"https://pub.example/{key}",
                              params_json=None, fetched_at=fetched_at, http_status=200,
                              sha256=f"sha-{key}", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, p, v), fid, fetched_at)
                                for p, v in rows])
    db.set_run_state(run, "verified")
    return run


def test_list_filters_by_source_and_active(env):
    c = env.client()
    assert sorted(_ids(c.get("/series").text)) == ["o1", "s1", "s2"]
    assert _ids(c.get("/series?source=fake&active=yes").text) == ["s1"]
    assert _ids(c.get("/series?source=fake&active=no").text) == ["s2"]
    assert _ids(c.get("/series?theme=energy").text) == ["o1"]
    assert _ids(c.get("/series?geography=EU27").text) == ["o1"]
    assert _ids(c.get("/series?q=NC1").text) == ["s1"]
    assert c.get("/series?active=maybe").status_code == 422


def test_list_shows_status_from_build_status(env):
    db = env.db()
    _direct_verified(db, "s1", "2024", "1.0", "2026-11-14T00:00:00+00:00", "k1")
    db.close()
    html = env.client().get("/series").text
    assert "verified, current" in html and "never fetched" in html


def test_list_paginates_100(make_env):
    env = make_env([series_row(f"x{i:03d}") for i in range(250)])
    c = env.client()
    first = c.get("/series").text
    assert len(_ids(first)) == 100 and _ids(first)[0] == "x000"
    assert "250 series" in first and "page=2" in first
    last = c.get("/series?page=3").text
    assert _ids(last) == [f"x{i:03d}" for i in range(200, 250)]
    assert c.get("/series?page=9").status_code == 200
    assert c.get("/series?page=0").status_code == 422


def test_detail_shows_exact_value_text_not_float(env):
    db = env.db()
    _verified_many(db, "s1", [("2022", "0.10"), ("2023", "-0.50"), ("2024", "1200.000")],
                   NOV13, "k1")
    db.close()
    html = env.client().get("/series/s1").text
    for token in ("0.10", "-0.50", "1200.000"):
        assert f'<td class="value">{token}</td>' in html
    assert '<td class="value">0.1</td>' not in html
    assert '<td class="value">1200.0</td>' not in html


def test_detail_never_fetched_series_renders(env):
    r = env.client().get("/series/s1")
    assert r.status_code == 200
    assert "never fetched" in r.text
    assert "0 served rows" in r.text
    assert "CC-BY-4.0" in r.text and "Fake publisher" in r.text and "NC1" in r.text


def test_detail_labels_legacy_served_rows_unverified(env):
    db = env.db()
    run = db.legacy_run("fake", "legacy:fake", "2025-01-01T00:00:00Z")
    db.write_legacy_observations(run, [(Observation.from_raw("s1", "2019", "7.5"),
                                        "2025-01-01T00:00:00Z")])
    db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    db.close()
    html = env.client().get("/series/s1").text
    assert "legacy only (unverified)" in html
    row = re.search(r'<tr class="obs-row legacy">.*?</tr>', html, re.S)
    assert row and "legacy, unverified" in row.group(0) and "7.5" in row.group(0)
    assert '<tr class="obs-row">' not in html  # never styled like verified data
    vint = env.client().get("/series/s1?period=2019").text
    assert re.search(r'<tr class="vintage-row legacy">.*?legacy, unverified', vint, re.S)


def test_detail_vintages_marks_served_only_once(env):
    db = env.db()
    old = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    new = _direct_verified(db, "s1", "2024", "2.0", "2026-11-03T00:00:00+00:00", "k2")
    bad = _direct_verified(db, "s1", "2024", "9.9", "2026-11-05T00:00:00+00:00", "k3")
    db.withdraw_run(bad, "unit defect", "2026-11-06T00:00:00+00:00")
    db.close()
    html = env.client().get("/series/s1?period=2024").text
    assert html.count('class="served-mark"') == 1
    served = re.search(r'<tr class="vintage-row">(?:(?!</tr>).)*served-mark.*?</tr>', html, re.S)
    assert served and f">{new}<" in served.group(0) and ">2.0<" in served.group(0)
    assert "withdrawn" in html and f">{old}<" in html


def test_detail_caps_observations_and_shows_total(env):
    db = env.db()
    _verified_many(db, "s1", [(str(1700 + i), str(i)) for i in range(250)], NOV13, "k1")
    db.close()
    html = env.client().get("/series/s1").text
    assert html.count('<tr class="obs-row">') == 200
    assert "newest 200 of 250 served rows" in html
    assert ">1949<" in html and ">1749<" not in html


def test_detail_shows_provenance_with_safe_links(env):
    db = env.db()
    run = _verified_many(db, "s1", [("2024", "1.0")], NOV01, "k1")
    db.write_quarantine(run, "s1", [Rejection("2023", "<b>n/a</b>", "non_numeric")], NOV01)
    vid = db.add_verification(run, 7, 1, True, NOV13, sample_procedure="prumo-sample-v2",
                              sample_design={}, input_origin="live", verifier_channel="live")
    item = {c: None for c in db._ITEM_COLUMNS}
    item.update(series_id="s1", period="2024", expected_text="1.0", observed_text="1.0",
                evidence_url="javascript:alert(1)", match=True, reason="latest")
    db.add_verification_item(vid, item)
    db.close()
    html = env.client().get("/series/s1").text
    assert "sha-k1" in html and "non_numeric" in html and "latest" in html
    assert "&lt;b&gt;n/a&lt;/b&gt;" in html and "<b>n/a</b>" not in html
    assert 'href="javascript:' not in html and "javascript:alert(1)" in html
    assert 'href="https://pub.example/k1"' in html  # https raw-fetch URL is a link
    assert 'href="http://other' not in html


def test_unknown_series_404(env):
    r = env.client().get("/series/nope")
    assert r.status_code == 404 and "unknown series" in r.text


def test_series_pages_refuse_missing_db_with_503(env):
    env.db_path.unlink()
    c = env.client()
    assert c.get("/series").status_code == 503
    assert c.get("/series/s1").status_code == 503
