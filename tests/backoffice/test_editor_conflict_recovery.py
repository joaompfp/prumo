"""A validation round trip must never turn an old form into a current write token."""
import re

import pytest

from tests.backoffice.test_cms_routes import ORIGIN, Env, page_create, page_form


@pytest.mark.parametrize("failure", ["missing_note", "bad_href", "bad_model"])
def test_invalid_stale_save_keeps_stale_version_and_private_values(tmp_path, failure):
    env = Env(tmp_path)
    client = env.client()
    assert page_create(client).status_code == 303
    assert client.post('/cms/page/precos/save', data=page_form(1, title='Outra sessão'),
                       headers=ORIGIN).status_code == 303
    before = env.revisions('page', 'precos')
    form = page_form(1, title='Texto ainda por guardar', intro='Introdução privada')
    if failure == 'missing_note':
        form['note'] = ''
    elif failure == 'bad_href':
        form = page_form(1, title='Texto ainda por guardar', intro='Introdução privada',
                         blocks=[{'type': 'hero', 'title': 'Cabeçalho privado',
                                  'actions': [{'label': 'Ler mais', 'href': ''}]}])
    else:
        form['section'] = 'invalid'
    response = client.post('/cms/page/precos/save', data=form, headers=ORIGIN)
    assert response.status_code == 422
    assert 'Texto ainda por guardar' in response.text
    versions = re.findall(r'name="version" value="([^"]*)"', response.text)
    assert versions and set(versions) == {'1'}
    assert env.revisions('page', 'precos') == before
    assert env.meta('page', 'precos')['version'] == 2
