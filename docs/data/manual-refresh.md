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
git clone <url do repositório> prumo-pipeline
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

Banco Mundial - tudo (18 indicadores ativos):

```bash
.venv/bin/python -m ingest capture worldbank --output /caminho/pacotes/bm-$(date -u +%F)
```

Banco Mundial - um só indicador (grupo completo de geografias, nunca um país):

```bash
.venv/bin/python -m ingest capture worldbank --output /caminho/pacotes/bm-pop-$(date -u +%F) \
    --indicator SP.POP.TOTL
```

E-REDES - janela de dias UTC explícita (obrigatória; o último dia tem de ser anterior a hoje
UTC, porque hoje é um dia parcial ainda em curso):

```bash
.venv/bin/python -m ingest capture eredes --output /caminho/pacotes/eredes-2026-11-10 \
    --from 2026-11-10 --to 2026-11-10          # um só dia
.venv/bin/python -m ingest capture eredes --output /caminho/pacotes/eredes-abril \
    --from 2026-04-01 --to 2026-04-30          # janela de recuperação
```

Limites de rede (valores por omissão razoáveis, todos físicos, redireções incluídas):

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
detetados pelo sha256):

```bash
scp -r /caminho/pacotes/bm-2026-11-12 <servidor>:/tmp/pacotes/bm-2026-11-12
```

Caminhos de HOJE no servidor/alojamento (sem contentor novo): qualquer pasta temporária
serve, por exemplo `/tmp/pacotes/...`. No FUTURO contentor da tarefa 18, os caminhos
persistentes serão `/data/prumo.sqlite3` (base) e `/data/raw/` (evidência); o pacote em si
continua a ser uma pasta à escolha do operador, montada ou copiada para dentro do contentor.

## 4. Importar no servidor (offline, sem rede)

Nada aqui abre a rede: a importação responde só com os pedidos exatos gravados no pacote e
falha fechada se faltar algum. As datas gravadas são as ORIGINAIS da captura; o instante da
importação fica em `started_at` do run e o run fica marcado `input_origin='recorded'`.

```bash
.venv/bin/python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    run worldbank --bundle /tmp/pacotes/bm-2026-11-12
.venv/bin/python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    run worldbank --bundle /tmp/pacotes/bm-pop-2026-11-12 --indicator SP.POP.TOTL
.venv/bin/python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    run eredes --bundle /tmp/pacotes/eredes-2026-11-10 --from 2026-11-10 --to 2026-11-10
```

Estados de saída:

- saída 0 e linhas `<grupo>: verified` = importado e verificado a 100% com amostra nova;
- saída 1 com `failed-fetch`/`failed-verification` = a importação honestamente falhou e os
  dados bons antigos continuam servidos (nada é apagado nem promovido);
- saída 1 com `refusing an outdated bundle` = o pacote é MAIS ANTIGO que os dados verificados
  já guardados; recusado antes de qualquer escrita. Um pacote mais recente é aceite. As linhas
  legacy de abril NUNCA são substituídas por este mecanismo - ficam servidas com a data
  original até haver dados verificados mais novos para o mesmo período;
- saída 2 = erro de argumentos/validação do pacote (manifesto inválido, pasta errada,
  combinações inválidas); nada foi escrito.

Inspecionar o estado depois (JSON; `real_data_fetched_at` é a data de recolha REAL dos dados,
`input_origin` mostra `recorded` nos datasets importados por pacote):

```bash
.venv/bin/python -m ingest --db /data/prumo.sqlite3 status --json
```

## 5. Funcionamento automático normal

Nada muda quando a rede do servidor funciona: a atualização automática continua a ser

```bash
.venv/bin/python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw run worldbank
.venv/bin/python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw run eredes
```

com `input_origin='live'`. A recuperação (catch-up) manual E-REDES com janela explícita,
sem pacote, também é automática e faz fetch real:

```bash
.venv/bin/python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
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
