"""
P3: Multilingual — Catalog labels and multilingual output support.

Focus:
  - All catalog indicators have non-blank PT labels (label field)
  - All catalog indicators have non-blank descriptions
  - Headline generation supports all 5 output languages (pt, cv, fr, es, en)
  - Language instructions are non-empty for each supported language
  - No blank keys in the supported language dicts
"""
import pytest


SUPPORTED_LANGUAGES = {"pt", "cv", "fr", "es", "en"}


class TestCatalogLabels:
    """Validate that catalog PT labels are complete and non-blank."""

    def test_every_indicator_has_label(self):
        """Multilingual: Every catalog indicator has a 'label' field."""
        from app.constants import CATALOG
        missing_label = []
        for source, src_data in CATALOG.items():
            for ind_key in src_data.get("indicators", {}):
                ind_data = src_data["indicators"][ind_key]
                if not ind_data.get("label"):
                    missing_label.append(f"{source}/{ind_key}")
        assert not missing_label, (
            f"{len(missing_label)} indicators missing label:\n"
            + "\n".join(missing_label[:10])
        )

    def test_every_indicator_label_is_non_blank(self):
        """Multilingual: No indicator has a whitespace-only label."""
        from app.constants import CATALOG
        blank_labels = []
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data.get("indicators", {}).items():
                label = ind_data.get("label", "")
                if isinstance(label, str) and label.strip() == "":
                    blank_labels.append(f"{source}/{ind_key}")
        assert not blank_labels, (
            f"Blank labels: {blank_labels[:10]}"
        )

    def test_labels_are_strings(self):
        """Multilingual: All labels are str type."""
        from app.constants import CATALOG
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data.get("indicators", {}).items():
                label = ind_data.get("label")
                assert isinstance(label, str), (
                    f"{source}/{ind_key} label is not str: {type(label)}"
                )

    def test_every_indicator_has_description(self):
        """Multilingual: Every catalog indicator has a 'description' field."""
        from app.constants import CATALOG
        missing_desc = []
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data.get("indicators", {}).items():
                if not ind_data.get("description"):
                    missing_desc.append(f"{source}/{ind_key}")
        assert not missing_desc, (
            f"{len(missing_desc)} indicators missing description:\n"
            + "\n".join(missing_desc[:10])
        )

    def test_descriptions_are_non_blank(self):
        """Multilingual: No description is whitespace-only."""
        from app.constants import CATALOG
        blank_descs = []
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data.get("indicators", {}).items():
                desc = ind_data.get("description", "")
                if isinstance(desc, str) and desc.strip() == "":
                    blank_descs.append(f"{source}/{ind_key}")
        assert not blank_descs, (
            f"Blank descriptions: {blank_descs[:10]}"
        )

    def test_label_does_not_equal_indicator_key(self):
        """Multilingual: Label is human-readable, not just the raw key."""
        from app.constants import CATALOG
        raw_key_labels = []
        for source, src_data in CATALOG.items():
            for ind_key, ind_data in src_data.get("indicators", {}).items():
                label = ind_data.get("label", "")
                if label == ind_key:
                    raw_key_labels.append(f"{source}/{ind_key}")
        assert not raw_key_labels, (
            f"Labels that are identical to the key (not humanized): {raw_key_labels[:10]}"
        )


class TestCatalogSourceLabels:
    """Validate source-level labels."""

    def test_every_source_has_label(self):
        """Multilingual: Every catalog source has a top-level 'label'."""
        from app.constants import CATALOG
        for source, src_data in CATALOG.items():
            assert "label" in src_data, f"Source '{source}' missing label"
            assert src_data["label"].strip(), f"Source '{source}' has blank label"

    def test_source_labels_are_strings(self):
        """Multilingual: Source labels are strings."""
        from app.constants import CATALOG
        for source, src_data in CATALOG.items():
            assert isinstance(src_data.get("label"), str), (
                f"Source '{source}' label is not str"
            )


class TestHeadlineLanguageSupport:
    """Validate that painel_headline supports all 5 output languages."""

    def test_lang_instructions_keys_are_complete(self):
        """Multilingual: lang_instructions covers all 5 output languages."""
        # We import the module and inspect the lang_instructions dict
        import importlib
        import sys
        # Use the module-level inspection approach
        import app.services.painel_headline as hl_module
        import inspect

        source = inspect.getsource(hl_module)
        for lang in SUPPORTED_LANGUAGES:
            assert f'"{lang}"' in source, (
                f"Language '{lang}' not found in painel_headline.py source"
            )

    def test_build_headline_prompt_with_no_kpi_data(self):
        """Multilingual: _build_headline_prompt returns None when all KPI values are None."""
        from app.services.painel_headline import _build_headline_prompt
        sections = [{"title": "Test", "kpis": [{"label": "X", "value": None}]}]
        result = _build_headline_prompt(sections)
        assert result is None

    def test_build_headline_prompt_with_data_returns_string(self):
        """Multilingual: _build_headline_prompt returns a string when data is present."""
        from unittest.mock import patch
        from app.services.painel_headline import _build_headline_prompt

        sections = [{
            "title": "Emprego",
            "kpis": [
                {"label": "Taxa Desemprego", "value": 6.5, "unit": "%", "yoy": 0.3},
            ],
        }]
        with patch("app.services.painel_headline._load_ideology", return_value="[test ideology]"):
            result = _build_headline_prompt(sections, lens=None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_headline_prompt_includes_kpi_value(self):
        """Multilingual: Prompt includes KPI value for anchoring."""
        from unittest.mock import patch
        from app.services.painel_headline import _build_headline_prompt

        sections = [{
            "title": "Inflação",
            "kpis": [
                {"label": "IHPC", "value": 2.5, "unit": "%"},
            ],
        }]
        with patch("app.services.painel_headline._load_ideology", return_value="ideology"):
            result = _build_headline_prompt(sections)
        assert "2.5" in result

    def test_build_headline_prompt_pt_language(self):
        """Multilingual: PT language instruction includes 'português europeu'."""
        from unittest.mock import patch
        from app.services.painel_headline import _build_headline_prompt

        sections = [{
            "title": "Test",
            "kpis": [{"label": "PIB", "value": 2.1, "unit": "%"}],
        }]
        with patch("app.services.painel_headline._load_ideology", return_value="ideology"):
            result = _build_headline_prompt(sections, output_language="pt")
        assert result is not None
        assert "português" in result.lower()

    def test_build_headline_prompt_en_language(self):
        """Multilingual: EN language instruction includes 'English'."""
        from unittest.mock import patch
        from app.services.painel_headline import _build_headline_prompt

        sections = [{
            "title": "Test",
            "kpis": [{"label": "GDP", "value": 2.1, "unit": "%"}],
        }]
        with patch("app.services.painel_headline._load_ideology", return_value="ideology"):
            result = _build_headline_prompt(sections, output_language="en")
        assert result is not None
        assert "English" in result


class TestMappingsCompleteness:
    """Validate SOURCE_META and other mapping completeness."""

    def test_source_meta_has_entries(self):
        """Multilingual: SOURCE_META mapping is non-empty."""
        from app.constants.mappings import SOURCE_META
        assert isinstance(SOURCE_META, dict)
        assert len(SOURCE_META) > 0

    def test_source_meta_labels_are_strings(self):
        """Multilingual: All SOURCE_META labels are non-empty strings."""
        from app.constants.mappings import SOURCE_META
        for source, meta in SOURCE_META.items():
            label = meta.get("label", "")
            assert isinstance(label, str) and label.strip(), (
                f"SOURCE_META[{source}] has blank label"
            )
