"""Curated Portugal comparisons on `/comparar`: eligibility, links and grouped Caderno.

The database carries the exact production series ids from
`docs/superpowers/handoff/reports/multiscale/curation.md`. Every index card must resolve against
the public catalogue on read and every advertised link must open the existing notebook path with
two explicit scale groups.
"""
import json
import re
from html import unescape

from fastapi.testclient import TestClient

from app import reads
from app.main import create_app
from ingest.db import open_db
from ingest.models import SeriesSpec, SourceSpec
from ingest.registry import sync_registry
from tests.app.conftest import EUROSTAT, T1, WORLDBANK, fetch

BP = SourceSpec(name="bportugal", licence="CC BY 4.0",
                licence_url="https://www.bportugal.pt/terms",
                attribution="Banco de Portugal", redistribution_ok=True)

RATES = ("bportugal.euribor_12m.EA", "bportugal.pt_10y.PT",
         "bportugal.credit_housing.PT", "bportugal.deposits_households.PT")
FINANCE = ("eurostat.gov_debt_pct_gdp.PT", "eurostat.gov_deficit_pct_gdp.PT",
           "eurostat.gdp_per_capita_eur.PT")
TRADE = ("worldbank.exports_pct_gdp.PT", "worldbank.imports_pct_gdp.PT",
         "eurostat.gdp_per_capita_eur.PT")
TITLES = ("Taxas de juro, crédito à habitação e depósitos",
          "Dívida pública, saldo orçamental e PIB per capita",
          "Comércio externo e PIB per capita")

_SERIES = (
    ("bportugal.euribor_12m.EA", BP, "euribor_12m.EA.M", "EA", "M", "%",
     {"2025-01": "2.50", "2026-09": "3.2470"}),
    ("bportugal.pt_10y.PT", BP, "pt_10y.PT.M", "PT", "M", "%",
     {"2025-01": "3.00", "2026-09": "3.85"}),
    ("bportugal.credit_housing.PT", BP, "credit_housing.PT.M", "PT", "M", "MEUR",
     {"2025-01": "118000", "2026-09": "120179"}),
    ("bportugal.deposits_households.PT", BP, "deposits_households.PT.M", "PT", "M", "MEUR",
     {"2025-01": "200000", "2026-09": "203204"}),
    ("eurostat.gov_debt_pct_gdp.PT", EUROSTAT, "eurostat_gov_debt_pct_gdp.PT.A", "PT", "A",
     "% GDP", {"2024": "88.0", "2025": "89.2"}),
    ("eurostat.gov_deficit_pct_gdp.PT", EUROSTAT, "eurostat_gov_deficit_pct_gdp.PT.A", "PT",
     "A", "% GDP", {"2024": "-1.0", "2025": "0.7"}),
    ("eurostat.gdp_per_capita_eur.PT", EUROSTAT, "eurostat_gdp_per_capita_eur.PT.A", "PT", "A",
     "EUR per capita", {"2024": "27000", "2025": "28560"}),
    ("worldbank.exports_pct_gdp.PT", WORLDBANK, "worldbank_exports_pct_gdp.PT.A", "PT", "A",
     "% PIB", {"2024": "42.0", "2025": "43.6580888492067"}),
    ("worldbank.imports_pct_gdp.PT", WORLDBANK, "worldbank_imports_pct_gdp.PT.A", "PT", "A",
     "% PIB", {"2024": "41.0", "2025": "42.7407881300597"}),
)


def build_site(tmp_path, name="portugal-comparisons.db"):
    path = tmp_path / name
    db = open_db(path)
    try:
        specs = [SeriesSpec(id=series_id, source=source, indicator_key=key, role="primary",
                            theme="economy", geography=geography, frequency=frequency,
                            unit=unit)
                 for series_id, source, key, geography, frequency, unit, _ in _SERIES]
        sync_registry(db, specs)
        for series_id, source, _key, _geography, _frequency, _unit, periods in _SERIES:
            fetch(db, series_id, periods, T1, source=source.name)
    finally:
        db.close()
    return path


def client(path):
    return TestClient(create_app(str(path)))


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def payload(html: str) -> dict:
    match = re.search(r'<script type="application/json" class="chart-data">(.*?)</script>',
                      html, re.S)
    assert match is not None
    return json.loads(match.group(1))


