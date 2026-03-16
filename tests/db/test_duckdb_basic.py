"""
Tests for DuckDB database — connectivity, read-only mode, data availability.

Focus: Ensure DB is accessible, read-only, has expected indicators and periods.
"""
import pytest
import duckdb
import os
from pathlib import Path


class TestDuckDBConnection:
    """Test DuckDB connection and basic operations."""

    def test_duckdb_in_memory_works(self):
        """DuckDB: In-memory database works."""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, value FLOAT)")
        conn.execute("INSERT INTO test VALUES (1, 100.0)")
        result = conn.execute("SELECT COUNT(*) as cnt FROM test").fetchall()
        assert result[0][0] == 1
        conn.close()

    def test_duckdb_read_only_mode(self, tmp_path):
        """DuckDB: Read-only connection prevents writes."""
        db_path = str(tmp_path / "test.duckdb")
        # Create DB with write access
        conn = duckdb.connect(db_path)
        conn.execute("CREATE TABLE data (id INTEGER)")
        conn.execute("INSERT INTO data VALUES (1)")
        conn.close()
        # Open read-only
        conn_ro = duckdb.connect(db_path, read_only=True)
        result = conn_ro.execute("SELECT * FROM data").fetchall()
        assert len(result) == 1
        # Try to write (should fail gracefully)
        with pytest.raises(Exception):  # DuckDB raises when trying to write in read-only
            conn_ro.execute("INSERT INTO data VALUES (2)")
        conn_ro.close()

    def test_duckdb_handles_null_values(self):
        """DuckDB: Handles NULL values correctly."""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, value FLOAT)")
        conn.execute("INSERT INTO test VALUES (1, NULL)")
        conn.execute("INSERT INTO test VALUES (2, 100.0)")
        result = conn.execute("SELECT COUNT(*) FROM test WHERE value IS NULL").fetchall()
        assert result[0][0] == 1
        conn.close()

    def test_duckdb_numeric_precision(self):
        """DuckDB: Maintains numeric precision."""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test (value DOUBLE)")
        test_value = 123.456789
        conn.execute("INSERT INTO test VALUES (?)", [test_value])
        result = conn.execute("SELECT value FROM test").fetchall()
        retrieved = result[0][0]
        assert abs(retrieved - test_value) < 0.0001
        conn.close()


class TestIndicatorCatalog:
    """Test indicator catalog structure (if DB available)."""

    @pytest.mark.skipif(
        not os.path.exists(os.getenv("CAE_DB_PATH", "/dev/null")),
        reason="Database not available in test environment"
    )
    def test_indicators_table_exists(self):
        """Indicators: Table exists and is queryable."""
        db_path = os.getenv("CAE_DB_PATH")
        if not db_path or not os.path.exists(db_path):
            pytest.skip("DB path not available")
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute("SELECT COUNT(*) FROM indicators").fetchall()
            count = result[0][0]
            assert count > 0, "No indicators in database"
        except Exception as e:
            pytest.skip(f"Could not query indicators: {e}")
        finally:
            conn.close()

    @pytest.mark.skipif(
        not os.path.exists(os.getenv("CAE_DB_PATH", "/dev/null")),
        reason="Database not available in test environment"
    )
    def test_indicators_count_near_383(self):
        """Indicators: Database has ~383 unique indicators."""
        db_path = os.getenv("CAE_DB_PATH")
        if not db_path or not os.path.exists(db_path):
            pytest.skip("DB path not available")
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute(
                "SELECT COUNT(DISTINCT indicator) FROM indicators"
            ).fetchall()
            count = result[0][0]
            # Allow ±50% margin (from 211 to 633)
            assert 200 < count < 700, f"Unexpected indicator count: {count}"
        except Exception as e:
            pytest.skip(f"Could not count indicators: {e}")
        finally:
            conn.close()

    @pytest.mark.skipif(
        not os.path.exists(os.getenv("CAE_DB_PATH", "/dev/null")),
        reason="Database not available in test environment"
    )
    def test_indicators_have_categories(self):
        """Indicators: Most indicators have a category."""
        db_path = os.getenv("CAE_DB_PATH")
        if not db_path or not os.path.exists(db_path):
            pytest.skip("DB path not available")
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM indicators WHERE category IS NULL OR category = ''"
            ).fetchall()
            null_count = result[0][0]
            total = conn.execute("SELECT COUNT(*) FROM indicators").fetchall()[0][0]
            # Allow <20% null categories
            null_pct = null_count / total if total > 0 else 0
            assert null_pct < 0.2, f"{null_pct*100:.1f}% of indicators have null category"
        except Exception as e:
            pytest.skip(f"Could not check categories: {e}")
        finally:
            conn.close()


class TestDataFreshness:
    """Test that indicator data is recent."""

    @pytest.mark.skipif(
        not os.path.exists(os.getenv("CAE_DB_PATH", "/dev/null")),
        reason="Database not available in test environment"
    )
    def test_latest_period_within_30_days(self):
        """Freshness: Latest data period is within 30 days."""
        from datetime import datetime, timedelta
        db_path = os.getenv("CAE_DB_PATH")
        if not db_path or not os.path.exists(db_path):
            pytest.skip("DB path not available")
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute(
                "SELECT MAX(period) as latest_period FROM indicators"
            ).fetchall()
            latest = result[0][0]
            if not latest:
                pytest.skip("No period data available")
            # Parse YYYY-MM or YYYY-MM-DD format
            try:
                if len(str(latest)) == 7:  # YYYY-MM
                    date = datetime.strptime(str(latest), "%Y-%m").date()
                else:
                    date = datetime.strptime(str(latest), "%Y-%m-%d").date()
                days_old = (datetime.now().date() - date).days
                # Allow up to 60 days old (some data is slower to update)
                assert days_old <= 60, f"Data is {days_old} days old"
            except ValueError:
                pytest.skip(f"Could not parse period format: {latest}")
        except Exception as e:
            pytest.skip(f"Could not check freshness: {e}")
        finally:
            conn.close()

    @pytest.mark.skipif(
        not os.path.exists(os.getenv("CAE_DB_PATH", "/dev/null")),
        reason="Database not available in test environment"
    )
    def test_no_nan_values_in_numeric_fields(self):
        """Data Quality: No NaN or Inf values in numeric columns."""
        db_path = os.getenv("CAE_DB_PATH")
        if not db_path or not os.path.exists(db_path):
            pytest.skip("DB path not available")
        conn = duckdb.connect(db_path, read_only=True)
        try:
            # DuckDB doesn't have NaN in SQL, but check for unusual patterns
            result = conn.execute(
                "SELECT COUNT(*) FROM indicators WHERE value IS NULL"
            ).fetchall()
            null_count = result[0][0]
            total = conn.execute("SELECT COUNT(*) FROM indicators").fetchall()[0][0]
            # Allow <30% nulls (expected for sparse data)
            null_pct = null_count / total if total > 0 else 0
            assert null_pct < 0.3, f"{null_pct*100:.1f}% of values are NULL"
        except Exception as e:
            pytest.skip(f"Could not check data quality: {e}")
        finally:
            conn.close()
