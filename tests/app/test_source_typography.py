"""Old database metadata follows display typography without rewriting the source records."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.app.conftest import DERIVED, HICP


@pytest.mark.parametrize("path", [
    "/fontes",
    f"/series/{HICP}",
    "/comparar/inflacao-e-desemprego",
    f"/calculadas/{DERIVED}",
    f"/series/{HICP}.csv",
    f"/calculadas/{DERIVED}.csv",
])
def test_existing_source_metadata_is_normalised_only_for_display(site_path, path):
    if path.startswith("/comparar/"):
        from tests.app.cms_fixtures import publish_comparisons
        publish_comparisons(site_path, ("inflacao-e-desemprego",))
    dash = chr(0x2014)
    attribution = f"Instituição {dash} dados oficiais"
    licence = f"CC BY 4.0 {dash} atribuição obrigatória"
    with sqlite3.connect(site_path) as connection:
        connection.execute("UPDATE source SET attribution = ?, licence = ?",
                           (attribution, licence))
        before = connection.execute("SELECT * FROM source ORDER BY id").fetchall()
        observations = connection.execute("SELECT * FROM observation ORDER BY id").fetchall()

    with TestClient(create_app(str(site_path))) as client:
        response = client.get(path)
    assert response.status_code == 200
    assert dash not in response.text
    assert "Instituição - dados oficiais" in response.text
    assert "CC BY 4.0 - atribuição obrigatória" in response.text

    # A web-only release must work with the old worker's metadata and keep it immutable.
    with sqlite3.connect(site_path) as connection:
        assert connection.execute("SELECT * FROM source ORDER BY id").fetchall() == before
        assert connection.execute("SELECT * FROM observation ORDER BY id").fetchall() == observations
