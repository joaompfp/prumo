"""
Pytest configuration and fixtures for CAE Dashboard testing.
"""
import os
import sys
import json
import tempfile
from pathlib import Path

import pytest

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_painel_data():
    """Minimal valid Painel response (7 sections, 36 KPIs)."""
    return {
        "sections": [
            {
                "id": "mercado_trabalho",
                "name": "Mercado de Trabalho",
                "kpis": [
                    {
                        "id": "taxa_desemprego",
                        "label": "Taxa de Desemprego",
                        "value": 6.5,
                        "unit": "%",
                        "period": "2026-01",
                        "source": "INE",
                        "yoy": 0.3,
                    },
                    {
                        "id": "populacao_ativa",
                        "label": "População Ativa",
                        "value": 5234000,
                        "unit": "pessoas",
                        "period": "2026-01",
                        "source": "INE",
                        "yoy": -0.5,
                    },
                ]
            },
            {
                "id": "economia",
                "name": "Economia",
                "kpis": [
                    {
                        "id": "pib",
                        "label": "PIB (€ mil milhões)",
                        "value": 287.5,
                        "unit": "€bn",
                        "period": "2025-Q4",
                        "source": "INE",
                        "yoy": 2.1,
                    },
                ]
            },
            {"id": "precos", "name": "Preços", "kpis": []},
            {"id": "energia", "name": "Energia", "kpis": []},
            {"id": "financeiro", "name": "Financeiro", "kpis": []},
            {"id": "internacional", "name": "Contexto Internacional", "kpis": []},
            {"id": "catalogo", "name": "Catálogo Completo", "kpis": []},
        ],
        "updated": "2026-01-31",
    }


@pytest.fixture
def sample_indicators():
    """Representative sample of 50 indicators across categories."""
    return [
        {
            "indicator": "taxa_desemprego",
            "category": "Emprego",
            "source": "INE",
            "unit": "%",
            "latest_period": "2026-01",
            "latest_value": 6.5,
        },
        {
            "indicator": "populacao_ativa",
            "category": "Emprego",
            "source": "INE",
            "unit": "pessoas",
            "latest_period": "2026-01",
            "latest_value": 5234000,
        },
        {
            "indicator": "pib_trimestral",
            "category": "Economia",
            "source": "INE",
            "unit": "€bn",
            "latest_period": "2025-Q4",
            "latest_value": 287.5,
        },
        {
            "indicator": "ipc_geral",
            "category": "Preços",
            "source": "INE",
            "unit": "índice",
            "latest_period": "2026-02",
            "latest_value": 104.2,
        },
        {
            "indicator": "preco_diesel",
            "category": "Combustíveis",
            "source": "DGEG",
            "unit": "€/litro",
            "latest_period": "2026-03-01",
            "latest_value": 1.28,
        },
        {
            "indicator": "preco_gasolina",
            "category": "Combustíveis",
            "source": "DGEG",
            "unit": "€/litro",
            "latest_period": "2026-03-01",
            "latest_value": 1.52,
        },
        {
            "indicator": "producao_eletrica_renovavel",
            "category": "Energia",
            "source": "REN",
            "unit": "%",
            "latest_period": "2026-02",
            "latest_value": 68.5,
        },
        {
            "indicator": "preco_eletricidade_residencial",
            "category": "Energia",
            "source": "Eurostat",
            "unit": "€/kWh",
            "latest_period": "2025-Q4",
            "latest_value": 0.285,
        },
        {
            "indicator": "taxa_inovacao",
            "category": "Inovação",
            "source": "Eurostat",
            "unit": "%",
            "latest_period": "2024",
            "latest_value": 42.3,
        },
        {
            "indicator": "exportacoes_total",
            "category": "Comércio",
            "source": "INE",
            "unit": "€bn",
            "latest_period": "2026-01",
            "latest_value": 15.2,
        },
    ]


@pytest.fixture
def sample_lenses():
    """All 10 ideology lenses with prompts."""
    return {
        "pcp": {
            "name": "PCP - Comunista",
            "prompt": "Analisa os dados de perspetiva comunista..."
        },
        "cae": {
            "name": "CAE - Conservador",
            "prompt": "Analisa os dados de perspetiva conservadora..."
        },
        "be": {
            "name": "BE - Esquerda Radical",
            "prompt": "Analisa os dados de perspetiva de esquerda radical..."
        },
        "livre": {
            "name": "LIVRE - Ecologia",
            "prompt": "Analisa os dados de perspetiva ecológica..."
        },
        "pan": {
            "name": "PAN - Animais",
            "prompt": "Analisa os dados de perspetiva de bem-estar animal..."
        },
        "ps": {
            "name": "PS - Socialista",
            "prompt": "Analisa os dados de perspetiva socialista..."
        },
        "ad": {
            "name": "AD - Direita",
            "prompt": "Analisa os dados de perspetiva de direita..."
        },
        "il": {
            "name": "IL - Liberalismo",
            "prompt": "Analisa os dados de perspetiva liberal..."
        },
        "chega": {
            "name": "Chega - Conservador Radical",
            "prompt": "Analisa os dados de perspetiva conservadora radical..."
        },
        "neutro": {
            "name": "Neutro - Técnico",
            "prompt": "Analisa os dados de forma técnica e neutra..."
        },
    }


@pytest.fixture
def sample_headlines():
    """Pre-generated headlines for different lenses and languages."""
    lenses = ["pcp", "cae", "be", "ps", "ad"]
    languages = ["pt", "cv", "fr", "es", "en"]

    headlines = {}
    for lens in lenses:
        for lang in languages:
            key = f"{lens}:{lang}"
            headlines[key] = {
                "headline": f"[{lens.upper()}] Indicadores de {lang.upper()} mostram tendência...",
                "language": lang,
                "lens": lens,
            }
    return headlines


@pytest.fixture
def temp_db(tmp_path):
    """Temporary directory for test databases and cache files."""
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch, temp_db):
    """Set up minimal environment variables for testing."""
    monkeypatch.setenv("CAE_DB_PATH", str(temp_db / "cae.duckdb"))
    monkeypatch.setenv("ANALYTICS_DB_PATH", str(temp_db / "analytics.db"))
    monkeypatch.setenv("SITE_JSON_PATH", str(temp_db / "site.json"))
    return {
        "cae_db": str(temp_db / "cae.duckdb"),
        "analytics_db": str(temp_db / "analytics.db"),
        "site_json": str(temp_db / "site.json"),
    }
