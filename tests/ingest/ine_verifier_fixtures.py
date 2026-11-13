"""Recorded real INE bddXplorer04.jsp pages/selections (tests/ingest/fixtures/ine/verify/,
fetched 2026-11-11 from the live INE bddXplorer with RequestsHttp, Referer header sent;
MANIFEST.json lists every case: series, period, expected observation as cross-checked by hand
against INE's JSON API fixture payloads and Eurostat, provenance and file) and an Http double
that serves them to ingest/verifiers/ine.py.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ingest.http import HttpResult

VFIX = Path(__file__).resolve().parent / "fixtures" / "ine" / "verify"
VMANIFEST: dict = json.loads((VFIX / "MANIFEST.json").read_text())


def vbody(file: str) -> bytes:
    return (VFIX / file).read_bytes()


def selection_key(params: dict) -> tuple[str, tuple]:
    """The routing key of a verifier selection request: ('sel', varcd, period label, per-class
    selected cod_categ tuple). Computed from the request's xmlDocHidden, so it follows any
    change in what the verifier selects."""
    root = ET.fromstring(params["xmlDocHidden"])
    periods = [c.get("label") for c in root.findall(".//CLASS_periodo//Categoria")
               if c.get("selected") == "true"]
    codes = tuple(sorted({c.get("cod_categ")
                          for el in root
                          if el.tag.startswith("CLASS_") and el.tag != "CLASS_periodo"
                          for c in el.iter("Categoria")
                          if c.get("selected") == "true"}))
    return "sel", root.get("indicadorOcorrCod"), tuple(periods), codes


def _tuplify(x):
    return tuple(_tuplify(v) for v in x) if isinstance(x, list) else x


class VerifyFixtureHttp:
    """Serves the recorded verifier-channel bodies. A page GET routes by indicator code; a
    selection GET routes by the exact cut it asks for (period label + pinned codes parsed from
    xmlDocHidden) — an unrecorded cut fails the test. The Referer header is mandatory, like on
    the real server. `override` maps a case name to replacement bytes (tampering tests)."""

    def __init__(self, override: dict[str, bytes] | None = None,
                 alias: dict[tuple, str] | None = None):
        self.override = override or {}
        self.alias = alias or {}  # request key -> a recorded case name (mismatch tests)
        self.calls: list = []

    def get(self, url, params=None, headers=None, timeout=None):
        assert headers and headers.get("Referer") == "https://www.ine.pt/", \
            "verifier must always send the Referer header (the real server 302s without it)"
        params = params or {}
        if "xmlDocHidden" not in params:
            key: tuple = ("page", params.get("indOcorrCod"))
        else:
            key = selection_key(params)
        self.calls.append(key)
        name = next((n for n, entry in VMANIFEST["routes"].items()
                     if _tuplify(entry["route"]) == key), None) or self.alias.get(key)
        if name is None:
            raise AssertionError(f"no recorded verifier response for {key}")
        file = VMANIFEST["routes"][name]["file"]
        return HttpResult(status=200, body=self.override.get(name, vbody(file)),
                          url=VMANIFEST["routes"][name]["url"])
