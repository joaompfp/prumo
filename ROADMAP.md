# Prumo PT — Roadmap de Evolução
**Versão:** 1.0 · **Data:** 2026-03-01  
**Contexto:** documento interno de planeamento técnico e estratégico

IDEIAS A TESTAR INICIALMENTE NUM FORK AO CODIGO DO SITE, NÃO FAZER COMMIT PARA SITE EM PRODUçÂO em joao.date/dados ANTES DE ESTAREM BEM TESTADAS.
---

## Estado actual (baseline)

| Componente | Estado |
|---|---|
| Painel com 36 KPIs curados | ✅ produção |
| Explorador de séries temporais | ✅ produção |
| Comparativos internacionais (PT + PALOP) | ✅ produção |
| Análise IA com prompt declarado (Haiku) | ✅ produção |
| Visitor tracking (Umami, self-hosted) | ✅ operacional |
| Ficha técnica por indicador | ✅ produção |
| Licenças abertas (AGPL + ODbL + CC-BY-NC-SA) | ✅ produção |

**Bugs pendentes (ver `prumo-pt-bugs.md`):** overflow horizontal a ~1000px, variações % enganosas em indicadores anuais com lag, legenda truncada no Explorador, comparação de referência ambígua.

---

## Fase 1 — Estabilização e fundações (curto prazo, ~1 mês)

Objectivo: corrigir bugs, fortalecer a infra de dados, preparar terreno para as fases seguintes sem acumular dívida técnica.

### 1.1 Bugfixes (ver `prumo-pt-bugs.md`)
- Corrigir overflow horizontal no Painel (CSS grid responsivo)
- Suprimir variação % em indicadores anuais com lag declarado
- Corrigir truncagem de legenda no Explorador
- Corrigir labels da secção "Portugal vs Mundo" (índice acumulado vs taxa anual)

### 1.2 Resiliência do pipeline de dados

Inspiração directa: arquitectura do `scotthurff/situation-monitor`.

- Implementar **CircuitBreaker** por fonte de dados (INE, Eurostat, Banco de Portugal, FRED): se uma fonte falha 3× consecutivas, entra em modo degradado e serve dados da cache com timestamp visível
- Implementar **CacheManager com TTL** e fallback para dados stale: em vez de erro a ecrã vazio quando a API falha, mostrar último valor conhecido com aviso `"Dados de YYYY-MM (última actualização disponível)"`
- Implementar **RequestDeduplicator**: eliminar chamadas API redundantes quando múltiplos componentes pedem a mesma série em simultâneo
- **Staged refresh** no frontend: sparklines e valores correntes carregam da cache imediatamente; análise IA carrega por último sem bloquear o render inicial

### 1.3 Substituição dos links de notícias gerados por IA

O problema actual: a análise IA gera links que podem ser inventados ou desactualizados.

Solução: ficheiro `feeds.ts` com 15-20 feeds RSS portugueses curados por categoria:
- **Conjuntura geral:** Lusa, Jornal Económico, Público Economia, RTP Notícias
- **Energia:** ERSE, DGEG, Renováveis na Net
- **Trabalho/indústria:** Jornal de Negócios, sindicalismo (UGT/CGTP comunicados)
- **PALOP:** RTP África, Jornal de Angola, Expresso das Ilhas

O agregador RSS corre em background, indexa por data, e a análise IA recebe os títulos + URLs reais das últimas 72h como contexto adicional no prompt — em vez de inventar links, cita os que existem.

---

## Fase 2 — Camada analítica em R (médio prazo, ~2-3 meses)

Objectivo: adicionar fundamentação estatística quantitativa à análise IA, transformando prosa qualitativa em afirmações verificáveis.

### 2.1 Pipeline R mensal

Script R executado via cron no dia de actualização de dados, que:

1. Lê as séries do pipeline existente (JSON/CSV)
2. Calcula indicadores derivados
3. Escreve `/data/derived/stats-context.json` para consumo pelo frontend e pelo prompt IA

**Indicadores derivados a calcular:**

| Indicador | Método | Valor para a análise IA |
|---|---|---|
| Dessazonalização | X-13ARIMA-SEATS (pacote `seasonal`) | Separar ciclo de sazonalidade em Produção Industrial, Emprego |
| Breakpoints estruturais | Bai-Perron (`strucchange`) | Detectar automaticamente datas de quebra significativa |
| Correlações com lag | Cross-Correlation Function (`ccf`) | "O Brent precede o IHPC em 2 meses, r=0.71" |
| Significância de tendência | Mann-Kendall (`Kendall`) | Distinguir tendência real de variação aleatória |
| Regressão CPI | OLS simples (M3+BCE+Brent+EUR/USD) | Contexto para análise de inflação |

**Acesso a dados:** usar `rOpenGov/eurostat` para séries Eurostat — biblioteca oficialmente financiada pela UE, superior ao equivalente Python para este caso de uso específico.

### 2.2 Integração no prompt da análise IA

O `stats-context.json` é passado ao prompt Haiku como secção adicional:

```
[Contexto estatístico calculado — R]
- IHPC: tendência descida significativa (Mann-Kendall p=0.02) desde Set 2024
- Spread PT/DE: breakpoint estrutural detectado em Mar 2024 (Bai-Perron, 95%)
- Correlação Brent→IHPC: r=0.71, lag=2 meses (CCF, n=48)
- Produção Industrial dessazonalizada: +1.2% (valor bruto: +2.3%)
```

