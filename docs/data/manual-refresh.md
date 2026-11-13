# Atualização manual com ficheiros originais (Banco Mundial e E-REDES)

A ingestão automática já está instalada e em execução no f0nix, no contentor
`prumo-ingest`, com base `/data/prumo.sqlite3` e evidência `/data/raw` partilhadas com
`prumo`. A observação real de 24 horas da tarefa 18 continua aberta. Não parar o
serviço nem importar dados durante essa janela sem autorização do dono. Uma
interrupção exige uma nova janela de observação.

Este procedimento serve quando a rota de uma fonte falha no servidor: capturar um
pacote auditável noutra máquina com rede, copiar os ficheiros originais para o f0nix
e importar sem rede. Não é necessário fazê-lo apenas porque houve falhas históricas:
o checkpoint de 13 de novembro às 08:36 UTC já regista recuperação automática de
todos os grupos do Banco Mundial. Ver [operação e checkpoint](operations.md).

Siglas: BM é Banco Mundial; WDI é World Development Indicators; UTC é Tempo Universal
Coordenado; HTTP é o protocolo de transferência usado na recolha; JSON é JavaScript
Object Notation; CSV é um formato de valores separados por delimitadores. Os nomes
exatos e as licenças constam do [catálogo de fontes](sources.md).

Âmbito: apenas Banco Mundial/WDI e E-REDES, pelos canais sem credenciais já revistos.
Não usar para outras fontes nem para uploads arbitrários. As datas ORIGINAIS de
recolha mantêm-se; a hora de importação nunca substitui a data dos dados.

## Preparar a máquina de captura

Usar Python 3.12 e um checkout da revisão e do registo compatíveis com a instalação
revista. Não escolher um ramo de desenvolvimento apenas por ser mais recente.
A máquina de captura não precisa da base de produção, de Docker nem de crond.

```bash
cd /caminho/absoluto/do/checkout-compativel
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m ingest --help
.venv/bin/python -m ingest capture --help
mkdir -p "$HOME/pacotes"
```

A captura executa o fluxo registado completo de coletor e verificador independente
numa base descartável sob `TMPDIR`. As opções globais `--db` e `--raw-dir` não são
abertas pela captura. O pacote durável fica no diretório explícito `--output`, fora
da base descartável, e contém os corpos exatos e um manifesto com URL, parâmetros,
URL final, estado HTTP real, instante original da recolha, tamanho e SHA-256.

## Capturar respostas originais

Cada captura exige um diretório novo ou vazio. Banco Mundial, todos os indicadores
ativos, ou um indicador com o grupo completo de geografias registadas:

```bash
.venv/bin/python -m ingest capture worldbank     --output "$HOME/pacotes/bm-$(date -u +%Y%m%dT%H%M%SZ)"
.venv/bin/python -m ingest capture worldbank     --output "$HOME/pacotes/bm-pop-$(date -u +%Y%m%dT%H%M%SZ)"     --indicator SP.POP.TOTL
```

E-REDES exige limites explícitos de dias UTC. `--to` é INCLUSIVO e tem de ser
anterior ao dia UTC atual; o exemplo é uma janela histórica, não uma promessa de
cobertura publicada até ao último dia:

```bash
.venv/bin/python -m ingest capture eredes     --output "$HOME/pacotes/eredes-2026-11-10-$(date -u +%Y%m%dT%H%M%SZ)"     --from 2026-11-10 --to 2026-11-10
```

Limites por omissão: `--timeout 30 --max-requests 256 --deadline 300`. Podem ser
passados ao comando `capture`, segundo a dimensão revista da janela. Contam pedidos
físicos, incluindo redirecionamentos; o prazo cobre toda a fase de rede, limita cada
pedido ao tempo restante, termina um transporte bloqueado e recusa respostas tardias.
Uma janela longa pode exceder o orçamento e deixar um pacote parcial.

O Banco Mundial usa JSON em
`https://api.worldbank.org/v2/country/<geos>/indicator/<COD>?format=json&per_page=20000`
e ZIP/CSV em `https://api.worldbank.org/v2/<en|es>/indicator/<COD>?downloadformat=csv`.
A configuração revista escolhe `es` apenas para `NY.GDP.MKTP.KD.ZG` e
`SL.UEM.TOTL.ZS`; não há substituição automática de canal. A E-REDES usa JSON em
`https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/energia-produzida-total-nacional/records`
e CSV em `.../exports/csv?lang=pt&timezone=UTC&where=...`, com metadados e um CSV por
cada dia UTC capturado para permitir uma nova amostra na importação.

Saída 0 significa captura completa e selada. Saída 1 significa captura parcial:
os ficheiros saudáveis ficam guardados com as falhas reais no manifesto, mas o
pacote NÃO é importável. Corrigir a rota e repetir num diretório novo. Saída 2 indica
erro de argumentos ou preparação, incluindo diretório de saída não vazio; não
presumir que esse diretório contém um pacote completo.

