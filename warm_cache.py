#!/usr/bin/env python3
"""
Prumo — Pre-warm the server-side interpret cache for all indicators × lenses × languages.

Calls /api/interpret directly (no browser needed). The backend caches each result
for 30 days. Uses the same 5-year window and quarter quantization as the frontend,
so real users get instant AI responses.

Usage:
    python warm_cache.py [--workers N] [--dry-run] [--resume]

Progress: tail -f /tmp/prumo-warm-cache.log
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

# ── Config ───────────────────────────────────────────────────────
INTERNAL_API = "http://172.20.0.6:8080"
LOG_FILE = "/tmp/prumo-warm-cache.log"
PROGRESS_FILE = "/tmp/prumo-warm-cache-progress.json"

# Match frontend default: 5-year window
_now = datetime.now()
DEFAULT_FROM = f"{_now.year - 5}-{_now.month:02d}"
DEFAULT_TO = f"{_now.year}-{_now.month:02d}"

# Skip 'custom' lens (user-specific ideology text, can't pre-cache)
# kriolu lens removed from site.json for now
LENSES = ["cae", "pcp", "be", "livre", "pan", "ps", "ad", "il", "chega", "neutro"]
LANGUAGES = ["pt", "cv", "fr", "es", "en"]

_log_lock = Lock()


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with _log_lock:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
        print(line, flush=True)


def fetch_indicators():
    """Get all indicators from the catalog API."""
    resp = urllib.request.urlopen(f"{INTERNAL_API}/api/catalog", timeout=30)
    catalog = json.loads(resp.read())
    indicators = []
    for src, src_info in catalog.items():
        for ind_id, ind_info in src_info.get("indicators", {}).items():
            indicators.append({
                "source": src,
                "indicator": ind_id,
                "label": ind_info.get("label", ind_id),
            })
    return indicators


def fetch_series(source, indicator):
    """Fetch series data for a single indicator."""
    url = (f"{INTERNAL_API}/api/series"
           f"?source={urllib.parse.quote(source)}"
           f"&indicator={urllib.parse.quote(indicator)}"
           f"&from={DEFAULT_FROM}&to={DEFAULT_TO}")
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        data = json.loads(resp.read())
        return data if data else None
    except Exception:
        return None


def warm_one(series_data, lens, lang, label=""):
    """Call /api/interpret via HTTP. Runs through uvicorn (needed for OAuth proxy)."""
    payload = json.dumps({
        "series": series_data,
        "from": DEFAULT_FROM,
        "to": DEFAULT_TO,
        "lang": "pt",
        "context": "economia portuguesa",
        "lens": lens,
        "custom_ideology": None,
        "output_language": lang,
    }).encode()

    req = urllib.request.Request(
        f"{INTERNAL_API}/api/interpret",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=180)
        result = json.loads(resp.read())
        has_text = bool(result.get("text"))
        return has_text
    except Exception as e:
        return f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser(description="Pre-warm Prumo interpret cache")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (default 1 — Prumo runs 1 uvicorn worker)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Just count combinations, don't call API")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-completed combos from progress file")
    parser.add_argument("--lenses", nargs="*", default=None,
                        help="Only warm these lenses (default: all)")
    parser.add_argument("--languages", nargs="*", default=None,
                        help="Only warm these languages (default: all)")
    args = parser.parse_args()

    lenses = args.lenses or LENSES
    languages = args.languages or LANGUAGES

    log("=" * 60)
    log("PRUMO CACHE WARM — STARTING")
    log(f"Period: {DEFAULT_FROM} → {DEFAULT_TO}")
    log(f"Lenses: {lenses}")
    log(f"Languages: {languages}")
    log(f"Workers: {args.workers}")
    log("=" * 60)

    # Fetch indicators
    indicators = fetch_indicators()
    log(f"Loaded {len(indicators)} indicators from catalog")

    total = len(indicators) * len(lenses) * len(languages)
    log(f"Total combinations: {len(indicators)} indicators × {len(lenses)} lenses × {len(languages)} langs = {total}")

    if args.dry_run:
        log("DRY RUN — exiting")
        return

    # Load resume state
    done_keys = set()
    if args.resume and Path(PROGRESS_FILE).exists():
        done_keys = set(json.loads(Path(PROGRESS_FILE).read_text()))
        log(f"Resuming: {len(done_keys)} already completed")

    # Pre-fetch all series data (fast, no LLM cost)
    log("Fetching series data for all indicators...")
    series_cache = {}
    for i, ind in enumerate(indicators):
        key = f"{ind['source']}/{ind['indicator']}"
        data = fetch_series(ind["source"], ind["indicator"])
        if data:
            series_cache[key] = data
        if (i + 1) % 50 == 0:
            log(f"  Fetched {i+1}/{len(indicators)} series")
    log(f"Series data ready: {len(series_cache)}/{len(indicators)} have data")

    # Build work queue
    work = []
    for ind in indicators:
        ind_key = f"{ind['source']}/{ind['indicator']}"
        if ind_key not in series_cache:
            continue
        for lens in lenses:
            for lang in languages:
                combo_key = f"{ind_key}|{lens}|{lang}"
                if combo_key not in done_keys:
                    work.append((ind_key, ind["label"], lens, lang, combo_key))

    log(f"Work queue: {len(work)} combos to warm (skipped {total - len(work)})")

    ok = fail = skip = 0
    start_time = time.time()

    def process(item):
        ind_key, label, lens, lang, combo_key = item
        result = warm_one(series_cache[ind_key], lens, lang, label)
        return combo_key, ind_key, lens, lang, result

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process, item): item for item in work}
        for i, future in enumerate(as_completed(futures)):
            combo_key, ind_key, lens, lang, result = future.result()
            done_keys.add(combo_key)

            if result is True:
                ok += 1
                status = "OK"
            elif result is False:
                skip += 1
                status = "EMPTY"
            else:
                fail += 1
                status = str(result)

            completed = ok + fail + skip
            if completed % 25 == 0 or status != "OK":
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(work) - completed) / rate if rate > 0 else 0
                log(f"[{completed}/{len(work)}] {status}: {ind_key} lens={lens} lang={lang}"
                    f" | {rate:.1f}/s ETA {eta/60:.0f}min | OK={ok} FAIL={fail} EMPTY={skip}")

            # Save progress every 50
            if completed % 50 == 0:
                Path(PROGRESS_FILE).write_text(json.dumps(list(done_keys)))

    # Final save
    Path(PROGRESS_FILE).write_text(json.dumps(list(done_keys)))

    elapsed = time.time() - start_time
    log("=" * 60)
    log(f"CACHE WARM COMPLETE in {elapsed/60:.1f} min")
    log(f"OK={ok} EMPTY={skip} FAIL={fail} Total={ok+fail+skip}")
    log("=" * 60)


if __name__ == "__main__":
    main()
