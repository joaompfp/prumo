"""Independently audit the World Bank production evidence offline, without ingest imports.

Input: controller-created JSON capsule from worldbank-live-export.py, or its gzip form.
All stored rows are checked against original JSON tokens; independent CSV checks cover
only the actual stored sample. Neither operation proves unsampled CSV agreement.
This auditor deliberately pins the counts of this acceptance receipt, not future data.
"""
import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit


def forbid_network(event, args):
    if event.startswith("socket."):
        raise RuntimeError("network forbidden during evidence replay")


class Number(str):
    """Keep genuine JSON number primitives distinct from strings and preserve tokens."""


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        assert key not in obj, f"duplicate JSON key: {key}"
        obj[key] = value
    return obj


def audit(path):
    sys.addaudithook(forbid_network)
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    capsule = json.loads(data, object_pairs_hook=unique_object)
    assert capsule["schema"] == "prumo-worldbank-production-evidence"
    assert capsule["version"] == 1 and capsule["task_18_closed"] is False
    active = {s["id"]: s for s in capsule["series"] if s["active"]}
    assert len(active) == 930
    runs = {r["id"]: r for r in capsule["runs"]}
    assert len(runs) == 18
    assert all(r["state"] == "verified" and r["input_origin"] == "live" for r in runs.values())
    blobs = {}
    for sha, encoded in capsule["blobs_base64"].items():
        body = base64.b64decode(encoded, validate=True)
        assert hashlib.sha256(body).hexdigest() == sha
        blobs[sha] = body
    receipts = {r["id"]: r for r in capsule["raw_receipts"]}
    assert len(receipts) == len(capsule["raw_receipts"]) == 18, "expected 18 collector receipts"
    raw_values = {}
    null_cells = 0
    other_non_numeric = 0
    native_to_id = {s["native_code"]: sid for sid, s in active.items()}
    assert len(native_to_id) == len(active)
    for receipt in receipts.values():
        assert receipt["http_status"] == 200 and receipt["ok"] == 1
        body = blobs[receipt["sha256"]]
        assert len(body) == receipt["bytes"]
        run = runs[receipt["dataset_run_id"]]
        assert (datetime.fromisoformat(run["started_at"]) <=
                datetime.fromisoformat(receipt["fetched_at"]) <=
                datetime.fromisoformat(run["finished_at"]))
        meta, rows = json.loads(body, parse_int=Number, parse_float=Number,
                               object_pairs_hook=unique_object)
        assert int(meta["pages"]) == 1 and int(meta["total"]) == len(rows)
        for row in rows:
            native = row["indicator"]["id"] + ":" + row["countryiso3code"]
            sid = native_to_id[native]
            assert row["country"]["id"] == active[sid]["geography"]
            assert row["unit"] == "" and row["obs_status"] == ""
            token = row["value"]
            if token is None:
                null_cells += 1
                continue
            assert type(token) is Number
            if not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", token):
                other_non_numeric += 1
                continue
            key = (run["id"], sid, row["date"])
            assert key not in raw_values
            raw_values[key] = (str(token), receipt["id"])
    observed = {}
    latest = {}
    for o in capsule["observations"]:
        key = (o["dataset_run_id"], o["series_id"], o["period"])
        assert key not in observed
        observed[key] = o
        assert o["kind"] == "fetched" and o["status_flag"] == "normal"
        assert raw_values[key] == (o["value_text"], o["raw_fetch_id"])
        assert o["fetched_at"] == receipts[o["raw_fetch_id"]]["fetched_at"]
        sid = o["series_id"]
        latest[sid] = max(latest.get(sid, ""), o["period"])
    assert set(raw_values) == set(observed)
    assert set(latest) == set(active)
    assert len(observed) == 45915
    assert null_cells == 15465 and other_non_numeric == 0, "unexpected publisher cell counts"
    assert len(capsule["verification_items"]) == 949, "expected 949 verification items"
    sample_keys = set()
    tables = {}
    sample_latest = set()
    per_run = defaultdict(list)
    for item in capsule["verification_items"]:
        assert item["passed"] == 1 and item["match"] == 1
        sid, period = item["series_id"], item["period"]
        assert item["observed_series_id"] == sid and item["observed_period"] == period
        assert item["expected_decimal"] == item["observed_decimal"] == "."
        assert item["expected_unit"] == active[sid]["unit"]
        assert item["expected_flag"] == "normal"
        assert item["observed_unit"] is None and item["observed_flag"] is None
        key = (item["dataset_run_id"], sid, period)
        assert key not in sample_keys, f"duplicate sample identity: {key}"
        sample_keys.add(key)
        assert observed[key]["value_text"] == item["expected_text"]
        code, iso3 = active[sid]["native_code"].split(":")
        sha = item["evidence_sha256"]
        if sha not in tables:
            envelope = json.loads(blobs[sha], object_pairs_hook=unique_object)
            assert envelope["schema"] == "worldbank-csv-evidence" and envelope["version"] == 1
            assert len(envelope["responses"]) == 1
            response = envelope["responses"][0]
            assert response["status"] == 200 and response["url"] == item["evidence_url"]
            language = "es" if code in {"NY.GDP.MKTP.KD.ZG", "SL.UEM.TOTL.ZS"} else "en"
            url = urlsplit(response["url"])
            assert url.hostname == "api.worldbank.org"
            assert url.path == f"/v2/{language}/indicator/{code}"
            assert url.query == "downloadformat=csv"
            payload = base64.b64decode(response["body_base64"], validate=True)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                names = archive.namelist()
                assert len(names) == 3 and all("/" not in n and ".." not in n for n in names)
                main = [n for n in names if n.startswith(f"API_{code}_DS2_{language}_csv_v2_")]
                assert len(main) == 1
                parsed = list(csv.reader(io.StringIO(archive.read(main[0]).decode("utf-8-sig")), strict=True))
            title = "Indicadores del desarrollo mundial" if language == "es" else "World Development Indicators"
            assert parsed[0] == ["Data Source", title, ""]
            header = parsed[4]
            assert header[:4] == ["Country Name", "Country Code", "Indicator Name", "Indicator Code"]
            table = {}
            for row in parsed[5:]:
                assert len(row) == len(header) and row[3] == code
                assert row[1] not in table
                table[row[1]] = dict(zip(header[4:-1], row[4:-1], strict=True))
            tables[sha] = table
        cell = tables[sha][iso3][period]
        assert cell == item["observed_text"]
        assert Decimal(cell) == Decimal(item["expected_text"])
        per_run[item["dataset_run_id"]].append(item)
        if period == latest[sid]:
            sample_latest.add(sid)
    assert len(tables) == 18, "expected 18 independent CSV evidence/table envelopes"
    assert sample_latest == set(active)
    assert set(per_run) == set(runs)
    for items in per_run.values():
        assert all(i["sample_size"] == len(items) for i in items)
        assert len({i["seed"] for i in items}) == 1
    failed = {r["id"]: r["state"] for r in capsule["historical_failures"]}
    return {
        "exported_at": capsule["exported_at"], "successful_live_groups": len(runs),
        "active_series": len(active), "raw_json_receipts": len(receipts),
        "stored_rows_exact_against_original_json": len(observed),
        "publisher_null_cells": null_cells, "other_non_numeric_cells": other_non_numeric,
        "independent_exact_csv_samples": len(capsule["verification_items"]),
        "latest_series_samples_covered": len(sample_latest), "csv_evidence_envelopes": len(tables),
        "historical_failed_runs": dict(Counter(failed.values())),
        "collector_receipt_min": min(r["fetched_at"] for r in receipts.values()),
        "collector_receipt_max": max(r["fetched_at"] for r in receipts.values()),
        "last_processing_finished_at": max(r["finished_at"] for r in runs.values()),
        "network": "forbidden", "task_13_live_gate": "passed in deployed per-indicator flow",
        "task_18_closed": False,
        "limitation": "Independent CSV verification is sampled, not every stored row.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capsule", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.capsule), sort_keys=True, indent=2))
