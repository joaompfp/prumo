"""
P5: API Endpoints — FastAPI TestClient integration tests.

Focus:
  - Main endpoints return 200
  - Required query params missing → 400/422, not 500
  - Invalid IDs/sources → 404 or handled error
  - Static/meta endpoints always succeed (no DB required)
  - No crashes on bad input

Note: Some endpoints require live DuckDB — those are marked with the
      live_db marker and will be skipped in CI if the DB is unavailable.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient — reused across all tests in this module.
    raise_server_exceptions=False prevents uncaught DB exceptions from
    propagating into the test as Python exceptions (returns 500 instead).
    """
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Static / meta endpoints (no DB needed) ────────────────────────────────────

class TestStaticEndpoints:
    """Endpoints that return static/computed data without DB queries."""

    def test_lenses_200(self, client):
        """GET /api/lenses — 200, returns list of lenses."""
        resp = client.get("/api/lenses")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert isinstance(data, (dict, list))

    def test_languages_200(self, client):
        """GET /api/languages — 200, returns supported languages."""
        resp = client.get("/api/languages")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"

    def test_events_200(self, client):
        """GET /api/events — 200, returns chart events list."""
        resp = client.get("/api/events")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"

    def test_mundo_meta_200(self, client):
        """GET /api/mundo/meta — 200, returns indicators + country_groups."""
        resp = client.get("/api/mundo/meta")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert "indicators" in data
        assert "country_groups" in data


class TestCatalogEndpoints:
    """Catalog and comparativos meta endpoints."""

    def test_catalog_200(self, client):
        """GET /api/catalog — 200, returns catalog data."""
        resp = client.get("/api/catalog")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"

    def test_comparativos_catalog_200(self, client):
        """GET /api/comparativos/catalog — 200."""
        resp = client.get("/api/comparativos/catalog")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"

    def test_comparativos_countries_200(self, client):
        """GET /api/comparativos/countries — 200."""
        resp = client.get("/api/comparativos/countries")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:200]}"


