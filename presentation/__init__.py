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


def calculated_attribution(lang: str, attribution: str) -> str:
    return f"{attribution} — {_catalog(lang).ATTRIBUTION_SUFFIX}"
