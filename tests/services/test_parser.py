"""
Tests for app/services/painel_analysis/parser.py — META_JSON and headline extraction.

Focus: Ensure LLM response markers are correctly parsed and stripped.
"""
import pytest
from app.services.painel_analysis.parser import _parse_meta_json, _extract_headline


class TestParseMetaJsonNoMarkers:
    """Text without any markers passes through unchanged."""

    def test_plain_text_returns_as_is(self):
        """No markers: text returned unchanged, empty dicts, no headline."""
        text = "A economia portuguesa cresceu 2.1% no último trimestre."
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == text
        assert links == {}
        assert chart is None
        assert section_charts == {}
        assert headline == ""
        assert sub == ""

    def test_empty_text(self):
        """Empty string: all fields empty/default."""
        clean, links, chart, section_charts, headline, sub = _parse_meta_json("")
        assert clean == ""
        assert links == {}
        assert chart is None
        assert section_charts == {}
        assert headline == ""
        assert sub == ""


class TestParseMetaJson:
    """META_JSON marker extraction."""

    def test_section_links_extracted(self):
        """META_JSON with section_links: links dict returned."""
        text = (
            "Analysis body here."
            '\nMETA_JSON:{"section_links": {"emprego": "/dados?s=emprego"}}'
        )
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Analysis body here."
        assert links == {"emprego": "/dados?s=emprego"}
        assert chart is None

    def test_chart_pick_extracted(self):
        """META_JSON with chart_pick: chart object returned."""
        text = (
            "Some analysis.\n"
            'META_JSON:{"chart_pick": {"indicator": "pib_real", "type": "line"}}'
        )
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Some analysis."
        assert chart == {"indicator": "pib_real", "type": "line"}
        assert links == {}

    def test_section_charts_extracted(self):
        """META_JSON with section_charts: section_charts dict returned."""
        text = (
            "Body text.\n"
            'META_JSON:{"section_charts": {"fiscal": "divida_publica"}}'
        )
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Body text."
        assert section_charts == {"fiscal": "divida_publica"}

    def test_all_meta_fields_together(self):
        """META_JSON with all three fields: all extracted correctly."""
        meta = {
            "section_links": {"x": "/y"},
            "chart_pick": {"indicator": "z"},
            "section_charts": {"a": "b"},
        }
        import json
        text = f"Full analysis.\nMETA_JSON:{json.dumps(meta)}"
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Full analysis."
        assert links == {"x": "/y"}
        assert chart == {"indicator": "z"}
        assert section_charts == {"a": "b"}

    def test_malformed_json_after_meta_json(self):
        """META_JSON with broken JSON: fallback to text before marker, empty dicts."""
        text = "Good analysis.\nMETA_JSON:{broken json here"
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Good analysis."
        assert links == {}
        assert chart is None
        assert section_charts == {}


class TestParseSectionLinksLegacy:
    """Legacy SECTION_LINKS marker extraction."""

    def test_section_links_legacy_format(self):
        """SECTION_LINKS (legacy): links dict extracted, no chart_pick."""
        text = (
            "Old-style analysis.\n"
            'SECTION_LINKS:{"emprego": "/dados?s=emprego", "fiscal": "/dados?s=fiscal"}'
        )
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Old-style analysis."
        assert links == {"emprego": "/dados?s=emprego", "fiscal": "/dados?s=fiscal"}
        assert chart is None

    def test_malformed_json_after_section_links(self):
        """SECTION_LINKS with broken JSON: fallback to empty dicts."""
        text = "Analysis.\nSECTION_LINKS:{not valid"
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert clean == "Analysis."
        assert links == {}
        assert chart is None


class TestExtractHeadline:
    """HEADLINE / SUBHEADLINE extraction from end of text."""

    def test_headline_at_end(self):
        """HEADLINE at end: extracted and removed from text."""
        text = "Body text.\nHEADLINE: Economy grows"
        headline, sub, rest = _extract_headline(text)
        assert headline == "Economy grows"
        assert sub == ""
        assert rest == "Body text."

    def test_subheadline_at_end(self):
        """SUBHEADLINE at end: extracted and removed from text."""
        text = "Body text.\nSUBHEADLINE: Q4 results"
        headline, sub, rest = _extract_headline(text)
        assert headline == ""
        assert sub == "Q4 results"
        assert rest == "Body text."

    def test_both_headline_and_subheadline(self):
        """Both HEADLINE and SUBHEADLINE: both extracted."""
        text = "Body.\nHEADLINE: Main title\nSUBHEADLINE: Subtitle here"
        headline, sub, rest = _extract_headline(text)
        assert headline == "Main title"
        assert sub == "Subtitle here"
        assert rest == "Body."

    def test_headline_with_markdown_hashes_stripped(self):
        """HEADLINE with # markdown prefix: hashes stripped."""
        text = "Body.\nHEADLINE: ## Strong Growth"
        headline, sub, rest = _extract_headline(text)
        assert headline == "Strong Growth"

    def test_multiple_headline_lines_uses_last(self):
        """Multiple HEADLINE lines: backwards search picks last one."""
        text = "Body.\nHEADLINE: First\nHEADLINE: Second"
        headline, sub, rest = _extract_headline(text)
        # Backwards search finds "Second" first and stops
        assert headline == "Second"
        # "First" line remains in the text since only last match is removed
        assert "HEADLINE: First" in rest

    def test_no_headline_no_subheadline(self):
        """No markers: empty strings, text unchanged."""
        text = "Just plain text with no markers."
        headline, sub, rest = _extract_headline(text)
        assert headline == ""
        assert sub == ""
        assert rest == text


class TestCombinedParsing:
    """Combined META_JSON + HEADLINE + SUBHEADLINE in same text."""

    def test_full_response_parsing(self):
        """Full LLM response with body, headlines, and META_JSON: all parsed."""
        text = (
            "The economy is expanding.\n"
            "HEADLINE: Growth Accelerates\n"
            "SUBHEADLINE: GDP up 2.3%\n"
            'META_JSON:{"section_links": {"pib": "/dados?s=pib"}, '
            '"chart_pick": {"indicator": "pib_real"}}'
        )
        clean, links, chart, section_charts, headline, sub = _parse_meta_json(text)
        assert headline == "Growth Accelerates"
        assert sub == "GDP up 2.3%"
        assert links == {"pib": "/dados?s=pib"}
        assert chart == {"indicator": "pib_real"}
        assert "The economy is expanding." in clean
        assert "META_JSON" not in clean
        assert "HEADLINE" not in clean
        assert "SUBHEADLINE" not in clean
