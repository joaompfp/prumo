# Revisão independente de especificação - incremento tipográfico

Data: 2026-11-17. Commit revisto: `3a88b1f` (`feat: increase Prumo type scale by ten
percent`), base `273b14b`, branch `pipeline-rebuild`.

## Veredito

**PASS** - o diff de 24 ficheiros cumpre o âmbito aprovado do incremento de ~10% e não
encontrei omissões funcionais nem alterações a dados, CMS, autenticação ou ingestão. As
observações no fim são de higiene/documentação, não bloqueantes.

## Âmbito confirmado

- **Raízes**: público `25.5px -> 28.05px`; Admin `24px -> 26.4px` (`0.875rem` = `23.1px`).
  Os restantes papéis de texto públicos e de Admin são `rem`, pelo que crescem 10% sem
  tocar em tokens, cores, Carmim, Lato/TeX Gyre Schola ou geometria do fio de prumo.
- **Clamps**: público `h1 6.9vw -> 7.6vw`, `h2 3.6vw -> 4vw`, valor de figura
  `7.5vw -> 8.25vw`; Admin `h1 3.3vw -> 3.63vw`, título do editor `3vw -> 3.3vw`. Os
  limites `rem` crescem com a raiz, pelo que o comportamento do clamp é preservado.
- **SVG**: ticks `16.5 -> 18.15px`; último valor `18 -> 19.8px`; nomes de unidade
  `16.5 -> 18.15px`; deslocamentos `10/6/8/18/26/40` -> `11/7/9/20/29/44` e limiares de
  colisão `30/22` -> `33/24`, todos na mesma proporção.
- **Canvas**: `fontSize` de eixo `18.15`, nomes de eixo e tooltip `19.8`, `lineHeight`
  `29.7`; grelha `97/33/31/68` e eixo duplo `172`, iguais ao modelo SVG. `nameGap`
  `12 -> 13`.
- **Responsivo**: o piso do SVG sem JavaScript passou de `600x240` para `660x264`; a
  search pública passa a ocupar uma linha própria abaixo de `900px` (antes `760px`), sem
  reduzir texto. A sidebar Admin `300px -> 330px` acompanha os 10% das etiquetas de
  navegação. Não há redução de `font-size` em nenhuma regra do diff.
- **Bundle**: `static/js/prumo-charts.min.js` tem `sha256
  63e097d47963d48d78cc19008e6e2bac724ff6a20c26591f5a8276a91c91cc3d`, `506603` bytes e
  gzip Node nível 9 `173132` bytes; `manifest.json` e `NOTICE.txt` estão coerentes e a
  isenção em `tests/test_typography.py` aponta para o mesmo hash.
- **Preservação**: o diff não inclui `registry/`, `seed_data/`, `ingest/`, `collectors/`,
  migrações, `backoffice/` (CMS/auth) nem templates públicos. `app/` só tem
  `chart_model.py` e `charts.py`, ambos limitados a geometria/posições de rótulos.

## Evidência executada

- `.venv-ci/bin/python -m pytest tests/app/test_type_increment.py
  tests/test_legibility_assets.py tests/app/test_chart_model.py -q` -> **29 passed**.
- `.venv-ci/bin/python -m pytest tests/test_typography.py
  tests/app/test_legibility_review.py -q` -> **23 passed** (dois ficheiros adjacentes ao
  âmbito, para confirmar hash do bundle e baseline dos ticks).
- `.venv-ci/bin/ruff check` nos Python alterados -> **All checks passed**.
- `node --check static/js/prumo-charts.min.js` -> **OK**.
- Comparação programática dos 11 goldens (`ElementTree` sobre o commit antigo e o atual):
  texto exatamente igual em todos; nos 9 alterados só mudaram atributos de coordenadas
  (`x`, `y`, `x1`, `x2`, `y1`, `y2`, `cx`, `cy`, `d`); `cmp_empty.svg`, `line_empty.svg`,
  `home_code_list.html` e `home_before_editorial.html` estão inalterados.
- `git diff --name-only 273b14b 3a88b1f` -> 24 ficheiros, sem caminhos de dados/CMS/auth/
  ingestão/migrações.

Não repeti as matrizes alargadas de browser (77/55/153 testes do relatório) por serem
explicitamente fora do âmbito desta revisão limitada; o parent continua dono dessa matriz.
Também não fiz commit.

## Observações não bloqueantes

1. **Comentários de teste desatualizados**: `tests/test_legibility_assets.py:65-70` e
   `:88-89` ainda mostram equivalências em px da raiz anterior (`nav 16.15 -> 24.225`,
   `table th 10.4 -> 15.6`, etc.). Com a raiz `28.05/26.4` os valores atuais são
   `26.6475`, `17.16`, etc. Não afeta o teste, mas o comentário engana a próxima revisão;
   vale a pena remover os números ou atualizá-los.
2. **"Axis names 18 -> 19.8" no README/report**: `tests/app/golden/README.md:4-5` e
   `docs/superpowers/handoff/reports/legibility-release/type-increment.md:15-16` dizem que
   os nomes de eixo passaram de 18 para 19.8. Na realidade o SVG usa
   `.chart-axis-label` (`app/charts.py:140,145`, `static/css/prumo.css:561`) a `18.15px`;
   `.chart-axis-title` a `19.8px` não tem consumidor. O canvas usa `19.8` em
   `tools/charts/src/adapter.js:168`. Não é uma omissão funcional do incremento - ambos os
   papéis cresceram 10% face à base aceite -, mas a frase "o SVG e o canvas usam os mesmos
   números" deve ser lida como geometria, não como tamanho de nome de eixo.
3. **Resíduos não versionados**: `docs/superpowers/handoff/reports/legibility-release/
   online_snapshot.py` e `qa_server.py` estão `untracked`. Não fazem parte do commit
   revisto; garantir que não entram no commit do relatório do parent.
4. **Confirmação visual residual**: a sidebar Admin de `330px` em `1025-1200px` e o
   alinhamento do canvas com `containLabel` continuam dependentes da matriz de browser do
   parent, como o próprio relatório declara. A geometria estática é coerente e os testes
   de interação disponíveis não foram repetidos aqui.
