"""Chart captions distinguish analytical units from immutable publisher units."""
import re

from tests.app.test_notebook_analysis import GDP_ES, GDP_PT, gdp_row
from tests.app.test_notebook_chart import build_site, client, visible


def test_rebased_caption_names_both_units_and_calculated_state(tmp_path):
    path = build_site(tmp_path, [
        gdp_row(GDP_PT, "eurostat_gdp_per_capita_eur.PT.A", "PT",
                {"2015": "100.00", "2016": "110.00"}),
        gdp_row(GDP_ES, "eurostat_gdp_per_capita_eur.ES.A", "ES",
                {"2015": "200.00", "2016": "240.00"}),
    ])
    with client(path) as site:
        response = site.get("/caderno", params=[
            ("s", GDP_PT), ("s", GDP_ES), ("frequencia", "anual"),
            ("transformacao", "base100"), ("base", "2015")])
    assert response.status_code == 200
    match = re.search(r'<ul class="notebook-chart-sources">(.*?)</ul>', response.text, re.S)
    assert match is not None
    caption = visible(match.group(1))
    assert caption.count("calculado") == 2
    assert caption.count("Unidade do gráfico: índice (base 2015=100)") == 2
    assert caption.count("Unidade da fonte: euros por habitante") == 2


def test_methodology_explains_explicit_views_without_claiming_official_inflation(tmp_path):
    path = build_site(tmp_path, [])
    with client(path) as site:
        response = site.get("/metodologia")
    assert response.status_code == 200
    text = visible(response.text)
    assert "Comparação temporal no Caderno" in text
    assert "não é a inflação anual oficial" in text
    assert "seis casas decimais" in text
    assert "não a data de publicação ou medição" in text
    assert "sem alterar a base de dados" in text
