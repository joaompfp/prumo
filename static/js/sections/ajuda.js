/* ═══════════════════════════════════════════════════════════════
   ajuda.js — Ajuda e Sobre
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('ajuda', () => {
  const container = document.getElementById('ajuda');
  const body = container.querySelector('.section-body');

  const titleEl = container.querySelector('.section-title');
  if (titleEl) titleEl.textContent = 'Como usar o Prumo PT';

  body.innerHTML = `
    <div class="ajuda-wrap">

      <!-- ── Guia de secções — collapsible cards ───────────────── -->
      <h3 class="ajuda-h3">Guia de Secções</h3>
      <div class="ajuda-cards-list">

        <details class="ajuda-card-collapse" open>
          <summary class="ajuda-card-summary">
            <span class="ajuda-icon">📊</span>
            <span class="ajuda-card-title">Painel</span>
          </summary>
          <div class="ajuda-card-body">
            <p>Visão geral de Portugal: 30+ indicadores organizados em 7 temas — Custo de Vida, Indústria, Emprego, Conjuntura, Energia, Externo e Competitividade. Cada cartão mostra o valor mais recente, tendência e variação homóloga.</p>
            <ul class="ajuda-tips">
              <li>Clique em qualquer cartão para abrir o indicador na secção Análise.</li>
              <li>O botão <strong>+ IA</strong> no início da página gera análise interpretativa (Claude Sonnet) de todos os temas, com leituras relacionadas por secção.</li>
            </ul>
          </div>
        </details>

        <details class="ajuda-card-collapse">
          <summary class="ajuda-card-summary">
            <span class="ajuda-icon">🌍</span>
            <span class="ajuda-card-title">Comparativos</span>
          </summary>
          <div class="ajuda-card-body">
            <p>Compara Portugal com todos os países da UE e do mundo em dezenas de indicadores. Combina dados do Eurostat (EU27, alta frequência) com o Banco Mundial (cobertura global, anual) numa única interface. Seleccione países por grupo (UE 27, Resto da Europa, OCDE, PALOP, Emergentes) ou use presets predefinidos.</p>
            <ul class="ajuda-tips">
              <li><strong>Linhas</strong>: evolução temporal de todos os países seleccionados. Passe o rato sobre a legenda para destacar uma série.</li>
              <li><strong>Snapshot</strong>: gráfico de barras com o último valor disponível, ordenado por país.</li>
              <li>Indicadores com <strong>★</strong> são compostos: Eurostat para EU27 + Banco Mundial para o resto.</li>
              <li>Países sem dados para o indicador seleccionado aparecem a cinzento e não são seleccionáveis.</li>
              <li>Os dados do Banco Mundial têm lag de 1–2 anos; o Eurostat, 1–3 meses.</li>
            </ul>
          </div>
        </details>

        <details class="ajuda-card-collapse">
          <summary class="ajuda-card-summary">
            <span class="ajuda-icon ajuda-icon-svg"><img src="${(window.__BASE_PATH__||'')}/static/images/prumo/icon-analise.svg" width="20" height="20" alt="" aria-hidden="true" style="vertical-align:middle;margin-bottom:1px"></span>
            <span class="ajuda-card-title">Análise</span>
          </summary>
          <div class="ajuda-card-body">
            <p>Explorador livre de séries temporais. Pesquise qualquer indicador das 9 fontes disponíveis (mais de 370 combinações fonte/indicador), ajuste o intervalo temporal e visualize o gráfico. Uma interpretação por IA (Claude Haiku) adapta o foco ao horizonte: conjuntural para 1 ano, estrutural para 10 anos — com links para artigos e relatórios recentes relacionados.</p>
            <ul class="ajuda-tips">
              <li>Pode seleccionar e sobrepor múltiplos indicadores em simultâneo.</li>
              <li>Quando dois indicadores têm unidades incompatíveis, o gráfico usa dois eixos verticais automaticamente.</li>
              <li>Botão <strong>CSV</strong> exporta os dados brutos para análise externa.</li>
              <li>Botão <strong>Partilhar</strong> copia o URL com o estado actual do gráfico.</li>
              <li>Deep-link a partir da Ficha Técnica: clique no código de qualquer indicador.</li>
            </ul>
          </div>
        </details>

        <details class="ajuda-card-collapse">
          <summary class="ajuda-card-summary">
            <span class="ajuda-icon">📋</span>
            <span class="ajuda-card-title">Ficha Técnica</span>
          </summary>
          <div class="ajuda-card-body">
            <p>Documentação completa de todas as fontes e indicadores disponíveis na base de dados: cobertura temporal, frequência de actualização, unidade e notas metodológicas. Inclui todas as séries — incluindo as que não estão no Painel.</p>
            <ul class="ajuda-tips">
              <li>Clicar no código de qualquer indicador leva-o directamente à secção Análise.</li>
              <li>Indicadores com cobertura multi-país (ex: Eurostat por nação) abrem nos Comparativos.</li>
              <li>A secção Metodologia explica ajustamento sazonal, bases de índice e comparabilidade.</li>
            </ul>
          </div>
        </details>

      </div>

      <!-- ── Perguntas frequentes ──────────────────────────────── -->
      <h3 class="ajuda-h3" style="margin-top:var(--sp-2xl)">Perguntas Frequentes</h3>
      <div class="ajuda-faq">

        <details class="method-accordion">
          <summary>Os dados são em tempo real?</summary>
          <p>Não. Os dados são actualizados periodicamente a partir das publicações oficiais de cada fonte (INE, Eurostat, Banco de Portugal, etc.). O atraso ("lag") varia por indicador: o IPI sai ~2 meses após o mês de referência; o PIB trimestral, ~3 meses após o trimestre; os dados do Banco Mundial chegam com 1–2 anos de atraso. A data da última actualização está indicada no topo do Painel.</p>
        </details>

        <details class="method-accordion">
          <summary>O que significa "ajustamento sazonal"?</summary>
          <p>Muitas séries económicas têm padrões que se repetem regularmente — a produção industrial cai sempre em Agosto por causa das férias, por exemplo. O ajustamento sazonal remove esses padrões previsíveis para que se possam comparar meses consecutivos sem distorção. As séries com "(dessaz.)" são assim tratadas. O método usado pelo INE e Eurostat é o TRAMO-SEATS.</p>
        </details>

        <details class="method-accordion">
          <summary>Posso usar estes dados num relatório?</summary>
          <p>Os dados são provenientes de fontes oficiais públicas (INE, Eurostat, Banco de Portugal, etc.). Pode usá-los citando a fonte primária correspondente. O Prumo PT não é uma publicação oficial e não substitui os dados originais. Para dados primários, consulte directamente cada entidade.</p>
        </details>

        <details class="method-accordion">
          <summary>O que é o EU27_2020?</summary>
          <p>É o agregado do Eurostat para os 27 Estados-membros actuais da União Europeia após a saída do Reino Unido (Brexit, Fevereiro de 2020). O Eurostat recalcula retroactivamente as séries históricas excluindo o UK — assim, a série "EU27_2020" é coerente em todos os anos, mesmo para períodos anteriores a 2020. É a referência mais representativa da UE actual para comparações históricas.</p>
        </details>

        <details class="method-accordion">
          <summary>Como funciona a análise com IA?</summary>
          <p>A secção Análise usa Claude Haiku para gerar um parágrafo interpretativo a partir dos dados visíveis no gráfico, com pesquisa na web para sugerir leituras recentes relacionadas. O foco adapta-se ao horizonte temporal: 1 ano → análise conjuntural; 5 anos → ciclo económico; 10 anos → tendência estrutural. O Painel usa Claude Sonnet para análise mais extensa de cada tema, também com links por secção temática.</p>
        </details>

        <details class="method-accordion">
          <summary>Porque é que alguns países aparecem a cinzento nos Comparativos?</summary>
          <p>Os países a cinzento não têm dados disponíveis na base de dados para o indicador seleccionado. Isso acontece porque nem todas as fontes cobrem todos os países: o Eurostat cobre principalmente a EU27; o Banco Mundial tem cobertura global mas com gaps em séries sectoriais. Ao mudar de indicador, a disponibilidade por país actualiza-se automaticamente.</p>
        </details>

        <details class="method-accordion">
          <summary>O que são os indicadores compostos (★)?</summary>
          <p>Para alguns indicadores com grande interesse comparativo (como Desemprego e Taxa de Emprego), combinamos duas fontes: o Eurostat para países da EU27 (dados mais frequentes e detalhados) e o Banco Mundial para o restante do mundo (dados anuais, cobertura global). O resultado é uma série única e coerente com cobertura mundial. A nota ★ identifica estes indicadores.</p>
        </details>

        <details class="method-accordion">
          <summary>Encontrei um erro ou tenho uma sugestão. O que faço?</summary>
          <p>Envie um <a href="mailto:joao.mpfp+prumo@gmail.com" style="color:var(--c-pt)">e-mail</a> com uma descrição do problema (qual indicador, que valor parece errado, o que esperaria ver). Erros de dados são prioritários — obrigado pela ajuda a melhorar o Prumo PT.</p>
        </details>

      </div>

      <!-- ── Sobre ───────────────────────────────────────────────── -->
      <h3 class="ajuda-h3" style="margin-top:var(--sp-2xl)">Sobre o Prumo PT</h3>
      <div class="ajuda-sobre">
        <p>O nome combina dois elementos. <strong>Prumo</strong> — instrumento de precisão da construção e engenharia civil, usado para verificar se uma estrutura está verdadeiramente vertical. Não orienta, não mede distâncias — verifica se está direito. A metáfora é exacta: esta ferramenta não descreve a economia portuguesa tal como nos é apresentada — verifica se o que nos dizem corresponde ao que os dados mostram. <strong>PT</strong> — âncora geográfica e identitária. Portugal. Directo, sem adjectivos.</p>

        <p>O ponto de partida é concreto: o que acontece à produção, ao emprego, aos preços, à energia. Não aos mercados financeiros em abstracto, mas à realidade que se mede em folhas de salário, em facturas de electricidade, em taxas de desemprego. A economia não é uma força da natureza — é o resultado de decisões e de condições que os dados ajudam a tornar visíveis.</p>

        <p>O Prumo PT reúne dados de 9 fontes estatísticas oficiais — INE, Eurostat, Banco de Portugal, OCDE, Banco Mundial, REN, DGEG, ERSE, FRED — e organiza-os de forma acessível e comparável, com análise interpretativa integrada por IA. Foi construído para quem analisa a conjuntura económica portuguesa e quer acesso rápido, consolidado e fundamentado. Não é uma publicação oficial. É uma ferramenta de trabalho.</p>

        <div class="ajuda-fontes-line">
          <strong>Fontes e licenças:</strong><br>
          <a href="https://www.ine.pt" target="_blank" rel="noopener">INE</a> ·
          <a href="https://ec.europa.eu/eurostat" target="_blank" rel="noopener">Eurostat</a>
          (<a href="https://ec.europa.eu/eurostat/help/copyright-notice" target="_blank" rel="noopener">CC BY 4.0</a>) ·
          <a href="https://www.bportugal.pt" target="_blank" rel="noopener">Banco de Portugal</a>
          (<a href="https://www.bportugal.pt/termos-e-condicoes" target="_blank" rel="noopener">termos</a>) ·
          <a href="https://stats.oecd.org" target="_blank" rel="noopener">OCDE</a>
          (<a href="https://www.oecd.org/en/about/terms-conditions.html" target="_blank" rel="noopener">termos</a>) ·
          <a href="https://data.worldbank.org" target="_blank" rel="noopener">Banco Mundial</a>
          (<a href="https://data.worldbank.org/summary-terms-of-use" target="_blank" rel="noopener">CC BY 4.0</a>) ·
          <a href="https://datahub.ren.pt" target="_blank" rel="noopener">REN</a>
          (<a href="https://datahub.ren.pt/pt/termos-legais-e-condicoes-gerais/" target="_blank" rel="noopener">termos</a>) ·
          <a href="https://www.dgeg.gov.pt" target="_blank" rel="noopener">DGEG</a> ·
          <a href="https://www.erse.pt" target="_blank" rel="noopener">ERSE</a> ·
          <a href="https://fred.stlouisfed.org" target="_blank" rel="noopener">FRED</a>
          (<a href="https://fred.stlouisfed.org/legal/" target="_blank" rel="noopener">termos</a>)
        </div>
      </div>

    </div>`;
});
