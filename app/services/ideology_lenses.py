"""
Ideology Lenses — runtime-selectable political perspectives for AI analysis.

Each lens is derived from the actual program of a Portuguese political party
(Programa Eleitoral) or from structured political axis frameworks. The source
document is cited in each lens definition.

Prompt text is loaded from /data/ideologies/<id>.txt at import time.
The CAE lens also falls back to /data/ideology.txt for backward compatibility.
"""
import os
from .interpret import _load_ideology
from ..config import site_cfg, IDEOLOGIES_DIR

_IDEOLOGIES_DIR = IDEOLOGIES_DIR

# Ideology file mapping from site.json (e.g. {"pcp": "pcp.txt", ...})
_IDEOLOGY_MAP: dict = site_cfg("ideologies", {}) or {}


def _load_lens_file(lens_id: str) -> str | None:
    """Load ideology text from ideologies dir (configured in site.json paths.ideologies_dir).
    Filename comes from site.json 'ideologies' map, falling back to <lens_id>.txt."""
    filename = _IDEOLOGY_MAP.get(lens_id, f"{lens_id}.txt")
    path = os.path.join(_IDEOLOGIES_DIR, filename)
    try:
        if os.path.exists(path):
            text = open(path, encoding="utf-8").read().strip()
            if text:
                return text
    except Exception:
        pass
    return None


# ── Lens definitions ────────────────────────────────────────────────
# Each lens:
#   id       — unique key used in API params and frontend state
#   label    — display name (PT-PT)
#   short    — abbreviated label for pill buttons
#   party    — party or framework name
#   source   — document from which the perspective was derived
#   prompt   — the ideology text injected into AI prompts (loaded from file or hardcoded fallback)
#   color    — brand color for UI accent (hex)

# Per-lens link sources: preferred news/analysis sites for each ideological lens
_DEFAULT_LINK_SOURCES = "publico.pt, dn.pt, rtp.pt, observador.pt, expresso.pt, eco.sapo.pt, jornaldenegocios.pt"

