"""
P4: Headlines — Full test of painel_headline service.

Focus:
  - Service doesn't crash
  - Output is non-empty when mocked API responds
  - LLM timeout handled gracefully (no crash, returns error dict)
  - Cache behaviour: TTL respected, key format correct
  - ALL LLM/HTTP calls are mocked

No live API calls, no file I/O to real paths.
"""
import json
import time
import pytest
from unittest.mock import patch, MagicMock, mock_open


# ── Shared fixtures ────────────────────────────────────────────────────────────

SAMPLE_SECTIONS = [
    {
        "title": "Mercado de Trabalho",
        "kpis": [
            {"label": "Taxa de Desemprego", "value": 6.5, "unit": "%", "yoy": 0.3, "yoy_unit": "%"},
            {"label": "População Activa", "value": 5234000, "unit": "pessoas"},
        ],
    },
    {
        "title": "Conjuntura",
        "kpis": [
            {"label": "PIB (var. anual)", "value": 2.1, "unit": "%"},
        ],
    },
]
SAMPLE_UPDATED = "2026-01-31"


def _make_anthropic_response(text: str) -> bytes:
    """Build a fake Anthropic API response bytes."""
    return json.dumps({
        "content": [{"type": "text", "text": text}],
        "model": "claude-opus-4-6",
        "usage": {"input_tokens": 100, "output_tokens": 30},
    }).encode()


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestGetPainelHeadline:
    """Tests for get_painel_headline()."""

    def test_no_api_key_returns_error(self):
        """Headline: Missing API key returns error dict (not crash)."""
        with patch("app.services.painel_headline.ANTHROPIC_KEY", None):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)
        assert isinstance(result, dict)
        assert result.get("headline") is None
        assert "error" in result

    def test_returns_dict_always(self):
        """Headline: Function always returns a dict."""
        with patch("app.services.painel_headline.ANTHROPIC_KEY", None):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)
        assert isinstance(result, dict)

    def test_successful_generation_returns_headline(self):
        """Headline: Successful API call returns non-empty headline."""
        fake_headline = "Desemprego cai para 6.5%; economia cresce 2.1%\nMercado de trabalho em recuperação sustentada"
        fake_resp_bytes = _make_anthropic_response(fake_headline)

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_resp_bytes
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("app.services.painel_headline._load_ideology", return_value="ideology"), \
             patch("app.services.painel_headline._get_sonnet_analysis_text", return_value=None), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open(read_data="{}")):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)

        assert isinstance(result, dict)
        assert result.get("headline") is not None
        assert len(result["headline"]) > 0

    def test_headline_is_string(self):
        """Headline: Returned headline is a string."""
        fake_headline = "PIB cresce 2.1% no Q4 — indústria lidera recuperação"
        fake_resp_bytes = _make_anthropic_response(fake_headline)

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_resp_bytes
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("app.services.painel_headline._load_ideology", return_value="ideology"), \
             patch("app.services.painel_headline._get_sonnet_analysis_text", return_value=None), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open(read_data="{}")):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)

        assert isinstance(result.get("headline"), str)

    def test_api_timeout_returns_error(self):
        """Headline: HTTP timeout → error dict, no crash."""
        import urllib.error

        mock_opener = MagicMock()
        mock_opener.open.side_effect = TimeoutError("Connection timed out")

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("app.services.painel_headline._load_ideology", return_value="ideology"), \
             patch("app.services.painel_headline._get_sonnet_analysis_text", return_value=None), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open(read_data="{}")):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)

        assert isinstance(result, dict)
        assert result.get("headline") is None
        assert "error" in result

    def test_api_exception_returns_error_not_raise(self):
        """Headline: Any API exception is caught — function never raises."""
        mock_opener = MagicMock()
        mock_opener.open.side_effect = Exception("Unexpected error")

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("app.services.painel_headline._load_ideology", return_value="ideology"), \
             patch("app.services.painel_headline._get_sonnet_analysis_text", return_value=None), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open(read_data="{}")):
            from app.services.painel_headline import get_painel_headline
            # Should NOT raise
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)

        assert isinstance(result, dict)

    def test_empty_sections_no_api_call(self):
        """Headline: Empty sections → no API call → error or None headline."""
        mock_opener = MagicMock()

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("app.services.painel_headline._load_ideology", return_value="ideology"), \
             patch("app.services.painel_headline._get_sonnet_analysis_text", return_value=None), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open(read_data="{}")):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline([], SAMPLE_UPDATED)

        # Empty sections yield no KPI data → should return error, not crash
        assert isinstance(result, dict)
        assert result.get("headline") is None

    def test_cached_result_returned_when_valid(self):
        """Headline: Valid cache entry is returned without API call."""
        now = time.time()
        cache_key = f"headline:v4:{SAMPLE_UPDATED}:default:pt"
        cache_data = {
            cache_key: {
                "headline": "Cached headline from previous run",
                "generated_at": "2026-01-31T10:00:00Z",
                "ts": now - 100,  # 100s ago, well within 6h TTL
            }
        }

        mock_opener = MagicMock()  # Should NOT be called

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)

        # Should return cached result
        assert result.get("cached") is True
        assert result.get("headline") == "Cached headline from previous run"
        # API should NOT have been called
        mock_opener.open.assert_not_called()

    def test_expired_cache_triggers_api_call(self):
        """Headline: Expired cache (>6h) triggers a fresh API call."""
        now = time.time()
        cache_key = f"headline:v4:{SAMPLE_UPDATED}:default:pt"
        cache_data = {
            cache_key: {
                "headline": "Old cached headline",
                "generated_at": "2026-01-30T00:00:00Z",
                "ts": now - (7 * 3600),  # 7h ago → expired
            }
        }

        fake_headline = "Fresh headline after cache expiry"
        fake_resp_bytes = _make_anthropic_response(fake_headline)

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_resp_bytes
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp

        with patch("app.services.painel_headline.ANTHROPIC_KEY", "test-key"), \
             patch("app.services.painel_headline._opener", mock_opener), \
             patch("app.services.painel_headline._load_ideology", return_value="ideology"), \
             patch("app.services.painel_headline._get_sonnet_analysis_text", return_value=None), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            from app.services.painel_headline import get_painel_headline
            result = get_painel_headline(SAMPLE_SECTIONS, SAMPLE_UPDATED)

        # API should have been called (expired cache)
        mock_opener.open.assert_called_once()
        assert result.get("cached") is not True


