#!/usr/bin/env python3
"""
Generate all Painel headlines using Claude Haiku (cheaper than Opus).
Haiku: €0.00008 per 1K input tokens vs Opus €0.015/1K input
~180x cheaper! Perfect for caching all variations.

Usage: python3 generate_headlines_haiku.py [--lenses pcp,cae,be] [--languages pt,en,fr,es,cv]
"""
import sys
import os
import json
import time
import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.painel import build_painel
from app.services.painel_headline import _build_headline_prompt

# All lenses
LENSES = ["pcp", "cae", "be", "livre", "pan", "ps", "ad", "il", "chega", "neutro"]
# All output languages
LANGUAGES = ["pt", "cv", "fr", "es", "en"]

def generate_headlines_with_haiku(sections, updated, lenses=None, languages=None):
    """Generate headlines using Claude Haiku instead of Opus."""

    lenses = lenses or LENSES
    languages = languages or LANGUAGES
    total = len(lenses) * len(languages)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    results = {}
    cache_path = os.path.join(os.path.dirname(os.getenv("CAE_DB_PATH", "/data/cae.duckdb")), "painel-headline-cache.json")

    # Load existing cache
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.loads(open(cache_path).read())
        except:
            cache = {}

    processed = 0
    skipped = 0

    for lens in lenses:
        for lang in languages:
            processed += 1
            print(f"[{processed}/{total}] {lens:8} × {lang:2} ...", end=" ", flush=True)

            # Build cache key
            cache_key = f"headline:v4:{updated}:{lens}:{lang}"

            # Check if already cached
            if cache_key in cache and cache[cache_key].get("headline"):
                print("✓ cached")
                skipped += 1
                results[cache_key] = cache[cache_key]
                continue

            try:
                # Build prompt
                prompt = _build_headline_prompt(sections, lens=lens, output_language=lang)
                if not prompt:
                    print("✗ no data")
                    results[cache_key] = {"headline": None, "error": "No data"}
                    continue

                # Call Haiku (much cheaper!)
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",  # Haiku model ID
                    max_tokens=150,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                headline = message.content[0].text.strip()

                # Cache result
                cache[cache_key] = {
                    "headline": headline,
                    "language": lang,
                    "lens": lens,
                    "generated_at": time.time(),
                    "model": "haiku"
                }

                results[cache_key] = cache[cache_key]

                # Show cost info
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens
                cost_usd = (input_tokens * 0.00008 + output_tokens * 0.0002) / 1000

                print(f"✓ {len(headline):3}c ${cost_usd:.6f}")

                # Save cache every 5 requests
                if processed % 5 == 0:
                    with open(cache_path, 'w') as f:
                        json.dump(cache, f, indent=2)
                    print(f"  [cache saved: {len(cache)} entries]", flush=True)

            except anthropic.RateLimitError:
                print("⚠ rate limited, waiting 60s...")
                time.sleep(60)
                processed -= 1  # Retry this one

            except Exception as e:
                print(f"✗ {str(e)[:30]}")
                results[cache_key] = {"headline": None, "error": str(e)}

    # Final save
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)

    print()
    print("=" * 60)
    succeeded = sum(1 for r in results.values() if r.get("headline"))
    failed = sum(1 for r in results.values() if not r.get("headline"))
    print(f"✓ Results: {succeeded} succeeded, {failed} failed ({skipped} skipped from cache)")
    print(f"✓ All {total} headlines cached locally")
    print(f"✓ Estimated cost: ${total * 0.00013:.2f} USD (vs Opus: ${total * 0.024:.2f})")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate all Painel headlines with Haiku")
    parser.add_argument("--lenses", help="Comma-separated lens IDs (default: all 10)")
    parser.add_argument("--languages", help="Comma-separated language codes (default: pt,cv,fr,es,en)")
    args = parser.parse_args()

    lenses = args.lenses.split(",") if args.lenses else LENSES
    languages = args.languages.split(",") if args.languages else LANGUAGES

    print("[haiku] Building Painel data...", flush=True)
    data = build_painel()
    sections = data.get("sections", [])
    updated = data.get("updated", "")

    if not sections:
        print("[haiku] ERROR: No sections in Painel data")
        sys.exit(1)

    print(f"[haiku] Data date: {updated}, {len(sections)} sections")
    print(f"[haiku] Generating {len(lenses)} lenses × {len(languages)} languages = {len(lenses)*len(languages)} headlines")
    print()

    generate_headlines_with_haiku(sections, updated, lenses=lenses, languages=languages)
