# Independent review dispositions

## Specification

Reviewed implementation through `9868cae`. B1 exact structured point inspection passed. The first B2 report incorrectly treated the legacy `compare.html` and `compare_countries.html` files as active public renderers. The controller checked actual route references: `app/main.py`, `app/cms_routes.py` and `app/cms_reads.py` render `cms_chart.html` for real comparisons, reusable charts and previews. The legacy country route redirects only when a published CMS country document exists. The plan wording was corrected to the CMS-owned route families; no dead route was revived.

A bounded read-only specification re-review confirmed PASS and withdrew that blocker. Human screen-reader and final browser/print gates were assigned to the controller rather than claimed as reviewer execution.

## Quality and security

Read-only quality review of `9868cae` returned APPROVED. The reviewer checked exact DOM-only text construction, shared point preparation, source/compiled hash consistency, prefix-correct CSS, native sparse missing rows and unchanged source-data/CMS boundaries. Its environment could not run Chromium; its skipped browser probes are not counted as passing acceptance.

The controller independently ran the real browser matrix, exact pointer/touch/keyboard test families, static Admin preview and the full CMS draft/publication workflow on an isolated copy. Print explicitly hides the inspector controls and restores SVG; notes and evidence are visible. Payload v2 requires an integer axis for every side, so the review's hypothetical undefined-axis debug attribute cannot arise from an accepted v2 payload.

## Final mobile delta

A separate bounded read-only review of `9868cae..4d6b4c6` returned APPROVED. The nearby fragment shortcut targets the hidden native disclosure body after the plot, preserving no-JavaScript operation. Ordinary series window/day controls retain their read-only GET contract, Caderno/CSV links and validated prefixes. Duplicate breadcrumb text was removed while origin-series links remain in the meta, action and provenance.

The committed new browser test passed on the controller with and without JavaScript. The additional real-data native-day probe exercised the 15-minute selector and submitted its GET form under both prefixes, also with and without JavaScript. Human screen-reader acceptance remains open.

## Visual findings

The controller rejected screenshot-driven requests to normalize source precision or alter statistical domains. The earlier neutral screenshot probe could leave a keyboard tooltip over the plot when the offscreen canvas never received pointer entry. The final capture path explicitly enters/leaves the real visible canvas and checks that tooltip rows are hidden before capture at `scrollY=0`.

Final visual inspection confirms the monthly plot is visible in the 390px first view and the structured inspector's series/value rows are aligned without clipped values. Long multi-series legends and complete evidence remain available below the fold; no claim is made that every six-series label fits the first viewport. The owner's visual acceptance is distinct from automated geometry and these design observations.

The original failing first-view receipt is retained losslessly in `initial-browser-result.json.gz`. Original JSON SHA-256: `1735a64e76b93f0bb3220e10c21609bc988cb7ad2cb2401bab1de651b84703b6`; archive SHA-256: `64c6d2989a7bf397a85940aeed2f6d59d35b68493fb230a18dcc556d48fe2bdc`. Decompression equality was checked before packaging.