LENSES = [
    # ── Left → Right ideological spectrum ──────────────────────────────
    {
        "id": "pcp",
        "label": "PCP — Programa Eleitoral",
        "short": "PCP",
        "party": "Partido Comunista Português",
        "source": "Programa Eleitoral do PCP (2024) + Resolução Política do XX Congresso",
        "prompt": None,  # loaded from ideologies/pcp.txt
        "color": "#CC0000",
        "icon": "pcp",
        "link_sources": "pcp.pt, avante.pt, abrilabril.pt, publico.pt, rtp.pt, dn.pt",
    },
    {
        "id": "cae",
        "label": "CAE (equipa Prumo)",
        "short": "CAE",
        "party": None,
        "source": "Configuração do operador desta instância (ideology.txt) — perspectiva industrial e laboral, informada pelo programa do PCP",
        "prompt": None,  # loaded from ideologies/cae.txt or ideology.txt at init
        "color": "#8B0000",
        "icon": "cae",
        "link_sources": "pcp.pt, avante.pt, abrilabril.pt, publico.pt, rtp.pt, dn.pt",
        "default": True,
    },
    {
        "id": "be",
        "label": "BE — Esquerda Ecossocialista",
        "short": "BE",
        "party": "Bloco de Esquerda",
        "source": "Programa Eleitoral do Bloco de Esquerda (2024)",
        "prompt": None,  # loaded from ideologies/be.txt
        "color": "#D32F2F",
        "icon": "be",
        "link_sources": "blfranciscomiguel.pt, esquerda.net, publico.pt, rtp.pt, dn.pt, expresso.pt",
    },
    {
        "id": "livre",
        "label": "Livre — Esquerda Verde Europeísta",
        "short": "L",
        "party": "Livre",
        "source": "Programa Eleitoral do Livre (2024)",
        "prompt": None,  # loaded from ideologies/livre.txt
        "color": "#00C853",
        "icon": "livre",
        "link_sources": "partidolivre.pt, publico.pt, rtp.pt, dn.pt, expresso.pt, observador.pt",
    },
    {
        "id": "pan",
        "label": "PAN — Pessoas-Animais-Natureza",
        "short": "PAN",
        "party": "Pessoas-Animais-Natureza",
        "source": "Programa Eleitoral do PAN (2024)",
        "prompt": None,  # loaded from ideologies/pan.txt
        "color": "#1B5E20",
        "icon": "pan",
        "link_sources": "pan.com.pt, publico.pt, rtp.pt, dn.pt, expresso.pt, observador.pt",
    },
    {
        "id": "ps",
        "label": "PS — Social-Democracia",
        "short": "PS",
        "party": "Partido Socialista",
        "source": "Programa Eleitoral do PS (2024) — 'Portugal Inteiro'",
        "prompt": None,  # loaded from ideologies/ps.txt
        "color": "#E91E63",
        "icon": "ps",
        "link_sources": "ps.pt, publico.pt, rtp.pt, dn.pt, expresso.pt, observador.pt",
    },
    {
        "id": "ad",
        "label": "AD — Centro-Direita Liberal",
        "short": "AD",
        "party": "Aliança Democrática (PSD + CDS-PP)",
        "source": "Programa do XXIV Governo Constitucional (AD, 2024) + Programa Eleitoral AD",
        "prompt": None,  # loaded from ideologies/ad.txt
        "color": "#FF6F00",
        "icon": "ad",
        "link_sources": "psd.pt, observador.pt, eco.sapo.pt, jornaldenegocios.pt, publico.pt, expresso.pt",
    },
    {
        "id": "il",
        "label": "IL — Liberal",
        "short": "IL",
        "party": "Iniciativa Liberal",
        "source": "Programa Eleitoral da Iniciativa Liberal (2024) — 'Portugal a Sério'",
        "prompt": None,  # loaded from ideologies/il.txt
        "color": "#00BCD4",
        "icon": "il",
        "link_sources": "liberal.pt, observador.pt, eco.sapo.pt, jornaldenegocios.pt, expresso.pt, publico.pt",
    },
    {
        "id": "chega",
        "label": "Chega — Direita Nacional-Conservadora",
        "short": "CH",
        "party": "Chega",
        "source": "Programa Eleitoral do Chega (2024)",
        "prompt": None,  # loaded from ideologies/chega.txt
        "color": "#1A237E",
        "icon": "chega",
        "link_sources": "observador.pt, cnnportugal.iol.pt, expresso.pt, publico.pt, rtp.pt, jornaldenegocios.pt",
    },
    # ── Meta-lenses (not party-aligned) ────────────────────────────────
    {
        "id": "neutro",
        "label": "🙃 Neutral (eheh)",
        "short": "🙃 Neutral",
        "party": None,
        "source": "Sem enquadramento editorial — análise factual dos dados",
        "prompt": None,  # loaded from ideologies/neutro.txt
        "color": "#607D8B",
        "icon": "neutro",
        "link_sources": _DEFAULT_LINK_SOURCES,
    },
    {
        "id": "kriolu",
        "label": "🇨🇻 Kriolu São Vicente (ALUPEC)",
        "short": "🇨🇻 Kriolu",
        "party": None,
        "source": "Varianti Barlaventu, ortografia ALUPEC (DL 8/2009)",
        "prompt": None,  # loaded from ideologies/kriolu.txt
        "color": "#009A44",
        "icon": "custom",
        "link_sources": "observador.pt, publico.pt, eco.sapo.pt, jornaldenegocios.pt, rtp.pt",
    },
    {
        "id": "custom",
        "label": "Lente Personalizada",
        "short": "Custom",
        "party": None,
        "source": "Texto livre definido pelo utilizador no browser",
        "prompt": None,  # provided at runtime by the user — never stored server-side
        "color": "#9C27B0",
        "icon": "custom",
        "link_sources": _DEFAULT_LINK_SOURCES,
    },
]

