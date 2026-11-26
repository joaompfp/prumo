"""Discovery selection boundary: bounded lenient references and the shared URL helper.

The discovery page accepts more references than the notebook (for recovery across a 24-result
page) but still refuses an unbounded address before any database work. The notebook's own parser
keeps its strict twelve-raw-parameter contract; these tests name both so one cannot quietly
replace the other.
"""
import re
from urllib.parse import parse_qs, urlsplit

from starlette.datastructures import QueryParams

from app import discovery_selection, notebook, notebook_chart, reads
from tests.app.conftest import T3


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
    def public_latest_values(self, series_ids):
        return {sid: {"period": "2026-10", "value_text": "1.0", "status_flag": None,
                      "fetched_at": T3} for sid in series_ids}


def test_discovery_parser_accepts_ordered_unique_references_through_48():
    assert discovery_selection.parse_references([]) == ()
    assert discovery_selection.parse_references(["b", "a", "b"]) == ("b", "a")
    assert discovery_selection.parse_references(["a.b-c_d", "S_2.0"]) == ("a.b-c_d", "S_2.0")

    boundary = [f"s{i}" for i in range(48)]
    parsed = discovery_selection.parse_references(boundary)
    assert parsed == tuple(boundary)
    assert discovery_selection.parse_references([f"s{i}" for i in range(49)]) is None
    # The ceiling is on raw parameters, before deduplication.
    assert discovery_selection.parse_references(["a"] * 49) is None
    # Thirteen unique references are recoverable on discovery, unlike the notebook's strict parser.
    thirteen = [f"s{i}" for i in range(13)]
    assert len(discovery_selection.parse_references(thirteen)) == 13
    assert notebook.parse_selection(thirteen) is None


def test_discovery_parser_rejects_malformed_references():
    for malformed in ("", "a b", "a/b", "a#b", "../a", "a\nb", "x" * 256):
        assert discovery_selection.parse_references([malformed]) is None


def test_native_order_metadata_cannot_restore_unchecked_references():
    assert discovery_selection.preserve_order(("b", "a", "c"), ("a", "b")) == ("a", "b", "c")
    assert discovery_selection.preserve_order(("b", "c"), ("a", "b")) == ("b", "c")
    assert discovery_selection.preserve_order(("a",), ("missing",)) == ("a",)


def test_pager_preserves_order_despite_native_hidden_field_submission_order(client):
    from tests.app.conftest import HICP, WORLD

    # Hidden off-page fields precede checked visible fields in a native GET submission.
    response = client.get("/pesquisa", params=[("s", WORLD), ("s", HICP),
        ("ordem", HICP), ("ordem", WORLD), ("acao", "abrir")], follow_redirects=False)
    assert response.status_code == 303
    assert parse_qs(urlsplit(response.headers["location"]).query)["s"] == [HICP, WORLD]
    unchecked = client.get("/pesquisa", params=[("s", WORLD), ("ordem", HICP),
        ("ordem", WORLD), ("acao", "abrir")], follow_redirects=False)
    assert parse_qs(urlsplit(unchecked.headers["location"]).query)["s"] == [WORLD]
    rendered = client.get(f"/pesquisa?s={HICP}&s={WORLD}").text
    assert re.findall(r'name="ordem" value="([^"]+)"', rendered) == [HICP, WORLD]


