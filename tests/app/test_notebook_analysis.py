"""Integration contract for notebook mixed-frequency and analytical views.

Every request runs through the installed application, a real read-only snapshot and the real
templates. The tests check the four reader surfaces together: the payload, the complete table,
the per-side provenance/evidence and the address controls that must survive every action.
"""
import hashlib
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from html import unescape

import pytest
from starlette.datastructures import QueryParams

from app import notebook
from app.notebook_chart import (
    PARAM_NAMES,
    ChartSettings,
    parse_settings,
    without_all_sides,
    without_side,
)
from presentation import notebook as notebook_copy
from tests.app.conftest import EUROSTAT, T1, T2
from tests.app.test_notebook_chart import (
    build_site,
    chart_block,
    chart_form,
    client,
    insert_served,
    payload,
    visible,
)

ROBOTS = "noindex, follow"
HICP = "ine.hicp.PT"
GDP_PT = "eurostat.gdp_pt.PT"
GDP_ES = "eurostat.gdp_es.ES"


def parse(query: str, selection: tuple[str, ...] = ("a", "b")) -> ChartSettings | None:
    values = QueryParams(query)
    return parse_settings({name: values.getlist(name) for name in PARAM_NAMES}, selection)


def annual_months(year, value="2.0"):
    return {f"{year}-{month:02d}": value for month in range(1, 13)}


def complete_months(start_year, end_year, value="2.0"):
    months = {}
    for year in range(start_year, end_year + 1):
        months.update(annual_months(year, value))
    return months


def gdp_row(series_id, key, geography, periods, at=T1):
    return {"id": series_id, "key": key, "source": EUROSTAT, "unit": "EUR per capita",
            "frequency": "A", "geography": geography, "periods": periods, "at": at}


@contextmanager
def live_site(path):
    """One real uvicorn server for browser-level print and control checks."""
    import uvicorn

    from app.main import create_app

    config = uvicorn.Config(create_app(str(path)), host="127.0.0.1", port=0,
                            log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    if not server.started:
        pytest.skip("uvicorn did not start the notebook site")
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@contextmanager
def _chromium_browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.app.test_chart_layout import _chromium

    options = {"headless": True, "args": ["--no-sandbox"]}
    executable = _chromium()
    if executable:
        options["executable_path"] = executable
    playwright = None
    try:
        playwright = sync_api.sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright unavailable: {exc}")
    assert playwright is not None
    browser = None
    try:
        browser = playwright.chromium.launch(**options)
    except Exception as exc:
        playwright.stop()
        pytest.skip(f"Chromium unavailable: {exc}")
    assert browser is not None
    try:
        yield browser
    finally:
        browser.close()
        playwright.stop()


def test_mixed_hicp_and_gdp_uses_calendar_rows_cards_and_side_provenance(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2023-01": "2.0", "2023-02": "2.1", "2024-12": "2.2"}, "at": T1},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2023": "20000", "2024": "21000"}, at=T2),
    ])
    with client(path) as site:
        response = site.get(f"/caderno?s={HICP}&s={GDP_PT}&escala=dupla")
    assert response.status_code == 200
    html = response.text
    text = visible(html)
    data = payload(html)

    assert data["version"] == 2 and data["kind"] == "calendar"
    assert data["periods"] == ["01/01/2023", "01/02/2023", "01/01/2024", "01/12/2024"]
    assert data["cell_periods"] == [
        ["janeiro de 2023", "2023"],
        ["fevereiro de 2023", None],
        [None, "2024"],
        ["dezembro de 2024", None],
    ]
    assert data["display"] == [
        ["2 %", "20\u00a0000 euros por habitante"],
        ["2,1 %", None],
        [None, "21\u00a0000 euros por habitante"],
        ["2,2 %", None],
    ]
    assert "Últimos períodos por série" in text
    assert "último período comum" not in text.lower()
    assert "Períodos originais por série" in text
    # Each card names its own last plotted native period; there is no shared one.
    cards = re.findall(r'<p class="card-chart"[^>]*>(.*?)</p>', html, re.S)
    assert any("dezembro de 2024" in card for card in cards)
    assert any(card.strip().endswith("2024.") for card in cards)
    # Per-side provenance is the actual last native period, fetched with its own run.
    assert "01/11/2026, 09:00 UTC" in text and "02/11/2026, 09:00 UTC" in text
    assert "03/11/2026, 09:00 UTC" not in text
    table = chart_block(html)
    assert "sem observação nesta posição temporal" in table
    assert "janeiro de 2023" in table and "2023" in table
    assert "<td class=\"num cell-missing\">" in table
    # Calendar placement is a display convention, not a publication or measurement date.
    assert "uma convenção de apresentação e não a data de publicação nem de medição" in text
    assert "Totais anuais e trimestrais não são diretamente equivalentes." in text
    sources = re.search(r'<ul class="notebook-chart-sources">.*?</ul>', html, re.S).group(0)
    assert "Frequência: Mensal" in sources and "Frequência: Anual" in sources


