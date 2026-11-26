"""Scoped contract for the notebook's reader-configured shared chart.

Every request goes through the installed application, one read-only snapshot and the real
templates. The chart is checked at the same three surfaces the reader sees: the SVG/payload, the
complete table and the provenance of the last common period.
"""
import hashlib
import json
import re
from datetime import date
from html import unescape

from fastapi.testclient import TestClient

from app.main import create_app
from ingest.db import open_db
from ingest.models import SourceSpec
from ingest.registry import sync_registry
from tests.app.conftest import (
    EUROSTAT,
    HICP,
    INE,
    T1,
    T2,
    T3,
    UNEMP,
    fetch,
    make_spec,
)

ROBOTS = "noindex, follow"
FAMILIES = ("hicp_yoy", "unemployment_rate", "consumer_confidence", "credit_consumer",
            "credit_housing", "ipi_total", "euribor_3m", "pt_10y")
EREDES = SourceSpec(name="eredes", licence="CC BY 4.0",
                    licence_url="https://www.eredes.pt/termos", attribution="E-REDES",
                    redistribution_ok=True)


def client(path):
    return TestClient(create_app(str(path)))


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def chart_block(html: str) -> str:
    match = re.search(r'<details class="table-details">.*?</details>', html, re.S)
    assert match is not None
    return match.group(0)


def payload(html: str) -> dict:
    match = re.search(r'<script type="application/json" class="chart-data">(.*?)</script>',
                      html, re.S)
    assert match is not None
    return json.loads(match.group(1))


def chart_form(html: str) -> str:
    match = re.search(r'<form id="notebook-chart-form".*?</form>', html, re.S)
    assert match is not None
    return match.group(0)


def build_site(tmp_path, rows, name="notebook-chart.db"):
    """Build one served database: each row carries its spec overrides and fetched periods."""
    path = tmp_path / name
    db = open_db(path)
    try:
        specs = [make_spec(row["id"], key=row["key"], source=row.get("source", INE),
                           unit=row.get("unit", "%"), frequency=row.get("frequency", "M"),
                           geography=row.get("geography", "PT"),
                           multiplier=row.get("multiplier"),
                           base_year=row.get("base_year")) for row in rows]
        sync_registry(db, specs)
        for row in rows:
            fetch(db, row["id"], row["periods"], row.get("at", T1), flag=row.get("flag"),
                  source=row.get("source", INE).name)
    finally:
        db.close()
    return path


def monthly_periods(start_year, start_month, end_year, end_month):
    """Every canonical month from start to end inclusive, oldest first."""
    out = {}
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        out[f"{year:04d}-{month:02d}"] = "1.0"
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return out


def insert_served(path, series_id, period, value_text, value=0.0):
    """A stored nonnumeric token, which the public ingest path would quarantine.

    The render layer still has to exclude such a token safely, so the focused test writes one
    directly into a verified run and checks that the chart reports the exclusion.
    """
    db = open_db(path)
    try:
        run, raw, fetched = db.conn.execute(
            "SELECT dataset_run_id, raw_fetch_id, fetched_at FROM observation "
            "WHERE series_id = ? AND kind = 'fetched' ORDER BY id LIMIT 1", (series_id,)).fetchone()
        db.conn.execute(
            "INSERT INTO observation(series_id, period, value_text, value, kind, dataset_run_id, "
            "raw_fetch_id, fetched_at) VALUES (?, ?, ?, ?, 'fetched', ?, ?, ?)",
            (series_id, period, value_text, value, run, raw, fetched))
        db.conn.commit()
    finally:
        db.close()


def test_default_chart_uses_the_common_periods_and_matches_its_table(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.chart_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2026-08": "10.00", "2026-09": "11.50"}, "at": T1},
        {"id": "ine.chart_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-08": "20.00", "2026-09": "21.50"}, "at": T2,
         "flag": "provisional"},
    ])
    db = open_db(path)
    try:
        fetch(db, "ine.chart_a.PT", {"2026-10": "12.00"}, T3)
    finally:
        db.close()
    with client(path) as site:
        response = site.get("/caderno?s=ine.chart_a.PT&s=ine.chart_b.PT")
    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == ROBOTS
    html = response.text
    text = visible(html)
    data = payload(html)

    # The pair is intersected; A's own newest period is not drawn just because it exists.
    assert data["periods"] == ["agosto de 2026", "setembro de 2026"]
    assert data["display"] == [["10 milhões de euros", "20 milhões de euros"],
                               ["11,5 milhões de euros", "21,5 milhões de euros"]]
    table = chart_block(html)
    assert re.findall(r"<td>(agosto de 2026|setembro de 2026)</td>", table) == [
        "setembro de 2026", "agosto de 2026"]
    assert "outubro de 2026" not in visible(table)
    assert 'class="num">10' in table and 'class="num">20' in table
    assert "11,5" in table and "21,5" in table
    assert table.count("provisório") == 2

    # Provenance is the last plotted period on each side, not A's newer October value.
    assert "01/11/2026, 09:00 UTC" in text
    assert "02/11/2026, 09:00 UTC" in text
    assert "03/11/2026, 09:00 UTC" not in text
    assert "setembro de 2026" in text


