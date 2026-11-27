# Revisão da coleção: decisões e verificação

## Pareceres independentes

Os pareceres originais estão em `/home/joao/reports/prumo-debate-20261127/statistical-review.md` e `/home/joao/reports/prumo-debate-20261127/publisher-review.md`. São auto-relatos dos revisores, sujeitos à verificação pelo controlador.

## Estatística e contexto

- Retirada a sobreposição EUR/kWh semestral com taxa homóloga mensal do IPC. Uma nota sobre causalidade não tornava útil uma composição visual arbitrária.
- Não reutilizado o gráfico antigo `taxas-juro-credito-depositos`, evitando duplicação no novo caderno. A alegação do revisor de que esse gráfico apresenta a taxa soberana como taxa hipotecária não se confirma: a nota publicada nomeia explicitamente a Euribor e a rendibilidade das obrigações do Tesouro a dez anos. O documento antigo foi preservado, sem alteração de operador.
- I&D conserva a família verificada do Banco Mundial, termina em 2023 na preparação e não inclui agregado UE. Título e nota tornam-no explícito, incluindo a existência de dados Eurostat posteriores ainda não integrados. Introduzir valores de 2024 de outra fonte só para responder ao parecer violaria o âmbito e a proveniência.
- Sinal do saldo confirmado no JSON Eurostat arquivado: `na_item=B9`, `Net lending (+)/net borrowing (-)`. As observações servidas portuguesas são 1,1 em 2023 e 0,7 em 2024/2025. Positivo é excedente. O nome técnico `gov_deficit_pct_gdp` não altera a convenção nativa.
- A citação da AD é explicitamente histórica, não um ponto novo de dados nem um veredicto de fact-checking. A referência da publicação governamental está associada ao saldo do primeiro semestre, não à dívida. O parecer tinha confundido esses âmbitos; não se inseriram números fixos atuais em prosa dinâmica.
- A capa e a segunda página do PDF do LIVRE identificam as Legislativas de 2025; a citação está na página física 100. O segmento `/2019/04/` do URL não data o conteúdo. Todas as trinta citações do corpus foram novamente localizadas nas páginas originais pelo controlador; apenas as referências relevantes foram usadas na coleção.
- Custo do trabalho explicita frequência anual, base 2020=100 e atividades B-N. A nota distingue custo nominal do empregador de salário líquido ou mediano. Produtividade rebaseada explicita evolução temporal, nunca nível relativo entre países nem produtividade por trabalhador.
- Nados-vivos e óbitos têm frequência anual, geografia PT e referências INE próprias. O caderno não calcula um saldo entre universos diferentes e exige verificação das definições de residência para novas combinações. As taxas por mil habitantes são mostradas num gráfico separado, da mesma fonte Banco Mundial.
- O gráfico de stocks anualizados foi exercitado: a última observação desenhada é 2025, excluindo 2026 incompleto. IPC e IHPC usam as observações mensais originais até outubro de 2026; não se inventaram meses intermédios.
- O diretório não usa `themes`: esse bloco aceita apenas temas do catálogo de séries e não páginas editoriais. Usa blocos existentes, com ação interna para cada um dos seis cadernos. Retirada a abertura hero duplicada, que criava espaço vazio no móvel. Não houve mudança de CSS ou biblioteca.
- Habitação, salários, desigualdade, gás, taxas de novas operações e migrações permanecem numa lista explícita de expansão; não se publicaram substitutos enganosos. A leitura do BE foi usada para distinguir proposta tributária de medição, não para fabricar uma comparação indisponível.

## Publicação e preservação

- O módulo é invocado por `python -m scripts.publish_cms_collection`; a invocação direta do ficheiro não é um contrato suportado devido ao `scripts/ingest.py` já existente. O manual dá o comando correto.
- Acrescentado recibo de falha parcial, com `completed: false`, alvo da falha, leitura exata e distinção entre rascunhos e publicações. Um teste provoca recusa no segundo documento após o primeiro publicado. Não há conclusão positiva após esse prefixo bem-sucedido.
- A leitura e a escrita devem apontar para o mesmo inode de SQLite, permitindo os dois mounts canónicos da mesma base e recusando ficheiros diferentes. O teste com duas bases confirma ausência de escritas.
- Cada identidade é verificada antes da primeira criação. Rascunhos do operador e publicações diferentes são recusados, sem edição; publicações iguais são preservadas sem novas revisões/eventos. Um ensaio integral de repetição confirma igualdade de todos os fingerprints CMS.
- As duas falhas iniciais dos coletores de evidência eram de configuração local: dependência de parser HTML não instalada e ausência de SHM numa cópia offline WAL. O coletor passou a usar `HTMLParser` da biblioteca standard e a manter uma conexão proprietária apenas na cópia isolada. Nenhuma recuperação ou alteração de sidecars foi feita na base live. Os primeiros recibos não são considerados aprovações.
- URLs externas em texto são uma limitação explícita do CMS atual; preservar texto escapado foi preferido a introduzir HTML livre ou um modelo novo neste lote editorial. Ligações estatísticas e internas continuam reais. Um bloco tipado de referências externas fica no roadmap.

## Resultado verificado antes da publicação

`isolated-final.json`: 188 verificações aprovadas, 23 documentos, quinze gráficos e oito páginas; esquema e vinte tabelas não-CMS preservados, além de todos os documentos/revisões/eventos anteriores. `browser-final.json`: 408 verificações aprovadas em Chromium, com dados reais, móvel/desktop, gráficos e leitura dos valores; zero erros/avisos locais. Os testes focados passaram 105 casos. Estes resultados são de cópia isolada, não de produção.
