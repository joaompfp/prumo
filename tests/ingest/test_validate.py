import pytest

from ingest.models import SeriesSpec, SourceSpec
from ingest.validate import RawRow, Rejection, validate


def make_spec(decimal=".", unit="EUR", frequency="M") -> SeriesSpec:
    return SeriesSpec(
        id="s1",
        source=SourceSpec(name="X", licence="CC", licence_url="http://x", attribution="X",
                          redistribution_ok=True),
        indicator_key="k", role="primary", theme="economy", geography="PT",
        frequency=frequency, unit=unit, decimal=decimal)


def row(period="2024-01", value="1", unit=None, flag=None) -> RawRow:
    return RawRow(period_raw=period, value_raw=value, unit_raw=unit, flag_raw=flag)


def reasons(rejs):
    return [r.reason for r in rejs]


def test_valid_row_accepted():
    obs, rej = validate(make_spec(), [row("2024-01", "12.5", "EUR", "p")])
    assert rej == []
    assert len(obs) == 1
    o = obs[0]
    assert (o.series_id, o.period, o.value_text, o.value, o.status_flag) == \
        ("s1", "2024-01", "12.5", 12.5, "p")


def test_bad_period():
    obs, rej = validate(make_spec(), [row("garbage", "1")])
    assert obs == []
    assert rej == [Rejection(period_raw="garbage", value_raw="1", reason="bad_period")]


def test_non_numeric():
    obs, rej = validate(make_spec(), [row("2024-01", "abc")])
    assert obs == [] and reasons(rej) == ["non_numeric"]


def test_dash_and_colon_are_non_numeric():
    obs, rej = validate(make_spec(), [row("2024-01", ":"), row("2024-02", "-")])
    assert obs == []
    assert reasons(rej) == ["non_numeric", "non_numeric"]


def test_unit_mismatch():
    obs, rej = validate(make_spec(unit="EUR"), [row(unit="USD")])
    assert obs == [] and reasons(rej) == ["unit_mismatch"]


def test_unit_absent_or_blank_accepted():
    obs, rej = validate(make_spec(), [row("2024-01", unit=None), row("2024-02", unit="  ")])
    assert rej == [] and len(obs) == 2


def test_unit_compared_after_strip_only():
    obs, rej = validate(make_spec(unit="EUR"), [row("2024-01", unit=" EUR "), row("2024-02", unit="eur")])
    assert [o.period for o in obs] == ["2024-01"]
    assert reasons(rej) == ["unit_mismatch"]


def test_duplicate_period_rejects_all_occurrences_even_identical():
    rows = [row("2024-01", "1"), row("2024-02", "5"), row("2024-01", "1"), row("jan", "3")]
    obs, rej = validate(make_spec(), rows)
    assert [o.period for o in obs] == ["2024-02"]
    assert [(r.period_raw, r.reason) for r in rej] == [
        ("2024-01", "duplicate_period"), ("2024-01", "duplicate_period"), ("jan", "bad_period")]


def test_duplicate_detected_on_normalized_period():
    rows = [row("2024-01", "1"), row("2024M01", "2")]
    obs, rej = validate(make_spec(), rows)
    assert obs == []
    assert [(r.period_raw, r.value_raw, r.reason) for r in rej] == [
        ("2024-01", "1", "duplicate_period"), ("2024M01", "2", "duplicate_period")]


def test_precedence_period_then_numeric_then_unit():
    obs, rej = validate(make_spec(unit="EUR"), [
        row("bad", "abc", "USD"), row("2024-01", "abc", "USD"), row("2024-02", "1", "USD")])
    assert obs == []
    assert reasons(rej) == ["bad_period", "non_numeric", "unit_mismatch"]


def test_comma_decimal_preserves_text():
    obs, rej = validate(make_spec(decimal=","), [row("2024-01", "1 234,5")])
    assert rej == []
    assert obs[0].value_text == "1 234,5"
    assert obs[0].value == 1234.5


def test_comma_text_rejected_under_dot_spec():
    obs, rej = validate(make_spec(decimal="."), [row("2024-01", "1 234,5")])
    assert obs == [] and reasons(rej) == ["non_numeric"]


