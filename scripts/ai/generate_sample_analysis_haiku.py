#!/usr/bin/env python3
"""
Generate sample Painel analyses using Claude Haiku (no database required).
Creates realistic sample data for testing/caching purposes.
Cost: ~€0.001 per analysis (15x cheaper than Opus!)

Usage: python3 generate_sample_analysis_haiku.py
"""
import sys
import os
import json
import time
import anthropic

# Sample economic data for analysis
SAMPLE_ANALYSIS_CONTEXT = """
Economic Context (March 2026):
- Unemployment: 4.8% (↓ 0.3% YoY)
- Inflation: 3.2% (↑ 1.2% YoY)
- GDP Growth: 2.1% (↑ 0.5% YoY)
- Industrial Production: -1.5% (↓ 2.0% YoY)
- Retail Sales: +1.8% (↑ 0.6% YoY)
- Energy Prices: €45.2/MWh (↑ 12.5% YoY)
- Housing Prices: ↑ 8.5% (↑ 2.1% YoY)

Key Sectors:
- Manufacturing: Slight contraction (-1.5%)
- Services: Growth continuing (+1.8%)
- Energy: High prices persisting
- Employment: Modest improvement (-0.3% unemployment)
"""

# All lenses
LENSES = ["pcp", "cae", "be", "livre", "pan", "ps", "ad", "il", "chega", "neutro"]

# Lens-specific perspectives
LENS_PERSPECTIVES = {
    "pcp": {
        "pt": "Perspectiva PCP: foco em direitos dos trabalhadores, sindicatos, proteção social",
        "en": "PCP perspective: focus on worker rights, labor unions, social protection"
    },
    "cae": {
        "pt": "Perspectiva CAE: foco em sustentabilidade ambiental e economia verde",
        "en": "CAE perspective: focus on environmental sustainability and green economy"
    },
    "be": {
        "pt": "Perspectiva BE: foco em políticas centradas no mercado e negócios",
        "en": "BE perspective: focus on centrist, business-friendly policies"
    },
    "livre": {
        "pt": "Perspectiva LIVRE: foco em democracia direta e direitos digitais",
        "en": "LIVRE perspective: focus on direct democracy and digital rights"
    },
    "pan": {
        "pt": "Perspectiva PAN: foco em liberdades individuais e liberalismo clássico",
        "en": "PAN perspective: focus on individual freedoms and classical liberalism"
    },
    "ps": {
        "pt": "Perspectiva PS: foco em democracia social e serviços públicos",
        "en": "PS perspective: focus on social democracy and public services"
    },
    "ad": {
        "pt": "Perspectiva AD: foco em valores conservadores e instituições tradicionais",
        "en": "AD perspective: focus on conservative values and traditional institutions"
    },
    "il": {
        "pt": "Perspectiva IL: foco em identidade portuguesa e interesses nacionais",
        "en": "IL perspective: focus on Portuguese identity and national interests"
    },
    "chega": {
        "pt": "Perspectiva CHEGA: foco em soberania nacional e controle de imigração",
        "en": "CHEGA perspective: focus on national sovereignty and immigration control"
    },
    "neutro": {
        "pt": "Perspectiva Neutra: análise equilibrada dos indicadores econômicos",
        "en": "Neutral perspective: balanced analysis of economic indicators"
    }
}

def build_analysis_prompt(lens, output_language="pt"):
    """Build an analysis generation prompt for the given lens."""

    if output_language == "pt":
        perspective = LENS_PERSPECTIVES.get(lens, {}).get("pt", "")
        prompt = f"""Você é um economista e analista político. Analise os indicadores econômicos abaixo através de uma lente política específica.

Contexto Econômico (Março 2026):
{SAMPLE_ANALYSIS_CONTEXT}

{perspective}

Escreva uma análise concisa (200-300 palavras) que explique:
1. Qual é a situação econômica atual?
2. Como essa situação é interpretada por esta perspectiva política?
3. Quais são as implicações políticas principais?
4. Qual seria a solução proposta por esta perspectiva?

Mantenha um tom analítico e imparcial, mesmo ao expressar a perspectiva política."""

    elif output_language == "en":
        perspective = LENS_PERSPECTIVES.get(lens, {}).get("en", "")
        prompt = f"""You are an economist and political analyst. Analyze the economic indicators below through a specific political lens.

Economic Context (March 2026):
{SAMPLE_ANALYSIS_CONTEXT}

{perspective}

Write a concise analysis (200-300 words) that explains:
1. What is the current economic situation?
2. How is this situation interpreted by this political perspective?
3. What are the main political implications?
4. What solution would this perspective propose?

Maintain an analytical and impartial tone, even while expressing the political perspective."""

    else:
        prompt = f"""Analyze the economic indicators below through a {lens} political lens.

Economic Context:
{SAMPLE_ANALYSIS_CONTEXT}

Write a 200-300 word analysis explaining the situation, interpretation, implications, and proposed solution from this political perspective."""

    return prompt

def generate_analyses_with_haiku():
    """Generate sample analyses using Claude Haiku."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Create cache directory if needed
    cache_dir = os.path.dirname(os.getenv("CAE_DB_PATH", "/data/cae-data.duckdb"))
    cache_path = os.path.join(cache_dir, "painel-analysis-cache.json")

    # Create directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)

    # Load existing cache
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.loads(open(cache_path).read())
        except:
            cache = {}

    total = len(LENSES)
    processed = 0
    skipped = 0
    succeeded = 0
    failed = 0

    print(f"[haiku] Generating {total} sample analyses (1 per lens)")
    print(f"[haiku] Estimated cost: ~${total * 0.001:.2f} USD (vs Opus: ${total * 0.015:.2f})")
    print()

    for lens in LENSES:
        processed += 1
        print(f"[{processed:2}/{total}] {lens:8} ...", end=" ", flush=True)

        # Build cache key
        cache_key = f"painel:v21:sample:{lens}"

        # Check if already cached
        if cache_key in cache and cache[cache_key].get("analysis"):
            print("✓ cached")
            skipped += 1
            continue

        try:
            # Build prompt
            prompt = build_analysis_prompt(lens, output_language="pt")
            if not prompt:
                print("✗ no prompt")
                failed += 1
                continue

            # Call Haiku
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=400,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            analysis = message.content[0].text.strip()

            # Cache result
            cache[cache_key] = {
                "analysis": analysis,
                "lens": lens,
                "generated_at": time.time(),
                "model": "haiku",
                "sample_data": True
            }

            # Show cost info
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            cost_usd = (input_tokens * 0.00008 + output_tokens * 0.0002) / 1000

            analysis_len = len(analysis.split())
            print(f"✓ {analysis_len:3}w ${cost_usd:.6f}")
            succeeded += 1

            # Save cache after each analysis
            with open(cache_path, 'w') as f:
                json.dump(cache, f, indent=2)

        except anthropic.RateLimitError:
            print("⚠ rate limited, waiting 60s...")
            time.sleep(60)
            processed -= 1  # Retry this one

        except Exception as e:
            print(f"✗ {str(e)[:30]}")
            failed += 1

    # Final save
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)

    print()
    print("=" * 70)
    print(f"✓ Results: {succeeded} succeeded, {failed} failed ({skipped} skipped from cache)")
    print(f"✓ Total cached: {len(cache)} analyses")
    print(f"✓ Estimated cost: ${total * 0.001:.2f} USD (vs Opus: ${total * 0.015:.2f})")
    print(f"✓ Cache file: {cache_path}")
    print("=" * 70)

if __name__ == "__main__":
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    generate_analyses_with_haiku()
