"""Reader-facing text, rendered from language-neutral codes.

The data layer stores codes only; this package owns every sentence a reader sees.
"""
from importlib import import_module

LANGUAGES: tuple[str, ...] = ("pt", "en")


class MissingText(KeyError):
    """A code has no text in the catalog."""


def _catalog(lang: str):
    if lang not in LANGUAGES:
        raise ValueError(f"unknown language {lang!r}")
    return import_module(f"presentation.catalog.{lang}")


def _lookup(table: dict[str, str], kind: str, lang: str, code: str) -> str:
    try:
        return table[code]
    except KeyError:
        raise MissingText(f"no {lang} {kind} text for {code!r}") from None


def describe_formula(lang: str, formula: str, params: dict[str, str],
                     base_series_id: str) -> str:
    template = _lookup(_catalog(lang).FORMULAS, "formula", lang, formula)
    if formula == "rebase_100" and "base_period" not in params:
        raise ValueError("rebase_100 needs params['base_period']")
    return template.format(base=base_series_id, **params)


def unit_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).UNITS, "unit", lang, code)


def caveat_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).CAVEATS, "caveat", lang, code)


def derived_title(lang: str, key: str) -> str:
    return _lookup(_catalog(lang).TITLES, "title", lang, key)


def search_aliases(lang: str, family: str) -> str:
    """Extra words a reader may type for this family (empty when none are declared)."""
    return _catalog(lang).SEARCH_ALIASES.get(family, "")


def calculated_attribution(lang: str, attribution: str) -> str:
    return f"{attribution} — {_catalog(lang).ATTRIBUTION_SUFFIX}"


# --- base-series catalogue (project 4) -------------------------------------------------------

def family_title(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).FAMILIES, "family", lang, code)


def geography_name(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).GEOGRAPHIES, "geography", lang, code)


def base_unit_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).BASE_UNITS, "unit", lang, code)


def flag_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).FLAGS, "flag", lang, code)


def theme_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).THEMES, "theme", lang, code)


def theme_blurb(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).THEME_BLURBS, "theme blurb", lang, code)


def frequency_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).FREQUENCIES, "frequency", lang, code)


def seasonal_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).SEASONAL, "seasonal adjustment", lang, code)


def source_title(lang: str, name: str) -> str:
    return _lookup(_catalog(lang).SOURCE_TITLES, "source", lang, name)


def series_title(lang: str, family: str, geography: str) -> str:
    """`family — geography`, except for families whose title already names the place."""
    catalog = _catalog(lang)
    title = _lookup(catalog.FAMILIES, "family", lang, family)
    if family in catalog.SELF_LOCATING_FAMILIES:
        return title
    return f"{title} — {_lookup(catalog.GEOGRAPHIES, 'geography', lang, geography)}"