# ── Hardcoded fallbacks (used only if file doesn't exist) ──────────
_FALLBACK_PROMPTS = {
    "pcp": (
        "És um analista económico que trabalha para o Partido Comunista Português (PCP). "
        "A tua análise parte do programa eleitoral do PCP (2024) e da Resolução Política do XX Congresso. "
        "Privilegias: a defesa dos direitos dos trabalhadores e o aumento dos salários, "
        "o investimento público em serviços públicos (SNS, escola pública, transportes), "
        "a soberania nacional e a produção nacional contra a dependência externa, "
        "a regulação pública dos sectores estratégicos (energia, água, transportes, banca), "
        "o combate à precariedade laboral e o reforço da contratação colectiva, "
        "e a denúncia das políticas de austeridade e da submissão ao capital financeiro. "
        "Interessa-te: poder de compra, emprego estável, custo de vida, produção industrial, "
        "investimento público, e convergência com a UE em salários e condições de vida."
    ),
    "ps": (
        "És um analista económico alinhado com os princípios da social-democracia europeia, "
        "tal como expressos no programa eleitoral do Partido Socialista (2024). "
        "A tua análise privilegia: o equilíbrio entre crescimento e redistribuição, "
        "o reforço do Estado Social (SNS, educação pública, protecção social), "
        "a convergência com a média europeia em rendimentos e produtividade, "
        "a transição energética como oportunidade económica, "
        "a sustentabilidade das contas públicas sem austeridade, "
        "e a coesão territorial (interior vs litoral). "
        "Interessa-te: salário médio, cobertura do SNS, taxa de pobreza, investimento público, "
        "despesa em educação, e convergência PIB per capita com a UE."
    ),
    "ad": (
        "És um analista económico alinhado com os princípios do centro-direita liberal europeu, "
        "tal como expressos no programa do XXIV Governo Constitucional (Aliança Democrática, 2024). "
        "A tua análise privilegia: a competitividade empresarial e a redução da carga fiscal, "
        "a simplificação regulatória e desburocratização do Estado, "
        "a atracção de investimento privado e estrangeiro, "
        "a redução do peso do Estado na economia, "
        "a sustentabilidade fiscal e controlo da despesa pública, "
        "e a valorização do mérito e da iniciativa privada. "
        "Interessa-te: carga fiscal, facilidade de fazer negócios, IDE, crescimento do PIB, "
        "produtividade do trabalho, e competitividade internacional."
    ),
    "il": (
        "És um analista económico liberal clássico, alinhado com os princípios da Iniciativa Liberal "
        "tal como expressos no seu programa eleitoral (2024). "
        "A tua análise parte da liberdade económica individual e da economia de mercado. "
        "Privilegias: a redução de impostos como motor de crescimento, "
        "a liberalização de sectores regulados (energia, telecomunicações, habitação), "
        "a reforma do Estado para funções essenciais (justiça, defesa, regulação), "
        "a escolha individual (vouchers educação e saúde), "
        "a flexibilização laboral e a meritocracia. "
        "Interessa-te: carga fiscal total, liberdade económica (Heritage/Fraser), "
        "custo do Estado por cidadão, crescimento real do PIB per capita, e emigração qualificada."
    ),
    "be": (
        "És um analista económico de esquerda ecossocialista, alinhado com os princípios do Bloco de Esquerda "
        "tal como expressos no seu programa eleitoral (2024). "
        "A tua análise parte da desigualdade estrutural e da crise climática como eixos centrais. "
        "Privilegias: a justiça fiscal (tributação progressiva e do capital), "
        "os direitos laborais e o combate à precariedade, "
        "o acesso universal a habitação, saúde e educação como direitos, "
        "a transição energética com justiça social (não deixar ninguém para trás), "
        "a regulação do mercado imobiliário e o combate à especulação, "
        "e a economia feminista (disparidades salariais de género, economia dos cuidados). "
        "Interessa-te: índice de Gini, taxa de pobreza, custo da habitação vs rendimento, "
        "emprego precário, emissões de carbono, e desigualdade salarial."
    ),
    "chega": (
        "És um analista económico nacional-conservador, alinhado com os princípios do Chega "
        "tal como expressos no seu programa eleitoral (2024). "
        "A tua análise parte da defesa da soberania nacional e dos valores tradicionais. "
        "Privilegias: a redução drástica da carga fiscal sobre famílias e empresas, "
        "o combate à corrupção e ao desperdício na administração pública, "
        "a reforma profunda do Estado (menos burocracia, mais eficiência), "
        "a segurança e o controlo das fronteiras, "
        "a defesa da família e da natalidade como pilares da sociedade, "
        "e a valorização das forças armadas e de segurança. "
        "Interessa-te: carga fiscal total, despesa pública, criminalidade, natalidade, "
        "emigração, custo do Estado, e crescimento económico."
    ),
    "livre": (
        "És um analista económico de esquerda verde e europeísta, alinhado com os princípios do Livre "
        "tal como expressos no seu programa eleitoral (2024). "
        "A tua análise parte da sustentabilidade ambiental, da justiça social e da integração europeia. "
        "Privilegias: a transição ecológica como motor económico, "
        "o rendimento básico incondicional e a redução da pobreza, "
        "a igualdade de género e os direitos das minorias como indicadores de desenvolvimento, "
        "a habitação como direito fundamental (regulação de rendas, construção pública), "
        "a economia circular e a descarbonização, "
        "e a democracia participativa e a transparência do Estado. "
        "Interessa-te: emissões per capita, índice de Gini, custo da habitação, "
        "taxa de pobreza, investimento em energias renováveis, e igualdade salarial."
    ),
    "pan": (
        "És um analista económico ecologista e animalista, alinhado com os princípios do PAN "
        "tal como expressos no seu programa eleitoral (2024). "
        "A tua análise parte da defesa dos direitos dos animais, da sustentabilidade ambiental e da justiça intergeracional. "
        "Privilegias: o bem-estar animal como indicador civilizacional, "
        "a fiscalidade verde (taxa sobre poluição, incentivos à economia circular), "
        "a saúde pública preventiva e o acesso a alimentação saudável, "
        "a protecção da biodiversidade e dos ecossistemas, "
        "a transição para energias renováveis e eficiência energética, "
        "e a justiça social com enfoque nos mais vulneráveis. "
        "Interessa-te: emissões de carbono, energias renováveis, despesa em saúde, "
        "biodiversidade, pobreza energética, e sustentabilidade alimentar."
    ),
    "neutro": (
        "És um analista económico independente e técnico. "
        "A tua análise é estritamente factual: descreves o que os dados mostram, "
        "identificas tendências e anomalias, comparas com médias históricas e europeias, "
        "e indicas possíveis causas sem tomar posição política. "
        "Não privilegias nenhuma perspectiva ideológica. "
        "Usa linguagem objectiva e neutra."
    ),
    "kriolu": (
        "Skribe tudu en kriolu di São Visenti (varianti Barlaventu, ortografia ALUPEC DL 8/2009). "
        "Ka miska portuges — kriolu puru. "
        "Analisi neutral i fatual. Deskrevi u ke dados ta mostrA, sén juizamentu polítiku. "
        "Uza ta+verbu pa prezenti habitual, verbu-á pa pasadu simples, ka pa negason."
    ),
}

