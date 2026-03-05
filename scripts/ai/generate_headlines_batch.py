#!/usr/bin/env python3
"""
Batch generate all Painel headlines (all lenses × all languages) for caching.
Usage: python3 generate_headlines_batch.py [--lenses lens1,lens2,...] [--languages pt,cv,fr,es,en]
"""
import sys
import os
import argparse

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.painel import build_painel
from app.services.painel_headline import generate_all_headlines


def main():
    parser = argparse.ArgumentParser(description="Batch generate Painel headlines")
    parser.add_argument("--lenses", help="Comma-separated lens IDs (default: all 10)")
    parser.add_argument("--languages", help="Comma-separated language codes (default: pt,cv,fr,es,en)")
    args = parser.parse_args()

    lenses = args.lenses.split(",") if args.lenses else None
    languages = args.languages.split(",") if args.languages else None

    print("[batch] Building Painel data...", flush=True)
    data = build_painel()
    sections = data.get("sections", [])
    updated = data.get("updated", "")

    if not sections:
        print("[batch] ERROR: No sections in Painel data", flush=True)
        sys.exit(1)

    print(f"[batch] Data date: {updated}, {len(sections)} sections", flush=True)
    print()

    results = generate_all_headlines(sections, updated, lenses=lenses, languages=languages)

    print()
    succeeded = sum(1 for r in results.values() if r.get("headline"))
    failed = sum(1 for r in results.values() if not r.get("headline"))

    print(f"[batch] ✓ Results: {succeeded} succeeded, {failed} failed", flush=True)
    print("[batch] All headlines are now cached. Fast switching between languages!", flush=True)


if __name__ == "__main__":
    main()
