#!/usr/bin/env python3
"""Build the pinned local Bootstrap component subset used by Prumo's public pages.

The public site needs Bootstrap's control, form, navigation and pagination components,
not the whole framework. This script starts from the official Bootstrap 5.3.9 dist
files, keeps the official reboot stylesheet intact, and extracts only the component
rules whose selectors belong to that reviewed set. The output therefore has no
container/grid/card/badge rules that could collide with Prumo's own presentation.

Reproduce from an official npm package (network is not used by this script):

    npm pack bootstrap@5.3.9
    tar -xzf bootstrap-5.3.9.tgz
    python scripts/vendor_bootstrap.py --package package

Or verify the checked-in bytes and their manifest without the package:

    python scripts/vendor_bootstrap.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = ROOT / "static" / "vendor" / "bootstrap"
SUBSET = VENDOR_DIR / "bootstrap-subset.css"
LICENSE = VENDOR_DIR / "LICENSE"
MANIFEST = VENDOR_DIR / "MANIFEST.json"

VERSION = "5.3.9"
UPSTREAM = {
    "bootstrap.css": "ec743fa098b0dc109177873c05296547234dcff6777c5a7d7324974a1aa4c172",
    "bootstrap-reboot.css": "8667435d3e5865bfdfbf60602245f433151ba918bf0a5518885e5bfef39621e7",
    "LICENSE": "bc0cd18d94c028f1c0b62ec9fdaddcb9921c1e07c29cf52dc7df8cca9daf2488",
}
COMPONENT_PREFIXES = (
    ".btn",
    ".form-label",
    ".form-text",
    ".form-control",
    ".form-select",
    ".form-check",
    ".input-group",
    ".nav-link",
    ".pagination",
    ".page-link",
    ".page-item",
    ".visually-hidden",
)
BANNER = (
    "/*!\n"
    f" * Bootstrap Components Subset v{VERSION} (https://getbootstrap.com/)\n"
    " * Copyright 2011-2026 The Bootstrap Authors\n"
    " * Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)\n"
    " *\n"
    " * Generated for Prumo by scripts/vendor_bootstrap.py. The official Bootstrap\n"
    " * reboot plus the reviewed button, form, navigation, pagination and visually\n"
    " * hidden components. See MANIFEST.json for the upstream byte receipt.\n"
    " */\n"
)


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _strip_source_map(text: str) -> str:
    return re.sub(r"/\*# sourceMappingURL=.*?\*/", "", text).rstrip() + "\n"


def _split_selectors(prelude: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(prelude):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(prelude[start:index].strip())
            start = index + 1
    parts.append(prelude[start:].strip())
    return [part for part in parts if part]


def _allowed(selector: str) -> bool:
    selector = selector.strip()
    if selector.startswith("@") or not selector:
        return False
    # Badge positioning is a Bootstrap badge rule, not a button/form component rule.
    if ".badge" in selector:
        return False
    # The base navigation component only; navbar and tab variants stay out.
    if re.match(r"^\.nav(?=$|[ :,.{[])", selector):
        return True
    for prefix in COMPONENT_PREFIXES:
        if selector == prefix:
            return True
        if any(selector.startswith(prefix + suffix)
               for suffix in ("-", ":", "::", ".", "[", " ", ",", ">")):
            return True
    return False


def _blocks(text: str):
    """Yield (prelude, body, whole) for top-level CSS blocks, skipping comments."""
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end == -1:
                break
            index = end + 2
            continue
        open_brace = text.find("{", index)
        if open_brace == -1:
            break
        prelude = text[index:open_brace].strip()
        depth = 1
        cursor = open_brace + 1
        while cursor < length and depth:
            if text[cursor] == "{":
                depth += 1
            elif text[cursor] == "}":
                depth -= 1
            cursor += 1
        body = text[open_brace + 1:cursor - 1]
        yield prelude, body, text[index:cursor]
        index = cursor


def _extract_components(css: str) -> str:
    pieces: list[str] = []
    for prelude, body, whole in _blocks(css):
        if prelude.startswith("@charset"):
            continue
        if prelude.startswith("@media") or prelude.startswith("@supports"):
            inner = _extract_components(body)
            if inner.strip():
                pieces.append(f"{prelude} {{\n{inner.strip()}\n}}")
            continue
        if prelude.startswith("@"):
            continue
        selectors = _split_selectors(prelude)
        if any(_allowed(selector) for selector in selectors):
            pieces.append(whole.strip())
    return "\n\n".join(pieces) + ("\n" if pieces else "")


def _read_package(package: Path) -> tuple[str, str, bytes]:
    css = package / "dist" / "css" / "bootstrap.css"
    reboot = package / "dist" / "css" / "bootstrap-reboot.css"
    licence = package / "LICENSE"
    for path in (css, reboot, licence):
        if not path.is_file():
            raise SystemExit(f"missing official Bootstrap file: {path}")
    return (css.read_text(encoding="utf-8"),
            reboot.read_text(encoding="utf-8"),
            licence.read_bytes())


def build(package: Path) -> None:
    css, reboot, licence = _read_package(package)
    for name, expected in UPSTREAM.items():
        actual = sha256((package / ("dist/css/" + name if name.endswith(".css") else name)).read_bytes())
        if actual != expected:
            raise SystemExit(f"{name}: upstream hash changed: {actual}")
    components = _extract_components(css)
    if not components.strip():
        raise SystemExit("no Bootstrap component rules were selected")
    subset = BANNER + _strip_source_map(reboot) + "\n" + components
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    SUBSET.write_text(subset, encoding="utf-8")
    LICENSE.write_bytes(licence)
    manifest = {
        "package": "bootstrap",
        "version": VERSION,
        "source": "https://www.npmjs.com/package/bootstrap/v/5.3.9",
        "reproduce": (
            "npm pack bootstrap@5.3.9 && tar -xzf bootstrap-5.3.9.tgz && "
            "python scripts/vendor_bootstrap.py --package package"
        ),
        "components": [
            "reboot", "buttons", "form-label", "form-text", "form-control",
            "form-select", "form-check", "input-group", "nav", "nav-link",
            "pagination", "page-item", "page-link", "visually-hidden",
        ],
        "upstream": {
            name: {"sha256": expected}
            for name, expected in sorted(UPSTREAM.items())
        },
        "subset": {
            "path": "static/vendor/bootstrap/bootstrap-subset.css",
            "bytes": len(subset.encode("utf-8")),
            "sha256": sha256(subset.encode("utf-8")),
        },
        "license": {
            "path": "static/vendor/bootstrap/LICENSE",
            "sha256": sha256(licence),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"wrote {SUBSET.relative_to(ROOT)} ({manifest['subset']['bytes']} bytes)")
    print(f"sha256 {manifest['subset']['sha256']}")


def check() -> None:
    if not SUBSET.is_file() or not MANIFEST.is_file() or not LICENSE.is_file():
        raise SystemExit("vendored Bootstrap files or manifest are missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["version"] != VERSION:
        raise SystemExit("manifest version does not match the vendor script")
    body = SUBSET.read_bytes()
    if len(body) != manifest["subset"]["bytes"] or sha256(body) != manifest["subset"]["sha256"]:
        raise SystemExit("bootstrap-subset.css does not match MANIFEST.json")
    licence = LICENSE.read_bytes()
    if sha256(licence) != manifest["license"]["sha256"]:
        raise SystemExit("LICENSE does not match MANIFEST.json")
    print(f"ok {SUBSET.relative_to(ROOT)} sha256 {manifest['subset']['sha256']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="extracted bootstrap@5.3.9 npm package")
    parser.add_argument("--check", action="store_true", help="verify checked-in vendor bytes")
    args = parser.parse_args()
    if args.check:
        check()
    elif args.package:
        build(args.package)
    else:
        parser.error("choose --package <dir> or --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
