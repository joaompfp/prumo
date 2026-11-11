"""Recorded real World Bank bulk CSV ZIP exports (tests/ingest/fixtures/worldbank/,
fetched 2026-11-11 from the publisher's genuine CSV channel
https://api.worldbank.org/v2/en/indicator/<CODE>?downloadformat=csv; full archives, sha256-pinned
by MANIFEST.json) and an Http double that serves one ZIP per indicator code. Imports nothing
from the collector side (safe to use from the independence-guard entrypoint)."""
import base64
import json
from pathlib import Path

from ingest.http import HttpResult

VFIX = Path(__file__).resolve().parent / "fixtures" / "worldbank"
_BY_FILE: dict = {e["file"]: e for e in json.loads((VFIX / "MANIFEST.json").read_text())["files"]}

# indicator code -> recorded full ZIP fixture
ZIP_BY_INDICATOR = {
    "NY.GDP.MKTP.CD": "r4-indicator-csv.zip",
    "SP.POP.TOTL": "csv-sp-pop-totl.zip",
    "SL.UEM.TOTL.ZS": "csv-sl-uem-totl-zs.zip",
}
CSV_URL = "https://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv"


def vbody(file: str) -> bytes:
    return (VFIX / file).read_bytes()


def zip_bytes(code: str) -> bytes:
    return vbody(ZIP_BY_INDICATOR[code])


def decode_evidence(blob: bytes) -> list[dict]:
    """Offline (no HTTP) read of an item's versioned 'worldbank-csv-evidence' v1 envelope: one
    exact wire record per deciding response — final URL, ACTUAL HTTP status (from the archive,
    not implied) and the body recovered byte-for-byte. Callers unpack `(rec,)` to pin the
    single deciding ZIP."""
    doc = json.loads(blob)
    assert doc["schema"] == "worldbank-csv-evidence" and doc["version"] == 1
    return [{"url": r["url"], "status": r["status"],
             "body": base64.b64decode(r["body_base64"], validate=True)}
            for r in doc["responses"]]


class VerifyFixtureHttp:
    """Serves one recorded CSV ZIP per indicator code. `override` maps an indicator code to
    replacement bytes (tampering tests); `status` maps a code to a non-2xx probe."""

    def __init__(self, override: dict[str, bytes] | None = None,
                 status: dict[str, int] | None = None):
        self.override = override or {}
        self.status = status or {}
        self.calls: list[str] = []

    def get(self, url, params=None, headers=None, timeout=None):
        for code, file in ZIP_BY_INDICATOR.items():
            if f"/indicator/{code}" in url:
                self.calls.append(code)
                e = _BY_FILE[file]
                return HttpResult(status=int(self.status.get(code, e["status"])),
                                  body=self.override.get(code, vbody(file)), url=e["url"])
        raise AssertionError(f"no recorded worldbank verifier ZIP for {url}")
