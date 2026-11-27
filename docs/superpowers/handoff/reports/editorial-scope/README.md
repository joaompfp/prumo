# Correção de âmbito editorial

## Pedido

O João pediu para popular as secções existentes com comparativos e cadernos relevantes. O índice "Debate nacional" e a página agregada de referências foram uma extrapolação não pedida. A correção retira essas publicações, sem substituir a taxonomia nem perder os gráficos ou as fontes úteis.

## Alteração delimitada

- Retirar a publicação de `page/debate-nacional` e `page/fontes-debate-nacional`, conservando rascunhos, revisões e auditoria.
- Manter os seis cadernos nas secções existentes `economy`, `energy` e `demography`.
- Remover as ligações ao agregador retirado e incluir em cada caderno apenas as referências que ele cita.
- Preservar todos os quinze comparativos, qualquer conteúdo anterior e a homepage. Não criar secções, rotas, documentos ou categorias.
- Usar apenas `Cms.save`, `Cms.publish` e `Cms.unpublish`, com versões esperadas, ator e motivo; nenhum SQL de escrita, migração ou instalação de runtime.

O plano explícito é `../../../../editorial/2026-11-27-existing-sections-correction/plan.json`. O manifesto anterior é evidência histórica, não deve voltar a ser publicado.

## Verificação anterior à operação

Os 28 testes de coleção/serviço CMS passaram e os 18 testes de tipografia passaram. Ruff e a verificação do diff passam. O controlador executou 118 verificações numa cópia consistente da base em `/home/joao/f0nix/prumo-data/prumo.sqlite3`, aberta só para leitura pela função protegida `read_db_readonly`: alterações exatas, descoberta nas secções existentes, quinze comparativos desenhados, wrappers a 404 nos dois mounts, repetição sem escrita, recusa de rascunho privado e igualdade de todas as tabelas fora do CMS/esquema.

Revisão independente de segurança e âmbito aprovada. O revisor confirmou cobertura das citações e igualdade das referências, e ensaiou a correção somente numa cópia local. A verificação de produção é responsabilidade do controlador, não fica estabelecida por esse relato.

Tentativas preliminares do controlador: uma cópia antiga tinha WAL sem SHM, e outras duas eram snapshots anteriores à publicação/refinamento final. Os guardas recusaram essas entradas; não houve escrita em produção. A passagem final usa uma cópia com os corpos realmente publicados. Os avisos FastAPI/httpx dos testes são separados do resultado.

## Operação

Correção aplicada em produção entre 09:55:45 e 09:56:01 UTC de 27/11/2026, com leitura exata dos oito alvos e dos eventos de auditoria. Os seis cadernos estão publicados em versão 4; os dois wrappers estão despublicados em versão 3. Foram acrescentadas seis revisões e catorze eventos, sem novos documentos. Os quinze comparativos e todos os documentos/históricos não-alvo, incluindo a homepage, ficaram idênticos.

`production.json` confirma igualdade de todas as tabelas fora do CMS e do esquema. `public.json` contém 196 verificações HTTP aprovadas nos dois endereços: páginas descobertas nos temas existentes, comparativos desenhados, nenhum link órfão e os dois wrappers a 404. `services-before.txt` e `services-after.txt` são iguais: nenhuma instalação, recriação ou reinício de serviço. O runtime permanece o anterior. Uma leitura separada do CMS após a operação confirmou novamente os corpos e versões.

A publicação de produção e a leitura posterior dos alvos são registadas em `production.json` e `public.json`. Não repetir uma operação parcialmente concluída para apagar um recibo de falha. Se existir rascunho divergente, parar e rever o alvo no editor; não sobrescrever trabalho do João.

Recuo, apenas se solicitado: recuperar as revisões anteriores como novos rascunhos no CMS e publicar deliberadamente. Não apagar história nem restaurar uma base antiga sobre os dados recolhidos entretanto.
