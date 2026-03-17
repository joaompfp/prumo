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