def test_no_rounding():
    obs, _ = validate(make_spec(), [row("2024-01", "0.30000000000000004")])
    assert obs[0].value_text == "0.30000000000000004"
    assert obs[0].value == 0.30000000000000004


def test_value_whitespace_stripped_only():
    obs, _ = validate(make_spec(), [row("2024-01", "  7.50 ")])
    assert obs[0].value_text == "7.50"


def test_flag_passthrough_and_blank_is_none():
    obs, _ = validate(make_spec(), [row("2024-01", "1", flag="p"), row("2024-02", "1", flag=" "),
                                    row("2024-03", "1", flag=None)])
    assert [o.status_flag for o in obs] == ["p", None, None]


def test_order_preserved_and_period_normalized():
    rows = [row("2024-03", "3"), row("x", "1"), row("2024-01", "1"), row("y", "2")]
    obs, rej = validate(make_spec(), rows)
    assert [o.period for o in obs] == ["2024-03", "2024-01"]
    assert [r.period_raw for r in rej] == ["x", "y"]


def test_accepts_generator():
    obs, _ = validate(make_spec(), (row(f"2024-0{i}", str(i)) for i in range(1, 4)))
    assert len(obs) == 3


def test_none_value_is_non_numeric_and_none_period_is_bad_period():
    obs, rej = validate(make_spec(), [row("2024-01", None), row(None, "1"), row(None, None)])
    assert obs == []
    assert rej == [Rejection("2024-01", None, "non_numeric"),
                   Rejection(None, "1", "bad_period"),
                   Rejection(None, None, "bad_period")]


def test_none_row_does_not_abort_payload():
    obs, rej = validate(make_spec(), [row("2024-01", "1"), row("2024-02", None), row("2024-03", "3")])
    assert [o.period for o in obs] == ["2024-01", "2024-03"]
    assert reasons(rej) == ["non_numeric"]


@pytest.mark.parametrize("kwargs", [
    dict(period_raw="2024-01", value_raw=1.5),
    dict(period_raw="2024-01", value_raw=1),
    dict(period_raw="2024-01", value_raw=True),
    dict(period_raw="2024-01", value_raw=b"1"),
    dict(period_raw=2024, value_raw="1"),
    dict(period_raw="2024-01", value_raw="1", unit_raw=5),
    dict(period_raw="2024-01", value_raw="1", flag_raw=1.0),
])
def test_non_str_token_is_contract_violation(kwargs):
    with pytest.raises(TypeError, match="adapters must pass the publisher's token as a str"):
        RawRow(**kwargs)


def test_three_copies_all_duplicate():
    obs, rej = validate(make_spec(), [row("2024-01", "1"), row("2024-01", "1"), row("2024-01", "2")])
    assert obs == []
    assert reasons(rej) == ["duplicate_period"] * 3


def test_copy_failing_numeric_does_not_make_twin_duplicate():
    obs, rej = validate(make_spec(), [row("2024-01", "1"), row("2024-01", "abc")])
    assert [(o.period, o.value_text) for o in obs] == [("2024-01", "1")]
    assert rej == [Rejection("2024-01", "abc", "non_numeric")]


def test_copy_failing_unit_does_not_make_twin_duplicate():
    obs, rej = validate(make_spec(unit="EUR"), [row("2024-01", "1", "EUR"), row("2024-01", "2", "USD")])
    assert [(o.period, o.value_text) for o in obs] == [("2024-01", "1")]
    assert rej == [Rejection("2024-01", "2", "unit_mismatch")]


@pytest.mark.parametrize("bad", [-1, True, "0", 1.0])
def test_rawrow_response_index_must_be_non_negative_int(bad):
    with pytest.raises(TypeError, match="response_index"):
        RawRow(period_raw="2024-01", value_raw="1", response_index=bad)


def test_response_index_is_carried_to_observation_and_duplicates_span_pages():
    rows = [RawRow("2024-01", "1", response_index=0), RawRow("2024-02", "2", response_index=1),
            RawRow("2024-03", "3", response_index=0), RawRow("2024-03", "3", response_index=1)]
    obs, rej = validate(make_spec(), rows)
    assert [(o.period, o.response_index) for o in obs] == [("2024-01", 0), ("2024-02", 1)]
    assert reasons(rej) == ["duplicate_period", "duplicate_period"]
    assert "response_index" not in obs[0].model_dump()