def test_shared_scale_mismatch_is_readable_and_dual_axes_show_both_units(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.scale_a.PT", "key": "credit_consumer.PT.M", "unit": "%",
         "periods": {"2026-09": "1.0", "2026-10": "2.0"}},
        {"id": "ine.scale_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "10.0", "2026-10": "20.0"}},
    ])
    with client(path) as site:
        shared = site.get("/caderno?s=ine.scale_a.PT&s=ine.scale_b.PT")
        dual = site.get("/caderno?s=ine.scale_a.PT&s=ine.scale_b.PT&escala=dupla")
    assert shared.status_code == 200
    assert "não partilham a mesma unidade, multiplicador e base" in visible(shared.text)
    assert "chart-data" not in shared.text
    assert shared.text.count('<article class="card">') == 2

    assert dual.status_code == 200
    data = payload(dual.text)
    assert len(data["axes"]) == 2
    assert [axis["unit"] for axis in data["axes"]] == ["%", "milhões de euros"]
    assert "milhões de euros" in visible(dual.text) and "%" in visible(dual.text)
    assert "chart-data" in dual.text


def test_dual_scale_with_one_compatible_group_asks_for_the_common_scale(tmp_path):
    ids = [f"ine.dual_{position}.PT" for position in range(3)]
    path = build_site(tmp_path, [
        {"id": series_id, "key": f"{FAMILIES[position]}.PT.M",
         "periods": {"2026-09": f"{position + 1}.0", "2026-10": f"{position + 2}.0"}}
        for position, series_id in enumerate(ids)])
    with client(path) as site:
        response = site.get("/caderno?" + "&".join(
            [*(f"s={series_id}" for series_id in ids), "escala=dupla"]))
    assert response.status_code == 200
    text = visible(response.text)
    assert "Todas as séries escolhidas partilham a mesma unidade" in text
    assert "Use a escala comum" in text
    assert "exactamente duas séries" not in text
    assert "chart-data" not in response.text
    assert response.text.count('<article class="card">') == 3
    form = chart_form(response.text)
    assert 'value="dupla" selected' in form
    assert form.count('name="g"') == 3 and form.count(" checked") == 3


def test_dual_scale_after_a_deliberate_removal_is_a_state_not_a_404(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.dual_a.PT", "key": "credit_consumer.PT.M", "unit": "%",
         "periods": {"2026-09": "1.0", "2026-10": "2.0"}},
        {"id": "ine.dual_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "3.0", "2026-10": "4.0"}},
    ])
    with client(path) as site:
        ready = site.get("/caderno?s=ine.dual_a.PT&s=ine.dual_b.PT&escala=dupla")
        removed = site.get("/caderno?s=ine.dual_b.PT&grafico=on&g=ine.dual_b.PT&escala=dupla")
    assert ready.status_code == 200 and "chart-data" in ready.text
    assert removed.status_code == 200
    assert "Todas as séries escolhidas partilham a mesma unidade" in visible(removed.text)
    assert "exactamente duas séries" not in visible(removed.text)
    assert removed.text.count('<article class="card">') == 1
    assert "chart-data" not in removed.text


def test_three_series_in_two_scale_groups_get_grouped_axes_and_reader_labels(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.group_a.PT", "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2026-08": "2.0", "2026-09": "2.1"}},
        {"id": "ine.group_b.PT", "key": "unemployment_rate.PT.M", "unit": "%",
         "periods": {"2026-08": "6.0", "2026-09": "6.1"}},
        {"id": "ine.group_c.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-08": "100000", "2026-09": "101000"}},
    ])
    query = ("/caderno?s=ine.group_a.PT&s=ine.group_b.PT&s=ine.group_c.PT"
             "&grafico=on&g=ine.group_a.PT&g=ine.group_b.PT&g=ine.group_c.PT&escala=dupla")
    with client(path) as site:
        response = site.get(query)
    assert response.status_code == 200
    html = response.text
    data = payload(html)
    assert data["kind"] == "group" and len(data["axes"]) == 2
    assert [axis["unit"] for axis in data["axes"]] == ["%", "milhões de euros"]
    assert [series["axis"] for series in data["series"]] == [0, 0, 1]
    assert html.count('<article class="card">') == 3

    # The legend and the Caderno metadata state the membership in words.
    assert "Eixo esquerdo" in visible(html) and "Eixo direito" in visible(html)
    assert 'data-axis="0"' in html and 'data-axis="1"' in html
    sources = re.search(r'<ul class="notebook-chart-sources">.*?</ul>', html, re.S).group(0)
    assert sources.count("Eixo esquerdo") == 2
    assert sources.count("Eixo direito") == 1
    assert "milhões de euros" in sources and " %" in sources
    assert "segunda série" not in visible(html)

    # The settings expose the same groups and keep every chosen side.
    form = chart_form(html)
    assert "Eixos deste gráfico" in visible(form)
    assert form.count('name="g"') == 3 and form.count(" checked") == 3
    assert 'value="dupla" selected' in form
    canonical_match = re.search(r'id="ligacao-limpa" href="([^"]+)"', html)
    assert canonical_match is not None
    assert unescape(canonical_match.group(1)) == query


