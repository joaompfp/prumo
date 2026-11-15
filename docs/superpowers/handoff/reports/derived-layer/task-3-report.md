# Task 3 report
Status: DONE. Extended ingest/derive.py (CONTEXT, scales, previous_period, year_ago, format_fixed, DerivedValue, Skip, compute); tests in tests/ingest/test_derive_formulas.py (brief's named tests + negative denominator, zero rebase base, ordering/distinct ids, random-grid Fraction property).
Notes: rebase base period yields (id,id) per brief (Task 5 must store [t]); zero rebase base gives per-period zero_denominator skips. Only Decimal via CONTEXT; no float.
