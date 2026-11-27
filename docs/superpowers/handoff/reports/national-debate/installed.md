# Acervo do debate nacional publicado

Estado histórico: o proprietário rejeitou a secção agregadora. Às 09:55-09:56 UTC de 27/11 os dois wrappers foram despublicados, sem retirar os quinze gráficos nem os seis cadernos das secções existentes. As referências de contexto passaram para cada caderno. O estado atual e a prova estão em `../editorial-scope/README.md`; os URLs agregadores abaixo já não são entradas públicas ativas.

## Estado instalado

Publicação editorial efetuada no f0nix a 27 de novembro de 2026, entre 04:31:11 e 04:31:32 UTC. Conteúdo e utilitário versionados em `9087bc47a67ca3f748eb57b108362b11a637f510`, enviado e integrado em main. Não houve instalação de código da aplicação. O runtime web/Admin mantém `acef14b`, com checkout de instalação anterior `391d12b`; as mesmas imagens, contentores, arranques e reinícios permanecem.

A coleção acrescentou quinze gráficos, seis cadernos temáticos, um índice e uma página de referências: 23 documentos, 23 revisões iniciais e 46 eventos de criação/publicação, atribuídos a `operator:jarbas` com motivo explícito de publicação pedida pelo João. Tudo é conteúdo CMS editável no backoffice. Os pedidos públicos não carregam o manifesto nem uma definição customizada em código.

Entrada pública: `https://joao.date/dados/paginas/debate-nacional`.
Editor do índice: `https://joao.date/dados/admin/cms/page/debate-nacional`.
Biblioteca e páginas: `https://joao.date/dados/admin/cms`.

Cadernos: energia e preços; trabalho, produtividade e investigação; contas públicas; crédito e depósitos; comércio e indústria; demografia. Cada um referencia gráficos publicados e liga a uma seleção independente no Caderno. As publicações editoriais não expõem formulários para substituir a composição. Os dados atualizam-se com as séries servidas; o contexto político e jornalístico fica identificado como uma seleção datada.

## Aceitação

- Pré-validação live: 23 documentos prontos, sem colisões, esquema e tabelas preservados. A publicação usa os mesmos mounts e o mesmo inode da base, através do serviço CMS e do writer restrito.
- Testes locais focados: 105 casos passaram; a repetição final de coleção/tipografia passou 27. A cópia limpa do commit `9087bc4` voltou a passar os 27, com importações locais comprovadas e ruff limpo.
- Cópia integral de produção: 188 verificações aprovadas; esquema, vinte tabelas não-CMS e todos os documentos/revisões/eventos existentes preservados. A repetição da coleção foi um no-op completo.
- Navegador isolado: 408 verificações, zero erros/avisos. Edição real no Admin: 196 verificações, todos os documentos preenchidos e previews estáticos; alteração da ordem de séries, guarda privada e publicação exercitadas, com dados e homepage preservados.
- Produção: 814 verificações no Chromium, ambos os endereços e ecrãs de 390/1440 px; todas as séries desenhadas e valores exatos de inspeção. Nenhum erro de aplicação. Noventa e dois avisos preexistentes do cabeçalho partilhado `Permissions-Policy` sobre `vr`, mantidos como exceção explícita.
- Admin live, apenas leitura: 137 verificações por ligação interna autenticada de serviço. Confirmados os 23 documentos, corpos publicados/rascunhos, atribuição de auditoria, séries, eixos, períodos/transformações e pré-visualizações. A entrada pública sem sessão continua a desafiar pelo Authelia. Não é uma afirmação de login humano ou leitor de ecrã.
- `production-acceptance.json` fecha os alvos exatos e confirma igualdade completa da identidade/imagens/arranques/reinícios dos três serviços. Não houve migração, alteração de direitos ou do encaminhamento, restart do worker ou edição da homepage.

A CI exata `45940395441`, de `9087bc4`, terminou aprovada: 3.442 testes passados, 43 saltados, sete de rede excluídos e três avisos de teste. Os jobs de lint/testes terminaram com sucesso; as anotações de migração Node das actions e o código 128 da limpeza de git não alteram a conclusão dos jobs e ficam separados dos resultados da aplicação. Uma revisão posterior apenas documental não é apresentada como uma nova execução integral.

## Concorrência da ingestão

O primeiro coletor live terminou com `completed: false` porque exigia igualdade absoluta das tabelas enquanto o worker continuava ativo. Esse recibo original fica em `production-publication.json`; não foi apagado, reclassificado como passagem nem usado para repetir a escrita.

Os 23 documentos já estavam publicados e a sua leitura confirmou o corpo esperado. A única alteração fora do CMS nesse intervalo foi a adição de `raw_fetch.id=1723`, fonte INE, execução 166, às 04:31:21 UTC, com resposta HTTP 504 e 74 bytes. A verificação posterior calculou o hash das 1.722 linhas preexistentes e obteve exatamente o hash anterior. Nenhuma linha preexistente foi alterada; observações, quarentena, séries, derivados e esquema ficaram iguais.

`concurrent-ingestion.json` atribui a adição ao recibo agendado e `production-acceptance.json` combina essa evidência com os alvos publicados, os leitores e a preservação. A resposta de rede do INE permanece uma ocorrência operacional separada; não foi alegada frescura de todas as fontes nem iniciado trabalho sobre o coletor.

## Recuo e continuação

Recuo editorial pelo Admin: retirar a publicação das páginas desta coleção e só depois a dos gráficos que não sejam usados noutros conteúdos. Conservar o histórico, verificar alterações posteriores do operador e indicar motivo. Não restaurar uma base inteira, apagar linhas ou reiniciar serviços para retirar conteúdo editorial.

Os programas de 2025 servem como contexto, sem veredictos partidários ou preenchimento de dados. Os valores estatísticos vêm das séries verificadas. A cobertura limita novos temas sobre salários, rendas/preços da casa, esforço financeiro, gás e migrações; a expansão dessas famílias segue os contratos normais de ingestão, fora deste lote. I&D é identificado como histórico do Banco Mundial até 2023 nesta preparação, mesmo havendo dados posteriores noutra fonte.

Melhoria futura de CMS: bloco tipado de referências externas clicáveis. Hoje os URLs de contexto são texto escapado, enquanto ligações internas, atalhos Caderno e fontes estatísticas são clicáveis. Não se abriu HTML livre para resolver esta limitação.

Fonte editorial e instruções do utilitário: `../../../../editorial/debate-nacional-2026-11-27/README.md`. Pesquisa e pareceres originais: `/home/joao/reports/prumo-debate-20261127/`. Recibos duráveis da operação no host: `f0nix:/home/joao/prumo-operations/debate-20261127/`. Manifesto e utilitário podem ser transmitidos ao contentor por cápsula stdin verificada; não se assume que scripts/documentação do git fazem parte da imagem Docker.
