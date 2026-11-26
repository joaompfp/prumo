# Quality re-review: compact selection tray and pending-chart guard

Reviewed the uncommitted working-tree delta on top of `daadbba` against the original mandatory
finding in `quality-review.md`. Read-only inspection plus one focused execution probe of the real
`static/js/selection.js`. No server setup, no full suite, no runtime edits and no commit.

## Verdict

APPROVED. The original mandatory finding is closed.

## Finding closure

The original defect was that `#notebook-chart-form` submitted only the applied `page.addressed`
set while the reader could hold pending ticks or unchecks in `#notebook-search-form`, silently
discarding that pending state.

- `static/js/selection.js:17-38` snapshots the initial submitted selection set and recomputes the
  pending flag from the current checkbox and hidden `s` values on every `s` change and on
  `pageshow`.
- `static/js/selection.js:45-55` attaches a submit guard only to `#notebook-chart-form` and only
  from `#notebook-search-form`. With pending changes it calls `preventDefault()` and moves focus
  to the explicit `button[name="acao"][value="abrir"]`. Search and apply submits in the selection
  form are never blocked, so the explicit apply contract remains native.
- `_notebook_search.html:29` renders the pending note that the script reveals. Its wording names
  the apply action: `Tem séries por aplicar. Use Acrescentar selecionadas antes de configurar o
  gráfico.`
- `_notebook_search.html:30` gives the no-script instruction: `Marque várias séries e envie a
  seleção antes de configurar o gráfico. A contagem só muda após o envio.` This is the accepted
  separate-transaction contract. Chart settings continue to operate on the already applied
  notebook, not on drafts, and no unrelated forms were merged or silently auto-applied.
- The catalogue consolidation keeps one `.discovery-selection` tray, a live `n / 12` heading, and
  labels the review count `Último envio`, so the applied count and the live count no longer
  compete as unlabeled duplicates.

## Disabled-choice semantics

The cap logic at `static/js/selection.js:30-34` was checked against the required recovery path:

- At 12 selected, unchecked choices become disabled; checked choices remain enabled and
  removable.
- Unchecking one checked choice drops the count to 11, and the same sync pass sets
  `disabled = false` for every previously disabled choice, so unmatched choices re-enable.
- Returning to the initial selection set clears the pending note and allows the chart submit
  again. A clean page allows the chart submit.
- The disabled attribute exists only in the JavaScript path. The server templates render no
  disabled choices, so a no-JavaScript submission of 13 choices still reaches the honest
  over-limit recovery instead of a silently truncated selection.

The focused probe executed the real script against a minimal 12-of-13 form and passed:
`PASS pending guard, pending note, cap disable, uncheck re-enable, checked removable,
clean-state chart submit`.

## Verification performed

- Inspected `git diff` for only the six changed files: `_notebook_search.html`, `search.html`,
  `discovery.css`, `prumo.css`, `selection.js`, and the changed test expectations.
- Read the current templates that own the two forms and the chart settings submit, confirming
  `#notebook-search-form` and `#notebook-chart-form` are separate, non-nested forms, and that the
  chart submit is inside the guarded chart form.
- Confirmed the search form still owns `q`, hidden off-page `s`, visible checkboxes, `ordem`, and
  the chart handoff fields, so search and apply preserve the submitted chosen and unchosen set
  natively.
- Confirmed `selection.js` is loaded on the notebook only when quick-search results exist, which
  is the only state in which a pending selection can be created, and on the catalogue when rows
  exist.
- `node --check static/js/selection.js` passed. The parent browser evidence covers the pending
  chart guard, the no-script recovery, the 12-choice disable and re-enable path, and the
  three-series chart at the stated widths. I did not repeat the browser matrix or the full test
  suite.
- No data or CMS files are touched by the delta.

## Non-blocking residuals

- **Catalogue no-script count.** Removing the duplicate results bar also removed its `<noscript>`
  note. The consolidated tray has no equivalent, so a no-script catalogue reader ticking rows
  sees the `0 / 12` heading stay unchanged with no explanation. The selection still submits
  correctly. One short no-script note in the tray would restore the old clarity.
- **Live limit message.** When the applied notebook has 11 selections and the reader ticks a
  twelfth, JavaScript disables the remaining choices but the server-rendered limit warning was
  computed at 11 and is absent. The disabled state is the only cue until the selection is
  applied. Unchecking recovers correctly. This is a copy gap, not a state-loss defect.
- **Count wording.** The existing JavaScript count says `N selecionadas` while the notebook
  server copy says `N referências selecionadas`. The value is correct; only the noun changes
  after the first live sync. This predates the delta.
- **Navigation boundary.** Chart activate and deactivate controls are links, not form submits.
  Leaving the page with pending changes loses unsubmitted state by native navigation. The
  guarded form submit, which was the original finding, is closed; the explicit apply contract
  does not turn unrelated navigation into autosave.

No new blocker was found in the compact tray, the pending guard, or the cap recovery.

## Files

- Created `docs/superpowers/handoff/reports/selection-ux/quality-rereview.md`.
- No runtime file was edited or committed.
