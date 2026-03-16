#!/usr/bin/env python3
"""
test_all_indicators.py — Test every indicator via /api/series endpoint.
Reports: indicators with 0 data points, missing from API, or errors.
Run inside container or from host with port forwarding.
"""

import json
import sys
import urllib.request
from collections import defaultdict

BASE_URL = "http://127.0.0.1:8080"


def get_catalog():
    """Get all indicators from the explorador catalog."""
    data = json.loads(urllib.request.urlopen(f"{BASE_URL}/api/explorador").read())
    return data


def get_series(source, indicator, from_period="2020-01", to_period="2026-12"):
    """Fetch series data for a source/indicator."""
    url = f"{BASE_URL}/api/series?source={source}&indicator={indicator}&from={from_period}&to={to_period}"
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 70)
    print("Prumo — Indicator Health Check (API-based)")
    print("=" * 70)

    # 1. Get catalog
    catalog = get_catalog()
    print(f"\nCatalog: {len(catalog)} groups")

    # Flatten all indicators from catalog
    all_indicators = []
    items = catalog.get("items", catalog) if isinstance(catalog, dict) else catalog
    for ind in items:
        if isinstance(ind, dict):
            all_indicators.append({
                "source": ind.get("source", ""),
                "indicator": ind.get("indicator", ""),
                "label": ind.get("label", ""),
                "group": ind.get("category", ""),
            })

    print(f"Total indicators in explorador: {len(all_indicators)}")

    # 2. Test each indicator
    results = {"ok": [], "empty": [], "error": [], "few_points": []}

    for i, ind in enumerate(all_indicators):
        src = ind["source"]
        name = ind["indicator"]
        label = ind["label"]

        # Test with 5-year window
        data = get_series(src, name, "2020-01", "2026-12")

        if "error" in data:
            results["error"].append({**ind, "msg": data["error"]})
            status = "ERR"
        elif isinstance(data, list):
            n_points = sum(len(series.get("data", [])) for series in data)
            if n_points == 0:
                results["empty"].append(ind)
                status = "EMPTY"
            elif n_points < 3:
                results["few_points"].append({**ind, "points": n_points})
                status = f"FEW({n_points})"
            else:
                results["ok"].append({**ind, "points": n_points})
                status = f"OK({n_points})"
        elif isinstance(data, dict) and "series" in data:
            n_points = sum(len(s.get("data", [])) for s in data["series"])
            if n_points == 0:
                results["empty"].append(ind)
                status = "EMPTY"
            elif n_points < 3:
                results["few_points"].append({**ind, "points": n_points})
                status = f"FEW({n_points})"
            else:
                results["ok"].append({**ind, "points": n_points})
                status = f"OK({n_points})"
        else:
            # Unknown response format — check if it has data
            data_str = json.dumps(data)
            if '"value"' in data_str or '"data"' in data_str:
                results["ok"].append({**ind, "points": "?"})
                status = "OK(?)"
            else:
                results["empty"].append({**ind, "response": str(data)[:100]})
                status = "EMPTY"

        progress = f"[{i+1}/{len(all_indicators)}]"
        if status.startswith("EMPTY") or status.startswith("ERR") or status.startswith("FEW"):
            print(f"  {progress} ❌ {src}/{name}: {status} — {label}")
        elif (i + 1) % 50 == 0:
            print(f"  {progress} ... ({len(results['ok'])} OK so far)")

    # 3. Report
    print("\n" + "=" * 70)
    print("RESULTS")
    print(f"  OK:         {len(results['ok'])}")
    print(f"  Empty (0):  {len(results['empty'])}")
    print(f"  Few (<3):   {len(results['few_points'])}")
    print(f"  Errors:     {len(results['error'])}")

    if results["empty"]:
        print(f"\n--- EMPTY (no data points in 2020-2026) ---")
        by_source = defaultdict(list)
        for ind in results["empty"]:
            by_source[ind["source"]].append(ind)
        for src in sorted(by_source):
            print(f"\n  {src}:")
            for ind in by_source[src]:
                print(f"    {ind['indicator']}: {ind['label']}")

    if results["few_points"]:
        print(f"\n--- FEW POINTS (<3 in 2020-2026) ---")
        for ind in results["few_points"]:
            print(f"  {ind['source']}/{ind['indicator']}: {ind['points']} pts — {ind['label']}")

    if results["error"]:
        print(f"\n--- ERRORS ---")
        for ind in results["error"]:
            print(f"  {ind['source']}/{ind['indicator']}: {ind['msg'][:80]}")

    # Save full results
    with open("/tmp/indicator_health.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to /tmp/indicator_health.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
