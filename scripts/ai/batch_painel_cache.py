#!/usr/bin/env python3
"""Batch-generate Painel IA analysis cache for all lens x language combos.

Usage (from host):
    docker exec prumo python3 scripts/ai/batch_painel_cache.py [--force]

Generates 20 entries: 10 lenses x 2 languages (pt, en).
Handles 429 rate limits with exponential backoff.
"""
import sys
import time
import urllib.request
import json

BASE = "http://127.0.0.1:8080"
LENSES = ["cae", "pcp", "be", "ps", "ad", "il", "livre", "pan", "chega", "neutro"]
LANGUAGES = ["pt", "en"]
FORCE = "--force" in sys.argv

def generate(lens: str, lang: str, attempt: int = 0) -> dict:
    """Call /api/painel-analysis with retry on 429 (HTTP or embedded in JSON error)."""
    params = f"lens={lens}&output_language={lang}"
    if FORCE:
        params += "&force=1"
    url = f"{BASE}/api/painel-analysis?{params}"

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if e.code == 429 and attempt < 10:
            wait = min(60 * (2 ** attempt), 600)
            print(f"  HTTP 429, waiting {wait}s (attempt {attempt+1})...", flush=True)
            time.sleep(wait)
            return generate(lens, lang, attempt + 1)
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}

    # Prumo returns HTTP 200 but embeds rate limit errors in {"error": "..."}
    err = result.get("error", "")
    if err and ("429" in err or "rate_limit" in err or "overloaded" in err.lower()):
        if attempt < 10:
            wait = min(60 * (2 ** attempt), 600)
            print(f"  rate limited (attempt {attempt+1}), waiting {wait}s...", flush=True)
            time.sleep(wait)
            return generate(lens, lang, attempt + 1)
    return result


def main():
    total = len(LENSES) * len(LANGUAGES)
    done = 0
    errors = []

    print(f"=== Batch Painel IA Generation ===")
    print(f"Combos: {total} ({len(LENSES)} lenses x {len(LANGUAGES)} languages)")
    print(f"Force regenerate: {FORCE}")
    print()

    for lens in LENSES:
        for lang in LANGUAGES:
            done += 1
            tag = f"[{done}/{total}] {lens}/{lang}"
            print(f"{tag}: generating...", flush=True)

            t0 = time.time()
            result = generate(lens, lang)
            elapsed = time.time() - t0

            if result.get("error"):
                print(f"{tag}: ERROR — {result['error']}", flush=True)
                errors.append(f"{lens}/{lang}: {result['error']}")
            elif result.get("cached"):
                print(f"{tag}: cached (already exists)", flush=True)
            else:
                ms = result.get("generation_ms", "?")
                headline = (result.get("headline") or "")[:60]
                print(f"{tag}: OK in {ms}ms — \"{headline}...\"", flush=True)

            # Delay between requests — generous to avoid rate limits
            if done < total and not result.get("cached"):
                time.sleep(15)

    print()
    print(f"=== Done: {done - len(errors)} succeeded, {len(errors)} failed ===")
    if errors:
        print("Failures:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
