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

Implementação e primeira revisão concluídas; correções de cascata e aceitação
com dados reais em curso. Ainda não instalada.
