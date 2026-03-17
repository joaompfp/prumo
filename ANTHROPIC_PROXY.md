# Anthropic Auth Proxy (mitmproxy)

Prumo usa um proxy MITM para converter tokens OAuth (Claude Max) em headers `Authorization: Bearer`, permitindo usar a subscrição Claude Max como se fosse uma API key normal — sem alterar o código da app.

## Porquê

A SDK/API da Anthropic envia autenticação via `x-api-key`, mas tokens OAuth (`sk-ant-oat01-...`) exigem `Authorization: Bearer` + o header beta `anthropic-beta: oauth-2025-04-20`. O proxy faz essa tradução de forma transparente.

## Arquitectura

```
Prumo (uvicorn)
  │  HTTPS_PROXY=http://anthropic-auth-proxy:8080
  ▼
anthropic-auth-proxy (mitmdump)
  │  1. Intercepta HTTPS para api.anthropic.com
  │  2. Remove header x-api-key
  │  3. Adiciona Authorization: Bearer <token>
  │  4. Adiciona anthropic-beta: oauth-2025-04-20
  ▼
api.anthropic.com
```

## Componentes

### 1. Serviço proxy — `anthropic-auth-proxy`

**Compose:** `stacks/main/compose/anthropic-auth-proxy.yml`

```yaml
image: mitmproxy/mitmproxy:latest
command: >
  mitmdump
  --listen-port 8080
  --set block_global=false
  --set connection_strategy=lazy
  -s /scripts/rewrite_auth.py
```

- **Stack:** main (always-on)
- **Rede:** `office_net` (partilhada com jarbas)
- **Porta Tailscale:** `100.103.119.5:8888` (acesso remoto para debug)
- **Memória:** 128 MB
- **Healthcheck:** verifica existência de `mitmproxy-ca-cert.pem`

### 2. Script de rewrite — `rewrite_auth.py`

**Localização:** `stacks/office/appdata/anthropic-auth-proxy/rewrite_auth.py`

Duas funções:

- **`request()`** — Intercepta pedidos a `api.anthropic.com`:
  - Lê `x-api-key` → move para `Authorization: Bearer`
  - Injeta `anthropic-beta: oauth-2025-04-20` (merge se já existir)

- **`response()`** — Loga erros (status >= 400) com body do request e resposta, para debug.

### 3. Volume de certificados

```
Volume: office-anthropic-proxy-certs
  ├── mitmproxy-ca-cert.pem   ← usado pelo Prumo
  ├── mitmproxy-ca.pem         ← chave privada do CA
  └── mitmproxy-dhparam.pem
```

Gerado automaticamente pelo mitmproxy no primeiro arranque. Montado read-only no Prumo em `/proxy-certs`.

### 4. Configuração no Prumo

**Compose:** `stacks/jarbas/compose/prumo.yml`

```yaml
environment:
  - HTTPS_PROXY=http://anthropic-auth-proxy:8080
  - NO_PROXY=localhost,127.0.0.1
volumes:
  - anthropic-proxy-certs:/proxy-certs:ro
```

**Entrypoint** (injeta o CA do proxy no bundle de certificados):

```bash
cp /etc/ssl/certs/ca-certificates.crt /tmp/ca-bundle.crt
cat /proxy-certs/mitmproxy-ca-cert.pem >> /tmp/ca-bundle.crt
export SSL_CERT_FILE=/tmp/ca-bundle.crt
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2
```

Sem isto, Python rejeita o certificado auto-assinado do proxy com erro SSL.

### 5. SSL context no código Python

**Ficheiro:** `app/services/interpret.py` (linhas 59–65)

```python
_ssl_ctx = _ssl.create_default_context()
_cert_file = os.environ.get("SSL_CERT_FILE")
if _cert_file and os.path.exists(_cert_file):
    _ssl_ctx.load_verify_locations(_cert_file)
_opener = _ur.build_opener(_ur.HTTPSHandler(context=_ssl_ctx))
```

O `_opener` é criado uma vez no import e reutilizado por todos os serviços:
- `interpret.py` — importa directamente
- `painel_headline.py` — `from .interpret import _opener`
- `painel_analysis/engine.py` — `from ..interpret import _opener`
- `painel_card_links.py` — `from .interpret import _opener`

## Serviços que usam o proxy

| Serviço | Ficheiro | Modelo | Timeout | Cache |
|---------|----------|--------|---------|-------|
| Interpretação de gráficos | `app/services/interpret.py` | Haiku 4.5 | 35s | 30 dias |
| Headlines do Painel | `app/services/painel_headline.py` | Opus 4.6 | — | 6 horas |
| Análise do Painel | `app/services/painel_analysis/engine.py` | Sonnet 4.6 | 180s | versionado (v23) |
| Links de cards | `app/services/painel_card_links.py` | Haiku 4.5 | — | 1 semana |

Todos enviam `x-api-key: $CAE_ANTHROPIC_TOKEN` via `urllib.request` → proxy converte para Bearer.

## Variável de ambiente

| Var | Origem | Descrição |
|-----|--------|-----------|
| `CAE_ANTHROPIC_TOKEN` | Infisical (`/jarbas`) | Token OAuth Claude Max |
| `HTTPS_PROXY` | `prumo.yml` | Endereço do proxy |
| `SSL_CERT_FILE` | Entrypoint (runtime) | Bundle CA com cert do proxy |

## Ordem de arranque

```
1. dc-core up -d       → cria office_net
2. dc-main-up          → arranca anthropic-auth-proxy (espera healthcheck)
3. dc-jarbas-up        → arranca prumo (precisa do proxy + volume de certs)
```

Se o proxy não estiver acessível, as chamadas à API falham com `ConnectionRefusedError`. Não há retry automático no Prumo — a resposta é servida sem interpretação/análise AI.

## Outro consumidor

O **paperless-gpt** (`stacks/office/compose/paperless-gpt.yml`) usa exactamente o mesmo padrão: `HTTPS_PROXY` + cert injection + `office_net`.

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `SSLCertVerificationError` | CA do proxy não injetado | Verificar volume `anthropic-proxy-certs` e entrypoint |
| `ConnectionRefusedError` | Proxy em baixo | `dc-main-up` e verificar `dc-main logs anthropic-auth-proxy` |
| 401/403 na API | Token expirado | Regenerar: `claude setup-token` → atualizar Infisical |
| Erros nos logs do proxy | Pedido malformado | Verificar `[ERR]` nos logs: `dc-main logs anthropic-auth-proxy` |
