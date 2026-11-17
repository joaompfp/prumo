# Prumo Tabler UI - quality and integration review

Scope: runtime HEAD 5f3e4e2 against baseline 7a35f47. Read-only inspection,
bounded local probes, no network, no full suite, no production access.

Verdict: one material accessibility finding. The rest of the change is sound
and keeps the server-rendered, no-JS baseline intact.

## Material finding: soft secondary badges fail light-mode AA contrast, and `.muted` cannot fix them

Evidence:

- Tabler's `.badge` defaults `--tblr-badge-color: var(--tblr-secondary)`.
  The pinned stylesheet resolves `--tblr-secondary` to
  `light-dark(var(--tblr-gray-500), var(--tblr-gray-400))`, which is
  `#737373` in light mode.
- Tabler's `.bg-secondary-lt` utility also sets
  `color: color-mix(... var(--tblr-secondary) ...) !important` and gives the
  badge a 10 percent secondary tint. The `!important` means the custom
  `.badge.muted` rule at `static/css/admin.css:339` is ignored on badges that
  also carry `bg-secondary-lt`.
- Measured contrast for `#737373` on the 10 percent tint: 4.2:1 over a white
  parent and 3.9:1 over the paper parent. Tabler's badge font is 12 px medium,
  so the required ratio is 4.5:1. Dark mode is fine because it resolves to
  gray-400 on a dark surface (about 5:1).
- Affected user-visible status and count badges:
  `backoffice/templates/cms_editor.html:16` (Versao),
  `backoffice/templates/cms_editor.html:17` (So rascunho),
  `backoffice/templates/cms_editor.html:30` (usage count),
  `backoffice/templates/cms_editor.html:34` (`bg-secondary-lt muted`),
  `backoffice/templates/cms_list.html:34-35` (Rascunho privado, versao),
  `backoffice/templates/queue.html:32` (item count),
  `backoffice/templates/derived_list.html:25-26` (series and served counts).
- The baseline rendered status text in normal ink on the page, about 12.5:1.
  This is a real reduction for labels that carry publication and count state,
  not only a cosmetic tint change.

Suggested fix, applied after the vendor stylesheet:

```css
.badge.bg-secondary-lt { color: var(--muted) !important; }
```

`--muted` is `#52645f` in light (about 5.8:1 on the tint) and `#a8b8b2` in
dark (about 7:1 on the dark tint). If the project prefers to keep the Tabler
secondary hue, override `--tblr-secondary` only inside the badge selector, not
globally, because the same token also drives outline buttons and borders.

## Checks that passed

- Local assets: `backoffice/templates/base.html:9` loads the pinned Tabler CSS
  before `admin.css` and `icons.css`; no offsite `src` or `href` was added.
  The vendor stylesheet has zero non-data `url()` values and zero U+2014
  characters. Manifest bytes and SHA-256 values match the committed files:
  `tabler.min.css` 4421622c90b17e122517d1f4bcc245be004ef3e353f43481ef07e13a55d32ce3
  (683684 bytes), `LICENSE`
  4f88a82d13be3c5c63a12c5631eae914aa4381b6dc17641bf1ab85f3f8f6c8a5
  (1090 bytes).
- Security and serving: `backoffice/app.py:64-66` keeps
  `style-src 'self'`, `script-src 'self'`, and `img-src 'self' data:`, so the
  embedded Tabler SVG data URIs are allowed and no new origin is trusted. No
  inline `style` or `<script>` was added to any backoffice template.
  `.dockerignore` keeps `!static/**`, so the vendor tree reaches the image.
- No dead Tabler JavaScript path: no template or script uses `data-bs-*`,
  Bootstrap, or Tabler JS. All disclosure, tabs-like section navigation, and
  form submission remain native HTML. `admin.js` only adds `aria-current` and
  filtering on top.
- Forms are semantically unchanged: for every changed template the sorted
  multiset of `name=` attributes and the sorted multiset of `action=` values
  are identical to baseline. Methods are unchanged, and the editor form closes
  before the publication, history, restore, and duplicate forms, so no nested
  forms were introduced.
- No-JS path: section jump links, all eight `<details>` elements, and every
  form work without JavaScript. The custom disclosure marker selectors cover
  every details class in use (`bare`, `block-card`, `disclosure`,
  `identity-card`).
- Other vendor class usage is valid: `btn-ghost-secondary` exists in Tabler
  1.7.5, as do `badge-sm` and `table-vcenter`. A static scan of all backoffice
  templates found no visible input, select, textarea, or button missing the
  expected `form-control`, `form-select`, `form-check-input`, or `btn` class.
- Date filter: `backoffice/app.py:91` registers `display_time` on the same
  Jinja environment. `cms_editor.html:17`, `:497`, and `:541` keep the exact
  stored ISO value in `datetime` and show the localized value as text. The
  helper accepts strings, returns the input unchanged when it cannot parse,
  and is escaped by autoescape.
- Dark contrast: measured token pairs all pass AA for body text. Lowest text
  pair is white on the dark primary fill at 5.08:1; semantic pairs range from
  5.6:1 to 8.6:1; dark muted text is 7.96:1 on surface and 8.79:1 on paper;
  dark ink is 15.53:1. The active nav and badge tints also pass.
- Public CSS: no new offsite asset; `--muted` on paper is 5.75:1, accent links
  are about 9:1, white on the accent button is 9.03:1, and the new table hover
  uses an accent tint with ink text. `.windows` is a flex container, so the
  40 px `min-height` on its anchor children takes effect. Search, nav, and
  window states use borders plus `aria-current`, not color alone.
- Vendor rebuild script: `tools/ui/vendor_tabler.py` verifies the npm archive
  SHA-512, extracts only the named CSS member, rejects `@import` and non-data
  URLs, pins the license SHA-256, removes the source map, and writes a
  deterministic gzip size. No package script is executed.

## Non-blocking observation

Tabler's control border resolves to `--line` (`#dbe2dd`), which is 1.3:1
against the white control surface. The previous stylesheet used `--line-strong`
at about 1.55:1. Both are below the 3:1 non-text contrast target for field
boundaries, so this is a small regression in ratio but not a new WCAG failure
introduced by this change. If the audit includes WCAG 1.4.11, a darker control
border token should be chosen. This is recorded for completeness, not as a
blocking item.

## Files written

- `docs/superpowers/handoff/reports/tabler-ui/quality-review.md`

No source, test, staging, or commit changes were made.
