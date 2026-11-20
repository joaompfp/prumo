# Multiscale spec re-review: nominal basis and geography copy

Verdict: PASS for closure of the nominal-versus-real and geography copy findings in
`docs/superpowers/handoff/reports/multiscale/spec-review.md`. No blocker remains in this scoped
re-review.

## Findings closed

1. Nominal GDP per capita basis. The fiscal summary now reads "O peso da dívida pública bruta e do
   saldo orçamental no PIB e o PIB per capita de Portugal, a preços correntes, em valores anuais."
   The trade summary now ends "PIB per capita de Portugal a preços correntes." Both statements are
   reader-facing, so the current-price basis no longer depends on the internal curation report.
2. Nominal interest rates. The first summary now reads "Taxas de juro nominais de referência e
   saldos de crédito e depósitos das famílias em Portugal." The caveat remains explicit that the
   Euribor is a euro-area reference rate and not a Portuguese rate, and that the 10-year rate is a
   Portuguese government bond yield.
3. Geography. The intro now reads "Comparações centradas em Portugal, em dois grupos de escala."
   This removes the earlier "séries portuguesas" implication that every member series is
   Portuguese, while the first card caveat still qualifies the euro-area Euribor member.

## Evidence

- The `git diff` for `presentation/portugal_comparisons.py` contains exactly the four supplied copy
  edits and no other code changes.
- The `git diff` for `tests/app/test_portugal_comparisons.py` adds only
  `test_curated_copy_distinguishes_nominal_values_and_geography`, which asserts "centradas em
  Portugal" in the intro, "nominais" in the first summary, "área do euro" in the first caveat, and
  "a preços correntes" in both the fiscal and trade summaries.
- Independent scoped re-run of `tests/app/test_portugal_comparisons.py`: 6 passed, 1 warning in
  12.55s. This matches the controller's supplied 6 passed in 12.26s.
- `ruff check` on the two changed files: all checks passed.

The full suite was not rerun, by scope.

## Nonblocking notes for the quality pass

- The new assertions are substring checks, not exact-sentence checks. A term could move elsewhere
  in a summary without failing the test. Exact phrases would express the copy intent more tightly
  but be more brittle.
- The test addresses definitions by index (`comparisons[0..2]`), so reordering the definitions
  would change which cards are asserted. This is not a current defect.
- The test imports inside the function body. That is harmless but could move to module scope for
  consistency.
- The prior nonblocking notes in `spec-review.md` remain outside this re-review: group-signature
  distinctness, the calendar unit re-read, and the catalogue cache TTL.
