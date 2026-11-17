# Backoffice Tabler interface implementation

## Outcome

The backoffice now loads the pinned local Tabler stylesheet before `admin.css`, and its
templates use Tabler components directly: `btn`, `form-control`, `form-select`,
`form-check-input`, `card`, `table`, `badge`, `alert`, `nav` and grid utilities. The old
handcrafted control rules were removed rather than layered over.

## Scope kept intact

- Forms keep every method, action, field name, value, hidden version/CAS field and Origin guard.
- Save and publish remain separate; publish/unpublish/restore/duplicate keep
  `data-requires-clean` and `data-confirm`.
- Dirty-draft watch, no-JS flows, native block disclosures and static previews are unchanged.
- No data, service, route, access, public template or vendor file was modified.

## Presentation changes

- System sans shell with warm paper `#f6f5f0`, white surfaces, green ink `#18322f`, primary
  `#1b514b`, hover `#123d38`, muted `#52645f`, rules `#dbe2dd` and small brass `#99672d`.
- Coherent dark equivalents through `light-dark()` and a small `prefers-color-scheme` block.
- Compact sticky sidebar with a clear active navigation item and a wrapped, fully labelled
  narrow-screen navigation.
- Cards, tables, alerts, badges and buttons now come from Tabler. Tables keep labelled stacked
  records on narrow screens.
- CMS list: prepared-home card, quieter section headings, one create entry per section plus its
  disclosure.
- CMS editor: compact status header, sticky reason/save toolbar, content-first block summaries
  with subordinate type badges, styled native chevrons and labelled audit/history tables.
- `admin.js` only gains Tabler classes on its generated option-filter input. Behaviour is
  unchanged.

## Verification

- `.venv-ci/bin/python -m pytest tests/backoffice -q`: 299 passed.
- `.venv-ci/bin/ruff check backoffice tests/backoffice`: clean.
- Browser QA with local Chromium at 1440 and 320, light and dark: no console errors, no
  page-level horizontal overflow, active navigation visible, sticky toolbar reaches the top on
  scroll, stacked CMS records keep their labels.
- Tabler CSS was served through browser route interception for QA because the controller-owned
  pinned vendor file is not in this worktree yet. The template link path and ordering are
  covered by tests.

## Residual risks

- The controller must add `static/vendor/tabler/1.7.5/tabler.min.css` before acceptance; this
  implementation does not own vendor files.
- The parent owns the authoritative full-suite gate and production acceptance; this report only
  covers the focused backoffice run.
- Human assistive-technology acceptance remains a separate gate.
