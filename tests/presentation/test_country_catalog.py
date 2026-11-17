"""The curated country catalogue: three reviewed groups over the same five countries.

The catalogue is code, not data: the registry must supply exactly the identities, unit,
frequency and native dimensions each group pins. A drift in either side is a catalogue defect,
not something a page may paper over by drawing a different series.
"""
from pathlib import Path

import pytest
import yaml

from presentation import (
    MissingText,
    country_comparison,
    country_comparison_countries,
    country_comparisons,
    country_comparisons_intro,
    country_comparisons_title,
)
from presentation.catalog import en, pt

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
SLUGS = ("eletricidade-domestica", "pib-por-habitante", "divida-publica")
COUNTRIES = ("PT", "ES", "FR", "DE", "IT")


def _registry():
    return yaml.safe_load(REGISTRY.read_text())


def test_three_groups_in_reading_order_over_five_countries():
    assert tuple(country_comparisons("pt")) == SLUGS
    assert country_comparison_countries("pt") == COUNTRIES
    assert len(set(COUNTRIES)) == 5
    assert country_comparisons_title("pt").strip()
    assert country_comparisons_intro("pt").strip()
    assert "escolha livre" in country_comparisons_intro("pt")


def test_every_group_declares_reviewed_meaning_and_pinned_dimensions():
    data = _registry()
    sources = data["sources"]
    for slug in SLUGS:
        group = country_comparison("pt", slug)
        assert group["family"].startswith("eurostat.")
        assert group["source"] == "eurostat" and sources["eurostat"]["redistribution_ok"]
        assert group["dataset"].strip()
        assert group["frequency"] in {"A", "S"}
        assert group["unit"].strip()
        assert group["dimensions"] and "geo" not in group["dimensions"]
        for key in ("title", "subtitle", "mechanism", "caption_note", "definition_note",
                    "notebook_action"):
            assert isinstance(group[key], str) and group[key].strip(), (slug, key)


def test_each_group_pins_exactly_the_fifteen_registry_identities():
    data = _registry()
    by_id = {row["id"]: row for row in data["series"]}
    for slug in SLUGS:
        group = country_comparison("pt", slug)
        for country in COUNTRIES:
            series_id = f"{group['family']}.{country}"
            row = by_id[series_id]
            assert row["active"] is True, series_id
            assert row["role"] == "primary", series_id
            assert row["source"] == group["source"], series_id
            assert row["geography"] == country, series_id
            assert row["frequency"] == group["frequency"], series_id
            assert row["unit"] == group["unit"], series_id
            assert row["indicator_key"] == (
                f"{group['family'].replace('.', '_')}.{country}.{group['frequency']}"
            ), series_id
            dataset, rest = row["native_code"].split(":", 1)
            assert dataset == group["dataset"], series_id
            dimensions = dict(part.split("=", 1) for part in rest.split(","))
            assert dimensions.pop("geo") == country, series_id
            assert dimensions == group["dimensions"], series_id


def test_every_group_uses_the_same_short_geography_labels():
    labels = [pt.GEOGRAPHIES[country] for country in COUNTRIES]
    assert labels == ["Portugal", "Espanha", "França", "Alemanha", "Itália"]
    assert len(set(labels)) == 5


def test_unknown_group_and_missing_key_raise_missing_text(monkeypatch):
    with pytest.raises(MissingText):
        country_comparison("pt", "nao-existe")
    broken = dict(pt.COUNTRY_COMPARISONS["pib-por-habitante"])
    del broken["subtitle"]
    monkeypatch.setitem(pt.COUNTRY_COMPARISONS, "pib-por-habitante", broken)
    with pytest.raises(MissingText):
        country_comparison("pt", "pib-por-habitante")


def test_english_catalogue_is_explicitly_empty_and_refuses():
    assert en.COUNTRY_COMPARISONS == {}
    assert en.COUNTRY_COMPARISONS_COUNTRIES == ()
    assert country_comparisons("en") == {}
    with pytest.raises(MissingText):
        country_comparison("en", "eletricidade-domestica")
