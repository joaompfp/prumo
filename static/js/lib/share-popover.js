/* ═══════════════════════════════════════════════════════════════
   share-popover.js — Reusable share popover for KPI cards
   Part of PrumoLib — loaded before section scripts
   ═══════════════════════════════════════════════════════════════ */

window.PrumoLib = window.PrumoLib || {};

/**
 * Show a share popover anchored to the given element.
 * @param {HTMLElement} anchorEl - The button that triggered the popover
 * @param {Object} options - { url, title, kpiId }
 */
PrumoLib.showSharePopover = function(anchorEl, options) {
  'use strict';

  var url   = options.url   || '';
  var title = options.title || '';

  // Close any existing popover
  PrumoLib.closeSharePopover();

  // Build popover element
  var pop = document.createElement('div');
  pop.className = 'share-popover';
  pop.setAttribute('role', 'menu');

  // ── Copy link button ──────────────────────────────────────
  var copyBtn = document.createElement('button');
  copyBtn.className = 'share-popover-btn';
  copyBtn.setAttribute('role', 'menuitem');
  copyBtn.innerHTML =
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="5" y="5" width="8" height="8" rx="1.5"/>' +
      '<path d="M11 3H4a1 1 0 00-1 1v7"/>' +
    '</svg>' +
    '<span>' + i18n.t('share.copy_link') + '</span>';
  copyBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function() {
        _showCopied(copyBtn);
      });
    } else {
      // Fallback for older browsers / non-HTTPS
      var ta = document.createElement('textarea');
      ta.value = url;
      ta.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      _showCopied(copyBtn);
    }
  });

  // ── Download image link ───────────────────────────────────
  var imgBtn = document.createElement('a');
  imgBtn.className = 'share-popover-btn';
  imgBtn.setAttribute('role', 'menuitem');
  imgBtn.href = url + '/image.png';
  imgBtn.target = '_blank';
  imgBtn.rel = 'noopener';
  imgBtn.innerHTML =
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M8 2v8M5 7l3 3 3-3"/>' +
      '<path d="M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2"/>' +
    '</svg>' +
    '<span>' + i18n.t('share.download_image') + '</span>';

  // ── Separator ─────────────────────────────────────────────
  var sep = document.createElement('div');
  sep.className = 'share-popover-sep';

  // ── Twitter/X share ───────────────────────────────────────
  var twBtn = document.createElement('a');
  twBtn.className = 'share-popover-btn';
  twBtn.setAttribute('role', 'menuitem');
  twBtn.href = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
  twBtn.target = '_blank';
  twBtn.rel = 'noopener';
  twBtn.innerHTML =
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">' +
      '<path d="M9.47 6.77L15.3 0h-1.38L8.85 5.88 4.81 0H.18l6.11 8.9L.18 16h1.38l5.35-6.21L11.19 16h4.63L9.47 6.77zm-1.9 2.2l-.62-.89L2.05 1.04h2.12l3.98 5.69.62.89 5.17 7.4h-2.12L7.57 8.97z"/>' +
    '</svg>' +
    '<span>' + i18n.t('share.share_twitter') + '</span>';

  // ── LinkedIn share ────────────────────────────────────────
  var liBtn = document.createElement('a');
  liBtn.className = 'share-popover-btn';
  liBtn.setAttribute('role', 'menuitem');
  liBtn.href = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(url);
  liBtn.target = '_blank';
  liBtn.rel = 'noopener';
  liBtn.innerHTML =
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">' +
      '<path d="M13.6 0H2.4C1.08 0 0 1.08 0 2.4v11.2C0 14.92 1.08 16 2.4 16h11.2c1.32 0 2.4-1.08 2.4-2.4V2.4C16 1.08 14.92 0 13.6 0zM4.75 13.6H2.4V6h2.35v7.6zM3.58 5.04c-.75 0-1.36-.62-1.36-1.36s.6-1.36 1.36-1.36c.75 0 1.36.61 1.36 1.36s-.61 1.36-1.36 1.36zM13.6 13.6h-2.35V9.92c0-.88-.02-2-.1-2.14-.12-.2-.39-.32-.68-.32-.86 0-1.05.66-1.05 1.6v4.54H7.08V6h2.26v1.04h.03c.31-.6 1.08-1.23 2.22-1.23 2.38 0 2.82 1.57 2.82 3.6v4.19h-.01z"/>' +
    '</svg>' +
    '<span>' + i18n.t('share.share_linkedin') + '</span>';

  // ── WhatsApp share ────────────────────────────────────────
  var waBtn = document.createElement('a');
  waBtn.className = 'share-popover-btn';
  waBtn.setAttribute('role', 'menuitem');
  waBtn.href = 'https://api.whatsapp.com/send?text=' + encodeURIComponent(title + ' ' + url);
  waBtn.target = '_blank';
  waBtn.rel = 'noopener';
  waBtn.innerHTML =
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">' +
      '<path d="M13.6 2.33A7.96 7.96 0 008.02 0C3.63 0 .06 3.57.06 7.95c0 1.4.37 2.77 1.06 3.97L0 16l4.2-1.1a7.93 7.93 0 003.8.97h.01c4.38 0 7.95-3.57 7.95-7.96a7.9 7.9 0 00-2.36-5.58zM8.02 14.55c-1.18 0-2.34-.32-3.35-.92l-.24-.14-2.49.65.66-2.43-.16-.25A6.56 6.56 0 011.4 7.95c0-3.64 2.97-6.6 6.62-6.6 1.77 0 3.43.69 4.68 1.93a6.56 6.56 0 011.93 4.68c0 3.64-2.97 6.59-6.61 6.59zm3.63-4.94c-.2-.1-1.17-.58-1.35-.65-.18-.06-.31-.1-.44.1-.13.2-.51.65-.63.78-.11.13-.23.15-.43.05-.2-.1-.84-.31-1.6-.99-.59-.53-.99-1.18-1.1-1.38-.12-.2-.01-.31.09-.41.09-.09.2-.23.3-.35.1-.12.13-.2.2-.34.07-.13.03-.25-.02-.35s-.44-1.06-.6-1.45c-.16-.38-.32-.33-.44-.34h-.38c-.13 0-.34.05-.52.25-.18.2-.68.66-.68 1.62 0 .96.7 1.88.8 2.01.1.13 1.37 2.1 3.33 2.94.46.2.83.32 1.11.41.47.15.9.13 1.23.08.38-.06 1.17-.48 1.33-.94.17-.46.17-.86.12-.94-.05-.08-.18-.13-.38-.23z"/>' +
    '</svg>' +
    '<span>' + i18n.t('share.share_whatsapp') + '</span>';

  // Assemble popover
  pop.appendChild(copyBtn);
  pop.appendChild(imgBtn);
  pop.appendChild(sep);
  pop.appendChild(twBtn);
  pop.appendChild(liBtn);
  pop.appendChild(waBtn);

  document.body.appendChild(pop);

  // Position relative to anchor
  _positionPopover(pop, anchorEl);

  // Close on click outside (after a tick to avoid the triggering click)
  setTimeout(function() {
    document._sharePopoverClose = function(e) {
      if (!pop.contains(e.target) && e.target !== anchorEl) {
        PrumoLib.closeSharePopover();
      }
    };
    document.addEventListener('click', document._sharePopoverClose, true);
  }, 0);

  // Close on Escape
  document._sharePopoverEsc = function(e) {
    if (e.key === 'Escape') PrumoLib.closeSharePopover();
  };
  document.addEventListener('keydown', document._sharePopoverEsc);

  // Store reference for cleanup
  PrumoLib._activePopover = pop;
};

