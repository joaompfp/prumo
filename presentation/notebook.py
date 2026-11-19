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
    status_note: str
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
    share_hint: str
    results_col_series: str
    results_col_value: str
    results_col_period: str
    results_col_source: str
    results_col_fetched: str
    results_col_notebook: str
    chart_heading: str
    chart_lede: str
    chart_period_label: str
    chart_state_off: str
    chart_state_empty: str
    chart_state_choose: str
    chart_state_unavailable: str
    chart_settings_summary: str
    chart_configure_label: str
    chart_group_legend: str
    chart_group_note: str
    chart_scale_legend: str
    chart_scale_shared: str
    chart_scale_dual: str
    chart_window_legend: str
    chart_window_10a: str
    chart_window_5a: str
    chart_window_max: str
    chart_day_label: str
    chart_submit: str
    chart_settings_note: str
    chart_off: str
    chart_activate: str
    chart_deactivate: str
    chart_empty_selection: str
    chart_empty_group: str
    chart_choose_many: str
    chart_unavailable_ineligible: str
    chart_unavailable_side: str
    chart_unavailable_no_eligible: str
    chart_dual_count: str
    chart_mixed_frequency: str
    chart_mixed_scale: str
    chart_duplicate_labels: str
    chart_no_common: str
    chart_no_day: str
    chart_day_unavailable: str
    chart_no_draw: str
    chart_comparison_note: str
    chart_table_summary: str
    chart_provenance_summary: str
    chart_provenance_heading: str
    chart_definition_summary: str
    chart_meta_source: str
    chart_meta_unit: str
    chart_meta_frequency: str
    chart_meta_geography: str
    chart_meta_adjustment: str
    chart_meta_no_adjustment: str
    chart_meta_base: str
    chart_meta_period: str
    chart_meta_value: str
    chart_meta_status: str
    chart_meta_fetched: str
    chart_meta_run: str
    chart_meta_sha: str
    chart_meta_licence: str
    chart_meta_attribution: str
    chart_meta_terms: str
    chart_join: str
    chart_unavailable_side_label: str
    chart_unavailable_mark: str
    chart_window_note: str
    chart_day_note: str
    chart_common_one: str
    chart_common_many: str
    chart_gap_one: str
    chart_gap_many: str
    chart_excluded: str
    chart_unparsed_one: str
    chart_unparsed_many: str
    chart_all_common: str
    chart_one_point: str
    chart_table_period: str
    chart_provenance_missing: str
    help_summary: str
    card_chart_drawn: str
    card_chart_excluded: str
    card_chart_off: str
    card_chart_empty: str
    card_chart_choose: str
    card_chart_unavailable: str


