"""Shared backoffice fixtures: a registry YAML on disk plus a real migrated DB written through
the production Db/registry paths (the same helpers the Task 1 read tests use)."""
from datetime import datetime, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from backoffice.app import create_app
from ingest.db import open_db
from ingest.registry import load_registry, sync_registry

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)

SOURCES = {
    "fake": {"licence": "CC-BY-4.0", "licence_url": "https://l.example/licence",
             "attribution": "Fake publisher", "redistribution_ok": True},
    "other": {"licence": "restricted", "licence_url": "http://other.example/terms",
              "attribution": "Other", "redistribution_ok": False},
}


def series_row(sid, *, source="fake", active=True, theme="economy", geography="PT",
               frequency="A", unit="EUR", **extra):
    return {"id": sid, "source": source, "indicator_key": f"k_{sid}", "role": "primary",
            "theme": theme, "geography": geography, "frequency": frequency, "unit": unit,
            "active": active, **extra}


DEFAULT_SERIES = [
    series_row("s1", native_code="NC1", url="https://pub.example/s1"),
    series_row("s2", active=False),
    series_row("o1", source="other", theme="energy", geography="EU27"),
]


class Env:
    """A registry + DB pair; `db()` opens it read-write for arranging data in a test."""

    def __init__(self, tmp_path, series):
        self.registry = tmp_path / "core.yaml"
        self.registry.write_text(yaml.safe_dump({"sources": SOURCES, "series": series},
                                                sort_keys=False))
        self.db_path = tmp_path / "prumo.sqlite3"
        self.specs = load_registry(self.registry)
        db = open_db(self.db_path)
        try:
            sync_registry(db, self.specs)
        finally:
            db.close()

    def db(self):
        return open_db(self.db_path)

    def client(self):
        return TestClient(create_app(self.db_path, self.registry, now=lambda: NOW))


@pytest.fixture
def make_env(tmp_path):
    return lambda series=DEFAULT_SERIES: Env(tmp_path, series)


@pytest.fixture
def env(make_env):
    return make_env()
