"""Reader-facing copy for the indicator notebook.

The notebook is a public reading tool, not a data product: its selection lives only in the
address. These strings keep that promise explicit, so no template has to invent a privacy or
snapshot claim of its own.
"""
from dataclasses import dataclass

from presentation import MissingText


@dataclass(frozen=True)
class NotebookCopy:
    title: str
    nav_label: str
    heading: str
    lede: str
    public_link_note: str
    not_snapshot_note: str
    cards_heading: str
    empty: str
    skipped_one: str
    skipped_many: str
    search_heading: str
    search_label: str
    search_placeholder: str
    search_button: str
    search_prompt: str
    search_empty: str
    search_note: str
    results_one: str
    results_many: str
    add_label: str
    remove_label: str
    in_notebook_label: str
    limit_reached: str
    clear_label: str
    canonical_heading: str
    canonical_label: str
    canonical_note: str
    detail_label: str
    fetched_prefix: str
    series_action: str
    comparison_action: str


_PT = NotebookCopy(
    title="Caderno de indicadores - Prumo",
    nav_label="Caderno",
    heading="Caderno de indicadores",
    lede="Reúna até 12 indicadores numa página. Guarde o endereço para retomar a seleção "
         "ou partilhá-la, sem criar uma conta.",
    public_link_note="Qualquer pessoa com esta ligação pode abrir a seleção.",
    not_snapshot_note="A seleção não é um retrato histórico. Cada abertura mostra os valores atuais.",
    cards_heading="Séries no caderno",
    empty="O caderno está vazio. Pesquise uma série e acrescente-a. A seleção fica guardada "
          "nesta ligação.",
    skipped_one="1 série desta ligação já não pode ser mostrada e foi omitida. O caderno mostra "
                "apenas séries publicadas neste momento.",
    skipped_many="{count} séries desta ligação já não podem ser mostradas e foram omitidas. O "
                  "caderno mostra apenas séries publicadas neste momento.",
    search_heading="Acrescentar séries",
    search_label="Pesquisar séries",
    search_placeholder="ex.: desemprego, inflação, INE",
    search_button="Pesquisar",
    search_prompt="Pesquise para encontrar séries e acrescentá-las ao caderno.",
    search_empty="Sem resultados para «{query}». Tente uma palavra mais geral.",
    search_note="Só aparecem séries que podem ser publicadas neste momento.",
    results_one="1 resultado.",
    results_many="{count} resultados.",
    add_label="Acrescentar ao caderno",
    remove_label="Remover do caderno",
    in_notebook_label="Já no caderno",
    limit_reached="O caderno tem 12 séries, o máximo. Remova uma para acrescentar outra.",
    clear_label="Limpar seleção",
    canonical_heading="Guardar esta seleção",
    canonical_label="Ligação limpa para guardar ou partilhar",
    canonical_note="A ligação limpa inclui a seleção e não inclui o termo de pesquisa.",
    detail_label="Série e proveniência",
    fetched_prefix="recolhido a",
    series_action="Criar caderno com esta série",
    comparison_action="Criar caderno com estas duas séries",
)

_COPY: dict[str, NotebookCopy] = {"pt": _PT}


def text(lang: str = "pt") -> NotebookCopy:
    """The notebook copy in `lang`; an unknown language is a programming error."""
    try:
        return _COPY[lang]
    except KeyError:
        raise MissingText(f"no {lang} notebook copy") from None


def skipped_text(lang: str, count: int) -> str:
    copy = text(lang)
    return copy.skipped_one if count == 1 else copy.skipped_many.format(count=count)


def search_empty_text(lang: str, query: str) -> str:
    return text(lang).search_empty.format(query=query)


def results_text(lang: str, count: int) -> str:
    copy = text(lang)
    return copy.results_one if count == 1 else copy.results_many.format(count=count)


__all__ = ["NotebookCopy", "text", "skipped_text", "search_empty_text", "results_text"]
