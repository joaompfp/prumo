"""Share card image generation using Pillow (fallback when Playwright pre-gen unavailable).

Produces branded 1200x630 PNG cards suitable for OpenGraph / Twitter Card previews.
Fonts are loaded from static/fonts/share/ — falls back to PIL default if missing.
"""

import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ── Font loading ────────────────────────────────────────────────────────
_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "fonts", "share")


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TTF font from the share fonts directory, fall back to default."""
    path = os.path.join(_FONTS_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        return ImageFont.load_default(size=size)


# ── Brand palette ───────────────────────────────────────────────────────
PT_RED = "#CC0000"
BG = "#F6F4F1"
TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#5A5550"
POSITIVE = "#2E7D32"
NEGATIVE = "#C62828"
NEUTRAL = "#6B6560"
BORDER = "#E2DED9"
BOTTOM_BAR = "#1A1A1A"
BOTTOM_TEXT = "#AAAAAA"

# ── Logo path ───────────────────────────────────────────────────────────
_LOGO_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static", "images", "prumo", "nav-icon.png"
)


def _paste_logo(img: Image.Image, x: int, y: int, size: int = 44):
    """Paste the nav-icon logo onto the image, silently skipping on error."""
    try:
        logo = Image.open(_LOGO_PATH).convert("RGBA").resize((size, size))
        img.paste(logo, (x, y), logo)
    except Exception:
        pass


def _sentiment_color(sentiment: str) -> str:
    """Map sentiment string to a hex color."""
    if sentiment == "positive":
        return POSITIVE
    if sentiment == "negative":
        return NEGATIVE
    return NEUTRAL


def _format_value(value, unit: str = "") -> str:
    """Format a numeric value for display on the card."""
    if value is None:
        return "\u2014"  # em dash
    if isinstance(value, float):
        if abs(value) < 0.01:
            s = f"{value:.4f}"
        elif abs(value) < 1:
            s = f"{value:,.3f}"
        elif abs(value) >= 10000:
            s = f"{value:,.0f}"
        else:
            s = f"{value:,.2f}"
        # Strip trailing zeros after decimal point
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    return str(value)


# ── Sparkline drawing ───────────────────────────────────────────────────

def _extract_values(data_points) -> list[float]:
    """Extract numeric values from spark data (list of dicts or numbers)."""
    if data_points and isinstance(data_points[0], dict):
        return [
            p.get("value") or p.get("v", 0)
            for p in data_points
            if isinstance(p, dict) and p.get("value") is not None
        ]
    return [p for p in data_points if isinstance(p, (int, float))]


def _draw_sparkline(draw: ImageDraw.ImageDraw, data_points, x: int, y: int,
                    w: int, h: int, color: str):
    """Draw sparkline — delegates to the supersampled version on the image."""
    # This is a no-op stub; the real rendering happens in generate_kpi_card_fallback
    # via _render_chart_supersampled which draws on a separate high-res canvas.
    pass


def _render_chart_supersampled(img: Image.Image, data_points, x: int, y: int,
                                w: int, h: int, color: str, scale: int = 3):
    """Render a smooth, anti-aliased area chart by supersampling.

    Draws at scale*x resolution then downsamples with LANCZOS for smooth lines.
    Includes a filled gradient area under the line for visual weight.
    """
    values = _extract_values(data_points)
    if len(values) < 2:
        return

    min_v, max_v = min(values), max(values)
    span = max_v - min_v if max_v != min_v else 1.0
    pad = 20 * scale  # padding so line doesn't touch edges

    sw, sh = w * scale, h * scale
    canvas = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw_hi = ImageDraw.Draw(canvas)

    # Compute points at high resolution
    points = []
    for i, v in enumerate(values):
        px = pad + (i / (len(values) - 1)) * (sw - 2 * pad)
        py = pad + (sh - 2 * pad) - ((v - min_v) / span) * (sh - 2 * pad)
        points.append((px, py))

    # ── Filled area under the line (gradient effect via opacity) ──────
    # Create polygon: line points + bottom-right + bottom-left
    area_points = list(points) + [(sw - pad, sh - pad), (pad, sh - pad)]
    # Parse color to RGB
    r_c = int(color[1:3], 16) if color.startswith("#") else 46
    g_c = int(color[3:5], 16) if color.startswith("#") else 125
    b_c = int(color[5:7], 16) if color.startswith("#") else 50
    draw_hi.polygon(area_points, fill=(r_c, g_c, b_c, 40))  # very subtle fill

    # ── Line ──────────────────────────────────────────────────────────
    line_width = 10 * scale  # will become ~10px after downsampling — very bold
    draw_hi.line(points, fill=color, width=line_width, joint="curve")

    # ── Endpoint dot ──────────────────────────────────────────────────
    last = points[-1]
    r = 6 * scale
    draw_hi.ellipse([(last[0] - r, last[1] - r), (last[0] + r, last[1] + r)], fill=color)

    # ── Downsample with high-quality filter ───────────────────────────
    chart = canvas.resize((w, h), Image.LANCZOS)
    img.paste(chart, (x, y), chart)


# ── Text wrapping ───────────────────────────────────────────────────────

def _draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, x: int, y: int,
                       max_width: int, font, color: str, max_lines: int = 2,
                       line_spacing: int = 30) -> int:
    """Draw word-wrapped text. Returns the y position after the last line."""
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines[:max_lines]):
        if i == max_lines - 1 and len(lines) > max_lines:
            # Truncate with ellipsis
            while len(line) > 3:
                line = line[:-1]
                bbox = draw.textbbox((0, 0), line + "\u2026", font=font)
                if bbox[2] - bbox[0] <= max_width:
                    break
            line = line + "\u2026"
        draw.text((x, y + i * line_spacing), line, fill=color, font=font)

    drawn = min(len(lines), max_lines)
    return y + drawn * line_spacing


def _draw_bottom_bar(draw: ImageDraw.ImageDraw, img_w: int, img_h: int,
                     left_text: str, font):
    """Draw the dark bottom bar with metadata and branding."""
    bar_h = 56
    bar_y = img_h - bar_h
    draw.rectangle([(0, bar_y), (img_w, img_h)], fill=BOTTOM_BAR)
    draw.text((40, bar_y + 16), left_text, fill=BOTTOM_TEXT, font=font)
    draw.text(
        (img_w - 40, bar_y + 16),
        "Prumo PT \u2014 Economia a R\u00e9gua e Esquadro",
        fill=BOTTOM_TEXT, font=font, anchor="ra",
    )


def _draw_header(draw: ImageDraw.ImageDraw, img: Image.Image, img_w: int,
                 font_brand, font_meta):
    """Draw the top accent bar, logo, brand name, and URL."""
    # Red accent line at top
    draw.rectangle([(0, 0), (img_w, 6)], fill=PT_RED)
    # Logo
    _paste_logo(img, 40, 20, size=44)
    # Brand name
    draw.text((96, 22), "Prumo PT", fill=PT_RED, font=font_brand)
    # URL top-right
    draw.text((img_w - 40, 26), "cae.joao.date", fill=TEXT_SECONDARY, font=font_meta, anchor="ra")


# ══════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════

def generate_kpi_card_fallback(kpi: dict, section_name: str = "") -> bytes:
    """Generate a 1200x630 branded PNG for a single KPI.

    Design: PURE CHART. No text at all — the OG title/description carry context.
    The image is just the trendline on a clean background, maximally visible
    even at WhatsApp/Telegram thumbnail sizes.
    """
    # Render at 600x315 so elements are large relative to thumbnail crop,
    # then upscale to 1200x630 for OG spec with LANCZOS for smooth scaling.
    WW, HH = 600, 315
    img = Image.new("RGBA", (WW, HH), BG)
    draw = ImageDraw.Draw(img)

    sentiment = kpi.get("sentiment", "neutral")
    color = _sentiment_color(sentiment)

    # ── Red accent line ───────────────────────────────────────────────
    draw.rectangle([(0, 0), (WW, 3)], fill=PT_RED)

    # ── Chart ─────────────────────────────────────────────────────────
    pad = 16
    spark = kpi.get("spark", [])
    if spark and len(spark) >= 3:
        _render_chart_supersampled(
            img, spark, pad, 3 + pad,
            WW - 2 * pad, HH - 3 - 2 * pad, color,
            scale=2,
        )
    else:
        value = kpi.get("value")
        unit = kpi.get("unit", "")
        value_str = f"{_format_value(value)} {unit}".strip()
        big_font = _load_font("Inter-Bold.ttf", 80)
        draw.text((WW // 2, HH // 2), value_str, fill=TEXT_PRIMARY, font=big_font, anchor="mm")

    # ── Watermark: logo + "Portugal" ──────────────────────────────────
    try:
        logo = Image.open(_LOGO_PATH).convert("RGBA").resize((260, 260))
        alpha = logo.split()[3].point(lambda a: min(a, 140))
        logo.putalpha(alpha)
        logo_x = WW // 2 - 130
        logo_y = HH // 2 - 160
        img.paste(logo, (logo_x, logo_y), logo)

        font_pt = _load_font("CormorantGaramond-BoldItalic.ttf", 36)
        txt_layer = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_layer)
        txt_draw.text((WW // 2, logo_y + 268), "Portugal",
                       fill=(139, 0, 0, 180), font=font_pt, anchor="mt")
        img.paste(txt_layer, (0, 0), txt_layer)
    except Exception:
        pass

    # ── Upscale to 1200x630 (OG spec) with smooth interpolation ──────
    final = img.convert("RGB").resize((1200, 630), Image.LANCZOS)

    buf = BytesIO()
    final.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_painel_card(headline: str, highlights: list, updated: str) -> bytes:
    """Generate a 1200x630 summary card for the Painel snapshot.

    highlights: list of dicts with keys 'sentence' and 'sentiment'.
    """
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), color=BG)
    draw = ImageDraw.Draw(img)

    # ── Fonts ───────────────────────────────────────────────────────
    font_brand = _load_font("PlayfairDisplay-Black.ttf", 34)
    font_title = _load_font("Inter-Bold.ttf", 30)
    font_body = _load_font("Inter-Regular.ttf", 21)
    font_meta = _load_font("Inter-Regular.ttf", 16)
    font_eyebrow = _load_font("Inter-Bold.ttf", 16)

    # ── Header ──────────────────────────────────────────────────────
    _draw_header(draw, img, W, font_brand, font_meta)

    # ── Eyebrow ─────────────────────────────────────────────────────
    draw.text((48, 86), "PORTUGAL EM 60 SEGUNDOS", fill=TEXT_SECONDARY, font=font_eyebrow)

    # ── Headline ────────────────────────────────────────────────────
    y_cursor = 116
    if headline:
        y_cursor = _draw_wrapped_text(
            draw, headline, 48, y_cursor, W - 96, font_title, TEXT_PRIMARY,
            max_lines=2, line_spacing=40,
        )
        y_cursor += 12

    # ── Separator line ──────────────────────────────────────────────
    draw.line([(48, y_cursor), (W - 48, y_cursor)], fill=BORDER, width=1)
    y_cursor += 16

    # ── Highlight bullets ───────────────────────────────────────────
    for h in highlights[:5]:
        if y_cursor > H - 90:
            break
        sentiment = h.get("sentiment", "neutral")
        color = _sentiment_color(sentiment)
        sentence = h.get("sentence", "")

        # Colored dot
        dot_y = y_cursor + 8
        draw.ellipse([(48, dot_y), (60, dot_y + 12)], fill=color)

        # Sentence text
        _draw_wrapped_text(
            draw, sentence, 74, y_cursor, W - 130, font_body, TEXT_PRIMARY,
            max_lines=1, line_spacing=28,
        )
        y_cursor += 44

    # ── Bottom bar ──────────────────────────────────────────────────
    meta = f"Dados: {updated} \u00b7 9 fontes oficiais"
    _draw_bottom_bar(draw, W, H, meta, font_meta)

    # ── Export ──────────────────────────────────────────────────────
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
