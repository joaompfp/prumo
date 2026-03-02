/* ═══════════════════════════════════════════════════════════════
   ficha.js — Ficha Técnica completa
   CAE Dashboard V7 — M5 (Analyst)
   Implementação: header + source cards + metodologia + dashboard info + disclaimer
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('ficha', async () => {
  const container = document.getElementById('ficha');
  const body = container.querySelector('.section-body');

  try {
    body.innerHTML = `<div class="loading-state"><div class="loading-spinner"></div><span>A carregar ficha técnica…</span></div>`;

    // Fetch catalog + explorador (real DB stats) + resumo in parallel
    const [catalog, explorador, resumo] = await Promise.all([
      API.catalog(),
      API.get('/api/explorador').catch(() => ({ items: [], total: 0 })),
      API.get('/api/resumo').catch(() => ({ updated: '—' })),
    ]);

    // ── Compute totals from real DB data (explorador) ──────────────────
    const expItems = explorador.items || [];
    const totalIndicators = explorador.total || expItems.length;
    const totalRows       = expItems.reduce((s, i) => s + (i.rows || 0), 0);
    let earliest = expItems.reduce((m, i) => i.since && i.since < m ? i.since : m, '9999');
    let latest   = expItems.reduce((m, i) => i.until && i.until > m ? i.until : m, '0000');
    if (earliest === '9999') earliest = '—';
    if (latest   === '0000') latest   = '—';

    // Group all DB indicators by source (all 377 combinations)
    const expBySrc = {};
    expItems.forEach(item => {
      if (!expBySrc[item.source]) expBySrc[item.source] = [];
      expBySrc[item.source].push(item);
    });

    // Display sources in catalog order first, then any extra from DB
    const catalogOrder = Object.keys(catalog);
    const allSrcs = [...new Set([...catalogOrder, ...Object.keys(expBySrc)])];

    const updated   = resumo.updated || '—';
    const totalSrcs = Object.keys(expBySrc).length || catalogOrder.length;

    // Update section title in header
    const titleEl = container.querySelector('.section-title');
    if (titleEl) titleEl.textContent = `Ficha Técnica — ${totalSrcs} fontes, ${totalIndicators} indicadores`;

    // ── Source card HTML generator (all DB indicators + catalog metadata) ──
    function renderSourceCard(src, idx = 0) {
      const expInds = expBySrc[src] || [];
      if (!expInds.length) return '';

      const catSrc  = catalog[src] || {};
      const srcLabel = catSrc.label       || src;
      const srcUrl   = catSrc.url         || null;
      const srcDesc  = catSrc.description || '';
      const catInds  = catSrc.indicators  || {};

      const rows = expInds.map(expInd => {
        const code    = expInd.indicator;
        const catInd  = catInds[code] || {};
        const label   = catInd.label || expInd.label || code;
        const unit    = catInd.unit  || expInd.unit  || '—';
        const rawFreq = catInd.frequency || expInd.frequency || '';
        const freq    = rawFreq === 'monthly'   ? 'Mensal'
                      : rawFreq === 'quarterly' ? 'Trimestral'
                      : rawFreq === 'annual'    ? 'Anual'
                      : rawFreq === 'weekly'    ? 'Semanal'
                      : rawFreq === 'semester'  ? 'Semestral'
                      : (rawFreq || '—');
        const since     = expInd.since    || catInd.since || '—';
        const until     = expInd.until    || catInd.until || '—';
        const rowsCount = expInd.rows;
        const regCount  = expInd.region_count || 1;

        // Single-region → Explorador link; multi-region → Comparativos
        const linkHref  = regCount > 1 ? '#comparativos' : `#explorador?s=${src}/${code}`;
        const linkTitle = regCount > 1
          ? `Ver nos Comparativos (${regCount} países/regiões)`
          : 'Ver no Explorador';
        const regBadge  = regCount > 1
          ? ` <span class="ficha-reg-badge" title="${regCount} países">${regCount}p</span>`
          : '';

        return `<tr id="ficha-row-${src}-${code}">
          <td><a href="${linkHref}" class="indicator-link" title="${linkTitle}">${code}</a>${regBadge}</td>
          <td>${label}</td>
          <td>${unit}</td>
          <td>${freq}</td>
          <td>${since}</td>
          <td>${until}</td>
          <td>${rowsCount != null ? rowsCount.toLocaleString('pt-PT') : '—'}</td>
        </tr>`;
      }).join('');

      const tableHTML = expInds.length > 0 ? `
        <div class="table-scroll-wrap">
          <table class="indicator-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Indicador</th>
                <th>Unidade</th>
                <th>Freq.</th>
                <th>Desde</th>
                <th>Até</th>
                <th>Obs.</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>` : '<p style="color:var(--c-muted);font-size:var(--fs-sm)">Sem indicadores registados.</p>';

      const urlHTML = srcUrl
        ? `<a href="${srcUrl}" target="_blank" rel="noopener" class="source-url-link">Site oficial ↗</a>`
        : '';

      const isOpen = idx === 0;
      return `
        <details class="source-card"${isOpen ? ' open' : ''}>
          <summary class="source-header">
            <div class="source-header-meta">
              <h3 class="source-title">${srcLabel}</h3>
              ${srcDesc ? `<p class="source-desc">${srcDesc}</p>` : ''}
            </div>
            <div class="source-header-right">
              <span class="source-badge" data-source="${src}">${expInds.length} indicadores</span>
              ${urlHTML}
              <span class="source-collapse-hint">
                <span class="source-collapse-closed">▶ Ver indicadores</span>
                <span class="source-collapse-open">▼ Ocultar</span>
              </span>
            </div>
          </summary>
          <div class="source-card-body">${tableHTML}</div>
        </details>`;
    }

    // ── Methodology section ───────────────────────────────────────────
    const methodologyHTML = `
      <div class="methodology-section" id="metodologia">
        <h3>Metodologia</h3>
        <div class="methodology-content">

          <details class="method-accordion">
            <summary>Ajustamento Sazonal</summary>
            <p>As séries de produção industrial (IPI) apresentadas no dashboard são <strong>ajustadas sazonalmente</strong> — os efeitos regulares e previsíveis que se repetem todos os anos (como o encerramento de fábricas em Agosto ou o aumento de produção alimentar antes do Natal) são removidos estatisticamente. Isto permite comparar meses consecutivos de forma directa, sem distorção. O método utilizado pelo INE e pelo Eurostat é o <strong>TRAMO-SEATS</strong>, integrado no software X-13ARIMA-SEATS desenvolvido pelo U.S. Census Bureau e recomendado pelas directrizes do Sistema Estatístico Europeu (ESS Guidelines on Seasonal Adjustment, 2015). Quando o dashboard apresenta o IPI "dessazonalizado", significa que a série já foi tratada na origem — o dashboard reproduz os dados tal como publicados pelo INE e Eurostat, sem aplicar ajustamento adicional.</p>
          </details>

          <details class="method-accordion">
            <summary>Base Temporal (Índices)</summary>
            <p>Um índice com <strong>base 2021=100</strong> significa que todos os valores são expressos em relação ao nível médio de 2021: se o índice marca 95, a produção está 5% abaixo do nível de 2021; se marca 110, está 10% acima. A base é uma convenção — não altera a informação económica subjacente, apenas a escala. <strong>Actualmente, tanto o INE como o Eurostat utilizam base 2021=100 para o IPI</strong> (a base anterior era 2015=100, actualizada em 2024). Quando comparamos séries de fontes diferentes, as <strong>variações percentuais</strong> (homólogas ou em cadeia) são directamente comparáveis; os <strong>valores nominais do índice</strong>, porém, só o são se partilharem a mesma base.</p>
          </details>

          <details class="method-accordion">
            <summary>Comparabilidade Europeia</summary>
            <p>O Eurostat garante a comparabilidade entre países impondo uma <strong>metodologia harmonizada</strong>: todos os Estados-membros recolhem dados sobre a produção industrial segundo a classificação <strong>NACE Rev. 2</strong>, utilizam métodos de ajustamento sazonal compatíveis (TRAMO-SEATS ou X-12ARIMA), e reportam ao Eurostat dentro de prazos definidos por regulamento. Não obstante, podem existir <strong>pequenas divergências</strong> entre os dados publicados directamente pelo INE e a versão Eurostat para Portugal, porque o Eurostat aplica as suas próprias revisões, validações e, por vezes, estimativas para dados em falta. As comparações internacionais no dashboard usam sempre a versão Eurostat, para assegurar que Portugal é comparado com outros países na mesma métrica.</p>
          </details>

          <details class="method-accordion">
            <summary>Cálculo do Diferencial PIB per Capita</summary>
            <p>O <strong>diferencial absoluto de PIB per capita</strong> entre Portugal e a média da UE-27 é expresso em <strong>euros correntes por habitante e por ano</strong>. O cálculo é simples: PIB per capita UE-27 menos PIB per capita Portugal, ambos em euros nominais (indicador Eurostat <code>nama_10_pc</code>). A opção por euros correntes (em vez de paridade de poder de compra) é deliberada: mostra quanto vale, em dinheiro real, a distância entre o que um português e um europeu médio produzem. A perspectiva complementar usa <strong>PPS</strong> (Purchasing Power Standards) do Eurostat, que corrige diferenças de nível de preços entre países — as duas leituras são complementares.</p>
          </details>

          <details class="method-accordion">
            <summary>Agregado EU27_2020</summary>
            <p>O dashboard utiliza o agregado <strong>EU27_2020</strong> do Eurostat, que corresponde aos <strong>27 Estados-membros actuais da União Europeia após a saída do Reino Unido</strong> (Brexit, 1 de Fevereiro de 2020). Este agregado <strong>não inclui o Reino Unido</strong> em nenhum período — mesmo para anos anteriores a 2020, o Eurostat recalcula retroactivamente as séries excluindo o UK, para garantir coerência temporal. Não usamos o agregado EA20 (Área do Euro, 20 países) excepto quando indicado explicitamente, porque excluiria Estados-membros relevantes fora da zona euro (como a Polónia, a Suécia ou a Roménia). O EU27_2020 é o agregado de referência mais abrangente e politicamente actual.</p>
          </details>

          <details class="method-accordion" open>
            <summary>Frequência de Actualização por Fonte</summary>
            <div class="table-scroll-wrap"><table class="methodology-table">
              <thead><tr><th>Fonte</th><th>Indicadores</th><th>Freq.</th><th>Lag</th></tr></thead>
              <tbody>
                <tr><td><strong>INE</strong></td><td>IPI (dessaz.), emprego e salários na indústria, IHPC, confiança empresarial</td><td>Mensal</td><td>~2 meses</td></tr>
                <tr><td><strong>Eurostat</strong></td><td>IPI por sector NACE (transformadora, total, alimentar, têxtil, química, transporte, construção), desemprego harmonizado, emprego, ULC, produtividade laboral, HICP, confiança dos consumidores, PIB trimestral e per capita, dívida e défice públicos, balança corrente</td><td>Mensal/Trim./Anual</td><td>~2–4 meses</td></tr>
                <tr><td><strong>FRED</strong></td><td>Brent, gás natural, cobre, alumínio, trigo, milho, café</td><td>Mensal</td><td>Quase em tempo real</td></tr>
                <tr><td><strong>Banco de Portugal</strong></td><td>Euribor (1m/3m/6m/12m), yields soberanos, spread PT-DE, EUR/USD, crédito, depósitos</td><td>Mensal</td><td>0–2 meses</td></tr>
                <tr><td><strong>OCDE</strong></td><td>CLI (indicador avançado), inquéritos BTS (encomendas, produção, preços, emprego)</td><td>Mensal</td><td>1–2 meses</td></tr>
                <tr><td><strong>REN</strong></td><td>Produção eléctrica por fonte, consumo, importações, preço MIBEL</td><td>Mensal</td><td>~1 mês</td></tr>
                <tr><td><strong>DGEG</strong></td><td>Produção eléctrica, combustíveis (semanal), gás natural indústria (semestral)</td><td>Semanal–Anual</td><td>Variável</td></tr>
                <tr><td><strong>ERSE</strong></td><td>Tarifas de acesso às redes (MAT, AT, MT, BTE, BTN)</td><td>Anual</td><td>Antes do período tarifário</td></tr>
                <tr><td><strong>World Bank</strong></td><td>Crescimento PIB, PIB per capita (USD e PPC), PIB total (USD), natalidade, mortalidade, esperança de vida, índice Gini, despesa em saúde % PIB, emprego feminino, desemprego (ILO), I&amp;D % PIB, IDE, exportações % PIB, balança comercial % PIB, utilizadores internet, ensino superior (matrícula)</td><td>Anual</td><td>~6–18 meses</td></tr>
              </tbody>
            </table></div>
          </details>

          <details class="method-accordion">
            <summary>Isenção de Responsabilidade</summary>
            <p>Os dados apresentados neste dashboard são compilados a partir de fontes estatísticas oficiais para fins de <strong>análise e discussão económica</strong>. Este painel <strong>não constitui publicação oficial</strong> e não substitui os relatórios, comunicados ou bases de dados das entidades produtoras de estatística. Os dados podem divergir ligeiramente das publicações oficiais devido a diferenças de data de extracção, revisões posteriores, ou arredondamentos.</p>
          </details>

          <details class="method-accordion">
            <summary>Notas de Interpretação</summary>
            <ul>
              <li><strong>O IPI mede volume, não valor.</strong> Uma queda nos preços das matérias-primas pode coexistir com um IPI estável ou crescente. Para avaliar a saúde real de um sector, o IPI deve ser lido em conjunto com o índice de volume de negócios.</li>
              <li><strong>A média EU27 esconde dispersões enormes.</strong> O PIB per capita do Luxemburgo é ~10x o da Bulgária. Comparar Portugal com a "média EU27" sugere uma distância moderada (~68%), mas a mediana seria uma referência mais honesta do que a média ponderada.</li>
              <li><strong>Taxa de emprego elevada não implica qualidade de emprego.</strong> Portugal tem das taxas de emprego mais altas da UE, mas também tem dos salários medianos mais baixos da UE-15 e uma das maiores proporções de trabalhadores a receber o salário mínimo (~28% em 2025).</li>
              <li><strong>Séries longas escondem quebras metodológicas.</strong> Comparações de convergência desde 2000 atravessam revisões contabilísticas (SEC 95→SEC 2010), inclusão de actividades anteriormente não contabilizadas, e mudança de composição do EU27. Níveis absolutos ao longo de 24 anos devem ser lidos com cautela.</li>
              <li><strong>O diferencial em euros correntes amplifica a percepção de divergência.</strong> Parte do aumento do diferencial reflecte inflação acumulada. Em PPC, Portugal recuou de ~85% para ~82% da média — uma divergência real, mas menos dramática do que o diferencial nominal sugere.</li>
              <li><strong>Dados do Banco Mundial têm lag elevado.</strong> Os indicadores anuais (Gini, esperança de vida, ensino superior, etc.) chegam com 1–2 anos de atraso. O último ponto visível pode não reflectir a situação actual.</li>
            </ul>
          </details>

        </div>
      </div>`;

    // ── Dashboard info ────────────────────────────────────────────────
    const _appBase = window.location.origin + (window.__BASE_PATH__ || '');
    const _appDisplay = window.location.hostname + (window.__BASE_PATH__ || '');
    const dashboardHTML = `
      <div class="dashboard-info">
        <h3>Sobre o Prumo PT</h3>
        <ul>
          <li>URL: <a href="${_appBase}" target="_blank" rel="noopener" style="color:var(--c-pt)">${_appDisplay}</a></li>
          <li>Embed: <code>&lt;div class="cae-embed" data-indicators="SOURCE/indicator"&gt;&lt;/div&gt;</code></li>
        </ul>
      </div>`;

    // ── Render ────────────────────────────────────────────────────────
    body.innerHTML = `
      <!-- 1. Header -->
      <div class="ficha-header">
        <div class="ficha-meta">
          <span><strong>${totalIndicators}</strong> indicadores em <strong>${totalSrcs}</strong> fontes</span>
          <span>Última actualização: <strong>${updated}</strong></span>
          <span>Total de observações: <strong>${totalRows > 0 ? totalRows.toLocaleString('pt-PT') : '—'}</strong></span>
          <span>Cobertura: <strong>${earliest} → ${latest}</strong></span>
        </div>
      </div>

      <!-- 2. Source cards -->
      <div class="source-cards-list">
        ${allSrcs.map((src, i) => renderSourceCard(src, i)).join('')}
      </div>

      <!-- 3. Metodologia -->
      ${methodologyHTML}

      <!-- 4. Dashboard info -->
      ${dashboardHTML}

      <!-- 5. Disclaimer -->
      <div class="ficha-disclaimer">
        <p>Os dados apresentados são compilados de fontes oficiais para fins informativos e de análise. Não substituem as publicações oficiais dos organismos de origem. Para dados primários, consulte INE, Eurostat, Banco de Portugal e Banco Mundial.</p>
      </div>`;

  } catch (e) {
    console.error('[ficha] error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
});
