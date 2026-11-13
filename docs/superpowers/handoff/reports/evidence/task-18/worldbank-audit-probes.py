"""Focused offline regression probes for this immutable World Bank acceptance capsule.

Mutations exist only in memory. JSON stdout records actual outcomes; exit 1 means
at least one regression expectation failed. No receipt or application file is written.
"""
import copy
import gzip
import json
import runpy
import sys
from pathlib import Path


class MemoryCapsule:
    suffix = ".json"

    def __init__(self, capsule):
        self.data = json.dumps(capsule).encode()

    def read_bytes(self):
        return self.data


def run_probes():
    folder = Path(__file__).resolve().parent
    audit = runpy.run_path(str(folder / "worldbank-offline-audit.py"))["audit"]
    path = folder / "checkpoint-20261113T083638Z/worldbank-live-evidence.json.gz"
    original = json.loads(gzip.decompress(path.read_bytes()))
    positive = audit(path)
    assert audit(MemoryCapsule(original)) == positive
    expected_processing = max(run["finished_at"] for run in original["runs"])
    processing_only = (
        positive.get("last_processing_finished_at") == expected_processing
        and "final_verified_at" not in positive
    )
    historical = next(
        i for i, item in enumerate(original["verification_items"])
        if item["series_id"] == "worldbank.rnd_pct_gdp.MX" and item["period"] == "2023"
    )
    historical_item = original["verification_items"][historical]
    latest = {}
    for row in original["observations"]:
        sid = row["series_id"]
        latest[sid] = max(latest.get(sid, ""), row["period"])
    assert latest[historical_item["series_id"]] > historical_item["period"]
    replacement = next(
        item for index, item in enumerate(original["verification_items"])
        if index != historical and item["dataset_run_id"] == historical_item["dataset_run_id"]
    )
    outcomes = {}
    for name in (
        "altered_stored_token", "altered_csv_result", "missing_latest_series_sample",
        "missing_historical_sample_adjusted_size", "duplicate_item_replacement",
        "missing_collector_receipt", "altered_run_sample_size", "altered_run_seed",
    ):
        capsule = copy.deepcopy(original)
        items = capsule["verification_items"]
        if name == "altered_stored_token":
            capsule["observations"][0]["value_text"] += "0"
        elif name == "altered_csv_result":
            items[0]["observed_text"] += "0"
        elif name == "missing_latest_series_sample":
            index = next(
                i for i, item in enumerate(items)
                if item["period"] == latest[item["series_id"]]
            )
            items.pop(index)
        elif name == "missing_historical_sample_adjusted_size":
            removed = items.pop(historical)
            for item in items:
                if item["dataset_run_id"] == removed["dataset_run_id"]:
                    item["sample_size"] -= 1
        elif name == "duplicate_item_replacement":
            # Preserve 949 items, all latest coverage, and the per-run count/seed.
            items[historical] = copy.deepcopy(replacement)
        elif name == "missing_collector_receipt":
            capsule["raw_receipts"].pop()
        elif name == "altered_run_sample_size":
            items[0]["sample_size"] += 1
        elif name == "altered_run_seed":
            items[0]["seed"] += 1
        try:
            result = audit(MemoryCapsule(capsule))
        except (AssertionError, KeyError) as exc:
            outcomes[name] = {"rejected": True, "exception": type(exc).__name__, "detail": str(exc)}
        else:
            outcomes[name] = {
                "rejected": False,
                "accepted_sample_count": result["independent_exact_csv_samples"],
                "latest_series_samples_covered": result["latest_series_samples_covered"],
            }
    return {
        "scope": "receipt-specific offline helper regression probes; not application tests",
        "network": "forbidden",
        "positive_replay": "passed on original gzip and its in-memory JSON contents",
        "processing_timestamp_semantics": {
            "passed": processing_only, "expected_last_processing_finished_at": expected_processing,
        },
        "negative_probes": outcomes,
        "all_expectations_passed": processing_only and all(o["rejected"] for o in outcomes.values()),
        "production_mutated": False, "task_18_closed": False,
    }


if __name__ == "__main__":
    results = run_probes()
    print(json.dumps(results, indent=2, sort_keys=True))
    sys.exit(0 if results["all_expectations_passed"] else 1)