_PT = NotebookCopy(
    title="Caderno de indicadores - Prumo",
    nav_label="Caderno",
    heading="Caderno de indicadores",
    lede="Reúna até 12 indicadores numa página. Guarde o endereço para retomar a seleção "
         "ou partilhá-la, sem criar uma conta.",
    status_note="Seleção partilhável.",
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
    share_hint="A ligação limpa guarda a seleção e as definições do gráfico, sem o termo de pesquisa.",
    results_col_series="Série",
    results_col_value="Último valor",
    results_col_period="Período",
    results_col_source="Fonte",
    results_col_fetched="Recolhido",
    results_col_notebook="Caderno",
    chart_heading="Evolução conjunta",
    chart_lede="Compare as séries escolhidas num só gráfico. A escala e a janela ficam guardadas "
               "nesta ligação.",
    chart_period_label="Último período comum",
    chart_state_off="Gráfico desativado",
    chart_state_empty="Sem séries escolhidas para o gráfico",
    chart_state_choose="Escolha as séries do gráfico",
    chart_state_unavailable="Gráfico indisponível",
    chart_settings_summary="Definições do gráfico",
    chart_configure_label="Configurar",
    chart_group_legend="Séries no gráfico (até seis)",
    chart_group_note="Marque até seis séries. Sem nenhuma marcada, o gráfico fica vazio; não "
                     "escolhemos séries por si.",
    chart_scale_legend="Escala",
    chart_scale_shared="Escala comum",
    chart_scale_dual="Dois eixos",
    chart_window_legend="Janela temporal",
    chart_window_10a="10 anos",
    chart_window_5a="5 anos",
    chart_window_max="Máximo",
    chart_day_label="Dia UTC (apenas para séries de intervalos)",
    chart_submit="Atualizar gráfico",
    chart_settings_note="O gráfico usa os valores publicados. Não há interpolação, "
                        "reagrupamento, normalização nem valores inventados.",
    chart_off="O gráfico está desativado nesta ligação.",
    chart_activate="Ativar gráfico",
    chart_deactivate="Desativar gráfico",
    chart_empty_selection="Escolha séries no caderno para as comparar neste gráfico.",
    chart_empty_group="Não há séries escolhidas para o gráfico. Marque até seis séries e "
                      "atualize.",
    chart_choose_many="O caderno tem mais de seis séries elegíveis. Escolha até seis para o "
                      "gráfico; nenhuma é escolhida automaticamente.",
    chart_unavailable_ineligible="Uma das séries escolhidas já não pode ser mostrada. O gráfico "
                                 "fica indisponível; as séries elegíveis continuam no caderno.",
    chart_unavailable_side="Uma série escolhida já não tem os dados públicos necessários. O "
                           "gráfico fica indisponível; as séries elegíveis continuam no caderno.",
    chart_unavailable_no_eligible="Nenhuma das séries desta ligação pode ser mostrada no gráfico "
                                  "neste momento.",
    chart_dual_count="A escala de dois eixos exige exactamente duas séries. Escolha duas séries "
                     "ou use a escala comum.",
    chart_mixed_frequency="As séries escolhidas têm frequências diferentes. Um gráfico conjunto "
                          "exige a mesma frequência.",
    chart_mixed_scale="As séries escolhidas não partilham a mesma unidade, multiplicador e base. "
                      "Use a escala de dois eixos com exactamente duas séries ou escolha séries "
                      "comparáveis.",
    chart_duplicate_labels="As séries escolhidas não se distinguem pelo título e pela fonte. "
                           "Escolha um conjunto diferente.",
    chart_no_common="As séries escolhidas não têm períodos comuns com valores numéricos.",
    chart_no_day="Nenhum dia UTC comum tem pelo menos dois períodos com valores numéricos.",
    chart_day_unavailable="O dia pedido não tem valores numéricos comuns para todas as séries. "
                          "Escolha outro dia.",
    chart_no_draw="Não foi possível preparar o gráfico com estes dados.",
    chart_comparison_note="Comparar curvas no mesmo gráfico não estabelece uma relação de causa.",
    chart_table_summary="Ver tabela completa do gráfico",
    chart_provenance_summary="Ver proveniência do último período comum",
    chart_provenance_heading="Último período comum",
    chart_meta_source="Fonte",
    chart_meta_unit="Unidade",
    chart_meta_frequency="Frequência",
    chart_meta_geography="Geografia",
    chart_meta_adjustment="Ajustamento",
    chart_meta_no_adjustment="sem ajustamento sazonal",
    chart_meta_base="Base",
    chart_meta_period="Período",
    chart_meta_value="Valor",
    chart_meta_status="Estado",
    chart_meta_fetched="Recolhido",
    chart_meta_run="Execução",
    chart_meta_sha="Ficheiro arquivado",
    chart_meta_licence="Licença",
    chart_meta_attribution="Atribuição",
    chart_meta_terms="termos",
    chart_join=" e ",
    chart_unavailable_side_label="Série indisponível",
    chart_unavailable_mark="indisponível",
    chart_window_note="Janela: {window}, de {first} a {last}, ancorada no período mais recente "
                      "comum.",
    chart_day_note="Dia UTC: {day}. Cada ponto é o valor publicado, sem agregação.",
    chart_common_one="1 período comum, em {first}.",
    chart_common_many="{count} períodos comuns, de {first} a {last}.",
    chart_gap_one="1 período de {label}",
    chart_gap_many="{count} períodos de {label}",
    chart_excluded="Ficam de fora {parts}, por faltar pelo menos uma das outras séries em cada "
                   "período.",
    chart_unparsed_one="1 período comum sem valor numérico ou data reconhecida fica fora do "
                       "gráfico e da tabela.",
    chart_unparsed_many="{count} períodos comuns sem valor numérico ou data reconhecida ficam "
                        "fora do gráfico e da tabela.",
    chart_all_common="Todas as séries cobrem exactamente os mesmos períodos.",
    chart_one_point="Este dia só tem um período comum. O gráfico mostra um ponto, não uma linha.",
    chart_table_period="Período",
    chart_provenance_missing="Sem registo de proveniência para este período.",
    chart_definition_summary="Definições e fontes das séries",
    help_summary="Sobre este caderno e o gráfico",
    card_chart_drawn="No gráfico, no período comum: {period}.",
    card_chart_excluded="Fora do gráfico. O período comum é {period}.",
    card_chart_off="Fora do gráfico. Gráfico desativado.",
    card_chart_empty="Fora do gráfico. Sem séries escolhidas.",
    card_chart_choose="Fora do gráfico. Escolha até seis séries nas definições.",
    card_chart_unavailable="Fora do gráfico. Gráfico indisponível.",
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
