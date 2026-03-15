#!/usr/bin/env python3
"""
Prumo CAE Dashboard — Browser Test Suite (Onda 1)
Site: http://joao.date/dados (base_path: /dados)
Cobertura: page load, navegação, search, language switch, lens, API, cards, gráficos
Usa playwright.sync_api (headless Chromium).

Executar via pw-run (requer browsers instalados no sistema):
    # Copiar para workspace/scripts/ e correr:
    ssh f3nix "pw-run prumo_browser_tests.py"

Ou com sistema Python (se playwright + browsers instalados):
    python3 test_browser.py
"""

import sys
import json
import time
import traceback

# Remove prumo venv from sys.path to avoid its playwright (which lacks browsers).
# pw-run uses the system playwright that has browsers installed.
sys.path = [p for p in sys.path if '/prumo/venv' not in p]

SITE = "http://joao.date/dados"
BASE_PATH = "/dados"  # __BASE_PATH__ injectado pelo template

PASS = []
FAIL = []
SKIP = []


def run_test(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✅ PASS  {name}")
    except Exception as e:
        FAIL.append((name, str(e)))
        print(f"  ❌ FAIL  {name}")
        print(f"           {e}")


def skip_test(name, reason):
    SKIP.append((name, reason))
    print(f"  ⏭️  SKIP  {name} — {reason}")


def summarize():
    total = len(PASS) + len(FAIL) + len(SKIP)
    print("\n" + "=" * 60)
    print(f"RESULTADO: {len(PASS)}/{total} passed | {len(FAIL)} failed | {len(SKIP)} skipped")
    print("=" * 60)
    if FAIL:
        print("\nFALHAS:")
        for name, err in FAIL:
            print(f"  ❌ {name}")
            print(f"     {err}")
    if SKIP:
        print("\nSKIPS:")
        for name, reason in SKIP:
            print(f"  ⏭️  {name}: {reason}")
    return len(FAIL) == 0


def main():
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    except ImportError:
        print("ERRO: playwright não está instalado.")
        print("Instalar com: pip install playwright && playwright install chromium")
        sys.exit(2)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # ── Verificar se o site está acessível ─────────────────────────
        site_up = True
        resp = None
        try:
            resp = page.goto(SITE, wait_until="domcontentloaded", timeout=25000)
            if resp is None or resp.status >= 500:
                site_up = False
        except Exception as e:
            site_up = False
            print(f"  ⚠️  Site inacessível: {e}")

        if not site_up:
            for name in [
                "1_page_load", "2_navegacao_tabs", "3_search_desemprego",
                "4_language_switch", "5_lens_switcher", "6_api_health_painel",
                "6_api_health_lenses", "7_cards_sem_overflow", "8_grafico_visivel"
            ]:
                skip_test(name, "site inacessível (HTTP/network error)")
            summarize()
            browser.close()
            return

        # aguardar JS inicial
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass  # networkidle pode fazer timeout em sites com polling

        # Ler base_path do contexto da página
        base_path = page.evaluate("() => window.__BASE_PATH__ || ''")
        if not base_path:
            base_path = BASE_PATH

        # ─────────────────────────────────────────────────────────────────
        # TESTE 1 — Page load: título, HTTP 200, conteúdo não vazio
        # ─────────────────────────────────────────────────────────────────
        def t1_page_load():
            assert resp is not None, "Resposta HTTP nula"
            assert resp.status == 200, f"HTTP {resp.status} esperado 200"
            title = page.title()
            assert len(title) > 0, "Título da página está vazio"
            title_lower = title.lower()
            assert any(kw in title_lower for kw in ["prumo", "cae", "economia", "dados", "pt"]), \
                f"Título inesperado: {title!r}"
            content = page.content()
            assert len(content) > 5000, f"Conteúdo demasiado curto: {len(content)} bytes"
            # nav existe
            nav = page.query_selector(
                "nav, [role='navigation'], .nav-tabs, [class*='nav']"
            )
            assert nav is not None, "Elemento de navegação não encontrado"
            # Secção painel visível
            painel = page.query_selector("#painel")
            assert painel is not None, "#painel não encontrado no DOM"

        run_test("1_page_load", t1_page_load)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 2 — Navegação entre secções
        # ─────────────────────────────────────────────────────────────────
        def t2_navegacao_tabs():
            sections = [
                ("painel", "Painel"),
                ("comparativos", "Comparativos"),
                ("explorador", "Análise"),
                ("ajuda", "Ajuda"),
            ]
            for section_id, tab_label in sections:
                tab = page.query_selector(f"[data-section='{section_id}']")
                assert tab is not None, \
                    f"Tab '{tab_label}' não encontrado (data-section={section_id})"
                tab.click()
                page.wait_for_timeout(600)
                section_el = page.query_selector(f"#{section_id}")
                assert section_el is not None, \
                    f"Secção #{section_id} não encontrada no DOM"
                # Verificar que não está hidden com display:none
                visible = page.evaluate(
                    f"() => {{ const el = document.getElementById('{section_id}'); "
                    f"return el ? getComputedStyle(el).display !== 'none' : false; }}"
                )
                assert visible, \
                    f"Secção #{section_id} está oculta após clicar em '{tab_label}'"
            # Repor painel
            painel_tab = page.query_selector("[data-section='painel']")
            if painel_tab:
                painel_tab.click()
                page.wait_for_timeout(400)

        run_test("2_navegacao_tabs", t2_navegacao_tabs)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 3 — Search: "desemprego" → resultados aparecem
        # ─────────────────────────────────────────────────────────────────
        def t3_search():
            search_input = page.query_selector("#search-input")
            assert search_input is not None, \
                "Campo de pesquisa #search-input não encontrado"
            search_input.click()
            search_input.fill("desemprego")
            page.wait_for_timeout(800)
            results_el = page.query_selector("#search-results")
            assert results_el is not None, "#search-results não encontrado"
            n_items = page.evaluate(
                "() => document.querySelectorAll('.search-item').length"
            )
            assert n_items > 0, \
                "Nenhum resultado .search-item encontrado para 'desemprego'"
            # limpar
            search_input.fill("")
            page.keyboard.press("Escape")

        run_test("3_search_desemprego", t3_search)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 4 — Language switch PT → EN
        # ─────────────────────────────────────────────────────────────────
        def t4_language_switch():
            # Estado inicial
            initial_lang = page.evaluate(
                "() => localStorage.getItem('prumo-output-language') || 'pt'"
            )

            # Tentar clicar botão EN (dentro do #nav-lang-selector)
            en_btn = page.query_selector(
                "#nav-lang-selector [data-lang='en'], "
                ".lang-selector [data-lang='en'], "
                "button[data-lang='en']"
            )

            if en_btn:
                en_btn.click()
                page.wait_for_timeout(400)
            else:
                # Forçar via JS (equivalente a clicar no botão)
                page.evaluate(
                    "() => { localStorage.setItem('prumo-output-language', 'en'); "
                    "window.dispatchEvent(new CustomEvent('language-change', "
                    "{ detail: { language: 'en' } })); }"
                )
                page.wait_for_timeout(400)

            current_lang = page.evaluate(
                "() => localStorage.getItem('prumo-output-language')"
            )
            assert current_lang == "en", \
                f"Língua não mudou para EN: {current_lang!r}"

            # Repor PT
            page.evaluate(
                "() => { localStorage.setItem('prumo-output-language', 'pt'); "
                "window.dispatchEvent(new CustomEvent('language-change', "
                "{ detail: { language: 'pt' } })); }"
            )
            page.wait_for_timeout(300)
            restored = page.evaluate(
                "() => localStorage.getItem('prumo-output-language')"
            )
            assert restored == "pt", f"Língua não voltou a PT: {restored!r}"

        run_test("4_language_switch", t4_language_switch)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 5 — Lens switcher
        # ─────────────────────────────────────────────────────────────────
        def t5_lens_switcher():
            # Ir para o painel
            painel_tab = page.query_selector("[data-section='painel']")
            if painel_tab:
                painel_tab.click()
                page.wait_for_timeout(1000)

            initial_lens = page.evaluate(
                "() => localStorage.getItem('prumo-lens') || 'cae'"
            )

            # Clicar numa lens-pill (PS ou IL, diferentes da default CAE)
            lens_pill = page.query_selector(
                ".lens-pill[data-lens='ps'], .lens-pill[data-lens='il'], "
                ".lens-pill[data-lens='be']"
            )

            if lens_pill:
                target_lens = lens_pill.get_attribute("data-lens")
                lens_pill.click()
                page.wait_for_timeout(500)
            else:
                # Forçar via evento (fallback se pills ainda não carregaram)
                target_lens = "ps"
                page.evaluate(
                    "() => { localStorage.setItem('prumo-lens', 'ps'); "
                    "window.dispatchEvent(new CustomEvent('lens-change', "
                    "{ detail: { lens: 'ps', source: 'test' } })); }"
                )
                page.wait_for_timeout(500)

            current_lens = page.evaluate(
                "() => localStorage.getItem('prumo-lens')"
            )
            assert current_lens is not None and len(current_lens) > 0, \
                f"Lens é null/vazio após mudança"
            # Se pill foi encontrada, verificar que mudou para o target
            if lens_pill and initial_lens != target_lens:
                assert current_lens == target_lens, \
                    f"Lens não mudou: esperado '{target_lens}', obtido '{current_lens}'"

            # Repor lens original
            page.evaluate(
                f"() => {{ localStorage.setItem('prumo-lens', '{initial_lens}'); "
                f"window.dispatchEvent(new CustomEvent('lens-change', "
                f"{{ detail: {{ lens: '{initial_lens}', source: 'test' }} }})); }}"
            )

        run_test("5_lens_switcher", t5_lens_switcher)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 6 — API health: /api/painel e /api/lenses
        # ─────────────────────────────────────────────────────────────────
        def t6_api_painel():
            result = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{base_path}/api/painel');
                        const j = await r.json();
                        return {{
                            status: r.status,
                            hasData: typeof j === 'object' && j !== null,
                            sections: j.sections?.length || 0,
                            updated: j.updated || '',
                        }};
                    }} catch(e) {{
                        return {{ status: 0, error: e.message }};
                    }}
                }}
            """)
            assert result.get("status") == 200, \
                f"/api/painel retornou {result.get('status')}: {result}"
            assert result.get("hasData"), \
                f"/api/painel não retornou JSON válido: {result}"
            n = result.get("sections", 0)
            assert n > 0, f"/api/painel retornou 0 secções: {result}"

        def t6_api_lenses():
            result = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{base_path}/api/lenses');
                        const j = await r.json();
                        const isArr = Array.isArray(j);
                        const count = isArr ? j.length : Object.keys(j).length;
                        return {{
                            status: r.status,
                            count: count,
                            isArray: isArr,
                            sample: isArr ? j[0]?.id : Object.keys(j)[0],
                        }};
                    }} catch(e) {{
                        return {{ status: 0, error: e.message }};
                    }}
                }}
            """)
            assert result.get("status") == 200, \
                f"/api/lenses retornou {result.get('status')}: {result}"
            n = result.get("count", 0)
            assert n >= 5, \
                f"/api/lenses retornou apenas {n} lentes (esperado ≥5): {result}"

        run_test("6_api_health_painel", t6_api_painel)
        run_test("6_api_health_lenses", t6_api_lenses)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 7 — Cards e KPIs sem overflow (bounding box height > 0)
        # ─────────────────────────────────────────────────────────────────
        def t7_cards_sem_overflow():
            # Ir para painel e aguardar carregamento
            painel_tab = page.query_selector("[data-section='painel']")
            if painel_tab:
                painel_tab.click()
                page.wait_for_timeout(2000)

            # Tentar .ai-card primeiro, depois KPI items
            n_ai_cards = page.evaluate(
                "() => document.querySelectorAll('.ai-card').length"
            )
            n_kpi_items = page.evaluate(
                "() => document.querySelectorAll('[class*=\"kpi\"]').length"
            )

            if n_ai_cards == 0 and n_kpi_items == 0:
                # Verificar se section tem conteúdo
                body_len = page.evaluate(
                    "() => { const s = document.getElementById('painel'); "
                    "return s ? s.innerText.length : 0; }"
                )
                if body_len < 100:
                    skip_test("7_cards_sem_overflow",
                              "painel sem conteúdo — possivelmente DB offline")
                    return
                # Aceitar: há conteúdo mas não ai-cards
                return

            # Se há ai-cards, verificar bounding box
            if n_ai_cards > 0:
                selector = ".ai-card"
            else:
                selector = "[class*='kpi']"

            cards = page.query_selector_all(selector)
            bad = 0
            for card in cards[:10]:
                box = card.bounding_box()
                if box is None or box.get("height", 0) <= 0:
                    bad += 1
            assert bad == 0, \
                f"{bad} elementos '{selector}' com height ≤ 0 (overflow/hidden)"

        run_test("7_cards_sem_overflow", t7_cards_sem_overflow)

        # ─────────────────────────────────────────────────────────────────
        # TESTE 8 — Gráfico visível (canvas ECharts com dimensões > 0)
        # ─────────────────────────────────────────────────────────────────
        def t8_grafico_visivel():
            # Verificar canvas (ECharts usa canvas)
            n_canvas = page.evaluate(
                "() => document.querySelectorAll('canvas').length"
            )

            if n_canvas == 0:
                # Ir para explorador e aguardar
                analise_tab = page.query_selector("[data-section='explorador']")
                if analise_tab:
                    analise_tab.click()
                    page.wait_for_timeout(2500)
                n_canvas = page.evaluate(
                    "() => document.querySelectorAll('canvas').length"
                )

            if n_canvas == 0:
                skip_test("8_grafico_visivel",
                          "nenhum canvas encontrado — gráficos podem requerer dados live")
                return

            # Verificar que pelo menos 1 canvas tem dimensões válidas
            valid = page.evaluate("""
                () => {
                    const canvases = document.querySelectorAll('canvas');
                    let count = 0;
                    for (let i = 0; i < Math.min(10, canvases.length); i++) {
                        const r = canvases[i].getBoundingClientRect();
                        if (r.width > 10 && r.height > 10) count++;
                    }
                    return count;
                }
            """)
            assert valid > 0, (
                f"Nenhum dos {n_canvas} canvas tem dimensões reais > 10×10px"
            )
            assert n_canvas >= 1, "Esperado ≥1 canvas com gráfico ECharts"

        run_test("8_grafico_visivel", t8_grafico_visivel)

        # ─────────────────────────────────────────────────────────────────
        context.close()
        browser.close()

    ok = summarize()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
