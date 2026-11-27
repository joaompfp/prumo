# Acervo do debate nacional

Data de seleção: 27 de novembro de 2026.
Estado: conteúdo final em aceitação, ainda não publicado em produção.

## Objetivo e contrato

Publicar leituras estatísticas úteis para o debate português, a partir de perguntas encontradas em programas partidários, imprensa e uma pesquisa exploratória de posts públicos no X. A seleção não é uma medição de tendências ou representatividade. As afirmações de partidos e jornais não são observações e não entram nas séries.

A coleção tem quinze gráficos e oito páginas CMS: seis cadernos temáticos, um índice e uma página de referências. O operador pode editar os documentos completos, séries, períodos, transformações, ordem e textos através do backoffice existente. Nenhuma rota, catálogo editorial fixo ou renderer específico desta coleção é acrescentado à aplicação. As páginas usam as publicações CMS; os atalhos para Caderno abrem uma exploração separada do leitor.

## Seleção e limites

| Caderno | Comparativos | Contexto e medida que não substituímos |
|---|---|---|
| Energia e preços | Eletricidade PT/ES/UE; inflação IPC/IHPC | O PS refere a crise dos preços de 2019-2022; o ECO compara preços domésticos em 2026. Banda de consumo fixa não é a média nacional de todas as bandas nem esforço sobre o rendimento.[2][8] |
| Trabalho, produtividade e investigação | Produtividade real por hora desde 2015; custo nominal do trabalho por hora; histórico de I&D | PCP cita despesa em I&D; CHEGA refere um nível relativo de produtividade. Um índice temporal não confirma a distância do nível por trabalhador; custo do empregador não é salário líquido.[1][4][9][12] |
| Contas públicas | Saldo orçamental; dívida PT/ES/UE; taxas de dívida a dez anos PT/DE | A AD cita rácios de dívida históricos; notícias e publicações de 2026 têm períodos trimestrais/semestrais diferentes. Não inserir previsões ou semestres como observações anuais.[3][10][14] |
| Crédito e depósitos | Stocks anuais em base 2015; Euribor a vários prazos | A notícia da RTP trata de taxas de novas operações. IL e LIVRE discutem acesso/oferta de habitação. Os stocks não substituem essas taxas, rendas, preços das casas ou situação dos jovens.[5][7][13] |
| Comércio e indústria | Comércio mensal de bens; indústria por setores; comércio de bens e serviços em % do PIB | A notícia distingue o total e uma exclusão de certas transações. O Prumo só dispõe aqui do total de bens; valores correntes não são volumes e não se confundem com bens e serviços.[11] |
| Demografia | Nados-vivos/óbitos INE; taxas brutas do Banco Mundial | Contagens, denominadores e calendários separados. Não deduzir migração da variação populacional ou do saldo natural. |

Os documentos consultados incluem o manifesto do BE, cuja proposta de imposto é uma proposta, não uma medição de riqueza.[6] Não se fabricou um gráfico para cada partido. Habitação, salários, distribuição, gás e migrações têm lacunas no catálogo e exigem expansão própria das séries.

O programa do LIVRE tem um caminho de ficheiro `/2019/04/`, mas a capa e o texto identificam explicitamente as Legislativas de 2025; o caminho não foi usado para datar o documento. Datas de criação do PDF não foram apresentadas como datas de publicação.

A fonte de I&D já tem informação mais recente noutras publicações do Eurostat, mas esta coleção usa apenas a família já verificada do Banco Mundial, que termina em 2023 nesta preparação. Título e nota identificam o histórico e a ausência de um agregado UE. Não se inseriu manualmente um número mais recente sem a verificação normal da ingestão.

## Operação

`collection.json` é uma fotografia versionada da publicação inicial, não a fonte de conteúdo dos pedidos públicos. Após publicação, o CMS é a autoridade. Alterações posteriores feitas pelo João no editor não devem ser substituídas por uma regeneração deste ficheiro.

O utilitário é um módulo e deve ser invocado a partir da raiz do checkout com `python -m scripts.publish_cms_collection`, não `python scripts/publish_cms_collection.py`: existe outro `scripts/ingest.py` que pode sombrear o pacote quando o caminho de execução é incorreto. `--db`, `--bundle`, `--actor` e `--note` são explícitos; sem `--publish`, apenas faz pré-validação. `--publish` exige `--editorial-db`, que tem de identificar o mesmo ficheiro de dados, incluindo montagens distintas do mesmo inode.

A pré-validação considera a coleção inteira antes de criar documentos. Um endereço já publicado e exatamente igual é preservado sem novos eventos. Qualquer rascunho existente, publicação diferente ou homepage provoca recusa, sem sobreposição. Não existe escrita direta em tabelas nem migração. O utilitário chama `Cms.create` e `Cms.publish`, com ator `operator:jarbas` e motivo que identifica a autorização do João, e lê novamente o alvo e a auditoria.

Cada publicação é atómica, mas a coleção completa não é uma só transação. Uma falha tardia devolve `completed: false`, os alvos já publicados, o eventual rascunho criado e a leitura exata do alvo da falha. Conservar o recibo; rever esse rascunho no backoffice. Não eliminar o rascunho nem o publicar automaticamente para forçar uma repetição. A repetição normal recusa esse conflito e protege o trabalho do operador.

