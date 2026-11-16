"""Derived layer v1, Task 8: /derived and /derived/{key} with the visible 'calculado' cue."""
import re

import pytest

from ingest.derive import run_derive
from presentation.catalog import pt
from tests.backoffice.conftest import DEFAULT_SERIES, NOW
from tests.ingest.derived_helpers import verified_values

BADGE = '<span class="calc" title="Valor calculado pelo Prumo">calculado</span>'
YOY = "derived.s1.yoy_change_pct"
CHG = "derived.s1.period_change"
DERIVED = [
    {"key": YOY, "base": "s1", "formula": "yoy_change_pct", "unit": "pct"},
    {"key": CHG, "base": "s1", "formula": "period_change", "unit": "pp"},
]
TITLES = {YOY: "Variação homóloga s1", CHG: "Variação s1"}


@pytest.fixture(autouse=True)
def _pt_titles(monkeypatch):
    """The test keys' pt titles (the backoffice renders titles from the presentation catalog)."""
    for key, title in TITLES.items():
        monkeypatch.setitem(pt.TITLES, key, title)
FETCHED = "2026-11-13T00:00:00+00:00"


def _env(make_env, derived=DERIVED):
    return make_env(DEFAULT_SERIES, derived)


def _derive_yoy(env):
    """s1: 2024 = 100, 2025 = 103.5 (verified) -> yoy 2025 = 3.5000, served."""
    db = env.db()
    try:
        verified_values(db, "s1", {"2024": "100", "2025": "103.5"}, FETCHED, "k1")
        run_derive(db, keys=[YOY], trigger="cli", now=lambda: NOW)
        return db.served_fetched_inputs("s1")
    finally:
        db.close()


def _row(html, key):
    m = re.search(rf'<tr class="derived-row" id="row-{re.escape(key)}">(.*?)</tr>', html, re.S)
    assert m, key
    return m.group(1)


def test_derived_list_renders_empty_db(env):
    r = env.client().get("/derived")
    assert r.status_code == 200
    assert "No derived series" in r.text
    assert 'href="/derived"' in r.text  # nav link


def test_derived_list_shows_badge_label_and_status(make_env):
    env = _env(make_env)
    _derive_yoy(env)
    html = env.client().get("/derived").text
    yoy, chg = _row(html, YOY), _row(html, CHG)
    assert BADGE in yoy and BADGE in chg
    assert "Variação homóloga s1" in yoy
    assert "Variação homóloga (%), calculada pelo Prumo a partir de s1" in yoy
    assert f'href="/derived/{YOY}"' in yoy
    assert "current" in yoy and ">1<" in yoy  # one served value
    assert "never computed" in chg


def test_detail_shows_exact_value_text_and_calculated_badge(make_env):
    env = _env(make_env)
    _derive_yoy(env)
    r = env.client().get(f"/derived/{YOY}")
    assert r.status_code == 200
    html = r.text
    assert "Variação homóloga (%), calculada pelo Prumo a partir de s1" in html
    assert "Fake publisher - Calculado pelo Prumo" in html
    served = re.findall(r'<tr class="served-row">(.*?)</tr>', html, re.S)
    assert len(served) == 1
    assert f"3.5000 {BADGE}" in served[0]
    versions = re.findall(r'<tr class="version-row"[^>]*>(.*?)</tr>', html, re.S)
    assert versions and all(BADGE in v for v in versions)


def test_detail_links_inputs_to_series_period_pages(make_env):
    env = _env(make_env)
    ids = _derive_yoy(env)
    html = env.client().get(f"/derived/{YOY}").text
    served = re.search(r'<tr class="served-row">(.*?)</tr>', html, re.S).group(1)
    cur, ref = ids["2025"][0], ids["2024"][0]
    assert 'href="/series/s1?period=2025"' in served
    assert 'href="/series/s1?period=2024"' in served
    assert served.index(f"obs {cur}") < served.index(f"obs {ref}")  # current input first
    version = re.search(r'<tr class="version-row"[^>]*>(.*?)</tr>', html, re.S).group(1)
    assert 'href="/series/s1?period=2025"' in version and f"obs {ref}" in version


