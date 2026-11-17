# Revisão independente de qualidade: incremento tipográfico

Data: 2026-11-17. Commit revisto: `3a88b1f` (`feat: increase Prumo type scale by ten
percent`), base `273b14b`, branch `pipeline-rebuild`. Servidor de QA usado nas sondagens:
`http://127.0.0.1:8124` (cópia de produção, com `/dados` e `/dados/admin`). Não alterei
ficheiros de aplicação, testes, CMS ou produção, não fiz commit nem push. Este relatório é a
única escrita no repositório.

## Veredito

**APPROVED**. Não encontrei regressões bloqueantes. O incremento é coerente com o âmbito
aprovado, os rótulos e os dados publicados não mudaram, o bundle é reproduzível e as
sondagens de layout não encontraram overflow horizontal nem clipping novo em Admin entre
`1025px` e `1440px` ou no público entre `320px` e `1440px`. Os achados abaixo são reais mas
não bloqueantes: dois são comportamentos pré-existentes que o incremento apenas torna
marginalmente mais visíveis, um é uma regressão cosmética numa faixa estreita de viewport e
os restantes são higiene de documentação/testes.

## Evidência executada

- `.venv-ci/bin/python -m pytest tests/app/test_type_increment.py
  tests/app/test_legibility_review.py tests/test_legibility_assets.py
  tests/app/test_chart_model.py -q` -> **34 passed**, 1 warning.
- `.venv-ci/bin/ruff check` nos Python alterados -> **All checks passed**.
- `node --check static/js/prumo-charts.min.js` -> **OK**; `git diff --check 273b14b..3a88b1f`
  -> sem erros.
- Rebuild do bundle em scratch, com as mesmas opções de `tools/charts/build.mjs`:
  `506603` bytes e `sha256 63e097d47963d48d78cc19008e6e2bac724ff6a20c26591f5a8276a91c91cc3d`,
  byte a byte igual ao ficheiro commitado. `gzip` Node nível 9 com `mtime=0` -> `173132`
  bytes, igual ao manifesto e ao NOTICE.
- Comparação programática dos 9 SVGs golden alterados entre `273b14b` e `3a88b1f`: todos os
  nós `text` e o texto da legenda são exatamente iguais; só mudaram coordenadas e atributos
  de geometria. `cmp_empty.svg` e `line_empty.svg` não aparecem no diff.
- Sondagens de browser reais com Playwright/Chromium sobre a cópia de QA, com JavaScript
  ligado e desligado. Público: `/dados`, `/dados/series/ine.hicp_yoy.PT`, `/dados/comparar`,
  `/dados/pesquisa` em `1440, 1100, 901, 900, 899, 800, 768, 761, 760, 600, 480, 390, 360,
  320px`. Admin: `/dados/admin`, `/series`, `/cms`, `/cms/home`, `/queue` em `1440, 1280,
  1200, 1100, 1025, 1024, 900, 768, 480, 360px`. Em todos os casos
  `documentElement.scrollWidth - clientWidth == 0`; nenhum erro de consola.

## Qualidade por eixo

### Correção e contrato

- Raízes confirmadas no browser: público `28.05px`, Admin `26.4px`, corpo Admin `23.1px`.
  Clamps públicos e de Admin medidos em `1440/1280/1100/1025px` seguem a proporção esperada
  (por exemplo, `h1` Admin `50.16 -> 46.464 -> 39.93 -> 39.6px`).
- O modelo SVG e o adapter continuam a partilhar a mesma geometria: `LEFT/RIGHT/TOP/BOTTOM`
  `97/33/31/68`, `RIGHT_DUAL 172`, `nameGap 13 * scale`. O teste novo fixa os dois lados.
- O bundle commitado contém os papéis novos (`fontSize: 18.15` duas vezes, `fontSize: 19.8`
  duas vezes, `lineHeight: 29.7`) e não contém os valores antigos.
- Não há alterações a dados, ingestão, migrações, CMS, autenticação ou templates públicos.

### Gráficos: gutter e ticks

