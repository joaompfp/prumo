# Notebook time transformations: verification and release pack

The owner approved comparison across publication frequencies and explicit analytical transformations, then authorized commit, push, merge and production deployment. The existing plot-first notebook and data pipeline remain the baseline. Implementation/design: [spec](../../../specs/2026-11-20-notebook-time-transformations-design.md), [plan](../../../plans/2026-11-20-notebook-time-transformations.md). Reader methods: [Caderno](../../../../data/notebook.md).

## Implementation and scope

Native mixed A/S/Q/M/D charts merge real period-start positions, retain each native period, leave absent cells empty and break each line only at a missing native period. Two explicit axes remain available. Complete-year annual means/year-end views, base100 for reviewed levels and percentage-point differences for reviewed rates are explicit options. All calculations retain raw inputs and base evidence and compare Decimal output to independently rounded Fraction output. Monthly HICP means are labelled as calculated annual means of monthly year-on-year rates, not official annual inflation. Source values, CSVs, schema, worker, rights and authored CMS content are not modified.

Provider commits f477613/6622dc2; adapter and packaging 3bbe7cd; service c79f634; evidence/print/control corrections ea01c80 and native break exclusion 0453b33; calendar tick/early-year fix a00f0d2; unit-title layout bb4b026; floating-boundary tooltip repair b17901f. Runtime/public-copy wording corrections are recorded by the controller's later commit.

## Independent review

Initial specification review requested changes for native-side evidence/status in mixed annual views, closed print disclosures, missing calendar/aggregation caveats and an unstyled base control. Related minor findings covered per-side calculation marking, presentation copy, excluded invalid-cell counts and annual-mean wording. All were corrected and scoped independently re-reviewed PASS at ea01c80.

Independent quality review identified sampled-year indices used as row indices and early-calendar window underflow. a00f0d2 corrected both, with regressions. Browser acceptance also found clipped/merged axis-unit titles; bb4b026 corrected left/right alignment, stagger and measured gutter. The scoped quality re-review approved these changes. One previously existing long-unit mobile clipping case remains outside the sampled acceptance population; this is not a claim that every possible unit string fits every canvas.

The final real-copy run exposed a separate ECharts boundary error: on 390px the last x coordinate round-tripped a few floating-point units beyond grid containment, leaving the old tooltip while the readout changed. A bounded inward drawing coordinate fixes that behavior without changing a value, period or domain. A 121-row real-browser regression failed against the old bundle and passed after b17901f. A reasoning-only independent review approved the supplied final delta; it is not described as another independently executed suite.

## Real-copy acceptance

`receipt.json` and `receipt.md` record the exact latest harness run. At b17901f the controller reran 110 matrix cells across 320/390/768/1440/1920 on direct and mounted local paths, 2,605 matrix assertions and 223 functional checks, all passing. This covered the real World Bank and Eurostat GDP variants against monthly HICP, annual view, base100 pair/six sides, pp rates, exact first/interior/last pointer/touch/keyboard, full tables/evidence, errors/off/empty, no-JS/blocked/print and unchanged legacy route families. All 23 tables/777,854 rows and schema fingerprints of the isolated production copy stayed unchanged, integrity ok, zero FK violations. Enlarged type, minimum 264px chart height and zero horizontal page overflow were checked; this is not human usability or screen-reader acceptance.

The first failed run is retained under `failed-ea01c80/`; later boundary failures under `checker-80ms/` and `failed-bb4b026-keyboard/`. A subsequent explicit 3-second DOM wait disproved the initial suspicion of a mere 80ms checker race: the boundary defect was real and was fixed in b17901f. The harness now waits for the actual tooltip text before exact comparisons; it never skips the requirement.

The complete offline controller suite on ea01c80 passed 3,089 tests, seven network deselected, three warnings. This precedes later runtime fixes; later focused and exact-main hosted/final full-suite results must be stated separately in the installed record. Do not attribute the old suite to a newer revision.

## Reproduction

Run from repository root, with the exact candidate server already running against an isolated production copy:

```bash
.venv-ci/bin/python docs/superpowers/handoff/reports/time-transformations/run_browser_acceptance.py \
  --base http://127.0.0.1:8197 \
  --db /home/joao/.hermes/cache/scratch/prumo-time-transformations/acceptance.sqlite3
```

The helper starts a local mount proxy and fingerprints the supplied copy. It is a development checker, not a substitute for actual public-prefix/edge checks against a moving production database. `--no-proxy` restricts the run deliberately. The actual release verifies both public addresses independently, exact served assets and content, access/preview, healthy actual images and unchanged worker/schema/CMS baselines.

Neutral screenshots include native mixed, annual, base100 and pp at 1440/390. Print PDFs and exact source-method disclosures are retained. Human screen-reader acceptance stays open. No deployment is implied by a local screenshot; see the installed record once activation has succeeded.
