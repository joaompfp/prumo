# Sistema de componentes públicos

## Objetivo e escolha

Refinar o frontend como ferramenta estatística, com tipografia menos dominante,
controlo consistente e espaçamento deliberado, conforme o feedback do João.
O pedido substitui a obrigação anterior de preservar os 28,05 px públicos.

ECharts mantém a visualização, inspeção e alternativas SVG. Bootstrap 5.3.9 fornece
apenas controlos, formulários, navegação e paginação, locais e com licença MIT.
As duas bibliotecas têm responsabilidades distintas. Um conjunto React como
Mantine/MUI obrigaria a introduzir outra forma de renderização e estado para
resolver esta passagem visual; não é necessário nesta aplicação de templates.
Tabler mantém-se no Admin, sem levar o painel administrativo para o site.

## Fronteiras

A primeira alteração fixa o pacote e a reprodução verificável do subconjunto.
Depois, os templates passam a componentes reais e o tema público torna-se o
proprietário único do seu aspeto. Removem-se os controlos artesanais substituídos.
Layout de descoberta, workspace e inspeção continua nos respetivos ficheiros.

Corpo público 22 px; navegação/formulários cerca de 19-20 px, metadados desde
16,5 px e alvos de ação pelo menos 44 px. A escala do Admin não muda. Mantêm-se
carmim, ícone, fontes locais, precisão, coordenadas, inspeção móvel sob o gráfico,
tooltip desktop, GET nativo, seleção múltipla e conteúdo publicado pelo CMS.

## Aceitação e publicação

Verificar ecrãs de 320 a 1920 px com dados de produção numa cópia isolada, menus
abertos, definições, foco, seleção com e sem JavaScript, SVG/impressão, rascunho e
pré-visualização. Rever a cascata e as colisões de componentes independentemente.
Suite integral da revisão enviada e verificações de navegador no commit exato.

A instalação mantém o âmbito de apresentação já autorizado: só site e Admin para
pré-visualização estática, sem migração, alteração do CMS, ingestão ou edge/auth.
Pré-construir fora dos bind mounts, fixar imagens de recuo, preservar esquema/CMS
e a identidade completa do worker. Verificar os dois endereços e observar leitores
por pelo menos 15 minutos. Só depois marcar instalada no handoff e no roadmap.

## Estado

Instalada em `acef14b` a 27/11 às 02:49 UTC, após CI exata `45929241699`
aprovada: 3.433 testes passaram, 43 saltados e sete de rede excluídos. Correções
de cascata e percurso nativo verificadas. Passaram 624 verificações públicas em
28 casos nos dois endereços, 27 do percurso nativo, 13 de cascata e 32 das
pré-visualizações privadas. Observação concluída às 03:04:22 UTC após
900,036153 segundos e 30 amostras estáveis; as 38 verificações finais passaram
novamente às 03:04:44 UTC. A aceitação humana com leitor de ecrã continua separada. Registo completo em
`../handoff/reports/frontend-toolkit/installed.md`.