def test_calendar_reports_invalid_native_records_and_uses_presentation_missing_copy(
        tmp_path, monkeypatch):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2023-12": "2.0"}},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT", {"2024": "21000"}),
    ])
    insert_served(path, HICP, "2024-01", "n.d.")
    monkeypatch.setitem(
        notebook_copy._COPY, "pt",
        replace(notebook_copy._PT, chart_missing_cell="sem célula nesta data"))
    with client(path) as site:
        response = site.get(f"/caderno?s={HICP}&s={GDP_PT}&escala=dupla")
    assert response.status_code == 200
    html = response.text
    data = payload(html)
    text = visible(html)

    # The invalid native record is never drawn or turned into a missing cell of its own, and
    # the alignment note names its side and count instead of filtering it silently.
    assert data["missing"] == "sem célula nesta data"
    assert data["periods"] == ["01/12/2023", "01/01/2024"]
    assert data["display"][1] == [None, "21\u00a0000 euros por habitante"]
    assert "1 observação de Taxa de variação homóloga do IHPC - Portugal sem valor " \
           "numérico ou data reconhecida fica fora do calendário e da tabela." in text
    table = chart_block(html)
    assert "sem célula nesta data" in table
    assert "n.d." not in table


def test_quarter_semester_and_annual_originals_share_only_real_start_rows(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.q.PT", "key": "credit_consumer.PT.Q", "unit": "MEUR", "frequency": "Q",
         "periods": {"2024-Q1": "1.0", "2024-Q2": "2.0"}},
        {"id": "ine.s.PT", "key": "credit_housing.PT.S", "unit": "MEUR", "frequency": "S",
         "periods": {"2024-S1": "3.0", "2024-S2": "4.0"}},
        {"id": "ine.a.PT", "key": "ipi_total.PT.A", "unit": "MEUR", "frequency": "A",
         "periods": {"2024": "5.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.q.PT&s=ine.s.PT&s=ine.a.PT")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["version"] == 2 and data["kind"] == "calendar"
    assert data["periods"] == ["01/01/2024", "01/04/2024", "01/07/2024"]
    assert data["cell_periods"] == [
        ["1.º trimestre de 2024", "1.º semestre de 2024", "2024"],
        ["2.º trimestre de 2024", None, None],
        [None, "2.º semestre de 2024", None],
    ]
    assert data["display"] == [["1 milhões de euros", "3 milhões de euros",
                                "5 milhões de euros"],
                               ["2 milhões de euros", None, None],
                               [None, "4 milhões de euros", None]]
    assert "Últimos períodos por série" in visible(response.text)


def test_mixed_shared_scale_uses_the_original_unit_signature_and_dual_names_the_limit(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.mixed_pct.PT", "key": "credit_consumer.PT.M", "unit": "%",
         "periods": {"2026-01": "1.0"}},
        {"id": "ine.mixed_eur.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-01": "10.0"}},
        {"id": "ine.mixed_idx.PT", "key": "ipi_total.PT.M", "unit": "index_2021=100",
         "periods": {"2026-01": "100.0"}},
    ])
    ids = ("ine.mixed_pct.PT", "ine.mixed_eur.PT", "ine.mixed_idx.PT")
    query = "&".join(f"s={series_id}" for series_id in ids)
    with client(path) as site:
        shared = site.get(f"/caderno?{query}")
        dual = site.get(f"/caderno?{query}&escala=dupla")
    assert shared.status_code == 200
    assert "não partilham a mesma unidade, multiplicador e base" in visible(shared.text)
    assert "chart-data" not in shared.text
    assert shared.text.count('<article class="card">') == 3
    assert dual.status_code == 200
    assert "no máximo dois grupos de unidade, multiplicador e base" in visible(dual.text)
    assert "exactamente duas séries" not in visible(dual.text)
    assert "chart-data" not in dual.text


def test_six_mixed_frequency_sides_on_two_scale_groups_use_the_calendar(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.mix_a.PT", "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2025-01": "2.0", "2025-02": "2.1"}},
        {"id": "ine.mix_b.PT", "key": "unemployment_rate.PT.M", "unit": "%",
         "periods": {"2025-01": "6.0"}},
        {"id": "ine.mix_c.PT", "key": "euribor_3m.PT.Q", "unit": "%", "frequency": "Q",
         "periods": {"2025-Q1": "2.5"}},
        {"id": "ine.mix_d.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2025-01": "100000"}},
        {"id": "ine.mix_e.PT", "key": "credit_consumer.PT.Q", "unit": "MEUR", "frequency": "Q",
         "periods": {"2025-Q1": "20000"}},
        {"id": "ine.mix_f.PT", "key": "deposits_households.PT.A", "unit": "MEUR",
         "frequency": "A", "periods": {"2024": "190000", "2025": "200000"}},
    ])
    ids = ("ine.mix_a.PT", "ine.mix_b.PT", "ine.mix_c.PT",
           "ine.mix_d.PT", "ine.mix_e.PT", "ine.mix_f.PT")
    query = "&".join(f"s={series_id}" for series_id in ids) + "&escala=dupla"
    with client(path) as site:
        response = site.get(f"/caderno?{query}")
    assert response.status_code == 200
    html = response.text
    data = payload(html)
    assert data["version"] == 2 and data["kind"] == "calendar"
    assert len(data["axes"]) == 2
    assert [axis["unit"] for axis in data["axes"]] == ["%", "milhões de euros"]
    assert [series["axis"] for series in data["series"]] == [0, 0, 0, 1, 1, 1]
    assert html.count('<article class="card">') == 6
    assert html.count('data-axis="0"') == 3 and html.count('data-axis="1"') == 3
    assert "Eixo esquerdo" in visible(html) and "Eixo direito" in visible(html)