def test_group_axis_domains_include_a_later_members_extreme(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.ext_a.PT", "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2026-08": "1.0", "2026-09": "2.0"}},
        {"id": "ine.ext_b.PT", "key": "unemployment_rate.PT.M", "unit": "%",
         "periods": {"2026-08": "100.0", "2026-09": "200.0"}},
        {"id": "ine.ext_c.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-08": "1000", "2026-09": "2000"}},
        {"id": "ine.ext_d.PT", "key": "deposits_households.PT.M", "unit": "MEUR",
         "periods": {"2026-08": "100000", "2026-09": "200000"}},
    ])
    with client(path) as site:
        response = site.get(
            "/caderno?s=ine.ext_a.PT&s=ine.ext_b.PT&s=ine.ext_c.PT&s=ine.ext_d.PT"
            "&grafico=on&g=ine.ext_a.PT&g=ine.ext_b.PT&g=ine.ext_c.PT&g=ine.ext_d.PT"
            "&escala=dupla")
    assert response.status_code == 200
    data = payload(response.text)
    assert [series["axis"] for series in data["series"]] == [0, 0, 1, 1]
    left, right = data["axes"]
    assert left["min"] <= 1 and left["max"] >= 200
    assert right["min"] <= 1000 and right["max"] >= 200000


def test_dual_scale_with_three_groups_explains_the_limit_and_keeps_settings(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.limit_a.PT", "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2026-09": "1.0"}},
        {"id": "ine.limit_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "10.0"}},
        {"id": "ine.limit_c.PT", "key": "ipi_total.PT.M", "unit": "index_2021=100",
         "periods": {"2026-09": "100.0"}},
    ])
    with client(path) as site:
        response = site.get(
            "/caderno?s=ine.limit_a.PT&s=ine.limit_b.PT&s=ine.limit_c.PT"
            "&grafico=on&g=ine.limit_a.PT&g=ine.limit_b.PT&g=ine.limit_c.PT"
            "&escala=dupla&janela=5a")
    assert response.status_code == 200
    html = response.text
    text = visible(html)
    assert "no máximo dois grupos de unidade, multiplicador e base" in text
    assert "exactamente duas séries" not in text
    assert "chart-data" not in html
    assert html.count('<article class="card">') == 3
    form = chart_form(html)
    assert 'value="dupla" selected' in form
    assert 'value="5a" selected' in form
    assert form.count('name="g"') == 3 and form.count(" checked") == 3
    assert "g=ine.limit_a.PT" in html and "escala=dupla" in html and "janela=5a" in html


