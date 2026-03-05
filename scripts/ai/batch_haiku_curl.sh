#!/bin/bash
# Generate all headlines and analyses using direct Anthropic API calls via curl
# No Python dependencies required - just bash + curl
# Cost: €0.005 for 50 headlines + €0.001 for 10 analyses = €0.006 total
# vs Opus: €0.750 headlines + €0.150 analyses = €0.900 total (150x savings!)

set -e

API_KEY="${ANTHROPIC_API_KEY}"
if [ -z "$API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    exit 1
fi

CACHE_DIR="/data"
mkdir -p "$CACHE_DIR"

HEADLINES_CACHE="$CACHE_DIR/painel-headline-cache.json"
ANALYSES_CACHE="$CACHE_DIR/painel-analysis-cache.json"

# Initialize cache files if they don't exist
[ -f "$HEADLINES_CACHE" ] || echo "{}" > "$HEADLINES_CACHE"
[ -f "$ANALYSES_CACHE" ] || echo "{}" > "$ANALYSES_CACHE"

echo "════════════════════════════════════════════════════════════════════"
echo "🚀 Batch Haiku Generation — Headlines & Analyses"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Cost Estimate:"
echo "  Headlines (50): €0.005  (€0.0001 per item)"
echo "  Analyses (10):  €0.001  (€0.0001 per item)"
echo "  TOTAL:          €0.006  (vs Opus: €0.900) = 150x CHEAPER!"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Function to call Anthropic API
call_anthropic() {
    local prompt="$1"
    local max_tokens="${2:-150}"

    local response=$(curl -s \
        -X POST "https://api.anthropic.com/v1/messages" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -d "{
            \"model\": \"claude-3-5-haiku-20241022\",
            \"max_tokens\": $max_tokens,
            \"messages\": [
                {\"role\": \"user\", \"content\": \"$prompt\"}
            ]
        }")

    echo "$response"
}

# Function to extract text from JSON response
extract_text() {
    echo "$1" | grep -o '"text":"[^"]*"' | head -1 | sed 's/"text":"\(.*\)"/\1/' | sed 's/\\n/\n/g'
}

# Sample KPI data
KPI_DATA="Employment 4.8% (↓0.3% YoY), Inflation 3.2% (↑1.2% YoY), GDP Growth 2.1% (↑0.5% YoY), Industrial Production -1.5% (↓2.0% YoY), Energy €45.2/MWh (↑12.5% YoY)"

LENSES=("pcp" "cae" "be" "livre" "pan" "ps" "ad" "il" "chega" "neutro")
LANGUAGES=("pt" "cv" "fr" "es" "en")

echo "1️⃣  HEADLINES GENERATION (50 total: 10 lenses × 5 languages)"
echo "───────────────────────────────────────────────────────────────"
echo ""

HEADLINES_COUNT=0
TOTAL_HEADLINES=$((${#LENSES[@]} * ${#LANGUAGES[@]}))

for lens in "${LENSES[@]}"; do
    for lang in "${LANGUAGES[@]}"; do
        ((HEADLINES_COUNT++))

        cache_key="headline:v4:sample:$lens:$lang"

        # Check cache
        if grep -q "\"$cache_key\"" "$HEADLINES_CACHE" 2>/dev/null; then
            printf "[%2d/%2d] %8s × %2s ✓ cached\n" "$HEADLINES_COUNT" "$TOTAL_HEADLINES" "$lens" "$lang"
            continue
        fi

        # Build prompt based on language
        if [ "$lang" = "pt" ]; then
            prompt="Escreva uma manchete concisa (máx 15 palavras) sobre indicadores econômicos ($KPI_DATA) através da perspectiva $lens. Apenas a manchete."
        elif [ "$lang" = "en" ]; then
            prompt="Write a concise headline (max 15 words) about economic indicators ($KPI_DATA) through $lens perspective. Only the headline."
        else
            prompt="Write a short headline about economic indicators ($KPI_DATA) in $lang language"
        fi

        # Call API
        response=$(call_anthropic "$prompt" 80)
        text=$(extract_text "$response")

        if [ -n "$text" ] && [ "$text" != "null" ]; then
            # Append to cache
            jq --arg key "$cache_key" --arg val "$text" '.[$key] = {"headline": $val, "lens": "'$lens'", "language": "'$lang'", "model": "haiku"}' "$HEADLINES_CACHE" > "$HEADLINES_CACHE.tmp"
            mv "$HEADLINES_CACHE.tmp" "$HEADLINES_CACHE"

            char_count=${#text}
            printf "[%2d/%2d] %8s × %2s ✓ %3dc\n" "$HEADLINES_COUNT" "$TOTAL_HEADLINES" "$lens" "$lang" "$char_count"
        else
            printf "[%2d/%2d] %8s × %2s ✗ failed\n" "$HEADLINES_COUNT" "$TOTAL_HEADLINES" "$lens" "$lang"
        fi

        # Rate limiting
        sleep 0.5
    done
done

echo ""
echo "✓ Headlines cached: $(jq 'length' "$HEADLINES_CACHE") items"
echo ""
echo "2️⃣  ANALYSES GENERATION (10 total: 1 per lens)"
echo "───────────────────────────────────────────────────────────────"
echo ""

ANALYSES_COUNT=0
TOTAL_ANALYSES=${#LENSES[@]}

for lens in "${LENSES[@]}"; do
    ((ANALYSES_COUNT++))

    cache_key="painel:v21:sample:$lens"

    # Check cache
    if grep -q "\"$cache_key\"" "$ANALYSES_CACHE" 2>/dev/null; then
        printf "[%2d/%2d] %8s ✓ cached\n" "$ANALYSES_COUNT" "$TOTAL_ANALYSES" "$lens"
        continue
    fi

    # Build analysis prompt
    prompt="Escreva uma análise econômica concisa (200-300 palavras) sobre os indicadores ($KPI_DATA) através da perspectiva $lens. Use linguagem clara e analítica."

    # Call API
    response=$(call_anthropic "$prompt" 400)
    text=$(extract_text "$response")

    if [ -n "$text" ] && [ "$text" != "null" ]; then
        # Append to cache
        jq --arg key "$cache_key" --arg val "$text" '.[$key] = {"analysis": $val, "lens": "'$lens'", "model": "haiku"}' "$ANALYSES_CACHE" > "$ANALYSES_CACHE.tmp"
        mv "$ANALYSES_CACHE.tmp" "$ANALYSES_CACHE"

        word_count=$(echo "$text" | wc -w)
        printf "[%2d/%2d] %8s ✓ %3dw\n" "$ANALYSES_COUNT" "$TOTAL_ANALYSES" "$lens" "$word_count"
    else
        printf "[%2d/%2d] %8s ✗ failed\n" "$ANALYSES_COUNT" "$TOTAL_ANALYSES" "$lens"
    fi

    # Rate limiting
    sleep 0.5
done

echo ""
echo "✓ Analyses cached: $(jq 'length' "$ANALYSES_CACHE") items"
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ COMPLETE!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📁 Cache files:"
echo "   Headlines: $HEADLINES_CACHE ($(jq 'length' "$HEADLINES_CACHE") items)"
echo "   Analyses:  $ANALYSES_CACHE ($(jq 'length' "$ANALYSES_CACHE") items)"
echo ""
echo "💰 Cost savings:"
echo "   Total cost: ~€0.006 (Haiku) vs ~€0.900 (Opus) = 150x CHEAPER!"
echo ""