def caderno_links(html: str) -> list[str]:
    links = [unescape(link) for link in re.findall(r'href="(/caderno\?[^"]+)"', html)]
    return list(dict.fromkeys(links))


def test_index_advertises_the_three_curated_portugal_configurations(tmp_path):
    path = build_site(tmp_path)
    with client(path) as site:
        response = site.get("/comparar")
    assert response.status_code == 200
    html = response.text
    assert '<section class="portugal-comparisons"' in html
    assert "<h2 id=\"portugal\">Portugal</h2>" in html
    for title in TITLES:
        assert title in html
    assert html.count("Abrir no Caderno") == 3
    assert "não estabelece causalidade" in visible(html)

    links = caderno_links(html)
    assert len(links) == 3
    for link, ids in zip(links, (RATES, FINANCE, TRADE)):
        assert "grafico=on" in link and "escala=dupla" in link
        assert all(f"s={series_id}" in link for series_id in ids)
        assert all(f"g={series_id}" in link for series_id in ids)
    assert "Eixo esquerdo: % · Eixo direito: milhões de euros" in visible(html)
    assert visible(html).count("Eixo esquerdo: % do PIB · Eixo direito: euros por habitante") == 2


def test_every_curated_card_opens_a_grouped_caderno(tmp_path):
    path = build_site(tmp_path)
    expected = (
        (RATES, 4, ["%", "milhões de euros"], [0, 0, 1, 1]),
        (FINANCE, 3, ["% do PIB", "euros por habitante"], [0, 0, 1]),
        (TRADE, 3, ["% do PIB", "euros por habitante"], [0, 0, 1]),
    )
    with client(path) as site:
        links = caderno_links(site.get("/comparar").text)
        assert len(links) == 3
        for link, (ids, cards, units, axes) in zip(links, expected):
            response = site.get(link)
            assert response.status_code == 200, link
            data = payload(response.text)
            assert len(data["axes"]) == 2, link
            assert [axis["unit"] for axis in data["axes"]] == units
            assert [series["axis"] for series in data["series"]] == axes
            assert response.text.count('<article class="card">') == cards
            assert "Eixo esquerdo" in visible(response.text)
            assert "Eixo direito" in visible(response.text)
            assert all(series_id in response.text for series_id in ids)


def test_index_hides_a_configuration_when_a_source_loses_redistribution(tmp_path):
    path = build_site(tmp_path)
    with client(path) as site:
        assert all(title in site.get("/comparar").text for title in TITLES)
        rates_link = caderno_links(site.get("/comparar").text)[0]

    db = open_db(path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'bportugal'")
        db.conn.commit()
    finally:
        db.close()
    reads.clear_cache()

    with client(path) as site:
        html = site.get("/comparar").text
        assert TITLES[0] not in html
        assert TITLES[1] in html and TITLES[2] in html
        assert html.count("Abrir no Caderno") == 2

        response = site.get(rates_link)
    assert response.status_code == 200
    assert "chart-data" not in response.text
    assert "já não pode ser mostrada" in visible(response.text)
    assert "s=bportugal.euribor_12m.EA" in response.text


def test_index_hides_a_configuration_when_a_scale_signature_changes(tmp_path):
    path = build_site(tmp_path)
    db = open_db(path)
    try:
        db.conn.execute("UPDATE series SET unit = '% PIB' WHERE id = ?",
                        ("eurostat.gov_debt_pct_gdp.PT",))
        db.conn.commit()
    finally:
        db.close()
    reads.clear_cache()
    with client(path) as site:
        html = site.get("/comparar").text
    # The reviewed "% GDP" left group no longer matches the live raw token.
    assert TITLES[1] not in html
    assert TITLES[0] in html and TITLES[2] in html
    assert html.count("Abrir no Caderno") == 2


def test_portugal_links_carry_the_mount_prefix(tmp_path):
    path = build_site(tmp_path)
    with client(path) as site:
        html = site.get("/comparar", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert 'href="/dados/caderno?' in html
    assert html.count('href="/dados/caderno?') >= 3


def test_curated_copy_distinguishes_nominal_values_and_geography():
    from presentation.portugal_comparisons import definitions, text

    comparisons = definitions()
    assert "centradas em Portugal" in text().intro
    assert "nominais" in comparisons[0].summary
    assert "área do euro" in comparisons[0].caveat
    assert "a preços correntes" in comparisons[1].summary
    assert "a preços correntes" in comparisons[2].summary