def test_two_series_dual_keeps_independent_axes_even_with_the_same_unit(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.pair_a.PT", "key": "hicp_yoy.PT.M", "unit": "%",
         "periods": {"2026-08": "1.0", "2026-09": "2.0"}},
        {"id": "ine.pair_b.PT", "key": "unemployment_rate.PT.M", "unit": "%",
         "periods": {"2026-08": "100.0", "2026-09": "200.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.pair_a.PT&s=ine.pair_b.PT&escala=dupla")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["kind"] == "comparison" and len(data["axes"]) == 2
    assert [axis["unit"] for axis in data["axes"]] == ["%", "%"]
    assert all("axis" not in series for series in data["series"])
    # The old pair legend stays byte-stable: two sides do not add grouped axis words.
    assert 'data-axis=' not in response.text


def test_mixed_frequency_uses_a_sparse_calendar_without_dropping_cards(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.freq_m.PT", "key": "credit_consumer.PT.M",
         "periods": {"2026-09": "1.0", "2026-10": "2.0"}},
        {"id": "ine.freq_a.PT", "key": "credit_housing.PT.A", "frequency": "A",
         "periods": {"2026": "10.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.freq_m.PT&s=ine.freq_a.PT")
    assert response.status_code == 200
    html = response.text
    data = payload(html)
    assert data["version"] == 2 and data["kind"] == "calendar"
    assert data["periods"] == ["01/01/2026", "01/09/2026", "01/10/2026"]
    # The annual side is present only on its own real start day; missing cells stay null.
    assert data["display"] == [[None, "10 %"],
                               ["1 %", None],
                               ["2 %", None]]
    assert data["cell_periods"] == [[None, "2026"],
                                    ["setembro de 2026", None],
                                    ["outubro de 2026", None]]
    assert "Últimos períodos por série" in visible(html)
    assert "último período comum" not in visible(html).lower()
    # The caption names the deferral instead of concatenating a bare chain of latest dates.
    caption = re.search(
        r'<figcaption class="notebook-chart-caption">.*?</figcaption>', html, re.S).group(0)
    assert "outubro de 2026 · 2026" not in visible(caption)
    assert "Datas por série em «Séries, eixos e fontes»." in visible(caption)
    sources = re.search(r'<ul class="notebook-chart-sources">.*?</ul>', html, re.S).group(0)
    assert "Período: outubro de 2026" in visible(sources)
    assert "Período: 2026" in visible(sources)
    assert html.count('<article class="card">') == 2
    assert "sem observação nesta posição temporal" in chart_block(html)


def test_no_common_period_is_unavailable_and_cards_stay(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.common_a.PT", "key": "credit_consumer.PT.M",
         "periods": {"2026-01": "1.0"}},
        {"id": "ine.common_b.PT", "key": "credit_housing.PT.M",
         "periods": {"2026-02": "2.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.common_a.PT&s=ine.common_b.PT")
    assert response.status_code == 200
    assert "não têm períodos comuns com valores numéricos" in visible(response.text)
    assert "chart-data" not in response.text
    assert response.text.count('<article class="card">') == 2


def test_nonfinite_tokens_and_bad_calendar_values_are_excluded_and_reported(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.bad_a.PT", "key": "credit_consumer.PT.M",
         "periods": {"2026-08": "1.0"}},
        {"id": "ine.bad_b.PT", "key": "credit_housing.PT.M",
         "periods": {"2026-08": "2.0"}},
    ])
    insert_served(path, "ine.bad_a.PT", "2026-09", "n.d.")
    insert_served(path, "ine.bad_b.PT", "2026-09", "3.0")
    insert_served(path, "ine.bad_a.PT", "2026-10", "4.0")
    insert_served(path, "ine.bad_b.PT", "2026-10", "NaN")
    with client(path) as site:
        response = site.get("/caderno?s=ine.bad_a.PT&s=ine.bad_b.PT")
    assert response.status_code == 200
    text = visible(response.text)
    assert "2 períodos comuns sem valor numérico ou data reconhecida" in text
    table = chart_block(response.text)
    assert "n.d." not in table and "NaN" not in table
    assert "agosto de 2026" in table and "setembro de 2026" not in table
    assert len(re.findall(r"<tr>\s*<td>", table)) == 1


def test_three_way_intersection_reports_every_excluded_side(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.three_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2026-01": "1.0", "2026-02": "2.0", "2026-03": "3.0"}},
        {"id": "ine.three_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-01": "4.0", "2026-02": "5.0"}},
        {"id": "ine.three_c.PT", "key": "ipi_total.PT.M", "unit": "MEUR",
         "periods": {"2026-01": "6.0", "2026-03": "7.0"}},
    ])
    ids = ("ine.three_a.PT", "ine.three_b.PT", "ine.three_c.PT")
    with client(path) as site:
        response = site.get("/caderno?" + "&".join(f"s={series_id}" for series_id in ids))
    assert response.status_code == 200
    assert payload(response.text)["periods"] == ["janeiro de 2026"]
    text = visible(response.text)
    assert "1 período comum, em janeiro de 2026." in text
    assert "2 períodos de" in text and "1 período de" in text
    assert "Todas as séries cobrem exactamente os mesmos períodos" not in text


def test_calendar_unparseable_period_is_dropped_before_the_model():
    from app import notebook_chart

    maps = [{"2026-13": {"value_text": "1.0"}}, {"2026-13": {"value_text": "2.0"}}]
    rows, unparsed = notebook_chart._finite_rows(["2026-13"], maps, "M")
    assert rows == [] and unparsed == 1
    maps = [{"2026-02": {"value_text": "1.0"}}, {"2026-02": {"value_text": "2.0"}}]
    rows, unparsed = notebook_chart._finite_rows(["2026-02"], maps, "M")
    assert len(rows) == 1 and unparsed == 0
    daily = [{"2026-11-01": {"value_text": "1.0"}}, {"2026-11-01": {"value_text": "2.0"}}]
    rows, unparsed = notebook_chart._finite_rows(["2026-11-01"], daily, "D")
    assert len(rows) == 1 and unparsed == 0
    assert notebook_chart._window_start("2026-11-02", "D", "10y") == "2016-11-02"

    # Canonical spelling only: strptime would accept `2026-1` and place it nowhere, which used
    # to turn the whole series into even spacing.
    assert notebook_chart._calendar_ok("2026-1", "M") is False
    assert notebook_chart._calendar_ok("2026-01", "M") is True
    assert notebook_chart._calendar_ok("2026-02-30", "D") is False
    assert notebook_chart._calendar_ok("2026-11-01", "D") is True
    assert notebook_chart._calendar_ok("2026-11-01T00:15:00", "PT15M") is False
    assert notebook_chart._calendar_ok("2026-11-01T00:15:00+00:00", "PT15M") is True


