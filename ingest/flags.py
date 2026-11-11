"""Observation status vocabulary shared by every source adapter (spec G3), and the per-publisher
mappings onto it.

Every fetched observation carries exactly one of FLAGS as its `status_flag` (adapters set
RawRow.flag_raw to a FLAGS member; 'normal' is stored explicitly, never left empty), so the
independent verifier can compare a flag on every sampled item.

FLAGS is ordered weakest -> strongest. When a publisher marks one value with several codes, the
strongest wins (`PRECEDENCE`):
    break        the value is not comparable with the rest of the series (affects every reader
                 of a chart, so it outranks everything);
    provisional  the value will change;
    estimated    the value is an estimate / carries an accuracy caveat;
    revised      the value changed since first publication (informational);
    normal       none of the above.

Unknown codes are never mapped to 'normal': they raise ValueError, so the parse (and therefore
the dataset run) fails loudly as a format_change instead of serving a value whose status we
could not read.
"""

FLAGS = ("normal", "provisional", "estimated", "revised", "break")

# Strongest first.
PRECEDENCE = ("break", "provisional", "estimated", "revised", "normal")

# Eurostat observation flags (code list ESTAT/OBS_FLAG, as published by the dissemination API;
# r and s are pre-2023 codes still present in older vintages). Codes that qualify a published
# value:
EUROSTAT_VALUE_FLAGS = {
    "b": "break",        # break in time series
    "d": "break",        # definition differs: not comparable with the rest of the series
    "p": "provisional",  # provisional
    "e": "estimated",    # estimated
    "s": "estimated",    # Eurostat estimate (pre-2023)
    "f": "estimated",    # forecast: a model value, not a measurement
    "u": "estimated",    # low reliability
    "n": "estimated",    # not significant
    "i": "estimated",    # value imputed by Eurostat or other receiving agencies (API label)
    "r": "revised",      # revised (pre-2023)
}
# Markers that only ever accompany a MISSING value: ':' not available, 'c' confidential,
# 'z' not applicable. Seen on a row that has a value, they mean we misread the payload.
EUROSTAT_NO_VALUE_MARKERS = frozenset({":", "c", "z"})
# Anything else raises (the API publishes each code's meaning in extension.status.label; a new
# code must be reviewed and added here, never defaulted).

# A Eurostat status string is '<observation flags>|<confidentiality>' (JSON-stat labels '|C',
# '|N'; the SDMX TSV renders the same cell as ': @C'). The confidentiality part is the SDMX
# CONF_STATUS. Reviewed codes (both seen in live sts_inpr_m payloads, 2026-11-11); each means the
# cell has NO publishable value. Any other code raises.
EUROSTAT_CONFIDENTIALITY = {
    "C": "confidential",
    "N": "not for publication",
}


def split_eurostat_status(status: str | None) -> tuple[str, str | None]:
    """'b|C' -> ('b', 'C'); 'p' -> ('p', None); '|N' -> ('', 'N'); None -> ('', None).
    The second part is a reviewed confidentiality code (EUROSTAT_CONFIDENTIALITY) or None;
    an unknown or repeated one raises ValueError. The first part still goes through
    map_eurostat_flag."""
    flags, bar, conf = (status or "").partition("|")
    conf = conf.strip()
    if not bar or not conf:
        return flags, None
    if conf not in EUROSTAT_CONFIDENTIALITY:
        raise ValueError(f"unknown Eurostat confidentiality code {conf!r} in {status!r}")
    return flags, conf


def map_eurostat_flag(code: str | None, *, value_present: bool = True) -> str | None:
    """Map a Eurostat flag string (one or more single-letter codes, spaces ignored, e.g. 'p',
    'bp', ': c') onto FLAGS.

    value_present=True (default): returns a FLAGS member ('normal' for None/blank); combined
        codes give the strongest by PRECEDENCE. A no-value marker (':', 'c', 'z') raises.
    value_present=False (the publisher shows no value): returns None after checking that every
        code is known (the row carries no value, so there is no status to keep).
    Any unknown code raises ValueError.
    """
    codes = [c for c in (code or "") if not c.isspace()]
    unknown = sorted({c for c in codes
                      if c not in EUROSTAT_VALUE_FLAGS and c not in EUROSTAT_NO_VALUE_MARKERS})
    if unknown:
        raise ValueError(f"unknown Eurostat flag code(s) {unknown} in {code!r}")
    if not value_present:
        return None
    markers = sorted({c for c in codes if c in EUROSTAT_NO_VALUE_MARKERS})
    if markers:
        raise ValueError(f"Eurostat marker(s) {markers} in {code!r} only accompany a missing "
                         "value, but a value is present")
    mapped = {EUROSTAT_VALUE_FLAGS[c] for c in codes}
    return next((f for f in PRECEDENCE if f in mapped), "normal")


# INE — Statistics Portugal (pindica.jsp JSON). A cell carries an optional conventional sign
# ('sinal_conv') with INE's own description ('sinal_conv_desc'); the sign is also appended to the
# formatted 'ind_string' ('5,0 &'). Reviewed signs only, each paired with the exact description
# observed live (2026-11-11, full-scope probe of every active INE series; see
# docs/superpowers/handoff/reports/task-10-report.md). A known symbol arriving with a different
# description raises: INE could reuse a symbol, and a status we did not review is never 'normal'.
# Signs that qualify a published value -> (flag, description):
INE_VALUE_SIGNS = {
    "&": ("provisional", "Dado provisório"),
}
# Signs that stand INSTEAD of a value (the cell has no 'valor') -> description:
INE_NO_VALUE_SIGNS = {
    "x": "Dado não disponível",
    "-": "Dado nulo ou não aplicável",
}


def map_ine_flag(sign: str | None, description: str | None, *,
                 value_present: bool = True) -> str | None:
    """Map an INE conventional sign onto FLAGS.

    value_present=True: no sign -> 'normal'; a reviewed value sign -> its flag; a no-value sign
        (or anything unknown) raises ValueError.
    value_present=False: a reviewed no-value sign -> None (the row carries no value, so no
        status); no sign at all, a value sign or anything unknown raises ValueError.
    The description must equal the reviewed one for that sign (blank sign needs blank
    description)."""
    sign = (sign or "").strip()
    description = (description or "").strip()
    if not sign:
        if description:
            raise ValueError(f"INE sign description {description!r} without a sign")
        if not value_present:
            raise ValueError("INE cell has no value and no conventional sign explaining why")
        return "normal"
    if sign in INE_VALUE_SIGNS:
        flag, expected = INE_VALUE_SIGNS[sign]
        if description != expected:
            raise ValueError(f"INE sign {sign!r} described as {description!r}, reviewed "
                             f"meaning is {expected!r}")
        if not value_present:
            raise ValueError(f"INE sign {sign!r} ({expected}) on a cell without a value")
        return flag
    if sign in INE_NO_VALUE_SIGNS:
        expected = INE_NO_VALUE_SIGNS[sign]
        if description != expected:
            raise ValueError(f"INE sign {sign!r} described as {description!r}, reviewed "
                             f"meaning is {expected!r}")
        if value_present:
            raise ValueError(f"INE sign {sign!r} ({expected}) only replaces a value, but a "
                             "value is present")
        return None
    raise ValueError(f"unknown INE conventional sign {sign!r} ({description!r})")
