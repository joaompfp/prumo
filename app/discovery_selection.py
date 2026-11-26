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

from ingest.editorial_rules import MAX_SLOTS

MAX_RAW_REFERENCES = 48
MAX_REFERENCES = MAX_SLOTS

_SERIES_ID = re.compile(r"[A-Za-z0-9_.-]{1,255}")


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
