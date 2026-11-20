"""Canonical native-period calendar tests."""
from datetime import date

import pytest

from analysis.periods import period_index, period_start


@pytest.mark.parametrize(("period", "frequency", "expected"), [
    ("2024", "A", date(2024, 1, 1)),
    ("0001", "A", date(1, 1, 1)),
    ("9999", "A", date(9999, 1, 1)),
    ("2024-S1", "S", date(2024, 1, 1)),
    ("2024-S2", "S", date(2024, 7, 1)),
    ("2024-Q1", "Q", date(2024, 1, 1)),
    ("2024-Q2", "Q", date(2024, 4, 1)),
    ("2024-Q3", "Q", date(2024, 7, 1)),
    ("2024-Q4", "Q", date(2024, 10, 1)),
    ("2024-01", "M", date(2024, 1, 1)),
    ("2024-12", "M", date(2024, 12, 1)),
    ("2024-02-29", "D", date(2024, 2, 29)),
    ("2000-02-29", "D", date(2000, 2, 29)),
    ("0001-01-01", "D", date(1, 1, 1)),
    ("9999-12-31", "D", date(9999, 12, 31)),
])
def test_period_start_canonical(period, frequency, expected):
    assert period_start(period, frequency) == expected


@pytest.mark.parametrize(("period", "frequency"), [
    ("2024-M01", "M"),
    ("2024-1", "M"),
    ("2024-01-01", "A"),
    ("2024-S3", "S"),
    ("2024-Q5", "Q"),
    ("2024-Q0", "Q"),
    ("2024-13", "M"),
    ("2024-00", "M"),
    ("2023-02-29", "D"),
    ("1900-02-29", "D"),
    ("2024-04-31", "D"),
    ("0000", "A"),
    ("0000-01", "M"),
    (" 2024", "A"),
    ("2024 ", "A"),
    ("2024/01", "M"),
    ("2024-q1", "Q"),
    ("2024\u201101", "M"),
    ("janeiro de 2024", "M"),
    ("2024年", "A"),
    ("٢٠٢٤", "A"),
    ("２０２４", "A"),
    ("2024-0２", "M"),
    ("2024-02-29T00:00:00+00:00", "D"),
])
def test_period_start_rejects_non_canonical_or_fictional(period, frequency):
    assert period_start(period, frequency) is None


@pytest.mark.parametrize("frequency", ["PT15M", "W", "", "a", "m"])
def test_period_start_unknown_frequency(frequency):
    assert period_start("2024-01", frequency) is None


def test_period_index_is_strictly_monotonic_and_detects_missing_periods():
    monthly = [f"2023-{month:02d}" for month in range(1, 13)] + [
        "2024-01", "2024-03"]
    indices = [period_index(period, "M") for period in monthly]
    assert all(index is not None for index in indices)
    assert [b - a for a, b in zip(indices, indices[1:])] == [1] * 12 + [2]

    for frequency, sequence, steps in [
        ("A", ["2022", "2023", "2025"], [1, 2]),
        ("S", ["2023-S2", "2024-S1", "2024-S2"], [1, 1]),
        ("Q", ["2024-Q3", "2024-Q4", "2025-Q2"], [1, 2]),
        ("M", ["2024-11", "2024-12", "2025-02"], [1, 2]),
        ("D", ["2024-02-28", "2024-02-29", "2024-03-01"], [1, 1]),
    ]:
        values = [period_index(period, frequency) for period in sequence]
        assert all(value is not None for value in values)
        assert [b - a for a, b in zip(values, values[1:])] == steps


def test_period_index_has_one_integer_per_native_period():
    for frequency, periods in {
        "A": ["2023", "2024", "2025"],
        "S": ["2023-S1", "2023-S2", "2024-S1", "2024-S2"],
        "Q": [f"2024-Q{quarter}" for quarter in range(1, 5)],
        "M": [f"2024-{month:02d}" for month in range(1, 13)],
        "D": [f"2024-02-{day:02d}" for day in range(1, 30)],
    }.items():
        indices = [period_index(period, frequency) for period in periods]
        assert len(set(indices)) == len(periods)


@pytest.mark.parametrize(("period", "frequency"), [
    ("2024-02-30", "D"),
    ("nope", "A"),
    ("2024-01", "PT15M"),
])
def test_period_index_invalid(period, frequency):
    assert period_index(period, frequency) is None
