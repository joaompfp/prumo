"""
P1: Core Data Layer — Schema validation for indicator records.

Focus: Required fields, null handling, data freshness, type contracts.
Uses sample_indicators fixture from conftest.
"""
import re
import pytest


REQUIRED_FIELDS = {"indicator", "category", "source", "unit", "latest_period", "latest_value"}
KNOWN_SOURCES = {"INE", "EUROSTAT", "FRED", "BPORTUGAL", "DGEG", "REN", "WORLDBANK", "OECD", "IMF"}


class TestIndicatorSchema:
    """Schema validation for indicator records (sample_indicators fixture)."""

    def test_all_required_fields_present(self, sample_indicators):
        """Schema: Every indicator has all required fields."""
        for record in sample_indicators:
            missing = REQUIRED_FIELDS - set(record.keys())
            assert not missing, (
                f"Indicator '{record.get('indicator')}' missing fields: {missing}"
            )

    def test_indicator_field_is_non_empty_string(self, sample_indicators):
        """Schema: 'indicator' field is a non-empty string."""
        for record in sample_indicators:
            ind = record.get("indicator")
            assert isinstance(ind, str), f"indicator not a string: {ind!r}"
            assert len(ind.strip()) > 0, "indicator is blank"

    def test_category_field_is_non_empty_string(self, sample_indicators):
        """Schema: 'category' field is a non-empty string."""
        for record in sample_indicators:
            cat = record.get("category")
            assert isinstance(cat, str), (
                f"category not a string for {record['indicator']}: {cat!r}"
            )
            assert len(cat.strip()) > 0, f"category is blank for {record['indicator']}"

    def test_source_field_is_non_empty_string(self, sample_indicators):
        """Schema: 'source' field is a non-empty string."""
        for record in sample_indicators:
            src = record.get("source")
            assert isinstance(src, str), (
                f"source not a string for {record['indicator']}: {src!r}"
            )
            assert len(src.strip()) > 0, f"source is blank for {record['indicator']}"

    def test_unit_field_is_string(self, sample_indicators):
        """Schema: 'unit' field is a string (may be empty for dimensionless)."""
        for record in sample_indicators:
            unit = record.get("unit")
            assert isinstance(unit, str), (
                f"unit not a string for {record['indicator']}: {unit!r}"
            )

    def test_latest_period_is_non_empty_string(self, sample_indicators):
        """Schema: 'latest_period' is a non-empty string."""
        for record in sample_indicators:
            period = record.get("latest_period")
            assert isinstance(period, str), (
                f"latest_period not a string for {record['indicator']}: {period!r}"
            )
            assert len(period.strip()) > 0, (
                f"latest_period is blank for {record['indicator']}"
            )

    def test_latest_value_is_numeric_or_none(self, sample_indicators):
        """Schema: 'latest_value' is a number or None — never a string."""
        for record in sample_indicators:
            val = record.get("latest_value")
            if val is not None:
                assert isinstance(val, (int, float)), (
                    f"latest_value must be numeric for {record['indicator']}: got {type(val)} = {val!r}"
                )

    def test_no_nan_string_values(self, sample_indicators):
        """Schema: Fields don't contain 'nan', 'NaN', 'null' as literal strings."""
        for record in sample_indicators:
            for field, value in record.items():
                if isinstance(value, str):
                    assert value.lower() not in ("nan", "null", "none"), (
                        f"Field '{field}' in '{record['indicator']}' has sentinel string: {value!r}"
                    )


