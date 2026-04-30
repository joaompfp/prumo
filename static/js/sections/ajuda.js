/* ═══════════════════════════════════════════════════════════════
   ajuda.js — Ajuda e Sobre
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('ajuda', () => {
  const container = document.getElementById('ajuda');
  const body = container.querySelector('.section-body');

  // Hide redundant section header — content headings are enough
  const header = container.querySelector('.section-header');
  if (header) header.style.display = 'none';

  const nIndicators = window.__N_INDICATORS__ || 420;

  const sections = [
    {
      type: 'about',
      title: i18n.t('ajuda.what_is.title'),
      body: `
        <p>${i18n.t('ajuda.what_is.intro')}</p>
        <ul class="ajuda-tips">
          <li>${i18n.t('ajuda.what_is.indicators', {count: nIndicators})}</li>
          <li>${i18n.t('ajuda.what_is.sources')}</li>
          <li>${i18n.t('ajuda.what_is.ai_analysis')}</li>
          <li>${i18n.t('ajuda.what_is.disclaimer')}</li>
        </ul>
        <div class="ajuda-fontes-line">
          <strong>${i18n.t('ajuda.what_is.sources_licenses')}:</strong><br>
          <a href="https://www.ine.pt" target="_blank" rel="noopener">INE</a> ·
          <a href="https://ec.europa.eu/eurostat" target="_blank" rel="noopener">Eurostat</a>
          (<a href="https://ec.europa.eu/eurostat/help/copyright-notice" target="_blank" rel="noopener">CC BY 4.0</a>) ·
          <a href="https://www.bportugal.pt" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.bportugal')}</a>
          (<a href="https://www.bportugal.pt/termos-e-condicoes" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.terms')}</a>) ·
          <a href="https://stats.oecd.org" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.oecd')}</a>
          (<a href="https://www.oecd.org/en/about/terms-conditions.html" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.terms')}</a>) ·
          <a href="https://data.worldbank.org" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.worldbank')}</a>
          (<a href="https://data.worldbank.org/summary-terms-of-use" target="_blank" rel="noopener">CC BY 4.0</a>) ·
          <a href="https://datahub.ren.pt" target="_blank" rel="noopener">REN</a>
          (<a href="https://datahub.ren.pt/pt/termos-legais-e-condicoes-gerais/" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.terms')}</a>) ·
          <a href="https://www.dgeg.gov.pt" target="_blank" rel="noopener">DGEG</a> ·
          <a href="https://www.erse.pt" target="_blank" rel="noopener">ERSE</a> ·
          <a href="https://fred.stlouisfed.org" target="_blank" rel="noopener">FRED</a>
          (<a href="https://fred.stlouisfed.org/legal/" target="_blank" rel="noopener">${i18n.t('ajuda.what_is.terms')}</a>)
        </div>`
    },
  ];

  // Section guide cards
  const guideCards = [
    {
      icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="#444" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><rect x="1.5" y="1.5" width="5" height="5" rx="0.5"/><rect x="9.5" y="1.5" width="5" height="5" rx="0.5"/><rect x="1.5" y="9.5" width="5" height="5" rx="0.5"/><rect x="9.5" y="9.5" width="5" height="5" rx="0.5"/></svg>',
      title: i18n.t('ajuda.sections.painel.title'),
      body: i18n.t('ajuda.sections.painel.body'),
      tips: [
        i18n.t('ajuda.sections.painel.tip_click'),
        i18n.t('ajuda.sections.painel.tip_ia'),
      ],
      open: true,
    },
    {
      icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="#444" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c-2 1.5-3 4-3 6.5s1 5 3 6.5M8 1.5c2 1.5 3 4 3 6.5s-1 5-3 6.5"/></svg>',
      title: i18n.t('ajuda.sections.comparativos.title'),
      body: i18n.t('ajuda.sections.comparativos.body'),
      tips: [
        i18n.t('ajuda.sections.comparativos.tip_lines'),
        i18n.t('ajuda.sections.comparativos.tip_snapshot'),
        i18n.t('ajuda.sections.comparativos.tip_composite'),
        i18n.t('ajuda.sections.comparativos.tip_grey'),
        i18n.t('ajuda.sections.comparativos.tip_lag'),
      ],
    },
    {
      icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="#444" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="6.5" cy="6.5" r="4.5"/><path d="M10 10l4 4M4 8.5l1.5-2L7 8l2-3"/></svg>',
      title: i18n.t('ajuda.sections.analise.title'),
      body: i18n.t('ajuda.sections.analise.body'),
      tips: [
        i18n.t('ajuda.sections.analise.tip_multi'),
        i18n.t('ajuda.sections.analise.tip_dual_axis'),
        i18n.t('ajuda.sections.analise.tip_csv'),
        i18n.t('ajuda.sections.analise.tip_share'),
        i18n.t('ajuda.sections.analise.tip_deeplink'),
      ],
    },
    {
      icon: '<svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="#444" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2h10v12H3zM5.5 5.5h5M5.5 8h5M5.5 10.5h2.5"/><circle cx="11" cy="10.5" r="1.5" fill="#444" stroke="none" opacity=".7"/></svg>',
      title: i18n.t('ajuda.sections.metodologia.title'),
      body: i18n.t('ajuda.sections.metodologia.body'),
      tips: [
        i18n.t('ajuda.sections.metodologia.tip_click_code'),
        i18n.t('ajuda.sections.metodologia.tip_multi_country'),
        i18n.t('ajuda.sections.metodologia.tip_methodology'),
      ],
    },
  ];

  // FAQ items
  const faqItems = [
    { q: i18n.t('ajuda.faq.realtime.q'), a: i18n.t('ajuda.faq.realtime.a') },
    { q: i18n.t('ajuda.faq.seasonal.q'), a: i18n.t('ajuda.faq.seasonal.a') },
    { q: i18n.t('ajuda.faq.report.q'), a: i18n.t('ajuda.faq.report.a') },
    { q: i18n.t('ajuda.faq.eu27.q'), a: i18n.t('ajuda.faq.eu27.a') },
    { q: i18n.t('ajuda.faq.ai.q'), a: i18n.t('ajuda.faq.ai.a') },
    { q: i18n.t('ajuda.faq.grey_countries.q'), a: i18n.t('ajuda.faq.grey_countries.a') },
    { q: i18n.t('ajuda.faq.composite.q'), a: i18n.t('ajuda.faq.composite.a') },
    { q: i18n.t('ajuda.faq.error.q'), a: i18n.t('ajuda.faq.error.a') },
  ];

  body.innerHTML = `
    <div class="ajuda-wrap">

      <!-- About section -->
      <h3 class="ajuda-h3">${sections[0].title}</h3>
      <div class="ajuda-sobre">
        ${sections[0].body}
      </div>

      <!-- Section guide -->
      <h3 class="ajuda-h3" style="margin-top:var(--sp-2xl)">${i18n.t('ajuda.guide.title')}</h3>
      <div class="ajuda-cards-list">
        ${guideCards.map(card => `
        <details class="ajuda-card-collapse"${card.open ? ' open' : ''}>
          <summary class="ajuda-card-summary">
            <span class="ajuda-icon">${card.icon}</span>
            <span class="ajuda-card-title">${card.title}</span>
          </summary>
          <div class="ajuda-card-body">
            <p>${card.body}</p>
            <ul class="ajuda-tips">
              ${card.tips.map(tip => `<li>${tip}</li>`).join('')}
            </ul>
          </div>
        </details>`).join('')}
      </div>

      <!-- FAQ -->
      <h3 class="ajuda-h3" style="margin-top:var(--sp-2xl)">${i18n.t('ajuda.faq.title')}</h3>
      <div class="ajuda-faq">
        ${faqItems.map(item => `
        <details class="method-accordion">
          <summary>${item.q}</summary>
          <p>${item.a}</p>
        </details>`).join('')}
      </div>

      <!-- Author -->
      <h3 class="ajuda-h3" style="margin-top:var(--sp-2xl)">${i18n.t('ajuda.author.title')}</h3>
      <div class="ajuda-sobre">
        <p>${i18n.t('ajuda.author.body')}</p>
        <p style="font-size:var(--fs-xs);color:var(--c-muted);margin-top:var(--sp-sm)"><a href="mailto:joao.mpfp+prumo@gmail.com" style="color:var(--c-pt)">${i18n.t('ajuda.author.email')}</a> · <a href="https://joao.date" target="_blank" rel="noopener" style="color:var(--c-pt)">joao.date</a></p>
      </div>

    </div>`;
});