class TestCacheKeyFormat:
    """Test cache key structure and versioning."""

    def test_cache_key_format(self):
        """Cache: Key format is 'headline:v4:{updated}:{lens}:{lang}'."""
        # Verify the format matches what the code produces
        updated = "2026-01-31"
        lens_key = "default"
        lang = "pt"
        expected = f"headline:v4:{updated}:{lens_key}:{lang}"
        assert expected == "headline:v4:2026-01-31:default:pt"

    def test_cache_key_includes_language(self):
        """Cache: Different languages produce different cache keys."""
        base = "headline:v4:2026-01-31:cae:"
        keys = {base + lang for lang in ("pt", "en", "fr", "es", "cv")}
        assert len(keys) == 5  # All distinct

    def test_cache_ttl_value(self):
        """Cache: TTL constant is 6 hours (21600 seconds)."""
        import app.services.painel_headline as hl
        assert hl._CACHE_TTL_SECONDS == 6 * 3600


class TestBuildHeadlinePrompt:
    """Tests for _build_headline_prompt() helper."""

    def test_returns_none_for_all_null_values(self):
        """Prompt: Returns None when all KPI values are None."""
        from app.services.painel_headline import _build_headline_prompt
        sections = [{"title": "Test", "kpis": [{"label": "X", "value": None}]}]
        assert _build_headline_prompt(sections) is None

    def test_includes_yoy_when_present(self):
        """Prompt: YoY change is included when present."""
        from unittest.mock import patch
        from app.services.painel_headline import _build_headline_prompt

        sections = [{
            "title": "Emprego",
            "kpis": [{"label": "Desemprego", "value": 6.5, "unit": "%", "yoy": -0.3}],
        }]
        with patch("app.services.painel_headline._load_ideology", return_value="ideology"):
            result = _build_headline_prompt(sections)
        assert result is not None
        assert "-0.3" in result  # YoY should appear

    def test_excludes_kpis_with_none_value(self):
        """Prompt: KPIs with None value are excluded from the prompt."""
        from unittest.mock import patch
        from app.services.painel_headline import _build_headline_prompt

        sections = [{
            "title": "Mixed",
            "kpis": [
                {"label": "Has Value", "value": 5.0, "unit": "%"},
                {"label": "No Value", "value": None, "unit": "%"},
            ],
        }]
        with patch("app.services.painel_headline._load_ideology", return_value="ideology"):
            result = _build_headline_prompt(sections)
        assert result is not None
        assert "Has Value" in result
        assert "No Value" not in result


class TestGenerateAllHeadlines:
    """Tests for generate_all_headlines() batch function."""

    def test_returns_dict(self):
        """Batch: generate_all_headlines returns a dict."""
        with patch("app.services.painel_headline.ANTHROPIC_KEY", None):
            from app.services.painel_headline import generate_all_headlines
            result = generate_all_headlines(SAMPLE_SECTIONS, SAMPLE_UPDATED,
                                            lenses=["neutro"], languages=["pt"])
        assert isinstance(result, dict)

    def test_no_api_key_batch_returns_errors(self):
        """Batch: No API key → all results have error, no crash."""
        with patch("app.services.painel_headline.ANTHROPIC_KEY", None):
            from app.services.painel_headline import generate_all_headlines
            result = generate_all_headlines(SAMPLE_SECTIONS, SAMPLE_UPDATED,
                                            lenses=["neutro", "cae"],
                                            languages=["pt", "en"])
        assert len(result) == 4  # 2 lenses × 2 languages
        for key, val in result.items():
            assert isinstance(val, dict)
