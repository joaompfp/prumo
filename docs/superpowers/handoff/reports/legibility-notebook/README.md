# Legibility and notebook implementation record

Status: implemented and independently reviewed on `pipeline-rebuild`, not installed. Baseline
checkout `6f851d4`; production public/Admin runtime remains `14f845e`. Controller full suite passed: 2,717 tests, 7 network deselected, 3 warnings in 1,292.46 seconds.
Code commit: a7388dc3537ee7aeb85bde5e7d0ee9574131dc4a. Implementation approval covers
larger typography, requested designer refinement and a useful surprise feature. No production
release, migration, source-data write, authentication change or edge operation ran.

## Scope and design

A separate designer inspected the actual public UI and an isolated production-copy Admin.
The controller adopted local Lato for text/data/controls and TeX Gyre Schola for display,
retaining carmim, warm paper, charcoal and the approved plumb-bob geometry. Public root/body
17px becomes 25.5px; Admin root 16px becomes 24px and body 14px becomes 21px. The requested 1.5x
minimum also applies to navigation, controls, table cells and fixed chart labels; the proposed
smaller table/nav exceptions were rejected. Layout is recomposed into 3/2/1-card grids, native
mobile disclosures, an editor block outline and a balanced mobile section-navigation grid.

The Caderno is a cohesive GET/HEAD-only read service and route with server-rendered selection,
search and remove/share actions. Ordered references live in the address, with at most twelve,
not accounts/cookies/storage/database. Values and rights remain authoritative. Shared card
markup/preparation avoids a second statistical display contract. Reopening updates the values;
it does not create a historical snapshot. [User guide](../../../../data/notebook.md).

## Verified browser scope

`browser-final/acceptance.json`: 783 passed checks, 485 matched computed-type samples, minimum
ratio 1.5 at matching viewports. It uses the real compiled asset and a fresh online SQLite
backup from f0nix: 217,755,648 bytes, SHA-256
`f6bf13164687f6a46749a850ac7ab6878faa92f9f6d65a70698ee8eabac00b54`, integrity ok, zero FK
violations. Nine screens are retained under `browser-final/` for public/Admin at 1440 and 390.

Coverage includes 320/390/768/1024/1440, public homepage/detail/comparison/catalogue, populated
Admin/editor/operational lists, local fonts, compact menus, notebook starts/search/add/remove/
clear/shared reopening on both public prefixes, noindex and withheld selections. Every actual
SVG text bounding box is checked against its viewBox, including first-paint/no-JS/print
geometry. The shipped dual-axis canvas preserves exact first/last keyboard values. Disabled
JavaScript, missing fonts and reduced motion retain labelled native actions. No console/CSP
errors, warnings or off-origin requests occurred locally. The known installed-edge vr-policy
warning is not closed by this local result.

The complete database fingerprint is identical before/after the notebook workflow. The CMS
mutation workflow then saved a private draft, refused dirty publication, previewed/published/
unpublished/restored on the isolated copy. All twenty non-CMS table fingerprints remain
identical afterwards, with quick_check ok and zero FK violations. No live trial content was
created. Human screen-reader and real human Authelia acceptance remain separate.

`browser-final/contrast.json`: 17 actual cascade groups, minimum sampled text contrast 5.54:1,
with solid focused outlines in light/dark. Exact local public/Admin/vendor/chart asset bytes
match the repository. `font-build.json` independently reproduces all five pinned local WOFF2
subsets through `/usr/bin/python3` FontTools 4.62.1/Brotli 1.2.0; default tool-environment Python
is not the system font-build interpreter. No runtime build dependency or CDN was added.

## Review and correction

Independent specification/safety review approved the notebook after scoped probes. Quality
review required inward endpoint SVG tick labels and a long left-axis unit title that grows
into the plot. The controller fixed both through one shared x-label renderer, added regressions
and checked real rendered bounding boxes; the scoped independent re-review approved them.
CTA spacing and a 2x2 mobile editor section menu also landed. The latter's actual browser
readback was `display:grid`, two 171.406px columns at 390px, four equal-width labelled links;
a review search had missed the early higher-specificity media rule.

Minor dispositions: failure responses carry noindex directly as well as through the public
middleware; missing notebook-search titles raise the generic logged503; the test uses real
create_app registration; series/comparison start actions are tested under both prefixes.
Formatted grouping spaces can wrap at thousands boundaries but all digits/precision and
source tokens remain unchanged. The unit/page-value model is not rescaled or rounded.

Goldens deliberately change for new chrome/fonts and chart geometry. Prior complete bytes
remain under `tests/app/golden/pre_legibility/`; `golden-deltas.json` records hashes and an
unchanged text/title/tick sequence for every chart. The original historic home is untouched.

Initial receipts remain separate: the first scoped run timed out with known fixture/assertion
failures, not an all-green run; `failing-golden-checks.log` shows those before correction. The
first browser matrix passed 773 checks before the additional SVG-bounds assertions; the final
matrix adds those actual bounds checks. A generated-HTML whitespace failure was corrected in
the template and fixture, not suppressed. Raw logs are retained losslessly as compressed
archives with SHA-256 entries in the delivery receipt.

## Acceptance and release boundary

Controller scoped post-review tests: 49 passed,1warning, and ruff clean. Final global result: 2,717 passed, 7 network deselected, 3 warnings in 1,292.46 seconds.
After preserving original whitespace-bearing licences/historic HTML as lossless gzip and
normalizing only the readable licence-copy whitespace, 30 focused checks passed; no application
Python/templates/CSS/JavaScript or compiled font/chart bytes changed after the full run. No hosted CI result is claimed for this branch (the workflow runs on main/PR only).

Release authorization is separate from implementation. Installation needs only public web and
backoffice through the established `dc-web` aliases, no worker/migration/Traefik/Authelia
change, no CMS initialization and no production publication. Preserve database/schema/content
and the worker baseline; pin the currently installed images before rebuilding, verify both
public prefixes and protected Admin, and read back untouched worker identity/start/restarts.
Use the existing schema-unchanged recovery procedure, not a database restore. Current runbook:
[operations.md](../../../../data/operations.md); handoff and the vault roadmap carry the final
branch/installed distinction. Rights/DGEG, lag classification, SIGBUS observation, dated
analyses and AI-draft phases are unchanged by this implementation.
