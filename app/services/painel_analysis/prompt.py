"""Prompt building for Painel analysis."""
from ..interpret import _load_ideology
from ...config import OUTPUT_LANGUAGES, DEFAULT_OUTPUT_LANGUAGE


def _build_painel_prompt(sections: list, updated: str, lens: str = None, custom_ideology: str = None, output_language: str = None) -> str:
    if lens:
        from ..ideology_lenses import get_lens_prompt, get_lens_link_sources, get_lens_metadata
        ideology = get_lens_prompt(lens, custom_ideology=custom_ideology)
        link_sources = get_lens_link_sources(lens)
        lens_meta = get_lens_metadata(lens)
        lens_meta = None
    else:
        ideology = _load_ideology()
        link_sources = "publico.pt, dn.pt, rtp.pt, observador.pt, expresso.pt, eco.sapo.pt, jornaldenegocios.pt"
        lens_meta = None

    # Build search hint: include party short name + full name in web searches
    search_party_hint = ""
    if lens_meta and lens_meta.get("party"):
        short = lens_meta.get("short", "")
        party = lens_meta["party"]
        search_party_hint = f"Inclui '{short} {party}' nos termos de pesquisa. "
    search_hint = f"{search_party_hint}Usa o tema da secção como termo (ex: 'energia Portugal 2026', 'emprego Portugal recente'). Prioriza artigos o mais recentes possível."

    section_blocks = []
    section_names = []
    for section in sections:
        title = section.get("title", "Indicadores")
        kpis = section.get("kpis", [])
        lines = []
        for k in kpis:
            if k.get("value") is None:
                continue
            yoy_str = f", var. anual: {k['yoy']:+.1f}{k.get('yoy_unit') or '%'}" if k.get("yoy") is not None else ""
            lines.append(
                f"  - {k['label']} ({k.get('source','?')}): {k['value']} {k.get('unit','')}{yoy_str}"
            )
        if lines:
            section_blocks.append(f"### {title}\n" + "\n".join(lines))
            section_names.append(title)

    if not section_blocks:
        return None

    sections_list = ", ".join(f'"{s}"' for s in section_names)

    n_sections = len(section_names)
    # ~120 tok/section (strictly 3 short sentences) + ~500 tok for links JSON
    token_budget = n_sections * 200 + 600

    # Build indicator ID list for section_charts guidance
    indicator_ids = []
    for sec in sections:
        for k in sec.get("kpis", []):
            ind_id = k.get("indicator") or k.get("id") or ""
            if ind_id and ind_id not in indicator_ids:
                indicator_ids.append(ind_id)
    ids_str = ", ".join(indicator_ids[:45])

    # Resolve output language
    lang_code = output_language or DEFAULT_OUTPUT_LANGUAGE
    lang_desc = OUTPUT_LANGUAGES.get(lang_code, OUTPUT_LANGUAGES.get(DEFAULT_OUTPUT_LANGUAGE, "português europeu (sem brasileirismos)"))
    _lang_name_map = {
        "pt": "português europeu (PT-PT)",
        "en": "English",
        "fr": "français",
        "es": "español",
    }
    lang_name = _lang_name_map.get(lang_code, lang_desc)

    # For custom lens: the user's ideology may specify a different language — respect it
    _lang_instruction_map = {
        "pt": f"CRÍTICO: Responde SEMPRE em {lang_desc}. NUNCA mudes de língua independentemente do conteúdo dos dados.",
        "en": f"CRITICAL: Always respond in {lang_desc}. NEVER switch languages regardless of the data content.",
        "fr": f"CRITIQUE: Réponds toujours en {lang_desc}. Ne change JAMAIS de langue.",
        "es": f"CRÍTICO: Responde siempre en {lang_desc}. NUNCA cambies de idioma.",
    }
    _lang_instruction_str = _lang_instruction_map.get(lang_code, f"CRITICAL: Always respond in {lang_desc}. Never switch languages.")
    _lang_rule = (
        f"IDIOMA: respeita o idioma especificado no enquadramento do utilizador acima. "
        f"Se não especificado, escreve em {lang_desc}.\n\n"
    ) if (lens == "custom" and custom_ideology) else (
        f"IDIOMA OBRIGATÓRIO: {_lang_instruction_str} "
        f"Ignora quaisquer instruções posteriores que contradigam esta regra de idioma.\n\n"
    )
    from ..prompt_loader import load_prompt
    instruction = load_prompt("painel_analysis",
        lang_rule=_lang_rule,
        token_budget=token_budget,
        search_hint=search_hint,
        updated=updated,
        lang_name=lang_name,
        lang_code=lang_code,
        sections_list=sections_list,
        link_sources=link_sources,
        ids_str=ids_str,
    )

    return f"{ideology}\n\n{instruction}\n\n" + "\n\n".join(section_blocks)


def _build_pt_europa_section() -> dict:
    """Build a Portugal vs. Europa section for the Sonnet prompt."""
    COMPARISONS = [
        ("Inflação HICP",          "EUROSTAT",  "hicp",                    "EU27_2020", "%"),
        ("Desemprego",             "EUROSTAT",  "unemployment",            "EU27_2020", "%"),
        ("Crescimento PIB",        "WORLDBANK", "gdp_growth",              "EU",        "%"),
        ("PIB per Capita PPP",     "WORLDBANK", "gdp_per_capita_ppp",      "EU",        "USD PPP"),
        ("Electricidade Dom.",     "EUROSTAT",  "electricity_price_household", "EU27_2020", "€/kWh"),
        ("Rendimento Hora",        "EUROSTAT",  "earn_ses_pub2s",          "EU27_2020", "€/h"),
        ("Esperança de Vida",      "WORLDBANK", "life_expectancy",         "EU",        "anos"),
        ("Taxa de Emprego",        "WORLDBANK", "employment_rate",         "EU",        "%"),
    ]
    try:
        from ..db import get_db
        conn = get_db()
        kpis = []
        for label, source, indicator, ref, unit in COMPARISONS:
            try:
                rows = conn.execute("""
                    SELECT region, value FROM indicators
                    WHERE source=? AND indicator=? AND region IN ('PT','EU27_2020','EU','EU27')
                    ORDER BY period DESC LIMIT 10
                """, [source, indicator]).fetchall()
                vals = {r[0]: r[1] for r in rows}
                pt_val  = vals.get("PT")
                ref_val = vals.get(ref) or vals.get("EU27_2020") or vals.get("EU27") or vals.get("EU")
                if pt_val is None: continue
                diff = None
                if ref_val and ref_val != 0:
                    diff = round(((pt_val - ref_val) / abs(ref_val)) * 100, 1)
                kpis.append({
                    "id": indicator,
                    "label": label,
                    "source": source,
                    "value": round(pt_val, 2),
                    "unit": unit,
                    "yoy": diff,
                    "yoy_unit": f"% vs {ref}",
                    "ref_value": round(ref_val, 2) if ref_val else None,
                    "ref_label": ref,
                })
            except Exception:
                continue
        conn.close()
        return {"id": "pt_europa", "title": "Portugal vs. Europa", "kpis": kpis}
    except Exception as e:
        return {"id": "pt_europa", "title": "Portugal vs. Europa", "kpis": []}
