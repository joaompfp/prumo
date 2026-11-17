# Caderno de indicadores

Estado: implementado no ramo `pipeline-rebuild`; ainda não instalado em produção.

O Caderno reúne até doze séries publicadas numa página. Cada cartão mantém o valor, unidade,
período, fonte, data de recolha, estado e ligação à proveniência da série. Não sobrepõe séries,
não calcula taxas e não altera dados.

## Utilização

A entrada Caderno fica no cabeçalho e rodapé do site. Numa página de série, a ação
"Criar caderno com esta série" abre uma seleção inicial. Nas comparações, a ação equivalente
começa com as duas séries já mostradas.

Dentro do Caderno, pesquise pelo nome do indicador, país ou instituição. "Acrescentar ao
caderno" conserva os cartões que já escolheu. Cada cartão tem "Remover do caderno";
"Limpar seleção" regressa ao caderno vazio. A pesquisa mantém a seleção e não exige JavaScript.

"Ligação limpa para guardar ou partilhar" abre o endereço com as séries escolhidas e sem o
termo de pesquisa. Guarde-o nos favoritos ou copie o endereço do navegador. Outra pessoa que
abra a ligação recebe a mesma seleção. Não há conta, cookie, armazenamento local ou registo
da escolha na base de dados.

O endereço guarda a escolha das séries, não os seus valores. Cada abertura mostra os dados
publicados nesse momento. Quem tiver a ligação pode abrir a seleção; não é conteúdo privado
nem uma análise histórica congelada.

## Disponibilidade e limites

Uma série sem valores publicados, retirada ou sem permissão de redistribuição deixa de
aparecer, com um aviso de quantas séries foram omitidas. As restantes continuam disponíveis.
A ligação limpa conserva apenas as séries que podem ser mostradas nesse momento. Os dados e
histórico originais não são apagados.

O máximo é doze referências no endereço. Pedidos malformados ou acima desse limite recebem
uma página genérica de endereço inexistente; não há truncagem silenciosa. As referências
repetidas válidas são desduplicadas sem mudar a ordem. Uma falha do catálogo ou da base recebe
o erro genérico de indisponibilidade, sem códigos operacionais no texto.

As páginas funcionam em `/caderno` no domínio direto e em `/dados/caderno` no endereço
montado. O parâmetro repetido `s` identifica cada série; `q` é uma pesquisa transitória.
A aplicação não aceita um anfitrião fornecido pelo utilizador. A página pede aos motores de
pesquisa que não a indexem, através de metadados e do cabeçalho `X-Robots-Tag`.

## Operação

Não existe migração nem estado do Caderno para recuperar. Uma instalação autorizada atualiza
apenas site e backoffice, como descrito em [operations.md](operations.md); a ingestão e o
encaminhamento mantêm-se. Um recuo de código não apaga conteúdo do sistema de gestão de
conteúdos nem observações estatísticas. Os endereços do Caderno voltam a funcionar quando o
código que os suporta regressar.
