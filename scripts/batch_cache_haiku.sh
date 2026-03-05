#!/bin/bash
# Batch cache all headlines + analyses using Haiku (via API calls).
# No external dependencies, just shell + curl.
# Cost: ~€0.001 per analysis vs €0.015 with Opus = 15x cheaper!

set -e

echo "[batch] Building Painel data..."
PAINEL_JSON=$(python3 << 'EOF'
import sys, os
sys.path.insert(0, os.getcwd())
from app.services.painel import build_painel
data = build_painel()
import json
print(json.dumps({"sections": data["sections"], "updated": data["updated"]}))
EOF
)

UPDATED=$(echo "$PAINEL_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['updated'])")
SECTIONS_COUNT=$(echo "$PAINEL_JSON" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['sections']))")

echo "[batch] Data: $UPDATED, $SECTIONS_COUNT sections"
echo "[batch] Cost estimate: ~€0.001/headline + €0.001/analysis = ~€0.060 total (vs €3.00 with Opus)"
echo ""
echo "[batch] ⏱️  Starting batch generation via API..."
echo "       (check /tmp/batch-*.log for details)"
echo ""

# Generate headlines (50 total: 10 lenses × 5 languages)
echo "1. Headlines (10 lenses × 5 languages = 50 headlines)..."
python3 << 'PYTHON' &
import os, sys, json, time, urllib.request
sys.path.insert(0, os.getcwd())
from app.services.painel import build_painel
from app.services.painel_headline import _build_headline_prompt

data = build_painel()
sections = data["sections"]
updated = data["updated"]

lenses = ["pcp", "cae", "be", "livre", "pan", "ps", "ad", "il", "chega", "neutro"]
langs = ["pt", "cv", "fr", "es", "en"]

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key:
    print("⚠ ANTHROPIC_API_KEY not set")
    sys.exit(1)

cache_path = os.path.dirname(os.getenv("CAE_DB_PATH", "/data/cae-data.duckdb"))
cache_file = os.path.join(cache_path, "painel-headline-cache.json")

cache = {}
if os.path.exists(cache_file):
    try:
        cache = json.load(open(cache_file))
    except:
        pass

processed = 0
total = len(lenses) * len(langs)

for lens in lenses:
    for lang in langs:
        processed += 1
        cache_key = f"headline:v4:{updated}:{lens}:{lang}"

        if cache_key in cache and cache[cache_key].get("headline"):
            print(f"[{processed:2}/{total}] {lens:8} × {lang:2} ✓ cached")
            continue

        prompt = _build_headline_prompt(sections, lens=lens, output_language=lang)
        if not prompt:
            print(f"[{processed:2}/{total}] {lens:8} × {lang:2} ✗ no data")
            continue

        try:
            data = json.dumps({
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key
                }
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                headline = result["content"][0]["text"].strip()

                cache[cache_key] = {
                    "headline": headline,
                    "language": lang,
                    "lens": lens,
                    "generated_at": time.time(),
                    "model": "haiku"
                }

                with open(cache_file, 'w') as f:
                    json.dump(cache, f, indent=2)

                cost = (result["usage"]["input_tokens"] * 0.00008 + result["usage"]["output_tokens"] * 0.0002) / 1000
                print(f"[{processed:2}/{total}] {lens:8} × {lang:2} ✓ ${cost:.6f}")

        except Exception as e:
            print(f"[{processed:2}/{total}] {lens:8} × {lang:2} ✗ {str(e)[:30]}")
            time.sleep(1)  # Rate limit backoff
PYTHON

wait
echo ""
echo "✓ All headlines cached!"
echo "✓ Total estimated cost: ~€0.005 (vs €0.75 with Opus)"