def test_detail_shows_mismatch_version_as_not_served(make_env):
    env = _env(make_env)
    ids = _derive_yoy(env)
    db = env.db()
    try:  # a later run whose recomputation disagreed: failed, never served
        with db.transaction():
            dsid = next(r["id"] for r in db.derived_series_rows() if r["key"] == YOY)
            run = db.begin_derived_run(NOW.isoformat(), "cli", [YOY])
            db.write_derived_observations(run, NOW.isoformat(), [
                (dsid, "2025", "9.9999", 4, f'[{ids["2025"][0]}, {ids["2024"][0]}]')])
            bad = db.derived_observations_of_run(run)[0]["id"]
            db.set_derived_row_states([(bad, "mismatch")])
            db.add_derived_event(NOW.isoformat(), run, dsid, "2025", "mismatch",
                                 {"expected": "3.5000"})
            db.finish_derived_run(run, "failed", NOW.isoformat(), n_written=1, n_checked=1,
                                  n_mismatch=1)
    finally:
        db.close()
    html = env.client().get(f"/derived/{YOY}").text
    row = re.search(rf'<tr class="version-row" id="v-{bad}">(.*?)</tr>', html, re.S).group(1)
    assert "9.9999" in row and "mismatch" in row and "failed" in row and "not served" in row
    served = re.findall(r'<tr class="served-row">(.*?)</tr>', html, re.S)
    assert len(served) == 1 and "3.5000" in served[0] and "9.9999" not in served[0]
    runs = re.search(rf'<tr class="run-row" id="run-{run}">(.*?)</tr>', html, re.S).group(1)
    assert "failed" in runs and re.search(r">1<.*>1<", runs, re.S)  # n_checked / n_mismatch


def test_unknown_derived_key_404(make_env):
    env = _env(make_env)
    r = env.client().get("/derived/derived.nope")
    assert r.status_code == 404
    assert "unknown derived series" in r.text


def test_derived_title_html_is_escaped(make_env, monkeypatch):
    monkeypatch.setitem(pt.TITLES, YOY, "<script>x()</script>")
    env = _env(make_env, [DERIVED[0]])
    for path in ("/derived", f"/derived/{YOY}"):
        html = env.client().get(path).text
        assert "<script>x()</script>" not in html
        assert "&lt;script&gt;x()&lt;/script&gt;" in html


def test_inactive_key_without_a_catalog_title_still_renders(make_env, monkeypatch):
    """A retired (inactive) key, no longer in the catalog, degrades visibly, not 500."""
    monkeypatch.delitem(pt.TITLES, CHG)
    env = _env(make_env, [DERIVED[0], DERIVED[1] | {"active": False}])
    for path in ("/derived", f"/derived/{CHG}"):
        r = env.client().get(path)
        assert r.status_code == 200 and "no title in the catalog" in r.text


def test_active_key_without_a_catalog_title_is_a_bug(make_env, monkeypatch):
    """An ACTIVE key the catalog cannot title is a missing translation: fail, never a placeholder."""
    from presentation import MissingText
    monkeypatch.delitem(pt.TITLES, CHG)
    env = _env(make_env)
    with pytest.raises(MissingText):
        env.client().get(f"/derived/{CHG}")


def test_detail_shows_caveat_sentence_only_for_caveated_series(make_env):
    from presentation import caveat_text
    derived = [DERIVED[0] | {"caveats": ["sa_base"]}, DERIVED[1]]
    env = _env(make_env, derived)
    caveated = env.client().get(f"/derived/{YOY}").text
    plain = env.client().get(f"/derived/{CHG}").text
    assert '<p class="caveat note">' in caveated
    assert caveat_text("pt", "sa_base") in caveated
    assert 'class="caveat note"' not in plain and "taxa oficial do editor" not in plain
    listing = env.client().get("/derived").text
    assert 'class="caveat-mark"' in _row(listing, YOY)
    assert 'class="caveat-mark"' not in _row(listing, CHG)


def test_detail_renders_without_any_derived_data(make_env):
    env = _env(make_env)  # declared, never computed, no base data
    html = env.client().get(f"/derived/{CHG}").text
    assert "No served values" in html and "No stored versions" in html
    assert "Fake publisher" in html


def test_overview_shows_derived_line(make_env):
    env = _env(make_env)
    _derive_yoy(env)
    html = env.client().get("/").text
    assert 'href="/derived"' in html
    m = re.search(r'<p id="derived-line">(.*?)</p>', html, re.S)
    assert m and "2 active derived series" in m.group(1) and "1 served" in m.group(1)


def test_derived_list_is_cached_for_the_status_ttl(make_env):
    """Review I3: /derived evaluates served_derived for every key; like the overview, the
    list is reused for status_ttl_s (monotonic clock), then recomputed."""
    from fastapi.testclient import TestClient

    from backoffice.app import create_app
    env = _env(make_env)
    tick = [1000.0]
    c = TestClient(create_app(env.db_path, env.registry, now=lambda: NOW, status_ttl_s=30,
                              monotonic=lambda: tick[0]), base_url="http://localhost")
    html = c.get("/derived").text
    assert "no base data" in _row(html, YOY)
    assert f"list generated {NOW.isoformat()} (0 s ago; reused for up to 30 s)" in html
    _derive_yoy(env)
    tick[0] += 29
    assert "no base data" in _row(c.get("/derived").text, YOY)  # still the cached list
    tick[0] += 2
    assert "current" in _row(c.get("/derived").text, YOY)