def test_annualised_sides_are_grouped_by_their_output_scale(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.cred_1.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": complete_months(2023, 2024, "100000")},
        {"id": "ine.cred_2.PT", "key": "deposits_households.PT.M", "unit": "MEUR",
         "periods": complete_months(2023, 2024, "200000")},
        gdp_row("eurostat.gdp_ann.PT", "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2023": "25000", "2024": "26000"}),
    ])
    with client(path) as site:
        response = site.get(
            "/caderno?s=ine.cred_1.PT&s=ine.cred_2.PT&s=eurostat.gdp_ann.PT"
            "&frequencia=anual&escala=dupla")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["kind"] == "group" and len(data["axes"]) == 2
    assert [axis["unit"] for axis in data["axes"]] == ["milhões de euros",
                                                       "euros por habitante"]
    assert [series["axis"] for series in data["series"]] == [0, 0, 1]
    assert response.text.count('<article class="card">') == 3


def test_annual_output_scale_drift_fails_closed(tmp_path, monkeypatch):
    path = build_site(tmp_path, [
        {"id": "ine.cred_1.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": complete_months(2023, 2024, "100000")},
        {"id": "ine.cred_2.PT", "key": "deposits_households.PT.M", "unit": "MEUR",
         "periods": complete_months(2023, 2024, "200000")},
        gdp_row("eurostat.gdp_ann.PT", "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2023": "25000", "2024": "26000"}),
    ])
    from app import calendar_notebook

    original = calendar_notebook._annual_output_signature

    def drifted(side):
        if side.row["id"] == "ine.cred_2.PT":
            return ("OUTRA", side.row["multiplier"], side.row["base_year"])
        return original(side)

    monkeypatch.setattr(calendar_notebook, "_annual_output_signature", drifted)
    with client(path) as site:
        response = site.get(
            "/caderno?s=ine.cred_1.PT&s=ine.cred_2.PT&s=eurostat.gdp_ann.PT"
            "&frequencia=anual&escala=dupla")
    assert response.status_code == 200
    assert "chart-data" not in response.text
    assert "Não foi possível preparar o gráfico" in visible(response.text)
    assert response.text.count('<article class="card">') == 3


def test_annual_pp_rates_disclose_calculated_method_base_and_raw_inputs(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": complete_months(2023, 2024, "2.0") | {f"2024-{m:02d}": "3.0"
                                                          for m in range(1, 13)}, "at": T1},
        {"id": "ine.unemp.PT", "key": "unemployment_rate.PT.M", "unit": "%",
         "periods": complete_months(2023, 2024, "6.0") | {f"2024-{m:02d}": "7.0"
                                                          for m in range(1, 13)}, "at": T2},
    ])
    with client(path) as site:
        url = f"/caderno?s={HICP}&s=ine.unemp.PT&frequencia=anual&transformacao=pp&base=2023"
        response = site.get(url)
        prefixed = site.get(url, headers={"X-Forwarded-Prefix": "/dados"})
    assert response.status_code == 200
    assert 'href="/dados/series/ine.hicp.PT"' in prefixed.text
    html = response.text
    text = visible(html)
    data = payload(html)
    assert data["version"] == 1 and data["kind"] == "comparison"
    assert data["periods"] == ["2023", "2024"]
    assert [axis["unit"] for axis in data["axes"]] == ["p.p."]
    assert data["display"] == [["0 p.p.", "0 p.p."],
                               ["1 p.p.", "1 p.p."]]
    assert "A média anual calculada de doze taxas homólogas mensais não é a taxa de " \
           "inflação anual oficial." in text
    assert "A média anual calculada de doze taxas mensais de desemprego é não ponderada" in text
    assert "Ano de base: 2023 (explícito)" in text
    assert "100 × valor ÷ valor do ano de base" not in text
    assert "valor − valor do ano de base" in text
    assert "arredondamento half-even a seis casas decimais" in text
    assert html.count('badge badge-quiet">calculado') >= 4
    # Evidence is after the plot and names both the latest and the base raw inputs.
    assert text.index("Entradas originais") > text.index("Evolução conjunta")
    assert "Último valor calculado" in text and "Valor de base" in text
    assert "01/11/2026, 09:00 UTC" in text and "02/11/2026, 09:00 UTC" in text
    assert "janeiro de 2023" in text and "dezembro de 2024" in text
    assert 'href="/series/ine.hicp.PT"' in html
    assert "Unidade da fonte" in text and "Unidade do gráfico" in text
    # A monthly source has no observation token for the annual output period, so the evidence
    # path must use the twelve raw months instead of asking for provenance at "2023".
    assert "Sem registo de proveniência para este período." not in text
    # The calculated output arrives with a mathematical check, not a source-verification claim.
    assert "não observações verificadas pela fonte" in text


