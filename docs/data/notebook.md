# Caderno de indicadores

O Caderno reúne até doze séries publicadas e permite escolher até seis para o mesmo gráfico. A ligação guarda a seleção e as definições; cada abertura usa os dados publicados nesse momento. Não é uma análise congelada, não exige conta nem grava escolhas na base de dados.

## Escolher e partilhar

Pesquise pelo indicador, país ou instituição e use "Acrescentar ao caderno". Os cartões mantêm os valores originais com período, unidade, estado, fonte, recolha e ligação à proveniência. Remover uma série conserva as outras definições. "Ligação limpa para guardar ou partilhar" retira apenas o termo de pesquisa.

O gráfico vem antes das definições e dos cartões. "Configurar" abre as opções sem o empurrar para baixo. As formas nativas de adicionar, remover, configurar, desativar e partilhar funcionam sem JavaScript. Seleção explicitamente vazia e gráfico desativado são estados diferentes; nunca escolhemos outras séries por si.

## Frequências originais

As séries anuais, semestrais, trimestrais, mensais e diárias podem partilhar um calendário. Cada observação conserva o seu período nativo. Posicioná-la no início do período é uma convenção de desenho, não uma data de publicação ou medição. Não repetimos PIB anual em todos os meses, não interpolamos e não substituímos ausências por zero.

Uma linha liga observações consecutivas da sua própria frequência; períodos nativos em falta interrompem essa linha. A tabela completa e a leitura do ponto indicam o período de cada valor ou "sem observação nesta posição temporal". As últimas datas e a proveniência são próprias de cada série, sem inventar um período comum. Totais anuais e trimestrais não são diretamente equivalentes.

Nas seleções da mesma frequência, os valores originais conservam o alinhamento anterior: apenas os períodos finitos comuns a todas as séries, com indicação das exclusões. A escala comum exige unidade, multiplicador e base compatíveis. A escala de dois eixos agrupa as séries por essa assinatura bruta: a ordem de primeira aparição define o eixo esquerdo e o direito, e cada grupo pode ter mais do que uma série. São necessários exactamente dois grupos; com um só grupo, use a escala comum, e com mais de dois escolha um subconjunto que forme dois grupos ou aplique uma transformação válida. O par antigo de duas séries com dois eixos mantém um eixo por série, mesmo quando as duas partilham a unidade. As unidades de cada grupo estão identificadas no gráfico, na legenda e nas definições. Sobrepor curvas não demonstra causalidade.

Em `/comparar`, a secção Portugal reúne configurações revistas que abrem directamente no Caderno já com as séries, a escala de dois eixos e a janela escolhidas. A elegibilidade é reavaliada em cada abertura: se uma série perder a publicação ou mudar a unidade, o multiplicador ou a base, o cartão correspondente desaparece por inteiro em vez de mostrar uma comparação incompleta. Os valores, a tabela e a proveniência continuam no caminho normal do Caderno.

A janela pode ser de dez anos, cinco anos ou todo o histórico. No calendário misto, ancora-se na observação finita mais recente da união; no alinhamento comum, no último período comum finito. Uma série escolhida sem observação na janela torna o gráfico indisponível com explicação, em vez de desaparecer silenciosamente.

As séries de quinze minutos continuam limitadas a um dia UTC comum. Não podem ser misturadas com frequências mais baixas nem anualizadas nesta versão. Um dia explicitamente pedido nunca é substituído por outro.

## Vista anual calculada

Selecione "Frequência: Anual". As séries originalmente anuais conservam os seus valores. Só existem métodos anuais para as famílias explicitamente revistas: médias simples de taxas mensais do IHPC/IPC, desemprego, Euribor e rendimentos abrangidos; médias dos índices de produção industrial abrangidos; dezembro para saldos de crédito e depósitos.

