# Componentes públicos e densidade da interface

## Âmbito

Pedido: reduzir um pouco a tipografia e rever padding, botões e identidade de
aplicação do frontend. A escolha de biblioteca ficou ao critério técnico.
Bootstrap 5.3.9 local fornece componentes; ECharts mantém a visualização existente.
O subconjunto tem 52.035 bytes sem compressão e recibo SHA-256 reproduzível.
Não foi introduzido JavaScript de Bootstrap ou outro modelo de renderização.

Implementação inicial: `cd2083a` e `6cf11c0`. Corpo público 22 px, navegação e
controlos cerca de 19-20 px, metadados desde 16,5 px, alvos de ação pelo menos
44 px. Fonte e identidade mantidas; Admin conserva a própria escala e Tabler.

## Revisão independente e correções

O parecer de qualidade foi aprovação condicionada, sem defeitos de dados,
autenticação ou formulários, com os seguintes problemas de cascata corrigidos:

- Reboot aumentava h4-h6 acima dos títulos de secção: escala explícita de evidência.
- Links únicos de cartões ficavam centrados: alinhamento igual às ações múltiplas.
- Mais perdia a indicação da secção atual: restaurado estado visual.
- Paginação continuava na impressão e tinha alvo inferior a 44 px: ambos corrigidos.
- Pesquisa do menu móvel perdia cantos e tinha margem negativa: exceção local à
  especificidade de input-group, verificada no DOM real, não só no texto CSS.

O percurso nativo sem JS encontrou ainda scroll suave global introduzido por
Reboot, com controlos em movimento ao passar de definir para aplicar. O tema
repõe scroll imediato; o mesmo percurso passou sem espera artificial/force click.
Conservam-se os recibos iniciais falhados. Um primeiro seletor do verificador de
cascata confundiu o formulário com o seu input-group; foi corrigido conforme o
HTML real, mantendo as verificações de cantos e margens. O parecer visual usou
capturas com dados reais; alegações de tamanhos, datas e conteúdo não visível
foram validadas contra DOM e âmbito antes de decidir alterações.

## Evidência antes da instalação

O controlador passou 81 testes focados, depois 63 após as primeiras correções e
77 após a revisão final de estilos. Ruff do runtime, apresentação, Admin, testes
e script de vendoring limpo. A matriz de navegador numa cópia online isolada de
produção passou 1.556 verificações/70 casos de 320 a 1920 px; a ronda final e as
verificações do commit exato são registadas separadamente. O percurso nativo
final passou 28 verificações com e sem JavaScript e hash integral da cópia igual;
a prova de cascata corrigida passou 13 verificações. O ensaio não altera o CMS.

Não se confunde o conjunto de testes focados com a suite integral. A CI exata,
a ativação, os resultados públicos e a observação ficam no recibo installed.md
apenas depois de ocorrerem. Aceitação humana com leitor de ecrã continua aberta.

## Fronteiras e recuperação

Não há migração nem alteração de dados, observações, precisão, payload,
coordenadas, CSV, unidades ou direitos. Conteúdo do CMS continua a ter rascunho,
publicação e histórico; não é substituído por páginas fixas. Tooltip de desktop e
leitura móvel sob o gráfico mantidas. A instalação limita-se a web e Admin pela
pré-visualização partilhada. Recuo só de código/imagens, preservando CMS e worker.

Plano: `../../../plans/2026-11-27-public-component-system.md`.
Scripts de aceitação: browser_check.py, workflow_check.py e cascade_check.py.
Recibos integrais locais: `/home/joao/.hermes/cache/scratch/prumo-frontend-release`.
A população aceite e capturas finais relevantes serão arquivadas na instalação.

## Verificação do commit enviado

No checkout destacado de `acef14b`, o controlador verificou as origens dos imports,
passou 75 testes focados, incluindo Chromium real, e ruff. O verificador de
navegador desse checkout passou 312 verificações/14 casos sobre o runtime com os
mesmos bytes de CSS e templates. O percurso nativo passou 28 e a cascata 13.

O ciclo adicional sobre outra cópia de produção criou uma página com texto,
indicador e gráfico publicado; guardou, previu, publicou, confirmou publicamente
e retirou a página. Passaram dez verificações, incluindo hashes iguais das vinte
tabelas fora do CMS. A primeira leitura final falhou porque o escritor do CMS
pôs essa cópia offline em WAL e removeu o SHM ao fechar. O verificador corrigido
preparou apenas a cópia de ensaio em DELETE antes de ler; não fez recuperação
no leitor nem tocou na base ou nos ficheiros auxiliares de produção. O recibo
incompleto permanece arquivado, separado da passagem concluída.

O primeiro cliente de acompanhamento da CI terminou com HTTP 502 da API GitHub;
a execução remota ainda estava em curso, não foi repetida nem tratada como falha
de testes. Mantêm-se o recibo e a consulta da mesma identidade de execução.
