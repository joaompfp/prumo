"""
Tests for composite indicator routing in app/services/series.py.

Focus: Ensure COMPOSITE_INDICATORS structure is valid and that
EU vs. world routing logic classifies countries correctly.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.series import (
    COMPOSITE_INDICATORS, EU27_CODES, EU_AGGREGATES,
    _eu_db_regions, query_composite,
)


class TestCompositeIndicatorsStructure:
    """Validate the shape of the COMPOSITE_INDICATORS registry."""

    def test_composite_indicators_has_required_keys(self):
        """Each composite indicator must define both 'eu' and 'world' sources."""
        for key, entry in COMPOSITE_INDICATORS.items():
            assert "eu" in entry, f"{key} missing 'eu' key"
            assert "world" in entry, f"{key} missing 'world' key"

    def test_composite_eu_entries_are_tuples(self):
        """Each 'eu' value must be a (source, indicator) tuple."""
        for key, entry in COMPOSITE_INDICATORS.items():
            eu = entry["eu"]
            assert isinstance(eu, tuple) and len(eu) == 2, (
                f"{key}['eu'] should be a 2-tuple, got {eu!r}"
            )

    def test_composite_world_entries_are_tuples(self):
        """Each 'world' value must be a (source, indicator) tuple."""
        for key, entry in COMPOSITE_INDICATORS.items():
            world = entry["world"]
            assert isinstance(world, tuple) and len(world) == 2, (
                f"{key}['world'] should be a 2-tuple, got {world!r}"
            )


class TestEU27Constants:
    """Validate EU membership sets used for routing."""

    def test_eu27_codes_count(self):
        """EU27_CODES must contain exactly 27 member-state codes."""
        assert len(EU27_CODES) == 27

    def test_eu27_codes_contains_pt(self):
        """Portugal (PT) must be in EU27_CODES."""
        assert "PT" in EU27_CODES

    def test_eu_aggregates_values(self):
        """EU_AGGREGATES must contain the three canonical aggregate codes."""
        assert EU_AGGREGATES == frozenset(["EU27", "EU27_2020", "EU"])


class TestCountryRouting:
    """Verify that countries are classified into the correct source bucket."""

    def test_eu_country_routed_to_eurostat(self):
        """PT (EU27 member) must be classified as eu_region, not world_region."""
        regions = ["PT"]
        eu_regions = [r for r in regions if r in EU27_CODES or r in EU_AGGREGATES]
        world_regions = [r for r in regions if r not in EU27_CODES and r not in EU_AGGREGATES]
        assert eu_regions == ["PT"]
        assert world_regions == []

    def test_non_eu_country_routed_to_worldbank(self):
        """BR, US, AO are non-EU countries — must be world_regions only."""
        regions = ["BR", "US", "AO"]
        eu_regions = [r for r in regions if r in EU27_CODES or r in EU_AGGREGATES]
        world_regions = [r for r in regions if r not in EU27_CODES and r not in EU_AGGREGATES]
        assert eu_regions == []
        assert world_regions == ["BR", "US", "AO"]

    def test_eu27_2020_is_eu_aggregate(self):
        """EU27_2020 is an aggregate code — must route as eu_region."""
        regions = ["EU27_2020"]
        eu_regions = [r for r in regions if r in EU27_CODES or r in EU_AGGREGATES]
        assert eu_regions == ["EU27_2020"]


class TestEuDbRegionMapping:
    """Verify the _eu_db_regions helper normalises region codes for the DB."""

    def test_eu_db_region_mapping(self):
        """EU27_2020→EU27, EU→EU27 in DB; PT stays PT."""
        db_regions, rev = _eu_db_regions(["EU27_2020", "EU", "PT"])
        assert db_regions == ["EU27", "EU27", "PT"]
        # Both EU27_2020 and EU map to DB key EU27; dict iteration order
        # means the last entry ("EU") overwrites in the reverse map.
        assert rev == {"EU27": "EU"}

    def test_eu_db_region_mapping_no_aliases(self):
        """Plain country codes pass through unchanged with empty reverse map."""
        db_regions, rev = _eu_db_regions(["PT", "DE", "FR"])
        assert db_regions == ["PT", "DE", "FR"]
        assert rev == {}


class TestQueryCompositeWithMockDB:
    """Integration-style test using a mocked database connection."""

    @patch("app.services.series.get_db")
    def test_query_composite_with_mock_db(self, mock_get_db):
        """Mock get_db() to verify correct SQL routing and response shape."""
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn

        # Canned rows for the EU query (PT via EUROSTAT)
        eu_rows = [
            ("PT", "2024-01", 6.5),
            ("PT", "2024-02", 6.4),
        ]
        # Canned rows for the world query (BR via WORLDBANK)
        world_rows = [
            ("BR", "2024", 8.1),
        ]

        # The mock connection's execute().fetchall() returns different results
        # depending on call order: first call is EU, second is world.
        mock_cursor = MagicMock()
        mock_cursor.fetchall = MagicMock(side_effect=[eu_rows, world_rows])
        mock_conn.execute = MagicMock(return_value=mock_cursor)

        result = query_composite("unemployment", "PT,BR", since_yr="2024")

        assert result["dataset"] == "composite:unemployment"
        assert result["source"] == "COMPOSITE"
        assert len(result["series"]) == 2

        pt_series = result["series"][0]
        assert pt_series["country"] == "PT"
        assert len(pt_series["data"]) == 2
        assert pt_series["data"][0] == {"period": "2024-01", "value": 6.5}

        br_series = result["series"][1]
        assert br_series["country"] == "BR"
        assert len(br_series["data"]) == 1

        # Verify DB was queried twice (once for EU, once for world)
        assert mock_conn.execute.call_count == 2
        mock_conn.close.assert_called_once()

        # Verify the first call used EUROSTAT source
        first_call_args = mock_conn.execute.call_args_list[0]
        assert "EUROSTAT" in first_call_args[0][1]

        # Verify the second call used WORLDBANK source
        second_call_args = mock_conn.execute.call_args_list[1]
        assert "WORLDBANK" in second_call_args[0][1]
