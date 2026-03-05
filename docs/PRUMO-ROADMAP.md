# Prumo PT — Roadmap de Features

> Estado: brainstorm / prioridade indicativa. Não compromete datas.

---

## Em curso / Quase pronto

- [x] Catálogo dinâmico de indicadores (Europa + Mundo)
- [x] Página Ajuda com guia de secções e FAQ
- [x] Colecção global WorldBank (PALOPs, G7, emergentes)
- [ ] **Bandeiras no Europa/Mundo** — instalar `fonts-noto-color-emoji` no Dockerfile

---

## Alta prioridade

### IA em PT vs Europa e PT vs Mundo
Análise textual (Claude Haiku) sobre a comparação seleccionada — igual ao que já existe no Explorador. O contexto enviado ao modelo incluiria: indicador, países, horizonte temporal, e os valores relevantes (Portugal, média UE, outliers). A análise focaria as diferenças estruturais PT vs resto.

### Colector de dados em falta (retry)
- FDI inflows (`BX.KLT.DINV.WD.GD.ZS`) — timeout na primeira colecção
- Taxa de matrícula terciária (`SE.TER.ENRR`) — idem
- Potencialmente: emissões CO₂ per capita, acesso à electricidade, mortalidade infantil

### Snapshot com ordenação + destaque PT
No modo Snapshot (PT vs Europa, PT vs Mundo), destacar visualmente a posição de Portugal no ranking e adicionar indicação da mediana europeia.

---

## Média prioridade

### Exportação de gráficos como PNG
Botão "Guardar imagem" nos gráficos ECharts — para uso directo em relatórios e apresentações.

### Histórico de análises IA (cache persistente)
Guardar em disco as análises já geradas (com hash dos dados) para evitar re-chamadas à API por dados que não mudaram. Já feito para o Painel — estender ao Explorador e às novas análises Europa/Mundo.

### Vista "Tabela" nos comparadores
Alternativa tabular ao gráfico — útil para leitura precisa de valores e cópia para relatórios.

### PT+UE27 diferencial no Mundo
Vista equivalente à do Europa (linha Portugal, linha referência, área de diferencial) mas usando a média OCDE ou G7 como referência.

### Indicadores de distribuição de rendimento
Coeficiente de Gini, S80/S20 (rácio de rendimento top 20% / bottom 20%) — já disponível no Eurostat, falta catálogo + colector.

---

## Baixa prioridade / Experimental

### Alertas / monitorização de publicações
Notificação (via Jarbas) quando sai nova publicação de um indicador-chave (e.g., IPI mensal, taxa de desemprego trimestral).

### Timeline de eventos políticos
Camada opcional nos gráficos do Explorador com eventos anotados (mudanças de governo, medidas orçamentais, crises) para contextualizar quebras nas séries.

### Indicadores laborais detalhados
Taxa de sindicalização, horas trabalhadas por semana, acidentes de trabalho mortais — fontes: Eurostat (Labour FORCE SURVEY), ACT.

### Comparação sectorial PT vs Europa (exportações)
Quota de exportações por sector (têxtil, calçado, metalurgia, turismo, TIC) vs média UE — para análise de especialização produtiva.

### Modo apresentação / fullscreen
Esconder o menu lateral e maximizar o gráfico activo — para uso em reuniões e apresentações públicas.
