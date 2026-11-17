# Incremento tipografico de 10 por cento

Data: 2026-11-17. Base: `273b14b` em `pipeline-rebuild`. Owner pediu um aumento adicional
moderado sobre o candidato de legibilidade: mais 10 por cento em todas as funcoes de leitura,
incluindo rotulos fixos de SVG/canvas, clamps e a geometria que os acomoda.

## Implementacao

- Publico: raiz `25.5px` -> `28.05px`. Todos os papeis em `rem` crescem 10 por cento sem
  alterar tokens, cores, Carmim, Lato/TeX Gyre Schola ou geometria do fio de prumo.
- Admin: raiz `24px` -> `26.4px`; corpo continua `0.875rem`, agora `23.1px`. Sidebar
  `300px` -> `330px` para manter a mesma largura relativa das etiquetas de navegacao.
- Clamps preferidos: publico `h1 6.9vw -> 7.6vw`, `h2 3.6vw -> 4vw`, valor de figura
  `7.5vw -> 8.25vw`; Admin `h1 3.3vw -> 3.63vw` e titulo do editor `3vw -> 3.3vw`.
- Graficos: ticks SVG e nomes de unidade `.chart-axis-label` `16.5px -> 18.15px`;
  ultimo valor valido SVG `18px -> 19.8px`, tal como o papel sem consumidor
  `.chart-axis-title`. O adapter ECharts usa nomes de eixo a `19.8px` e os restantes papeis
  equivalentes (`18.15`, tooltip `19.8/29.7`). A geometria e a mesma; o tamanho do nome de
  eixo difere entre SVG (`18.15`) e canvas (`19.8`).
- Geometria partilhada: margens `88/30/28/62 -> 97/33/31/68`, eixo duplo `156 -> 172`,
  estimativa de texto `9/5 -> 9.9/5.5`, deslocamentos de rotulos e limiares de colisao
  escalados na mesma proporcao. A geometria partilhada usa os mesmos numeros nos dois
  renderizadores.
- Estreito: piso do SVG sem JavaScript `600x240 -> 660x264`; a search publica passa a
  ocupar uma linha propria abaixo de `900px` (antes de `760px`), porque o campo rotulado
  ampliado deixava de caber ao lado da marca em 768px. Nenhum texto foi reduzido nem
  escondido para recuperar densidade.
- Bundle: `npm ci --prefix tools/charts ...` e `node tools/charts/build.mjs`. Hash novo
  `63e097d47963d48d78cc19008e6e2bac724ff6a20c26591f5a8276a91c91cc3d`, 506603 bytes,
  gzip local 173132. Rebuild repetido devolveu o mesmo hash. A isencao de em dash em
  `tests/test_typography.py` foi reapontada para esse hash revisto.

## Golden ativo

`tests/app/golden/charts/*.svg` foram recapturados apenas para a mudanca de geometria:
9 ficheiros com conteudo mudaram; `cmp_empty.svg` e `line_empty.svg` ficaram iguais. Uma
comparacao programatica de todos os nos de texto (`ElementTree.itertext` mais o texto da
legenda) provou igualdade exata em todos os 11 casos: pontos, titulos, ticks, unidades e
valores publicados nao mudaram. `pre_legibility/` nao foi tocado. `home_code_list.html` e
`home_before_editorial.html` nao mudam (a home nao contem rotulos de grafico e o CSS e
externo). O delta esta descrito em `tests/app/golden/README.md`.

## Testes executados

- `.venv-ci/bin/python -m pytest tests/test_legibility_assets.py tests/app/test_type_increment.py tests/app/test_legibility_review.py -q` -> 18 passed.
- `.venv-ci/bin/python -m pytest tests/app/test_chart_model.py tests/app/test_chart_engine.py tests/app/test_charts.py tests/app/test_legibility_review.py tests/app/test_type_increment.py tests/test_legibility_assets.py tests/test_typography.py -q` -> 77 passed.
- `.venv-ci/bin/python -m pytest tests/app/test_interactive.py tests/app/test_chart_interaction.py tests/app/test_chart_layout.py tests/app/test_home_composition.py tests/app/test_visual_identity.py tests/app/test_country_layout.py -q` -> 55 passed (uma primeira execucao expôs 8px de overflow em 768px na search; corrigido com a linha propria e reexecutado).
- `.venv-ci/bin/python -m pytest tests/app/test_public_ui.py tests/app/test_country_comparisons.py tests/app/test_comparisons.py tests/app/test_notebook.py tests/app/test_cms_home.py tests/app/test_routes.py tests/app/test_reads.py -q` -> 153 passed.
- `.venv-ci/bin/ruff check` nos ficheiros Python alterados -> All checks passed.
- `node --check static/js/prumo-charts.min.js` -> OK.
- Sonda real de browser (temporaria, removida) em 1440 e 320: raiz/corpo `28.05px`,
  nav `26.6475px`, tick SVG `18.15px`, ultimo valor `19.8px`, leitura do grafico
  `25.245px`, cabecalho de tabela `20.757px`. Sem erros de consola.

Nao executado por desenho: suite completa, matriz alargada de browser, fetch de producao,
merge, push e deploy. Esses passos pertencem ao parent.

## Caminhos sob propriedade desta fatia

- `static/css/prumo.css`
- `static/css/admin.css`
- `app/chart_model.py`
- `app/charts.py`
- `tools/charts/src/adapter.js`
- `static/js/prumo-charts.min.js`
- `static/js/prumo-charts.manifest.json`
- `static/js/prumo-charts.NOTICE.txt`
- `tests/test_legibility_assets.py`
- `tests/test_typography.py`
- `tests/app/test_type_increment.py`
- `tests/app/test_legibility_review.py`
- `tests/app/test_chart_model.py`
- `tests/app/golden/README.md`
- `tests/app/golden/charts/cmp_dual.svg`
- `tests/app/golden/charts/cmp_gap.svg`
- `tests/app/golden/charts/cmp_negative.svg`
- `tests/app/golden/charts/cmp_single.svg`
- `tests/app/golden/charts/line_annual.svg`
- `tests/app/golden/charts/line_monthly.svg`
- `tests/app/golden/charts/line_negative.svg`
- `tests/app/golden/charts/line_nonfinite.svg`
- `tests/app/golden/charts/line_single.svg`
- `docs/superpowers/handoff/reports/legibility-release/type-increment.md`

Sem alteracoes a dados, ingestao, migracoes, documentos CMS, autenticacao, edge partilhado,
`AGENTS.md` ou `CLAUDE.md`.

## Riscos e verificacao pendente

- O tamanho efetivo do rotulo SVG continua a depender da largura renderizada do grafico;
  o piso de 660px evita encolher o SVG sem JavaScript em ecras estreitos.
- A sidebar Admin de 330px entre 1025px e 1200px deve ser confirmada na matriz do parent.
- O alinhamento ponto a ponto do canvas depende do `containLabel` do ECharts; as margens
  foram igualadas ao modelo, mas a matriz de browser do parent deve confirmar a sobreposicao.
- O hash do bundle mudou de proposito; qualquer rebuild futuro exige nova revisao da
  isencao em `tests/test_typography.py`.
