import pytest

from ingest.db import open_db


@pytest.fixture
def db(tmp_path):
    d = open_db(tmp_path / "prumo.db")
    yield d
    d.close()