def test_same_title_from_two_publishers_gets_distinct_labels(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.pub_a.PT", "key": "hicp_yoy.PT.M", "periods": {"2026-09": "1.0",
                                                                  "2026-10": "2.0"}},
        {"id": "eurostat.pub_b.PT", "key": "hicp_yoy.PT.M", "source": EUROSTAT,
         "periods": {"2026-09": "3.0", "2026-10": "4.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.pub_a.PT&s=eurostat.pub_b.PT")
    assert response.status_code == 200
    assert "chart-data" in response.text
    assert "INE - Instituto Nacional de Estatística" in visible(response.text)
    assert "Eurostat" in visible(response.text)
    assert "não se distinguem" not in visible(response.text)


def test_duplicate_labels_return_a_readable_unavailable_state(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.same_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "1.0", "2026-10": "2.0"}},
        {"id": "ine.same_b.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "3.0", "2026-10": "4.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.same_a.PT&s=ine.same_b.PT")
    assert response.status_code == 200
    assert "não se distinguem pelo título e pela fonte" in visible(response.text)
    assert "chart-data" not in response.text
    assert response.text.count('<article class="card">') == 2


def test_more_than_six_implicit_sides_require_an_explicit_subset(tmp_path):
    ids = [f"ine.many_{position}.PT" for position in range(7)]
    path = build_site(tmp_path, [
        {"id": series_id, "key": f"{FAMILIES[position]}.PT.M",
         "periods": {"2026-09": f"{position + 1}.0", "2026-10": f"{position + 2}.0"}}
        for position, series_id in enumerate(ids)])
    selection = "&".join(f"s={series_id}" for series_id in ids)
    with client(path) as site:
        implicit = site.get(f"/caderno?{selection}")
        chosen = site.get(f"/caderno?{selection}&grafico=on&"
                          + "&".join(f"g={series_id}" for series_id in ids[:6]))
    assert implicit.status_code == 200
    assert "mais de seis séries elegíveis" in visible(implicit.text)
    assert "chart-data" not in implicit.text
    form = chart_form(implicit.text)
    assert form.count('name="g"') == 7
    assert " checked" not in form

    assert chosen.status_code == 200
    data = payload(chosen.text)
    assert len(data["series"]) == 6
    assert len(data["periods"]) == 2


def test_explicit_unavailable_side_makes_the_chart_unavailable_but_keeps_cards(site_path):
    with client(site_path) as site:
        response = site.get(f"/caderno?s={HICP}&s=ine.hicp_yoy.PT.old&grafico=on"
                            "&g=ine.hicp_yoy.PT.old")
    assert response.status_code == 200
    html = response.text
    assert html.count('<article class="card">') == 1
    assert "Uma das séries escolhidas já não pode ser mostrada" in visible(html)
    assert "chart-data" not in html
    assert f"/caderno?s={HICP}&amp;s=ine.hicp_yoy.PT.old&amp;grafico=on" in html


def test_rights_loss_keeps_the_addressed_selection_and_group(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.rights_a.PT", "key": "hicp_yoy.PT.M", "periods": {"2026-09": "1.0",
                                                                     "2026-10": "2.0"}},
        {"id": "eurostat.rights_b.PT", "key": "hicp_yoy.PT.M", "source": EUROSTAT,
         "periods": {"2026-09": "3.0", "2026-10": "4.0"}},
    ])
    db = open_db(path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = ?", (INE.name,))
        db.conn.commit()
    finally:
        db.close()
    with client(path) as site:
        response = site.get("/caderno?s=ine.rights_a.PT&s=eurostat.rights_b.PT"
                            "&grafico=on&g=ine.rights_a.PT")
    assert response.status_code == 200
    html = response.text
    assert html.count('<article class="card">') == 1
    assert "Uma das séries escolhidas já não pode ser mostrada" in visible(html)
    assert "chart-data" not in html
    # The whole addressed selection and the explicit group survive a rights loss.
    assert ("/caderno?s=ine.rights_a.PT&amp;s=eurostat.rights_b.PT"
            "&amp;grafico=on&amp;g=ine.rights_a.PT") in html


def test_interval_chart_uses_only_a_bounded_shared_day(tmp_path):
    path = build_site(tmp_path, [
        {"id": "eredes.market.PT", "key": "eredes_production_market.PT.PT15M",
         "source": EREDES, "unit": "GWh", "frequency": "PT15M",
         "periods": {"2026-11-01T00:00:00+00:00": "10.0",
                     "2026-11-01T00:15:00+00:00": "11.0",
                     "2026-11-01T00:30:00+00:00": "12.0",
                     "2026-11-02T00:00:00+00:00": "99.0"}},
        {"id": "eredes.special.PT", "key": "eredes_production_special.PT.PT15M",
         "source": EREDES, "unit": "GWh", "frequency": "PT15M",
         "periods": {"2026-11-01T00:00:00+00:00": "20.0",
                     "2026-11-01T00:15:00+00:00": "21.0",
                     "2026-11-01T00:30:00+00:00": "22.0",
                     "2026-11-02T00:00:00+00:00": "98.0"}},
    ])
    with client(path) as site:
        default = site.get("/caderno?s=eredes.market.PT&s=eredes.special.PT")
        one = site.get("/caderno?s=eredes.market.PT&s=eredes.special.PT&dia=2026-11-02")
        missing = site.get("/caderno?s=eredes.market.PT&s=eredes.special.PT&dia=2026-11-03")
    assert default.status_code == 200
    data = payload(default.text)
    assert data["periods"] == ["01/11/2026, 00:00 UTC", "01/11/2026, 00:15 UTC",
                               "01/11/2026, 00:30 UTC"]
    assert all(99.0 not in row for row in data["y"])
    assert "Dia UTC: 01/11/2026" in visible(default.text)

    assert one.status_code == 200
    assert "um período comum" in visible(one.text)
    assert len(payload(one.text)["periods"]) == 1

    assert missing.status_code == 200
    assert "O dia pedido não tem valores numéricos comuns" in visible(missing.text)
    assert "chart-data" not in missing.text


def test_window_is_bounded_and_anchored_on_the_newest_common_period(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.win_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2015-01": "1.0", "2020-01": "2.0", "2026-10": "3.0"}},
        {"id": "ine.win_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2015-01": "4.0", "2020-01": "5.0", "2026-10": "6.0"}},
    ])
    query = "s=ine.win_a.PT&s=ine.win_b.PT"
    with client(path) as site:
        ten = site.get(f"/caderno?{query}")
        five = site.get(f"/caderno?{query}&janela=5a")
        maximum = site.get(f"/caderno?{query}&janela=max")
    assert payload(ten.text)["periods"] == ["janeiro de 2020", "outubro de 2026"]
    assert "Janela: 10 anos" in visible(ten.text)
    assert payload(five.text)["periods"] == ["outubro de 2026"]
    assert "Janela: 5 anos" in visible(five.text)
    assert payload(maximum.text)["periods"] == ["janeiro de 2015", "janeiro de 2020",
                                               "outubro de 2026"]
    assert "Janela: Todo o histórico" in visible(maximum.text)


