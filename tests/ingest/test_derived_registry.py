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
    return {"key": key, "base": base, "formula": formula, "unit": "pp", **extra}


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
    with pytest.raises(ValueError, match=r"(?s)^derived\.a: invalid entry.*formula"):
        _load(tmp_path, [_entry(formula="median")])


def test_unknown_base_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a: unknown base"):
        _load(tmp_path, [_entry(base="nope")])


def test_active_entry_on_inactive_base_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a: active entry on inactive base"):
        _load(tmp_path, [_entry(base="s2")])


def test_inactive_entry_on_inactive_base_allowed(tmp_path):
    assert _load(tmp_path, [_entry(base="s2", active=False)])[0].active is False


@pytest.mark.parametrize("freq", ["D", "S", "PT15M"])
def test_daily_semester_and_pt15m_bases_rejected(tmp_path, freq):
    with pytest.raises(ValueError, match=r"derived.a: base frequency .* \(M/Q/A only\)"):
        _load(tmp_path, [_entry()], series=[_series("s1", frequency=freq)])


def test_decimal_comma_base_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a: base decimal separator"):
        _load(tmp_path, [_entry()], series=[_series("s1", decimal=",")])


def test_duplicate_key_rejected(tmp_path):
    with pytest.raises(ValueError, match="derived.a: duplicate key"):
        _load(tmp_path, [_entry(), _entry()])


def test_key_must_start_with_derived_and_not_shadow_series(tmp_path):
    with pytest.raises(ValueError, match="^plain: key must start with"):
        _load(tmp_path, [_entry("plain")])
    with pytest.raises(ValueError, match="^derived.s1: key equals a series id"):
        _load(tmp_path, [_entry("derived.s1")], series=[_series("derived.s1")])


@pytest.mark.parametrize("params", [{}, {"base_period": "2021-01", "x": "1"}, {"x": "1"}])
def test_rebase_requires_exactly_base_period_param(tmp_path, params):
    with pytest.raises(ValueError, match="derived.a: rebase_100 needs exactly params"):
        _load(tmp_path, [_entry(formula="rebase_100", params=params)])


@pytest.mark.parametrize("period", ["2021-13", "2021", "2021-1", "2021-Q1"])
def test_rebase_refuses_non_canonical_base_period_for_monthly(tmp_path, period):
    with pytest.raises(ValueError, match="derived.a: base_period .* not a canonical M period"):
        _load(tmp_path, [_entry(formula="rebase_100", params={"base_period": period})])


@pytest.mark.parametrize("freq,period", [("Q", "2021-Q1"), ("A", "2021")])
def test_rebase_base_period_positive_for_quarterly_and_annual(tmp_path, freq, period):
    out = _load(tmp_path, [_entry(formula="rebase_100", params={"base_period": period})],
                series=[_series("s1", frequency=freq)])
    assert out[0].params == {"base_period": period}


def test_rebase_base_period_wrong_frequency_form_rejected(tmp_path):
    with pytest.raises(ValueError, match="not a canonical Q period"):
        _load(tmp_path, [_entry(formula="rebase_100", params={"base_period": "2021-01"})],
              series=[_series("s1", frequency="Q")])


def test_int_base_period_raises_value_error_naming_key(tmp_path):
    with pytest.raises(ValueError, match="^derived.a: invalid entry"):
        _load(tmp_path, [_entry(formula="rebase_100", params={"base_period": 2021})],
              series=[_series("s1", frequency="A")])


def test_unknown_field_rejected_naming_key(tmp_path):
    with pytest.raises(ValueError, match="(?s)^derived.a: invalid entry.*foo"):
        _load(tmp_path, [_entry(foo="x")])


@pytest.mark.parametrize("unit", ["", "%", "EUR"])
def test_empty_or_non_code_unit_rejected(tmp_path, unit):
    with pytest.raises(ValueError, match=r"(?s)^derived.a: invalid entry.*unit"):
        _load(tmp_path, [_entry(unit=unit)])


def test_reader_text_label_is_not_a_registry_field(tmp_path):
    with pytest.raises(ValueError, match=r"(?s)^derived.a: invalid entry.*label"):
        _load(tmp_path, [_entry(label="Variação")])


def test_bare_derived_dot_key_rejected(tmp_path):
    with pytest.raises(ValueError, match="^derived.: key must start with"):
        _load(tmp_path, [_entry("derived.")])
    with pytest.raises(ValueError, match="(?s)invalid entry.*key"):
        _load(tmp_path, [_entry("")])


def test_non_mapping_entry_rejected(tmp_path):
    with pytest.raises(ValueError, match=r"^derived\[0\]: entry must be a mapping"):
        _load(tmp_path, ["derived.a"])


def test_non_list_section_rejected(tmp_path):
    with pytest.raises(ValueError, match="^derived: section must be a list"):
        _load(tmp_path, {"derived.a": _entry()})


def test_rebase_valid_base_period_loads(tmp_path):
    out = _load(tmp_path, [_entry(formula="rebase_100", params={"base_period": "2021-01"})])
    assert out[0].params == {"base_period": "2021-01"}


def test_params_refused_for_non_rebase(tmp_path):
    with pytest.raises(ValueError, match="derived.a: formula .* takes no params"):
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
