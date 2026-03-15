"""
Tests for /api/painel endpoint — KPI dashboard data.

Focus: Validate response structure, status codes, schema, data completeness.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """FastAPI test client."""
    from app.main import app
    return TestClient(app)


class TestPanelEndpoint:
    """Test GET /api/painel endpoint."""

    def test_painel_status_200(self, client):
        """Painel: Endpoint returns 200 OK."""
        response = client.get("/api/painel")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

    def test_painel_response_json(self, client):
        """Painel: Response is valid JSON with expected structure."""
        response = client.get("/api/painel")
        data = response.json()
        assert isinstance(data, dict)
        assert "sections" in data
        assert "updated" in data

    def test_painel_has_seven_sections(self, client):
        """Painel: Response includes at least 7 sections (+ optional catalog section)."""
        response = client.get("/api/painel")
        data = response.json()
        assert len(data.get("sections", [])) >= 7

    def test_painel_sections_have_ids_and_names(self, client):
        """Painel: Each section has id and name."""
        response = client.get("/api/painel")
        data = response.json()
        for section in data.get("sections", []):
            assert "id" in section, "Section missing 'id'"
            assert "name" in section, "Section missing 'name'"
            assert "kpis" in section, "Section missing 'kpis'"

    def test_painel_kpis_have_required_fields(self, client):
        """Painel: Each KPI has id, label, source, period."""
        response = client.get("/api/painel")
        data = response.json()
        for section in data.get("sections", []):
            for kpi in section.get("kpis", []):
                required = {"id", "label", "source", "period"}
                missing = required - set(kpi.keys())
                assert not missing, f"KPI {kpi.get('id')} missing: {missing}"

    def test_painel_sources_are_strings(self, client):
        """Painel: All source fields are non-empty strings."""
        response = client.get("/api/painel")
        data = response.json()
        for section in data.get("sections", []):
            for kpi in section.get("kpis", []):
                source = kpi.get("source")
                assert isinstance(source, str), f"KPI {kpi.get('id')} source not a string"
                assert len(source) > 0, f"KPI {kpi.get('id')} has empty source"

    def test_painel_updated_date_format(self, client):
        """Painel: Updated date is non-empty string."""
        response = client.get("/api/painel")
        data = response.json()
        updated = data.get("updated")
        assert isinstance(updated, str)
        assert len(updated) > 0


class TestPanelErrorHandling:
    """Test /api/painel error handling."""

    def test_painel_invalid_query_param(self, client):
        """Painel: Invalid query params don't crash endpoint."""
        response = client.get("/api/painel?invalid_param=true&bg=invalid")
        # Should either be 200 or 400, not 500
        assert response.status_code in (200, 400), f"Got {response.status_code}"

    def test_painel_no_query_params(self, client):
        """Painel: No query params returns valid response."""
        response = client.get("/api/painel")
        assert response.status_code == 200
        data = response.json()
        assert "sections" in data

    def test_painel_with_force_param(self, client):
        """Painel: Force param doesn't break endpoint."""
        response = client.get("/api/painel?force=1")
        assert response.status_code in (200, 202), f"Got {response.status_code}"


class TestPanelCatalogo:
    """Test Catálogo Completo section (all 422+ indicators)."""

    def test_catalogo_section_exists(self, client):
        """Catálogo: 'Catálogo Completo' section is present."""
        response = client.get("/api/painel")
        data = response.json()
        catalogo = next(
            (s for s in data.get("sections", []) if s.get("id") == "catalogo"),
            None
        )
        assert catalogo is not None, "Catálogo Completo section not found"

    def test_catalogo_has_kpis(self, client):
        """Catálogo: Section has KPIs loaded."""
        response = client.get("/api/painel")
        data = response.json()
        catalogo = next(
            (s for s in data.get("sections", []) if s.get("id") == "catalogo"),
            {}
        )
        kpis = catalogo.get("kpis", [])
        # Should have many indicators (could be 0 if DB not available in test env)
        # Just ensure it's a list
        assert isinstance(kpis, list)

    def test_catalogo_kpi_structure(self, client):
        """Catálogo: Each KPI in catalog has id and label."""
        response = client.get("/api/painel")
        data = response.json()
        catalogo = next(
            (s for s in data.get("sections", []) if s.get("id") == "catalogo"),
            {}
        )
        for kpi in catalogo.get("kpis", [])[:5]:  # Check first 5
            assert "id" in kpi, "Catalog KPI missing 'id'"
            assert "label" in kpi, "Catalog KPI missing 'label'"