Resultado: a análise IA passa de "a inflação está a desacelerar" para "a dessazonalização X-13 confirma uma quebra estrutural em Setembro 2024 significativa a 95%, correlacionada com a descida do Brent com lag de 2 meses (r=0.71)".

### 2.3 Templates Quarto para relatórios da CAE

Template RMarkdown/Quarto que consome os dados do Prumo PT e gera automaticamente um relatório mensal em PDF de 4 páginas — directamente útil para os relatórios mensais da Comissão de Assuntos Económicos. Mantém o estilo visual do Prumo PT (paleta, fontes) mas em formato imprimível.

---

## Fase 3 — Expansão de cobertura (médio-longo prazo, ~3-6 meses)

Objectivo: resolver os gaps de cobertura identificados para atingir 9/10 na avaliação Storytelling with Data.

### 3.1 Habitação — o indicador politicamente mais relevante ausente

Portugal tem o problema de habitação mais agudo da UE em termos de esforço salarial. Fontes disponíveis:

- **INE:** Índice de Preços da Habitação (trimestral), taxa de esforço das famílias
- **Banco de Portugal:** crédito à habitação, spread médio nos novos contratos
- **Confidencial Imobiliário / Idealista:** preço mediano €/m² por distrito (API paga — avaliar custo vs impacto)

Mínimo viável: 3 cards no Painel (Preço Habitação Índice, Crédito Habitação Novos Contratos, Taxa de Esforço) + série no Explorador.

### 3.2 PALOP — dados de desenvolvimento humano

Resolver o gap estrutural identificado (score 5/10 para audiência PALOP).

Fontes com cobertura razoável mesmo com lag:
- **World Bank:** HDI, mortalidade infantil, despesa pública saúde/educação, acesso água potável (API pública, lag 1-2 anos mas consistente)
- **PNUD:** relatórios anuais Human Development por país PALOP

Implementação: nova secção no tab Comparativos — "Desenvolvimento Humano PALOP" com 5-6 indicadores separados da secção de conjuntura macroeconómica europeia. Labels explícitos de lag ("Dados de 2023").

### 3.3 Modo de análise simplificado

Resolver a barreira de literacia para audiências PALOP e utilizadores sem formação económica.

Toggle na análise IA: **"Técnico / Acessível"**

- Modo técnico (actual): "subordinação estrutural da política monetária europeia aos interesses financeiros"
- Modo acessível: "o BCE aumentou as taxas de juro para travar a inflação, mas isso encareceu o crédito das famílias portuguesas — os salários reais ainda não recuperaram"

Implementação: segundo prompt Haiku com instrução de registo, sem alterar a análise principal.

---

## Fase 4 — Infraestrutura open source (longo prazo, ~6-12 meses)

Objectivo: preparar o Prumo PT para crescimento via contribuição externa e possível replicação para outros contextos lusófonos.

### 4.1 GitHub público com documentação

- README com arquitectura clara, instruções de instalação, estrutura do ficheiro de configuração de indicadores
- `CONTRIBUTING.md` com guia para adicionar novas séries (formato esperado, como configurar fonte, metadados obrigatórios)
- `data/indicators.yaml` como ficheiro de configuração central e legível — uma linha por indicador com fonte, frequência, unidade, lag, descrição PT

Critério de sucesso: um investigador externo consegue adicionar um novo indicador sem tocar no código frontend, apenas editando o YAML.

### 4.2 Instâncias para outros países CPLP

O Prumo PT como **plataforma**, não apenas como instância portuguesa.

Cada país CPLP com capacidade técnica local poderia fazer fork e configurar a sua instância:
- `prumo-ao.date` — Angola (foco petróleo, kwanza, dívida pública)
- `prumo-cv.date` — Cabo Verde (foco turismo, remessas, escudo cabo-verdiano)
- `prumo-mz.date` — Moçambique (foco gás natural, metical, IDH)

Requisito técnico: parametrizar todas as referências a "Portugal" e "EUR" via ficheiro de configuração de instância. A análise IA recebe o contexto da instância no prompt — o mesmo mecanismo declarado já existente.

### 4.3 API pública de dados processados

Expor os dados curados e processados do Prumo PT como API REST simples:

```
GET /api/v1/series/{source}/{id}?from=2020-01&to=2026-03
GET /api/v1/painel/latest
GET /api/v1/comparativos/{indicator}?countries=PT,ES,DE
```

Valor: investigadores e jornalistas que queiram os dados já limpos e normalizados, sem ter de lidar com as APIs originais (INE tem interface antiquada, Eurostat tem SDMX complexo). Gera citações e links externos ao Prumo PT como fonte.

---

## Resumo por horizonte temporal

| Fase | Horizonte | Prioridade | Esforço estimado |
|---|---|---|---|
| **1 — Estabilização** | ~1 mês | Crítica | Baixo-médio |
| **2 — Camada R** | ~2-3 meses | Alta | Médio |
| **3 — Cobertura** | ~3-6 meses | Média | Médio-alto |
| **4 — Open source** | ~6-12 meses | Estratégica | Alto |

### Sequência recomendada dentro da Fase 1

1. Bugfixes (bloqueantes para credibilidade)
2. CircuitBreaker + CacheManager (bloqueante para escalar)
3. Feeds RSS (melhoria imediata na qualidade das análises)

A Fase 2 (R) pode começar em paralelo com a Fase 1.3 — o script R mensal é independente do frontend e pode ser desenvolvido sem afectar a produção.

---

*Roadmap elaborado com base em: avaliação Storytelling with Data (2026-03-01), análise comparativa de projectos análogos no GitHub, e sessão de testes de produção do Prumo PT.*
