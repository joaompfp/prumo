# Hugo Integration — Research Report

> Scout M7 | 2026-02-28 22:26 GMT

## 1. Estado actual do Hugo site

**Estrutura encontrada:**

- **Hugo config:** `hugo.toml` (baseURL: `https://joao.date`, languageCode: `pt`)
- **Shortcodes existentes:** `/layouts/shortcodes/`
  - `mermaid.html` — simples wrapper `<div class="mermaid">{{ .Inner }}</div>`
  - `video.html` — tag `<video>` com parâmetros `src`, `width`, `title`
  - `center.html` — wrapper de alinhamento

- **Layout hierarchy:**
  - `layouts/_default/baseof.html` — layout base com `{{ block "scripts" . }}{{ end }}` antes de `</body>`
  - `layouts/textos/single.html` — **já implementa carregamento condicional de scripts!**
    ```html
    {{ define "scripts" }}
    {{ if findRE "class=\"mermaid\"" .Content }}
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad: true, theme: 'default'});</script>
    {{ end }}
    {{ end }}
    ```
  - Este é **exatamente o padrão que precisamos replicar** para charts CAE

- **CSS:**
  - `assets/css/custom.css` — CSS customizado (variáveis `:root`, `.mermaid`, `.video-container`, etc.)
  - `assets/css/styles.css` — estilos gerais
  - Pattern: classes específicas por shortcode (`.mermaid`, `.video-container`)

- **Configuração de segurança:**
  - `[markup.goldmark.renderer]` tem `unsafe = true` — permite HTML raw
  - Não vi `[security.html] allowInlineScripts` explícito, mas o site já aceita `<script>` via shortcodes

- **Hugo version:** Não disponível no PATH, mas site funciona (tem `public/` gerado)

**Conclusão:** O site já tem a infraestrutura perfeita. Basta replicar o padrão Mermaid.

---

## 2. Padrão recomendado: Shortcode

Com base no padrão Mermaid existente e nas best practices pesquisadas, o shortcode `cae-chart.html`:

```html
<!-- layouts/shortcodes/cae-chart.html -->
<div class="cae-embed" 
     data-chart-id="{{ .Get "id" }}" 
     data-dashboard-url="{{ .Site.Params.caeDashboardUrl | default "http://localhost:3500" }}">
  {{ with .Get "title" }}<p class="chart-title">{{ . }}</p>{{ end }}
  <!-- Placeholder enquanto carrega -->
  <div class="cae-loading">Carregando gráfico...</div>
</div>
```

**Uso no Markdown:**

```markdown
---
title: "Evolução do PIB Português"
date: 2026-02-28
---

## Contexto macroeconómico

Análise da evolução do PIB no último trimestre:

{{< cae-chart id="pib-evolution" title="PIB Portugal 2020-2025" >}}

Os dados mostram recuperação...
```

**Parâmetros:**
- `id` (obrigatório) — ID do chart no dashboard CAE
- `title` (opcional) — legenda acima do chart
- `data-dashboard-url` — URL do dashboard (configurable via `hugo.toml`)

**Alternativa: Front matter approach** (para múltiplos charts):

```markdown
---
title: "Relatório CAE Janeiro 2026"
custom_charts:
  - id: "pib-evolution"
    title: "PIB Portugal"
  - id: "inflation-yoy"
    title: "Inflação homóloga"
---

{{< load-cae-charts >}}
```

**Shortcode `load-cae-charts.html`:**

```html
{{ range .Page.Params.custom_charts }}
<div class="cae-embed" 
     data-chart-id="{{ .id }}" 
     data-dashboard-url="{{ $.Site.Params.caeDashboardUrl | default "http://localhost:3500" }}">
  {{ with .title }}<p class="chart-title">{{ . }}</p>{{ end }}
  <div class="cae-loading">Carregando gráfico...</div>
</div>
{{ end }}
```

---

## 3. Carregamento condicional do script

**Pattern actual (Mermaid):**

```html
{{ define "scripts" }}
{{ if findRE "class=\"mermaid\"" .Content }}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad: true, theme: 'default'});</script>
{{ end }}
{{ end }}
```

**Adaptação para CAE charts** (em `layouts/textos/single.html`):

```html
{{ define "scripts" }}
{{ if findRE "class=\"mermaid\"" .Content }}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad: true, theme: 'default'});</script>
{{ end }}

{{ if findRE "class=\"cae-embed\"" .Content }}
{{ $dashboardUrl := .Site.Params.caeDashboardUrl | default "http://localhost:3500" }}
<script src="{{ $dashboardUrl }}/embed.js" defer></script>
{{ end }}
{{ end }}
```

