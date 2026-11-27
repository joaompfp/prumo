# Interface de aplicação: navegação, ações e definições

## Âmbito

Pedido do João: manter a funcionalidade aprovada, especialmente a leitura móvel abaixo do gráfico, e reformular a UI pública para parecer uma ferramenta estatística. Ações, definições e informação precisam de funções visuais distintas. A escala de leitura, carmim, ícone de prumo, quatro algarismos significativos e as fontes locais mantêm-se.

## Entrega

- Navegação principal diretamente acessível em telemóvel e desktop: Catálogo, Comparações e Caderno. Um menu nativo Mais reúne pesquisa secundária, temas e informação institucional. O destino ativo é preparado uma vez no modelo de navegação.
- Separar a propriedade dos estilos: shell e ações em `app-shell.css`, área analítica em `workspace.css`, descoberta em `discovery.css`, leitura de pontos em `chart-inspector.css`. Retirar as regras substituídas do monólito em vez de sobrepor outra camada indefinida.
- Superfície branca e delimitada para o gráfico, títulos de ferramenta em Lato, leitura de pontos estruturada. Acrescentar é primário; Configurar é secundário; limpar fica separado.
- Definições com grupos semânticos de período/escalas, tratamento, séries e dia UTC. Mesmos parâmetros GET e limites existentes; o ponto do gráfico não pertence ao formulário de configuração.
- Filtros e seleção do catálogo separados visualmente. Em telemóvel, a barra de seleção não tapa resultados enquanto se percorre a página.
- Entrada CMS mais compacta por apresentação, sem substituir conteúdo, ordem, rascunhos ou publicações do operador. Isto não conclui a futura passagem editorial L4.

## Aceitação

Navegador com dados reais em 320, 360, 390, 600, 768, 900, 901, 1120, 1440 e 1920 px. Abrir efetivamente menus e definições, validar foco e hierarquia das ações, manter controlo por toque/rato/teclado e provar seleção múltipla nativa com e sem JavaScript. SVG, fontes, notas e proveniência continuam na impressão; o gráfico mantém altura útil e não encolhe letras para caber. A aceitação humana com leitor de ecrã permanece separada.

Revisões independentes de design e engenharia, testes do commit limpo, CI integral da revisão instalada e ensaio de navegador nos dois endereços públicos. Preservar imagens e recibos iniciais, incluindo falhas dos verificadores corrigidos.

## Instalação e recuo

Apenas site e backoffice, que incorpora a pré-visualização pública estática. Sem migração, escrita no CMS, recolha, reinício da ingestão ou alteração de Authelia/Traefik. Pré-construir a revisão enviada antes de avançar o checkout com bind mounts. Fixar as imagens antigas, preservar esquema e hashes do CMS/histórico e comparar todo o estado do worker antes/depois. Observar os leitores durante pelo menos 15 minutos e atualizar o handoff e o roadmap com a revisão instalada. O recuo é só código/imagens, sem restaurar a base.

## Estado

Implementação, revisões independentes, CI integral e instalação concluídas em `733a536` (runtime `5e68fd0`). A aceitação pública, os percursos nativos e as pré-visualizações passaram; o recibo da observação final dos leitores fica em `../handoff/reports/app-ui/installed.md`. A passagem editorial L4 e a aceitação humana com leitor de ecrã continuam separadas.
