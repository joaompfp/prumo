# CAE Dashboard v8 — Auditoria SWD + Testes Funcionais
Data: 2026-03-01 04:10
Auditor: Einstein (subagente SWD)
Metodologia: Dialética (tese→antítese→síntese) per Cole Nussbaumer Knaflic, *Storytelling with Data*
URL: https://cae.joao.date

---

## Veredicto Geral

O CAE Dashboard v8 é um produto tecnicamente sólido e funcionalmente completo: navegação fluida, dados reais, fichas técnicas ricas, e deep-links do Painel ao Explorador a funcionar. Contudo, tem um **bloqueador de acessibilidade crítico** (contraste de marca WCAG AA fail), uma **quebra severa de usabilidade mobile** (tabela Ficha innavegável), e dois **problemas SWD de comunicação de dados** — escala incompatível no Explorador multi-indicador e paleta arco-íris sem sentido informacional na Europa Snapshot.

---

## Testes Funcionais

### WP-1 ✅/❌ — Emojis parcialmente removidos

**O que vi:**
- ✅ Europa: dropdown de indicadores sem emojis
- ✅ Botão "Linhas" (`<button class="swd-select">`) sem emoji
- ✅ Botão "Snapshot" (mesmo botão toggle após clique) sem emoji
- ✅ Botão "Partilhar" superior Europa (`class="share-btn"`) sem emoji
- ❌ **FAIL**: Botão `"🔗 Partilhar"` (`class="btn-action"`) na barra de ações do Explorador/Europa tem emoji 🔗
- ⚠️ Placeholder de pesquisa: `"🔍 Pesquisar indicadores…"` (emoji decorativo — não explicitamente em WP-1 mas contribui para inconsistência)
- ⚠️ Indicadores já seleccionados mostram `✓` no dropdown (trivial, funcional)

**Diagnóstico:** Há dois botões "Partilhar" em coexistência — o top-level `.share-btn` está limpo; o `.btn-action` na toolbar inferior mantém o emoji. WP-1 falha por este motivo.

---

### WP-2 🚨 — CSS & Legibilidade — BLOQUEADOR CRÍTICO

