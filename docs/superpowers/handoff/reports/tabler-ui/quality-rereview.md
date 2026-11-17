# Quality re-review: neutral badge contrast (scoped)

Scope: the single delta `5f3e4e2..0162e7c`, finding Q1 of `quality-review.md` only.
No broad re-review, no source edits, no production changes.

## Delta under review

- `static/css/admin.css`: one new rule, 2 added lines (comment plus declaration):
  `.badge.bg-secondary-lt { color: var(--muted) !important; }`
- `tests/backoffice/test_tabler_ui.py`: 5 added lines, a unit regression that asserts
  the rule text is present in the stylesheet.
- No other tracked files changed (`git diff --stat` reports only these two).

The rule targets the neutral status badge, whose text previously lost AA contrast because
Tabler's light badge utility sets its own color with `!important` over a 10 percent alpha
secondary background.

## Verification method

Measured in a real browser: own cached Chromium 1248, headless, fresh context per scheme,
no HTTP cache, against the local acceptance host
`http://127.0.0.1:8117/dados/admin/cms/page/inicio` (HTTP 200).

Every color was resolved through a canvas rather than string parsing, because the vendor
badge background computes to an `oklab()` value. Background layers were composited
root-to-element including alpha, then the foreground was composited over that result.
Contrast is the WCAG 2.1 relative-luminance ratio. The measured badge text is
10.6971px at weight 500, so the small-text threshold of 4.5:1 applies.

Page contained 3 badges; 1 neutral `bg-secondary-lt` badge in each scheme.

## Measured result: light scheme

| Text | Computed color | Raw background | Composited background | Size / weight | Contrast | AA 4.5:1 |
| --- | --- | --- | --- | --- | --- | --- |
| Versao 16 | `rgb(82, 100, 95)` | `oklab(0.5555 0 0 / 0.1)` | rgb(233, 232, 227) | 10.6971px / 500 | 5.11:1 | PASS |
| legado (context) | `rgb(125, 84, 36)` | `rgb(244, 234, 219)` | rgb(244, 234, 219) | 9.28px / 650 | 5.57:1 | PASS |
| Em direto (context) | oklab green | oklab green / 0.1 | rgb(226, 231, 220) | 10.6971px / 500 | 5.11:1 | PASS |

`--muted` resolves to `#52645f` in light scheme, matching the computed foreground exactly.
The 10 percent secondary layer over the card surface composites to rgb(233, 232, 227).
Ratio 5.11:1 clears 4.5:1 with 0.61 of headroom.

## Measured result: dark scheme

| Text | Computed color | Raw background | Composited background | Size / weight | Contrast | AA 4.5:1 |
| --- | --- | --- | --- | --- | --- | --- |
| Versao 16 | `rgb(168, 184, 178)` | `oklab(0.7155 0 0 / 0.1)` | rgb(32, 37, 34) | 10.6971px / 500 | 7.53:1 | PASS |
| legado (context) | `rgb(224, 183, 122)` | `rgb(51, 40, 27)` | rgb(51, 40, 27) | 9.28px / 650 | 7.69:1 | PASS |
| Em direto (context) | oklab green | oklab green / 0.1 | rgb(31, 41, 33) | 10.6971px / 500 | 8.64:1 | PASS |

`--muted` resolves to `#a8b8b2` in dark scheme, again matching the computed foreground.
Ratio 7.53:1. No descendant element overrides the color; no differing computed child
colors were found.

## Assessment

- Finding Q1 is resolved by measured computed colors, not by the intent of the rule.
  Both schemes clear AA on the neutral badge; worst measured neutral ratio is 5.11:1.
- The override is narrowly scoped to `.badge.bg-secondary-lt`. It does not touch
  `.badge.bad`, `.badge.good`, `.badge.muted`, severity classes, or `bg-success-lt`.
- The `!important` is justified: it exists to defeat a vendor utility that also uses
  `!important`. Precedence is source-order among equal specificity, which is documented
  Tabler behavior, and the comment on the rule records the reason.
- The unit regression pins the selector and declaration so the fix cannot vanish silently.
- Rule ordering matters and is correct: `admin.css` loads after the vendored Tabler sheet,
  so the override wins the source-order tie.

Verdict: APPROVED.

## Residual notes

- Only `/dados/admin/cms/page/inicio` was measured. That is the page the original finding
  cited; the selector is also used on `cms_list.html`, `cms_editor.html`, and
  `series_detail.html`, where the same `--muted` foreground and the same 10 percent
  neutral background apply, so the measured ratio carries over.
- Because the badge background is 10 percent alpha, the composite depends on the parent
  surface. If a future surface darkens or lightens under the badge, re-measure rather
  than assume the ratio holds.
- The light-scheme context badge "Em direto" sits at 5.11:1, the same as the neutral badge.
  It passes, but it is the thinnest margin on the page and worth remembering if the
  success palette is ever retuned.
