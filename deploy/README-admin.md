# Public Admin entry: versioned preparation, deployment and rollback

Status: **prepared, not deployed.** This repository change does not touch the live edge, the
live Authelia configuration, DNS or any running container. The owner gates the release.

The Admin entry is `https://joao.date/dados/admin/`. It reaches the existing backoffice on
f0nix through Traefik on f3nix. The backoffice keeps its own bridge network, its read-only
root filesystem and its Tailscale-bound port; the public router is an additional path to the
same service, not a replacement for the private one.

## The boundary that must stay exact

The Traefik router uses the exact path boundary, not a bare prefix:

```
Host(`joao.date`) && (Path(`/dados/admin`) || PathPrefix(`/dados/admin/`))
```

This is why `priority 60` is required: it must win over the public `/dados` router at
priority 50 and the `/static` router at 55, while leaving `/dados/administration` on the
public site. There is deliberately no VPN-bypass router.

The two middleware properties that matter:

- Authelia runs **before** StripPrefix. Access control sees `/dados/admin/...`; the app sees
  `/` plus `X-Forwarded-Prefix: /dados/admin` from the strip.
- Client-supplied `X-Prumo-Proxy-Secret`, `Remote-User`, `Remote-Groups` and
  `X-Forwarded-Prefix` are removed before Authelia. The shared secret is injected only after
  forwardAuth succeeds. A client cannot mint either header.

## Two layers: challenge at the edge, authorization in the app

`deploy/authelia-prumo-admin.yml` is one rule, not an allow rule followed by a deny. It uses
the same exact `resources` scope as the Traefik router, `policy: two_factor`, and no
`subject`. An anonymous visitor is therefore redirected to the Authelia portal to
authenticate instead of receiving a dead-end 403. The rule must be the first match under
`access_control.rules`, before the external wall, the `group:bots` rules and the generic
`two_factor` catch-alls: a later bot or bypass rule must not win.

Authelia authenticates; the app authorizes. After forwardAuth succeeds, Traefik injects the
shared secret and forwards `Remote-User`. The backoffice requires both and admits only its
configured identity, `PRUMO_ADMIN_USER` (default `joao`). Any other Authelia user receives
401 `admin access denied` from the app and no HTML or database content. A missing or wrong
secret fails closed in exactly the same place. The owner allowlist lives in one verified
place, the app; adding an unconditional `deny` after the challenge would instead block the
owner immediately after a successful login.

The versioned files are:

- `deploy/traefik-prumo-admin.yml`: the file-provider router, middlewares and service.
- `deploy/authelia-prumo-admin.yml`: the single exact-scope `two_factor` challenge rule,
  inserted as the first entry under `access_control.rules`, before the external wall, the
  `group:bots` rules and the generic `two_factor` catch-alls.
- `deploy/prumo-backoffice.yml`: the staged environment variables, disabled by default.

## Secret provisioning (SOPS)

The shared secret is required in two stacks because each stack is started with its own
SOPS-decrypted environment file: Traefik injects it, the backoffice verifies it. Generate one
value and put the **same** value in both files. Run these from `/home/joao/docker`:

```bash
openssl rand -hex 32
sops secrets/web.enc.env
sops secrets/core.enc.env
```

The accepted alphabet is exactly `[A-Za-z0-9_-]`, at least 32 characters. `openssl rand -hex 32`
produces 64 hexadecimal characters and is the recommended form. The backoffice rejects any
other character at startup, before a value can reach the edge: the Traefik template places the
secret inside a single-quoted YAML scalar, where a quote cannot be represented safely. Do not
substitute a passphrase containing spaces, quotes, `$`, `!` or a backslash.

In each editor add one line, for example:

```
PRUMO_ADMIN_PROXY_SECRET=<the generated value>
```

Never write the value into this repository, a compose label, a Docker image, a shell
history, a terminal log or a ticket. The encrypted `.enc.env` files are the only at-rest
copies.

Also set the non-secret Admin values in `secrets/web.enc.env`:

```
PRUMO_ADMIN_USER=joao
PRUMO_ADMIN_ORIGIN=https://joao.date
PRUMO_BACKOFFICE_ALLOWED_HOSTS=joao.date,100.118.19.6,localhost,127.0.0.1
```

The allowed-host value keeps the existing Tailscale host and healthcheck names and adds the
canonical public host. `joao.date` is required by the app's exact Host check in proxy mode.

Traefik must receive the secret in its own environment before it can render the template.
Add this to the `traefik` service environment in
`stacks/core/compose/traefik.yml` during the release (this is a live-infra edit, not part of
the repository change):

```yaml
      - PRUMO_ADMIN_PROXY_SECRET=${PRUMO_ADMIN_PROXY_SECRET}
```

The dynamic template uses Traefik's documented file-provider Go templating syntax:

```
X-Prumo-Proxy-Secret: '{{ env "PRUMO_ADMIN_PROXY_SECRET" }}'
```

