#!/usr/bin/env python3
"""
Generate Painel analysis for all 10 lenses using Claude Haiku.
Costs: ~€0.001 per analysis (vs €0.015 with Opus = 15x cheaper).

Usage: python3 generate_analysis_haiku.py [--lenses pcp,cae,be]
"""
import sys
import os
import json
import time
import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.painel import build_painel
from app.services.ideology_lenses import get_all_lenses

LENSES = list(get_all_lenses().keys())
CAE_DB_PATH = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
_DATA_DIR = os.path.dirname(CAE_DB_PATH)
CACHE_PATH = os.path.join(_DATA_DIR, "painel-analysis-cache.json")

def generate_analysis_with_haiku(sections, updated, lenses=None):
    """Generate analysis using Haiku (15x cheaper than Opus)."""

    lenses = lenses or LENSES
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Load existing cache
    cache = {}
    if os.path.exists(CACHE_PATH):
        try:
            cache = json.loads(open(CACHE_PATH).read())
        except:
            cache = {}

    processed = 0
    skipped = 0

    for lens in lenses:
        processed += 1
        print(f"[{processed}/{len(lenses)}] {lens:12} ...", end=" ", flush=True)

        cache_key = f"painel:v21:{updated}:{lens}"

        # Check if cached
        if cache_key in cache and cache[cache_key].get("text"):
            print("✓ cached")
            skipped += 1
            continue

        try:
            # Get ideology lens
            from app.services.ideology_lenses import get_lens_prompt
            ideology_prompt = get_lens_prompt(lens)

            # Build analysis prompt
            kpi_summary = []
            for section in sections:
                title = section.get("label", "Section")
                for kpi in section.get("kpis", []):
                    value = kpi.get("value")
                    if value is None:
                        continue
                    yoy = kpi.get("yoy")
                    yoy_str = f" (var: {yoy:+.1f}%)" if yoy is not None else ""
                    kpi_summary.append(f"  - {kpi['label']}: {value} {kpi.get('unit', '')}{yoy_str}")

            kpi_block = "\n".join(kpi_summary[:20])  # First 20 KPIs only

            prompt = f"""{ideology_prompt}

---

Painel data ({updated}):
{kpi_block}

Based on this lens, write a 2-3 paragraph analysis of the most important economic trends and what they mean under this ideological perspective. Focus on interconnections and systemic implications. Be direct and factual. Portuguese language."""

            # Call Haiku
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            analysis_text = message.content[0].text.strip()

            # Cache
            cache[cache_key] = {
                "text": analysis_text,
                "lens": lens,
                "period": updated,
                "generated_at": time.time(),
                "model": "haiku",
                "tokens_in": message.usage.input_tokens,
                "tokens_out": message.usage.output_tokens
            }

            cost_usd = (message.usage.input_tokens * 0.00008 + message.usage.output_tokens * 0.0002) / 1000
            print(f"✓ {len(analysis_text):4}c ${cost_usd:.6f}")

            # Save cache every 3 lenses
            if processed % 3 == 0:
                with open(CACHE_PATH, 'w') as f:
                    json.dump(cache, f, indent=2)
                print(f"  [cache saved: {len(cache)} lenses]", flush=True)

        except anthropic.RateLimitError:
            print("⚠ rate limited, waiting 60s...")
            time.sleep(60)
            processed -= 1

        except Exception as e:
            print(f"✗ {str(e)[:40]}")

    # Final save
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)

    print()
    print("=" * 60)
    succeeded = sum(1 for k, v in cache.items() if k.startswith(f"painel:v21:{updated}") and v.get("text"))
    print(f"✓ Cached {succeeded}/{len(lenses)} analyses")
    print(f"✓ Estimated cost per analysis: $0.001 USD (vs Opus: €0.015)")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Painel analysis with Haiku")
    parser.add_argument("--lenses", help="Comma-separated lens IDs (default: all)")
    args = parser.parse_args()

    lenses = args.lenses.split(",") if args.lenses else LENSES

    print("[haiku] Building Painel data...", flush=True)
    data = build_painel()
    sections = data.get("sections", [])
    updated = data.get("updated", "")

    if not sections:
        print("[haiku] ERROR: No sections")
        sys.exit(1)

    print(f"[haiku] Data: {updated}, {len(sections)} sections")
    print(f"[haiku] Generating {len(lenses)} analyses with Haiku")
    print()

    generate_analysis_with_haiku(sections, updated, lenses=lenses)
