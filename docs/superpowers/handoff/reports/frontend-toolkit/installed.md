# Componentes públicos instalados

Código `acef14ba0f2733c8b14ebb6ad29b14790b515d04`, enviado e confirmado em
main e `feature/frontend-toolkit`. Instalado no f0nix a 27/11/2026 às 02:49 UTC.
CI exata [45929241699](https://github.com/joaompfp/prumo/actions/runs/45929241699):
3.433 testes passaram, 43 saltados, sete de rede excluídos, três avisos.
Os testes Chromium saltados na CI foram exercitados localmente; não são
apresentados como testes de navegador da infraestrutura GitHub.

## Resultado

Frontend com corpo de 22 px em vez de 28,05 px, controlos e navegação perto de
19-20 px, metadados desde 16,5 px e alvos de ação de pelo menos 44 px.
Bootstrap 5.3.9 local fornece os componentes; ECharts conserva os gráficos.
Não se introduziu React, Bootstrap JS ou CDN. Os templates usam componentes
reais, com tema único e sem a antiga camada duplicada de controlos nativos.
O Admin mantém Tabler e a própria escala; a pré-visualização pública usa o
aspeto do site, servida privadamente pelo Admin.

Botões com hierarquia, formulários e pesquisa consistentes; tamanhos e espaços
revistos, paginação com alvo adequado, menu com contexto ativo, títulos de
evidência sem colisões do reset, foco visível e pesquisa móvel com cantos
corretos. A reposição de scroll imediato elimina a corrida de foco/formulário
introduzida por Reboot. Tooltip desktop, leitura móvel sob o gráfico, identidade
carmim/prumo, valores exatos e limite de quatro algarismos mantêm-se.

A revisão de implementação teve condições, todas corrigidas. A revisão final
independente aprovou sem bloqueadores; a indicação de estado de Mais também
foi comprovada no DOM pelo controlador, além da inspeção CSS do revisor.
As reservas visuais não bloqueadoras ficam limitadas à proximidade de h3/h4 e
à largura analítica maior que a medida da prosa/cabeçalho. Nada abaixo de um
recorte de viewport foi declarado ausente.

## Verificações

Antes da publicação, o controlador passou 106 testes focados e ruff. No checkout
limpo do commit enviado, passaram 75 testes com origens dos imports confirmadas,
incluindo interação/layout reais de Chromium. Matriz numa cópia online dos
dados: 1.556 verificações/70 casos; a ronda final passou 312/14, percurso nativo
28 e cascata 13. Conteúdo original dos payloads e CSV coincidente na mesma cópia.

Um ciclo CMS noutra cópia de produção criou e guardou texto, indicador e gráfico,
pré-visualizou, publicou, confirmou a página e retirou a publicação: dez
verificações passaram e as vinte tabelas fora do CMS mantêm os hashes.
O primeiro verificador final dessa cópia recusou o WAL sem SHM; a preparação
posterior foi feita pelo proprietário exclusivo apenas da cópia isolada, não
por um leitor nem em produção. Os recibos inicial e corrigido estão separados.

Em produção, passaram 624 verificações/28 casos públicos nos dois endereços,
27 de percurso nativo com/sem JS, 13 da cascata, 32 das pré-visualizações privadas
e 38 de estado/acesso. Os bytes exatos do toolkit e CSS são os referenciados
pelas páginas em cada endereço, incluindo os assets do Admin. Pedido HTML
anónimo ao Admin devolve 302 para Authelia; recusas de acesso indevido mantêm-se.
Não se confunde esse teste técnico com login ou leitor de ecrã humano.

## Ativação e preservação

Pré-construção de fonte destacada enviada, com código legível sob umask 022;
206 ficheiros de runtime e diretórios verificados. Checkout ativo, serviços,
esquema, CMS e mudanças alheias de infraestrutura permaneceram iguais durante
a construção. Na ativação parou-se apenas o leitor público com bind mounts,
avançou-se para o SHA aprovado e recriaram-se site e Admin pelos aliases normais.

Web `ad076093`, imagem `774d2bde`, e Admin `93438d63`, imagem `81edb4e1`, arrancaram
às 02:49:22 UTC, saudáveis e sem reinícios. O worker `fd1f7b57`, imagem `8679a19d`,
arranque de 23/11 às 08:32:43 UTC e zero reinícios, conserva todos os campos.
Esquema/migrações e hashes de documentos, versões e eventos do CMS iguais à
amostra imediatamente prévia. Integridade rápida válida, zero violações FK.
Não houve migração, recolha, escrita editorial ao vivo, direitos, ownership ou
alteração do encaminhamento/autenticação. A fonte de dados continua a recolher;
não se exige congelar o hash de toda a base viva.

## Observação e recuo

Observação concluída às 03:04:22 UTC após 900,036153 segundos e 30 amostras
com identidade/imagem/arranque, reinícios e readiness iguais ao baseline.
Leitores saudáveis, sem reinícios; as 38 verificações finais passaram novamente
às 03:04:44 UTC com esquema, CMS, worker e mudanças alheias de infraestrutura
intactos. Aceitação humana com leitor de ecrã e gates separados de fontes/worker
continuam abertos.

Recuo: código anterior `72d1cdaf7a2c53f78f6f88687a3ec605112ad7ba` e imagens
antigas realmente em execução, fixadas nas tags `rollback-frontend-toolkit-20261127`
dos dois leitores. Web anterior `a15299e5`; Admin `307f5eb6`. Parar o leitor com
bind mounts antes de repor código, recriar leitores pelos aliases sem restaurar
a base e sem reiniciar a ingestão. Os scripts datados são recibos, não comandos
para repetir sem confirmar o estado.

Diretório operacional privado:
`f0nix:/home/joao/prumo-operations/frontend-toolkit-20261127`.
Roadmap: `/home/joao/vaults/projects/prumo/roadmap-e-implementacao.md`.
L4, agrupamento semântico e análises datadas/IA aprovada continuam separados.
