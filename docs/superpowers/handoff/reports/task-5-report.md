# Task 5 report
Status: DONE. Commit f121f48.
Files: ingest/validate.py, tests/ingest/test_validate.py.
RED: pytest tests/ingest/test_validate.py -> ModuleNotFoundError: No module named 'ingest.validate' (collection error).
GREEN: pytest tests/ingest -> 122 passed (17 new in test_validate).
Decisions implemented per rulings H, I, flags passthrough (blank -> None), unit blank accepted / strip-exact compare, duplicates reject all occurrences (on normalized period) after per-row checks, precedence bad_period > non_numeric > unit_mismatch, input order preserved.
Notes: RawRow/Rejection are frozen dataclasses; RawRow unit_raw/flag_raw default None. Reuses normalize_period and Observation.from_raw (ValueError -> non_numeric).

## Fix round 1 (I-1, Ruling J) - commit b66e249
Changes: RawRow/Rejection period_raw and value_raw now `str | None`. validate maps period_raw None -> bad_period, value_raw None -> non_numeric (Rejection keeps the None). RawRow.__post_init__ raises TypeError for any non-str, non-None field (float/int/bool/bytes; unit_raw/flag_raw too) with message pointing adapters to json.loads(..., parse_float=str, parse_int=str); no coercion. Added a deliberate-semantics comment on duplicates-after-other-checks.
New tests: None value/period -> exact Rejections; None row does not abort payload; 7 parametrized TypeError cases; three copies all duplicate_period; [("2024-01","1"),("2024-01","abc")] -> first accepted, second non_numeric; same for unit_mismatch copy.
Command: .venv-ci/bin/python -m pytest tests/ingest -v
Result (tail): ... test_validate.py::test_three_copies_all_duplicate PASSED, test_copy_failing_numeric_does_not_make_twin_duplicate PASSED, test_copy_failing_unit_does_not_make_twin_duplicate PASSED
============================= 134 passed in 3.53s ==============================
