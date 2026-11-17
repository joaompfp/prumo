"""Bounded integer parsing for backoffice forms.

Form values are untrusted text: Python accepts non-ASCII digits and raises on very long
``int()`` conversions, which must be a 422 refusal, never a 500 after a write. SQLite cannot
bind an integer above ``2**63 - 1``, so that is the shared ceiling for every id and version.
"""

SQLITE_MAX_INT = 2**63 - 1
_MAX_DIGITS = len(str(SQLITE_MAX_INT))


def parse_int(value: str | None, *, field: str) -> int:
    """Parse one non-negative ASCII integer no larger than SQLite can bind.

    Raises ``ValueError`` with an operator-facing message for every malformed shape:
    non-ASCII digits (which ``str.isdigit`` would accept), more digits than the ceiling can
    have, and values above the ceiling.
    """
    raw = "" if value is None else value.strip()
    if not raw or len(raw) > _MAX_DIGITS or not raw.isascii() or not raw.isdigit():
        raise ValueError(f"{field} must be an ASCII integer in range")
    try:
        number = int(raw)
    except (ValueError, OverflowError):
        raise ValueError(f"{field} must be an ASCII integer in range") from None
    if number > SQLITE_MAX_INT:
        raise ValueError(f"{field} is above the supported range")
    return number
