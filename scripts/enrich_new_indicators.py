#!/usr/bin/env python3
"""
enrich_new_indicators.py — AI auto-labeling for new indicators.

When ingest.py detects new indicator IDs (not yet in the catalog),
this script generates labels, descriptions, section suggestions, and
sentiment rules via Claude Haiku.

Output is written to data/enrichment-queue.json for human review.
Nothing is auto-committed to the catalog.

Usage:
  python scripts/enrich_new_indicators.py                  # detect + enrich
  python scripts/enrich_new_indicators.py --review         # show pending queue
  python scripts/enrich_new_indicators.py --approve <id>   # approve an entry
  python scripts/enrich_new_indicators.py --dry-run        # detect only, no API
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

DEFAULT_DB = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
QUEUE_PATH = os.environ.get("ENRICHMENT_QUEUE",
                             os.path.join(os.path.dirname(DEFAULT_DB), "enrichment-queue.json"))
ANTHROPIC_KEY = os.environ.get("CAE_ANTHROPIC_TOKEN", "")


def get_known_indicators() -> set:
    """Get indicator IDs already in the catalog (app/constants/catalog.py)."""
    try:
        from app.constants import CATALOG
        known = set()
        for src, src_info in CATALOG.items():
            for ind in src_info.get("indicators", {}):
                known.add((src, ind))
        return known
    except Exception as e:
        print(f"  ⚠ could not load catalog: {e}", file=sys.stderr)
        return set()


def get_db_indicators(db_path: str) -> set:
    """Get all (source, indicator) pairs present in the DB."""
    import duckdb
    conn = duckdb.connect(db_path, read_only=True)
    try:
        rows = conn.execute(
            "SELECT DISTINCT source, indicator FROM indicators"
        ).fetchall()
        return {(r[0], r[1]) for r in rows}
    finally:
        conn.close()


def detect_new_indicators(db_path: str) -> list:
    """Find indicators in DB that are not in the catalog."""
    known = get_known_indicators()
    in_db = get_db_indicators(db_path)
    new = sorted(in_db - known)
    return [{"source": src, "indicator": ind} for src, ind in new]


def enrich_indicator(source: str, indicator: str) -> dict:
    """Call Claude Haiku to generate labels and metadata for a new indicator."""
    if not ANTHROPIC_KEY:
        return {"error": "API key not configured"}

    import urllib.request

    prompt = (
        f"You are labeling a new economic indicator for a Portuguese economic dashboard.\n\n"
        f"Source: {source}\n"
        f"Indicator ID: {indicator}\n\n"
        f"Based on the source and ID, generate:\n"
        f'1. "label_pt": Short Portuguese label (max 40 chars)\n'
        f'2. "label_en": Short English label (max 40 chars)\n'
        f'3. "description": One-sentence Portuguese description\n'
        f'4. "section_suggestion": Which Painel section it belongs to '
        f'(one of: custo_vida, industria, emprego, conjuntura, energia, externo, competitividade)\n'
        f'5. "sentiment_rule": "higher_is_better", "lower_is_better", or "neutral"\n'
        f'6. "unit_guess": Likely unit (%, €, index, etc.)\n\n'
        f'Return ONLY valid JSON with these 6 keys.'
    )

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = "".join(
                b["text"] for b in data.get("content", []) if b.get("type") == "text"
            ).strip()

        # Parse the JSON response
        # Handle markdown code blocks if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        result["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result["model"] = "claude-haiku-4-5-20251001"
        return result
    except Exception as e:
        return {"error": str(e)}


def load_queue() -> dict:
    """Load the enrichment queue from disk."""
    try:
        if os.path.exists(QUEUE_PATH):
            return json.loads(open(QUEUE_PATH, encoding="utf-8").read())
    except Exception:
        pass
    return {"pending": [], "approved": [], "rejected": []}


def save_queue(queue: dict):
    """Save the enrichment queue to disk."""
    open(QUEUE_PATH, "w", encoding="utf-8").write(
        json.dumps(queue, ensure_ascii=False, indent=2)
    )


def show_review(queue: dict):
    """Display pending enrichment entries for review."""
    pending = queue.get("pending", [])
    if not pending:
        print("No pending enrichments.")
        return

    print(f"\n{len(pending)} pending enrichment(s):\n")
    for i, entry in enumerate(pending):
        print(f"  [{i}] {entry['source']}/{entry['indicator']}")
        enrich = entry.get("enrichment", {})
        if enrich.get("error"):
            print(f"      ✗ Error: {enrich['error']}")
        else:
            print(f"      PT: {enrich.get('label_pt', '?')}")
            print(f"      EN: {enrich.get('label_en', '?')}")
            print(f"      Section: {enrich.get('section_suggestion', '?')}")
            print(f"      Sentiment: {enrich.get('sentiment_rule', '?')}")
            print(f"      Unit: {enrich.get('unit_guess', '?')}")
        print()


def main():
    parser = argparse.ArgumentParser(description="AI enrichment for new indicators")
    parser.add_argument("--db", default=DEFAULT_DB, help="DuckDB path")
    parser.add_argument("--review", action="store_true", help="Show pending queue")
    parser.add_argument("--approve", type=int, help="Approve entry by index")
    parser.add_argument("--reject", type=int, help="Reject entry by index")
    parser.add_argument("--dry-run", action="store_true", help="Detect only, no API")
    args = parser.parse_args()

    queue = load_queue()

    if args.review:
        show_review(queue)
        return

    if args.approve is not None:
        pending = queue.get("pending", [])
        if 0 <= args.approve < len(pending):
            entry = pending.pop(args.approve)
            queue.setdefault("approved", []).append(entry)
            save_queue(queue)
            print(f"✓ Approved: {entry['source']}/{entry['indicator']}")
        else:
            print(f"Invalid index: {args.approve}")
        return

    if args.reject is not None:
        pending = queue.get("pending", [])
        if 0 <= args.reject < len(pending):
            entry = pending.pop(args.reject)
            queue.setdefault("rejected", []).append(entry)
            save_queue(queue)
            print(f"✗ Rejected: {entry['source']}/{entry['indicator']}")
        else:
            print(f"Invalid index: {args.reject}")
        return

    # Detect new indicators
    new_indicators = detect_new_indicators(args.db)
    if not new_indicators:
        print("[enrich] no new indicators detected")
        return

    # Filter out already-queued indicators
    already_queued = {
        (e["source"], e["indicator"])
        for e in queue.get("pending", []) + queue.get("approved", [])
    }
    to_enrich = [
        ind for ind in new_indicators
        if (ind["source"], ind["indicator"]) not in already_queued
    ]

    if not to_enrich:
        print(f"[enrich] {len(new_indicators)} new indicator(s) found, "
              f"all already in queue")
        return

    print(f"[enrich] {len(to_enrich)} new indicator(s) to enrich")

    if args.dry_run:
        for ind in to_enrich:
            print(f"  would enrich: {ind['source']}/{ind['indicator']}")
        return

    # Enrich each new indicator
    for ind in to_enrich:
        src, name = ind["source"], ind["indicator"]
        print(f"  ▶ enriching {src}/{name}...", end=" ", flush=True)
        enrichment = enrich_indicator(src, name)

        entry = {
            "source": src,
            "indicator": name,
            "enrichment": enrichment,
            "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        queue.setdefault("pending", []).append(entry)

        if enrichment.get("error"):
            print(f"✗ {enrichment['error']}")
        else:
            print(f"✓ {enrichment.get('label_pt', '?')}")

        time.sleep(0.5)  # Rate limiting

    save_queue(queue)
    print(f"\n[enrich] {len(to_enrich)} entries added to {QUEUE_PATH}")
    print(f"         Review with: python {__file__} --review")


if __name__ == "__main__":
    main()