def test_annual_base100_two_geographies_auto_and_explicit_base_outside_window(tmp_path):
    path = build_site(tmp_path, [
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2010": "10000", "2019": "20000", "2020": "21000", "2024": "25000"}),
        gdp_row(GDP_ES, "eurostat_gdp_per_capita_eur.ES.A", "ES",
                {"2010": "20000", "2019": "30000", "2020": "33000", "2024": "36000"}),
    ])
    base_query = (f"s={GDP_PT}&s={GDP_ES}&frequencia=anual&transformacao=base100&janela=5a")
    with client(path) as site:
        auto = site.get(f"/caderno?{base_query}")
        explicit = site.get(f"/caderno?{base_query}&base=2010")
        missing = site.get(f"/caderno?{base_query}&base=2000")
    auto_data = payload(auto.text)
    assert auto_data["periods"] == ["2019", "2020", "2024"]
    assert auto_data["display"][0] == ["100 índice (base 2019=100)",
                                       "100 índice (base 2019=100)"]
    assert auto_data["display"][1] == ["105 índice (base 2019=100)",
                                       "110 índice (base 2019=100)"]
    assert "automático, primeiro ano comum na janela" in visible(auto.text)
    assert "2019" in visible(auto.text)

    # The explicit base may be outside the display window, but it must exist on every side.
    explicit_data = payload(explicit.text)
    assert explicit_data["periods"] == ["2019", "2020", "2024"]
    assert explicit_data["display"][0] == ["200 índice (base 2010=100)",
                                           "150 índice (base 2010=100)"]
    assert "explícito" in visible(explicit.text)
    assert "Entradas originais" in visible(auto.text)
    assert "Valor de base" in visible(explicit.text)
    assert explicit.text.count("2010") >= 2  # base statement plus its original input evidence
    assert "Unidade da fonte" in visible(auto.text)
    assert "índice (base 2019=100)" in visible(auto.text)

    assert missing.status_code == 200
    assert "não existe em todas as séries escolhidas" in visible(missing.text)
    assert "chart-data" not in missing.text
    assert missing.text.count('<article class="card">') == 2
    assert "índice (base 2000=100)" not in visible(missing.text)  # no silent replacement


def test_incomplete_years_are_omitted_with_an_explicit_per_series_count(tmp_path):
    incomplete = annual_months(2023, "2.0")
    del incomplete["2023-12"]
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": incomplete | annual_months(2024, "3.0")},
    ])
    with client(path) as site:
        response = site.get(f"/caderno?s={HICP}&frequencia=anual")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["periods"] == ["2024"]
    text = visible(response.text)
    assert "1 ano incompleto excluído (2023)" in text
    assert "Anos comuns completos: 1, de 2024 a 2024." in text
    table = chart_block(response.text)
    assert table.count('badge badge-quiet">calculado') == 1


def test_native_annual_original_remains_an_original_observation(tmp_path):
    path = build_site(tmp_path, [
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2023": "20000", "2024": "21000"}),
    ])
    with client(path) as site:
        response = site.get(f"/caderno?s={GDP_PT}")
        requested = site.get(f"/caderno?s={GDP_PT}&frequencia=anual")
    assert response.status_code == 200
    assert requested.status_code == 200
    assert payload(requested.text)["periods"] == ["2023", "2024"]
    assert 'badge badge-quiet">calculado' not in chart_block(requested.text)
    data = payload(response.text)
    assert data["version"] == 1 and data["kind"] == "line"
    assert data["periods"] == ["2023", "2024"]
    assert data["display"] == [["20\u00a0000 euros por habitante"],
                               ["21\u00a0000 euros por habitante"]]
    assert 'badge badge-quiet">calculado' not in chart_block(response.text)
    assert "Entradas originais" not in visible(response.text)
    assert "01/11/2026, 09:00 UTC" in visible(response.text)


def test_mixed_annual_keeps_native_status_and_native_provenance_evidence(tmp_path):
    gdp = gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                  {"2023": "20000", "2024": "21000"}, at=T2)
    gdp["flag"] = "provisional"
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": complete_months(2023, 2024, "2.0"), "at": T1},
        gdp,
    ])
    with client(path) as site:
        response = site.get(
            f"/caderno?s={HICP}&s={GDP_PT}&frequencia=anual&escala=dupla")
    assert response.status_code == 200
    html = response.text
    data = payload(html)
    table = chart_block(html)

    # The native annual side keeps its publisher status; the calculated side is marked only
    # as calculated. A provisional native value must never look like a verified calculation.
    assert table.count("provisório") == 2
    rows = re.findall(r"<tr>(.*?)</tr>", table, re.S)
    row_2024 = next(row for row in rows if "<td>2024</td>" in row)
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_2024, re.S)
    assert "calculado" in cells[1] and "provisório" not in cells[1]
    assert "provisório" in cells[2] and "calculado" not in cells[2]

    # Per-side payload badge and SVG/legend title carry the calculated mark only on the
    # computed side. The native side stays unmarked.
    assert data["series"][0]["badge"] == "calculado"
    assert data["series"][1]["badge"] == ""
    assert "calculado" in data["series"][0]["title"]
    assert "calculado" not in data["series"][1]["title"]
    assert f'{data["series"][0]["title"]} - 2023' in html
    assert f'{data["series"][1]["title"]} - 2023' in html

    # The evidence section now carries both sides: the calculated HICP inputs and the native
    # GDP observation with its own run, fetched time, archived file, unit and series link.
    sections = re.findall(
        r'<section class="notebook-calculation-side">(.*?)</section>', html, re.S)
    assert len(sections) == 2
    hicp_side = next(section for section in sections if f"/series/{HICP}" in section)
    gdp_side = next(section for section in sections if f"/series/{GDP_PT}" in section)
    assert 'badge badge-quiet">calculado' in hicp_side
    assert "média aritmética de doze valores mensais" in hicp_side
    assert "calculado" not in gdp_side
    assert "valor anual original" in gdp_side
    assert "Último valor original" in gdp_side
    assert "02/11/2026, 09:00 UTC" in gdp_side
    assert re.search(r"#\d+", gdp_side)
    assert "euros por habitante" in gdp_side
    assert "provisório" in gdp_side
    assert "Ficheiro arquivado" in gdp_side
    assert "Entradas originais" in visible(html)