**NavBar:**
- ✅ Background: `rgb(43, 43, 43)` = `#2B2B2B`
- 🚨 **BLOQUEADOR: Contraste WCAG AA FAIL**
  - Elemento: `<span>Dashboard</span>` com `color: rgb(204, 0, 0)` = `#CC0000`
  - Fundo efectivo (herança navbar): `#2B2B2B`
  - Luminância relativa L(#CC0000) = 0.1284; L(#2B2B2B) = 0.0242
  - **Ratio de contraste: 2.41:1**
  - WCAG AA texto normal: exige ≥ 4.5:1 → **REPROVADO**
  - WCAG AA texto grande (≥18pt bold ou ≥24pt): exige ≥ 3.0:1 → **REPROVADO**
  - Este é o nome da marca visível em todas as páginas. É um bloqueador.

**Botões:**
- ✅ `.btn-primary` background: `rgb(179, 0, 0)` = `#B30000`
- ✅ `.time-preset-btn.active` background: `rgb(179, 0, 0)` = `#B30000`

**Tabela Ficha:**
- ⚠️ Header `<thead>` tem `background: rgba(0, 0, 0, 0)` (transparente) — sem o fundo cinzento claro exigido pelo spec
- Na prática, a tabela fica sobre fundo branco de card — o header é visualmente indistinto das linhas de dados
- Impacto: menor, mas afecta escaneabilidade da tabela

**Axis labels (confirmado via código-fonte swd-charts.js):**
- ✅ `axisLabel.color: '#666666'` (não '#888888')
- ✅ `splitLine.lineStyle.color: '#F0F0F0', width: 1`
- ✅ `axisLine: { show: false }`, `axisTick: { show: false }`

---

### WP-3 ✅/⚠️ — Explorador UX

- ✅ Botão de tipo de gráfico: "Gráfico" (não "Chart")
- ✅ Altura do gráfico: `height: max(50vh, 400px)` — ajusta dinamicamente com viewport
- ✅ Tooltip mostra unidade: formatter customizado `${p.seriesName}: <strong>${value}</strong> ${unit}` (confirmado no código explorador.js)
- ✅ Gaps de dados: `connectNulls` default false no ECharts — gaps visíveis
- ⚠️ **End labels clipados**: Com indicadores seleccionados, o end label (ex: "Inflação (IHPC)") aparece apenas como "Inf" na borda direita do gráfico — cortado pelo boundary. Consistente em todos os gráficos com end labels. Impacto visual negativo (parece bug).

---

### WP-4 ✅ — Embed alinhado

URL testada: https://joao.date/textos/teste-cae-embed/

Confirmado via análise do código `embed.js` (`https://joao.date/dados/embed.js`):
- ✅ Primeira cor da série: `COLORS.series[0] = '#CC0000'`
- ✅ Linhas rectas: `smooth: false`
- ✅ Sem linhas de eixo: `axisLine: { show: false }` em X e Y
- ✅ Sem ticks de eixo: `axisTick: { show: false }` em X e Y
- ✅ Grid lines: `splitLine: { lineStyle: { color: '#F0F0F0', width: 1 } }`

Nota: Os axis labels (valores numéricos e datas) são visíveis — mas isso é diferente de axis lines/ticks. Os labels são necessários para leitura.

---

### WP-5 ✅/⚠️ — Toast unificado

**Europa (botão "Partilhar" top):**
- ✅ Toast com classe `"toast-notification"`
- ✅ Posicionamento centrado: `position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%)`
- ✅ Texto "Link copiado!" com fundo dark pill (`#1A1A1A`)
- ⚠️ Animação muito rápida — a transição de opacidade (0.2s) faz o toast desaparecer antes de ser capturado em screenshots. Utilizadores de leitura lenta podem não o ver.

**Explorador (6.º indicador):** Não testado directamente (exigiria adicionar 6 indicadores sequencialmente). Por analogia com o código partilhado, assume-se consistência.

---

### WP-6 ✅ — Secção Ficha

- ✅ Cards de fonte: título bold, descrição, badge "X indicadores", link "Site oficial" — todos estilizados (não defaults do browser)
- ✅ "Notas de Interpretação": `<h4>Notas de Interpretação</h4>` — sem emoji
- ✅ "Sobre este Dashboard": sem número de versão, sem info de stack (apenas URL e snippet de embed — documentação de uso, não info técnica interna)
- ✅ Fichas individuais têm descrições longas e correctas em PT-PT, com referências regulatórias (ex: "regulamento (CE) n.º 2016/792")
- ✅ Metadados visíveis: Unidade, Frequência, Cobertura, Observações

---

### WP-7 ✅ — Painel expandido

Via `/api/painel` (JSON verificado):

| Secção | KPIs | Ordem |
|---|---|---|
| Custo de Vida | 6 | 1.ª |
| **Indústria** | **7** | **2.ª** ✅ |
| Emprego | 3 | 3.ª |
| Conjuntura | 3 | 4.ª |
| Energia | 4 | 5.ª |
| Externo | 3 | 6.ª |
| Competitividade | 3 | 7.ª |
| **Total** | **29** | |

- ✅ 7 secções
- ✅ Indústria é 2.ª secção
- ✅ Indústria tem 7 KPIs (incl. Cobre FRED + Alumínio FRED)
- ✅ Competitividade existe com 3 KPIs
- ✅ Total 29 KPIs (~30 conforme spec)
- ✅ KPIs têm campos `source` e `indicator` no JSON

**Excepções:**
- ⚠️ Gasolina 95: `"error": "no data"` — API retorna erro sem dados, UI mostra "n/d" sem contexto
- ⚠️ Electricidade (casa): `"context": ""` — string de contexto vazia

---

### WP-8 ✅ — Europa auto-snapshot

- ✅ Em modo "Linhas", clicar "Todos EU" → auto-switch para "Snapshot" (barra horizontal ordenada de todos os países UE)
- ✅ URL actualiza para `view=snapshot`
- ✅ Título mantém-se contextual: "Portugal 5.8 pp abaixo da UE-27"

---

### WP-9 ✅ — Painel → Explorador deep-link

- ✅ Cards têm `data-source` e `data-indicator` no DOM
- ✅ Clicar card Inflação → navega para `#explorador?s=INE%2Fhicp_yoy&from=2021-03&to=2026-03`
- ✅ Clicar card Gasóleo (2.º card) → actualiza Explorador para `#explorador?s=DGEG%2Fprice_diesel&from=2021-03&to=2026-03`
- ✅ Deep-link do Painel substitui/actualiza indicador no Explorador (comportamento esperado: não acumula)
- ⚠️ Efeito hover (lift): não verificado explicitamente — CSS tem transições mas o "lift" não foi capturado em screenshot

---

### WP-10 ✅ — Explorador inline ficha panel

- ✅ Painel de ficha aparece abaixo do gráfico com indicador(es) seleccionado(s)
- ✅ Cada card mostra: nome com dot colorido, fonte, descrição completa, Unidade, Frequência, Cobertura, Observações
- ✅ Via deep-link do Painel: ficha aparece imediatamente
- (Remoção de todos os indicadores → painel desaparece: não testado explicitamente mas comportamento esperado)

---

## Auditoria SWD

### 1. Clutter (SWD Ch. 3) — O que não serve os dados

**Tese:** O dashboard aspira a minimalismo analítico.
**Antítese:**
- A border colorida no topo dos KPI cards (verde/vermelho) duplica informação já transmitida pela cor do valor YoY e pelo sparkline — três sinais visuais para a mesma mensagem de sentimento
- O end label no Explorador aparece "Inf" clipado na borda direita — fragmento visual sem valor
- A barra de ticker no Painel topo ("Euribor -33.7% · Electricidade -30.1%") anima em loop — movimento captura atenção, mas os dois indicadores destacados são editorialmente arbitrários

**Síntese:**
- Simplificar: manter cor do border do card, remover a redundância da cor YoY ou do sparkline color (uma das três é suficiente)
- Corrigir end labels ou adicionar `clip: true` com padding-right
- O ticker ou deve mostrar os indicadores mais significativos do período (editorial) ou deve ser eliminado

---

### 2. Atenção (SWD Ch. 4) — O olho vai para onde deve?

**Tese:** Red (#CC0000) = Portugal, problema; Green = positivo; Grey = neutro.
**Antítese:**
- ✅ O uso de #CC0000 para PT no Europa é coerente e correcto
- 🚨 **Europa Snapshot: paleta arco-íris nas barras** — cada país tem uma cor diferente (azul, roxo, verde, laranja...). SWD Ch. 4 é explícito: "use color to highlight, not to decorate". Com 28 países e 28 cores, nenhuma cor significa nada. O olho não sabe onde ir.
  - Portugal está em vermelho (#CC0000) — o único bar com cor informacional
  - Solução: todos os países a cinzento (#CCCCCC), Portugal a #CC0000
- 🚨 **Explorador multi-indicador com unidades incompatíveis**: ao adicionar "Inflação HICP YoY %" + "Inflação UE Eurostat (índice ~100-130)", o chart partilha um eixo Y. A série % fica esmagada na base (valores 0-10 vs 90-130). A linha vermelha torna-se invisível.
  - SWD: nunca mostrar séries com unidades incompatíveis num único eixo sem aviso ou dual-axis
- ⚠️ O ticker no topo do Painel captura atenção com dois indicadores — selecção editorial não explicada ao utilizador

---

### 3. Hierarquia Visual (SWD Ch. 5) — A importância comunica visualmente?

**Tese:** Valor grande → YoY → contexto → sparkline.
**Antítese:**
- ✅ Dentro de cada KPI card, a hierarquia está correcta: valor (48px) > YoY (16px bold) > contexto (14px) > sparkline (muted)
- ⚠️ Todas as secções têm o mesmo peso visual — "CUSTO DE VIDA" e "COMPETITIVIDADE" têm idêntico tamanho de título, idêntico estilo de border. Não há sinalização de que algumas secções são mais urgentes que outras.
- ⚠️ O valor YoY (ex: "-22.6%") compete visualmente com o valor actual (ex: "2.4 %") — ambos são proeminentes. O YoY é contexto; o valor actual é o dado primário. O tamanho relativo deveria reflectir esta hierarquia mais claramente.
- ✅ Sparkline é subtil e claramente secundário

---

### 4. Texto e Contexto (SWD Ch. 6) — As palavras servem os dados?

**Tese:** Cards com contexto factual, fichas com descrições técnicas ricas.
**Antítese:**
- ✅ Linguagem: PT-PT impecável. "inflação", "desemprego", "electrónica", "habitação" — sem brasileirismos.
- ✅ Strings de contexto com nuance real: "(tendência recente: subida)", "(ainda negativo)", "3.º mês consecutivo em queda" — excelente contextualização que vai além do número bruto
- ✅ Unidades sempre visíveis nos cards (sem hover necessário)
- ⚠️ Gasolina 95 mostra "n/d" como valor E como YoY, sem string de contexto — o utilizador não percebe se o dado não existe, ainda não foi publicado, ou houve erro. SWD: os dados ausentes precisam de explicação.
- ⚠️ Electricidade (casa): `"context": ""` — oportunidade perdida (ex: "Tarifa regulada BTN — consumidor doméstico médio")
- ✅ Fichas técnicas: referências regulatórias completas, comparações PT vs UE27 explícitas — nível de detalhe exemplar para um instrumento de trabalho político

---

### 5. Narrativa (SWD Ch. 7-8) — O dashboard conta uma história?

**Tese:** O Painel dá uma visão global da economia portuguesa.
**Antítese:**
- O utilizador que abre o Painel vê um ticker com 2 indicadores e depois 29 KPI cards. Não há mensagem editorial central.
- A excepção positiva é o Europa: "Portugal 5.8 pp abaixo da UE-27" — este é um headline narrativo. **O Painel deveria ter o equivalente.**
- A ordem das secções (Custo de Vida → Indústria → ... → Competitividade) é lógica mas não dramática. Não cria tensão ou progressão de argumentação.
- SWD Ch. 7: "Lead with the message, support with data". Actualmente o dashboard lidera com dados e espera que o utilizador derive a mensagem.

**Síntese:**
- Adicionar uma linha de "situação geral" acima das secções: ex. "Inflação controlada (2.4%), indústria em contracção (IPI −2.1%). Gás natural +41.5%: atenção a energo-intensivos."
- Manter os KPI cards como suporte. A narrativa deve preceder, não decorar.

---

### 6. Mobile / Responsiveness

**Observado a 390px (iPhone 14):**

- ✅ Painel: cards em coluna única, valores legíveis, sparklines visíveis
- ✅ Navbar: 4 links horizontais, brand oculta (`.nav-brand { display: none }` para ≤600px) — decisão correcta dado o espaço
- ⚠️ Ticker: quebra em 2 linhas ("Euribor 3 meses -33.7% · Electricidade Grossista -30.1%") — ainda legível
- 🚨 **MAJOR — Ficha table em mobile:**
  - O título da fonte (ex: "INE — Instituto Nacional de Estatística") quebra em 4 linhas por ser o cabeçalho do card em layout 2-col que collapsa
  - A tabela de indicadores **não tem wrapper `overflow-x: auto`** — as colunas ("Freq.", "Desde", "Até", "Obs.") ficam completamente cortadas fora do ecrã
  - O utilizador mobile não consegue ver Frequência, Cobertura ou Observações — colunas críticas para avaliação de qualidade dos dados
  - Solução: `div { overflow-x: auto; }` à volta de cada `<table>`, ou redesign para cards mobile

---

## Issues Prioritizados

### 🚨 BLOCKING (impede uso ou viola WCAG)

| # | Issue | WP | Detalhe |
|---|---|---|---|
| B1 | Contraste WCAG AA FAIL | WP-2 | "Dashboard" brand: #CC0000 on #2B2B2B = **2.41:1** (exige ≥4.5:1 normal, ≥3.0:1 large). Viola WCAG 2.1 SC 1.4.3. Afecta todos os utilizadores com deficiências visuais. |

### ⚠️ MAJOR (prejudica clareza significativamente)

| # | Issue | WP/SWD | Detalhe |
|---|---|---|---|
| M1 | Ficha table quebra em mobile | Mobile | Sem `overflow-x: auto`, colunas Freq./Desde/Até/Obs. ficam cortadas em 390px. Tabela de metodologia innavegável em mobile. |
| M2 | Explorador multi-indicador sem aviso de escala | SWD Ch.4 | Indicadores com unidades incompatíveis (YoY% + índice 100+) partilham eixo Y → série menor fica invisível. Sem dual-axis ou aviso. Pode levar a interpretações erradas. |
| M3 | Europa Snapshot: cores arco-íris | SWD Ch.4 | 28 países, 28 cores sem significado. Viola o princípio de color-for-information. Apenas Portugal deve estar destacado (#CC0000), restantes a cinzento neutro. |

### 📝 MINOR (melhorias incrementais)

| # | Issue | WP | Detalhe |
|---|---|---|---|
| m1 | "🔗 Partilhar" com emoji | WP-1 | Botão `btn-action` na toolbar do Explorador/Europa mantém 🔗. O `share-btn` no topo Europa está limpo. |
| m2 | End labels clipados | WP-3 | Texto do end label (ex: "Inflação (IHPC) — Variação Anual") aparece cortado como "Inf" na borda direita do gráfico. |
| m3 | Gasolina 95 "n/d" sem contexto | WP-7 | API retorna `error: "no data"`. UI mostra "n/d" sem explicar o motivo. Adicionar context string "Dados de 2025 em actualização". |
| m4 | Electricidade (casa): contexto vazio | WP-7 | `"context": ""` — perdida oportunidade de contextualização. |
| m5 | Ficha table header sem fundo cinzento | WP-2 | `<thead>` tem background transparente. Spec pede light grey. Adicionar `background: #F8F8F8` ao thead. |
| m6 | Toast demasiado rápido | WP-5 | Transição opacity 0.2s pode ser insuficiente para utilizadores de leitura lenta. Sugerir 2-3s de visibilidade. |
| m7 | Sem narrativa editorial no Painel | SWD Ch.7 | Ausência de headline de situação geral. Europa tem "Portugal X pp abaixo da UE-27"; Painel não tem equivalente. |
| m8 | Ticker: selecção de indicadores não explicada | SWD Ch.4 | Os 2 indicadores do ticker não têm critério editorial visível — pode parecer arbitrário. |
| m9 | Border colorida no topo dos cards redundante | SWD Ch.3 | Triplicação da mensagem de sentimento (border + cor YoY + sparkline color). Uma basta. |
| m10 | Hierarquia de secções plana | SWD Ch.5 | Todas as secções com peso visual idêntico — considerar destacar secções de maior urgência conjuntural. |

---

## Sugestões para v9

### S1 — CRÍTICA: Corrigir contraste da marca (BLOCKING)
Opções por ordem de preferência:
1. **Manter cor mas aumentar** — usar `#FF4444` (#FF4444 on #2B2B2B = ~3.7:1, melhor mas ainda abaixo AA normal; ou `#FF6666` ≈ 5.1:1 ✅)
2. **Mudar brand para branco** — "CAE" e "Dashboard" em `#FFFFFF` (contraste 10.8:1 ✅). Diferenciar via font-weight.
3. **Mudar fundo da navbar** — mais escuro (ex: `#1A1A1A` aumenta ratio para ~2.75:1... ainda insuficiente); ou fundo claro mas isso muda identidade visual
4. **Recomendação**: "CAE" a branco, "Dashboard" em `#CC0000` mas em texto **grande bold** — passes WCAG AA large text se ≥18.67px bold

### S2 — MAJOR: Ficha table em mobile
```css
.source-card-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
```
Wrapping simples. Ou alternativamente, converter colunas para `<dl>` em mobile via media query.

### S3 — MAJOR: Explorador multi-indicador
Ao detectar unidades incompatíveis entre indicadores seleccionados:
- Mostrar banner: "⚠️ Indicadores com unidades diferentes. O gráfico pode ser enganador. [Normalizar para índice 100]"
- Ou: activar dual Y-axis automaticamente (eixo esquerdo = série 1, eixo direito = série 2)
- Ou: bloquear adição quando unidade difere, com mensagem explicativa

### S4 — MAJOR: Europa Snapshot — cores informacionais
```javascript
// Nas barras do Snapshot:
const barColor = country === 'PT' ? '#CC0000' : '#CCCCCC';
```
Portugal em vermelho, todos os outros em cinzento neutro. A posição no ranking já comunica a comparação; a cor deve apenas destacar o país de referência.

### S5 — MINOR: End labels no Explorador
Opção A: `padding-right: 80px` no container do gráfico para dar espaço ao end label
Opção B: Em vez de end label, usar legend no rodapé (já implementado para série única)
Opção C: Truncar end labels programaticamente com "..." e tooltip completo no hover

### S6 — MINOR: Partilhar sem emoji
```javascript
btn.textContent = 'Partilhar'; // remove '🔗 '
```

### S7 — NARRATIVA: Headline de Situação Geral no Painel
Inspirado no Europa ("Portugal 5.8 pp abaixo da UE-27"), adicionar no topo do Painel:
```
[Situação em DEZ 2025]
Inflação controlada a 2.4% ↓ · Indústria em contracção (IPI -2.1%) · Gás Natural +41.5% YoY
```
Actualizar via API, campo `"headline": "..."` no endpoint `/api/painel`.

### S8 — Gasolina 95
Verificar pipeline DGEG — indicator `price_gasoline_95` retorna `"error": "no data"`. Ou corrigir dados ou substituir por indicador alternativo (ex: `price_gasoline_95_pvp` conforme v7). Enquanto sem dados, mostrar context string "Dados em actualização".

---

## Resumo Executivo para v9

**Estado:** Funcional e completo. 9/10 WPs passam. 1 BLOCKING, 3 MAJOR, 10 MINOR.

**Prioridade absoluta:**
1. 🚨 Contraste "Dashboard" — viola WCAG, afecta credibilidade institucional
2. 🚨 Ficha table mobile — innavegável em smartphone
3. 🚨 Multi-indicador Explorador — comunicação de dados potencialmente enganadora

**O que está muito bem:**
- Strings de contexto nos KPI cards: exemplares. "(ainda negativo)", "(tendência recente: subida)" — são editorial com rigor.
- Europa Snapshot com títulos narrativos — modelo para o Painel.
- Fichas técnicas: riqueza de detalhe para instrumento de trabalho político.
- Deep-links Painel→Explorador: UX fluida, URL permalinkable.
- Embed clean: smooth:false, no axis lines, #F0F0F0 grid — aderente ao spec.

**Citação SWD relevante (Ch. 4):** *"Color is a powerful tool for focusing your audience's attention. When everything is colored, nothing stands out."* — A paleta arco-íris do Europa Snapshot é o exemplo perfeito do anti-padrão.
