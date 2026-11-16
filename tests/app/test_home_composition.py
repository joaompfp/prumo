"""The home page with an editorial composition, and the proof that an empty one changes nothing.

`golden/home_before_editorial.html` was rendered by the deployed commit before this feature;
the byte comparison is the deploy's safety argument, so it uses the same deterministic fixture
(`tests/app/conftest.py`), never a refreshed capture.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app import reads
from app.main import create_app
from ingest.db import open_db
from presentation.catalog import pt
from tests.app.conftest import DERIVED, HICP, T2, UNEMP, WORLD, fetch

GOLDEN = Path(__file__).parent / "golden" / "home_before_editorial.html"
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


def test_publishing_the_code_list_reproduces_the_cards(site_path):
    _publish(site_path, [(HICP, None), (UNEMP, DERIVED)])
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    # labels now come from the catalogue title, not from the short hand-written label
    assert "Taxa de variação homóloga do IHPC — Portugal" in html
    assert "Taxa de desemprego — Portugal" in html
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
    assert "Taxa de variação homóloga do IHPC — Portugal" in r.text
    assert "Crescimento do PIB" not in r.text
    assert any("editorial slot dropped" in m and WORLD in m and "inactive" in m
               for m in caplog.messages)


def test_duplicate_title_keeps_the_first_slot(site_path, caplog):
    _add_extra_series(site_path)
    _publish(site_path, [(HICP, None), (EXTRA, None)])
    with caplog.at_level("WARNING", logger="prumo.app"):
        with TestClient(create_app(str(site_path))) as c:
            html = c.get("/").text
    assert html.count("Taxa de variação homóloga do IHPC — Portugal") == 1
    assert any("duplicate_title" in m for m in caplog.messages)


def test_note_switches_when_a_card_is_not_portuguese(site_path):
    _publish(site_path, [(WORLD, None)])
    with TestClient(create_app(str(site_path))) as c:
        html = c.get("/").text
    assert "Crescimento do PIB — Estados Unidos" in html
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
    assert "Crescimento do PIB — Estados Unidos" in html
    assert "Taxa de variação homóloga do IHPC — Portugal" not in html


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