def test_annualised_mixed_units_need_the_deliberate_dual_scale(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": complete_months(2023, 2024, "2.0")},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2023": "20000", "2024": "21000"}),
    ])
    query = f"s={HICP}&s={GDP_PT}&frequencia=anual"
    with client(path) as site:
        shared = site.get(f"/caderno?{query}")
        dual = site.get(f"/caderno?{query}&escala=dupla")
    assert shared.status_code == 200
    assert "não partilham a mesma unidade, multiplicador e base" in visible(shared.text)
    assert "chart-data" not in shared.text
    assert shared.text.count('<article class="card">') == 2

    data = payload(dual.text)
    assert data["kind"] == "comparison" and len(data["axes"]) == 2
    assert data["periods"] == ["2023", "2024"]
    assert [axis["unit"] for axis in data["axes"]] == ["%", "euros por habitante"]
    table = chart_block(dual.text)
    assert table.count('badge badge-quiet">calculado') == 2
    assert "Os valores anuais nativos mantêm-se observações originais." in visible(dual.text)
    assert "Métodos por série:" in visible(dual.text)


def test_zero_base_is_valid_for_percentage_points(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": annual_months(2023, "0.0") | annual_months(2024, "2.0")},
    ])
    with client(path) as site:
        response = site.get(
            f"/caderno?s={HICP}&frequencia=anual&transformacao=pp&base=2023")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["display"] == [["0 p.p."], ["2 p.p."]]
    assert "O índice base 100 exige" not in visible(response.text)


