# Revisão final de âmbito limitado: correções de clipping tipográfico

Data: 2026-11-17. Commit revisto: `42c581f` (`fix: close typography clipping and figure
wrapping findings`), base `3a88b1f` (`feat: increase Prumo type scale by ten percent`),
branch `pipeline-rebuild`. Revisão independente e read-only do diff `3a88b1f..42c581f`.
Não alterei runtime, testes, assets, bundle, CMS ou produção, não reconstruí o bundle e não
fiz commit. Este ficheiro é a única escrita no repositório.

## Veredito

**PASS / APPROVED.** Não encontrei bloqueadores. Os achados visuais da revisão anterior
(gutter SVG, topo do canvas e largura da figura) e a quebra do `h1` a 390px estão fechados;
a documentação e os comentários de teste foram corrigidos. O placeholder Admin truncado que
o achado 5 já classificou como pré-existente e não bloqueante continua fora deste diff.
O hash, os bytes e o manifesto do bundle coincidem com o ficheiro commitado.

## Evidência por achado

### 1. Gutter esquerdo do SVG com largura real do Lato

`app/chart_model.py:33-53` substitui a estimativa de `9.9` por dígito e `5.5` por separador
por uma estimativa conservadora: `10.6` para dígitos e sinais, `4.8` para separadores e
pontuação, mais `15` unidades de folga em `_left_gutter`. O texto dos ticks continua
byte a byte igual; só a geometria de margem muda. O renderer mantém a âncora em
`model.left - 11` (`app/charts.py:61`).

Com os valores medidos no Lato servido a 18.15 unidades, a folga à esquerda fica positiva:

| Tick | Gutter novo | x do texto | Largura medida | Folga |
| --- | ---: | ---: | ---: | ---: |
| `10 000 000` | 109 | 98 | 93.461 | 4.54 |
| `10 000 000 000` | 146 | 135 | 129.670 | 5.33 |

`tests/app/test_typography_followup.py:23-45` fixa estes dois casos e exige pelo menos
`2.0` unidades de folga. Passa. O teste usa as larguras medidas do Lato e não a estimativa
do modelo, pelo que não é circular.

### 2. Piso em píxeis CSS no topo do canvas

`tools/charts/src/adapter.js:153-159` introduz `top = Math.max(31 * scale, 31)` e
`nameGap = Math.max(13 * scale, 13)`. `nameGap` é consumido pelo eixo Y (`:169`) e `top`
pelo `grid` (`:257`), em vez dos valores escalados que ficavam abaixo da altura fixa do
nome do eixo. O piso restaura, nas larguras estreitas, a mesma gutter do desenho completo
de 880px. O bundle novo contém o código compilado do adapter
(`Math.max(31*u,31)` e `Math.max(13*u,13)` com `u = e/CP`), pelo que o hash novo não é um
pin de fonte sem efeito.

`tests/app/test_typography_followup.py:47-57` fixa o piso, rejeita as formas antigas
`top: 31 * scale` e `nameGap: 13 * scale` e confirma os dois papéis de 19.8px. Passa. A
prova renderizada a 320px e 480px continua a pertencer à matriz do parent; não a repeti.

### 3. Empilhamento da figura antes de estreitar o valor

`static/css/prumo.css:460-466` acrescenta `@media (max-width: 1200px)` com
`.figure-block` numa coluna e a borda da metadata no topo. `static/css/prumo.css:468-471`
já não colapsa a figura a 1100px. A faixa problemática de 1101px a 1139px fica inteiramente
empilhada, e a partir de 1201px a coluna do valor volta a ter largura para as duas linhas
revistas. O token publicado e o tamanho do valor não mudam.

`tests/app/test_typography_followup.py:59-70` verifica a nova query, a ausência de
`.figure-block` na query de 1100px e a ordem dos blocos. Passa.

### 4. Hifenização nativa do h1

`static/css/prumo.css:57-64` declara `hyphens: auto` e `-webkit-hyphens: auto` no `h1`.
A regra partilhada em `static/css/prumo.css:49-55` mantém `overflow-wrap: anywhere` como
fallback. O documento público tem `lang="pt-PT"` em `app/templates/base.html:2`, pelo que o
Chromium usa o dicionário português em vez de quebrar a palavra a meio.

