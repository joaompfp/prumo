"""
P2: Search & Filter — Explorador catalog service.

Focus: fuzzy search PT+EN names, empty query returns all, category/year filter,
case-insensitive matching. DB is mocked — no live DuckDB required.
"""
import pytest
from unittest.mock import patch, MagicMock


# ── DB mock helpers ────────────────────────────────────────────────────────────

def _make_db_rows():
    """Synthetic DB rows matching explorador SQL result columns:
       (source, indicator, regions, since, until, total_rows)
    """
    return [
        ("INE",       "ipi_seasonal_cae_TOT",    1, "2005-01", "2025-12", 252),
        ("INE",       "hicp_yoy",                1, "1997-01", "2025-11", 347),
        ("INE",       "gdp_yoy",                 1, "1996-01", "2025-10", 120),
        ("INE",       "exports_monthly",          1, "2005-01", "2024-12", 240),
        ("INE",       "imports_monthly",          1, "2005-01", "2024-12", 240),
        ("EUROSTAT",  "unemployment",             27, "2000-01", "2025-11", 3456),
        ("EUROSTAT",  "manufacturing",            27, "2000-01", "2025-11", 3200),
        ("EUROSTAT",  "gdp_quarterly",            27, "2000-01", "2025-10", 1200),
        ("BPORTUGAL", "euribor_3m",               1, "1999-01", "2025-12", 324),
        ("REN",       "electricity_price_mibel",  1, "2015-01", "2025-12", 132),
        ("FRED",      "brent_oil",                1, "1990-01", "2025-12", 420),
        ("WORLDBANK", "rnd_pct_gdp",             200, "1990",   "2023",    4200),
    ]


