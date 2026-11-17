"""Regressions found by the independent legibility review."""
import re
import xml.etree.ElementTree as ET

import pytest

from app import chart_model
from app.charts import comparison_svg, line_chart
from tests.app.conftest import HICP, UNEMP


def ticks(svg):
    baseline = str(chart_model.HEIGHT - 20)
    return [node for node in ET.fromstring(svg).iter()
            if node.tag.endswith('text') and node.attrib.get('y') == baseline]


def test_monthly_endpoint_labels_grow_inwards_instead_of_clipping():
    svg = str(line_chart([{'period':f'2026-{month:02d}','value_text':'1.0'}
                          for month in (1,2,3)], frequency='M', title='Taxa'))
    labels = ticks(svg)
    assert len(labels) >= 2
    assert labels[0].attrib['text-anchor'] == 'start'
    assert labels[-1].attrib['text-anchor'] == 'end'
    assert labels[-1].text == 'mar 2026'


def test_long_left_unit_name_grows_into_the_plot():
    model = chart_model.comparison_model(
        [{'period':'2026-01','a':'100000','b':'1.0'},
         {'period':'2026-02','a':'101000','b':'1.5'}],
        frequency='M', title='Crédito e taxa', labels=('Crédito','Taxa'),
        unit_a='milhões de euros', unit_b='%', dual=True)
    assert model is not None
    svg = str(comparison_svg(model)).split('</svg>')[0] + '</svg>'
    names = [node for node in ET.fromstring(svg).iter()
             if node.tag.endswith('text') and node.attrib.get('class') == 'chart-axis-label']
    assert len(names) == 2
    assert names[0].text == 'milhões de euros'
    assert names[0].attrib['text-anchor'] == 'start'
    assert float(names[0].attrib['x']) == model.left
    assert names[1].attrib['text-anchor'] == 'end'


@pytest.mark.parametrize('prefix',['','/dados'])
def test_detail_start_actions_keep_the_public_mount(client, prefix):
    headers = {'X-Forwarded-Prefix':prefix}
    response = client.get('/series/'+HICP, headers=headers)
    assert response.status_code == 200
    assert f'href="{prefix}/caderno?s={HICP}"' in response.text
    response = client.get('/comparar/inflacao-e-desemprego', headers=headers)
    assert response.status_code == 200
    assert f'href="{prefix}/caderno?s={HICP}&amp;s={UNEMP}"' in response.text
    assert 'Criar caderno com estas duas séries' in response.text


def test_local_font_policy_does_not_enable_scripts_on_notebook(client):
    response = client.get('/caderno')
    policy = response.headers['content-security-policy']
    assert "font-src 'self'" in policy
    assert "default-src 'none'" in policy
    assert 'script-src' not in policy
    assert 'unsafe-inline' not in policy and 'unsafe-eval' not in policy
    assert re.search(r'<meta name="robots" content="noindex, follow">',response.text)
