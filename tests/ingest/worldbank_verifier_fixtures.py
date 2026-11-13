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

# indicator code -> recorded full ZIP fixture, per LOCALE of the publisher export channel.
# English fixtures were recorded 2026-11-11; the Spanish ones are the 2026-11-12 f0nix
# recovery probes of the SAME per-indicator exporter under /v2/es/.
ZIP_BY_INDICATOR = {
    "NY.GDP.MKTP.CD": "r4-indicator-csv.zip",
    "SP.POP.TOTL": "csv-sp-pop-totl.zip",
    "SL.UEM.TOTL.ZS": "csv-sl-uem-totl-zs.zip",
}
ZIP_BY_INDICATOR_ES = {
    "NY.GDP.MKTP.KD.ZG": "csv-es-ny-gdp-mktp-kd-zg.zip",
    "SL.UEM.TOTL.ZS": "csv-es-sl-uem-totl-zs.zip",
}
CSV_URL = "https://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv"
CSV_URL_ES = "https://api.worldbank.org/v2/es/indicator/{code}?downloadformat=csv"
_ZIPS_BY_LANGUAGE = {"en": ZIP_BY_INDICATOR, "es": ZIP_BY_INDICATOR_ES}


def _zips(language: str) -> dict[str, str]:
    if language not in _ZIPS_BY_LANGUAGE:
        raise ValueError(f"no recorded worldbank verifier ZIPs for language {language!r}; "
                         f"recorded locales: {sorted(_ZIPS_BY_LANGUAGE)}")
    return _ZIPS_BY_LANGUAGE[language]


def vbody(file: str) -> bytes:
    return (VFIX / file).read_bytes()


def zip_bytes(code: str, language: str = "en") -> bytes:
    return vbody(_zips(language)[code])


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
    """Serves one recorded CSV ZIP per indicator code of ONE export locale (`language='en'` is
    the default, matching the original recorded fixtures; `language='es'` serves the Spanish
    recovery probes). `override` maps an indicator code to replacement bytes (tampering tests);
    `status` maps a code to a non-2xx probe. The served HttpResult carries the FINAL url and the
    ACTUAL status recorded for that fixture in MANIFEST.json — never a composed URL."""

    def __init__(self, override: dict[str, bytes] | None = None,
                 status: dict[str, int] | None = None, language: str = "en"):
        self.override = override or {}
        self.status = status or {}
        self.mapping = _zips(language)
        self.calls: list[str] = []

    def get(self, url, params=None, headers=None, timeout=None):
        for code, file in self.mapping.items():
            if f"/indicator/{code}" in url:
                self.calls.append(code)
                e = _BY_FILE[file]
                return HttpResult(status=int(self.status.get(code, e["status"])),
                                  body=self.override.get(code, vbody(file)), url=e["url"])
        raise AssertionError(f"no recorded worldbank verifier ZIP for {url}")
