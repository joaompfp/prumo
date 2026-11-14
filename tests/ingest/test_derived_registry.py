import pytest
import yaml

from ingest.registry import load_derived, load_registry

SOURCES = {"fake": {"licence": "CC-BY-4.0", "licence_url": "https://l.example/l",
                    "attribution": "Fake", "redistribution_ok": True}}


def _series(sid, frequency="M", active=True, **extra):
    return {"id": sid, "source": "fake", "indicator_key": f"k_{sid}", "role": "primary",
            "theme": "economy", "geography": "PT", "frequency": frequency, "unit": "EUR",
            "active": active, **extra}


def _entry(key="derived.a", base="s1", formula="period_change", **extra):
    return {"key": key, "base": base, "formula": formula, "label": "Variação", "unit": "EUR", **extra}


def _load(tmp_path, derived, series=None):
    doc = {"sources": SOURCES, "series": series or [_series("s1"), _series("s2", active=False)]}
    if derived is not None:
        doc["derived"] = derived
    p = tmp_path / "core.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return load_derived(p, load_registry(p))


def test_absent_derived_section_gives_empty_list(tmp_path):
    assert _load(tmp_path, None) == []
    assert _load(tmp_path, []) == []


def test_valid_entries_load_in_file_order(tmp_path):
    out = _load(tmp_path, [_entry("derived.b"), _entry("derived.a", formula="rebase_100",
                                                        params={"base_period": "2021-01"})])
    assert [d.key for d in out] == ["derived.b", "derived.a"]
    assert out[0].active is True and out[0].params == {}


def test_unknown_formula_rejected(tmp_path):
    with pytest.raises(ValueError):
        _load(tmp_path, [_entry(formula="median")])


def test_unknown_base_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry(base="nope")])


def test_active_entry_on_inactive_base_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry(base="s2")])


def test_inactive_entry_on_inactive_base_allowed(tmp_path):
    assert _load(tmp_path, [_entry(base="s2", active=False)])[0].active is False


@pytest.mark.parametrize("freq", ["D", "S", "PT15M"])
def test_daily_semester_and_pt15m_bases_rejected(tmp_path, freq):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry()], series=[_series("s1", frequency=freq)])


def test_decimal_comma_base_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry()], series=[_series("s1", decimal=",")])


def test_duplicate_key_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry(), _entry()])


def test_key_must_start_with_derived_and_not_shadow_series(tmp_path):
    with pytest.raises(ValueError, match="plain"):
        _load(tmp_path, [_entry("plain")])
    with pytest.raises(ValueError, match="derived.s1"):
        _load(tmp_path, [_entry("derived.s1")], series=[_series("derived.s1")])


@pytest.mark.parametrize("params", [{}, {"base_period": "2021-13"}, {"base_period": "2021"},
                                    {"base_period": "2021-01", "x": "1"}])
def test_rebase_requires_valid_base_period(tmp_path, params):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry(formula="rebase_100", params=params)])


def test_rebase_valid_base_period_loads(tmp_path):
    out = _load(tmp_path, [_entry(formula="rebase_100", params={"base_period": "2021-01"})])
    assert out[0].params == {"base_period": "2021-01"}


def test_params_refused_for_non_rebase(tmp_path):
    with pytest.raises(ValueError, match="derived.a"):
        _load(tmp_path, [_entry(params={"base_period": "2021-01"})])


def test_load_registry_ignores_derived_section(tmp_path):
    with_d = _load(tmp_path, [_entry()])
    assert with_d
    p = tmp_path / "core.yaml"
    a = load_registry(p)
    doc = yaml.safe_load(p.read_text())
    del doc["derived"]
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    assert load_registry(p) == a