- Com JavaScript desligado, o SVG a `1440px` renderiza a `1176px` (escala `1.3364`), pelo que
  o tick de `18.15` unidades aparece a cerca de `24.25px` reais. O eixo direito do caso dual
  começa em `x=719` e termina em `783`, dentro do viewBox `880`. O último valor termina em
  `x=838`, também dentro.
- O gutter esquerdo aguenta bem valores até sete dígitos. Para valores publicados de oito ou
  mais dígitos há clipping residual no fallback SVG, descrito no achado 1.
- Com JavaScript desligado a `600px`, `480px`, `390px` e `320px`, o `.chart-scroll` mantém
  `scrollWidth=660` e a página continua sem overflow (`sw=660`, `cw` entre `552px` e `284px`);
  a `760px` o SVG encolhe para `712px` e cabe sem scroll. O piso novo de `660x264` cumpre o
  objetivo e não empurra a página.

### Responsivo público e Admin

- A search pública passa para a linha 3 abaixo de `900px` e volta a ficar ao lado da marca em
  `901px`. Medições: em `900px` ocupa `852px` (input `688.6px`, botão `163.4px`); em `320px`
  ocupa `284px` e empilha input e botão. Não há overflow em nenhum dos dois lados do
  breakpoint.
- Em `901px` a search ainda cabe ao lado da marca (marca `203.7px`, search `506.4px`, folga de
  `126.9px`). O novo breakpoint não cria uma faixa intermédia partida.
- Admin entre `1025px` e `1440px`: sidebar `330px`, main `695px` a `1110px`, sem overflow. Em
  `1024px` a sidebar passa a bloco e o `bo-menu` aparece, como antes. Formulários passam de 4
  para 3, 2 ou 1 colunas sem overflow. O `h1` máximo é `50.16px` e o título do editor
  `40.92px`.
- Controlos nativos em `1025px`: checkbox `33x33px`, alinhado com a primeira linha da
  etiqueta; `select` com `73.9px` de altura, texto `23.1px`, seta `16x12` visível e centrada;
  botões e inputs sem texto cortado. O placeholder do filtro de séries fica truncado, mas
  isso já acontecia antes do incremento (ver achado 5).

### Legibilidade e manutenção

- A alteração é pequena e localizada: CSS de tipo, geometria do modelo, adapter e testes de
  pins. Não introduz dependências, caminhos de erro, estado ou código morto novo.
- O padrão de constantes duplicadas entre `app/chart_model.py` e `tools/charts/src/adapter.js`
  é aceitável porque o teste `test_chart_gutters_and_adapter_grid_share_the_scaled_geometry`
  falha se divergirem e o bundle é reconstruído a partir do adapter. O rebuild independente
  prova que o ficheiro commitado corresponde à fonte.
- Os testes novos são pins estáticos de release. São adequados para esta fatia, mas exigem
  atualização deliberada em qualquer incremento futuro; não os considerei um contrato
  permanente de design.

## Achados não bloqueantes

### 1. Fallback SVG ainda corta o primeiro dígito de ticks com oito ou mais dígitos

`app/chart_model.py:33-45` estima `9.9` unidades por dígito e `5.5` por espaço, e
`app/charts.py:61` coloca o texto em `model.left - 11`. Em valores reais:

- `ine.population.PT`, tick `10 000 000`: `getBBox().x = -1.49` unidades.
- `ine.exports_monthly.PT`, tick `10 000 000 000`: `getBBox().x = -2.71` unidades.

O clipping é de cerca de 2 a 3 unidades SVG (cerca de 2 a 4px na largura renderizada de
`1176px`), visível apenas no fallback sem JavaScript; com JavaScript o ECharts usa
`containLabel` e não corta. A simulação da geometria anterior dá aproximadamente `-0.99` e
`-1.92`, portanto o defeito já existia e o incremento apenas o agravou em menos de uma
unidade. O comentário em `app/chart_model.py:26-28` afirma que o gutter aguenta sem clipping,
o que não é verdade para estes dois valores. Não considero bloqueante por ser um defeito
pré-existente, restrito ao fallback e de amplitude sub-pixel a poucos pixels, mas deve ser
corrigido numa fatia própria, por exemplo alargando a estimativa para a largura real do Lato
tabular ou aumentando a folga de `13` para um valor que cubra os 6% de subestimação.

