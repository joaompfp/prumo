from pathlib import Path

import pytest
import yaml

from presentation import (
    LANGUAGES,
    MissingText,
    calculated_attribution,
    caveat_text,
    derived_title,
    describe_formula,
    unit_text,
)
from presentation.catalog import en, pt

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
FORMULAS = ("period_change", "period_change_pct", "yoy_change", "yoy_change_pct", "rebase_100")


def test_pt_formula_text_is_verbatim():
    assert describe_formula("pt", "yoy_change_pct", {}, "ine.x") == \
        "Variação homóloga (%), calculada pelo Prumo a partir de ine.x"
    assert describe_formula("pt", "yoy_change", {}, "ine.x") == \
        "Variação homóloga (diferença), calculada pelo Prumo a partir de ine.x"
    assert describe_formula("pt", "period_change", {}, "ine.x") == \
        "Variação face ao período anterior (diferença), calculada pelo Prumo a partir de ine.x"
    assert describe_formula("pt", "period_change_pct", {}, "ine.x") == \
        "Variação face ao período anterior (%), calculada pelo Prumo a partir de ine.x"
    assert describe_formula("pt", "rebase_100", {"base_period": "2015"}, "ine.x") == \
        "Índice rebaseado (2015 = 100), calculado pelo Prumo a partir de ine.x"


def test_rebase_needs_base_period():
    with pytest.raises(ValueError):
        describe_formula("pt", "rebase_100", {}, "ine.x")


def test_pt_attribution_suffix():
    assert calculated_attribution("pt", "INE") == "INE — Calculado pelo Prumo"


def test_en_second_language():
    assert describe_formula("en", "yoy_change_pct", {}, "ine.x") == \
        "Year-on-year change (%), calculated by Prumo from ine.x"
    assert describe_formula("en", "rebase_100", {"base_period": "2015"}, "ine.x") == \
        "Rebased index (2015 = 100), calculated by Prumo from ine.x"
    for f in FORMULAS:
        assert "Prumo" in describe_formula("en", f, {"base_period": "2015"}, "ine.x")
    assert calculated_attribution("en", "INE") == "INE — Calculated by Prumo"
    assert unit_text("en", "balance") == "balance"


def test_units_and_caveats_pt():
    assert unit_text("pt", "pp") == "p.p."
    assert unit_text("pt", "balance") == "saldo"
    assert unit_text("pt", "index_2015_100") == "índice 2015=100"
    assert caveat_text("pt", "sa_base") == (
        "Calculado pelo Prumo sobre a série ajustada de sazonalidade; "
        "não é a taxa oficial do editor.")
    assert caveat_text("pt", "stock_base") == (
        "Calculado pelo Prumo sobre montantes em saldo (stocks); "
        "não é a taxa oficial do editor.")


def test_missing_key_raises():
    for call in (lambda: describe_formula("pt", "nope", {}, "x"),
                 lambda: unit_text("pt", "nope"),
                 lambda: caveat_text("en", "nope"),
                 lambda: derived_title("en", "nope")):
        with pytest.raises(MissingText):
            call()
    assert issubclass(MissingText, KeyError)


def test_unknown_language_raises():
    for call in (lambda: describe_formula("fr", "yoy_change", {}, "x"),
                 lambda: unit_text("fr", "pct"),
                 lambda: caveat_text("fr", "sa_base"),
                 lambda: derived_title("fr", "k"),
                 lambda: calculated_attribution("fr", "INE")):
        with pytest.raises(ValueError):
            call()


def test_catalog_covers_registry():
    assert LANGUAGES == ("pt", "en")
    rows = yaml.safe_load(REGISTRY.read_text())["derived"]
    assert len(rows) == 23
    for lang in LANGUAGES:
        for row in rows:
            assert row["formula"] in FORMULAS
            assert derived_title(lang, row["key"])
    for cat in (pt, en):
        assert set(cat.FORMULAS) == set(FORMULAS)
        assert set(cat.TITLES) == {r["key"] for r in rows}
        assert set(cat.UNITS) == {"pct", "pp", "balance", "index_2015_100"}
        assert set(cat.CAVEATS) == {"sa_base", "stock_base"}
    for row in rows:
        assert derived_title("pt", row["key"]) == row["label"]
