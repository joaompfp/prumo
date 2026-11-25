# Decimal-display correction

## Scope

Candidate branch: `fix/ui-decimal-limits`, based on installed main `50ede36`. The owner requested limits after the source tokens `2.35673648910157` and `80.7926829268293` wrapped across headline lines. A behavior-neutral localization extraction was committed first as `04241a6`.

The new policy is at most two displayed decimal places, HALF_UP, no redundant fractional zeros and Portuguese separators. Tiny nonzero values use bounds instead of zero. Axis labels round rather than truncate and use scientific notation when necessary. See [numeric-display.md](../../../../data/numeric-display.md).

Data, mathematical calculations, chart coordinates/domains and CSV precision are unchanged. Revisions, cross-checks and calculation inputs expose original tokens through closed, escaped disclosures. Public/CMS chart preparation remains shared; no CMS document, publication or migration is changed.

## Verification

Controller checks before the full-suite gate: 116 formatter/evidence/chart-model tests passed; then 66 precision/legibility/typography/backoffice-boundary checks passed, with broader ruff and whitespace checks clean. These are separate overlapping scopes, not a summed test total.

Independent focused review approved the numeric policy, geometry/CSV separation and escaped original evidence. Its separate focused run passed 45 tests. Non-blocking observations concern historical test wording, native disclosure styling and the distinct small-value roles for axis ticks versus value labels. Normal reader values deliberately no longer print full source precision.

The full offline run on the unchanged application runtime executed 3,315 tests: 3,314 passed, one failed, and seven live tests were deselected. The sole failure was an obsolete assertion for the old calculation-precision sentence, not a value, geometry or CSV failure. The test-only follow-up `4c8cb3b` explicitly checks internal six-place calculation precision separately from the two-place reader policy and strengthens visible headline/table assertions. All 66 precision/evidence/annual-analysis tests then passed, both in the working tree and in a clean checkout of that exact follow-up. The earlier clean committed runtime check at `082c4d2` passed 158 tests with local import paths verified. No application/runtime file changed after the whole run began. These scopes are retained separately in `gates.json`; a fresh all-green whole-suite execution and hosted CI are not claimed.

Runner logs/XML and the earlier failed browser checker are losslessly archived under `receipts/`, with original/archive hashes in `manifest.json`. The corrected visible examples are in `assets/worldbank.life_expectancy.DE-390.png` and `assets/worldbank.trade_balance_pct_gdp.DE-1440.png`.

## Browser acceptance

`browser_check.py` exercised the real archived production copy through the local mounted QA server. The accepted run passed 178 checks across 20 populated source-detail/address/viewport cases, plus Caderno, published CMS comparison, catalogue, static Admin preview and no-JavaScript checks. The two screenshot values were located in the archived database as Germany's life expectancy (2024) and trade balance as a percentage of GDP (2025), not invented fixture outputs.

Both public mount shapes and widths 320/390/768/1024/1440 were exercised. The actual main value, payload display, exact numeric geometry, keyboard first/last selection, complete tooltip and original CSV were checked. Default visible text contains no long source token and no page overflow. Local requests and console checks passed. Browser inspection confirmed the large numbers fit clearly without a typography reduction or metadata clipping. Human screen-reader acceptance remains separate.

The archived source copy was `/home/joao/.hermes/cache/scratch/prumo-discovery-20261125/prumo.sqlite3`; its SQLite backup for this task is under `prumo-decimal-20261125`. The entire isolated database file has the same SHA-256 before/after browser QA: `118d2a5f3f0b925f3643d4404fc2ab5cd9dd83d78536841b6b9e2ea105d98b5c`. This is an isolated read-only acceptance, not a claim of a frozen live ingestion database.

The first browser checker incorrectly expected the value in tooltip row zero, which contains the period; that failed receipt is retained. The corrected collector asserts the full row population and value in row one. No app change was made to satisfy the mistaken checker. `golden-deltas.json` pins the eight text-only current SVG golden updates; every geometry/attribute comparison matched the baseline, and older historical captures remain intact.

## Release boundary

No merge or deployment is part of this candidate checkpoint. A later authorized installation affects only `prumo` and `prumo-backoffice`, because Admin's static preview consumes these templates. It requires no migration, worker restart, CMS write, source refresh, rights/ownership or shared-edge change. Until that installation, public pages continue on their prior formatting.
