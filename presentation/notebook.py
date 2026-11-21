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
    chart_add_label: str
    chart_group_legend: str
    chart_group_note: str
    chart_scale_legend: str
    chart_scale_shared: str
    chart_scale_dual: str
    chart_window_legend: str
    chart_window_1a: str
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
    chart_dual_one_group: str
    chart_dual_many_groups: str
    chart_axis_groups_note: str
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
    chart_frequency_legend: str
    chart_frequency_original: str
    chart_frequency_annual: str
    chart_transform_legend: str
    chart_transform_original: str
    chart_transform_base100: str
    chart_transform_pp: str
    chart_base_label: str
    chart_base_placeholder: str
    chart_analysis_note: str
    chart_period_mixed: str
    chart_period_calendar: str
    chart_period_annual: str
    chart_missing_cell: str
    chart_calendar_alignment: str
    chart_calendar_window: str
    chart_calendar_excluded_one: str
    chart_calendar_excluded_many: str
    chart_interval_analysis: str
    chart_transform_annual: str
    chart_transform_shared: str
    chart_annual_unsupported: str
    chart_base100_unsupported: str
    chart_pp_unsupported: str
    chart_base_missing: str
    chart_base_not_positive: str
    chart_method_unavailable: str
    chart_analysis_annual: str
    chart_analysis_rounding: str
    chart_analysis_calculated: str
    chart_analysis_hicp: str
    chart_analysis_unemployment: str
    chart_analysis_year_end: str
    chart_analysis_native: str
    chart_analysis_methods: str
    chart_analysis_dropped: str
    chart_analysis_dropped_one: str
    chart_annual_alignment: str
    chart_formula_base100: str
    chart_formula_pp: str
    chart_base_auto: str
    chart_base_explicit: str
    chart_evidence_summary: str
    chart_evidence_heading: str
    chart_evidence_method: str
    chart_evidence_formula: str
    chart_evidence_base: str
    chart_evidence_rounding: str
    chart_evidence_source_unit: str
    chart_evidence_chart_unit: str
    chart_evidence_output: str
    chart_evidence_output_original: str
    chart_evidence_inputs: str
    chart_evidence_latest: str
    chart_evidence_latest_native: str
    chart_evidence_base_output: str
    chart_evidence_calculated: str
    chart_evidence_note: str
    chart_evidence_note_native: str
    chart_evidence_series_link: str
    chart_provenance_summary_own: str
    chart_provenance_heading_own: str
    card_chart_drawn_own: str
    card_chart_excluded_own: str
    chart_cell_period: str
    chart_calculated_badge: str
    chart_method_native: str
    chart_method_mean: str
    chart_method_year_end: str
    chart_frequency_annual_computed: str
    chart_unit_base100: str
    chart_unit_pp: str


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
    chart_lede="Compare as séries escolhidas num só gráfico. A escala, a janela, a frequência, a "
               "transformação e a base ficam guardadas nesta ligação.",
    chart_period_label="Último período comum",
    chart_state_off="Gráfico desativado",
    chart_state_empty="Sem séries escolhidas para o gráfico",
    chart_state_choose="Escolha as séries do gráfico",
    chart_state_unavailable="Gráfico indisponível",
    chart_settings_summary="Definições do gráfico",
    chart_configure_label="Configurar",
    chart_add_label="Acrescentar",
    chart_group_legend="Séries no gráfico (até seis)",
    chart_group_note="Marque até seis séries. Sem nenhuma marcada, o gráfico fica vazio; não "
                     "escolhemos séries por si.",
    chart_scale_legend="Escala",
    chart_scale_shared="Escala comum",
    chart_scale_dual="Dois eixos",
    chart_window_legend="Janela temporal",
    chart_window_1a="1 ano",
    chart_window_10a="10 anos",
    chart_window_5a="5 anos",
    chart_window_max="Máximo",
    chart_day_label="Dia UTC (apenas para séries de intervalos)",
    chart_submit="Atualizar gráfico",
    chart_settings_note="O gráfico usa os valores publicados. Quando escolhe uma vista anual ou "
                        "uma transformação, os valores calculados são assinalados e explicados. "
                        "Não há interpolação nem valores inventados.",
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
    chart_dual_one_group="Todas as séries escolhidas partilham a mesma unidade, multiplicador e "
                         "base. Use a escala comum para as desenhar num só eixo.",
    chart_dual_many_groups="A escala de dois eixos admite no máximo dois grupos de unidade, "
                           "multiplicador e base. Escolha um subconjunto que forme dois grupos "
                           "ou aplique uma transformação com escala comum.",
    chart_axis_groups_note="Eixos deste gráfico, na ordem da primeira série de cada grupo:",
    chart_mixed_frequency="As séries escolhidas têm frequências diferentes. Um gráfico conjunto "
                          "exige a mesma frequência.",
    chart_mixed_scale="As séries escolhidas não partilham a mesma unidade, multiplicador e base. "
                      "Use a escala de dois eixos ou escolha séries comparáveis.",
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
    chart_frequency_legend="Frequência",
    chart_frequency_original="Original",
    chart_frequency_annual="Anual",
    chart_transform_legend="Transformação",
    chart_transform_original="Original",
    chart_transform_base100="Índice base 100",
    chart_transform_pp="Pontos percentuais",
    chart_base_label="Ano de base (opcional, automático)",
    chart_base_placeholder="automático",
    chart_analysis_note="As transformações exigem frequência anual e escala comum.",
    chart_period_mixed="Últimos períodos por série",
    chart_period_calendar="Última posição no calendário",
    chart_period_annual="Último período anual",
    chart_missing_cell="sem observação nesta posição temporal",
    chart_calendar_alignment="A posição de cada linha é um dia de início real no calendário, "
                             "uma convenção de apresentação e não a data de publicação nem de "
                             "medição. Cada série mantém o seu período nativo; uma célula sem "
                             "observação não é zero nem uma interpolação. Totais anuais e "
                             "trimestrais não são diretamente equivalentes.",
    chart_calendar_window="Janela: {window}, de {first} a {last}, medida pelo calendário real e "
                          "ancorada na observação finita mais recente.",
    chart_calendar_excluded_one="1 observação de {label} sem valor numérico ou data reconhecida "
                                "fica fora do calendário e da tabela.",
    chart_calendar_excluded_many="{count} observações de {label} sem valor numérico ou data "
                                  "reconhecida ficam fora do calendário e da tabela.",
    chart_interval_analysis="As séries de intervalos de 15 minutos só podem ser comparadas entre "
                            "si, no mesmo dia UTC, e não podem ser anuais nem transformadas.",
    chart_transform_annual="As transformações exigem a frequência anual. Mude a frequência para "
                           "Anual ou volte à transformação original.",
    chart_transform_shared="As transformações usam uma escala comum, porque todas as séries "
                           "passam a partilhar a mesma unidade. Não é possível usar dois eixos.",
    chart_annual_unsupported="Não há um método anual revisto para uma das séries escolhidas. "
                             "Mantenha a frequência original ou escolha outra série.",
    chart_base100_unsupported="O índice base 100 só está definido para séries de nível revistas, "
                              "como o PIB por habitante. Não se aplica a taxas nem a "
                              "percentagens.",
    chart_pp_unsupported="Os pontos percentuais só estão definidos para séries de taxa revistas, "
                         "como a inflação homóloga, o desemprego e a Euribor.",
    chart_base_missing="O ano de base escolhido não existe em todas as séries escolhidas. "
                       "Escolha outro ano ou deixe o campo vazio para a escolha automática.",
    chart_base_not_positive="O índice base 100 exige um valor de base positivo em todas as "
                            "séries.",
    chart_method_unavailable="Não foi possível aplicar o método anual a uma das séries "
                             "escolhidas. O gráfico fica indisponível; as séries elegíveis "
                             "continuam no caderno.",
    chart_analysis_annual="Vista anual calculada a partir do histórico completo.",
    chart_analysis_rounding="Os valores calculados usam aritmética decimal e arredondamento "
                            "half-even a seis casas decimais; os valores originais não são "
                            "arredondados.",
    chart_analysis_calculated="Os valores assinalados como calculados são vistas analíticas do "
                              "Prumo, não observações verificadas pela fonte.",
    chart_analysis_hicp="A média anual calculada de doze taxas homólogas mensais não é a taxa "
                        "de inflação anual oficial.",
    chart_analysis_unemployment="A média anual calculada de doze taxas mensais de desemprego é "
                                "não ponderada e não é a estimativa anual oficial.",
    chart_analysis_year_end="O valor de dezembro é uma vista calculada e exige um ano mensal "
                            "completo.",
    chart_analysis_native="Os valores anuais nativos mantêm-se observações originais.",
    chart_analysis_methods="Métodos por série: {parts}.",
    chart_analysis_dropped="{label}: {count} anos incompletos excluídos ({years}).",
    chart_analysis_dropped_one="{label}: 1 ano incompleto excluído ({years}).",
    chart_annual_alignment="Anos comuns completos: {count}, de {first} a {last}.",
    chart_formula_base100="100 × valor ÷ valor do ano de base",
    chart_formula_pp="valor − valor do ano de base",
    chart_base_auto="automático, primeiro ano comum na janela",
    chart_base_explicit="explícito",
    chart_evidence_summary="Ver entradas originais e proveniência",
    chart_evidence_heading="Entradas originais",
    chart_evidence_method="Método",
    chart_evidence_formula="Fórmula",
    chart_evidence_base="Ano de base",
    chart_evidence_rounding="Arredondamento",
    chart_evidence_source_unit="Unidade da fonte",
    chart_evidence_chart_unit="Unidade do gráfico",
    chart_evidence_output="Valor calculado",
    chart_evidence_output_original="Valor original",
    chart_evidence_inputs="Entradas originais",
    chart_evidence_latest="Último valor calculado",
    chart_evidence_latest_native="Último valor original",
    chart_evidence_base_output="Valor de base",
    chart_evidence_calculated="calculado",
    chart_evidence_note="A verificação matemática do valor calculado é independente da "
                        "verificação da fonte dos valores originais.",
    chart_evidence_note_native="Esta linha mantém o valor anual original da fonte; o Prumo "
                              "não o transformou.",
    chart_evidence_series_link="Abrir série original",
    chart_provenance_summary_own="Ver proveniência dos períodos originais",
    chart_provenance_heading_own="Períodos originais por série",
    card_chart_drawn_own="No gráfico, último período da série: {period}.",
    card_chart_excluded_own="Fora do gráfico.",
    chart_cell_period="Período original",
    chart_calculated_badge="calculado",
    chart_method_native="valor anual original",
    chart_method_mean="média aritmética de doze valores mensais",
    chart_method_year_end="valor de dezembro, com ano mensal completo",
    chart_frequency_annual_computed="anual calculado a partir de valores mensais",
    chart_unit_base100="índice (base {base}=100)",
    chart_unit_pp="p.p.",
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