def test_order_metadata_is_bounded_before_database_reads(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    broken = TestClient(create_app(str(tmp_path / "missing.db")))
    for params in ([("ordem", "bad/id")], [("ordem", "x")] * 49):
        response = broken.get("/pesquisa", params=params)
        assert response.status_code == 404
        assert "bad/id" not in response.text


def test_clearing_selection_resets_previous_chart_off_setting(client):
    from tests.app.conftest import HICP

    response = client.get(f"/pesquisa?s={HICP}&grafico=off&limpar=selecao")
    assert response.status_code == 200
    assert 'name="grafico" value="off"' not in _form(response.text)


def test_retiring_references_removes_only_named_values_and_preserves_order():
    selection = ("a", "b", "c")
    assert discovery_selection.retire(selection, ["b"]) == ("a", "c")
    assert discovery_selection.retire(selection, ["b", "b"]) == ("a", "c")
    assert discovery_selection.retire(selection, ["missing"]) == selection
    # A malformed control value is not an address error and cannot remove an arbitrary reference.
    assert discovery_selection.retire(selection, ["a/b", ""]) == selection


def test_shared_address_helper_keeps_first_order_and_omits_empty_values():
    assert discovery_selection.build_address("/pesquisa", []) == "/pesquisa"
    assert discovery_selection.build_address(
        "/pesquisa", [("s", "b"), ("q", ""), ("s", "a")]) == "/pesquisa?s=b&s=a"
    encoded = discovery_selection.build_address(
        "/pesquisa", [("s", "a"), ("q", "a&b"), ("g", "a")])
    assert "q=a%26b" in encoded
    assert parse_qs(urlsplit(encoded).query) == {"s": ["a"], "q": ["a&b"], "g": ["a"]}


def test_chart_settings_round_trip_through_the_catalogue_form():
    settings = notebook_chart.ChartSettings(
        mode="explicit", group=("a", "b"), scale="dupla", window="5a",
        frequency="anual", transform="base100", base="2020")
    params = discovery_selection.chart_form_params(settings)
    assert ("frequencia_grafico", "anual") in params
    assert all(name != "frequencia" for name, _ in params)

    query = QueryParams(discovery_selection.build_address(
        "/pesquisa", params).partition("?")[2])
    assert discovery_selection.read_chart_settings(query, ("a", "b", "c")) == settings


def test_catalogue_chart_settings_prune_unchecked_group_members_only():
    # A stale `g` for a current-page box the reader unchecked is pruned, not a 404.
    query = QueryParams("grafico=on&g=a&g=b&escala=dupla&janela=5a")
    assert discovery_selection.read_chart_settings(query, ("a",)) == (
        notebook_chart.ChartSettings(mode="explicit", group=("a",), scale="dupla", window="5a"))
    # Removing the only grouped member is the existing deliberate-removal off state.
    assert discovery_selection.read_chart_settings(QueryParams("grafico=on&g=b"), ("a",)) == (
        notebook_chart.ChartSettings(mode="off"))
    # A malformed or invalid chart address is still refused.
    assert discovery_selection.read_chart_settings(QueryParams("g=a/b"), ("a",)) is None
    assert discovery_selection.read_chart_settings(QueryParams("escala=mista"), ("a",)) is None
    # A plain catalogue address keeps the default all-series chart settings.
    assert discovery_selection.read_chart_settings(QueryParams(""), ("a",)) == (
        notebook_chart.ChartSettings())


def test_search_page_resolves_tray_titles_and_unavailable_refs_from_one_snapshot(monkeypatch):
    rows = [
        _catalogue_row(0) | {"id": "ine.hicp_yoy.PT", "indicator_key": "hicp_yoy.PT.M"},
        _catalogue_row(1, family="unemployment_rate") | {
            "id": "ine.unemployment_rate.PT", "indicator_key": "unemployment_rate.PT.M"},
    ]
    monkeypatch.setattr(reads, "catalogue", lambda db, **options: rows)
    page = reads.search_page(
        _FakeDb(), "", selection=("ine.hicp_yoy.PT", "ren.withheld.PT", "ine.gone.PT"),
        duplicate_count=2)

    assert page.selection_count == 3
    assert page.selected_ids == ("ine.hicp_yoy.PT", "ren.withheld.PT", "ine.gone.PT")
    assert [ref.available for ref in page.selection] == [True, False, False]
    assert page.selection[0].title == "Taxa de variação homóloga do IHPC - Portugal"
    assert page.selection[1].title == page.selection[2].title == "Referência indisponível"
    assert "ren.withheld.PT" not in page.selection[1].title
    assert "repetidas" in page.selection_duplicate_notice


def test_search_page_counts_limits_and_choose_six_note_without_truncation(monkeypatch):
    monkeypatch.setattr(reads, "catalogue", lambda db, **options: [_catalogue_row(0)])
    db = _FakeDb()

    seven = tuple(f"ref{i}" for i in range(7))
    page = reads.search_page(db, "", selection=seven)
    assert page.selection_count == 7
    assert page.selection_can_open
    assert "Escolha até 6 para o gráfico" in page.selection_chart_notice
    assert len(page.selection) == 7

    twelve = tuple(f"ref{i}" for i in range(12))
    page = reads.search_page(db, "", selection=twelve)
    assert page.selection_count == 12 and page.selection_can_open
    assert "Escolha até 6 para o gráfico" in page.selection_chart_notice
    assert len(page.selection) == 12

    thirteen = tuple(f"ref{i}" for i in range(13))
    page = reads.search_page(db, "", selection=thirteen)
    assert page.selection_count == 13 and not page.selection_can_open
    assert "13" in page.selection_limit_notice and "12" in page.selection_limit_notice
    assert page.selection_chart_notice == ""
    assert len(page.selection) == 13

    six = reads.search_page(db, "", selection=tuple(f"ref{i}" for i in range(6)))
    assert six.selection_chart_notice == ""

    repeated = reads.search_page(db, "", selection=("a", "b"), duplicate_count=2)
    assert "repetidas" in repeated.selection_duplicate_notice
    assert "repetidas" not in repeated.selection_limit_notice


# --- rendered native selection surface --------------------------------------------------------

def _visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _form(html: str) -> str:
    match = re.search(r'<form class="discovery-search".*?</form>', html, re.S)
    assert match is not None
    return match.group(0)


def _tray(html: str) -> str:
    match = re.search(r'<section class="discovery-selection".*?</section>', html, re.S)
    assert match is not None
    return match.group(0)


def test_catalogue_has_one_form_owner_and_the_search_landmark_is_only_its_query_group(client):
    html = client.get("/pesquisa").text
    assert html.count("<form ") == 1
    form = _form(html)
    assert form.count('role="search"') == 1
    assert '<div class="discovery-search-group" role="search"' in form
    assert form.count('type="checkbox" name="s"') == 3
    assert 'name="acao" value="abrir"' in form  # submits newly checked results on the first visit
    assert "disabled" not in _tray(html)
    assert html.index('class="discovery-selection"') < html.index('class="discovery-results"')
    assert 'name="retirar"' not in form  # empty selection, no tray rows

    theme_html = client.get("/temas/economy").text
    assert 'type="checkbox"' not in theme_html
    assert 'name="s"' not in theme_html


def test_tray_counts_server_state_lists_titles_and_keeps_offpage_refs_hidden(client):
    from tests.app.conftest import HICP, WORLD

    html = client.get(f"/pesquisa?s={HICP}&s={WORLD}&grupo=pt").text
    form = _form(html)
    tray = _tray(html)
    text = _visible(tray)
    assert "2 referências selecionadas" in text
    assert "Taxa de variação homóloga do IHPC - Portugal" in text
    assert "Crescimento do PIB - Estados Unidos" in text
    assert f'<input type="hidden" name="s" value="{WORLD}">' in form
    assert form.count(f'name="s" value="{HICP}"') == 1
    assert 'checked' in re.search(
        rf'<input type="checkbox" name="s" value="{HICP}"[^>]*>', form).group(0)
    assert 'type="checkbox" name="s" value="' + WORLD + '"' not in form
    assert f'name="retirar" value="{HICP}"' in tray
    assert f'name="retirar" value="{WORLD}"' in tray
    assert "Atualizar seleção" in tray

    removed_current = client.get(
        f"/pesquisa?s={HICP}&s={WORLD}&grupo=pt&retirar={HICP}").text
    assert "1 referência selecionada" in _visible(_tray(removed_current))
    assert f'name="retirar" value="{HICP}"' not in _tray(removed_current)

    removed_offscreen = client.get(
        f"/pesquisa?s={HICP}&s={WORLD}&grupo=pt&retirar={WORLD}").text
    assert "1 referência selecionada" in _visible(_tray(removed_offscreen))
    assert f'name="s" value="{WORLD}"' not in _form(removed_offscreen)
    assert f'name="retirar" value="{WORLD}"' not in _tray(removed_offscreen)


def test_unavailable_references_get_a_generic_label_and_never_a_protected_name(client):
    from tests.app.conftest import INACTIVE, WITHHELD

    html = client.get(f"/pesquisa?s={WITHHELD}&s={INACTIVE}").text
    tray_text = _visible(_tray(html))
    assert tray_text.count("Referência indisponível") == 2
    assert "Indisponível" in tray_text
    assert "Redes Energéticas Nacionais" not in tray_text
    assert WITHHELD not in tray_text and INACTIVE not in tray_text
    assert "99,9" not in html


def test_duplicates_and_thirteen_to_forty_eight_refs_are_recoverable_not_truncated(client):
    from tests.app.conftest import HICP

    refs = [HICP] + [f"missing.reference.{i}" for i in range(12)]
    html = client.get("/pesquisa", params=[("s", value) for value in refs]).text
    text = _visible(html)
    assert "13 referências selecionadas" in text
    assert "A seleção tem 13 referências" in text and "aceita 12" in text
    assert "Remova 1 referência" in text
    # The server refuses over-limit handoff. Keep the native submit available so unchecking
    # current-page results can recover immediately, without JS or an intermediate refresh.
    assert "Abrir caderno" in text and "disabled" not in _tray(html)
    assert len(re.findall(r'name="retirar" ', _tray(html))) == 13

    blocked = client.get("/pesquisa", params=[("s", value) for value in refs]
                         + [("acao", "abrir")])
    assert blocked.status_code == 200
    assert "A seleção tem 13 referências" in _visible(blocked.text)

    twelve = refs[:12]
    duplicated = client.get("/pesquisa", params=[("s", value) for value in twelve]
                            + [("s", twelve[0])]).text
    assert "12 referências selecionadas" in _visible(duplicated)
    assert "1 referência repetida" in _visible(duplicated)
    assert "disabled" not in _tray(duplicated)

    # The handoff is canonical: the repeated reference appears once, in first-seen order.
    opened = client.get("/pesquisa", params=[("s", value) for value in twelve]
                        + [("s", twelve[0]), ("acao", "abrir")], follow_redirects=False)
    assert opened.status_code == 303
    handed_off = parse_qs(urlsplit(opened.headers["location"]).query)
    assert handed_off["s"] == twelve

    forty_eight = [HICP] + [f"missing.reference.{i}" for i in range(47)]
    assert "48 referências selecionadas" in _visible(client.get(
        "/pesquisa", params=[("s", value) for value in forty_eight]).text)


def test_discovery_bounds_and_malformed_values_refuse_before_any_database_work(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    broken = TestClient(create_app(str(tmp_path / "missing.db")))
    forty_nine = broken.get("/pesquisa", params=[("s", f"x{i}") for i in range(49)])
    assert forty_nine.status_code == 404
    assert "x0" not in forty_nine.text

    malformed = broken.get("/pesquisa?s=bad%2Fid")
    assert malformed.status_code == 404
    assert "bad/id" not in malformed.text

    # Forty-eight valid references pass the address boundary and only then reach the DB.
    assert broken.get("/pesquisa", params=[("s", f"x{i}") for i in range(48)]).status_code == 503
    assert broken.get("/pesquisa", params=[("s", "bad/id")]).status_code == 404


def test_abrir_redirects_to_a_canonical_notebook_and_sanitizes_group(client):
    from tests.app.conftest import HICP, UNEMP

    response = client.get("/pesquisa", params=[
        ("s", HICP), ("s", UNEMP), ("grafico", "on"), ("g", UNEMP),
        ("escala", "dupla"), ("janela", "5a"), ("frequencia_grafico", "anual"),
        ("transformacao", "base100"), ("base", "2020"), ("acao", "abrir"),
    ], follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == (
        f"/caderno?s={HICP}&s={UNEMP}&grafico=on&g={UNEMP}&escala=dupla&janela=5a"
        "&frequencia=anual&transformacao=base100&base=2020")

    stale = client.get("/pesquisa", params=[
        ("s", HICP), ("grafico", "on"), ("g", UNEMP), ("escala", "dupla"),
        ("acao", "abrir"),
    ], follow_redirects=False)
    assert stale.status_code == 303
    assert stale.headers["location"] == f"/caderno?s={HICP}&grafico=off&escala=dupla"


def test_seven_and_twelve_cards_warn_to_choose_six_without_dropping_any(client):
    from tests.app.conftest import HICP

    for count in (7, 12):
        refs = [HICP] + [f"missing.reference.{i}" for i in range(count - 1)]
        html = client.get("/pesquisa", params=[("s", value) for value in refs]).text
        text = _visible(html)
        assert f"{count} referências selecionadas" in text
        assert "Escolha até 6 para o gráfico" in text
        assert len(re.findall(r'name="retirar" ', _tray(html))) == count
        opened = client.get("/pesquisa", params=[("s", value) for value in refs]
                             + [("acao", "abrir")], follow_redirects=False)
        assert opened.status_code == 303
        assert opened.headers["location"].count("s=") == count


def test_native_clear_actions_keep_the_last_submitted_selection(client):
    from tests.app.conftest import HICP, WORLD

    html = client.get(f"/pesquisa?s={HICP}&s={WORLD}&q=ine&tema=economy").text
    assert 'name="limpar" value="filtros"' in html
    assert 'name="limpar" value="pesquisa"' in html
    assert 'name="limpar" value="selecao"' in html

    cleared_filters = client.get("/pesquisa", params=[
        ("s", HICP), ("s", WORLD), ("q", "ine"), ("tema", "economy"),
        ("limpar", "filtros")]).text
    assert "2 referências selecionadas" in _visible(cleared_filters)
    assert '<details class="discovery-filters">' in cleared_filters
    assert 'name="q" type="search" value="ine"' in cleared_filters

    cleared_query = client.get("/pesquisa", params=[
        ("s", HICP), ("s", WORLD), ("q", "ine"), ("tema", "economy"),
        ("limpar", "pesquisa")]).text
    assert "2 referências selecionadas" in _visible(cleared_query)
    assert 'name="q" type="search" value=""' in cleared_query
    assert '<option value="">Todos os temas</option>' in cleared_query

    cleared_selection = client.get("/pesquisa", params=[
        ("s", HICP), ("s", WORLD), ("limpar", "selecao")]).text
    assert "Seleção" in _visible(_tray(cleared_selection))
    assert 'name="retirar"' not in _tray(cleared_selection)
    assert 'name="retirar"' not in _form(cleared_selection)


def test_check_germany_and_spain_across_a_page_change_then_uncheck_spain(client, monkeypatch):

    rows = ([_catalogue_row(0, geography="DE")]
            + [_catalogue_row(i, geography="BR") for i in range(1, 24)]
            + [_catalogue_row(24, geography="ES")])
    monkeypatch.setattr(reads, "catalogue", lambda db, **options: rows)

    def prepared(db, chunk, lang):
        return tuple(reads._row(r, {"period": "2026-10", "value_text": "1.0",
                                    "status_flag": None, "fetched_at": T3}, lang)
                     for r in chunk)
    monkeypatch.setattr(reads, "_served_rows", prepared)

    de = "ine.hicp_yoy.DE.000"
    es = "ine.hicp_yoy.ES.024"

    first = client.get("/pesquisa", params=[("s", de), ("s", es)]).text
    assert "2 referências selecionadas" in _visible(_tray(first))
    assert re.search(rf'name="s" value="{de}"[^>]*checked', _form(first))
    assert f'type="checkbox" name="s" value="{es}"' not in _form(first)
    assert f'<input type="hidden" name="s" value="{es}">' in _form(first)

    second = client.get("/pesquisa", params=[("s", de), ("s", es), ("pagina", "2")]).text
    assert "2 referências selecionadas" in _visible(_tray(second))
    assert re.search(rf'name="s" value="{es}"[^>]*checked', _form(second))
    assert f'<input type="hidden" name="s" value="{de}">' in _form(second)

    changed_query = client.get("/pesquisa", params=[
        ("s", de), ("s", es), ("q", "Taxa")]).text
    assert "2 referências selecionadas" in _visible(_tray(changed_query))

    unchecked = client.get("/pesquisa", params=[
        ("s", de), ("pagina", "2")]).text
    assert "1 referência selecionada" in _visible(_tray(unchecked))
    assert f'<input type="hidden" name="s" value="{es}">' not in _form(unchecked)
    assert "checked" not in re.search(
        rf'<input type="checkbox" name="s" value="{es}"[^>]*>', _form(unchecked)).group(0)

    opened = client.get("/pesquisa", params=[("s", de), ("acao", "abrir")],
                        follow_redirects=False)
    assert opened.status_code == 303
    assert opened.headers["location"] == f"/caderno?s={de}"


# --- Caderno to catalogue bridge --------------------------------------------------------------

def _catalogue_href(html: str) -> str:
    from html import unescape
    match = re.search(
        r'<a class="button-quiet" href="([^"]+)" aria-label="Acrescentar séries"', html)
    assert match is not None
    return unescape(match.group(1))


def test_caderno_links_to_the_catalogue_with_addressed_refs_and_chart_settings(client):
    from html import escape as html_escape

    from tests.app.conftest import HICP, UNEMP, WORLD

    settings = notebook_chart.ChartSettings(
        mode="explicit", group=(HICP, UNEMP), scale="dupla", window="5a",
        frequency="anual", transform="base100", base="2020")
    caderno = client.get("/caderno", params=[("s", HICP), ("s", UNEMP), ("s", WORLD)]
                         + notebook_chart.ChartSettings(
                             mode=settings.mode, group=settings.group, scale=settings.scale,
                             window=settings.window, frequency=settings.frequency,
                             transform=settings.transform, base=settings.base).params()).text
    href = _catalogue_href(caderno)
    assert href == (
        f"/pesquisa?s={HICP}&s={UNEMP}&s={WORLD}&grafico=on&g={HICP}&g={UNEMP}"
        "&escala=dupla&janela=5a&frequencia_grafico=anual&transformacao=base100&base=2020")
    assert caderno.count(f'href="{html_escape(href)}"') == 2
    assert "Escolher várias no catálogo" in _visible(caderno)
    assert "Pesquisa rápida neste caderno" in _visible(caderno)

    catalogue = client.get(href)
    assert catalogue.status_code == 200
    form = _form(catalogue.text)
    assert f'<input type="hidden" name="s" value="{HICP}">' not in form  # current page checkbox
    assert f'name="g" value="{HICP}"' in form
    assert f'name="g" value="{UNEMP}"' in form
    assert 'name="frequencia_grafico" value="anual"' in form
    assert 'name="transformacao" value="base100"' in form
    assert 'name="base" value="2020"' in form
    # The chart display frequency is not the catalogue frequency filter.
    assert '<select name="frequencia">' in form
    assert '<option value="anual"' not in form
    assert "3 séries publicadas no catálogo" in _visible(catalogue.text)
    assert '<details class="discovery-filters">' in catalogue.text


def test_caderno_three_plus_three_remove_one_opens_five_and_keeps_settings(client):
    from tests.app.conftest import HICP, UNEMP, WORLD

    settings = notebook_chart.ChartSettings(
        mode="explicit", group=(HICP, UNEMP), scale="dupla", window="5a",
        frequency="anual", transform="base100", base="2020")
    extras = ["extra.one", "extra.two", "extra.three"]
    params = ([("s", HICP), ("s", UNEMP), ("s", WORLD)]
              + [("s", value) for value in extras]
              + discovery_selection.chart_form_params(settings))
    six = client.get(discovery_selection.build_address("/pesquisa", params)).text
    assert "6 referências selecionadas" in _visible(_tray(six))

    removed = client.get(discovery_selection.build_address(
        "/pesquisa", params + [("retirar", UNEMP)])).text
    assert "5 referências selecionadas" in _visible(_tray(removed))
    removed_form = _form(removed)
    assert f'name="g" value="{HICP}"' in removed_form
    assert f'name="g" value="{UNEMP}"' not in removed_form

    opened = client.get(discovery_selection.build_address(
        "/pesquisa", params + [("retirar", UNEMP), ("acao", "abrir")]),
        follow_redirects=False)
    assert opened.status_code == 303
    location = opened.headers["location"]
    assert location == (
        f"/caderno?s={HICP}&s={WORLD}&s={extras[0]}&s={extras[1]}&s={extras[2]}"
        "&grafico=on&g=" + HICP + "&escala=dupla&janela=5a&frequencia=anual"
        "&transformacao=base100&base=2020")

    caderno = client.get(location)
    assert caderno.status_code == 200
    text = _visible(caderno.text)
    assert "2 de 12 séries." in text
    assert "3 séries desta ligação já não podem ser mostradas" in text


def test_discovery_form_and_handoff_keep_the_mount_prefix(client):
    from tests.app.conftest import HICP

    html = client.get("/pesquisa", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert ('<form class="discovery-search" id="discovery-form" action="/dados/pesquisa"'
            ' method="get" aria-describedby="selecao-ajuda">') in html
    opened = client.get("/pesquisa", params=[("s", HICP), ("acao", "abrir")],
                        headers={"X-Forwarded-Prefix": "/dados"}, follow_redirects=False)
    assert opened.status_code == 303
    assert opened.headers["location"] == f"/dados/caderno?s={HICP}"


def test_selection_controls_are_native_44px_labels_and_print_keeps_results(client):
    html = client.get("/pesquisa").text
    labels = re.findall(r'<label class="series-result-select">.*?</label>', html, re.S)
    assert len(labels) == 3
    for label in labels:
        assert 'type="checkbox" name="s"' in label
        assert "Selecionar" in label and "sr-only" in label
        assert "/series/" not in label  # the title link is a separate action

    css = client.get("/static/css/discovery.css").text
    assert ".series-result-select" in css and "min-height: 44px" in css
    assert "accent-color: var(--accent)" in css
    assert "#discovery-form .selection-remove" in css
    assert ".discovery-selection," in css  # hidden in print, unlike the results


def test_selection_page_stays_script_free_and_keeps_the_base_csp(client):
    from tests.app.conftest import HICP, UNEMP

    response = client.get("/pesquisa", params=[
        ("s", HICP), ("s", UNEMP), ("grafico", "on"), ("g", HICP)])
    assert response.status_code == 200
    assert "<script" not in response.text
    policy = response.headers["content-security-policy"]
    assert "script-src" not in policy
    assert policy.startswith("default-src 'none';")
