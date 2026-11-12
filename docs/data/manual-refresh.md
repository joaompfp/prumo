# Atualização manual com ficheiros originais (BM e E-REDES)

Procedimento operacional para atualizar os dados do Banco Mundial (BM/WDI) e da E-REDES
quando a rota de rede do servidor falha: captura-se um pacote auditável de ficheiros
originais noutra máquina com rede, copia-se para o servidor e importa-se offline. As datas
de recolha ORIGINAIS são preservadas; uma importação manual nunca se apresenta como
verificação fresca nem toca nos dados antigos (legacy) quando falha.

Âmbito suportado: apenas as fontes sem credenciais já revistas - Banco Mundial (WDI) e
E-REDES. Não usar para FRED/OECD/INE/REN/BPstat nem para uploads arbitrários.

## 1. Preparar o repositório noutra máquina (a de captura)

Qualquer máquina com Python 3.12 e rede serve. Não é preciso crond, Docker nem a base de
dados de produção - a captura corre toda num diretório descartável debaixo de TMPDIR.

```bash
# na máquina com rede
git clone https://github.com/joaompfp/prumo.git prumo-pipeline
cd prumo-pipeline
git checkout pipeline-rebuild
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Verificar instalação (produz a ajuda; sai 0):

```bash
.venv/bin/python -m ingest --help
```

## 2. Capturar (na máquina com rede)

A captura corre o fluxo registado completo (coletor + verificador independente) sobre uma
base descartável e grava corpos exatos + manifesto (URL, parâmetros, URL final, estado HTTP
REAL, data/hora ORIGINAL da recolha, bytes e sha256 de cada resposta).

O diretório dos pacotes é à escolha do operador; os exemplos usam `$HOME/pacotes`
(criar uma vez com `mkdir -p "$HOME/pacotes"`). A captura recusa diretórios de saída
existentes não vazios - cada captura usa um diretório NOVO.

Banco Mundial - tudo (18 indicadores ativos):

```bash
.venv/bin/python -m ingest capture worldbank --output "$HOME/pacotes/bm-$(date -u +%F)"
```

Banco Mundial - um só indicador (grupo completo de geografias, nunca um país):

```bash
.venv/bin/python -m ingest capture worldbank --output "$HOME/pacotes/bm-pop-$(date -u +%F)" \
    --indicator SP.POP.TOTL
```

E-REDES - janela de dias UTC explícita (obrigatória; o último dia tem de ser anterior a hoje
UTC, porque hoje é um dia parcial ainda em curso):

```bash
.venv/bin/python -m ingest capture eredes --output "$HOME/pacotes/eredes-2026-11-10" \
    --from 2026-11-10 --to 2026-11-10          # um só dia
.venv/bin/python -m ingest capture eredes --output "$HOME/pacotes/eredes-abril" \
    --from 2026-04-01 --to 2026-04-30          # janela de recuperação
```

Limites de rede (valores por omissão razoáveis, todos físicos, redireções incluídas; o
`--deadline` é um limite real de relógio para TODA a fase de rede: cada pedido fica com o
tempo que falta, um servidor parado é morto ao chegar ao limite e uma resposta tardia é
descartada em vez de contada como sucesso):

```bash
    --timeout 30 --max-requests 256 --deadline 300
```

URLs efetivamente usados: BM JSON `https://api.worldbank.org/v2/country/<geos>/indicator/<COD>?format=json&per_page=20000`
e ZIP CSV `https://api.worldbank.org/v2/<en|es>/indicator/<COD>?downloadformat=csv` (a
variante `es` só para NY.GDP.MKTP.KD.ZG e SL.UEM.TOTL.ZS, escolha revista e fixa no código,
sem substituição automática); E-REDES JSON
`https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/energia-produzida-total-nacional/records?...`
e CSV `.../exports/csv?lang=pt&timezone=UTC&where=...` (um CSV por cada dia UTC da janela).

Saída 0 = captura completa e selada. Saída 1 = captura PARCIAL: os ficheiros saudáveis ficam
gravados para auditoria e o manifesto regista as falhas reais, mas o pacote NÃO é
importável (o `run --bundle` recusa manifestos com falhas). Corrigir a rota e repetir a
captura num diretório NOVO - a captura recusa diretórios existentes não vazios.

## 3. Copiar o pacote para o servidor

O pacote é uma pasta com `manifest.json` + `responses/<sha[:2]>/<sha>`. Copiar a pasta
INTEIRA sem alterar nada (os manifestos são validados bit a bit; bytes alterados são
detetados pelo sha256). Destino de HOJE no f3nix: uma pasta do operador, por exemplo
`/home/joao/pacotes/` (criar com `mkdir -p /home/joao/pacotes`):

```bash
scp -r "$HOME/pacotes/bm-2026-11-12" f3nix:/home/joao/pacotes/bm-2026-11-12
```

Nota de estado: a ingestão ainda NÃO está instalada como serviço no f3nix (sem contentor nem
crond); a importação corre a partir do checkout existente. Os caminhos `/data/prumo.sqlite3`
e `/data/raw/` são PLANEADOS para o futuro contentor da tarefa 18 - ainda não existem neste
servidor e não devem ser usados agora.

## 4. Importar no servidor (offline, sem rede)

