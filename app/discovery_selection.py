"""Bounded reader selection for the complete discovery catalogue.

`/pesquisa` lets a reader accumulate references across pages before opening the notebook. That
recovery model is deliberately more lenient than `app.notebook.parse_selection`: it accepts up
to forty-eight raw, syntactically valid `s` parameters (enough to add a full page of results to
a previous selection), keeps their first-appearance order and reports the real unique count.
It never truncates. The notebook's strict twelve-raw-parameter parser stays the final handoff
contract and is not reused here.

The module holds no SQL, no cache and no template markup. Address values are built through one
local-only helper so the discovery and notebook routes cannot invent different prefixes.
"""
import re
from typing import Sequence
from urllib.parse import urlencode

from app import notebook_chart
from ingest.editorial_rules import MAX_SLOTS

MAX_RAW_REFERENCES = 48
MAX_REFERENCES = MAX_SLOTS

_SERIES_ID = re.compile(r"[A-Za-z0-9_.-]{1,255}")
# The catalogue already uses `frequencia` for its series-frequency filter. Chart display
# frequency therefore travels under one explicit alias so a Caderno round trip cannot turn
# `frequencia=anual` into an impossible catalogue filter.
_CHART_ALIASES = {"frequencia": "frequencia_grafico"}


def build_address(path: str, params: Sequence[tuple[str, str]]) -> str:
    """A local path carrying the non-empty `params` in order, percent-encoded once."""
    pairs = [(name, value) for name, value in params if value]
    encoded = urlencode(pairs)
    return f"{path}?{encoded}" if encoded else path


def parse_references(values: Sequence[str]) -> tuple[str, ...] | None:
    """The ordered unique references, or None for an over-ceiling or malformed address.

    The ceiling applies to the raw parameters before deduplication: forty-nine submitted values
    are refused even when they collapse to one series. Thirteen through forty-eight unique
    references are retained; the page explains the twelve-card limit and withholds the handoff
    instead of silently dropping the excess.
    """
    if len(values) > MAX_RAW_REFERENCES:
        return None
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, str) or _SERIES_ID.fullmatch(value) is None:
            return None
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def preserve_order(selection: Sequence[str], previous: Sequence[str]) -> tuple[str, ...]:
    """Keep retained references in prior order; append new choices in submission order.

    Native forms submit hidden off-page fields before visible checked boxes. The separately
    bounded prior-order metadata is not a selection: absent/unchecked references never return.
    """
    selected = set(selection)
    retained = tuple(value for value in previous if value in selected)
    old = set(retained)
    return retained + tuple(value for value in selection if value not in old)


def retire(selection: Sequence[str], values: Sequence[str]) -> tuple[str, ...]:
    """Remove the named references, preserving every other reference and its order.

    A malformed or absent `retirar` value is a no-op: it is a control value, not an address
    reference, and must not turn the whole selection into a generic error.
    """
    named = {value for value in values
             if isinstance(value, str) and _SERIES_ID.fullmatch(value) is not None}
    if not named:
        return tuple(selection)
    return tuple(series_id for series_id in selection if series_id not in named)


def chart_form_params(settings: notebook_chart.ChartSettings) -> list[tuple[str, str]]:
    """The chart settings as catalogue form fields, with the one required name alias."""
    return [(_CHART_ALIASES.get(name, name), value) for name, value in settings.params()]


def _chart_values(values, name: str) -> list[str]:
    """One chart parameter's repeated values from a QueryParams or a plain mapping."""
    if hasattr(values, "getlist"):
        return list(values.getlist(_CHART_ALIASES.get(name, name)))
    raw = values.get(_CHART_ALIASES.get(name, name), ())
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def read_chart_settings(values, selection: Sequence[str]) -> notebook_chart.ChartSettings | None:
    """The Caderno chart settings carried by a catalogue address, or None when invalid.

    `g` values are sanitized against the submitted selection: a grouped series that the reader
    unchecked on this response is pruned with `notebook_chart.without_side`, so the handoff does
    not 404 merely because a hidden round-trip field outlived its checkbox. Every other chart
    parameter keeps the notebook's strict bounds.
    """
    mapped = {name: _chart_values(values, name) for name in notebook_chart.PARAM_NAMES}
    raw_group = mapped["g"]
    for series_id in raw_group:
        if not isinstance(series_id, str) or _SERIES_ID.fullmatch(series_id) is None:
            return None
    candidate = tuple(dict.fromkeys([*selection, *raw_group]))
    settings = notebook_chart.parse_settings(mapped, candidate)
    if settings is None:
        return None
    chosen = set(selection)
    for series_id in raw_group:
        if series_id not in chosen:
            settings = notebook_chart.without_side(settings, series_id)
    return settings