def test_window_reads_the_full_common_history_before_trimming(tmp_path):
    """A side whose own newest value is older must not hide an older shared period.

    The window is a display trim of the common history, never a read bound: A's own newest
    period (2026-10) is older than B's (2020-01) in the shared set, so the true anchor is
    2016-01 and a ten-year window reaches back to 2006-01.
    """
    path = build_site(tmp_path, [
        {"id": "ine.hist_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2006-01": "1.0", "2016-01": "2.0", "2026-10": "3.0"}},
        {"id": "ine.hist_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2006-01": "4.0", "2016-01": "5.0", "2020-01": "6.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.hist_a.PT&s=ine.hist_b.PT")
    assert response.status_code == 200
    assert payload(response.text)["periods"] == ["janeiro de 2006", "janeiro de 2016"]
    assert "de janeiro de 2006 a janeiro de 2016" in visible(response.text)


def test_window_anchors_on_the_newest_common_finite_period(tmp_path):
    """A newer common period without a numeric value cannot pull the window past 2016-09."""
    periods = monthly_periods(2016, 9, 2026, 9)
    assert len(periods) == 121
    path = build_site(tmp_path, [
        {"id": "ine.bound_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": periods},
        {"id": "ine.bound_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": periods},
    ])
    insert_served(path, "ine.bound_a.PT", "2026-10", "9.9")
    insert_served(path, "ine.bound_b.PT", "2026-10", "NaN")
    with client(path) as site:
        response = site.get("/caderno?s=ine.bound_a.PT&s=ine.bound_b.PT")
    assert response.status_code == 200
    data = payload(response.text)
    assert len(data["periods"]) == 121
    assert data["periods"][0] == "setembro de 2016"
    assert data["periods"][-1] == "setembro de 2026"
    text = visible(response.text)
    assert "de setembro de 2016 a setembro de 2026" in text
    assert "1 período comum sem valor numérico ou data reconhecida" in text


def test_window_does_not_anchor_on_a_newer_common_period_that_cannot_be_drawn(tmp_path):
    """The only drawable period is 2015-12; a non-finite 2026-10 must not hide it."""
    path = build_site(tmp_path, [
        {"id": "ine.finite_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2015-12": "1.0"}},
        {"id": "ine.finite_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2015-12": "2.0"}},
    ])
    insert_served(path, "ine.finite_a.PT", "2026-10", "3.0")
    insert_served(path, "ine.finite_b.PT", "2026-10", "NaN")
    with client(path) as site:
        response = site.get("/caderno?s=ine.finite_a.PT&s=ine.finite_b.PT")
    assert response.status_code == 200
    assert payload(response.text)["periods"] == ["dezembro de 2015"]
    assert "de dezembro de 2015 a dezembro de 2015" in visible(response.text)