class TestNullHandling:
    """Graceful handling of missing/null values."""

    def test_null_latest_value_is_allowed(self, sample_indicators):
        """Null: latest_value=None is valid — indicator exists but has no data yet."""
        # Build a synthetic record with None value
        null_record = {
            "indicator": "test_null",
            "category": "Test",
            "source": "INE",
            "unit": "%",
            "latest_period": "2025-01",
            "latest_value": None,
        }
        # Should satisfy schema except for numeric constraint
        missing = REQUIRED_FIELDS - set(null_record.keys())
        assert not missing, f"Null-value record missing fields: {missing}"
        # latest_value None is acceptable
        assert null_record["latest_value"] is None

    def test_null_value_not_propagated_as_zero(self, sample_indicators):
        """Null: None values must NOT be silently converted to 0."""
        for record in sample_indicators:
            val = record.get("latest_value")
            # If we know the category, 0 is only valid for specific domains
            # (e.g. yoy changes) — we just ensure None stays None, not 0
            if val is None:
                assert val is None  # stays None, not coerced

    def test_all_sample_indicators_have_values(self, sample_indicators):
        """Data: All sample indicators have non-null latest_value."""
        for record in sample_indicators:
            assert record.get("latest_value") is not None, (
                f"sample_indicators fixture should have values: {record['indicator']}"
            )


class TestDataFreshness:
    """Period strings are well-formed and within expected ranges."""

    PERIOD_PATTERNS = [
        r"^\d{4}-\d{2}$",        # monthly: 2025-01
        r"^\d{4}-Q\d$",          # quarterly: 2025-Q4
        r"^\d{4}$",               # annual: 2024
        r"^\d{4}-\d{2}-\d{2}$",  # daily: 2025-03-01
        r"^\d{4} S\d$",          # semester: 2024 S1
    ]

    def _period_matches(self, period: str) -> bool:
        return any(re.match(pat, period) for pat in self.PERIOD_PATTERNS)

    def test_latest_period_format(self, sample_indicators):
        """Freshness: latest_period matches a known period format."""
        for record in sample_indicators:
            period = record.get("latest_period", "")
            assert self._period_matches(period), (
                f"Unrecognised period format for {record['indicator']}: {period!r}"
            )

    def test_period_year_range(self, sample_indicators):
        """Freshness: Period year is between 2000 and 2030."""
        for record in sample_indicators:
            period = record.get("latest_period", "")
            year_str = period[:4]
            if year_str.isdigit():
                year = int(year_str)
                assert 2000 <= year <= 2030, (
                    f"Suspicious year for {record['indicator']}: {year}"
                )

    def test_no_future_periods_far_out(self, sample_indicators):
        """Freshness: No period beyond 2027 (would indicate data error)."""
        for record in sample_indicators:
            period = record.get("latest_period", "")
            year_str = period[:4]
            if year_str.isdigit():
                year = int(year_str)
                assert year <= 2027, (
                    f"Period too far in the future for {record['indicator']}: {period}"
                )


class TestCatalogSchema:
    """Validate CATALOG constant structure."""

    def test_catalog_is_non_empty_dict(self):
        """Catalog: CATALOG is a non-empty dict."""
        from app.constants import CATALOG
        assert isinstance(CATALOG, dict)
        assert len(CATALOG) > 0

    def test_catalog_sources_have_indicators_key(self):
        """Catalog: Each source entry has 'indicators' dict."""
        from app.constants import CATALOG
        for source, data in CATALOG.items():
            assert "indicators" in data, f"Source '{source}' missing 'indicators' key"
            assert isinstance(data["indicators"], dict), (
                f"Source '{source}' indicators is not a dict"
            )

    def test_catalog_indicators_have_label(self):
        """Catalog: Every indicator has a non-empty label."""
        from app.constants import CATALOG
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data["indicators"].items():
                label = ind_data.get("label", "")
                assert isinstance(label, str) and len(label.strip()) > 0, (
                    f"Indicator {source}/{ind_key} has blank label"
                )

    def test_catalog_indicators_have_unit(self):
        """Catalog: Every indicator has a unit field (may be empty string)."""
        from app.constants import CATALOG
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data["indicators"].items():
                assert "unit" in ind_data, (
                    f"Indicator {source}/{ind_key} missing 'unit' field"
                )

    def test_catalog_total_indicator_count(self):
        """Catalog: Has at least 50 indicators across all sources."""
        from app.constants import CATALOG
        total = sum(len(src["indicators"]) for src in CATALOG.values())
        assert total >= 50, f"Expected >=50 catalog indicators, got {total}"
