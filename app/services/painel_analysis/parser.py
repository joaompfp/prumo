"""Parsing helpers for Painel analysis responses."""
import json


def _parse_meta_json(text: str) -> tuple:
    """Extract META_JSON:{section_links:{...}, chart_pick:{...}} from end of text."""
    marker = '\nMETA_JSON:'
    idx = text.rfind(marker)
    if idx == -1:
        # Fallback: try old SECTION_LINKS format
        marker_old = '\nSECTION_LINKS:'
        idx_old = text.rfind(marker_old)
        if idx_old == -1:
            clean = text.strip()
            headline, subheadline, clean = _extract_headline(clean)
            return clean, {}, None, {}, headline, subheadline
        try:
            json_start = text.index('{', idx_old + len(marker_old))
            links, _ = json.JSONDecoder().raw_decode(text, json_start)
            clean = text[:idx_old].strip()
            headline, subheadline, clean = _extract_headline(clean)
            return clean, links, None, {}, headline, subheadline
        except Exception:
            clean = text[:idx_old].strip()
            headline, subheadline, clean = _extract_headline(clean)
            return clean, {}, None, {}, headline, subheadline
    try:
        json_start = text.index('{', idx + len(marker))
        meta, _ = json.JSONDecoder().raw_decode(text, json_start)
        section_links = meta.get('section_links', {})
        chart_pick = meta.get('chart_pick')
        section_charts = meta.get('section_charts', {})
        clean = text[:idx].strip()
        headline, subheadline, clean = _extract_headline(clean)
        return clean, section_links, chart_pick, section_charts, headline, subheadline
    except Exception:
        clean = text[:idx].strip()
        headline, subheadline, clean = _extract_headline(clean)
        return clean, {}, None, {}, headline, subheadline


def _extract_headline(text: str) -> tuple:
    """Extract HEADLINE/SUBHEADLINE from END of text. Returns (headline, subheadline, rest_of_text).
    Searches backwards so that HEADLINE/SUBHEADLINE placed at the end (editorial synthesis) are found.
    Also strips leading markdown heading markers (#) from extracted values."""
    headline = ""
    subheadline = ""
    lines = text.split('\n')
    headline_idx = None
    subheadline_idx = None
    # Search from the end backwards
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if not headline and stripped.startswith('HEADLINE:'):
            headline = stripped[len('HEADLINE:'):].strip()
            headline = headline.lstrip('#').strip()  # strip markdown heading markers
            headline_idx = i
        elif not subheadline and stripped.startswith('SUBHEADLINE:'):
            subheadline = stripped[len('SUBHEADLINE:'):].strip()
            subheadline = subheadline.lstrip('#').strip()  # strip markdown heading markers
            subheadline_idx = i
        if headline and subheadline:
            break
    # Remove HEADLINE/SUBHEADLINE lines from the rest
    indices_to_remove = set()
    if headline_idx is not None:
        indices_to_remove.add(headline_idx)
    if subheadline_idx is not None:
        indices_to_remove.add(subheadline_idx)
    rest_lines = [l for i, l in enumerate(lines) if i not in indices_to_remove]
    rest = '\n'.join(rest_lines).strip()
    return headline, subheadline, rest
