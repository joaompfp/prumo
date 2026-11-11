import textwrap

import pytest

from ingest.db import open_db
from ingest.registry import load_registry, sync_registry

SRC = {"licence": "CC-BY 4.0", "licence_url": "https://x/l", "attribution": "INE", "redistribution_ok": True}


def _series(sid, key="gdp", role="primary", source="ine"):
    return {"id": sid, "source": source, "indicator_key": key, "role": role, "theme": "economy",
            "geography": "PT", "frequency": "Q", "unit": "EUR"}


def _write(tmp_path, sources, series):
    import yaml
    p = tmp_path / "r.yaml"
    p.write_text(yaml.safe_dump({"sources": sources, "series": series}))
    return p


def test_core_registry_loads_and_syncs(tmp_path):
    """The committed (provisional) core registry is valid and syncs into a fresh DB."""
    from pathlib import Path
    root = Path(__file__).parents[2] / "registry"
    assert (root / "core.yaml").read_text() == (root / "core.proposed.yaml").read_text()
    assert (root / "core.yaml").read_text().startswith("# PROVISIONAL — owner review pending")
    specs = load_registry(root / "core.yaml")
    assert specs
    db = open_db(tmp_path / "fresh.db")
    try:
        sync_registry(db, specs)
        assert db.conn.execute("SELECT count(*) FROM series").fetchone()[0] == len(specs)
    finally:
        db.close()


def test_registry_loads_with_defaults(tmp_path):
    specs = load_registry(_write(tmp_path, {"ine": SRC}, [_series("a")]))
    assert specs[0].source.name == "ine"
    assert specs[0].schedule is None and specs[0].throttle_rps == 1.0
    assert specs[0].decimal == "."


def test_registry_decimal_roundtrip_and_validation(tmp_path):
    specs = load_registry(_write(tmp_path, {"ine": SRC}, [{**_series("a"), "decimal": ","}]))
    assert specs[0].decimal == ","
    with pytest.raises(ValueError):
        load_registry(_write(tmp_path, {"ine": SRC}, [{**_series("a"), "decimal": ";"}]))


def test_registry_exactly_one_primary_per_indicator_key(tmp_path):
    two = [_series("a"), _series("b")]
    with pytest.raises(ValueError, match="primary"):
        load_registry(_write(tmp_path, {"ine": SRC}, two))
    zero = [_series("a", role="cross_check")]
    with pytest.raises(ValueError, match="primary"):
        load_registry(_write(tmp_path, {"ine": SRC}, zero))
    ok = [_series("a"), _series("b", role="cross_check")]
    assert len(load_registry(_write(tmp_path, {"ine": SRC}, ok))) == 2


@pytest.mark.parametrize("missing", ["licence", "licence_url", "attribution", "redistribution_ok"])
def test_registry_requires_licence_fields(tmp_path, missing):
    src = {k: v for k, v in SRC.items() if k != missing}
    with pytest.raises(ValueError):
        load_registry(_write(tmp_path, {"ine": src}, [_series("a")]))


def test_registry_rejects_unknown_source(tmp_path):
    with pytest.raises(ValueError, match="source"):
        load_registry(_write(tmp_path, {}, [_series("a")]))


def test_registry_rejects_duplicate_series_id(tmp_path):
    s = [_series("a"), _series("a", key="other")]
    with pytest.raises(ValueError, match="duplicate"):
        load_registry(_write(tmp_path, {"ine": SRC}, s))


def test_sync_registry_idempotent(tmp_path):
    specs = load_registry(_write(tmp_path, {"ine": SRC}, [_series("a"), _series("b", role="cross_check")]))
    db = open_db(tmp_path / "t.db")
    sync_registry(db, specs)
    sync_registry(db, specs)
    assert db.conn.execute("SELECT count(*) FROM source").fetchone()[0] == 1
    assert db.conn.execute("SELECT count(*) FROM series").fetchone()[0] == 2
    row = db.conn.execute("SELECT redistribution_ok, licence FROM source").fetchone()
    assert tuple(row) == (1, "CC-BY 4.0")


def test_sync_registry_updates_changed_fields(tmp_path):
    db = open_db(tmp_path / "t.db")
    sync_registry(db, load_registry(_write(tmp_path, {"ine": SRC}, [_series("a")])))
    s = _series("a")
    s["unit"] = "USD"
    sync_registry(db, load_registry(_write(tmp_path, {"ine": {**SRC, "attribution": "New"}}, [s])))
    assert db.conn.execute("SELECT unit FROM series WHERE id='a'").fetchone()[0] == "USD"
    assert db.conn.execute("SELECT attribution FROM source").fetchone()[0] == "New"