Traefik applies Go templating only to dedicated dynamic files, not to its static
configuration. The expression is validated by the repository test after substituting a test
value; the real environment value is never in git. An empty value at the edge produces an empty
injected header, but that is fail-closed **only after the backoffice itself is in proxy mode**
(its own `PRUMO_ADMIN_PROXY_SECRET` is set). While every Admin variable is blank, the shipped
private service intentionally stays in local mode. This is why the release sequence sets the
app's proxy secret and recreates the backoffice (step 3) before the Authelia rules (step 5) and
the Traefik environment/router (steps 6-7): never expose the router while the app is still
local. Do not rely on the empty-edge failure to protect a local-mode backoffice.

## Deployment sequence

The order is deliberate: the ACL and the app's proxy mode are effective before the public
router exists. A mistake costs a 401 on a private service, not an open Admin page.

1. **Record the rollback point.** On f0nix and f3nix save the current backoffice image id,
   the current `main` commit and copies of the installed compose files. This slice changes no
   schema and writes no data, so the rollback is code and environment only.
2. **Provision SOPS.** Add the same secret to `secrets/web.enc.env` and
   `secrets/core.enc.env`; set the three non-secret Admin values in `secrets/web.enc.env`.
3. **Recreate the backoffice** from the updated include with the private service still
   unrouted. Proxy mode now rejects the direct Tailscale port without the secret.
4. **Verify the lock before exposing anything.** `GET /healthz` on the direct port still
   answers 200 with only `{"status":"ok","db":...}`. A page request without the secret
   answers 401; a request with only `Remote-User: joao` also answers 401.
5. **Install the Authelia rule** in `configuration.yml` as the first access-control rule
   and restart Authelia. Verify an unauthenticated `/dados/admin/` is redirected to the
   Authelia portal, not answered with a bare 403, and that the public `/dados` pages are
   unchanged for ordinary readers.
6. **Add the Traefik environment value** and recreate Traefik. It has no Admin router yet, so
   this cannot expose the app.
7. **Install the dynamic router** by copying `deploy/traefik-prumo-admin.yml` to
   `stacks/core/appdata/traefik2/rules/f3nix/router-prumo-admin.yml`. Keep the file watch on
   and confirm Traefik accepted it without dropping the existing `/dados` route. Inspect the
   Traefik log for a template/parse error before trusting the route: the file-provider Go
   template is rendered before YAML parsing, so a missing environment value or a malformed
   expression leaves the router absent rather than half-configured.
8. **Owner acceptance** in a browser: open `https://joao.date/dados/admin/`, complete
   Authelia, navigate every section, submit a harmless editorial form, and confirm the URL
   stays below `/dados/admin/`. Then verify a direct tailnet request and a forged
   `Remote-User` request still answer 401.

Do not enable the router first and fix the ACL afterwards. Do not add a router that skips
Authelia for the tailnet. Do not copy the secret into a Traefik label, where `docker inspect`
would show it.

## Verification points

- Unauthenticated `https://joao.date/dados/admin/` is challenged by Authelia (redirect to the
  portal), not a dead-end 403, and does not return the backoffice HTML.
- An authenticated owner sees the overview and prefixed navigation under `/dados/admin/`.
- An authenticated Authelia identity other than the owner receives 401
  `admin access denied` from the app, with no HTML or database content.
- `curl` to `http://100.118.19.6:8089/` answers 401, including with a forged
  `Remote-User: joao` header and without `X-Prumo-Proxy-Secret`.
- A request with the right secret but `Host: 100.118.19.6:8089` still answers 401: the app
  requires the canonical `Host: joao.date` in proxy mode.
- A form POST with `Origin: http://joao.date` is refused even when
  `X-Forwarded-Proto: https` is forged.
- `/dados/administration` still reaches the public app, not Admin.
- Responses carry `Cache-Control: no-store`, `form-action 'self'`, `base-uri 'none'` and
  `frame-ancestors 'none'`.
- `/healthz` never returns a database path, schema version or exception text.

## Rollback

Remove the public path first, then restore the private service; never leave the router up
while reverting the app to local mode.

1. Remove or rename
   `stacks/core/appdata/traefik2/rules/f3nix/router-prumo-admin.yml` and confirm Traefik has
   dropped the Admin router.
2. Remove `PRUMO_ADMIN_PROXY_SECRET` and the other Admin values
   (`PRUMO_ADMIN_USER`, `PRUMO_ADMIN_ORIGIN`, `PRUMO_BACKOFFICE_ALLOWED_HOSTS`) from
   `secrets/web.enc.env`, then recreate the backoffice. With no proxy variable the app
   returns to local mode and the Tailscale-only service behaves exactly as before.
3. Remove the Traefik environment value and recreate Traefik, if the template file is also
   removed. Removing the template first makes this step optional.
4. Remove the Authelia rule if the path is no longer needed. It is harmless while no
   router exists, but leaving an access-control rule around invites a later false diagnosis.
5. If the image itself is suspect, redeploy the recorded previous backoffice image id. No
   database migration, data copy or worker restart is involved in this slice.

The rollback is complete when the private `http://100.118.19.6:8089` service answers its
normal pages, `/healthz` is 200, and `https://joao.date/dados/admin/` is not routed by
Traefik.
