"""
snapshot.py — "Portugal em 60 Segundos": data-driven hero highlights.

Picks the most newsworthy KPIs from the painel, fills sentence templates,
and returns a compact JSON payload for the hero section.
"""

import json
import os
from pathlib import Path

from .painel import build_painel


# ── Priority KPIs: citizen-facing indicators get 2x weight ───────────
PRIORITY_KPIS = {
    "inflation", "unemployment", "diesel", "gasoline_95",
    "electricity_btn", "euribor_3m", "euribor_6m", "euribor_12m",
    "renewable_share", "wages_industry", "gdp_per_capita",
    "employment_rate", "energy_cost",
}

# KPIs to EXCLUDE from the snapshot — raw commodities / technical
EXCLUDE_KPIS = {
    "copper", "aluminum", "electricity_mt", "electricity_at",
}

# Target: 5 positive + 5 negative highlights
TARGET_POS = 5
TARGET_NEG = 5

# Map KPI IDs to their parent section IDs (for diversity enforcement)
_KPI_SECTION_MAP = {}  # populated lazily

# Mood labels by mood category and language
MOOD_LABELS = {
    "pt": {"positive": "Sinais positivos", "negative": "Sinais preocupantes", "mixed": "Sinais mistos"},
    "en": {"positive": "Positive signals", "negative": "Warning signs", "mixed": "Mixed signals"},
}

# ── Load templates ────────────────────────────────────────────────────
_CONSTANTS_DIR = Path(__file__).resolve().parent.parent / "constants"
_templates_cache = {}


def _load_templates(lang="pt"):
    if lang not in _templates_cache:
        suffix = f"_{lang}" if lang != "pt" else ""
        path = _CONSTANTS_DIR / f"snapshot_templates{suffix}.json"
        if not path.exists():
            path = _CONSTANTS_DIR / "snapshot_templates.json"  # fallback to PT
        with open(path, "r", encoding="utf-8") as f:
            _templates_cache[lang] = json.load(f)
    return _templates_cache[lang]


_MONTH_NAMES = {
    "pt": ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
           "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}

_REFERENCE_LABELS = {
    "pt": "Variação face ao mesmo período do ano anterior",
    "en": "Change vs same period last year",
}


def _format_period(period_str, lang="pt"):
    """Convert '2026-03' to 'March 2026' for display."""
    if not period_str or len(period_str) < 7:
        return period_str or ""
    month_names = _MONTH_NAMES.get(lang, _MONTH_NAMES["pt"])
    try:
        parts = period_str.split("-")
        yr = parts[0]
        mo = int(parts[1])
        return f"{month_names[mo - 1]} {yr}"
    except (IndexError, ValueError):
        return period_str


def _build_section_map(sections):
    """Build KPI ID -> section ID map from painel sections."""
    global _KPI_SECTION_MAP
    if _KPI_SECTION_MAP:
        return _KPI_SECTION_MAP
    for section in sections:
        sid = section.get("id", "")
        if sid == "catalogo":
            continue
        for kpi in section.get("kpis", []):
            kpi_id = kpi.get("id")
            if kpi_id:
                _KPI_SECTION_MAP[kpi_id] = sid
    return _KPI_SECTION_MAP


def build_snapshot(lang="pt"):
    """Build data-driven snapshot for hero section.

    Returns:
        {
            "mood": "mixed"|"positive"|"negative",
            "mood_label": "Sinais mistos",
            "highlights": [
                {
                    "id": "inflation",
                    "label": "Inflacao",
                    "sentence": "Os precos sobem 2.3% ao ano...",
                    "sentiment": "negative",
                    "value": 2.3,
                    "yoy": 0.5,
                    "period": "2026-03",
                    "section": "custo_de_vida",
                },
                ...
            ],
            "updated": "2026-03",
            "updated_label": "Marco 2026",
        }
    """
    painel = build_painel()
    sections = painel.get("sections", [])
    updated = painel.get("updated", "")
    section_map = _build_section_map(sections)
    templates = _load_templates(lang)

    # ── Collect all scoreable KPIs ────────────────────────────────────
    candidates = []
    for section in sections:
        if section.get("id") == "catalogo":
            continue
        for kpi in section.get("kpis", []):
            kpi_id = kpi.get("id")
            if not kpi_id:
                continue
            if kpi.get("error"):
                continue
            if kpi_id in EXCLUDE_KPIS:
                continue
            yoy = kpi.get("yoy")
            value = kpi.get("value")
            sentiment = kpi.get("sentiment", "neutral")
            if yoy is None or value is None:
                continue

            # Score: abs(yoy) * priority_weight
            weight = 2.0 if kpi_id in PRIORITY_KPIS else 1.0
            score = abs(yoy) * weight

            candidates.append({
                "id": kpi_id,
                "label": kpi.get("label", kpi_id),
                "value": value,
                "yoy": yoy,
                "yoy_abs": round(abs(yoy), 2),
                "period": kpi.get("period", ""),
                "sentiment": sentiment,
                "section": section_map.get(kpi_id, ""),
                "unit": kpi.get("unit", ""),
                "score": score,
            })

    # ── Sort by score descending ──────────────────────────────────────
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # ── Pick 5 positive + 5 negative (max 2 per section) ──────────────
    positives = [c for c in candidates if c["sentiment"] == "positive"]
    negatives = [c for c in candidates if c["sentiment"] in ("negative", "neutral")]

    def _pick(pool, target):
        picked = []
        section_counts = {}
        for c in pool:
            sec = c["section"]
            if section_counts.get(sec, 0) >= 2:
                continue
            picked.append(c)
            section_counts[sec] = section_counts.get(sec, 0) + 1
            if len(picked) >= target:
                break
        # Relax section constraint if not enough
        if len(picked) < target:
            for c in pool:
                if c not in picked:
                    picked.append(c)
                    if len(picked) >= target:
                        break
        return picked

    pos_selected = _pick(positives, TARGET_POS)
    neg_selected = _pick(negatives, TARGET_NEG)
    selected = pos_selected + neg_selected

    # ── Fill sentence templates ───────────────────────────────────────
    highlights = []
    for item in selected:
        kpi_id = item["id"]
        sentiment = item["sentiment"]
        tpl_set = templates.get(kpi_id, {})
        tpl = tpl_set.get(sentiment, tpl_set.get("neutral", "{label}: {value}"))

        sentence = tpl.format(
            value=item["value"],
            yoy_abs=item["yoy_abs"],
            period=_format_period(item["period"], lang),
            label=item["label"],
        )

        highlights.append({
            "id": kpi_id,
            "label": item["label"],
            "sentence": sentence,
            "sentiment": sentiment,
            "value": item["value"],
            "yoy": item["yoy"],
            "period": item["period"],
            "section": item["section"],
        })

    # ── Compute mood ──────────────────────────────────────────────────
    pos_count = sum(1 for h in highlights if h["sentiment"] == "positive")
    neg_count = sum(1 for h in highlights if h["sentiment"] == "negative")
    total = len(highlights)

    if total == 0:
        mood = "mixed"
    elif pos_count > neg_count and pos_count >= total * 0.6:
        mood = "positive"
    elif neg_count > pos_count and neg_count >= total * 0.6:
        mood = "negative"
    else:
        mood = "mixed"

    return {
        "mood": mood,
        "mood_label": MOOD_LABELS.get(lang, MOOD_LABELS["pt"]).get(mood, "Mixed"),
        "highlights": highlights,
        "updated": updated,
        "updated_label": _format_period(updated, lang),
        "reference": _REFERENCE_LABELS.get(lang, _REFERENCE_LABELS["pt"]),
    }
