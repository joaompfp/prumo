"""Equivalence contracts for the shared search and series-list boundaries.

These tests describe the public reader contract the C0 refactor must preserve: one
series row looks the same whether it was found by search or listed by theme, the
catalogue fields search matches stay the same, and theme filtering/pagination keeps its
current order.
"""
import re

from app import reads
from app.main import SCRIPT_CSP, SECURITY_HEADERS
from ingest.db import read_db_readonly
from tests.app.conftest import HICP, T3, UNEMP

GENERIC = 120


def _catalogue_row(i, *, geography="PT", family="hicp_yoy", source="ine", theme="economy"):
    return {
        "id": f"ine.hicp_yoy.{geography}.{i:03d}",
        "indicator_key": f"hicp_yoy.{geography}.M",
        "geography": geography,
        "theme": theme,
        "frequency": "M",
        "unit": "%",
        "multiplier": None,
        "seasonal_adjustment": None,
        "base_year": None,
        "native_code": None,
        "url": None,
        "role": "primary",
        "source": source,
        "family": family,
    }


class _FakeDb:
    """Only the catalogue read the public list functions need."""

    def __init__(self):
        self.requested = []

    def public_latest_values(self, series_ids):
        self.requested.append(tuple(series_ids))
        return {sid: {"period": "2026-10", "value_text": "1.0", "status_flag": None,
                      "fetched_at": T3} for sid in series_ids}


def _generic_rows(count=GENERIC):
    return [_catalogue_row(i) for i in range(count)]


def _visible_series_rows(theme_page):
    return [row for group in theme_page.groups for row in group.rows]


def test_search_matches_the_catalogue_fields_and_caps_results(monkeypatch):
    rows = _generic_rows()
    rows.extend([
        _catalogue_row(200, family="ine_population").copy() | {
            "id": "ine.population.PT", "indicator_key": "population.PT.M"},
        _catalogue_row(201, geography="US", family="worldbank_gdp_growth",
                       source="worldbank").copy() | {
            "id": "ine.worldbank_gdp_growth.US",
            "indicator_key": "worldbank_gdp_growth.US.A"},
    ])
    monkeypatch.setattr(reads, "catalogue", lambda db, **options: rows)
    db = _FakeDb()

    capped = reads.search(db, "ine")
    assert len(capped) == reads.SEARCH_CAP == 100
    assert [row.id for row in capped] == [row["id"] for row in rows[:reads.SEARCH_CAP]]
    assert db.requested == [tuple(row["id"] for row in rows[:reads.SEARCH_CAP])]

    assert [row.id for row in reads.search(db, "populacao")] == ["ine.population.PT"]
    assert [row.id for row in reads.search(db, "population.pt.m")] == ["ine.population.PT"]
    assert [row.id for row in reads.search(db, "estados unidos")] == [
        "ine.worldbank_gdp_growth.US"]
    assert reads.search(db, "   ") == ()
    assert reads.search(db, "zzzz") == ()


def test_theme_filters_orders_and_pages_the_catalogue_without_extra_reads(monkeypatch):
    rows = [_catalogue_row(i, geography="DE" if i % 10 == 0 else "PT")
            for i in range(GENERIC)]
    monkeypatch.setattr(reads, "catalogue", lambda db, **options: rows)
    db = _FakeDb()

    first = reads.theme(db, "economy")
    assert first.total == GENERIC and first.page == 1 and first.pages == 3
    assert len(_visible_series_rows(first)) == reads.PAGE_SIZE == 50
    assert len(first.groups) == 1
    assert first.groups[0].title == "Taxa de variação homóloga do IHPC"
    assert first.groups[0].rows[0].geography_text == "Alemanha"
    assert db.requested == [tuple(row.id for row in first.groups[0].rows)]

    second = reads.theme(db, "economy", page=2)
    third = reads.theme(db, "economy", page=99)
    assert second.page == 2 and len(_visible_series_rows(second)) == 50
    assert third.page == 3 and len(_visible_series_rows(third)) == 20
    assert len(db.requested) == 3

    world = reads.theme(db, "economy", group="world")
    assert world.total == 12 and world.pages == 1
    assert all(row.geography_text == "Alemanha" for row in _visible_series_rows(world))
    assert reads.theme(db, "economy", source="ine").total == GENERIC
    assert reads.theme(db, "economy", source="nope").total == 0
    assert reads.theme(db, "economy", frequency="M").total == GENERIC
    assert reads.theme(db, "economy", frequency="A").total == 0


