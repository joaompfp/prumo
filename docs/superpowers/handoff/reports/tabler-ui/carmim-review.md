# Carmim release amendment review

Owner approved the Tabler release and requested the previous carmim highlight instead of petrol green, preserving the plumb-bob icon. Runtime under review: 2899d7d98ae121f8f8f483c7d712c233c6445150 over e80f391. Earlier Tabler specification and quality reviews remain in this directory.

Independent specification review: PASS. Scoped inspection found only palette CSS, favicon fill, chart fallback/bundle metadata and focused tests. Plumb-bob geometry is unchanged; no vendor, template, access, data or migration edits. The bundled JavaScript differs only by its fallback colour. The bundle SHA-256 and byte count match the manifest and typography pin.

Independent quality/integration review after specification PASS: APPROVED. Focused tests were run with the repository virtual environment: 39 passed. Token contrast, cascade, labelled semantic colours, first/second chart mapping, dashed second line, icon geometry and rebuilt bundle were checked. Node gzip measurement reproduced the manifest exactly. Human screen-reader acceptance is not claimed.

Controller acceptance found a further focus issue after those initial approvals: vendor selector specificity and an outline-colour transition made the actual focused control too faint. The root token alone did not establish painted contrast. Fixed in 14f845e with a solid immediate 3px primary outline for keyboard-focused Tabler controls. A fresh independent scoped specification/quality review approved the two-file correction; actual computed outlines were checked on input, select, checkbox and button controls in both colour schemes. The pre-fix controller suite was interrupted, not reported as passing. The contrast driver now measures the actual outline colour rather than the root token, and accepts the visible outline instead of wrongly requiring a box-shadow.

The controller independently runs the final full suite and browser acceptance against the actual local assets and a fresh production-derived SQLite backup. These results and installed status belong to the separate delivery/production receipts; this review is not deployment evidence.
