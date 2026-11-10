import pytest
from pydantic import ValidationError

from ingest.models import Observation, normalize_period


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


def _obs(**kw):
    base = dict(series_id="s1", period="2025-09", value_text="1", value=1.0)
    base.update(kw)
    return Observation(**base)


@pytest.mark.parametrize("text", [":", "..", "", "n/d", "abc", "nan", "inf"])
def test_observation_rejects_non_numeric(text):
    with pytest.raises(ValidationError):
        Observation(series_id="s1", period="2025-09", value_text=text, value=text)


def test_observation_parses_comma_decimal_and_keeps_text():
    o = Observation(series_id="s1", period="2025-09", value_text="1 234,5", value="1 234,5")
    assert o.value == 1234.5
    assert o.value_text == "1 234,5"
    assert o.status_flag is None and o.released_at is None
