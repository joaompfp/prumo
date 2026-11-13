"""Registry <-> E-REDES publisher metadata pairing (same pattern as test_registry_ren_units.py).

Unit/field/licence evidence is the genuine dataset metadata body archived at
tests/ingest/fixtures/eredes/metadata.body (HTTP 200, fetched 2026-11-12, sha256-pinned by
MANIFEST.json): fields dgm/pre/total are type double with labels 'Market (kWh)',
'Special Regime (kWh)', 'Total (kWh)'; datahora is the datetime key; default metas license is
'CC BY 4.0' with https://creativecommons.org/licenses/by/4.0/ and publisher 'E-REDES'. The CSV
export header (window_csv fixture) re-confirms the field names on the independent channel.
EREDES_PUBLISHER_UNIT and the label/licence assertions below are read from that evidence, not
echoed from the registry.
"""
import csv
import hashlib
import io
import json
from pathlib import Path

from ingest.registry import load_registry

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
FIX = Path(__file__).resolve().parent / "fixtures" / "eredes"
MANIFEST = json.loads((FIX / "MANIFEST.json").read_text())

# native_code -> unit read from the publisher metadata labels on 2026-11-12 (fixture above).
EREDES_PUBLISHER_UNIT = {
    "energia-produzida-total-nacional:dgm": "kWh",
    "energia-produzida-total-nacional:pre": "kWh",
    "energia-produzida-total-nacional:total": "kWh",
}

EXPECTED_LABELS = {"dgm": "Market (kWh)", "pre": "Special Regime (kWh)", "total": "Total (kWh)"}
EXPECTED_CSV_HEADER = ["datahora", "dia", "mes", "ano", "date", "time", "dgm", "pre", "total"]


def _metadata() -> dict:
    body = (FIX / MANIFEST["sets"]["metadata"]["file"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == MANIFEST["sets"]["metadata"]["sha256"]
    return json.loads(body)


def _eredes_specs():
    return [s for s in load_registry(REGISTRY) if s.source.name == "eredes"]


def test_eredes_registry_block_matches_publisher_metadata():
    doc = _metadata()
    assert doc["dataset_id"] == "energia-produzida-total-nacional"
    default = doc["metas"]["default"]
    assert default["license"] == "CC BY 4.0"
    assert default["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert default["publisher"] == "E-REDES"
    fields = {f["name"]: f for f in doc["fields"]}
    assert fields["datahora"]["type"] == "datetime"  # native 15-min timestamp field
    for name, label in EXPECTED_LABELS.items():
        assert fields[name]["type"] == "double" and fields[name]["label"] == label
    src = _eredes_specs()[0].source
    assert (src.licence, src.licence_url) == ("CC BY 4.0", default["license_url"])
    assert src.redistribution_ok is True and src.verifiable is True


def test_every_active_eredes_series_is_native_pt15m_with_matching_unit():
    active = [s for s in _eredes_specs() if s.active]
    assert len(active) == 3
    for s in active:
        assert s.frequency == "PT15M" and s.theme == "energy" and s.geography == "PT"
        assert s.role == "primary" and s.decimal == "." and s.schedule == "1d"
        assert EREDES_PUBLISHER_UNIT.get(s.native_code) == s.unit == "kWh"
        dataset, _, field = s.native_code.partition(":")
        assert dataset == "energia-produzida-total-nacional" and field in EXPECTED_LABELS
        assert s.throttle_rps <= 1.0  # <= 1 request/s on the portal


def test_table_has_no_stale_entries():
    used = {s.native_code for s in _eredes_specs() if s.active}
    assert used == set(EREDES_PUBLISHER_UNIT)


def test_csv_verifier_channel_exposes_exactly_the_native_fields():
    body = (FIX / MANIFEST["sets"]["window_csv"]["file"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == MANIFEST["sets"]["window_csv"]["sha256"]
    rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig")), delimiter=";"))
    assert rows[0] == EXPECTED_CSV_HEADER
    assert len(rows) - 1 == 96  # full UTC day of quarter-hour records, no truncation
    assert rows[1][0] == "2026-11-10T00:00:00+00:00"
    assert rows[-1][0] == "2026-11-10T23:45:00+00:00"


def test_fixture_manifest_hashes_pin_every_body():
    for name, m in MANIFEST["sets"].items():
        assert MANIFEST["sets"][name]["status"] == 200
        assert hashlib.sha256((FIX / m["file"]).read_bytes()).hexdigest() == m["sha256"]
