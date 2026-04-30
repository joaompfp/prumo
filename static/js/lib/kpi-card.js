/* ═══════════════════════════════════════════════════════════════
   kpi-card.js — KPI card shared utilities & event delegation
   Part of the Explain / Accessibility layer (V9)
   ═══════════════════════════════════════════════════════════════ */

/**
 * Global event delegation for KPI explain trigger buttons.
 * Works with dynamically rendered cards (innerHTML) — no per-card
 * binding needed. The handler is registered once on document.
 *
 * - Toggles .hidden on the sibling .kpi-explain panel
 * - stopPropagation prevents the card's deep-link click from firing
 */
document.addEventListener('click', function (e) {
  var trigger = e.target.closest('.kpi-explain-trigger');
  if (!trigger) return;

  // Don't trigger the card's deep-link navigation
  e.stopPropagation();
  e.preventDefault();

  var card = trigger.closest('.kpi-card') || trigger.closest('.painel-kpi');
  if (!card) return;

  var panel = card.querySelector('.kpi-explain');
  if (panel) panel.classList.toggle('hidden');
});

/**
 * Global event delegation for KPI share buttons.
 * Opens a share popover via PrumoLib.showSharePopover().
 */
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.kpi-share-btn');
  if (!btn) return;

  e.stopPropagation();
  e.preventDefault();

  var kpiId = btn.dataset.kpiId;
  if (!kpiId) return;

  var base = window.location.origin + (window.__BASE_PATH__ || '');
  var shareUrl = base + '/s/kpi/' + kpiId;
  var card = btn.closest('.kpi-card');
  var labelEl = card ? card.querySelector('.kpi-label') : null;
  var label = (labelEl ? labelEl.textContent : kpiId) + ' \u2014 Prumo PT';

  if (window.PrumoLib && PrumoLib.showSharePopover) {
    PrumoLib.showSharePopover(btn, { url: shareUrl, title: label, kpiId: kpiId });
  }
});
