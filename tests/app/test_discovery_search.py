"""Phase C2: the search page is the complete, honest, paginated catalogue.

The old `reads.search` contract stays for the notebook (one query string, cap 100).
These tests describe the new page contract: uncapped total, filters that keep their
whole option list, URL-encoded pager state and accent-insensitive all-token matching.
"""
import re
from urllib.parse import parse_qs, urlsplit

from app import reads
from tests.app.conftest import HICP, T3, UNEMP


def _catalogue_row(i, *, geography="PT", family="hicp_yoy", source="ine", theme="economy",
                   frequency="M"):
    return {
        "id": f"ine.hicp_yoy.{geography}.{i:03d}",
        "indicator_key": f"hicp_yoy.{geography}.M",
        "geography": geography,
        "theme": theme,
        "frequency": frequency,
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
    """Only the latest-value read the result boundary needs."""

    def __init__(self):
        self.requested = []

    def public_latest_values(self, series_ids):
        self.requested.append(tuple(series_ids))
        return {sid: {"period": "2026-10", "value_text": "1.0", "status_flag": None,
                      "fetched_at": T3} for sid in series_ids}


def _generic_rows(count):
    return [_catalogue_row(i) for i in range(count)]


def _ids(rows):
    return [row.id for row in rows]


def test_all_tokens_must_match_accent_insensitively(monkeypatch):
    rows = [
        _catalogue_row(0, family="unemployment_rate") | {
            "id": "ine.unemployment_rate.PT",
            "indicator_key": "unemployment_rate.PT.M",
        },
        _catalogue_row(1, geography="DE", family="unemployment_rate") | {
            "id": "ine.unemployment_rate.DE",
            "indicator_key": "unemployment_rate.DE.M",
        },
        _catalogue_row(2, family="eurostat_ipi_total", source="eurostat") | {
            "id": "eurostat.ipi.PT",
            "indicator_key": "eurostat_ipi_total.PT.M",
        },
    ]
    monkeypatch.setattr(reads, "catalogue", lambda db: rows)
    db = _FakeDb()

    assert _ids(reads.search(db, "desemprego Portugal")) == ["ine.unemployment_rate.PT"]
    assert _ids(reads.search(db, "PRODUÇÃO INDUSTRIAL")) == ["eurostat.ipi.PT"]
    assert reads.search(db, "desemprego Alemanha")[0].id == "ine.unemployment_rate.DE"
    assert reads.search(db, "desemprego Portugal industrial") == ()
    # The old helper still takes one query string and still stops at the shared cap.
    assert len(reads.search(db, "ine")) == 2
    assert reads.SEARCH_CAP == 100


def test_search_page_reports_the_real_total_and_pages_without_the_cap(monkeypatch):
    rows = _generic_rows(130)
    monkeypatch.setattr(reads, "catalogue", lambda db: rows)
    db = _FakeDb()

    first = reads.search_page(db, "ine")
    assert first.total == 130 > reads.SEARCH_CAP
    assert first.per_page == reads.SEARCH_PAGE_SIZE == 24
    assert first.page == 1 and first.pages == 6
    assert len(first.rows) == 24
    assert db.requested == [tuple(row["id"] for row in rows[:24])]
    assert first.prev_path is None
    assert first.next_path == "/pesquisa?q=ine&pagina=2"
    assert first.clear_path == "/pesquisa?q=ine"
    assert not first.filters_active

    last = reads.search_page(db, "ine", page=99)
    assert last.page == 6 and len(last.rows) == 10
    assert last.next_path is None
    assert last.prev_path == "/pesquisa?q=ine&pagina=5"
    assert reads.search(db, "ine") and len(reads.search(db, "ine")) == reads.SEARCH_CAP


def test_filter_options_come_from_before_filtering_and_unknown_values_are_empty(monkeypatch):
    rows = (_generic_rows(60)
            + [_catalogue_row(100 + i, geography="EU27_2020", family="eurostat_ipi_total",
                              source="eurostat", theme="energy", frequency="A")
               for i in range(50)]
            + [_catalogue_row(200 + i, geography="US", family="worldbank_population",
                              source="worldbank", theme="demography", frequency="A")
               for i in range(40)])
    monkeypatch.setattr(reads, "catalogue", lambda db: rows)
    db = _FakeDb()

    page = reads.search_page(db, "", theme="energy")
    assert page.total == 50 and page.pages == 3 and page.page == 1
    assert {code for code, _ in page.theme_options} == {"economy", "energy", "demography"}
    assert {code for code, _ in page.source_options} == {"ine", "eurostat", "worldbank"}
    assert {code for code, _ in page.frequency_options} == {"M", "A"}
    assert page.group_options == reads.GROUPS
    assert page.filters_active and page.clear_path == "/pesquisa"

    filtered = reads.search_page(db, "", theme="energy", group="eu", source="eurostat",
                                 frequency="A", page=2)
    assert filtered.total == 50 and filtered.page == 2 and filtered.pages == 3
    assert filtered.prev_path == (
        "/pesquisa?tema=energy&grupo=eu&fonte=eurostat&frequencia=A")
    assert filtered.next_path == (
        "/pesquisa?tema=energy&grupo=eu&fonte=eurostat&frequencia=A&pagina=3")
    assert filtered.clear_path == "/pesquisa"

    for field in ("theme", "group", "source", "frequency"):
        empty = reads.search_page(db, "", **{field: "nope"})
        assert empty.total == 0 and empty.rows == ()
        assert empty.filters_active
        assert empty.clear_path == "/pesquisa"
        assert empty.prev_path is None and empty.next_path is None


def test_search_page_paths_are_percent_encoded_and_keep_all_state(monkeypatch):
    rows = [_catalogue_row(i) | {"indicator_key": f"a&b.C{i:02d}"} for i in range(30)]
    monkeypatch.setattr(reads, "catalogue", lambda db: rows)
    db = _FakeDb()

    page = reads.search_page(db, "a&b", theme="economy", group="pt", source="ine",
                             frequency="M")
    assert page.total == 30 and page.next_path is not None
    assert "q=a%26b" in page.next_path
    params = parse_qs(urlsplit(page.next_path).query)
    assert params == {"q": ["a&b"], "tema": ["economy"], "grupo": ["pt"],
                      "fonte": ["ine"], "frequencia": ["M"], "pagina": ["2"]}

    clear = parse_qs(urlsplit(page.clear_path).query)
    assert clear == {"q": ["a&b"]}
    assert all(name not in clear for name in ("tema", "grupo", "fonte", "frequencia"))


def test_query_and_page_parsing_are_bounded_before_any_database_work(monkeypatch):
    monkeypatch.setattr(reads, "catalogue", lambda db: _generic_rows(3))
    db = _FakeDb()

    assert reads.parse_search_query("  desemprego  ") == "desemprego"
    assert reads.parse_search_query("a" * 200) == "a" * 200
    assert reads.parse_search_query("a" * 201) is None
    assert reads.parse_search_query("a\x00b") is None
    assert reads.parse_page_number("3") == 3
    for value in ("", "0", "-4", "abc", "3.5", "²", "9" * 120):
        assert reads.parse_page_number(value) == 1

    page = reads.search_page(db, "a" * 500)
    assert page.query == "" and page.rows
    assert "demasiado longo" in page.notice


def test_theme_pager_keeps_its_filters_and_clear_path(monkeypatch):
    rows = _generic_rows(70) + [
        _catalogue_row(100 + i, geography="DE", source="eurostat") for i in range(30)]
    monkeypatch.setattr(reads, "catalogue", lambda db: rows)
    db = _FakeDb()

    first = reads.theme(db, "economy", group="pt", source="ine", frequency="M")
    assert first.total == 70 and first.pages == 2 and first.page == 1
    assert first.filters_active and first.clear_path == "/temas/economy"
    assert first.prev_path is None
    assert first.next_path == (
        "/temas/economy?grupo=pt&fonte=ine&frequencia=M&pagina=2")

    last = reads.theme(db, "economy", group="pt", source="ine", frequency="M", page=9)
    assert last.page == 2 and len(_ids([row for group in last.groups
                                       for row in group.rows])) == 20
    assert last.next_path is None
    assert last.prev_path == "/temas/economy?grupo=pt&fonte=ine&frequencia=M"


def test_empty_search_opens_the_catalogue(client):
    response = client.get("/pesquisa")
    assert response.status_code == 200
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", response.text))
    assert "Catálogo" in text
    assert "3 séries publicadas no catálogo" in text
    assert "Taxa de variação homóloga do IHPC" in text
    assert "Taxa de desemprego" in text
    assert "Crescimento do PIB" in text
    task_form = re.search(r'<form class="filters discovery-search".*?</form>', response.text,
                          re.S)
    assert task_form is not None
    assert task_form.group(0).count('type="search"') == 1
    assert 'name="q"' in task_form.group(0)


def test_search_results_are_one_semantic_list_with_an_explicit_single_series_action(client):
    html = client.get("/pesquisa?q=desemprego Portugal").text
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert "<table" not in html and 'class="series-results"' in html
    assert "Taxa de desemprego" in text
    assert "Taxa de variação homóloga do IHPC" not in text
    assert "INE - Instituto Nacional de Estatística" in text
    assert "outubro de 2026" in text and "03/11/2026" in text
    assert f'href="/series/{UNEMP}"' in html
    assert f'href="/caderno?s={UNEMP}"' in html
    assert 'aria-label="Criar caderno para Taxa de desemprego' in html
    assert "Criar caderno" in text
    assert html.count(f'href="/caderno?s={UNEMP}"') == 1


def test_theme_uses_the_shared_result_list_and_keeps_its_counts(client):
    html = client.get("/temas/economy").text
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert "<table" not in html and 'class="series-results"' in html
    assert "3 séries publicadas nesta secção" in text
    assert f'href="/caderno?s={HICP}"' in html
    assert "Taxa de variação homóloga do IHPC" in text


def test_unknown_filters_are_a_truthful_empty_state_with_a_clear_path(client):
    for path in ("/pesquisa?tema=nope", "/pesquisa?grupo=nope",
                 "/pesquisa?fonte=nope", "/pesquisa?frequencia=nope"):
        response = client.get(path)
        assert response.status_code == 200, path
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", response.text))
        assert "Nenhuma série corresponde a estes filtros" in text, path
        assert 'href="/pesquisa"' in response.text, path

    html = client.get("/pesquisa?q=desemprego&tema=nope").text
    assert 'href="/pesquisa?q=desemprego"' in html
    assert "Limpar filtros" in html


def test_filters_are_in_details_open_only_when_they_are_active(client):
    closed = client.get("/pesquisa").text
    assert '<details class="discovery-filters">' in closed
    assert '<details class="discovery-filters" open>' not in closed
    opened = client.get("/pesquisa?tema=economy").text
    assert '<details class="discovery-filters" open>' in opened

    theme_closed = client.get("/temas/economy").text
    assert '<details class="discovery-filters">' in theme_closed
    theme_opened = client.get("/temas/economy?grupo=world").text
    assert '<details class="discovery-filters" open>' in theme_opened


def test_catalogue_and_search_never_expose_ineligible_rows(client):
    for path in ("/pesquisa", "/pesquisa?q=ren", "/pesquisa?q=old"):
        html = client.get(path).text
        assert "Redes Energéticas Nacionais" not in html, path
        assert "99,9" not in html, path
        assert "eurostat.hicp_yoy.PT" not in html, path
        assert "ine.hicp_yoy.PT.old" not in html, path


def test_discovery_css_is_served_and_never_shrinks_inherited_type(client):
    response = client.get("/static/css/discovery.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    css = response.text
    assert ".series-results" in css and ".discovery-filters" in css
    assert not re.search(r"font-size:\s*[\d.]", css)


def test_invalid_page_and_query_inputs_recover_without_a_500(client):
    for path in ("/pesquisa?pagina=abc", "/pesquisa?pagina=" + "9" * 120,
                 "/temas/economy?pagina=abc", "/temas/economy?pagina=" + "9" * 120):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "Página 1 de 1" in response.text, path

    long_query = client.get("/pesquisa?q=" + "a" * 500)
    assert long_query.status_code == 200
    assert "demasiado longo" in long_query.text
    assert "Catálogo" in long_query.text

    control = client.get("/pesquisa?q=a%00b")
    assert control.status_code == 200
    assert "demasiado longo" in control.text


def test_the_pager_carries_percent_encoded_state_into_the_page(client, monkeypatch):
    rows = [_catalogue_row(i) | {"indicator_key": f"a&b.C{i:02d}"} for i in range(30)]
    monkeypatch.setattr(reads, "catalogue", lambda db: rows)
    page = reads.search_page(_FakeDb(), "a&b", theme="economy", group="pt",
                             source="ine", frequency="M")
    monkeypatch.setattr(reads, "search_page", lambda db, query="", **kwargs: page)

    html = client.get("/pesquisa?q=a%26b&tema=economy").text
    assert ('href="/pesquisa?q=a%26b&amp;tema=economy&amp;grupo=pt&amp;fonte=ine'
            '&amp;frequencia=M&amp;pagina=2"' in html)
    assert 'rel="next"' in html
