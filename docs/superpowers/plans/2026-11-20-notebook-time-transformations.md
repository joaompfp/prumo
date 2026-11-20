# Notebook time alignment and transformations implementation

Authority: owner approved the previous proposal and explicitly authorized commit, push, merge and deployment. Specification: `../specs/2026-11-20-notebook-time-transformations-design.md`. Baseline b6c9b42. This is the additional T phase of the analytical-workspace roadmap, prioritized before B by the owner.

## Tasks and ownership

T1: pure analytical contract in `analysis/periods.py`, `analysis/transforms.py`, tests under `tests/analysis/`. Reviewed family policies, immutable inputs/outputs, complete-year annualisation, Decimal plus independent Fraction checking, shared base. Domain has no SQL/HTTP/templates and never writes source data. Commit tested provider before consumers.

T2: additive sparse calendar model/renderer/payload in `app/calendar_model.py`, `app/calendar_svg.py`, explicit dispatch in `app/charts.py` and `app/interactive.py`; scoped tests. Preserve dense golden bytes. T1 and T2 have file-disjoint ownership and can proceed in parallel after the spec contract.

T3: notebook service/query/copy/templates plus local ECharts v2 adapter. Consume committed T1/T2 providers; do not commit imports of untracked files. Native mixed-frequency chart, annual view, normalization/base and complete method/input disclosure; preserve off/empty/add/remove/search/share, exact originals, same-snapshot eligibility and static Admin previews. Rebuild and reproduce pinned bundle with original licences and typography hash guard. Update reader methodology and notebook guide.

T4: independent specification review then quality review, focused tests, full offline controller suite, real-copy browser/visual acceptance and protected fingerprints. Repair and independently re-review important findings; record actual tested revisions, known warning scopes and human screen-reader gate.

T5: clean committed-checkout gate; push and remote readback; authorized main merge and exact-SHA hosted CI; mount-safe detached prebuild and normal web/Admin deployment. Worker/schema/CMS remain unchanged. Pin actual rollback images, verify installed route content/interactions/assets/logs and exact worker baseline. Update handoff, operation record and owner roadmap; send owner one concise installed result, no redundant release question.

## Progress

T1-T3 implemented: f477613, 6622dc2, 3bbe7cd and c79f634, followed by independently reviewed evidence/print/domain/axis and last-point corrections through b17901f. Specification re-review PASS; quality re-review scoped APPROVED. Controller real-copy acceptance at b17901f passed110 matrix cells (2605 assertions) and223 functional checks with all23table fingerprints unchanged. Earlier full offline suite3089passed at ea01c80 retains its pre-correction scope. Final code/copy checks and exact-release full-suite/CI are recorded by the controller separately. T5 release remains authorized, pending exact-main CI and activation; it does not require another owner permission.

Reader-copy correction: methodology now distinguishes original source precision from explicit six-decimal analytical views; normalized captions name source unit and graph unit separately and mark calculated sides. This does not change a statistical result, model or source-data contract.