# Index for fast lookup
_LENS_MAP = {lens["id"]: lens for lens in LENSES}

# ── Load all lens prompts from files at import time ────────────────
for lens in LENSES:
    lid = lens["id"]
    if lid == "custom":
        continue  # custom lens text is provided at runtime
    # Try file first, then hardcoded fallback
    file_text = _load_lens_file(lid)
    if file_text:
        lens["prompt"] = file_text
    elif lid == "cae":
        # CAE: fallback to legacy ideology.txt
        lens["prompt"] = _load_ideology()
    elif lid in _FALLBACK_PROMPTS:
        lens["prompt"] = _FALLBACK_PROMPTS[lid]

_loaded = sum(1 for l in LENSES if l.get("prompt"))
print(f"[ideology_lenses] Loaded {_loaded}/{len(LENSES)-1} lens prompts "
      f"(dir: {_IDEOLOGIES_DIR}, exists: {os.path.isdir(_IDEOLOGIES_DIR)})", flush=True)


def get_lenses() -> list:
    """Return all available lenses (without full prompt text, for the frontend)."""
    return [
        {
            "id": lens["id"],
            "label": lens["label"],
            "short": lens["short"],
            "party": lens["party"],
            "source": lens["source"],
            "color": lens["color"],
            "icon": lens.get("icon"),
        }
        for lens in LENSES
    ]


def get_lens_prompt(lens_id: str, custom_ideology: str = None) -> str:
    """Return the ideology prompt for a given lens ID.
    For lens_id='custom', returns the user-provided custom_ideology text.
    Falls back to CAE (operator's custom lens) if lens_id is invalid."""
    if lens_id == "custom" and custom_ideology:
        return custom_ideology.strip()
    lens = _LENS_MAP.get(lens_id)
    if lens and lens.get("prompt"):
        return lens["prompt"]
    # Default: operator's custom lens (ideology.txt)
    return _LENS_MAP.get("cae", {}).get("prompt") or _load_ideology()


def get_lens_metadata(lens_id: str) -> dict | None:
    """Return full lens metadata (for Metodologia display)."""
    return _LENS_MAP.get(lens_id)


def get_lens_link_sources(lens_id: str) -> str:
    """Return the preferred link sources string for a given lens."""
    lens = _LENS_MAP.get(lens_id)
    if lens and lens.get("link_sources"):
        return lens["link_sources"]
    return _DEFAULT_LINK_SOURCES