/**
 * Close any open share popover.
 */
PrumoLib.closeSharePopover = function() {
  if (PrumoLib._activePopover) {
    PrumoLib._activePopover.remove();
    PrumoLib._activePopover = null;
  }
  if (document._sharePopoverClose) {
    document.removeEventListener('click', document._sharePopoverClose, true);
    document._sharePopoverClose = null;
  }
  if (document._sharePopoverEsc) {
    document.removeEventListener('keydown', document._sharePopoverEsc);
    document._sharePopoverEsc = null;
  }
};

/**
 * Position popover below-right of anchor, flipping if near viewport edge.
 */
function _positionPopover(pop, anchor) {
  var rect = anchor.getBoundingClientRect();
  var top = rect.bottom + 6;
  var left = rect.left;

  // Measure popover (briefly make visible off-screen to measure)
  pop.style.visibility = 'hidden';
  pop.style.left = '0px';
  pop.style.top = '0px';
  var pw = pop.offsetWidth;
  var ph = pop.offsetHeight;
  pop.style.visibility = '';

  // Flip horizontally if too close to right edge
  if (left + pw > window.innerWidth - 12) {
    left = rect.right - pw;
  }
  // Clamp to left edge
  if (left < 8) left = 8;

  // Flip vertically if too close to bottom edge
  if (top + ph > window.innerHeight - 12) {
    top = rect.top - ph - 6;
  }

  pop.style.left = left + 'px';
  pop.style.top = top + 'px';
}

/**
 * Show "Copied!" feedback on a button, then revert.
 */
function _showCopied(btn) {
  var span = btn.querySelector('span');
  var original = span.textContent;
  span.textContent = i18n.t('share.copied');
  btn.classList.add('copied');
  setTimeout(function() {
    span.textContent = original;
    btn.classList.remove('copied');
  }, 1500);
}
