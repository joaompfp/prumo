"""Curated Portuguese multiseries comparisons that open as configured Caderno links.

The configurations are reviewed code, not database rows: the series ids, their raw scale groups,
the window and every reader sentence live in git. A group keeps series that share unit,
multiplier and base year; the first group is the left axis and the second the right axis. The
read service checks current eligibility and compatibility before it advertises a card, so an
incomplete configuration is never presented as a working comparison.
"""
from dataclasses import dataclass

from presentation import MissingText


@dataclass(frozen=True)
class PortugalGroup:
    """One raw scale group: its axis, stored signature and member series ids."""

    axis: int
    unit: str
    multiplier: float | None
    base_year: int | None
    series: tuple[str, ...]


@dataclass(frozen=True)
class PortugalComparison:
    """One curated Caderno configuration with its reviewed copy and scale groups."""

    slug: str
    title: str
    summary: str
    caveat: str
    groups: tuple[PortugalGroup, ...]
    frequency: str
    window: str

    @property
    def series(self) -> tuple[str, ...]:
        return tuple(series_id for group in self.groups for series_id in group.series)

    @property
    def axes(self) -> tuple[int, ...]:
        return tuple(group.axis for group in self.groups for _ in group.series)


@dataclass(frozen=True)
class PortugalComparisonsCopy:
    title: str
    intro: str
    action: str
    axis_left: str
    axis_right: str
    window_10a: str
    window_5a: str
    window_max: str
    series_one: str
    series_many: str


_PT = PortugalComparisonsCopy(
    title="Portugal",
    intro="Comparações centradas em Portugal, em dois grupos de escala. Cada cartão abre "
          "uma configuração revista no Caderno, onde pode mudar a janela, a seleção e as "
          "restantes definições.",
    action="Abrir no Caderno",
    axis_left="Eixo esquerdo",
    axis_right="Eixo direito",
    window_10a="10 anos",
    window_5a="5 anos",
    window_max="máximo",
    series_one="1 série",
    series_many="{count} séries",
)

_DEFINITIONS = (
    PortugalComparison(
        slug="taxas-juro-credito-depositos",
        title="Taxas de juro, crédito à habitação e depósitos",
        summary="Taxas de juro nominais de referência e saldos de crédito e depósitos das famílias em "
                "Portugal. As taxas estão em percentagem; os saldos, em milhões de euros.",
        caveat="A Euribor é uma taxa de referência da área do euro (composição variável), não "
               "uma taxa portuguesa; a taxa a 10 anos é a rendibilidade de obrigações do Tesouro "
               "português. O crédito e os depósitos são saldos em fim de mês, não fluxos. A "
               "evolução conjunta não estabelece causalidade.",
        groups=(
            PortugalGroup(axis=0, unit="%", multiplier=None, base_year=None, series=(
                "bportugal.euribor_12m.EA",
                "bportugal.pt_10y.PT",
            )),
            PortugalGroup(axis=1, unit="MEUR", multiplier=None, base_year=None, series=(
                "bportugal.credit_housing.PT",
                "bportugal.deposits_households.PT",
            )),
        ),
        frequency="M",
        window="10a",
    ),
    PortugalComparison(
        slug="divida-saldo-pib-per-capita",
        title="Dívida pública, saldo orçamental e PIB per capita",
        summary="O peso da dívida pública bruta e do saldo orçamental no PIB e o PIB per capita "
                "de Portugal, a preços correntes, em valores anuais.",
        caveat="A dívida é um stock bruto e o saldo orçamental é um fluxo anual; ambos são rácios "
               "do PIB. No saldo, valores positivos indicam capacidade líquida de financiamento "
               "e valores negativos indicam défice. O PIB per capita é uma média por habitante, "
               "não o rendimento disponível das famílias. A comparação não estabelece "
               "causalidade.",
        groups=(
            PortugalGroup(axis=0, unit="% GDP", multiplier=None, base_year=None, series=(
                "eurostat.gov_debt_pct_gdp.PT",
                "eurostat.gov_deficit_pct_gdp.PT",
            )),
            PortugalGroup(axis=1, unit="EUR per capita", multiplier=None, base_year=None,
                          series=("eurostat.gdp_per_capita_eur.PT",)),
        ),
        frequency="A",
        window="10a",
    ),
    PortugalComparison(
        slug="comercio-externo-pib-per-capita",
        title="Comércio externo e PIB per capita",
        summary="Exportações e importações de bens e serviços em percentagem do PIB e PIB per "
                "capita de Portugal a preços correntes.",
        caveat="As exportações e importações são fluxos brutos de bens e serviços, não valor "
               "acrescentado; ambos usam o PIB como denominador. O PIB per capita é uma média "
               "por habitante e não uma medida de poder de compra. A comparação não estabelece "
               "causalidade.",
        groups=(
            PortugalGroup(axis=0, unit="% PIB", multiplier=None, base_year=None, series=(
                "worldbank.exports_pct_gdp.PT",
                "worldbank.imports_pct_gdp.PT",
            )),
            PortugalGroup(axis=1, unit="EUR per capita", multiplier=None, base_year=None,
                          series=("eurostat.gdp_per_capita_eur.PT",)),
        ),
        frequency="A",
        window="10a",
    ),
)

_COPY: dict[str, PortugalComparisonsCopy] = {"pt": _PT}


def text(lang: str = "pt") -> PortugalComparisonsCopy:
    """The Portugal section copy in `lang`; an unknown language is a programming error."""
    try:
        return _COPY[lang]
    except KeyError:
        raise MissingText(f"no {lang} Portugal comparison copy") from None


def definitions(lang: str = "pt") -> tuple[PortugalComparison, ...]:
    """The curated configurations in reading order, after copy validation."""
    text(lang)
    return _DEFINITIONS


def window_text(lang: str, code: str) -> str:
    copy = text(lang)
    try:
        return {"10a": copy.window_10a, "5a": copy.window_5a, "max": copy.window_max}[code]
    except KeyError:
        raise MissingText(f"no {lang} Portugal window text for {code!r}") from None


def series_text(lang: str, count: int) -> str:
    copy = text(lang)
    return copy.series_one if count == 1 else copy.series_many.format(count=count)


__all__ = [
    "PortugalComparison",
    "PortugalComparisonsCopy",
    "PortugalGroup",
    "definitions",
    "series_text",
    "text",
    "window_text",
]
