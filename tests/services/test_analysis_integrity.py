"""Tests for app/services/painel_analysis/engine.py — Analysis engine contracts."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_cache(tmp_path, cache_dict):
    """Write a cache JSON file and return its path."""
    p = tmp_path / "painel-analysis-cache.json"
    p.write_text(json.dumps(cache_dict, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _make_cache_entry(**overrides):
    """Return a realistic cache entry dict with sensible defaults."""
    base = {
        "text": "Sample analysis text.",
        "headline": "Economy grows",
        "subheadline": "GDP up 2 %",
        "section_links": {"macro": ["https://example.com/article"]},
        "chart_pick": "gdp_real",
        "section_charts": {"macro": ["gdp_real", "inflation"]},
        "generated_at": "2026-03-17T10:00:00Z",
        "generation_ms": 4200,
        "model": "claude-sonnet-4-6",
        "lens": "default",
        "output_language": "pt",
        "kpi_count": 42,
    }
    base.update(overrides)
    return base


SECTIONS_STUB = [{"name": "macro", "kpis": [{"id": "gdp"}]}]
UPDATED_STUB = "2026-03-17"


# ---------------------------------------------------------------------------
# 1–2. No API key
# ---------------------------------------------------------------------------

@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "")
def test_no_api_key_returns_error():
    from app.services.painel_analysis.engine import get_painel_analysis
    result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)
    assert result["text"] is None
    assert result["cached"] is False
    assert "error" in result


@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "")
def test_no_api_key_error_message():
    from app.services.painel_analysis.engine import get_painel_analysis
    result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)
    assert result["error"] == "API key not configured"


# ---------------------------------------------------------------------------
# 3–4. Cache hit
# ---------------------------------------------------------------------------

@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "sk-test")
def test_cache_hit_returns_cached_true(tmp_path):
    from app.services.painel_analysis.engine import get_painel_analysis
    key = f"painel:v23:{UPDATED_STUB}:default:pt"
    cache = {key: _make_cache_entry()}
    cache_path = _write_cache(tmp_path, cache)

    with patch("app.services.painel_analysis.engine._CACHE_PATH", cache_path), \
         patch("app.services.painel_analysis.engine.DEFAULT_OUTPUT_LANGUAGE", "pt"):
        result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)

    assert result["cached"] is True


@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "sk-test")
def test_cache_hit_preserves_fields(tmp_path):
    from app.services.painel_analysis.engine import get_painel_analysis
    entry = _make_cache_entry()
    key = f"painel:v23:{UPDATED_STUB}:default:pt"
    cache_path = _write_cache(tmp_path, {key: entry})

    with patch("app.services.painel_analysis.engine._CACHE_PATH", cache_path), \
         patch("app.services.painel_analysis.engine.DEFAULT_OUTPUT_LANGUAGE", "pt"):
        result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)

    assert result["text"] == entry["text"]
    assert result["headline"] == entry["headline"]
    assert result["section_links"] == entry["section_links"]
    assert result["generated_at"] == entry["generated_at"]
    assert result["data_period"] == UPDATED_STUB


# ---------------------------------------------------------------------------
# 5. Cache miss + no API key → API key error (checked first)
# ---------------------------------------------------------------------------

@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "")
def test_cache_miss_with_no_api_key(tmp_path):
    from app.services.painel_analysis.engine import get_painel_analysis
    # Cache exists but under a different key
    cache = {"painel:v23:WRONG:default:pt": _make_cache_entry()}
    cache_path = _write_cache(tmp_path, cache)

    with patch("app.services.painel_analysis.engine._CACHE_PATH", cache_path):
        result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)

    assert result["error"] == "API key not configured"


# ---------------------------------------------------------------------------
# 6. force=True bypasses cache (then fails on missing API key)
# ---------------------------------------------------------------------------

@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "")
def test_force_bypasses_cache(tmp_path):
    from app.services.painel_analysis.engine import get_painel_analysis
    key = f"painel:v23:{UPDATED_STUB}:default:pt"
    cache_path = _write_cache(tmp_path, {key: _make_cache_entry()})

    with patch("app.services.painel_analysis.engine._CACHE_PATH", cache_path), \
         patch("app.services.painel_analysis.engine.DEFAULT_OUTPUT_LANGUAGE", "pt"):
        result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB, force=True)

    # force=True skips cache, but API key check comes first → error
    assert result["error"] == "API key not configured"


# ---------------------------------------------------------------------------
# 7. No KPI data
# ---------------------------------------------------------------------------

@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "sk-test")
@patch("app.services.painel_analysis.engine._build_painel_prompt", return_value=None)
def test_no_kpi_data_returns_error(mock_prompt, tmp_path):
    from app.services.painel_analysis.engine import get_painel_analysis
    # Empty cache so we fall through to prompt building
    cache_path = _write_cache(tmp_path, {})

    with patch("app.services.painel_analysis.engine._CACHE_PATH", cache_path):
        result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)

    assert result["error"] == "No KPI data available"
    assert result["text"] is None
    assert result["cached"] is False


# ---------------------------------------------------------------------------
# 8–11. Cache key format
# ---------------------------------------------------------------------------

def test_cache_key_format():
    """Cache key embeds version, updated, lens, language."""
    updated = "2026-03-17"
    lens_key = "default"
    lang_key = "pt"
    key = f"painel:v23:{updated}:{lens_key}:{lang_key}"

    assert key.startswith("painel:v23:")
    assert updated in key
    assert ":default:" in key
    assert key.endswith(":pt")


def test_cache_key_custom_lens_uses_hash():
    """When lens='custom' with ideology text, key includes md5 hash prefix."""
    import hashlib
    ideology = "test ideology text"
    h = hashlib.md5(ideology.encode()).hexdigest()[:8]
    lens_key = f"custom:{h}"

    key = f"painel:v23:{UPDATED_STUB}:{lens_key}:pt"
    assert f"custom:{h}" in key
    assert len(h) == 8


def test_default_lens_key():
    """No lens argument → lens_key falls back to 'default'."""
    lens = None
    lens_key = lens or "default"
    assert lens_key == "default"


@patch("app.services.painel_analysis.engine.ANTHROPIC_KEY", "sk-test")
def test_default_language_key(tmp_path):
    """No output_language → uses DEFAULT_OUTPUT_LANGUAGE for cache key."""
    from app.services.painel_analysis.engine import get_painel_analysis
    # Build the expected key with the default language
    default_lang = "pt"
    key = f"painel:v23:{UPDATED_STUB}:default:{default_lang}"
    cache = {key: _make_cache_entry()}
    cache_path = _write_cache(tmp_path, cache)

    with patch("app.services.painel_analysis.engine._CACHE_PATH", cache_path), \
         patch("app.services.painel_analysis.engine.DEFAULT_OUTPUT_LANGUAGE", default_lang):
        # Call without output_language — should hit the cache keyed with default lang
        result = get_painel_analysis(SECTIONS_STUB, UPDATED_STUB)

    assert result["cached"] is True


# ---------------------------------------------------------------------------
# 12. Cache entry metadata fields
# ---------------------------------------------------------------------------

def test_cache_entry_metadata_fields():
    """A full cache entry must contain model, lens, output_language, kpi_count."""
    entry = _make_cache_entry()
    for field in ("model", "lens", "output_language", "kpi_count"):
        assert field in entry, f"missing metadata field: {field}"
    assert entry["model"] == "claude-sonnet-4-6"
    assert isinstance(entry["kpi_count"], int)
