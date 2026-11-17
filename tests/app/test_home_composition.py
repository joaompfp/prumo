"""The home page with an editorial composition, and the proof that an empty one changes nothing.

`golden/home_before_editorial.html` was rendered by the deployed commit before this feature and
stays in the tree as the historical reference. Both captures subsequently received only the
owner-requested U+2014-to-ASCII-hyphen replacement, not a new render (see golden/README.md).
`golden/home_code_list.html` is the capture this
test uses: it was re-taken once, in the comparisons release (2026-11-16), because that release
added one item to the site navigation and the nav is part of every page, the home included. At
that re-capture the two files differed by exactly that one `<a>` plus the whitespace line the
nav loop emits around it (see the commit diff); the deterministic fixture
(`tests/app/conftest.py`) is unchanged. The second deliberate edit, in the Admin-entry slice,
adds exactly one footer anchor on the same `footer-links` line:
`<a href="https://joao.date/dados/admin/">Admin</a>` and its ` · ` separator. It is absolute on
both public hosts (`cae.joao.date` and `joao.date/dados`) and does not depend on
`X-Forwarded-Prefix`. The statistics CMS slice adds a third audited delta: one relative
`<a href="/paginas">Páginas</a>` footer anchor plus its ` · ` separator, rendered from the
mount base on both hosts; `NAV` is unchanged, so the anchor appears only in `footer-links`.
A fourth audited delta binds each footer separator to the link before it with `&nbsp;`, so a
wrapped row never starts with an orphan ` · ` at 320px. No other byte changed. From here
on the byte comparison is again frozen: any unintended change to the home with no composition
fails, and a future re-capture needs the same kind of auditable reason.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app import reads
from app.main import create_app
from ingest.db import open_db
from presentation.catalog import pt
from tests.app.conftest import DERIVED, HICP, T2, UNEMP, WORLD, fetch

GOLDEN = Path(__file__).parent / "golden" / "home_code_list.html"
SLUG = "inicio"
EXTRA = "ine.hicp_yoy_extra.PT"


def _publish(site_path, pairs, note="publica a composição"):
    db = open_db(site_path)
    try:
        version = 0
        for series_id, key in pairs:
            version = db.editorial_add(SLUG, series_id, key, version, f"add {series_id}")
        db.editorial_publish(SLUG, version, note)
    finally:
        db.close()
    reads.clear_cache()


def _add_extra_series(site_path):
    """A second series with HICP's family and geography, so it renders the same title.
    Inserted after `build` so the golden fixture itself stays untouched."""
    db = open_db(site_path)
    try:
        db.conn.execute(
            "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
            "frequency, unit, active) SELECT ?, source_id, 'hicp_yoy.PT.Q', 'primary', "
            "'economy', 'PT', 'Q', '%', 1 FROM series WHERE id = ?", (EXTRA, HICP))
    finally:
        db.close()
    db = open_db(site_path)
    try:
        fetch(db, EXTRA, {"2026-Q1": "2.0"}, T2, sha="f" * 64)
    finally:
        db.close()
    reads.clear_cache()


def test_empty_composition_home_is_byte_identical(site_path):
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    assert html == GOLDEN.read_text(encoding="utf-8")


def test_empty_composition_renders_the_code_list(site_path):
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    assert "Inflação (IHPC)" in html and "Desemprego" in html
    assert "Portugal. Valores publicados tal como a fonte os publica." in html


def test_footer_admin_link_is_absolute_on_both_public_hosts(client):
    for headers in ({}, {"X-Forwarded-Prefix": "/dados"}):
        html = client.get("/", headers=headers).text
        assert html.count('href="https://joao.date/dados/admin/"') == 1, headers
        assert '>Admin</a>' in html, headers
        assert 'href="/dados/admin/"' not in html, headers


def test_publishing_the_code_list_reproduces_the_cards(site_path):
    _publish(site_path, [(HICP, None), (UNEMP, DERIVED)])
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    # labels now come from the catalogue title, not from the short hand-written label
    assert "Taxa de variação homóloga do IHPC - Portugal" in html
    assert "Taxa de desemprego - Portugal" in html
    # values are the stored tokens, formatted for the reader, in the same order
    assert html.index("1,8") < html.index("6,2")
    assert "0,3" in html  # the calculated change line survived the composition


def test_a_slot_that_stops_qualifying_is_dropped_with_a_warning(site_path, caplog):
    _publish(site_path, [(HICP, None), (WORLD, None)])
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE series SET active = 0 WHERE id = ?", (WORLD,))
    finally:
        db.close()
    reads.clear_cache()
    with caplog.at_level("WARNING", logger="prumo.app"):
        with TestClient(create_app(str(site_path))) as c:
            r = c.get("/")
    assert r.status_code == 200
    assert "Taxa de variação homóloga do IHPC - Portugal" in r.text
    assert "Crescimento do PIB" not in r.text
    assert any("editorial slot dropped" in m and WORLD in m and "inactive" in m
               for m in caplog.messages)


def test_duplicate_title_keeps_the_first_slot(site_path, caplog):
    _add_extra_series(site_path)
    _publish(site_path, [(HICP, None), (EXTRA, None)])
    with caplog.at_level("WARNING", logger="prumo.app"):
        with TestClient(create_app(str(site_path))) as c:
            html = c.get("/").text
    assert html.count("Taxa de variação homóloga do IHPC - Portugal") == 1
    assert any("duplicate_title" in m for m in caplog.messages)


def test_note_switches_when_a_card_is_not_portuguese(site_path):
    _publish(site_path, [(WORLD, None)])
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    assert "Crescimento do PIB - Estados Unidos" in html
    assert "Cada número indica a instituição e a data da recolha." in html
    assert "Portugal. Valores publicados" not in html


def test_a_page_row_for_an_unknown_slug_is_inert(site_path):
    db = open_db(site_path)
    try:
        db.conn.execute("INSERT INTO editorial_page(slug, version) VALUES ('nao-existe', 0)")
    finally:
        db.close()
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    assert html == GOLDEN.read_text(encoding="utf-8")


def test_missing_page_text_is_a_503_not_a_500(site_path, monkeypatch):
    monkeypatch.setattr(pt, "PAGES", {})
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        r = c.get("/")
    assert r.status_code == 503


def test_a_published_composition_is_not_used_by_another_slug(site_path):
    _publish(site_path, [(WORLD, None)])
    db = open_db(site_path)
    try:
        version = db.editorial_add("outra", HICP, None, 0, "add")
        db.editorial_publish("outra", version, "publica")
    finally:
        db.close()
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    # /inicio still has its own composition
    assert "Crescimento do PIB - Estados Unidos" in html
    assert "Taxa de variação homóloga do IHPC - Portugal" not in html


def test_a_composition_with_no_surviving_card_does_not_fall_back(site_path, caplog):
    """The doomsday case: every published slot lost eligibility. The page renders no cards.
    Falling back to the list in code would publish twelve series nobody chose."""
    _publish(site_path, [(WORLD, None)])
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'worldbank'")
    finally:
        db.close()
    reads.clear_cache()
    with caplog.at_level("WARNING", logger="prumo.app"):
        with TestClient(create_app(str(site_path))) as c:
            r = c.get("/")
    assert r.status_code == 200
    assert 'class="card"' not in r.text
    assert "Desemprego" not in r.text  # the code list did not take over
    assert any("withheld" in m for m in caplog.messages)


def test_the_fallback_reports_itself_and_its_section_copy(site_path):
    reads.clear_cache()
    db = open_db(site_path)
    try:
        page = reads.home(db)
    finally:
        db.close()
    assert page.composed is False
    assert page.section_title == "Números em destaque"


def test_after_a_reset_the_code_list_is_in_force_again(site_path):
    """Reset deletes both states, so the next request falls back to the list in code."""
    _publish(site_path, [(HICP, None)])
    db = open_db(site_path)
    try:
        db.editorial_reset(SLUG, db.editorial_page(SLUG)["version"], "volta ao código")
    finally:
        db.close()
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    assert "Inflação (IHPC)" in html


def test_a_slot_published_after_the_catalogue_was_cached_renders_at_once(site_path):
    """The catalogue is cached for 30 s and `cards_for` used to read it. The composition read
    now hands over its own fresh rows: warm the home, make a new series eligible, publish it
    without clearing the cache, and the card must be on the very next request rather than
    disappearing for half a minute with no log line."""
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as c:
        assert c.get("/").status_code == 200  # fills the catalogue cache
        db = open_db(site_path)
        try:
            db.conn.execute(
                "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
                "frequency, unit, active) SELECT ?, source_id, 'hicp_yoy.PT.Q', 'primary', "
                "'economy', 'PT', 'Q', '%', 1 FROM series WHERE id = ?", (EXTRA, HICP))
        finally:
            db.close()
        db = open_db(site_path)
        try:
            fetch(db, EXTRA, {"2026-Q1": "2.0"}, T2, sha="f" * 64)
        finally:
            db.close()
        db = open_db(site_path)
        try:
            version = db.editorial_add(SLUG, EXTRA, None, 0, "add extra")
            db.editorial_publish(SLUG, version, "publica")
        finally:
            db.close()
        html = c.get("/").text  # same client, catalogue cache still warm
    assert 'class="card"' in html
    assert "Taxa de variação homóloga do IHPC - Portugal" in html
    assert "2,0" in html