São exigidos os doze meses finitos, canónicos e sem quebra de série. Duplicados, meses em falta ou anos incompletos excluem esse ano, com indicação explícita. Não se calcula uma média parcial nem se anualiza um ano incompleto. Outros conceitos ou frequências sem método revisto recebem uma explicação, não uma agregação presumida.

A média anual calculada de doze taxas homólogas mensais do IHPC NÃO é a inflação anual oficial. A média simples das taxas mensais de desemprego também não é a estimativa anual oficial. Estas qualificações acompanham a vista; não se inventa uma série oficial que não existe no catálogo.

## Base 100 e pontos percentuais

As transformações desta versão exigem frequência anual e escala comum, com o mesmo ano de base para todas as séries. Um ano explícito deve existir em todas as séries, mesmo que esteja fora da janela visível. Sem ano escolhido, usa-se o primeiro ano completo comum na janela, e essa escolha automática é identificada.

Base 100: `100 * valor / valor_base`. Apenas níveis de famílias revistas, como PIB por habitante, população, crédito/depósitos e índices abrangidos; a base tem de ser estritamente positiva. Taxas de crescimento, percentagens e saldos de confiança não são rebaseados indiscriminadamente.

Pontos percentuais: `taxa - taxa_base`. Apenas taxas percentuais abrangidas. A base pode ser nula ou negativa; não há divisão. Não é uma variação percentual de níveis.

Os cálculos são vistas temporárias do leitor, não novas observações do editor nem séries guardadas pelo worker. A aritmética Decimal é comparada com uma recomputação racional independente antes de mostrar o resultado. Médias e normalizações são apresentadas com seis casas decimais e arredondamento para o par mais próximo. Uma normalização usa os inputs originais, nunca uma média já arredondada. Os tokens publicados e o valor exato de dezembro permanecem intactos.

Cada vista calculada identifica o método, a fórmula e a base; permite consultar os valores e períodos originais usados, incluindo os da base. Os inputs conservam estados e referências de recolha/execução/arquivo. A impressão mantém SVG, qualificações e ligações aos originais. Os CSV das páginas das séries continuam a exportar os originais; esta entrega não oferece um CSV transformado.

## Interação e disponibilidade

Rato, toque e teclado percorrem os pontos reais. As setas, Início e Fim usam o controlo inferior. Sem JavaScript, com o pacote bloqueado ou na impressão, SVG e tabela permanecem. Não há CDN nem pedidos externos.

Licenças e elegibilidade são reavaliadas em cada abertura. A perda de uma série explicitamente escolhida bloqueia o gráfico inteiro, mantendo os cartões elegíveis e as referências da ligação. Incompatibilidades estatísticas são explicadas; nunca mudamos silenciosamente a frequência, a escala, a base ou as séries escolhidas.

## Contrato do endereço e operação

`s`: até doze referências ordenadas; `g`: grupo explícito até seis; `grafico=on|off`; `escala=comum|dupla`; `janela=10a|5a|max`; `dia=YYYY-MM-DD` para intervalos; `frequencia=original|anual`; `transformacao=original|base100|pp`; `base=YYYY` opcional; `q`: pesquisa transitória. Valores iniciais omitidos conservam os endereços antigos. Parâmetros únicos repetidos ou malformados dão 404 antes de abrir a base; uma configuração válida mas estatisticamente indisponível dá 200 com explicação e cartões.

A app pública continua apenas GET/HEAD, com uma transação só de leitura por resposta. Não há migração, escrita estatística, publicação do CMS nem reinício da ingestão. A instalação atualiza site e backoffice, que partilha os modelos na pré-visualização estática. O recuo restaura código e imagens desses leitores, conservando dados e histórico.

Desenho/métodos: [spec](../superpowers/specs/2026-11-20-notebook-time-transformations-design.md). Provas e limitações: [relatório](../superpowers/handoff/reports/time-transformations/README.md). A aceitação humana com leitor de ecrã permanece separada dos testes automáticos.
