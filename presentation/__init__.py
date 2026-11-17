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
                     base_label: str) -> str:
    template = _lookup(_catalog(lang).FORMULAS, "formula", lang, formula)
    if formula == "rebase_100" and "base_period" not in params:
        raise ValueError("rebase_100 needs params['base_period']")
    return template.format(base=base_label, **params)


def unit_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).UNITS, "unit", lang, code)


def caveat_text(lang: str, code: str) -> str:
    return _lookup(_catalog(lang).CAVEATS, "caveat", lang, code)


def derived_title(lang: str, key: str) -> str:
    return _lookup(_catalog(lang).TITLES, "title", lang, key)


def search_aliases(lang: str, family: str) -> str:
    """Extra words a reader may type for this family (empty when none are declared)."""
    return _catalog(lang).SEARCH_ALIASES.get(family, "")


def source_text(text: str) -> str:
    """Apply display typography to stored source copy, never to values or evidence."""
    return text.replace(chr(0x2014), "-")


def calculated_attribution(lang: str, attribution: str) -> str:
    return f"{source_text(attribution)} - {_catalog(lang).ATTRIBUTION_SUFFIX}"


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


def chart_ui(lang: str, key: str) -> str:
    """Words the interactive chart adds around a prepared chart (label, hint, calculated)."""
    return _lookup(_catalog(lang).CHART_UI, "chart ui", lang, key)


def withheld_note(lang: str, name: str) -> str:
    """Why a withheld institution publishes nothing here, in reader words."""
    return _lookup(_catalog(lang).WITHHELD_NOTES, "withheld source", lang, name)


def series_title(lang: str, family: str, geography: str) -> str:
    """`family - geography`, except for families whose title already names the place."""
    catalog = _catalog(lang)
    title = _lookup(catalog.FAMILIES, "family", lang, family)
    if family in catalog.SELF_LOCATING_FAMILIES:
        return title
    return f"{title} - {_lookup(catalog.GEOGRAPHIES, 'geography', lang, geography)}"


def family_of(indicator_key: str) -> str:
    """The indicator family: the key without its trailing geography and frequency parts.
    `consumer_confidence.AT.M` -> `consumer_confidence`; a two-part key stays whole.
    Lives here because a family is what `series_title` needs, not what the data layer stores.
    """
    parts = indicator_key.split(".")
    return ".".join(parts[:-2]) if len(parts) >= 3 else indicator_key


def page_text(lang: str, slug: str) -> dict[str, str]:
    """A public page's copy (title, section heading and notes) by slug.

    The page set lives in code so every public sentence is reviewed; a composition in the
    database only chooses which series appear. An unknown slug raises MissingText.
    """
    catalog = _catalog(lang)
    try:
        return catalog.PAGES[slug]
    except KeyError:
        raise MissingText(f"no {lang} page text for {slug!r}") from None


# --- two-series comparisons (project 4, extension) -------------------------------------------

def comparison_intro(lang: str) -> str:
    return _catalog(lang).COMPARISONS_INTRO


def comparisons(lang: str) -> dict[str, dict[str, str]]:
    """The curated pairs, in reading order, keyed by slug.

    A pair is code, not data: its two series, its title, its one-sentence mechanism and its scale
    mode are all reviewed in git. There is no route that accepts two series ids.
    """
    return _catalog(lang).COMPARISONS


PAIR_KEYS = ("series_a", "series_b", "title", "subtitle", "mechanism", "scale", "caption_note")


def comparison_pair(lang: str, slug: str) -> dict[str, str]:
    """One curated pair, with every key it needs. A missing key is an operator fault and raises
    MissingText (the app renders 503 and logs the slug), never a KeyError 500 on a public page."""
    catalog = _catalog(lang)
    try:
        pair = catalog.COMPARISONS[slug]
    except KeyError:
        raise MissingText(f"no {lang} comparison for {slug!r}") from None
    for key in PAIR_KEYS:
        if key not in pair or not str(pair[key]).strip():
            raise MissingText(f"comparison {slug!r} has no {lang} {key}")
    return pair


# --- country comparisons (project 4, extension) -----------------------------------------------

COUNTRY_COMPARISON_KEYS = (
    "family", "source", "dataset", "frequency", "unit", "seasonal_adjustment", "multiplier",
    "base_year", "dimensions", "title", "subtitle", "mechanism", "caption_note",
    "definition_note", "notebook_action",
)
_COUNTRY_COMPARISON_TEXT_KEYS = (
    "title", "subtitle", "mechanism", "caption_note", "definition_note", "notebook_action",
)