**Como funciona `findRE`:**
- Hugo function que faz regex no `.Content` renderizado (HTML)
- Detecta se existe `class="cae-embed"` no output
- Se sim, injeta o script `embed.js` apenas nessa página
- `defer` carrega script async sem bloquear rendering

**Requisitos do Hugo:**
- `findRE` disponível desde Hugo 0.36 (2018)
- Site actual certamente compatível (tem Mermaid a funcionar com o mesmo padrão)

**Alternativa: Verificação via Page Resources** (mais robusta):

```html
{{ if or (findRE "class=\"cae-embed\"" .Content) (.Params.custom_charts) }}
{{ $dashboardUrl := .Site.Params.caeDashboardUrl | default "http://localhost:3500" }}
<script src="{{ $dashboardUrl }}/embed.js" defer></script>
{{ end }}
```

Isto detecta tanto shortcodes inline como charts via front matter.

---

## 4. Integração em single.html

**Ficheiro:** `layouts/textos/single.html`

**Mudanças necessárias:**

1. **Adicionar bloco `{{ define "scripts" }}` expandido** (se ainda não existir a secção CAE):

```html
{{ define "main" }}
    <article class="mb-4">
        <div class="container px-4 px-lg-5">
            <div class="row gx-4 gx-lg-5 justify-content-center">
                <div class="col-md-10 col-lg-8 col-xl-7">
                    {{ .Content }}

                    {{ with .GetTerms "tags" }}
                    <div class="mt-4">
                        {{ range . }}
                        <a href="{{ .RelPermalink }}" class="badge bg-secondary text-decoration-none">{{ .LinkTitle }}</a>
                        {{ end }}
                    </div>
                    {{ end }}
                </div>
            </div>
        </div>
    </article>
{{ end }}

{{ define "scripts" }}
{{ if findRE "class=\"mermaid\"" .Content }}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad: true, theme: 'default'});</script>
{{ end }}

{{ if findRE "class=\"cae-embed\"" .Content }}
{{ $dashboardUrl := .Site.Params.caeDashboardUrl | default "http://localhost:3500" }}
<script src="{{ $dashboardUrl }}/embed.js" defer></script>
{{ end }}
{{ end }}
```

**Nota:** O `baseof.html` já tem `{{ block "scripts" . }}{{ end }}` no final antes de `</body>`. Scripts injetados aqui executam após DOM ready.

2. **Adicionar configuração em `hugo.toml`:**

```toml
[params]
  # ... existing params ...
  caeDashboardUrl = "http://localhost:3500"  # Dev
  # caeDashboardUrl = "https://cae.joao.date"  # Production
```

---

## 5. CSS

**Adicionar a `assets/css/custom.css`:**

```css
/* ==========================================================
   CAE DASHBOARD EMBEDS
   ========================================================== */
.cae-embed {
  margin: 2rem 0;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 4px solid var(--bordeaux);
  min-height: 400px;
  position: relative;
}

.cae-embed .chart-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 1rem;
  text-align: center;
}

.cae-embed .cae-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #adb5bd;
  font-size: 0.85rem;
}

/* Chart container (injected by embed.js) */
.cae-embed .chart-container {
  width: 100%;
  height: auto;
  min-height: 350px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .cae-embed {
    padding: 0.75rem;
    margin: 1.5rem 0;
    min-height: 300px;
  }
}

/* Dark mode support (if needed) */
@media (prefers-color-scheme: dark) {
  .cae-embed {
    background: #1a1a1a;
    border-left-color: var(--bordeaux-light);
  }
  .cae-embed .chart-title {
    color: #e0e0e0;
  }
}
```

**Variáveis já existentes em `custom.css`:**
- `--bordeaux: #8e2221`
- `--bordeaux-light: #c1443b`

Reutilizamos para consistência visual.

---

## 6. Post de teste

**Ficheiro:** `content/textos/2026-02-28-teste-cae-charts.md`

