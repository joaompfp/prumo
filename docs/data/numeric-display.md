# Numeric display

This reader policy implements the owner's request for bounded UI precision, replacing the former full-source-precision display rule. This is a presentation change, not a transformation of statistical data.

## Reader values

All normal statistical UI values use `app.formatting.format_value`: at most two decimal places, rounded with Decimal `ROUND_HALF_UP` (ties away from zero). Redundant fractional zeros disappear; decimal commas and grouped thousands follow Portuguese presentation. Exact zero, including a negative-zero token, displays as `0`.

Examples: `2.35673648910157` displays as `2,36`; `80.7926829268293` as `80,79`; `3.90` as `3,9`; `999.999` as `1 000`.

A nonzero value that would round to zero is shown as a bound: `< 0,01` for a small positive value or `> -0,01` for a small negative value. This must not be interpreted as an exact zero. Axis labels use bounded scientific notation below one hundredth, rather than flattening distinct small ticks to zero. Unsupported nonnumeric tokens are not guessed or converted.

The shared boundary covers public cards, catalogue results, detail summaries, values tables, revisions and cross-checks, calculated detail, Caderno, published CMS charts and the static Admin preview. Plot coordinates and numeric domains continue to use the original numbers, not reader strings. The browser consumes prepared strings and does not repeat rounding.

## Original precision

Publisher tokens, observations, calculation inputs, independent verification and source receipts remain exact. CSV exports bypass the reader formatter and keep stored tokens. Calculated internal precision and verification methods remain unchanged.

Revision/cross-check values and calculation inputs provide a closed `Valor original` disclosure with the complete stored token. This allows inspection of revisions that differ beyond the second decimal place and reconstruction of calculations without printing long tokens in the ordinary interface. The operational backoffice's source/evidence token tables also retain their exact audit role.

No migration, source refresh, CMS publication, licence change or data rewrite is part of this correction. A reader-only release must include both the public site and the backoffice, since its static preview consumes public preparation and templates; it must not restart ingestion.
