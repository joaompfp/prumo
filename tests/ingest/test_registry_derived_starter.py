"""Task 9: the starter `derived:` set in registry/core.yaml (project 3)."""
from pathlib import Path

import pytest

from ingest.registry import load_derived, load_registry

CORE = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
PCT_FORMULAS = {"period_change_pct", "yoy_change_pct"}
NO_PCT_UNITS = {"%", "balance", "% GDP"}
# Portuguese wording each label must carry for its formula (the reader-facing reading).
LABEL_WORDS = {
    "period_change": "variação face ao período anterior",
    "period_change_pct": "variação face ao período anterior",
    "yoy_change": "variação homóloga",
    "yoy_change_pct": "variação homóloga",
    "rebase_100": "índice",
}


@pytest.fixture(scope="module")
def specs():
    return {s.id: s for s in load_registry(CORE)}


@pytest.fixture(scope="module")
def derived(specs):
    return load_derived(CORE, list(specs.values()))


def test_starter_set_loads(derived):
    assert 20 <= len(derived) <= 60
    assert all(d.active for d in derived)


def test_starter_bases_are_active_redistributable_primary(derived, specs):
    for d in derived:
        base = specs[d.base]
        assert base.active, d.key
        assert base.source.redistribution_ok, d.key
        assert base.role == "primary", d.key
        assert base.frequency in {"M", "Q", "A"} and base.decimal == ".", d.key


def test_keys_follow_base_id_and_formula(derived):
    for d in derived:
        assert d.key == f"derived.{d.base.split('.', 1)[1]}.{d.formula}"


def test_no_pct_formula_on_percent_or_balance_units(derived, specs):
    for d in derived:
        if specs[d.base].unit in NO_PCT_UNITS:
            assert d.formula not in PCT_FORMULAS, d.key


def test_pp_entries_declare_pp_unit(derived, specs):
    for d in derived:
        if d.formula in {"period_change", "yoy_change"} and specs[d.base].unit == "%":
            assert d.unit == "p.p.", d.key
        if d.formula in PCT_FORMULAS:
            assert d.unit == "%", d.key


def test_every_label_is_nonempty_portuguese_text(derived):
    for d in derived:
        label = d.label.strip()
        assert label and label == d.label, d.key
        assert label != d.key and d.base not in label, d.key
        assert LABEL_WORDS[d.formula] in label.lower(), d.key