Os links externos do contexto editorial são texto escapado, segundo o contrato atual do CMS. Não são links clicáveis. Os botões de navegação interna, os atalhos Caderno e as fontes estatísticas continuam ligações reais. Um bloco tipado de referências externas é uma melhoria posterior, não uma abertura de HTML livre neste conteúdo.

## Verificação e recuo

A cópia integral da produção é obtida por SQLite online backup com origem só de leitura e `readonly_shm=1`, não pela cópia do ficheiro principal ao vivo. Os ensaios verificam todos os fingerprints das tabelas fora do CMS, esquema e os documentos/revisões/eventos que já existiam, incluindo a homepage.

O ciclo de publicação, repetição sem alteração, conflitos e falha tardia é exercitado. A aceitação dos leitores inclui ambas as bases de URL, gráficos completos, tabela, leitura exata de pontos, atalhos Caderno e visualização móvel/desktop. A edição e pré-visualização são confirmadas no Admin. A aceitação humana com leitor de ecrã permanece separada.

A publicação apenas acrescenta conteúdo no CMS, sem imagens novas de aplicação, migração, reinício de serviços, recolha de dados ou alteração de direitos/encaminhamento. Recuo editorial: retirar primeiro as publicações das páginas desta coleção e depois as dos gráficos, pelo backoffice e com motivo, conservando todas as revisões e os eventos. Nunca restaurar uma cópia antiga da base sobre dados entretanto recolhidos. Se já houver alterações do operador, rever os documentos individualmente antes de qualquer retirada.

Pesquisa completa e arquivos originais: `/home/joao/reports/prumo-debate-20261127/parties/` e `/home/joao/reports/prumo-debate-20261127/press/`. Recibos de aceitação e instalação: `../../superpowers/handoff/reports/national-debate/`.

## Sources

[1] https://www.pcp.pt/sites/default/files/documentos/2025_compromisso_eleitoral_pcp_legislativas.pdf - PCP - Compromisso Eleitoral Legislativas 2025 (PDF, 2025-04-10)
[2] https://ps.pt/wp-content/uploads/2025/04/programa-eleitoral.pdf - PS - Programa Eleitoral 2025 (PDF, 2025-04-14)
[3] https://ad2025.pt/pdf/programa-eleitoral.pdf - AD - Programa Eleitoral Legislativas 2025 (PDF, 2025-04-23)
[4] https://pub-acfa34005415427bb560174ca37a9c6f.r2.dev/Programa%20Eleitoral%20CHEGA%20-%202025.pdf - CHEGA - Programa Eleitoral 2025 (PDF, 2025-04-23)
[5] https://iniciativaliberal.pt/wp-content/uploads/IL_Programa_ACelerarPortugal.pdf - Iniciativa Liberal - Programa Eleitoral 2025 (PDF, 2025-04-10)
[6] https://bloco.org/media/Manifesto_Bloco_legislativas2025.pdf - Bloco de Esquerda - Manifesto Eleitoral Legislativas 2025 (PDF, 2025-04-07)
[7] https://partidolivre.pt/wp-content/uploads/2019/04/ProgramaV1.pdf - LIVRE - Programa Eleitoral Legislativas 2025 (PDF, 2025-05-13)
[8] https://eco.sapo.pt/2026/10/30/preco-da-eletricidade-em-portugal-abaixo-da-media-europeia-mas-gas-para-familias-mais-caro-ate-junho - Preço da eletricidade em Portugal abaixo da média europeia mas gás para famílias mais caro até junho – ECO
[9] https://eco.sapo.pt/2026/09/22/produtividade-de-portugal-face-a-ue-e-mais-baixa-do-que-em-2000 - Produtividade de Portugal face à UE é mais baixa do que em 2000 – ECO
[10] https://eco.sapo.pt/2026/10/21/portugal-foi-o-quarto-pais-do-euro-que-mais-cortou-a-divida-publica-no-ultimo-ano - Portugal foi o quarto país do euro que mais cortou a dívida pública no último ano – ECO
[11] https://www.noticiasaominuto.com/economia/2981361/exportacoes-caem-6-4-e-importacoes-sobem-2-6-no-1-trimestre - Exportações caem 6,4% e importações sobem 2,6% no 1.º trimestre - Notícias ao Minuto
[12] https://eco.sapo.pt/2026/11/13/salario-medio-em-portugal-sobe-49-para-1-696-euros - Salário médio em Portugal sobe 4,9% para 1.696 euros – ECO
[13] https://www.rtp.pt/noticias/economia/juro-dos-novos-depositos-a-prazo-sobe-em-setembro-mas-continua-abaixo-da-media-europeia_n1776320 - Juro dos novos depósitos a prazo sobe em setembro mas continua abaixo da média europeia
[14] https://portugal.gov.pt/gc25/comunicacao/noticias/portugal-regista-excedente-orcamental-de-05-do-pib-no-primeiro-semestre - Portugal regista excedente orçamental de 0,5% do PIB no primeiro semestre - XXV Governo Constitucional
