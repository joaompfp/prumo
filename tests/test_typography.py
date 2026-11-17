"""Keep project-owned text free of em dashes, including encoded spellings.

Original publisher receipts are immutable evidence, not editorial copy. The one
receipt containing an encoded em dash is exempt only while its hash is unchanged.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(
    "|".join((
        chr(0x2014),
        r"\\u" + "2014",
        r"\\U" + "00002014",
        r"\\u\{0*2014\}",
        r"\\N\{EM DASH\}",
        r"\\0*2014(?![0-9a-f])",
        "%" + r"e2%80%94",
        "&" + r"mdash;?",
        "&" + r"#0*8212;?",
        "&" + r"#x0*2014;?",
    )),
    re.IGNORECASE,
)
ORIGINAL_RECEIPT = (
    "docs/superpowers/handoff/evidence/task-16-discovery/01-eredes-catalog.body"
)
ORIGINAL_RECEIPT_SHA256 = "551b749b9d8f35c87248ec3445b6f4ec852e76dfd08502d26c7223c197580bd8"
# The generated ECharts bundle carries upstream localisation strings verbatim, including one
# em dash inside library code. It is vendored evidence, not authored copy: exempt only while the
# exact rebuilt bytes match this hash, so any rebuild is an explicit reviewed change.
VENDORED_BUNDLE = "static/js/prumo-charts.min.js"
VENDORED_BUNDLE_SHA256 = "70a45c776a6bf397f75ddd0e22807ec837a7ba3a4b0545b61d2ff79c9a4e3d0a"


@pytest.mark.parametrize("text", [
    chr(0x2014),
    chr(92) + "u2014",
    chr(92) + "U00002014",
    chr(92) + "u{2014}",
    chr(92) + "N{EM DASH}",
    chr(92) + "2014 ",
    chr(92) + "002014",
    "%" + "E2%80%94",
    "&" + "mdash;",
    "&" + "#8212;",
    "&" + "#x2014;",
    "&" + "#X02014;",
])
def test_em_dash_spellings_are_rejected(text):
    assert FORBIDDEN.search(text)


@pytest.mark.parametrize("text", ["Prumo - dados", "0x2014", "U+2014", "1998-2026"])
def test_plain_hyphens_and_code_point_names_are_allowed(text):
    assert not FORBIDDEN.search(text)


def _repository_files():
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    ).decode("utf-8").split("\0")
    return [(name, ROOT / name) for name in sorted(set(names) - {""})]


def test_repository_text_has_no_em_dashes():
    receipt = ROOT / ORIGINAL_RECEIPT
    assert receipt.is_file() and not receipt.is_symlink()
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == ORIGINAL_RECEIPT_SHA256
    violations = []
    for name, path in _repository_files():
        if path.is_symlink() or not path.is_file():
            continue
        body = path.read_bytes()
        if name == ORIGINAL_RECEIPT:
            # Keep the archived HTTP response byte-identical to its original capture.
            assert hashlib.sha256(body).hexdigest() == ORIGINAL_RECEIPT_SHA256
            continue
        if name == VENDORED_BUNDLE:
            # Upstream ECharts localisation text is preserved, not rewritten.
            assert hashlib.sha256(body).hexdigest() == VENDORED_BUNDLE_SHA256
            continue
        if b"\0" in body:
            continue
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN.search(line):
                violations.append(f"{name}:{number}")
    assert not violations, "Replace em dashes with ASCII hyphens (-):\n" + "\n".join(violations)


def test_repository_json_documents_are_valid():
    invalid = []
    for name, path in _repository_files():
        if path.suffix not in {".json", ".ipynb"} or not path.is_file() or path.is_symlink():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            invalid.append(f"{name}: {exc}")
    assert not invalid, "Invalid JSON or notebook documents:\n" + "\n".join(invalid)
