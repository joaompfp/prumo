import pytest
from pydantic import ValidationError

from ingest.models import Observation, normalize_period, parse_number


@pytest.mark.parametrize("raw,freq,expected", [
    ("Setembro de 2025", "M", "2025-09"),
    ("setembro de 2025", "M", "2025-09"),
    ("Março de 2025", "M", "2025-03"),
    ("2025", "A", "2025"),
    ("2025Q3", "Q", "2025-Q3"),
    ("3º Trimestre de 2025", "Q", "2025-Q3"),
    ("2025-S1", "S", "2025-S1"),
    ("2025M09", "M", "2025-09"),
    ("2025-09", "M", "2025-09"),
    ("2025-09-30", "D", "2025-09-30"),
])
def test_normalize_period(raw, freq, expected):
    assert normalize_period(raw, freq) == expected


@pytest.mark.parametrize("raw,freq", [
    ("n/d", "M"), ("", "M"), ("2025-13", "M"), ("2025-Q5", "Q"),
    ("2025", "M"), ("2025-09", "A"), ("2025-02-30", "D"), ("2025-S3", "S"),
])
def test_normalize_period_rejects_garbage(raw, freq):
    with pytest.raises(ValueError):
        normalize_period(raw, freq)


@pytest.mark.parametrize("text", [":", "..", "", "n/d", "abc", "nan", "inf", "1e3", "\u22125",
                                  "(5)", "5%", "1_000", "1,23", "1,234,56", "\u0663"])
def test_observation_rejects_non_numeric(text):
    with pytest.raises(ValueError):
        Observation.from_raw("s1", "2025-09", text)


def test_observation_from_raw_keeps_text_and_parses():
    o = Observation.from_raw("s1", "2025-09", "1 234.5")
    assert (o.value, o.value_text) == (1234.5, "1 234.5")
    o = Observation.from_raw("s1", "2025-09", "1.234,5", decimal=",")
    assert (o.value, o.value_text) == (1234.5, "1.234,5")
    assert o.status_flag is None and o.released_at is None


def test_observation_consistent_pair_accepted():
    assert Observation(series_id="s", period="2025", value_text="1.5", value=1.5).value == 1.5


def test_observation_mismatched_value_rejected():
    with pytest.raises(ValidationError):
        Observation(series_id="s", period="2025", value_text="999", value=1.0)


def test_observation_non_numeric_text_rejected_even_with_numeric_value():
    with pytest.raises(ValidationError):
        Observation(series_id="s", period="2025", value_text="n/d", value=1.0)


@pytest.mark.parametrize("v", [True, False, "1.0"])
def test_observation_rejects_bool_and_str_value(v):
    with pytest.raises(ValidationError):
        Observation(series_id="s", period="2025", value_text="1", value=v)


@pytest.mark.parametrize("text,decimal,expected", [
    ("1.234", ".", 1.234), ("1.234", ",", 1234.0),
    ("1,234", ".", 1234.0), ("1,234", ",", 1.234),
    ("1,234.5", ".", 1234.5), ("1 234", ".", 1234.0), ("1\u00a0234", ".", 1234.0),
    ("1\u202f234,5", ",", 1234.5), ("1.234,5", ",", 1234.5), ("1 234,5", ",", 1234.5),
    ("-12,5", ",", -12.5), ("+3.5", ".", 3.5), ("0", ".", 0.0), ("1,234,567", ".", 1234567.0),
])
def test_parse_number_ok(text, decimal, expected):
    assert parse_number(text, decimal) == expected


@pytest.mark.parametrize("text,decimal", [
    ("1,23", "."), ("1,234,56", "."), ("1,234.5", ","), ("1.23.4", ","), ("12 34", "."),
    ("1,234 567", "."), ("", "."), ("1.", "."), ("1e3", "."), ("1_000", "."),
])
def test_parse_number_rejects(text, decimal):
    with pytest.raises(ValueError):
        parse_number(text, decimal)
