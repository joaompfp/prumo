/* ═══════════════════════════════════════════════════════════════
   markdown.js — Minimal markdown renderer (shared utility)
   Extracted from painel.js for reuse across sections.
   ═══════════════════════════════════════════════════════════════ */

window.PrumoLib = window.PrumoLib || {};

/**
 * Minimal markdown → HTML: headings, **bold**, *italic*, lists, paragraphs.
 * Strips --- separators.
 */
PrumoLib.renderMd = function(text) {
  return text
    .replace(/^---+\s*$/gm, '')
    .replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, m => `<ul>${m}</ul>`)
    .split(/\n\n+/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => p.startsWith('<ul>') ? p : `<p>${p.replace(/\n/g, ' ')}</p>`)
    .join('');
};
