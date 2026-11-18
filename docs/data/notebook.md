# Caderno de indicadores

Estado: cartões instalados; extensão com gráfico conjunto implementada em `pipeline-rebuild`, ainda sem merge nem instalação desta extensão.

O Caderno reúne até doze séries publicadas numa página. Cada cartão mantém o valor, unidade,
período, fonte, data de recolha, estado e ligação à proveniência da série. A extensão permite
escolher até seis dessas séries para o mesmo gráfico, sem editar observações ou calcular
transformações estatísticas.

## Utilização

A entrada Caderno fica na navegação e no rodapé do site. Numa página de série, a ação
"Criar caderno com esta série" abre uma seleção inicial. Nas comparações, a ação equivalente
começa com as séries já mostradas.

Dentro do Caderno, pesquise pelo nome do indicador, país ou instituição. "Acrescentar ao
caderno" conserva os cartões e a configuração já escolhida. Cada cartão tem "Remover do
caderno"; "Limpar seleção" regressa ao caderno vazio. Tudo isto funciona sem JavaScript.

"Ligação limpa para guardar ou partilhar" abre o endereço com as séries e a configuração do
gráfico, sem o termo de pesquisa. Guarde-o nos favoritos ou copie o endereço do navegador.
Quem abrir a ligação recebe a mesma seleção. Não há conta, cookie, armazenamento local ou
registo da escolha na base de dados. As referências são públicas, não conteúdo privado.

O endereço guarda a escolha das séries, não os seus valores. Cada abertura mostra os dados
publicados nesse momento. Não é uma análise histórica congelada.

## Gráfico conjunto

O painel "Evolução conjunta" aparece antes dos cartões. Com até seis séries elegíveis, tenta
mostrar todas num eixo comum. Com sete a doze séries, pede uma escolha explícita de até seis;
não seleciona automaticamente um grupo nem descarta as incompatíveis.

Abra "Definições do gráfico", marque as séries e escolha a escala e a janela. O eixo comum
exige a mesma periodicidade, unidade nativa, multiplicador e base de índice. Os dois eixos
exigem exatamente duas séries com a mesma periodicidade e uma escolha explícita. As unidades
ficam identificadas. Sobrepor curvas não demonstra causalidade; o Caderno conserva as
geografias e definições de cada série e não decide por si se a relação tem significado.

A janela inicial é de dez anos a partir do último período comum com valores finitos. Há
opções de cinco anos e de todo o histórico. Os períodos sem correspondência nas outras
séries, sem número finito ou sem data válida ficam fora de todas as linhas e da tabela, com
uma nota de exclusão. Não há interpolação, normalização, alteração de base ou preenchimento
com zeros. A tabela inclui todos os períodos realmente desenhados, com os valores exatos e
os estados publicados. A proveniência refere-se ao último período comum mostrado.

Nas séries de quinze minutos, o gráfico usa um só dia UTC: o mais recente partilhado com
pelo menos dois pontos comuns, ou o dia escolhido no campo respetivo. Um dia sem dados
comuns dá uma explicação sem substituir a escolha por outro dia. Não existe agregação
implícita. O campo de dia só afeta estas séries; a janela de anos só afeta as restantes.

O gráfico permite leitura por rato, toque e teclado. As setas, Início e Fim percorrem os
períodos no controlo inferior. Sem JavaScript, se o pacote falhar, ou na impressão, o SVG e
a tabela continuam disponíveis. Os cartões e as listagens conservam os SVG pequenos. A
biblioteca é local e não desencadeia pedidos a serviços externos.

Para deixar de mostrar o gráfico, use "Desativar gráfico" ou desmarque todas as séries e
aplique a configuração. A seleção vazia do gráfico é distinta de usar todas as séries.
Remover o último membro de um grupo explícito não seleciona automaticamente outros cartões.

## Disponibilidade e limites

Uma série sem valores publicados, retirada ou sem permissão de redistribuição deixa de
aparecer nos cartões, com um aviso de quantas séries foram omitidas. Os dados e histórico
originais não são apagados. As referências do endereço são conservadas, incluindo na
ligação limpa, para não transformar silenciosamente uma comparação noutra.

Se uma série escolhida explicitamente para o gráfico perder elegibilidade, o gráfico todo
fica indisponível; os restantes cartões continuam visíveis. Uma seleção com periodicidades
ou escalas incompatíveis conserva os cartões e apresenta uma explicação no painel, com os
controlos disponíveis para corrigir a escolha.

O máximo do endereço é doze parâmetros `s`; o grupo explícito aceita até seis parâmetros
`g`, antes da desduplicação. Valores malformados, referências do gráfico fora do Caderno e
parâmetros únicos repetidos dão a página genérica de endereço inexistente. Não há truncagem
silenciosa. Uma falha do catálogo ou da base dá a indisponibilidade genérica, sem códigos
operacionais no texto.

As páginas funcionam em `/caderno` no domínio direto e em `/dados/caderno` no endereço
montado. `s` é a seleção ordenada, `g` o grupo explícito do gráfico, `grafico=on` distingue
uma escolha explícita vazia de usar todas, `grafico=off` oculta o gráfico, `escala` aceita
`comum` ou `dupla`, `janela` aceita `10a`, `5a` ou `max`, `dia` é uma data ISO e `q` uma
pesquisa transitória. Os parâmetros não indicados usam os valores iniciais. Todas as
respostas do Caderno mantêm `noindex, follow` nos metadados e no cabeçalho `X-Robots-Tag`.

## Operação e custo

Não existe migração nem estado do Caderno para recuperar. A instalação autorizada desta
extensão atualiza o site e a pré-visualização pública incluída no backoffice, sem tocar na
ingestão, conteúdo do CMS, credenciais ou encaminhamento. Um recuo de código não apaga
conteúdo editorial nem observações estatísticas. Endereços antigos do Caderno continuam
válidos; endereços com opções do novo gráfico precisam de uma versão que as compreenda.

Para encontrar corretamente a janela, as séries não intervalares são lidas com o seu
histórico completo na mesma transação de leitura; a janela limita o que é desenhado e
publicado na tabela. As séries intervalares mantêm leituras de valores limitadas a um dia.
O histórico máximo pode produzir mais HTML do que o objetivo de 250 kB. A aceitação desta
extensão conserva o histórico completo em vez de truncar observações; o resultado medido,
condições de carga e exceção de orçamento estão no relatório de entrega. Compressão local
não é uma medição da transferência em produção.

Relatório: [notebook-navigation](../superpowers/handoff/reports/notebook-navigation/README.md).
