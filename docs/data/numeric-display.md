# Numeric display

The owner refined the bounded UI policy to at most four significant figures, replacing the fixed two-decimal limit. This is a presentation change, not a transformation of statistical data.

## Reader values

All normal statistical UI values use `app.formatting.format_value`: at most four significant figures, rounded with Decimal `ROUND_HALF_UP` (ties away from zero). The number of decimal places follows the magnitude. Leading fractional zeros do not consume significant figures; integer place-value zeros remain. Redundant fractional zeros disappear, without padding a publisher's short number to four digits. Decimal commas and grouped thousands follow Portuguese presentation. Exact zero, including a negative-zero token, displays as `0`.

Examples: `2.35673648910157` displays as `2,357`; `80.7926829268293` as `80,79`; `0.0123456` as `0,01235`; `12345` as `12 350`; `1234567.80` as `1 235 000`; and `3.90` as `3,9`. Values below one hundredth are no longer replaced by bounds: `0.004` remains `0,004`.

After rounding, values with a base-ten exponent below -6 or at least 12 use scientific notation to bound text length: `1.234567e-8` displays as `1,235e-8`. Axis labels share the four-significant-figure rule and use scientific notation below one hundredth. Small nonzero values never become a false zero. Unsupported nonnumeric tokens are not guessed or converted. Counts, dates, identifiers and operational evidence are not rounded statistical measurements.

The shared boundary covers public cards, catalogue results, detail summaries, values tables, revisions and cross-checks, calculated detail, Caderno, published CMS charts and the static Admin preview. Plot coordinates and numeric domains continue to use the original numbers, not reader strings. The browser consumes prepared strings and does not repeat rounding.

## Original precision

Publisher tokens, observations, calculation inputs, independent verification and source receipts remain exact. CSV exports bypass the reader formatter and keep stored tokens. Calculated internal precision and verification methods remain unchanged.

Revision/cross-check values and calculation inputs provide a closed `Valor original` disclosure with the complete stored token. This allows inspection of changes beyond the displayed significant figures and reconstruction of calculations without printing long tokens in the ordinary interface. The operational backoffice's source/evidence token tables also retain their exact audit role.

No migration, source refresh, CMS publication, licence change or data rewrite is part of this correction. A reader-only release must include both the public site and the backoffice, since its static preview consumes public preparation and templates; it must not restart ingestion.