def test_search_and_theme_prepare_identical_row_views(site_path):
    def read(db):
        theme_rows = {row.id: row for row in _visible_series_rows(reads.theme(db, "economy"))}
        return {
            "search_hicp": reads.search(db, "inflacao")[0],
            "theme_hicp": theme_rows[HICP],
            "search_unemp": reads.search(db, "desemprego")[0],
            "theme_unemp": theme_rows[UNEMP],
        }

    views = read_db_readonly(str(site_path), read)
    assert views["search_hicp"] == views["theme_hicp"]
    assert views["search_unemp"] == views["theme_unemp"]
    assert views["search_hicp"].href == f"/series/{HICP}"


def _squash(value):
    return re.sub(r"\s+", " ", value).strip()


def _series_row(html, series_id):
    blocks = re.findall(r'<li class="series-result[^"]*"[^>]*>(.*?)</li>', html, re.S)
    matches = [block for block in blocks if f'href="/series/{series_id}"' in block]
    assert len(matches) == 1, series_id
    return _squash(matches[0])


def test_search_and_theme_render_the_same_series_row_markup(client):
    search = client.get("/pesquisa?q=inflacao")
    theme = client.get("/temas/economy")
    for response in (search, theme):
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        path = response.request.url.raw_path.decode("utf-8")
        assert client.head(path).status_code == 200
    # The catalogue carries the local selection enhancement; the theme list does not.
    assert search.headers["content-security-policy"] == SCRIPT_CSP
    assert theme.headers["content-security-policy"] == SECURITY_HEADERS[
        "Content-Security-Policy"]

    flagged = client.get("/pesquisa?q=desemprego")
    assert flagged.status_code == 200

    assert 'class="series-results"' in search.text
    assert 'class="series-results"' in theme.text
    def without_selection_and_shortcut(markup):
        # Only the complete catalogue opts into multi-selection; all statistical text, facts
        # and the title link remain the authoritative shared partial. A theme keeps its one
        # series shortcut, which is deliberately not repeated on a selectable catalogue row.
        labels = re.findall(r'<label class="series-result-select">.*?</label>', markup, re.S)
        if labels:
            markup = markup.replace(labels[0], "")
        actions = re.findall(r'<p class="series-result-action">.*?</p>', markup, re.S)
        for action in actions:
            markup = markup.replace(action, "")
        return _squash(markup)

    assert without_selection_and_shortcut(_series_row(search.text, HICP)) == \
        without_selection_and_shortcut(_series_row(theme.text, HICP))
    assert without_selection_and_shortcut(_series_row(flagged.text, UNEMP)) == \
        without_selection_and_shortcut(_series_row(theme.text, UNEMP))
    assert 'type="checkbox"' not in theme.text
    row = _series_row(search.text, HICP)
    assert "INE - Instituto Nacional de Estatística" in row
    assert "1,8" in row and "outubro de 2026" in row and "03/11/2026" in row
    assert row.count('href="/series/' + HICP + '"') == 1
    assert f'href="/caderno?s={HICP}"' not in row
    assert f'href="/caderno?s={HICP}"' in _series_row(theme.text, HICP)
    assert '<span class="flag">provisório</span>' in _series_row(flagged.text, UNEMP)


def test_theme_clamps_an_out_of_range_page_on_the_same_route(client):
    first = client.get("/temas/economy")
    last = client.get("/temas/economy?pagina=99")
    assert last.status_code == 200
    assert last.text == first.text
    assert "Página 1 de 1" in last.text