def test_year_end_policy_keeps_december_token_and_calls_it_calculated(tmp_path):
    months = annual_months(2023, "1.0") | annual_months(2024, "2.0")
    months["2023-12"] = "9.0"
    months["2024-12"] = "12.5"
    path = build_site(tmp_path, [
        {"id": "ine.credit.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": months},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.credit.PT&frequencia=anual")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["periods"] == ["2023", "2024"]
    assert data["display"] == [["9 milhões de euros"], ["12,5 milhões de euros"]]
    text = visible(response.text)
    assert "valor de dezembro, com ano mensal completo" in text
    assert "O valor de dezembro é uma vista calculada" in text
    assert chart_block(response.text).count('badge badge-quiet">calculado') == 2


def test_unsupported_transformations_and_missing_annual_methods_are_readable(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": annual_months(2024, "2.0")},
        {"id": "ine.hicp_s.PT", "key": "hicp_yoy.PT.S", "unit": "%", "frequency": "S",
         "periods": {"2024-S1": "2.0", "2024-S2": "3.0"}},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT", {"2024": "21000"}),
    ])
    with client(path) as site:
        inflation_index = site.get(
            f"/caderno?s={HICP}&frequencia=anual&transformacao=base100")
        gdp_pp = site.get(
            f"/caderno?s={GDP_PT}&frequencia=anual&transformacao=pp")
        not_annual = site.get(f"/caderno?s={HICP}&transformacao=base100")
        dual_transform = site.get(
            f"/caderno?s={HICP}&s={GDP_PT}&frequencia=anual&transformacao=pp&escala=dupla")
        semester = site.get("/caderno?s=ine.hicp_s.PT&frequencia=anual")

    assert "só está definido para séries de nível revistas" in visible(inflation_index.text)
    assert "chart-data" not in inflation_index.text
    assert inflation_index.text.count('<article class="card">') == 1

    assert "só estão definidos para séries de taxa revistas" in visible(gdp_pp.text)
    assert "chart-data" not in gdp_pp.text

    assert "As transformações exigem a frequência anual" in visible(not_annual.text)
    assert "chart-data" not in not_annual.text

    assert "usam uma escala comum" in visible(dual_transform.text)
    assert "chart-data" not in dual_transform.text

    # A semester series has no reviewed annual method; this is a readable 200, not a 404.
    assert "Não há um método anual revisto" in visible(semester.text)
    assert "chart-data" not in semester.text


def test_analysis_address_parameters_are_strict_before_any_database_read(tmp_path):
    absent = tmp_path / "absent-analysis.db"
    with client(absent) as site:
        for query in (
            "s=a&frequencia=anual&frequencia=original",
            "s=a&frequencia=semanal",
            "s=a&transformacao=mista",
            "s=a&transformacao=base100&transformacao=pp",
            "s=a&base=26",
            "s=a&base=2023&base=2024",
            "s=a&base=0000",
            "s=a&base=99999",
        ):
            response = site.get(f"/caderno?{query}")
            assert response.status_code == 404, query
            assert response.headers["x-robots-tag"] == ROBOTS
        # Blank base means automatic and is a valid address; valid addresses reach the missing
        # database, so the 404s above happened before any read-only handle was opened.
        assert site.get("/caderno?s=a&base=").status_code == 503
        assert site.get("/caderno?s=a&frequencia=anual&transformacao=pp&base=9999").status_code == 503


def test_controls_links_and_actions_preserve_frequency_transform_and_base(tmp_path):
    path = build_site(tmp_path, [
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2019": "20000", "2024": "25000"}),
        gdp_row(GDP_ES, "eurostat_gdp_per_capita_eur.ES.A", "ES",
                {"2019": "30000", "2024": "36000"}),
        {"id": "ine.credit.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2024-12": "1.0"}},
    ])
    query = (f"s={GDP_PT}&s={GDP_ES}&grafico=on&g={GDP_PT}&g={GDP_ES}&janela=5a"
             "&frequencia=anual&transformacao=base100&base=2019&q=cr%C3%A9dito")
    with client(path) as site:
        response = site.get(f"/caderno?{query}")
        off = site.get(f"/caderno?{query.replace('grafico=on', 'grafico=off')}")
        empty = site.get(
            f"/caderno?s={GDP_PT}&s={GDP_ES}&grafico=on&janela=5a"
            "&frequencia=anual&transformacao=base100&base=2019")
    html = response.text
    form = chart_form(html)
    assert 'name="frequencia"' in form and 'value="anual" selected' in form
    assert 'name="transformacao"' in form and 'value="base100" selected' in form
    assert re.search(r'name="base"[^>]*value="2019"', form)
    search_form = re.search(r'<form id="notebook-search-form".*?</form>', html, re.S).group(0)
    assert 'name="frequencia" value="anual"' in search_form
    assert 'name="transformacao" value="base100"' in search_form
    assert 'name="base" value="2019"' in search_form

    canonical = unescape(re.search(r'id="ligacao-limpa" href="([^"]+)"', html).group(1))
    assert canonical == (f"/caderno?s={GDP_PT}&s={GDP_ES}&grafico=on&g={GDP_PT}&g={GDP_ES}"
                          "&janela=5a&frequencia=anual&transformacao=base100&base=2019")

    add = unescape(re.search(r'href="([^"]+)">Acrescentar ao caderno</a>', html).group(1))
    assert "frequencia=anual" in add and "transformacao=base100" in add and "base=2019" in add
    assert "g=ine.credit.PT" not in add

    remove = unescape(re.search(r'href="([^"]+)">Remover do caderno</a>', html).group(1))
    assert f"s={GDP_PT}" not in remove and f"s={GDP_ES}" in remove
    assert "frequencia=anual" in remove and "transformacao=base100" in remove
    assert "base=2019" in remove

    clear = unescape(re.search(
        r'href="([^"]+)">Limpar seleção</a>', html).group(1))
    assert clear.startswith("/caderno?")
    assert "q=cr%C3%A9dito" in clear
    assert "grafico=off" in clear
    assert "frequencia=anual" in clear and "transformacao=base100" in clear
    assert "base=2019" in clear

    off_form = chart_form(off.text)
    assert 'value="anual" selected' in off_form
    assert 'value="base100" selected' in off_form
    assert re.search(r'name="base"[^>]*value="2019"', off_form)
    empty_form = chart_form(empty.text)
    assert "Não há séries escolhidas para o gráfico" in visible(empty.text)
    assert 'value="anual" selected' in empty_form
    assert 'value="base100" selected' in empty_form
    assert re.search(r'name="base"[^>]*value="2019"', empty_form)
    activate = re.search(r'href="([^"]+)">Ativar gráfico</a>', off.text)
    assert activate is not None and "base=2019" in unescape(activate.group(1))


