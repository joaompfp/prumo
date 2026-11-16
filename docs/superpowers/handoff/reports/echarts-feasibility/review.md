# Interactive-chart design review

Scope: `docs/superpowers/specs/2026-11-16-interactive-charts-design.md` and the renderer evidence README. Independent read-only technical discovery preceded design authoring. A separate design review requested changes; a fresh scoped re-review of the revised spec found no remaining material contradictions and returned ready for owner review. These are design reviews, not code-quality or release acceptance.

## Dispositions

Accessible fallback and layout: accepted. The spec now pins an in-flow opacity-zero SVG with an absolute canvas overlay, preserved accessible name, reserved control space, print restoration, and an unchanged following-block offset check. It forbids hiding the accessible SVG with display/visibility/ARIA removal.

Comparison missing periods: clarified, with one reviewer recommendation rejected. The reviewer proposed expanding observations to the union and reporting absent values. The shipped comparison contract deliberately uses the finite intersection, which the owner did not ask to change. That rule stays. Null drawing sentinels now explicitly create breaks but never become inspectable observations, table rows or slider steps. Both genuine comparison values are inspected together. Base/calculated connection behaviour is explicitly `connectNulls:true`.

UTC metadata correction: accepted as a narrow explicit change. It reuses the existing `Db.public_day_counts` on the read-only handle once if needed, adds no SQL definition or upstream request, keeps default-day behaviour when omitted, and answers 404 when an explicit day remains unavailable. Its timing cost must be measured. Other database failures retain existing 503 handling.

Tick and style ownership: accepted. Python owns y bounds and uniform tick interval and supplies both dual axes; the adapter cannot pick a new automatic domain. Solid/dashed line and legend parity is an explicit feature change after the byte-preserving refactor. Animation is disabled.

HTML budget: accepted. Candidate public responses were measured but are not called an exhaustive baseline. The inherited 250,000-byte target is provisional until the largest current population is measured; a miss needs an explicit decision, never data truncation, reduced precision or removal of the fallback. No arbitrary history cap is added. The final bundle budget includes the future adapter, which the measured probe does not.

Assistive technology: accepted. A real screen-reader pass is an explicit gate; if unavailable it must be reported as unmet, not substituted with a DOM assertion.

## Re-review result

The scoped re-review read the revised design, checked the preceding findings and returned no remaining material contradictions. The spec is ready for the owner's review. Application implementation, implementation/code-quality reviews, full-suite acceptance, release authorisation and deployment remain unperformed.