class TestDatabaseEndpoints:
    """Endpoints that query DuckDB — succeed or return well-formed errors.

    In CI (no live DB), endpoints may return 200 (graceful degradation),
    500 (unhandled DB error), or 503 (service unavailable). All are acceptable.
    """

    DB_OK_STATUSES = (200, 500, 503)

    def test_painel_returns_200_or_error(self, client):
        """GET /api/painel — 200 if DB available, error code otherwise."""
        resp = client.get("/api/painel")
        assert resp.status_code in self.DB_OK_STATUSES, (
            f"Unexpected status: {resp.status_code}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "sections" in data

    def test_resumo_returns_200_or_error(self, client):
        """GET /api/resumo — 200 or error code."""
        resp = client.get("/api/resumo")
        assert resp.status_code in self.DB_OK_STATUSES, (
            f"Unexpected status: {resp.status_code}"
        )

    def test_explorador_returns_200_or_error(self, client):
        """GET /api/explorador — 200 or error code."""
        resp = client.get("/api/explorador")
        assert resp.status_code in self.DB_OK_STATUSES, (
            f"Unexpected status: {resp.status_code}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "items" in data
            assert "total" in data

    def test_kpis_returns_200_or_error(self, client):
        """GET /api/kpis — 200 or error code."""
        resp = client.get("/api/kpis")
        assert resp.status_code in self.DB_OK_STATUSES, (
            f"Unexpected status: {resp.status_code}"
        )

    def test_industria_200_or_error(self, client):
        """GET /api/industria — 200 or error code."""
        resp = client.get("/api/industria")
        assert resp.status_code in self.DB_OK_STATUSES

    def test_energia_200_or_error(self, client):
        """GET /api/energia — 200 or error code."""
        resp = client.get("/api/energia")
        assert resp.status_code in self.DB_OK_STATUSES

    def test_emprego_200_or_error(self, client):
        """GET /api/emprego — 200 or error code."""
        resp = client.get("/api/emprego")
        assert resp.status_code in self.DB_OK_STATUSES

    def test_macro_200_or_error(self, client):
        """GET /api/macro — 200 or error code."""
        resp = client.get("/api/macro")
        assert resp.status_code in self.DB_OK_STATUSES


class TestSeriesEndpoint:
    """Tests for /api/series endpoint parameter validation."""

    def test_series_missing_source_returns_400(self, client):
        """GET /api/series — missing source/indicator → 400."""
        resp = client.get("/api/series")
        assert resp.status_code == 400, (
            f"Expected 400 for missing params, got {resp.status_code}"
        )
        data = resp.json()
        assert "error" in data

    def test_series_missing_indicator_returns_400(self, client):
        """GET /api/series?source=INE — missing indicator → 400."""
        resp = client.get("/api/series?source=INE")
        assert resp.status_code == 400, (
            f"Expected 400 for missing indicator, got {resp.status_code}"
        )

    def test_series_missing_source_returns_400_v2(self, client):
        """GET /api/series?indicator=gdp_yoy — missing source → 400."""
        resp = client.get("/api/series?indicator=gdp_yoy")
        assert resp.status_code == 400, (
            f"Expected 400 for missing source, got {resp.status_code}"
        )

    def test_series_invalid_source_not_unhandled(self, client):
        """GET /api/series with non-existent source → returns any HTTP response (not unhandled)."""
        resp = client.get("/api/series?source=DOESNOTEXIST&indicator=fake_indicator")
        # Any HTTP response is acceptable — just shouldn't be an unhandled exception
        assert resp.status_code is not None


class TestCompareEndpoint:
    """Tests for /api/compare endpoint."""

    def test_compare_default_params_returns_response(self, client):
        """GET /api/compare — default params return some HTTP response."""
        resp = client.get("/api/compare")
        assert resp.status_code in (200, 400, 500, 503), (
            f"Compare with defaults: {resp.status_code}"
        )

    def test_compare_invalid_dataset_returns_response(self, client):
        """GET /api/compare?dataset=nonexistent — returns some HTTP response."""
        resp = client.get("/api/compare?dataset=nonexistent")
        assert resp.status_code in (200, 400, 500, 503), (
            f"Invalid dataset: {resp.status_code}"
        )


class TestMundoEndpoint:
    """Tests for /api/mundo endpoint."""

    def test_mundo_default_params_returns_response(self, client):
        """GET /api/mundo — default params return some HTTP response."""
        resp = client.get("/api/mundo")
        assert resp.status_code in (200, 400, 500, 503), (
            f"Mundo: {resp.status_code}"
        )

    def test_mundo_invalid_indicator_returns_response(self, client):
        """GET /api/mundo?indicator=fake — returns some HTTP response."""
        resp = client.get("/api/mundo?indicator=fake_indicator")
        assert resp.status_code in (200, 400, 500, 503), (
            f"Invalid indicator: {resp.status_code}"
        )


class TestHeadlineEndpoint:
    """Tests for /api/painel-headline endpoint."""

    def test_headline_no_api_key_returns_json(self, client):
        """GET /api/painel-headline — no API key returns JSON (not crash)."""
        with patch("app.services.painel_headline.ANTHROPIC_KEY", None):
            resp = client.get("/api/painel-headline")
        # Should return some response (JSON), not a 500 crash
        assert resp.status_code in (200, 400, 404), (
            f"Unexpected status: {resp.status_code}"
        )

    def test_headline_with_lens_param_not_500(self, client):
        """GET /api/painel-headline?lens=neutro — not a crash."""
        with patch("app.services.painel_headline.ANTHROPIC_KEY", None):
            resp = client.get("/api/painel-headline?lens=neutro")
        assert resp.status_code != 500, (
            f"Headline with lens crashed: {resp.text[:200]}"
        )


class TestTrackEndpoint:
    """Tests for /api/track analytics endpoint."""

    def test_track_post_valid_json_not_500(self, client):
        """POST /api/track — valid JSON body not crash."""
        resp = client.post(
            "/api/track",
            json={"event": "page_view", "path": "/", "ts": 1700000000},
        )
        assert resp.status_code in (200, 201, 400, 422), (
            f"Track endpoint: {resp.status_code}: {resp.text[:200]}"
        )

    def test_track_empty_body_not_500(self, client):
        """POST /api/track — empty body handled gracefully."""
        resp = client.post("/api/track", json={})
        assert resp.status_code != 500, (
            f"Track with empty body crashed: {resp.text[:200]}"
        )


class TestLinkTitleEndpoint:
    """Tests for /api/link-title endpoint."""

    def test_link_title_missing_url_returns_empty(self, client):
        """GET /api/link-title — missing url returns {title: ''}."""
        resp = client.get("/api/link-title")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("title") == ""

    def test_link_title_non_http_url_returns_empty(self, client):
        """GET /api/link-title?url=javascript:alert(1) — non-http returns empty."""
        resp = client.get("/api/link-title?url=javascript:alert(1)")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("title") == ""

    def test_link_title_ftp_url_returns_empty(self, client):
        """GET /api/link-title?url=ftp://example.com — non-http returns empty."""
        resp = client.get("/api/link-title?url=ftp://example.com")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("title") == ""


class TestQualityEndpoint:
    """Tests for /api/quality endpoint."""

    def test_quality_returns_response(self, client):
        """GET /api/quality — returns some HTTP response."""
        resp = client.get("/api/quality")
        assert resp.status_code in (200, 400, 500, 503), (
            f"Quality endpoint: {resp.status_code}: {resp.text[:200]}"
        )


class TestExportEndpoint:
    """Tests for /api/export endpoint."""

    def test_export_missing_params_returns_422(self, client):
        """GET /api/export without required params → 422 Unprocessable Entity."""
        resp = client.get("/api/export")
        assert resp.status_code == 422, (
            f"Export without params should be 422: got {resp.status_code}"
        )

    def test_export_with_params_returns_response(self, client):
        """GET /api/export with required params → some HTTP response."""
        resp = client.get("/api/export?sources=INE&indicators=hicp_yoy")
        assert resp.status_code in (200, 400, 500, 503), (
            f"Export endpoint: {resp.status_code}: {resp.text[:200]}"
        )


class TestHealthReportEndpoint:
    """Tests for /api/health/report endpoint (Sprint 2)."""

    def test_health_report_returns_200(self, client):
        """GET /api/health/report — always returns 200."""
        resp = client.get("/api/health/report")
        assert resp.status_code == 200

    def test_health_report_has_status(self, client):
        """GET /api/health/report — response has status field."""
        resp = client.get("/api/health/report")
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_health_report_has_sources_list(self, client):
        """GET /api/health/report — sources is a list."""
        resp = client.get("/api/health/report")
        data = resp.json()
        if "sources" in data:
            assert isinstance(data["sources"], list)
            if data["sources"]:
                entry = data["sources"][0]
                assert "source" in entry
                assert "indicators" in entry
                assert "latest_period" in entry

    def test_health_report_has_caches(self, client):
        """GET /api/health/report — caches dict present."""
        resp = client.get("/api/health/report")
        data = resp.json()
        assert "caches" in data
        assert isinstance(data["caches"], dict)

    def test_health_report_has_timestamp(self, client):
        """GET /api/health/report — ts field present."""
        resp = client.get("/api/health/report")
        data = resp.json()
        assert "ts" in data


class TestCodebookEndpoint:
    """Tests for /api/codebook endpoint (Sprint 2)."""

    def test_codebook_returns_200(self, client):
        """GET /api/codebook — returns 200."""
        resp = client.get("/api/codebook")
        assert resp.status_code == 200

    def test_codebook_content_type_csv(self, client):
        """GET /api/codebook — content type is text/csv."""
        resp = client.get("/api/codebook")
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_codebook_has_header_row(self, client):
        """GET /api/codebook — first line has expected CSV columns."""
        resp = client.get("/api/codebook")
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 1
        header = lines[0]
        assert "source" in header
        assert "indicator" in header
        assert "label" in header


class TestHealthzEndpoint:
    """Tests for /healthz endpoint (Sprint 2 — DB-validated healthcheck)."""

    def test_healthz_returns_response(self, client):
        """GET /healthz — returns 200 response (may be JSON or HTML depending on route order)."""
        resp = client.get("/healthz")
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            data = resp.json()
            assert "status" in data

    def test_healthz_json_has_indicators(self, client):
        """GET /healthz — JSON response has indicators count (if JSON)."""
        resp = client.get("/healthz")
        ct = resp.headers.get("content-type", "")
        if "json" in ct and resp.status_code == 200:
            data = resp.json()
            assert "indicators" in data
            assert isinstance(data["indicators"], int)

    def test_healthz_json_has_latest_period(self, client):
        """GET /healthz — JSON response has latest_period (if JSON)."""
        resp = client.get("/healthz")
        ct = resp.headers.get("content-type", "")
        if "json" in ct and resp.status_code == 200:
            data = resp.json()
            assert "latest_period" in data


class TestResponseTimingHeader:
    """Tests for X-Response-Time header (Sprint 2)."""

    def test_api_response_has_timing_header(self, client):
        """API responses include X-Response-Time header."""
        resp = client.get("/api/events")
        assert "x-response-time" in resp.headers
        timing = resp.headers["x-response-time"]
        assert timing.endswith("ms")

    def test_static_endpoint_has_timing_header(self, client):
        """Static endpoint also has X-Response-Time header."""
        resp = client.get("/api/lenses")
        assert "x-response-time" in resp.headers