```markdown
---
title: "Teste de integração — CAE Dashboard Charts"
description: "Post de teste para validar embedding de charts do CAE Dashboard"
date: 2026-02-28
author: "João Peixoto"
tags: ["cae", "economia", "testes"]
draft: false
---

## Teste de Chart Único

Exemplo de embedding de um chart individual:

{{< cae-chart id="pib-evolution" title="Evolução do PIB Portugal 2020-2025" >}}

Análise: os dados mostram recuperação gradual após pandemia.

---

## Teste de Múltiplos Charts

Comparação de indicadores macroeconómicos:

{{< cae-chart id="inflation-yoy" title="Inflação Homóloga (YoY)" >}}

{{< cae-chart id="unemployment-rate" title="Taxa de Desemprego" >}}

---

## Integração com texto

O gráfico abaixo ilustra a evolução sectorial:

{{< cae-chart id="ipi-sectorial" >}}

Como se pode observar, o sector químico apresenta contração significativa.

---

## Validações esperadas

✅ Script `embed.js` carregado apenas nesta página  
✅ Cada `.cae-embed` renderiza chart independente  
✅ CSS aplicado corretamente (bordeaux border, loading state)  
✅ Responsive em mobile  
✅ Sem erros de CORS (mesma origem ou headers corretos)  
```

**Front matter alternativo (múltiplos charts via params):**

```markdown
---
title: "Relatório CAE — Janeiro 2026"
date: 2026-02-28
custom_charts:
  - id: "pib-evolution"
    title: "PIB Portugal"
  - id: "inflation-yoy"
    title: "Inflação Homóloga"
  - id: "ipi-sectorial"
    title: "Índice de Produção Industrial por Sector"
---

## Análise macroeconómica

{{< load-cae-charts >}}

Texto de análise...
```

---

## 7. Considerações

### 7.1 X-Frame-Options vs JS Embed

**Problema com iframes:**
- Header `X-Frame-Options: SAMEORIGIN` no nginx bloqueia embedding de iframes externos
- Mesmo domínio (joao.date → cae.joao.date) pode ter issues dependendo do CSP

**Solução com JS embed:**
- Script `embed.js` carregado diretamente do dashboard
- Renderiza chart via JavaScript no DOM da página Hugo
- **Bypassa completamente X-Frame-Options** (não há iframe!)
- Mais leve: apenas JS/CSS necessários, sem overhead de iframe

**Trade-off:**
- ✅ Sem problemas de CORS/CSP para rendering
- ✅ Melhor performance (menos HTTP overhead)
- ⚠️ Requer CORS headers corretos para fetch de `embed.js`:
  ```nginx
  # No nginx do dashboard CAE
  location /embed.js {
    add_header Access-Control-Allow-Origin "https://joao.date";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
  }
  ```

### 7.2 CORS

**Cenários:**

1. **Desenvolvimento local:**
   - Hugo dev server: `http://localhost:1313`
   - CAE dashboard: `http://localhost:3500`
   - CORS necessário: `Access-Control-Allow-Origin: http://localhost:1313`

2. **Produção (mesma origem):**
   - Se Hugo e CAE dashboard estiverem em `https://joao.date/*`:
   - Sem CORS issues (mesma origem)

3. **Produção (subdomains diferentes):**
   - Hugo: `https://joao.date`
   - CAE: `https://cae.joao.date`
   - CORS necessário: `Access-Control-Allow-Origin: https://joao.date`

**Configuração nginx recomendada (CAE dashboard):**

```nginx
location /embed.js {
  add_header Access-Control-Allow-Origin "https://joao.date" always;
  add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
  add_header Cache-Control "public, max-age=3600";
}

location /api/charts/ {
  add_header Access-Control-Allow-Origin "https://joao.date" always;
  add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
}
```

### 7.3 Performance

**Best practices implementadas:**

1. **Conditional loading:**
   - `{{ if findRE "class=\"cae-embed\"" .Content }}` — script só carrega em páginas com charts
   - Páginas sem charts: zero overhead

2. **Defer attribute:**
   - `<script src="..." defer>` — não bloqueia HTML parsing
   - Script executa após DOMContentLoaded

3. **CSS inline vs external:**
   - `.cae-embed` CSS no `custom.css` (já minificado pelo Hugo pipes)
   - Sem bloat de CSS inline

4. **Caching strategy:**
   ```nginx
   # No nginx do Hugo site
   location ~* \.(js|css)$ {
     expires 1h;
     add_header Cache-Control "public, immutable";
   }
   ```

5. **Lazy loading (future enhancement):**
   - `embed.js` pode implementar IntersectionObserver
   - Charts só renderizam quando visíveis no viewport

**Métricas esperadas:**
- First Contentful Paint (FCP): +50-100ms (script defer)
- Largest Contentful Paint (LCP): sem impacto (defer não bloqueia)
- Cumulative Layout Shift (CLS): 0 (`.cae-embed` tem `min-height` definida)

### 7.4 Caching

**Hugo build:**
- Charts embedados são **HTML estático** (shortcode output)
- Rebuild necessário apenas se Markdown mudar
- `embed.js` carregado via CDN/dashboard (não bundled)

