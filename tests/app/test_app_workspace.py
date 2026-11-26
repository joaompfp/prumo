"""App-style surfaces preserve the notebook's native state and published CMS boundary."""
from pathlib import Path

from tests.app.conftest import HICP, UNEMP
from tests.app.test_notebook_workspace import dom, one

ROOT = Path(__file__).resolve().parents[2]


def test_settings_have_named_groups_and_every_native_control(client):
    response = client.get('/caderno', params=[('s', HICP), ('s', UNEMP)])
    assert response.status_code == 200
    root = dom(response.text)
    form = next(node for node in root.find_all('form')
                if node.attrs.get('id') == 'notebook-chart-form')
    groups = form.find_all('fieldset')
    assert len(groups) == 4
    legends = [one(group, 'legend').all_text().strip() for group in groups]
    assert legends[:2] == ['Período e escalas', 'Tratamento dos dados']
    assert legends[-1] == 'Séries de 15 minutos'
    assert {node.attrs.get('name') for node in form.find_all('select')} == {
        'janela', 'escala', 'frequencia', 'transformacao'}
    assert {node.attrs.get('name') for node in form.find_all('input')} >= {
        's', 'grafico', 'base', 'g', 'dia'}
    # Settings keep their form; point inspection stays outside it.
    assert not form.find_all('output')
    assert not [node for node in form.find_all('input') if node.attrs.get('type') == 'range']


def test_notebook_primary_add_and_secondary_settings_are_distinct(client):
    html = client.get('/caderno', params=[('s', HICP), ('s', UNEMP)]).text
    root = dom(html)
    toolbar = one(root, 'div', 'notebook-chart-links')
    links = toolbar.find_all('a')
    assert 'button' in links[0].classes()
    assert links[0].all_text().strip() == 'Acrescentar'
    assert 'button-quiet' in links[1].classes()
    assert links[1].attrs['href'] == '#definicoes'
    assert links[1].all_text().strip() == 'Configurar'
    assert all(link.find_all('svg') for link in links)
    method = one(root, 'details', 'notebook-method')
    assert 'Notas e método' in method.all_text()
    assert 'Comparar curvas no mesmo gráfico não estabelece uma relação de causa.' in method.all_text()
    assert one(root, 'p', 'notebook-caveat').parent.parent is method


def test_workspace_styles_are_local_prefix_safe_and_readable_in_preview(client):
    for prefix in ('', '/dados'):
        html = client.get('/comparar', headers={'X-Forwarded-Prefix': prefix}).text
        assert f'href="{prefix}/static/css/workspace.css"' in html
        assert 'directory-main' in html
    response = client.get('/static/css/workspace.css')
    assert response.status_code == 200
    assert response.content == (ROOT / 'static/css/workspace.css').read_bytes()
    css = response.text
    assert '.notebook-main .page-head h1 { font-family: var(--sans)' in css
    assert '.notebook-chart-options .settings-group' in css
    assert 'font-size: .9rem' in css
    assert 'position: fixed' not in css
    assert '.notebook-main { overflow: hidden' not in css
    assert '.notebook-chart { overflow: hidden' not in css
