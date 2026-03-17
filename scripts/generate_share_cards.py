#!/usr/bin/env python3
"""Generate social share card screenshots using Playwright.

Usage (run on HOST, not inside Docker):
    source venv/bin/activate
    python scripts/generate_share_cards.py [--base-url URL] [--output-dir DIR] [--kpi-id ID]

Captures 1200x630 screenshots of each KPI card from the live site.
Saves to appdata/prumo/share-cards/ (same dir the API serves from).

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# Default paths
DEFAULT_BASE_URL = "https://cae.joao.date"
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "appdata", "share-cards"
)

# Card dimensions for OG images
CARD_WIDTH = 1200
CARD_HEIGHT = 630


def fetch_painel(base_url: str) -> dict:
    """Fetch /api/painel to get all KPI IDs and metadata."""
    url = f"{base_url}/api/painel"
    print(f"  Fetching {url} ...")
    resp = urllib.request.urlopen(url, timeout=30)
    return json.loads(resp.read())


def generate_kpi_card(page, base_url: str, kpi_id: str, period: str, output_dir: str) -> str | None:
    """Capture a single KPI card as a 1200x630 screenshot.

    Returns the output path on success, None on failure.
    """
    out_path = os.path.join(output_dir, f"kpi_{kpi_id}_{period}.png")

    # Navigate to dashboard and wait for cards to render
    page.goto(f"{base_url}/#painel", wait_until="networkidle", timeout=30000)

    # Wait for KPI cards to appear
    page.wait_for_selector(".kpi-card", timeout=15000)

    # Find the specific KPI card by data-kpi-id or matching content
    # Cards use data attributes from the kpi-share-btn inside them
    card = page.query_selector(f'.kpi-share-btn[data-kpi-id="{kpi_id}"]')
    if card:
        card = card.evaluate_handle("el => el.closest('.kpi-card')").as_element()

    if not card:
        # Fallback: search by text content within labels
        cards = page.query_selector_all(".kpi-card")
        for c in cards:
            share_btn = c.query_selector(f'[data-kpi-id="{kpi_id}"]')
            if share_btn:
                card = c
                break

    if not card:
        print(f"    [SKIP] Card not found for {kpi_id}")
        return None

    # Scroll card into view
    card.scroll_into_view_if_needed()
    page.wait_for_timeout(500)  # let sparklines render

    # Take element screenshot at high quality
    card.screenshot(path=out_path, type="png")

    # The element screenshot will be the card's natural size.
    # Resize to 1200x630 for OG compliance using Playwright's page screenshot
    # with a clip, or post-process with Pillow if needed.
    # For now, the element screenshot is good enough — the share route
    # also has a Pillow fallback for exact 1200x630 sizing.

    print(f"    [OK] {out_path}")
    return out_path


def generate_painel_summary(page, base_url: str, updated: str, output_dir: str) -> str | None:
    """Capture the hero snapshot / painel header as a summary card."""
    out_path = os.path.join(output_dir, f"painel_{updated}.png")

    page.goto(f"{base_url}/#painel", wait_until="networkidle", timeout=30000)
    page.wait_for_selector(".kpi-card", timeout=15000)
    page.wait_for_timeout(1000)  # let all sparklines render

    # Capture the full painel section header + first row of cards
    section = page.query_selector("#painel")
    if not section:
        print("    [SKIP] #painel section not found")
        return None

    # Use page screenshot with clip for exact 1200x630 dimensions
    box = section.bounding_box()
    if not box:
        print("    [SKIP] Could not measure #painel bounding box")
        return None

    # Capture top portion of painel section at 1200x630
    page.screenshot(
        path=out_path,
        type="png",
        clip={
            "x": box["x"],
            "y": box["y"],
            "width": min(box["width"], CARD_WIDTH),
            "height": min(CARD_HEIGHT, box["height"]),
        }
    )
    print(f"    [OK] {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate social share card PNGs via Playwright")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the Prumo site")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for PNGs")
    parser.add_argument("--kpi-id", default=None, help="Generate card for a single KPI (by ID)")
    parser.add_argument("--no-summary", action="store_true", help="Skip painel summary card")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with visible window")
    args = parser.parse_args()

    # Validate output dir
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Output dir: {args.output_dir}")

    # Fetch KPI data
    print("\n1. Fetching painel data...")
    try:
        painel = fetch_painel(args.base_url)
    except Exception as e:
        print(f"   FATAL: Could not fetch /api/painel: {e}", file=sys.stderr)
        sys.exit(1)

    updated = painel.get("updated", "unknown")
    sections = painel.get("sections", [])

    # Collect all KPIs
    all_kpis = []
    for section in sections:
        for kpi in section.get("kpis", []):
            if kpi.get("value") is not None and not kpi.get("error"):
                all_kpis.append(kpi)

    if args.kpi_id:
        all_kpis = [k for k in all_kpis if k["id"] == args.kpi_id]
        if not all_kpis:
            print(f"   KPI '{args.kpi_id}' not found in painel data.", file=sys.stderr)
            sys.exit(1)

    print(f"   Found {len(all_kpis)} KPIs, updated={updated}")

    # Launch Playwright
    print("\n2. Launching Playwright browser...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("   FATAL: playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        # Use a viewport wide enough for desktop layout
        context = browser.new_context(
            viewport={"width": CARD_WIDTH, "height": 900},
            device_scale_factor=2,  # retina-quality screenshots
        )
        page = context.new_page()

        # Dismiss hero onboarding if present
        page.goto(f"{args.base_url}/#painel", wait_until="networkidle", timeout=30000)
        page.evaluate("localStorage.setItem('prumo-hero-dismissed', '1')")

        # Generate painel summary card
        if not args.no_summary:
            print("\n3. Generating painel summary card...")
            generate_painel_summary(page, args.base_url, updated, args.output_dir)

        # Generate individual KPI cards
        print(f"\n4. Generating {len(all_kpis)} KPI cards...")
        ok = 0
        skip = 0
        for kpi in all_kpis:
            kpi_id = kpi["id"]
            period = kpi.get("period", "unknown")
            result = generate_kpi_card(page, args.base_url, kpi_id, period, args.output_dir)
            if result:
                ok += 1
            else:
                skip += 1

        browser.close()

    print(f"\nDone: {ok} cards generated, {skip} skipped.")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