**Dashboard updates:**
- Se chart data muda → `embed.js` puxa nova data via API
- Hugo page não precisa rebuild
- Cache-busting via query param: `embed.js?v=20260228`

**Configuração `hugo.toml`:**

```toml
[caches]
  [caches.getjson]
    dir = ":cacheDir/:project"
    maxAge = "1h"  # Cache de API calls durante build
```

### 7.5 Segurança

**Content Security Policy (CSP):**

Se o site tiver CSP headers, adicionar:

```nginx
# No nginx do Hugo site
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' http://localhost:3500 https://cae.joao.date;
  connect-src 'self' http://localhost:3500 https://cae.joao.date;
  style-src 'self' 'unsafe-inline';
" always;
```

**Notas:**
- `script-src` permite `embed.js` do dashboard
- `connect-src` permite fetch API calls para chart data
- `'unsafe-inline'` para styles — Hugo `custom.css` já é trusted

### 7.6 Fallback para JavaScript desabilitado

**Pattern `<noscript>`:**

```html
<!-- layouts/shortcodes/cae-chart.html -->
<div class="cae-embed" data-chart-id="{{ .Get "id" }}">
  {{ with .Get "title" }}<p class="chart-title">{{ . }}</p>{{ end }}
  <div class="cae-loading">Carregando gráfico...</div>
  <noscript>
    <p class="text-muted small">
      Este gráfico requer JavaScript. 
      <a href="{{ .Site.Params.caeDashboardUrl }}/charts/{{ .Get "id" }}" target="_blank">
        Ver no dashboard →
      </a>
    </p>
  </noscript>
</div>
```

---

## 8. Referências

**Pesquisa web (2026-02-28):**

1. **javaspring.net** — [How to Include Simple JavaScript in Hugo Articles Without Editing the Theme](https://www.javaspring.net/blog/how-to-include-simple-javascript-within-hugo/)
   - Métodos: inline JS, shortcodes reusáveis, page resources, front matter params
   - Security config: `allowInlineScripts = true`
   - Best practices: defer/async, avoid global scope

2. **GitHub hugo-chart** — [Shen-Yu/hugo-chart](https://github.com/Shen-Yu/hugo-chart)
   - Shortcode component para Chart.js
   - Pattern: `{{< chart 90 200 >}} {...} {{< /chart >}}`

3. **Hugo Discourse** — [Responsive lazy loaded images](https://discourse.gohugo.io/t/responsive-lazy-loaded-images/26041)
   - Conditional loading: `{{ if or (.Resources.Match "**.jpg") ... }}`
   - Performance pattern: load library only when needed

4. **barnz.dev** — [Embed an iframe in Hugo content](https://barnz.dev/blog/embed-iframe-in-hugo-content/)
   - X-Frame-Options: `SAMEORIGIN` restricts iframes
   - CSP `frame-ancestors` policy for external origins
   - **Key insight:** JS embed bypasses iframe restrictions

5. **Hugo Official Docs:**
   - [Shortcodes Documentation](https://gohugo.io/content-management/shortcodes/)
   - [Page Resources](https://gohugo.io/content-management/page-resources/)
   - [Security Configuration](https://gohugo.io/getting-started/configuration/#security-configuration)

**Ficheiros locais analisados:**

- `/home/node/.openclaw/workspace/web-stack/hugo-site/layouts/shortcodes/mermaid.html`
- `/home/node/.openclaw/workspace/web-stack/hugo-site/layouts/textos/single.html`
- `/home/node/.openclaw/workspace/web-stack/hugo-site/layouts/_default/baseof.html`
- `/home/node/.openclaw/workspace/web-stack/hugo-site/assets/css/custom.css`
- `/home/node/.openclaw/workspace/web-stack/hugo-site/hugo.toml`

---

## Sumário executivo

**Padrão recomendado:** Replicar exatamente o pattern Mermaid existente.

**3 mudanças necessárias:**

1. **Shortcode** → `layouts/shortcodes/cae-chart.html` (10 linhas)
2. **Script loading** → adicionar bloco `{{ if findRE "class=\"cae-embed\"" .Content }}` em `textos/single.html` (4 linhas)
3. **CSS** → adicionar classe `.cae-embed` em `custom.css` (30 linhas)

**Vantagens sobre iframe:**
- ✅ Bypassa X-Frame-Options
- ✅ Melhor performance (defer, conditional loading)
- ✅ Integração nativa com tema Hugo
- ✅ Zero overhead em páginas sem charts

**Pronto para implementação pelo Coder.**
