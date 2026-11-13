import pytest
from pydantic import ValidationError

from ingest.models import Observation, normalize_period, parse_number

# --- PT15M: native quarter-hour timestamps (Task 16; single canonical UTC spelling) ----------

@pytest.mark.parametrize("raw", [
    "2026-11-10T23:45:00+00:00",
    "2023-01-01T00:00:00+00:00",  # E-REDES production first record (discovery fixture 04)
    "2026-11-11T00:00:00+00:00",  # E-REDES production latest record (discovery fixture 03)
    "2026-10-25T00:45:00+00:00",  # Europe/Lisbon DST end day: UTC is unaffected
    "2026-10-25T01:15:00+00:00",
    "2026-03-29T01:30:00+00:00",  # Europe/Lisbon DST start day
    "2024-02-29T12:15:00+00:00",  # leap day
])
def test_normalize_period_pt15m_accepts_canonical(raw):
    assert normalize_period(raw, "PT15M") == raw


@pytest.mark.parametrize("raw", [
    "2026-11-10T23:46:00+00:00",      # minute not a quarter hour
    "2026-11-10T23:01:00+00:00",
    "2026-11-10T23:45:01+00:00",      # seconds must be 00
    "2026-11-10T23:45:00",            # missing UTC offset
    "2026-11-10T23:45:00Z",           # 'Z' spelling is not the canonical '+00:00'
    "2026-11-10 23:45:00+00:00",      # space separator, not 'T'
    "2026-11-10T23:45:00+01:00",      # non-UTC offset
    "2026-11-10T23:45:00.000+00:00",  # fractional seconds
    "2026-11-10T23:45+00:00",         # missing seconds
    "2026-02-30T00:00:00+00:00",      # no such Gregorian date
    "2025-02-29T00:00:00+00:00",      # 2025 is not a leap year
    "2026-13-10T00:00:00+00:00",      # month 13
    "2026-11-10T24:00:00+00:00",      # no such hour
    "2026-11-10",                     # a date is D, not PT15M
    "٢٠٢٦-١١-١٠T٢٣:٤٥:٠٠+٠٠:٠٠",       # non-ASCII digits (Arabic-Indic)
    "2026-11-10T23:45:00-00:00",      # negative zero offset is not the canonical spelling
    " 2026-11-10T23:45:00+00:00Z",    # trailing junk
    # Task 16 spec review R2: PT15M matches the RAW string - no fold/strip/unicode normalize
    "2026-11-10t23:45:00+00:00",      # lowercase t: T must be uppercase
    " 2026-11-10T23:45:00+00:00",     # leading whitespace is not stripped
    "2026-11-10T23:45:00+00:00 ",     # trailing whitespace is not stripped
    "２０２６-１１-１０Ｔ２３：４５：００＋００：００",  # fullwidth tokens (NFKD would fold them)
])
def test_normalize_period_pt15m_rejects_noncanonical(raw):
    with pytest.raises(ValueError):
        normalize_period(raw, "PT15M")


@pytest.mark.parametrize("freq", ["A", "S", "Q", "M", "D"])
def test_normalize_period_pt15m_timestamp_is_not_a_coarser_period(freq):
    with pytest.raises(ValueError):
        normalize_period("2026-11-10T23:45:00+00:00", freq)


@pytest.mark.parametrize("raw,freq,expected", [
    ("Setembro de 2025", "M", "2025-09"),
    ("setembro de 2025", "M", "2025-09"),
    ("Março de 2025", "M", "2025-03"),
    ("2025", "A", "2025"),
    ("2025Q3", "Q", "2025-Q3"),
    ("3º Trimestre de 2025", "Q", "2025-Q3"),
    # INE's own quarterly labels, as returned live by pindica.jsp (varcd 0010704, 2026-11-11)
    ("1.º Trimestre de 2011", "Q", "2011-Q1"),
    ("4.º Trimestre de 2024", "Q", "2024-Q4"),
    ("1.º Semestre de 2024", "S", "2024-S1"),
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
    ("5.º Trimestre de 2024", "Q"), ("1.º Trimestre de 24", "Q"), ("Trimestre de 2024", "Q"),
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


def test_parse_decimal_is_exact_and_follows_parse_number_rules():
    from decimal import Decimal

    from ingest.models import parse_decimal
    assert parse_decimal("1.10") == Decimal("1.1")
    assert parse_decimal("1.234,50", ",") == Decimal("1234.5")
    assert parse_decimal("0.30000000000000004") != Decimal("0.3")
    for bad in ("1,23", "nan", "1e3", ""):
        with pytest.raises(ValueError):
            parse_decimal(bad)
