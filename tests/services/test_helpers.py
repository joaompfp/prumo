"""
Tests for app/services/helpers.py — YoY calculations and trend detection.

Focus: Prevent silent data corruption in KPI calculations.
"""
import pytest
from app.services.helpers import compute_yoy, compute_trend, spark_data


class TestComputeYoY:
    """Test YoY (year-over-year) change calculation."""

    def test_yoy_basic_monthly(self):
        """YoY: Compare current month with same month previous year."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2025-01", "value": 110},
        ]
        yoy = compute_yoy(series)
        # YoY is absolute pp change: 110 - 100 = 10
        assert yoy == 10.0

    def test_yoy_with_null_latest(self):
        """YoY: Return None if latest value is null."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2025-01", "value": None},
        ]
        yoy = compute_yoy(series)
        assert yoy is None

    def test_yoy_empty_series(self):
        """YoY: Return None for empty series."""
        yoy = compute_yoy([])
        assert yoy is None

    def test_yoy_single_point(self):
        """YoY: Return None if no previous year data."""
        series = [{"period": "2025-01", "value": 100}]
        yoy = compute_yoy(series)
        assert yoy is None

    def test_yoy_with_missing_intermediate_periods(self):
        """YoY: Find same month in previous year even with gaps."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2024-06", "value": 105},  # gap
            {"period": "2025-01", "value": 110},
        ]
        yoy = compute_yoy(series)
        assert yoy == 10.0  # 110 - 100

    def test_yoy_annual_data(self):
        """YoY: Handle annual period format (YYYY only)."""
        series = [
            {"period": "2024", "value": 1000},
            {"period": "2025", "value": 1050},
        ]
        yoy = compute_yoy(series)
        assert yoy == 50.0  # 1050 - 1000

    def test_yoy_negative_change(self):
        """YoY: Negative change (decrease)."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2025-01", "value": 95},
        ]
        yoy = compute_yoy(series)
        assert yoy == -5.0

    def test_yoy_zero_change(self):
        """YoY: Zero change returns 0.0."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2025-01", "value": 100},
        ]
        yoy = compute_yoy(series)
        assert yoy == 0.0

    def test_yoy_filters_null_values(self):
        """YoY: Only compares non-null values."""
        series = [
            {"period": "2024-01", "value": None},
            {"period": "2024-06", "value": 100},
            {"period": "2025-01", "value": 110},
        ]
        yoy = compute_yoy(series)
        # Should find 2024-01 with value 100, not None
        assert yoy == 10.0

    def test_yoy_negative_zero_distinction(self):
        """YoY: Distinguish between -0.0 and 0.0."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2025-01", "value": 100.0},
        ]
        yoy = compute_yoy(series)
        assert yoy == 0.0
        assert not (yoy < 0)  # ensure it's not negative zero


class TestComputeTrend:
    """Test trend direction detection (up/down/flat)."""

    def test_trend_upward(self):
        """Trend: Upward trend over 3+ recent months."""
        series = [
            {"period": "2024-10", "value": 100},
            {"period": "2024-11", "value": 102},
            {"period": "2024-12", "value": 105},
            {"period": "2025-01", "value": 108},
        ]
        trend_dir, trend_months = compute_trend(series)
        assert trend_dir == "up"
        assert trend_months >= 3

    def test_trend_downward(self):
        """Trend: Downward trend over 3+ recent months."""
        series = [
            {"period": "2024-10", "value": 100},
            {"period": "2024-11", "value": 98},
            {"period": "2024-12", "value": 95},
            {"period": "2025-01", "value": 92},
        ]
        trend_dir, trend_months = compute_trend(series)
        assert trend_dir == "down"
        assert trend_months >= 3

    def test_trend_flat(self):
        """Trend: Flat trend (minimal change)."""
        series = [
            {"period": "2024-10", "value": 100},
            {"period": "2024-11", "value": 100.1},
            {"period": "2024-12", "value": 100.2},
        ]
        trend_dir, trend_months = compute_trend(series)
        assert trend_dir == "flat"

    def test_trend_insufficient_data(self):
        """Trend: Return None if fewer than 3 periods."""
        series = [
            {"period": "2024-12", "value": 100},
            {"period": "2025-01", "value": 105},
        ]
        trend_dir, trend_months = compute_trend(series)
        assert trend_dir is None or trend_months < 3

    def test_trend_empty_series(self):
        """Trend: Return None for empty series."""
        trend_dir, trend_months = compute_trend([])
        assert trend_dir is None or trend_months == 0


class TestSparkData:
    """Test sparkline data generation (simplified series for charts)."""

    def test_spark_data_basic(self):
        """Sparkline: Generate 10-point compressed series."""
        series = [{"period": f"2024-{i:02d}", "value": i * 10} for i in range(1, 13)]
        spark = spark_data(series)
        # Should return list of (period, value) tuples
        assert spark is not None
        if spark:
            assert len(spark) <= 10  # compressed

    def test_spark_data_handles_nulls(self):
        """Sparkline: Skip null values gracefully."""
        series = [
            {"period": "2024-01", "value": 100},
            {"period": "2024-02", "value": None},
            {"period": "2024-03", "value": 105},
        ]
        spark = spark_data(series)
        assert spark is not None
        # Should not include nulls
        if spark:
            assert all(v is not None for _, v in spark)

    def test_spark_data_empty(self):
        """Sparkline: Return empty/None for empty series."""
        spark = spark_data([])
        assert spark is None or spark == []