def country_comparisons(lang: str) -> dict[str, dict]:
    """The curated country groups, in reading order, keyed by slug. Code, not data: there is no
    route that accepts a list of series ids."""
    groups = _catalog(lang).COUNTRY_COMPARISONS
    if not isinstance(groups, dict):
        raise MissingText(f"{lang} country comparisons are not a mapping")
    return groups


def country_comparisons_title(lang: str) -> str:
    title = _catalog(lang).COUNTRY_COMPARISONS_TITLE
    if not isinstance(title, str) or not title.strip():
        raise MissingText(f"no {lang} country comparisons title")
    return title


def country_comparisons_intro(lang: str) -> str:
    intro = _catalog(lang).COUNTRY_COMPARISONS_INTRO
    if not isinstance(intro, str) or not intro.strip():
        raise MissingText(f"no {lang} country comparisons intro")
    return intro


def country_comparison_countries(lang: str) -> tuple[str, ...]:
    """The fixed ordered countries of every group, validated before any page uses them."""
    countries = tuple(_catalog(lang).COUNTRY_COMPARISONS_COUNTRIES)
    if not 3 <= len(countries) <= 6 or len(set(countries)) != len(countries):
        raise MissingText(f"{lang} country comparisons need three to six unique countries")
    if any(not isinstance(code, str) or not code.strip() for code in countries):
        raise MissingText(f"{lang} country comparisons have a blank country code")
    labels = [geography_name(lang, code) for code in countries]
    if len(set(labels)) != len(labels):
        raise MissingText(f"{lang} country comparisons have duplicate geography labels")
    return countries


def country_comparison(lang: str, slug: str) -> dict:
    """One curated country group, with every reviewed field it needs.

    Unknown slugs are the caller's 404. A known slug whose authored definition is incomplete or
    malformed raises MissingText: the app logs it and serves the generic 503 instead of leaking a
    KeyError or drawing a group under a title the catalogue no longer supports.
    """
    catalog = _catalog(lang)
    try:
        group = catalog.COUNTRY_COMPARISONS[slug]
    except KeyError:
        raise MissingText(f"no {lang} country comparison for {slug!r}") from None
    if not isinstance(group, dict):
        raise MissingText(f"country comparison {slug!r} is not a mapping in {lang}")
    for key in COUNTRY_COMPARISON_KEYS:
        if key not in group:
            raise MissingText(f"country comparison {slug!r} has no {lang} {key}")
    for key in _COUNTRY_COMPARISON_TEXT_KEYS:
        value = group[key]
        if not isinstance(value, str) or not value.strip():
            raise MissingText(f"country comparison {slug!r} has a blank {lang} {key}")
    for key in ("family", "source", "dataset", "unit", "frequency"):
        value = group[key]
        if not isinstance(value, str) or not value.strip():
            raise MissingText(f"country comparison {slug!r} has a blank {lang} {key}")
    dimensions = group["dimensions"]
    if not isinstance(dimensions, dict) or not dimensions or "geo" in dimensions:
        raise MissingText(f"country comparison {slug!r} has no pinned native dimensions")
    for key, value in dimensions.items():
        if not isinstance(key, str) or not key.strip() \
                or not isinstance(value, str) or not value.strip():
            raise MissingText(f"country comparison {slug!r} has a malformed native dimension")
    adjustment = group["seasonal_adjustment"]
    if adjustment is not None:
        if not isinstance(adjustment, str) or not adjustment.strip():
            raise MissingText(f"country comparison {slug!r} has a blank seasonal adjustment")
        seasonal_text(lang, adjustment)
    multiplier = group["multiplier"]
    if multiplier is not None and (isinstance(multiplier, bool)
                                   or not isinstance(multiplier, (int, float))):
        raise MissingText(f"country comparison {slug!r} has a malformed multiplier")
    base_year = group["base_year"]
    if base_year is not None and (isinstance(base_year, bool) or not isinstance(base_year, int)):
        raise MissingText(f"country comparison {slug!r} has a malformed base year")
    # Every visible code must resolve; a missing family/unit/source is a catalogue fault.
    family_title(lang, group["family"].replace(".", "_"))
    source_title(lang, group["source"])
    base_unit_text(lang, group["unit"])
    frequency_text(lang, group["frequency"])
    country_comparison_countries(lang)
    return group
