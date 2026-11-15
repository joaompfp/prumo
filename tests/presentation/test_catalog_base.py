"""The base-series catalogue must cover every series the site can serve.

The registry is the authority: every active series whose source may be redistributed must
resolve a Portuguese family, geography, unit, theme, frequency and (when declared) adjustment,
so a page render can never fall back to a raw code.
"""
from pathlib import Path

import pytest
import yaml

from presentation import (
    MissingText,
    base_unit_text,
    family_title,
    flag_text,
    frequency_text,
    geography_name,
    seasonal_text,
    series_title,
    source_title,
    theme_text,
)
from presentation.catalog import en, pt

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"


def _registry():
    return yaml.safe_load(REGISTRY.read_text())


def _family(indicator_key: str) -> str:
    parts = indicator_key.split(".")
    return ".".join(parts[:-2]) if len(parts) >= 3 else indicator_key


def _served_series():
    data = _registry()
    rows = [s for s in data["series"]
            if s.get("active") is not False
            and data["sources"][s["source"]].get("redistribution_ok")]
    assert rows, "registry has no active redistributable series"
    return data, rows


def test_catalogue_covers_every_served_series():
    _, rows = _served_series()
    for s in rows:
        assert family_title("pt", _family(s["indicator_key"]))
        assert geography_name("pt", s["geography"])
        assert base_unit_text("pt", s["unit"])
        assert theme_text("pt", s["theme"])
        assert frequency_text("pt", s["frequency"])
        assert source_title("pt", s["source"])
        if s.get("seasonal_adjustment"):
            assert seasonal_text("pt", s["seasonal_adjustment"])


def test_catalogue_has_no_orphan_family_titles():
    _, rows = _served_series()
    used = {_family(s["indicator_key"]) for s in rows}
    assert set(pt.FAMILIES) == used


def test_series_title_composes_with_geography():
    assert series_title("pt", "ine_population", "PT") == "População residente — Portugal"
    assert series_title("pt", "unemployment_rate", "DE") == "Taxa de desemprego — Alemanha"
    assert series_title("pt", "eur_usd", "EA") == "Taxa de câmbio euro-dólar"


def test_flags_cover_the_stored_codes():
    assert set(pt.FLAGS) == {"normal", "estimated", "provisional", "break"}
    assert flag_text("pt", "provisional") == "provisório"
    assert flag_text("pt", "normal") == ""


def test_missing_base_key_raises():
    for call in (lambda: family_title("pt", "nope"),
                 lambda: geography_name("pt", "XX"),
                 lambda: base_unit_text("pt", "nope"),
                 lambda: flag_text("pt", "nope"),
                 lambda: theme_text("pt", "nope"),
                 lambda: frequency_text("pt", "nope"),
                 lambda: seasonal_text("pt", "nope"),
                 lambda: source_title("pt", "nope"),
                 lambda: series_title("pt", "nope", "PT")):
        with pytest.raises(MissingText):
            call()


def test_english_catalogue_is_explicitly_empty_and_refuses():
    assert en.FAMILIES == {}
    assert en.GEOGRAPHIES == {}
    assert en.SELF_LOCATING_FAMILIES == frozenset()
    with pytest.raises(MissingText):
        family_title("en", "ine_population")


def test_curated_home_resolves_to_active_series_and_declared_derived():
    data, rows = _served_series()
    ids = {s["id"] for s in rows}
    by_id = {s["id"]: s for s in rows}
    derived = {d["key"]: d for d in data["derived"]}
    assert 8 <= len(pt.CURATED_HOME) <= 16
    seen = set()
    for card in pt.CURATED_HOME:
        assert set(card) == {"series", "label", "derived"}
        assert card["series"] in ids, card["series"]
        assert card["series"] not in seen, f"duplicate curated series {card['series']}"
        seen.add(card["series"])
        assert by_id[card["series"]].get("role", "primary") == "primary"
        assert card["label"].strip()
        if card["derived"] is not None:
            assert card["derived"] in derived, card["derived"]
            assert derived[card["derived"]]["base"] == card["series"]
            assert derived[card["derived"]].get("active") is not False


def test_no_visible_text_is_a_raw_code():
    # Units whose publisher symbol is already the reader text ('%', 'GWh', ...) may match.
    identical_ok = {"%", "anos", "GWh", "kWh"}
    for table in (pt.FAMILIES, pt.GEOGRAPHIES, pt.BASE_UNITS, pt.THEMES,
                  pt.FREQUENCIES, pt.SOURCE_TITLES):
        for code, text in table.items():
            assert text.strip(), code
            if table is pt.BASE_UNITS and code in identical_ok:
                continue
            assert text != code, code