def test_daily_chart_keeps_real_calendar_distance_and_breaks_the_gap(tmp_path):
    """Daily points sit a day or a year apart on the axis, and the gap breaks both lines."""
    days = {"2025-01-01": "1.0", "2025-01-02": "2.0", "2025-12-31": "3.0"}
    path = build_site(tmp_path, [
        {"id": "ine.day_a.PT", "key": "credit_consumer.PT.D", "frequency": "D",
         "periods": days},
        {"id": "ine.day_b.PT", "key": "credit_housing.PT.D", "frequency": "D",
         "periods": {"2025-01-01": "4.0", "2025-01-02": "5.0", "2025-12-31": "6.0"}},
    ])
    with client(path) as site:
        response = site.get("/caderno?s=ine.day_a.PT&s=ine.day_b.PT")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["periods"] == ["01/01/2025", "02/01/2025", "31/12/2025"]
    assert data["x"] == [float(date(2025, 1, 1).toordinal()),
                         float(date(2025, 1, 2).toordinal()),
                         float(date(2025, 12, 31).toordinal())]
    assert data["x"][2] - data["x"][1] == 363 * (data["x"][1] - data["x"][0])
    assert data["breaks"] == [2]
    # The SVG fallback must break at the same point the payload sentinel marks.
    paths = re.findall(r'class="chart-line chart-line-(?:a|b)" d="([^"]+)"', response.text)
    assert len(paths) == 2 and all(path.count("M") == 2 for path in paths)


def test_malformed_chart_parameters_are_404_before_any_database_read(tmp_path):
    absent = tmp_path / "absent.db"
    with client(absent) as site:
        for query in (
            "s=a&g=b",
            "s=a&" + "&".join(["g=a"] * 7),
            "s=a&dia=2026-02-30",
            "s=a&dia=2026-11-01&dia=2026-11-02",
            "s=a&grafico=on&grafico=off",
            "s=a&escala=mista",
            "s=a&janela=20a",
        ):
            response = site.get(f"/caderno?{query}")
            assert response.status_code == 404, query
            assert "Serviço indisponível" not in response.text
            assert response.headers["x-robots-tag"] == ROBOTS
        # A valid address would reach the missing database, proving the 404s above happened
        # before any read-only handle was opened.
        assert site.get("/caderno?s=a").status_code == 503


