# Interface de aplicação

## Entrega verificada localmente

Implementação `20df28e`, correção geométrica `5e68fd0`; revisão de testes `733a536` sem alteração dos inputs de runtime. O site passa a separar navegação, ações, configuração e leitura. Carmim, fontes locais, precisão de até quatro algarismos significativos, conteúdo/histórico do CMS e comportamento do motor dos gráficos mantêm-se.

`app-shell.css` passa a ser dono do cabeçalho e dos papéis das ações. `workspace.css` é dono da superfície analítica e das definições. As regras substituídas foram retiradas de `prumo.css`. O catálogo mantém o mesmo formulário nativo para pesquisa, filtros e seleção; o Caderno mantém os mesmos parâmetros GET, com o inspetor fora do formulário de definições. Os novos textos de grupo pertencem a `presentation/notebook.py`.

## Evidência

- Revisões independentes de design e engenharia aprovadas nos âmbitos declarados. Os pareceres não substituem os testes do controlador; a execução de testes do revisor foi impedida pelo ambiente isolado.
- Suite focada de desenvolvimento: 165 passaram. Outra passagem de 57 testes incluiu interação real dos gráficos, layout, tipografia, identidade e homepage do CMS.
- Cópia limpa do commit final de runtime: 95 passaram, incluindo os nove cenários de não sobreposição e 18 regressões reais de gráficos. Ruff passou. O commit de testes foi exercitado nos dois módulos completos: 48 passaram.
- Matriz com a cópia real da produção: 1.276 verificações / 70 casos, de 320 a 1920 px. A versão neutra do verificador acrescenta a recusa de tooltip transitória antes das capturas; 256 verificações / 14 casos adicionais passaram.
- Percurso nativo: 28 verificações, com e sem JavaScript, incluindo seleção conjunta, aplicação das definições, foco, impressão do SVG e das notas/proveniência. A base isolada mantém o SHA-256 integral `72044db83620d3458259bd2c725213f63442bba5ae5b2312e1b478c6a9c1795c`, igual à cópia remota original.
- A 390px, o cabeçalho final mede 117px; o gráfico mantém 328x264px e começa em Y=468,58. Tamanhos funcionais preservados; a largura do desenho desconta a nova moldura analítica.

As capturas são do conteúdo real, com fontes carregadas e scroll em zero. A captura desktop anterior à neutralização pode conservar um estado de inspeção; preferir as capturas neutras finais para avaliação do desenho. `manifest.json` identifica as cópias e os arquivos por hash.

## Falhas preservadas

Os primeiros testes de desenvolvimento encontraram expectativas ligadas ao HTML antigo e à localização monolítica do CSS; os recibos iniciais permanecem nos arquivos. O verificador inicial também chamou um método inexistente do Playwright; a correção cria uma página por caso e não altera a aplicação.

A subida da letra do botão Mais revelou 8,3px de interseção com a área de navegação móvel. A correção reserva altura à linha da marca e limita o seu alvo; os testes medem as caixas pintadas e não apenas o overflow da página.

A primeira CI completa de `5e68fd0`, execução `45911984349`, terminou com 3.422 passados e duas falhas de expectativa: CSS de impressão movido e ícone na ação de limpar. Ambos os módulos corrigidos passaram integralmente. O recibo original está arquivado sem sanitizar; essa execução não é apresentada como uma passagem integral verde. A execução anterior de `20df28e` foi cancelada por ter sido substituída, não contou como aprovação.

## Instalação

Instalada a revisão `733a536`, com runtime `5e68fd0`, após CI integral verde. O relatório `installed.md` regista a ativação, a correção dos modos de código, os testes públicos/Admin e a observação dos leitores. A aceitação técnica não substitui a avaliação visual do João.

O âmbito é apenas site e backoffice para a pré-visualização estática. Sem migrações, alterações de dados/conteúdo, recolha, reinício do worker ou configuração de Authelia/Traefik. Prebuild e recuo fixado em `f0nix:/home/joao/prumo-operations/app-ui-release-20261126`. Recuperação: checkout anterior `2c784a1` e tags exatas `prumo:rollback-app-ui-20261126` / `prumo-backoffice:rollback-app-ui-20261126`, sem restaurar a base.

A aceitação humana com leitor de ecrã permanece pendente. A composição editorial L4, agrupamento de indicadores e análises datadas/IA não são encerrados por esta alteração visual.
