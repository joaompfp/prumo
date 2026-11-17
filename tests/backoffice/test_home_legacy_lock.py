"""Old editor cannot change the home once its CMS draft exists."""
import sqlite3

import pytest

from tests.backoffice.test_cms_routes import ORIGIN, PREFIX, Env


def legacy_rows(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        return {name: db.execute(f"SELECT * FROM {name} ORDER BY rowid").fetchall()
                for name in ("editorial_page", "editorial_slot", "editorial_event")}


@pytest.mark.parametrize("prefix", ["", PREFIX])
def test_prepared_home_redirects_old_editor_and_refuses_every_old_action(tmp_path, prefix):
    env = Env(tmp_path)
    client = env.client()
    headers = {**ORIGIN, "X-Forwarded-Prefix": prefix}
    result = client.post("/cms/home/prepare", data={"note": "importar a página atual"},
                         headers=headers, follow_redirects=False)
    assert result.status_code == 303
    before = legacy_rows(env.db_path)
    response = client.get("/editorial/inicio", headers=headers, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"{prefix}/cms/page/inicio"
    for action in ("add", "move", "remove", "discard", "publish", "reset"):
        response = client.post(f"/editorial/inicio/{action}",
                               data={"version": "0", "note": "formulário antigo"},
                               headers=headers, follow_redirects=False)
        assert response.status_code == 409
        assert "já está no CMS" in response.text
    assert legacy_rows(env.db_path) == before
