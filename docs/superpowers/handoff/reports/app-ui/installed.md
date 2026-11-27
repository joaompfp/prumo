# Interface de aplicação instalada

Revisão instalada `733a5362ca0c90ccacf4f5c447c79cdde3a2516f`, runtime `5e68fd0`. Merge fast-forward e push confirmados. A CI exata [45913029165](https://github.com/joaompfp/prumo/actions/runs/45913029165) passou 3.424 testes, com 43 saltados, sete de rede excluídos e três avisos. Os testes de navegador saltados foram exercitados localmente: 95 testes na cópia limpa, incluindo as regressões de toque, rato, teclado, layout e alvos do cabeçalho; os dois módulos corrigidos de impressão/transformações passaram 48 testes. A diferença entre runtime e revisão de CI contém apenas esses testes.

A UI tem navegação direta, ações primárias/secundárias distintas, grupos semânticos nas definições e superfícies próprias para gráfico, leitura e informação. A escala de leitura, carmim, ícone, fontes e limite de quatro algarismos significativos mantêm-se. O Caderno continua exploração por endereço; comparativos e homepage continuam propriedade do CMS. A passagem editorial L4 não foi publicada nem encerrada.

## Ativação e correção operacional

O prebuild de contexto separado preservou os serviços e o checkout ativo. A primeira ativação, às 00:01 UTC de 27/11, manteve o site a responder 200 mas o backoffice falhou ao importar `presentation/notebook.py`. O `umask 077` aplicado ao materializar o checkout tinha criado código em modo 0600 e diretórios do contexto em 0700; o leitor root podia arrancar e o Admin uid 1000 não podia ler o módulo. O timeout de readiness e os reinícios desse primeiro contentor não são apresentados como uma ativação saudável.

Foram repostos apenas os modos dos ficheiros de runtime versionados e dos seus diretórios nos dois contextos de código, preservando o bit executável de Git. A base, WAL/SHM, segredos e proprietário dos dados não foram alterados. Depois da reconstrução pelos aliases estabelecidos, os dois leitores arrancaram saudáveis às 00:05:14 UTC. A importação e os 139 ficheiros públicos/de pré-visualização foram confirmados como legíveis sob uid 1000. Os recibos originais e a reparação estão em `f0nix:/home/joao/prumo-operations/app-ui-release-20261126`; para futuras instalações, materializar código com `umask 022` dentro de uma pasta operacional privada.

Leitores finais: web `3df68917`, imagem `a15299e5`; Admin `38f8892d`, imagem `307f5eb6`. O worker mantém a identidade completa `fd1f7b57`, imagem `8679a19d`, arranque de 23/11 às 08:32:43 UTC e zero reinícios. Esquema/migrações e todos os hashes de documentos, versões e eventos do CMS coincidem com a amostra imediatamente anterior à ativação. Integridade rápida válida, sem violações de chaves estrangeiras. Não houve migração, recolha, publicação de conteúdo ou alteração de Authelia/Traefik.

## Aceitação instalada

Passaram 512 verificações públicas em 28 casos nos dois endereços, incluindo CSS exato, menus/definições abertos, alvos sem sobreposição, gráfico real, leitura por teclado, tipografia e largura. O percurso nativo público passou 27 verificações, com e sem JavaScript, incluindo seleção conjunta, aplicação das definições, foco e impressão. Os nove editores passaram 54 verificações; as duas pré-visualizações privadas passaram 26. As 36 verificações de estado/acesso passaram depois da ativação e novamente às 00:17 UTC.

Os oito casos de coordenadas e seis CSV mantêm os valores originais, com a exceção delimitada da hora de exportação. Não houve erros da aplicação/CSP nem pedidos para outras origens nos casos concluídos; o aviso preexistente da camada partilhada `vr` fica separado. A aceitação humana com leitor de ecrã mantém-se aberta.

A primeira matriz pública alargada excedeu o timeout de 400 segundos e não produziu recibo concluído. Não é contada como passagem. A matriz local completa passou 1.276 verificações em 70 casos e dez larguras; a aceitação instalada foi concluída através do percurso menor explicitamente descrito acima, sem enfraquecer verificações de valores, alvos, fontes, CSS ou origens.

## Observação e recuo

Observação concluída às 00:20:14 UTC: 900,036113 segundos, 29 amostras com todos os campos iguais, leitores saudáveis e zero reinícios. As 36 verificações finais de estado/acesso passaram novamente às 00:21:11 UTC, com worker, esquema/CMS e alterações alheias de infraestrutura preservados. O pedido público HTML ao Admin respondeu 302 para Authelia; o primeiro verificador sem Accept HTML recebeu 401 e falhou a expectativa de redirecionamento. A negociação HTML foi depois verificada com 302, sem afrouxar recusas de acesso ou alterar o encaminhamento. A prova técnica não é um login humano.

Recuo: checkout anterior `2c784a125ff1e8ace664d881b9d466c0e5dc2e82` e tags exatas `prumo:rollback-app-ui-20261126` / `prumo-backoffice:rollback-app-ui-20261126`, que apontam para as imagens antigas realmente em execução antes da ativação. Parar apenas o leitor público com bind mounts antes de repor código, materializar com modos legíveis e recriar os leitores pelos aliases normais. Não restaurar a base nem operar ingestão para este recuo de apresentação. Scripts datados são recibos, não procedimentos para repetir sem validar o estado atual.