def test_analysis_requests_do_not_change_the_database(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": annual_months(2023) | annual_months(2024, "3.0")},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2023": "20000", "2024": "21000"}),
    ])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with client(path) as site:
        for query in (
            f"/caderno?s={HICP}&s={GDP_PT}&escala=dupla",
            f"/caderno?s={HICP}&frequencia=anual&transformacao=pp&base=2023",
            f"/caderno?s={GDP_PT}&frequencia=anual&transformacao=base100&base=2023",
            f"/caderno?s={HICP}&s={GDP_PT}&frequencia=anual&escala=dupla",
        ):
            assert site.get(query).status_code == 200
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_rights_loss_keeps_the_analysis_controls_and_omits_only_the_card(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": annual_months(2024, "2.0")},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT", {"2024": "21000"}),
    ])
    from ingest.db import open_db
    db = open_db(path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'ine'")
        db.conn.commit()
    finally:
        db.close()
    with client(path) as site:
        response = site.get(
            f"/caderno?s={HICP}&s={GDP_PT}&grafico=on&g={HICP}"
            "&frequencia=anual&transformacao=base100&base=2024")
    assert response.status_code == 200
    html = response.text
    assert html.count('<article class="card">') == 1
    assert "Uma das séries escolhidas já não pode ser mostrada" in visible(html)
    assert "chart-data" not in html
    form = chart_form(html)
    assert 'value="anual" selected' in form and 'value="base100" selected' in form
    assert re.search(r'name="base"[^>]*value="2024"', form)
    assert f"s={HICP}" in unescape(html)


def test_pt15m_keeps_the_day_view_and_refuses_mixing_or_annualisation(tmp_path):
    ered = {"name": "eredes", "licence": "CC BY 4.0",
            "licence_url": "https://www.eredes.pt/termos", "attribution": "E-REDES",
            "redistribution_ok": True}
    from ingest.models import SourceSpec
    source = SourceSpec(**ered)
    path = build_site(tmp_path, [
        {"id": "eredes.market.PT", "key": "eredes_production_market.PT.PT15M",
         "source": source, "unit": "GWh", "frequency": "PT15M",
         "periods": {"2026-11-01T00:00:00+00:00": "10.0",
                     "2026-11-01T00:15:00+00:00": "11.0"}},
        {"id": "ine.daily_mix.PT", "key": "credit_consumer.PT.M", "unit": "GWh",
         "periods": {"2026-11": "1.0"}},
    ])
    with client(path) as site:
        original = site.get("/caderno?s=eredes.market.PT")
        mixed = site.get("/caderno?s=eredes.market.PT&s=ine.daily_mix.PT")
        annual = site.get("/caderno?s=eredes.market.PT&frequencia=anual")
        transform = site.get(
            "/caderno?s=eredes.market.PT&frequencia=anual&transformacao=base100")
    assert payload(original.text)["version"] == 1
    assert payload(original.text)["periods"] == ["01/11/2026, 00:00 UTC",
                                                 "01/11/2026, 00:15 UTC"]
    for response in (mixed, annual, transform):
        assert response.status_code == 200
        assert "só podem ser comparadas entre si" in visible(response.text)
        assert "chart-data" not in response.text
        assert response.text.count('<article class="card">') == (
            2 if response is mixed else 1)


def test_mixed_window_uses_real_calendar_years_not_lexicographic_tokens(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2010-01": "1.0", "2020-01": "2.0", "2024-12": "3.0"}},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2010": "10000", "2015": "15000", "2024": "21000"}),
    ])
    query = f"s={HICP}&s={GDP_PT}&escala=dupla"
    with client(path) as site:
        ten = site.get(f"/caderno?{query}")
        five = site.get(f"/caderno?{query}&janela=5a")
        maximum = site.get(f"/caderno?{query}&janela=max")
    assert "01/01/2010" not in payload(ten.text)["periods"]
    assert "01/01/2015" in payload(ten.text)["periods"]
    assert "01/01/2010" not in payload(five.text)["periods"]
    assert "01/01/2015" not in payload(five.text)["periods"]
    assert payload(five.text)["periods"][0] == "01/01/2020"
    assert "01/01/2010" in payload(maximum.text)["periods"]
    assert "01/01/2015" in payload(maximum.text)["periods"]


def test_rollback_clamps_target_before_year_one_and_leaves_modern_dates_alone(tmp_path):
    from datetime import date

    from app.calendar_notebook import _rollback

    assert _rollback(date(5, 1, 1), 10) == date(1, 1, 1)
    assert _rollback(date(2026, 5, 20), 10) == date(2016, 5, 20)
    assert _rollback(date(2024, 2, 29), 5) == date(2019, 2, 28)

    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {f"0005-{month:02d}": "2.0" for month in range(1, 13)}},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT", {"0005": "10000"}),
    ])
    query = f"s={HICP}&s={GDP_PT}&escala=dupla&janela=10a"
    with client(path) as site:
        response = site.get(f"/caderno?{query}")
    assert response.status_code == 200
    periods = payload(response.text)["periods"]
    assert len(periods) == 12
    assert periods[0].startswith("01/01/") and periods[-1].startswith("01/12/")


def test_mixed_side_without_a_drawable_window_makes_the_chart_unavailable(tmp_path):
    path = build_site(tmp_path, [
        {"id": HICP, "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2024-12": "3.0"}},
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT", {"2010": "10000"}),
    ])
    with client(path) as site:
        response = site.get(f"/caderno?s={HICP}&s={GDP_PT}&escala=dupla&janela=5a")
    assert response.status_code == 200
    assert "não têm períodos comuns com valores numéricos" in visible(response.text)
    assert "chart-data" not in response.text
    assert response.text.count('<article class="card">') == 2