### 2. Valor principal de "Valor mais recente" passa de duas para três linhas em 1101-1139px

`static/css/prumo.css:309` mantém a coluna de metadados em `minmax(18rem, 24rem)`. Como a
raiz cresceu 10%, o máximo passou de `612px` para `673.2px` e a coluna do valor encolheu de
`317px` para `255.8px` a `1101px`. Com `font-size` de `89.76px` (`prumo.css:322-325`) e
`overflow-wrap: anywhere`, `11 424 031 número` passa a três linhas, com o dígito final
isolado na segunda linha e a unidade na terceira. Em `1140px` já volta a duas linhas. A
simulação da raiz anterior (`25.5px`, valor `81.6px`) dá `317px` e duas linhas.

É uma regressão cosmética real, mas numa faixa estreita de viewport, sem clipping, sem
overflow e sem alteração do valor publicado. Antes do incremento o número já quebrava a meio
do grupo (`11 424 0` / `31 número`), pelo que a classe de defeito não nasce aqui. Não bloqueia
a release; fica como follow-up recomendado (mover o breakpoint de `1100px` para cerca de
`1200px`, limitar a coluna de metadados ou tornar o valor atómico com uma fonte responsiva).

### 3. Nome do eixo no canvas corta no topo em viewports estreitos

`tools/charts/src/adapter.js:252` escala `top: 31 * scale` com a largura, mas
`adapter.js:168` mantém `fontSize: 19.8` em píxeis CSS. Em `480px` e `320px` o nome do eixo
(`número`) aparece cortado no topo do canvas; em `768px` e `1024px` está completo. O mesmo
acontecia antes: a geometria antiga `28 * scale` com `fontSize: 18` e `nameGap: 12 * scale`
era proporcionalmente igual ou ligeiramente pior. Não é uma regressão introduzida por este
diff, mas é um defeito visível na matriz móvel. Fica como follow-up: usar um piso de topo em
píxeis CSS quando os rótulos são píxeis CSS, em vez de escalar o gutter com a largura.

### 4. Documentação e comentários ainda descrevem 19.8 para nomes de eixo SVG

`tests/app/golden/README.md:4-5` e
`docs/superpowers/handoff/reports/legibility-release/type-increment.md:15-16` dizem que os
nomes de eixo passaram de `18` para `19.8px`. No SVG, os nomes de unidade usam
`.chart-axis-label` a `18.15px` (`static/css/prumo.css:561`, `app/charts.py:140,145`);
`.chart-axis-title` a `19.8px` (`prumo.css:338`) não tem consumidor. O canvas usa `19.8` em
`adapter.js:168`. A afirmação "o SVG e o canvas usam os mesmos números" é verdadeira para a
geometria, não para o tamanho do nome do eixo. Confirmo a observação 2 do `spec-review.md`;
não é uma omissão funcional, porque ambos os papéis cresceram 10% face à base aceite.

### 5. Comentários de testes com valores antigos e placeholder Admin truncado

`tests/test_legibility_assets.py:65-70` e `:88-89` ainda mostram equivalências em px da raiz
antiga (`nav 16.15 -> 24.225`, `table th 10.4 -> 15.6`, etc.). Com `28.05/26.4` os valores
atuais são `26.6475`, `17.16`, `15.312`, etc. Não afeta o teste, mas engana a próxima revisão.
Confirmo a observação 1 do `spec-review.md`.

Em `backoffice/templates/series_list.html:49`, o placeholder
`id, indicador ou código nativo` aparece truncado no filtro a `1025px` (input de `175.3px`,
fonte `23.1px`, visível até `id, indicad`). O campo e a etiqueta `Pesquisar` continuam
utilizáveis e o truncamento já existia com a raiz anterior, apenas com mais caracteres
visíveis. Não bloqueia.

## Limites desta revisão

Não repeti a suite completa, a matriz alargada de browser, a cópia de produção, o CMS
autenticado nem o fetch de produção; esses passos pertencem ao parent. Também não auditei
outra funcionalidade antiga nem ingestão. `qa_server.py` e `online_snapshot.py` continuam
untracked na pasta do relatório e não foram alterados por mim.

**Veredito final: APPROVED.**