HOJE a importação corre a partir do checkout existente `/home/joao/projects/prumo-pipeline`
(ramo `pipeline-rebuild`), com a venv de CI `.venv-ci`, e com base de dados e evidência
ISOLADAS da operação manual num diretório do operador - por exemplo
`/home/joao/pacotes/manual/` (também serve `/home/joao/.hermes/cache/scratch/...` para
corridas realmente descartáveis; `/data/...` é só o plano da tarefa 18):

```bash
cd /home/joao/projects/prumo-pipeline
OP=/home/joao/pacotes/manual            # diretório do operador; mkdir -p "$OP/db" na 1.ª vez
mkdir -p "$OP/db"
.venv-ci/bin/python -m ingest --db "$OP/db/prumo.sqlite3" --raw-dir "$OP/db/raw" \
    run worldbank --bundle /home/joao/pacotes/bm-2026-11-12
.venv-ci/bin/python -m ingest --db "$OP/db/prumo.sqlite3" --raw-dir "$OP/db/raw" \
    run worldbank --bundle /home/joao/pacotes/bm-pop-2026-11-12 --indicator SP.POP.TOTL
.venv-ci/bin/python -m ingest --db "$OP/db/prumo.sqlite3" --raw-dir "$OP/db/raw" \
    run eredes --bundle /home/joao/pacotes/eredes-2026-11-10 --from 2026-11-10 --to 2026-11-10
```

Nada aqui abre a rede: a importação responde só com os pedidos exatos gravados no pacote e
falha fechada se faltar algum. As datas gravadas são as ORIGINAIS da captura; o instante da
importação fica em `started_at` do run e o run fica marcado `input_origin='recorded'`.

Estados de saída:

- saída 0 e linhas `<grupo>: verified` = importado e verificado a 100% com amostra nova;
- saída 1 com `failed-fetch`/`failed-verification` = a importação honestamente falhou e os
  dados bons antigos continuam servidos (nada é apagado nem promovido);
- saída 1 com a linha `refusing an outdated bundle for dataset group '<grupo>'` = o pacote é
  MAIS ANTIGO que os dados verificados guardados PARA ESSE GRUPO. A recusa é POR GRUPO de
  dataset (indicador), acontece antes de qualquer escrita nesse grupo (e, quando TODOS os
  grupos são mais antigos, antes até de mexer nos metadados do registo), e é diagnosticada
  com o grupo e as duas datas; os grupos sãos do mesmo pacote continuam a importar (aparecem
  `verified`), o grupo velho aparece `blocked` com a razão. Um pacote mais recente é aceite.
  As linhas legacy de abril NUNCA são substituídas por este mecanismo - ficam servidas com a
  data original até haver dados verificados mais novos para o mesmo período;
- saída 2 = erro de argumentos/validação do pacote (manifesto inválido, pasta errada,
  combinações inválidas); nada foi escrito.

Inspecionar o estado depois (JSON; `real_data_fetched_at` é a data de recolha REAL dos dados,
`input_origin` mostra `recorded` nos datasets importados por pacote, e runs pendentes ficam
listados na SUA própria fonte mesmo com chaves de dataset antigas):

```bash
.venv-ci/bin/python -m ingest --db "$OP/db/prumo.sqlite3" status --json
```

## 5. Funcionamento automático normal

Quando a tarefa 18 instalar a ingestão no contentor (PLANO), a atualização automática passa a
ser, dentro do contentor, com a base e a evidência persistentes planeadas:

```bash
python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw run worldbank
python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw run eredes
```

com `input_origin='live'`. A recuperação (catch-up) manual E-REDES com janela explícita, sem
pacote, também é automática e faz fetch real:

```bash
python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    run eredes --from 2026-11-01 --to 2026-11-10
```

Enquanto a tarefa 18 não acontecer (HOJE), o equivalente manual corre com a rede do f3nix
partindo do checkout existente, sempre com a base isolada do operador ("$OP" da secção 4):

```bash
cd /home/joao/projects/prumo-pipeline
.venv-ci/bin/python -m ingest --db "$OP/db/prumo.sqlite3" --raw-dir "$OP/db/raw" run worldbank
.venv-ci/bin/python -m ingest --db "$OP/db/prumo.sqlite3" --raw-dir "$OP/db/raw" \
    run eredes --from 2026-11-01 --to 2026-11-10
```

## 6. Limites honestos

- Um ZIP do BM descarregado à mão no browser NÃO é um pacote importável: não traz recibo HTTP
  (estado, URL final, data da recolha) e ninguém lhe deve inventar um. Guardar esses ficheiros
  imodificados (não extrair, não abrir no Excel/gravar por cima: altera bytes e quebra o
  sha256), mas usar SEMPRE o comando `capture` acima para produzir o pacote auditável. Esta
  via de upload manual não é suportada como importação.
- As datas dos DADOS (período de referência, ex. ano 2025 ou dia UTC) não são a data de
  recolha: o `status` mostra-as separadamente (`real_data_fetched_at` vs período).
- O verificador E-REDES lê um CSV por dia UTC amostrado; a captura grava já o CSV de TODOS os
  dias da janela, por isso qualquer amostra nova na importação é servida pelo pacote.
