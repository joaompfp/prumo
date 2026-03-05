#!/usr/bin/env python3
"""
Generate sample Painel headlines using Claude Haiku (no database required).
Creates realistic sample data for testing/caching purposes.
Cost: ~€0.00013 per headline (180x cheaper than Opus!)

Usage: python3 generate_sample_headlines_haiku.py
"""
import sys
import os
import json
import time
import anthropic

# Sample economic data for headlines (no database needed)
SAMPLE_KPI_DATA = {
    "Employment": {"current": 4.8, "yoy_change": -0.3, "source": "INE"},
    "Inflation": {"current": 3.2, "yoy_change": 1.2, "source": "Eurostat"},
    "GDP Growth": {"current": 2.1, "yoy_change": 0.5, "source": "INE"},
    "Industrial Production": {"current": -1.5, "yoy_change": -2.0, "source": "Eurostat"},
    "Retail Sales": {"current": 1.8, "yoy_change": 0.6, "source": "INE"},
    "Energy Prices": {"current": 45.2, "yoy_change": 12.5, "source": "DGEG"},
    "Housing Prices": {"current": 8.5, "yoy_change": 2.1, "source": "INE"},
}

# All lenses
LENSES = ["pcp", "cae", "be", "livre", "pan", "ps", "ad", "il", "chega", "neutro"]

# All output languages
LANGUAGES = ["pt", "cv", "fr", "es", "en"]

# Language display names
LANG_NAMES = {
    "pt": "português",
    "cv": "kriolu",
    "fr": "français",
    "es": "español",
    "en": "english"
}

# Lens methodology (simplified samples)
LENS_PROMPTS = {
    "pcp": "PCP perspective: focus on worker rights, labor unions, social protection",
    "cae": "CAE perspective: focus on environmental sustainability and green economy",
    "be": "BE perspective: focus on centrist, business-friendly policies",
    "livre": "LIVRE perspective: focus on direct democracy and digital rights",
    "pan": "PAN perspective: focus on individual freedoms and classical liberalism",
    "ps": "PS perspective: focus on social democracy and public services",
    "ad": "AD perspective: focus on conservative values and traditional institutions",
    "il": "IL perspective: focus on Portuguese identity and national interests",
    "chega": "CHEGA perspective: focus on national sovereignty and immigration control",
    "neutro": "Neutral perspective: balanced analysis of economic indicators"
}

def build_headline_prompt(kpis, lens, output_language):
    """Build a headline generation prompt for the given lens and language."""

    lang_name = LANG_NAMES.get(output_language, output_language)

    kpi_summary = "\n".join([
        f"- {name}: {data['current']}% (YoY: {data['yoy_change']:+.1f}%, Source: {data['source']})"
        for name, data in kpis.items()
    ])

    if output_language == "pt":
        prompt = f"""Você é um analista econômico que escreve manchetes para um dashboard de indicadores.

Dados:
{kpi_summary}

Perspectiva ({lens}): {LENS_PROMPTS.get(lens, 'Neutral perspective')}

Escreva uma manchete concisa (máx 15 palavras) que capture a essência dos indicadores através desta perspectiva política.
A manchete deve ser impactante, clara e direta. Use tom profissional.

Responda APENAS com a manchete, sem aspas ou explicações."""

    elif output_language == "cv":
        prompt = f"""Você é um analista econômico que escreve manchetes em Kriolu Cabo-verdiano.

Dados:
{kpi_summary}

Perspectiva ({lens}): {LENS_PROMPTS.get(lens, 'Neutral perspective')}

Screvi un manchete concisu (máx 15 palávra) ki capture essencia di indicadór sé perspektiva politik.
Manchete deve sê impactante, clara e direta. Usa ton profisional.

Responda APENAS ku manchete, sin aspas ou explicasõi."""

    elif output_language == "fr":
        prompt = f"""Vous êtes un analyste économique qui rédige des titres pour un tableau de bord d'indicateurs.

Données:
{kpi_summary}

Perspective ({lens}): {LENS_PROMPTS.get(lens, 'Neutral perspective')}

Rédigez un titre concis (max 15 mots) qui capture l'essence des indicateurs selon cette perspective politique.
Le titre doit être percutant, clair et direct. Utilisez un ton professionnel.

Répondez UNIQUEMENT avec le titre, sans guillemets ni explications."""

    elif output_language == "es":
        prompt = f"""Eres un analista económico que escribe titulares para un panel de indicadores.

Datos:
{kpi_summary}

Perspectiva ({lens}): {LENS_PROMPTS.get(lens, 'Neutral perspective')}

Escribe un titular conciso (máx 15 palabras) que capture la esencia de los indicadores desde esta perspectiva política.
El titular debe ser impactante, claro y directo. Usa tono profesional.

Responde SOLO con el titular, sin comillas ni explicaciones."""

    else:  # English
        prompt = f"""You are an economic analyst writing headlines for an indicators dashboard.

Data:
{kpi_summary}

Perspective ({lens}): {LENS_PROMPTS.get(lens, 'Neutral perspective')}

Write a concise headline (max 15 words) that captures the essence of these indicators from this political perspective.
The headline should be impactful, clear and direct. Use professional tone.

Respond ONLY with the headline, no quotes or explanations."""

    return prompt

def generate_headlines_with_haiku():
    """Generate sample headlines using Claude Haiku."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Create cache directory if needed
    cache_dir = os.path.dirname(os.getenv("CAE_DB_PATH", "/data/cae-data.duckdb"))
    cache_path = os.path.join(cache_dir, "painel-headline-cache.json")

    # Create directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)

    # Load existing cache
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.loads(open(cache_path).read())
        except:
            cache = {}

    total = len(LENSES) * len(LANGUAGES)
    processed = 0
    skipped = 0
    succeeded = 0
    failed = 0

    print(f"[haiku] Generating {len(LENSES)} lenses × {len(LANGUAGES)} languages = {total} sample headlines")
    print(f"[haiku] Estimated cost: ~${total * 0.00013:.2f} USD (vs Opus: ${total * 0.024:.2f})")
    print()

    for lens in LENSES:
        for lang in LANGUAGES:
            processed += 1
            print(f"[{processed:2}/{total}] {lens:8} × {lang:2} ...", end=" ", flush=True)

            # Build cache key
            cache_key = f"headline:v4:sample:{lens}:{lang}"

            # Check if already cached
            if cache_key in cache and cache[cache_key].get("headline"):
                print("✓ cached")
                skipped += 1
                continue

            try:
                # Build prompt
                prompt = build_headline_prompt(SAMPLE_KPI_DATA, lens=lens, output_language=lang)
                if not prompt:
                    print("✗ no prompt")
                    failed += 1
                    continue

                # Call Haiku
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=80,
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
                    "model": "haiku",
                    "sample_data": True
                }

                # Show cost info
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens
                cost_usd = (input_tokens * 0.00008 + output_tokens * 0.0002) / 1000

                print(f"✓ {len(headline):3}c ${cost_usd:.6f}")
                succeeded += 1

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
                failed += 1

    # Final save
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)

    print()
    print("=" * 70)
    print(f"✓ Results: {succeeded} succeeded, {failed} failed ({skipped} skipped from cache)")
    print(f"✓ Total cached: {len(cache)} headlines")
    print(f"✓ Estimated cost: ${total * 0.00013:.2f} USD (vs Opus: ${total * 0.024:.2f})")
    print(f"✓ Cache file: {cache_path}")
    print("=" * 70)

if __name__ == "__main__":
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    generate_headlines_with_haiku()