## Copiar para o f0nix e usar o runbook de importação

O pacote é a pasta inteira com `manifest.json` e `responses/<sha[:2]>/<sha>`. Copiar
sem extrair, reformatar ou gravar por cima dos ficheiros. Definir `BUNDLE_LOCAL` como
a pasta absoluta da captura completa; executar este bloco na máquina de captura
apenas quando a transferência estiver autorizada:

```bash
: "${BUNDLE_LOCAL:?Definir a pasta absoluta do pacote completo}"
[[ "$BUNDLE_LOCAL" = /* ]]
test -f "$BUNDLE_LOCAL/manifest.json"
scp -r "$BUNDLE_LOCAL" f0nix:/home/joao/prumo-operations/task18-49a3602/
```

Confirmar previamente que o destino com o mesmo nome não existe, para não misturar
capturas. A cópia para o host não importa dados. No f0nix, definir `BUNDLE_HOST` como
o caminho absoluto da pasta copiada e `BUNDLE_SOURCE` como `worldbank` ou `eredes`.
Para uma captura BM limitada a um indicador, manter o mesmo `INDICATOR`; para
E-REDES, `BUNDLE_FROM`/`BUNDLE_TO` são os limites inclusivos ORIGINAIS da captura.

Executar exclusivamente a [sequência parar/importar/rever/reiniciar](operations.md#manual-update-with-original-response-bundles).
Esse é o único runbook de escrita de produção: usa `dc-web-*` no f0nix, copia para
`/data/migration/bundles/` e passa as opções globais explícitas
`--db /data/prumo.sqlite3 --raw-dir /data/raw` antes do subcomando. O lock do
scheduler só coordena schedulers, não importações independentes. Um comando com
base isolada no f3nix não atualiza produção.

## Resultado e datas da importação offline

`run <fonte> --bundle DIR` lê apenas os pedidos exatos gravados no pacote. Não há
fallback de rede se faltar uma resposta. O manifesto e todos os corpos são validados
antes da abertura da base de destino. Uma falha posterior de um grupo pode deixar
outros grupos já importados, pelo que se devem rever todos os resultados.

- Saída 0 com `<grupo>: verified` significa sucesso técnico para os grupos selecionados.
  Quando há amostragem nova, exige-se 100% de correspondência da amostra, não uma
  verificação independente de todas as linhas. Bytes idênticos aos do último run
  verificado podem terminar por atalho, sem amostra nova.
- Saída 1 com `failed-fetch`, `failed-validation` ou `failed-verification` indica falha;
  os dados desse run não são promovidos e os dados bons anteriores mantêm-se.
- Saída 1 com `refusing an outdated bundle for dataset group '<grupo>'` e estado
  `blocked` recusa um grupo cujos recibos originais do coletor são mais antigos do
  que os dados verificados já guardados para esse grupo. Outros grupos podem avançar.
  Se todos forem recusados na pré-validação, nem os metadados do registo são alterados.
  Uma segunda proteção dentro da transação pode terminar em `blocked-stale` se uma
  escrita concorrente tiver entretanto introduzido dados mais recentes.
- Saída 2 indica erro de argumentos ou validação inicial do pacote; essa validação
  antecede a abertura da base e não escreve nela.

Cada tentativa de importação fica com `input_origin=recorded`; `started_at` é o
instante da tentativa, enquanto os `fetched_at` dos dados e recibos mantêm os tempos
originais. `status --json` separa `last_verified`, `real_data_fetched_at`, origem e
período de referência. Uma verificação feita agora sobre ficheiros antigos não torna
a sua recolha recente. O estado técnico também não concede direitos de redistribuição.

As linhas `legacy-unverified` mantêm a identificação e as datas originais. Só a
continuidade revista do BM ativo e licenciado está autorizada; uma observação nova
verificada e elegível prevalece para o mesmo período, sem apagar a linha antiga.
Consultar a [metodologia](methodology.md) para regras de vintages e amostragem.

## Operação automática e limites

A atualização normal já é feita por `prumo-ingest` no f0nix, com
`input_origin=live`. Não executar outro `run`/`replay` em paralelo. Uma recuperação
manual com rede real também exige autorização, paragem e revisão conforme
[operações](operations.md); `run --dry-run` isola a base mas continua a usar rede.

Um ZIP descarregado no browser sem recibo HTTP não é um pacote importável. Guardar
o original imodificado, sem inventar estado ou data e sem fabricar um novo ZIP do
publicador. Recibos mais de cinco minutos no futuro são recusados, tanto na leitura
do pacote como na escrita do pipeline. O período de referência não é a data de
recolha, e pedir uma janela maior não cria observações ainda não publicadas.