`tests/app/test_typography_followup.py:72-80` fixa as duas declarações e o fallback.
Passa. A quebra renderizada a 390px fica com a matriz do parent.

### 5. Documentação e comentários

`docs/superpowers/handoff/reports/legibility-release/type-increment.md:15-22` distingue
corretamente o papel SVG `.chart-axis-label` a 18.15px do nome de eixo do canvas a 19.8px e
identifica `.chart-axis-title` como papel sem consumidor. `tests/app/golden/README.md:4-8`
faz a mesma correção. Os comentários de `tests/test_legibility_assets.py:62-77` e `:90-91`
usam agora as raízes atuais: 28.05px no público e 26.4px no Admin, com os valores
26.6475, 22.44, 21.879, 20.757, 23.001, 17.16 e 15.312. A aritmética confere.
`tests/app/test_type_increment.py:72-79` passou a fixar o piso do adapter em vez da
multiplicação simples.

## Bundle e integridade

- `static/js/prumo-charts.min.js`: 506637 bytes,
  `sha256 70a45c776a6bf397f75ddd0e22807ec837a7ba3a4b0545b61d2ff79c9a4e3d0a`.
- `static/js/prumo-charts.manifest.json:3-5` e `static/js/prumo-charts.NOTICE.txt:2-3`
  declaram o mesmo hash e os mesmos bytes.
- `tests/test_typography.py:39` fixa o mesmo hash na exceção do bundle vendorizado.
- `gzip` nível 9 com `mtime=0` pelo `zlib` do Node usado em
  `tools/charts/build.mjs:40` dá 173149 bytes, igual ao manifesto e ao NOTICE. O mesmo
  método aplicado ao bundle de `3a88b1f` dá 173132, igual ao manifesto anterior, pelo que a
  medição é consistente entre revisões.
- `node --check static/js/prumo-charts.min.js` passa. O bundle novo contém os dois pisos do
  adapter e as duas roles de 19.8px.
- `git diff 3a88b1f..42c581f --check` está limpo.
- Não há alterações em `tests/app/golden/charts/*.svg`; só o README dos golden fixtures
  mudou. Os 11 SVGs continuam byte a byte iguais a `3a88b1f`.

## Testes executados

```text
.venv-ci/bin/python -m pytest tests/app/test_typography_followup.py \
  tests/app/test_type_increment.py -q
11 passed, 1 warning

.venv-ci/bin/python -m pytest tests/test_typography.py \
  tests/test_legibility_assets.py -q
25 passed
```

Total focado: 36 passed, 0 failed. `ruff check` nos ficheiros Python alterados passa.
Não corri a suite completa nem a matriz de browser, que são do parent.

## Em dashes

Não há travessões longos literais nem entidades HTML ou escapes que os codifiquem nas
linhas adicionadas fora do bundle. O bundle vendorizado contém 4 ocorrências do caractere
em `3a88b1f` e as mesmas 4 em `42c581f`, em texto da biblioteca. A
exceção de `tests/test_typography.py` está presa ao hash novo e o teste
`test_repository_text_has_no_em_dashes` passa com o `spec-review.md` já corrigido pelo
parent.

## Observações menores, sem bloqueio

- O `gzip_bytes` do manifesto é reproduzível com o `zlib` do Node de `build.mjs`, mas não
  com o `zlib` do Python desta máquina, que dá 172530. O mesmo acontecia na revisão
  anterior (172513 em Python contra 173132 no manifesto), pelo que é uma diferença de
  implementação do compressor, não um desalinhamento introduzido por `42c581f`. O hash e os
  bytes, que são o contrato, coincidem.
- `tests/app/test_typography_followup.py` fixa as declarações CSS de hifenização, mas não o
  atributo `lang` do documento. Hoje `app/templates/base.html:2` tem `pt-PT`; um pin do
  `lang` tornaria o teste mais completo numa próxima alteração. Não afeta a aceitação.

## Fronteira desta revisão

Não reconstruí o bundle, não alterei runtime, testes, assets nem CMS, não acedi a produção e
não repeti a matriz alargada de browser. A verificação renderizada de 320px, 390px, 480px,
1101px, 1140px, 1201px e 1440px fica com o parent. Este parecer cobre apenas o diff
`3a88b1f..42c581f` e a árvore final desse commit.

**Veredito final: PASS / APPROVED.**
