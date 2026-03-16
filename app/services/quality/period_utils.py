"""Period normalisation helpers for quality checks."""


def _period_to_ym(period: str) -> str | None:
    """Normalise any period string to YYYY-MM for comparison."""
    if not period:
        return None
    p = period.strip()
    if len(p) == 4 and p.isdigit():          # "YYYY" → annual → Dec
        return f"{p}-12"
    if len(p) == 7 and p[4] == '-':
        suffix = p[5:]
        if suffix[0] == 'Q' and suffix[1:].isdigit():   # YYYY-Q1..Q4
            return f"{p[:4]}-{int(suffix[1:]) * 3:02d}"
        if suffix[0] == 'H' and suffix[1:].isdigit():   # YYYY-H1/H2
            return f"{p[:4]}-{int(suffix[1:]) * 6:02d}"
        return p                                         # YYYY-MM
    if len(p) == 9 and ' S' in p:            # "YYYY S1" / "YYYY S2"
        year, _, sem = p.partition(' S')
        return f"{year}-{int(sem) * 6:02d}"
    return p


def _ym_diff_months(a_ym: str, b_ym: str) -> int:
    """Return a - b in months (positive → a is newer). Both must be YYYY-MM."""
    try:
        ay, am = int(a_ym[:4]), int(a_ym[5:7])
        by_, bm = int(b_ym[:4]), int(b_ym[5:7])
        return (ay - by_) * 12 + (am - bm)
    except Exception:
        return 0
