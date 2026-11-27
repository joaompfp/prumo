# Bootstrap 5.3.9 component subset

Prumo's public pages load one pinned local Bootstrap stylesheet. It is not the full
framework: only reboot plus the button, form, navigation, pagination and visually hidden
components are present, so Bootstrap's `.card`, `.badge` and navbar rules cannot collide
with Prumo's own presentation or its Admin Tabler toolkit.

- Upstream package: `bootstrap@5.3.9` from npm.
- Upstream files: `dist/css/bootstrap-reboot.css` and `dist/css/bootstrap.css`.
- Licence: MIT, reproduced in `LICENSE`.
- Byte receipt and component list: `MANIFEST.json`.
- The public templates load `bootstrap-subset.css` before `fonts.css` and `prumo.css`.

Reproduce from the official npm package:

```bash
npm pack bootstrap@5.3.9
tar -xzf bootstrap-5.3.9.tgz
python scripts/vendor_bootstrap.py --package package
```

Verify the checked-in bytes without the package:

```bash
python scripts/vendor_bootstrap.py --check
```

The script refuses a package whose pinned upstream SHA-256 values differ. It never
downloads anything at runtime and the generated stylesheet contains no `@import`, no
remote URL and no script.
