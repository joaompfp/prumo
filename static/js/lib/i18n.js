/* =================================================================
   i18n.js — Lightweight i18n runtime for Prumo PT
   Supports dot-notation keys, {{param}} interpolation,
   data-i18n DOM attributes, and lazy language loading.
   ================================================================= */

window.i18n = (function() {
  'use strict';

  // PT strings are loaded from pt.json on first need (or inline for zero-latency).
  // The runtime always starts in PT to avoid FOUC for Portuguese users.
  let _PT = null;  // loaded lazily
  let _lang = localStorage.getItem('prumo-output-language') || 'pt';
  let _strings = null;
  let _loaded = {};
  let _ready = false;
  let _readyCallbacks = [];

  const BASE = window.__BASE_PATH__ || '';

  // ── Deep key lookup via dot-notation ────────────────────────────
  function _resolve(obj, key) {
    if (!obj || !key) return undefined;
    return key.split('.').reduce(function(o, k) { return o && o[k]; }, obj);
  }

  // ── Main translation function ──────────────────────────────────
  function t(key, params) {
    var val = _resolve(_strings, key);
    if (val === undefined && _strings !== _PT) {
      // Fallback to PT
      val = _resolve(_PT, key);
    }
    if (val === undefined) return key; // Return key as last resort
    if (params && typeof val === 'string') {
      Object.keys(params).forEach(function(k) {
        val = val.replace(new RegExp('\\{\\{' + k + '\\}\\}', 'g'), params[k]);
      });
    }
    return val;
  }

  // ── Load a language JSON file ──────────────────────────────────
  function _loadLang(lang) {
    if (_loaded[lang]) return Promise.resolve(_loaded[lang]);
    return fetch(BASE + '/static/i18n/' + lang + '.json?v=3')
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        _loaded[lang] = data;
        return data;
      });
  }

  // ── Set active language ────────────────────────────────────────
  function setLang(lang) {
    if (lang === _lang && _loaded[lang]) {
      _strings = _loaded[lang];
      return Promise.resolve();
    }
    _lang = lang;
    localStorage.setItem('prumo-output-language', lang);
    if (_loaded[lang]) {
      _strings = _loaded[lang];
      _fireChange();
      return Promise.resolve();
    }
    return _loadLang(lang)
      .then(function(data) {
        _strings = data;
        _fireChange();
      })
      .catch(function(err) {
        console.warn('[i18n] Failed to load', lang, err);
        _strings = _PT; // fallback to PT
      });
  }

  // ── Global params available to all data-i18n replacements ──────
  var _globalParams = { n: window.__N_INDICATORS__ || '368' };

  // ── Re-scan DOM for data-i18n attributes + dispatch event ──────
  function _fireChange() {
    _globalParams.n = window.__N_INDICATORS__ || '368';
    document.querySelectorAll('[data-i18n]').forEach(function(el) {
      el.textContent = t(el.dataset.i18n, _globalParams);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(function(el) {
      el.title = t(el.dataset.i18nTitle);
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function(el) {
      el.innerHTML = t(el.dataset.i18nHtml, _globalParams);
    });
    // Update html lang attribute
    document.documentElement.lang = _lang === 'pt' ? 'pt-PT' : _lang;
    // Dispatch event for JS sections to re-render
    window.dispatchEvent(new CustomEvent('i18n-change', { detail: { lang: _lang } }));
  }

  // ── Convenience helpers ────────────────────────────────────────
  function months() {
    return t('fmt.months') || ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  }

  function countryName(code) {
    return t('countries.' + code) || code;
  }

  function lang() { return _lang; }

  // ── Ready callback — fires when PT strings are loaded ──────────
  function onReady(fn) {
    if (_ready) { fn(); return; }
    _readyCallbacks.push(fn);
  }

  function _notifyReady() {
    _ready = true;
    _readyCallbacks.forEach(function(fn) { try { fn(); } catch(e) {} });
    _readyCallbacks = [];
  }

  // ── Initialisation — load PT synchronously to avoid race conditions ──
  // PT strings MUST be available before any t() call from other scripts.
  try {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/static/i18n/pt.json?v=3', false); // synchronous, versioned
    xhr.send();
    if (xhr.status === 200) {
      _PT = JSON.parse(xhr.responseText);
    } else {
      _PT = {};
    }
  } catch(e) {
    console.warn('[i18n] Failed to load PT strings:', e);
    _PT = {};
  }
  _loaded.pt = _PT;
  _strings = _PT;
  _ready = true;

  // If non-PT language was selected, load it async (PT is the fallback)
  if (_lang !== 'pt') {
    _loadLang(_lang).then(function(langData) {
      _strings = langData;
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _fireChange);
      } else {
        _fireChange();
      }
    }).catch(function() {
      _strings = _PT;
    });
  }

  return { t: t, setLang: setLang, months: months, countryName: countryName, lang: lang, onReady: onReady };
})();