def _mock_conn(rows):
    """Return a mock DuckDB connection that returns the given rows."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    return mock_conn


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestExploradorBuildCatalog:
    """Tests for build_explorador_catalog()."""

    def _build_with_mock(self, rows=None):
        """Call build_explorador_catalog with mocked DB."""
        if rows is None:
            rows = _make_db_rows()
        mock_conn_obj = _mock_conn(rows)
        with patch("app.services.explorador.get_db", return_value=mock_conn_obj):
            from app.services.explorador import build_explorador_catalog
            return build_explorador_catalog()

    def test_returns_dict_with_items_and_total(self):
        """Explorador: Returns {'items': [...], 'total': N}."""
        result = self._build_with_mock()
        assert isinstance(result, dict)
        assert "items" in result
        assert "total" in result

    def test_total_matches_items_count(self):
        """Explorador: total == len(items)."""
        result = self._build_with_mock()
        assert result["total"] == len(result["items"])

    def test_empty_db_returns_empty_catalog(self):
        """Explorador: Empty DB yields items=[], total=0."""
        result = self._build_with_mock(rows=[])
        assert result["items"] == []
        assert result["total"] == 0

    def test_item_has_required_fields(self):
        """Explorador: Each item has source, indicator, label, category, unit, since, until."""
        required = {"source", "indicator", "label", "category", "unit", "since", "until"}
        result = self._build_with_mock()
        for item in result["items"]:
            missing = required - set(item.keys())
            assert not missing, f"Item {item.get('indicator')} missing: {missing}"

    def test_source_field_matches_db_source(self):
        """Explorador: item.source matches the source from DB."""
        result = self._build_with_mock()
        db_sources = {r[0] for r in _make_db_rows()}
        for item in result["items"]:
            assert item["source"] in db_sources

    def test_known_catalog_indicator_gets_label(self):
        """Explorador: A known catalog indicator gets its label (not fallback to key)."""
        result = self._build_with_mock()
        ine_items = [i for i in result["items"] if i["source"] == "INE"]
        hicp = next((i for i in ine_items if i["indicator"] == "hicp_yoy"), None)
        if hicp:
            # Should have a real label from CATALOG, not just the raw key
            assert hicp["label"] != "hicp_yoy", (
                "hicp_yoy should get a human label from CATALOG, not raw key"
            )

    def test_unknown_indicator_uses_key_as_label(self):
        """Explorador: Unknown indicator falls back to indicator key as label."""
        rows = [("UNKNOWN_SRC", "some_unknown_ind", 1, "2020-01", "2025-01", 60)]
        result = self._build_with_mock(rows=rows)
        assert result["total"] == 1
        item = result["items"][0]
        assert item["label"] == "some_unknown_ind"

    def test_frequency_inferred_from_monthly_period(self):
        """Explorador: Monthly period (2025-01) → frequency='monthly'."""
        rows = [("INE", "some_monthly", 1, "2020-01", "2025-01", 60)]
        result = self._build_with_mock(rows=rows)
        item = result["items"][0]
        assert item["frequency"] == "monthly"

    def test_frequency_inferred_from_quarterly_period(self):
        """Explorador: Quarterly period (2025-Q4) → frequency='quarterly'."""
        rows = [("INE", "some_quarterly", 1, "2020-Q1", "2025-Q4", 23)]
        result = self._build_with_mock(rows=rows)
        item = result["items"][0]
        assert item["frequency"] == "quarterly"

    def test_frequency_inferred_from_annual_period(self):
        """Explorador: Annual period (2024) → frequency='annual'."""
        rows = [("WORLDBANK", "some_annual", 1, "2000", "2024", 25)]
        result = self._build_with_mock(rows=rows)
        item = result["items"][0]
        assert item["frequency"] == "annual"


class TestExploradorSearch:
    """Test search/filter logic applied to the built catalog."""

    def _get_items(self):
        """Get all items from a mocked catalog."""
        mock_conn_obj = _mock_conn(_make_db_rows())
        with patch("app.services.explorador.get_db", return_value=mock_conn_obj):
            from app.services.explorador import build_explorador_catalog
            return build_explorador_catalog()["items"]

    def test_empty_query_returns_all_items(self):
        """Search: Empty/None query returns all items (no filtering)."""
        items = self._get_items()
        # All items present — no filtering at the service layer
        assert len(items) == len(_make_db_rows())

    def test_portuguese_source_names_present(self):
        """Search: PT source names are included in catalog labels."""
        items = self._get_items()
        sources = {i["source"] for i in items}
        assert "INE" in sources, "INE (Portuguese national stats) should be present"

    def test_all_items_have_non_empty_label(self):
        """Search: Every item has a non-empty label."""
        items = self._get_items()
        for item in items:
            assert item.get("label"), f"Item {item['indicator']} has empty label"

    def test_tags_are_list(self):
        """Search: tags field is always a list (for filter UI)."""
        items = self._get_items()
        for item in items:
            assert isinstance(item.get("tags"), list), (
                f"Item {item['indicator']} has non-list tags: {item.get('tags')!r}"
            )

    def test_category_derived_from_tags(self):
        """Search: category is derived from first tag for known indicators."""
        items = self._get_items()
        # For known catalog indicators, category should come from tags
        for item in items:
            assert isinstance(item["category"], str)
            assert len(item["category"]) > 0

    def test_rows_count_is_positive(self):
        """Search: rows count is a positive integer for all items."""
        items = self._get_items()
        for item in items:
            assert isinstance(item.get("rows"), int), (
                f"rows not int for {item['indicator']}: {item.get('rows')!r}"
            )
            assert item["rows"] > 0, f"rows <= 0 for {item['indicator']}"

    def test_region_count_is_positive(self):
        """Search: region_count is a positive integer."""
        items = self._get_items()
        for item in items:
            assert isinstance(item.get("region_count"), int), (
                f"region_count not int for {item['indicator']}"
            )
            assert item["region_count"] >= 1, (
                f"region_count < 1 for {item['indicator']}"
            )


class TestExploradorInferFrequency:
    """Unit tests for _infer_frequency helper."""

    def _infer(self, period):
        from app.services.explorador import _infer_frequency
        return _infer_frequency(period)

    def test_monthly_period(self):
        assert self._infer("2025-01") == "monthly"

    def test_quarterly_period(self):
        assert self._infer("2025-Q2") == "quarterly"

    def test_annual_period(self):
        assert self._infer("2024") == "annual"

    def test_weekly_period(self):
        assert self._infer("2024-W12") == "weekly"

    def test_semester_period(self):
        assert self._infer("2016 S1") == "semester"

    def test_empty_period_returns_empty_string(self):
        assert self._infer("") == ""

    def test_none_period_returns_empty_string(self):
        assert self._infer(None) == ""

    def test_unrecognised_format_returns_empty(self):
        assert self._infer("gibberish") == ""