def test_chart_head_csp_script_and_noindex_are_state_consistent(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.head_a.PT", "key": "credit_consumer.PT.M",
         "periods": {"2026-09": "1.0", "2026-10": "2.0"}},
        {"id": "ine.head_b.PT", "key": "credit_housing.PT.M",
         "periods": {"2026-09": "3.0", "2026-10": "4.0"}},
    ])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    ready = "/caderno?s=ine.head_a.PT&s=ine.head_b.PT"
    with client(path) as site:
        response = site.get(ready)
        head = site.head(ready)
        off = site.get(f"{ready}&grafico=off")
        empty = site.get(f"{ready}&grafico=on")
        unavailable = site.get(f"{ready}&escala=dupla&g=ine.head_a.PT")
    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == ROBOTS
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert 'src="/static/js/prumo-charts' in response.text
    assert head.status_code == 200 and head.text == ""
    assert head.headers["x-robots-tag"] == ROBOTS

    for response in (off, empty):
        assert response.status_code == 200
        assert "script-src" not in response.headers["content-security-policy"]
        assert "chart-data" not in response.text
        assert "prumo-charts" not in response.text
        assert response.headers["x-robots-tag"] == ROBOTS
    assert unavailable.status_code == 200
    assert "chart-data" not in unavailable.text
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_search_and_card_actions_preserve_or_prune_the_chart_settings(tmp_path):
    path = build_site(tmp_path, [
        {"id": "ine.act_a.PT", "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "1.0", "2026-10": "2.0"}},
        {"id": "ine.act_b.PT", "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": {"2026-09": "3.0", "2026-10": "4.0"}},
        {"id": "ine.act_c.PT", "key": "consumer_confidence.PT.M",
         "periods": {"2026-09": "5.0", "2026-10": "6.0"}},
    ])
    with client(path) as site:
        response = site.get(
            "/caderno?s=ine.act_a.PT&s=ine.act_b.PT&grafico=on&g=ine.act_a.PT&g=ine.act_b.PT"
            "&escala=dupla&janela=5a&q=confian%C3%A7a")
    html = response.text
    form = chart_form(html)
    assert form.count('name="s" value="ine.act_a.PT"') == 1
    assert form.count('name="s" value="ine.act_b.PT"') == 1
    assert 'name="grafico" value="on"' in form
    assert form.count('name="g" value="ine.act_a.PT"') == 1
    assert form.count('name="g" value="ine.act_b.PT"') == 1
    assert form.count('name="escala"') == 1 and 'value="dupla" selected' in form
    assert form.count('name="janela"') == 1 and 'value="5a" selected' in form
    search_form = re.search(r'<form id="notebook-search-form".*?</form>', html, re.S).group(0)
    assert 'name="grafico" value="on"' in search_form
    assert search_form.count('name="g" value=') == 2
    assert 'name="escala" value="dupla"' in search_form
    assert 'name="janela" value="5a"' in search_form

    batch_match = re.search(r'<form id="notebook-search-form".*?</form>', html, re.S)
    assert batch_match is not None
    batch = batch_match.group(0)
    assert 'action="/pesquisa"' in batch and 'name="acao" value="abrir"' in batch
    assert batch.count('name="s" value="ine.act_a.PT"') == 1
    assert batch.count('name="s" value="ine.act_b.PT"') == 1
    assert 'type="checkbox" name="s" value="ine.act_c.PT"' in batch
    assert 'name="grafico" value="on"' in batch
    assert batch.count('name="g" value=') == 2
    assert 'name="escala" value="dupla"' in batch and 'name="janela" value="5a"' in batch
    assert "Acrescentar selecionadas" in visible(batch)

    canonical = re.search(r'id="ligacao-limpa" href="([^"]+)"', html).group(1)
    assert canonical.startswith("/caderno?s=ine.act_a.PT&amp;s=ine.act_b.PT&amp;grafico=on")
    assert "q=" not in canonical

    # A native batch submission appends the checked result without silently joining it to the
    # explicit chart group; the hidden settings keep the reader's actual graph.
    with client(path) as site:
        added = site.get("/pesquisa", params=[
            ("s", "ine.act_a.PT"), ("s", "ine.act_b.PT"),
            ("ordem", "ine.act_a.PT"), ("ordem", "ine.act_b.PT"),
            ("s", "ine.act_c.PT"), ("grafico", "on"),
            ("g", "ine.act_a.PT"), ("g", "ine.act_b.PT"),
            ("escala", "dupla"), ("janela", "5a"), ("acao", "abrir")],
            follow_redirects=False)
    assert added.status_code == 303
    assert added.headers["location"] == (
        "/caderno?s=ine.act_a.PT&s=ine.act_b.PT&s=ine.act_c.PT&grafico=on"
        "&g=ine.act_a.PT&g=ine.act_b.PT&escala=dupla&janela=5a")

    # Unchecking a visible member removes it and prunes only its group side.
    with client(path) as site:
        pruned = site.get("/pesquisa", params=[
            ("ordem", "ine.act_a.PT"), ("ordem", "ine.act_b.PT"),
            ("s", "ine.act_b.PT"), ("grafico", "on"),
            ("g", "ine.act_a.PT"), ("g", "ine.act_b.PT"),
            ("escala", "dupla"), ("janela", "5a"), ("acao", "abrir")],
            follow_redirects=False)
    assert pruned.status_code == 303
    assert pruned.headers["location"] == (
        "/caderno?s=ine.act_b.PT&grafico=on&g=ine.act_b.PT&escala=dupla&janela=5a")

    with client(path) as site:
        last = site.get("/caderno?s=ine.act_a.PT&s=ine.act_b.PT&grafico=on&g=ine.act_a.PT")
    remove = re.search(r'class="card-remove" href="([^"]+)"', last.text)
    assert remove is not None
    assert "grafico=off" in remove.group(1)
    assert "g=" not in remove.group(1)


def test_one_series_still_draws_a_chart(site_path):
    with client(site_path) as site:
        response = site.get(f"/caderno?s={HICP}")
    assert response.status_code == 200
    data = payload(response.text)
    assert data["kind"] == "line"
    assert len(data["series"]) == 1
    assert data["periods"] == ["agosto de 2026", "setembro de 2026", "outubro de 2026"]


def test_explicit_empty_and_off_states_keep_the_controls_and_never_select_all(site_path):
    with client(site_path) as site:
        empty = site.get(f"/caderno?s={HICP}&s={UNEMP}&grafico=on")
        off = site.get(f"/caderno?s={HICP}&s={UNEMP}&grafico=off")
    assert empty.status_code == 200
    assert "Não há séries escolhidas para o gráfico" in visible(empty.text)
    assert "chart-data" not in empty.text
    assert chart_form(empty.text).count(" checked") == 0

    assert off.status_code == 200
    assert "O gráfico está desativado nesta ligação" in visible(off.text)
    assert "Ativar gráfico" in visible(off.text)
    assert "chart-data" not in off.text


def test_chart_forms_and_scripts_respect_the_public_mount_prefix(site_path):
    url = f"/caderno?s={HICP}&s={UNEMP}&grafico=on&g={HICP}&g={UNEMP}"
    with client(site_path) as site:
        response = site.get(url, headers={"X-Forwarded-Prefix": "/dados"})
    html = response.text
    assert 'action="/dados/caderno"' in chart_form(html)
    assert 'action="/dados/pesquisa"' in re.search(
        r'<form id="notebook-search-form".*?</form>', html, re.S).group(0)
    assert 'src="/dados/static/js/prumo-charts' in html
    assert 'href="/caderno' not in html and 'action="/caderno' not in html
