"""PT reader formatting is bounded without changing source tokens."""
from decimal import Decimal

from app.formatting import (
    decimal_or_none,
    format_axis,
    format_count,
    format_date,
    format_datetime,
    format_period,
    format_value,
)


def test_value_limits_decimals_and_groups_thousands():
    assert format_value("1234567.80") == "1\u00a0234\u00a0567,8"
    assert format_value("3.90") == "3,9"
    assert format_value("3.9") == "3,9"
    assert format_value("-0.50") == "-0,5"
    assert format_value("0") == "0"


def test_unparseable_token_is_returned_unchanged():
    assert format_value("n/d") == "n/d"
    assert format_value("1,5") == "1,5"


def test_axis_ticks_round_and_use_pt_separators():
    assert format_axis(Decimal("5000")) == "5\u00a0000"
    assert format_axis(Decimal("2.5")) == "2,5"
    assert format_axis(Decimal("-0.25")) == "-0,25"
    assert format_axis(Decimal("0.0001")) == "1e-4"


def test_periods_in_portuguese():
    assert format_period("2026", "A") == "2026"
    assert format_period("2026-10", "M") == "outubro de 2026"
    assert format_period("2026-Q1", "Q") == "1.º trimestre de 2026"
    assert format_period("2026-S2", "S") == "2.º semestre de 2026"
    assert format_period("2026-11-13", "D") == "13/11/2026"
    assert format_period("2026-11-13T14:30:00+00:00", "PT15M") == "13/11/2026, 14:30 UTC"


def test_unknown_period_shape_falls_back_to_the_stored_string():
    assert format_period("2026-Q9", "Q") == "2026-Q9"


def test_timestamps_are_utc():
    assert format_datetime("2026-11-15T08:49:47.174522+00:00") == "15/11/2026, 08:49 UTC"
    assert format_datetime("2026-11-15T10:49:47+02:00") == "15/11/2026, 08:49 UTC"
    assert format_date("2026-11-15T08:49:47+00:00") == "15/11/2026"
    assert format_datetime(None) == ""


def test_counts_are_grouped():
    assert format_count(1308) == "1\u00a0308"
    assert format_count(0) == "0"


def test_decimal_helper_is_strict():
    assert decimal_or_none("1.50") == Decimal("1.50")
    assert decimal_or_none("n/d") is None
