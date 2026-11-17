"""Prepare the pinned Tabler CSS used only by the backoffice.

The archive is verified before reading exact named members. No package scripts or
archive paths are executed/extracted. Run from any directory with Python 3.12+.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from urllib.request import urlopen

VERSION = "1.7.5"
URL = f"https://registry.npmjs.org/@tabler/core/-/core-{VERSION}.tgz"
INTEGRITY = "lqR2kfrxvH6q0fESm4ABJk3lhUJGQ/tBtiNi4oSCvDgMNljStTLpY38F+e5EtaUqufpbZq8MIxN94QK8cTApAA=="
LICENCE_URL = "https://raw.githubusercontent.com/tabler/tabler/dev/LICENSE"
LICENCE_SHA256 = "4f88a82d13be3c5c63a12c5631eae914aa4381b6dc17641bf1ab85f3f8f6c8a5"
DEST = Path(__file__).resolve().parents[2] / "static" / "vendor" / "tabler" / VERSION


def prepare() -> dict:
    with urlopen(URL, timeout=60) as response:
        archive = response.read(32 * 1024 * 1024)
    if base64.b64encode(hashlib.sha512(archive).digest()).decode() != INTEGRITY:
        raise ValueError("Tabler archive integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        member = package.extractfile("package/dist/css/tabler.min.css")
        if member is None:
            raise ValueError("Tabler CSS is not a regular archive member")
        source = member.read()
    # The npm package omits the project licence; fetch the upstream text with a byte pin.
    with urlopen(LICENCE_URL, timeout=30) as response:
        licence = response.read(32_768)
    if hashlib.sha256(licence).hexdigest() != LICENCE_SHA256:
        raise ValueError("Tabler licence integrity mismatch")
    css = source.decode("utf-8")
    # These are visible generated quote separators, not archived statistical evidence.
    replacements = css.count(chr(0x2014))
    css = css.replace(chr(0x2014), "-")
    css = re.sub(r"/\*# sourceMappingURL=.*?\*/", "", css).rstrip() + "\n"
    if "@import" in css:
        raise ValueError("Review new CSS imports before vendoring")
    for url in re.findall(r"url\(([^)]+)\)", css):
        if not url.strip("\"'").startswith("data:"):
            raise ValueError("Review non-embedded CSS resource before vendoring")
    body = css.encode("utf-8")
    manifest = {
        "package": "@tabler/core",
        "version": VERSION,
        "url": URL,
        "archive_integrity": "sha512-" + INTEGRITY,
        "upstream_css_sha256": hashlib.sha256(source).hexdigest(),
        "changes": {
            "U+2014_to_ASCII_hyphen": replacements,
            "source_map_reference_removed": True,
        },
        "files": {
            "tabler.min.css": {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()},
            "LICENSE": {"bytes": len(licence), "sha256": hashlib.sha256(licence).hexdigest()},
        },
        "local_gzip_bytes": len(gzip.compress(body, mtime=0)),
    }
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "tabler.min.css").write_bytes(body)
    (DEST / "LICENSE").write_bytes(licence)
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