def test_print_opens_evidence_disclosure_with_real_inputs_and_links(tmp_path):
    path = build_site(tmp_path, [
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2010": "10000", "2019": "20000", "2024": "25000"}, at=T2),
    ])
    query = (f"/caderno?s={GDP_PT}&frequencia=anual&transformacao=base100"
             "&base=2019&janela=5a")
    probe = """() => {
      const details = document.querySelector('details.notebook-calculation');
      const link = details.querySelector('a[href*="/series/"]');
      const list = details.querySelector('.provenance-list');
      const nested = details.querySelector('details.table-details');
      const direct = [...details.querySelectorAll('.notebook-calculation-side')]
        .flatMap(side => [...side.querySelectorAll(':scope > table.analysis-inputs')]);
      return {
        open: details.open,
        linkVisible: link ? link.checkVisibility() : null,
        listHeight: list ? list.getBoundingClientRect().height : 0,
        directTables: direct.map(t => ({visible: t.checkVisibility(),
                                        height: t.getBoundingClientRect().height})),
        nestedOpen: nested ? nested.open : null,
        nestedVisible: nested ? nested.querySelector('table').checkVisibility() : null,
        svgHeight: document.querySelector('svg.chart')
          ? document.querySelector('svg.chart').getBoundingClientRect().height : 0,
        canvasDisplay: getComputedStyle(document.querySelector('.chart-canvas')).display,
      };
    }"""
    with live_site(path) as base_url, _chromium_browser() as browser:
        context = browser.new_context(viewport={"width": 1280, "height": 900},
                                      java_script_enabled=False)
        page = context.new_page()
        page.goto(f"{base_url}{query}", wait_until="networkidle")
        screen = page.evaluate(probe)
        # The disclosure is genuinely closed on screen and needs no JavaScript to render.
        assert screen["open"] is False
        assert screen["linkVisible"] is False

        page.emulate_media(media="print")
        printed = page.evaluate(probe)
        assert printed["open"] is False  # the open attribute did not change
        assert printed["linkVisible"] is True
        assert printed["listHeight"] > 0
        assert len(printed["directTables"]) == 2
        assert all(row["visible"] and row["height"] > 0
                   for row in printed["directTables"])
        assert printed["nestedOpen"] is False
        assert printed["nestedVisible"] is True
        assert printed["svgHeight"] > 0
        assert printed["canvasDisplay"] == "none"
        body = page.locator("details.notebook-calculation").inner_text()
        assert "Fórmula" in body and "100 × valor ÷ valor do ano de base" in body
        assert "Ano de base" in body and "2019 (explícito)" in body
        assert "Último valor calculado" in body and "Valor de base" in body
        assert "Abrir série original" in body
        assert "Entradas originais" in body
        context.close()


def test_base_control_matches_enlarged_controls_at_mobile_widths(tmp_path):
    path = build_site(tmp_path, [
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT", {"2024": "25000"}, at=T2),
    ])
    probe = """() => {
      const read = (el) => {
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {font: parseFloat(style.fontSize), minHeight: parseFloat(style.minHeight),
                height: rect.height, left: rect.left, right: rect.right};
      };
      return {
        base: read(document.querySelector('input[name="base"]')),
        select: read(document.querySelector('select[name="transformacao"]')),
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      };
    }"""
    with live_site(path) as base_url, _chromium_browser() as browser:
        page = browser.new_page(viewport={"width": 320, "height": 900})
        page.goto(f"{base_url}/caderno?s={GDP_PT}&grafico=off&base=2019",
                  wait_until="networkidle")
        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 900})
            boxes = page.evaluate(probe)
            for control in (boxes["base"], boxes["select"]):
                assert control["font"] >= 25.2
                assert control["minHeight"] >= 52
                assert control["height"] >= 52
            assert boxes["base"]["left"] >= 0
            assert boxes["base"]["right"] <= boxes["innerWidth"] + 0.5
            assert boxes["scrollWidth"] <= boxes["innerWidth"] + 1
        page.close()


def test_analysis_settings_parse_only_valid_combinations_and_keep_the_old_order():
    assert parse("") == ChartSettings()
    settings = parse("frequencia=anual&transformacao=base100&base=2023")
    assert settings == ChartSettings(frequency="anual", transform="base100", base="2023")
    assert settings.params() == [("frequencia", "anual"), ("transformacao", "base100"),
                                 ("base", "2023")]
    old = ChartSettings(mode="explicit", group=("b", "a"), scale="dupla", window="5a",
                        day="2026-11-01")
    assert old.params() == [("grafico", "on"), ("g", "b"), ("g", "a"), ("escala", "dupla"),
                            ("janela", "5a"), ("dia", "2026-11-01")]
    extended = ChartSettings(mode="explicit", group=("a",), scale="dupla", window="5a",
                             day="2026-11-01", frequency="anual", transform="pp",
                             base="2019")
    assert extended.params() == [
        ("grafico", "on"), ("g", "a"), ("escala", "dupla"), ("janela", "5a"),
        ("dia", "2026-11-01"), ("frequencia", "anual"), ("transformacao", "pp"),
        ("base", "2019")]
    assert parse("base=").base is None
    assert parse("base=0001").base == "0001"


def test_analysis_settings_reject_malformed_or_repeated_values():
    for query in (
        "frequencia=anual&frequencia=original",
        "frequencia=",
        "transformacao=pp&transformacao=original",
        "transformacao=index",
        "base=0",
        "base=0000",
        "base=20233",
        "base=abcd",
        "base=2020&base=2021",
    ):
        assert parse(query) is None, query


def test_removing_sides_preserves_analysis_settings_and_clears_only_the_group():
    settings = ChartSettings(mode="explicit", group=("a", "b"), window="5a",
                             frequency="anual", transform="base100", base="2019")
    pruned = without_side(settings, "a")
    assert pruned.group == ("b",)
    assert pruned.frequency == "anual" and pruned.transform == "base100"
    assert pruned.base == "2019" and pruned.window == "5a"
    cleared = without_all_sides(settings)
    assert cleared.mode == "off" and cleared.group == ()
    assert cleared.frequency == "anual" and cleared.transform == "base100"
    assert cleared.base == "2019"
    assert without_all_sides(ChartSettings()).mode == "all"
    assert notebook.selection_path(("a",), chart=cleared) == (
        "/caderno?s=a&grafico=off&janela=5a&frequencia=anual&transformacao=base100"
        "&base=2019")
