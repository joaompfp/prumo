"""Derived layer (project 3): calculated series over verified served observations."""

_LABELS = {
    "period_change": "Variação face ao período anterior (diferença), calculada pelo Prumo "
                     "a partir de {base}",
    "period_change_pct": "Variação face ao período anterior (%), calculada pelo Prumo "
                         "a partir de {base}",
    "yoy_change": "Variação homóloga (diferença), calculada pelo Prumo a partir de {base}",
    "yoy_change_pct": "Variação homóloga (%), calculada pelo Prumo a partir de {base}",
    "rebase_100": "Índice rebaseado ({base_period} = 100), calculado pelo Prumo "
                  "a partir de {base}",
}


def formula_label_pt(formula: str, params: dict[str, str], base_series_id: str) -> str:
    """The Portuguese reader-facing description of how a derived value was calculated."""
    if formula not in _LABELS:
        raise ValueError(f"unknown formula {formula!r}")
    if formula == "rebase_100" and "base_period" not in params:
        raise ValueError("rebase_100 needs params['base_period']")
    return _LABELS[formula].format(base=base_series_id, **params)
