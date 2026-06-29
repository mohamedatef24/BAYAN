/**
 * Bayan — Background Service Worker (Phase 7.1 Simplified)
 *
 * Single network boundary. Owns:
 *   1. Context menu → side panel (Phase 5)
 *   2. API calls with cache + timeout + retry (Phase 7)
 *
 * Uses: BAYAN (shared/constants.js), bayanHash (shared/hash.js)
 *   loaded via importScripts().
 */

importScripts('shared/constants.js', 'shared/hash.js');

// ── Context constants ──
const ACTIONS = { CORRECT: 'correct', SUMMARIZE: 'summarize', DIALECT: 'dialect', QURAN: 'quran' };
const CONTEXT_KEYS = ['contextAction', 'contextText', 'contextTimestamp'];
const SIDE_PANEL_PATH = 'sidepanel/sidepanel.html';

// ── Deduplication cache ──
const _cache = new Map();

function cacheGet(text) {
  const key = bayanHash(text);
  const entry = _cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > BAYAN.CACHE_TTL_MS) { _cache.delete(key); return null; }
  if (entry.text !== text) return null;
  // FIX-19: LRU — move to end on access (Map maintains insertion order)
  _cache.delete(key);
  _cache.set(key, entry);
  return entry.data;
}

function cacheSet(text, data) {
  const key = bayanHash(text);
  if (_cache.size >= BAYAN.CACHE_MAX_ENTRIES) {
    _cache.delete(_cache.keys().next().value);
  }
  _cache.set(key, { text, data, ts: Date.now() });
}

// ── Storage helper ──
function getStorage() {
  return chrome.storage?.session || chrome.storage?.local;
}

// ══════════════════════════════════════════════════════════
// Context Menu
// ══════════════════════════════════════════════════════════

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'bayan-correct',
      title: 'تصحيح النص مع بيان',
      contexts: ['selection'],
    });
    chrome.contextMenus.create({
      id: 'bayan-summarize',
      title: 'تلخيص النص مع بيان',
      contexts: ['selection'],
    });
    chrome.contextMenus.create({
      id: 'bayan-dialect',
      title: 'تحويل للفصحى مع بيان',
      contexts: ['selection'],
    });
    chrome.contextMenus.create({
      id: 'bayan-quran',
      title: 'تدقيق النص القرآني مع بيان',
      contexts: ['selection'],
    });
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const selectedText = info.selectionText?.trim();
  if (!selectedText) return;

  let action = null;
  if (info.menuItemId === 'bayan-correct') action = ACTIONS.CORRECT;
  if (info.menuItemId === 'bayan-summarize') action = ACTIONS.SUMMARIZE;
  if (info.menuItemId === 'bayan-dialect') action = ACTIONS.DIALECT;
  if (info.menuItemId === 'bayan-quran') action = ACTIONS.QURAN;
  if (!action) return;

  // Open side panel IMMEDIATELY (preserve user gesture)
  if (chrome.sidePanel) {
    chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {
      chrome.tabs.create({ url: chrome.runtime.getURL(SIDE_PANEL_PATH) });
    });
  } else {
    chrome.tabs.create({ url: chrome.runtime.getURL(SIDE_PANEL_PATH) });
  }

  // Store context (async)
  const storage = getStorage();
  storage.set({
    contextAction: action,
    contextText: selectedText,
    contextTimestamp: Date.now(),
  });
  setTimeout(() => storage.remove(CONTEXT_KEYS), 15000);
});

// ══════════════════════════════════════════════════════════
// Message Handler
// ══════════════════════════════════════════════════════════

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'HEALTH_CHECK') {
    sendResponse({
      status: 'ok',
      version: chrome.runtime.getManifest().version,
      cache: _cache.size,
    });
    return true;
  }

  if (message.type === 'CLEAR_CONTEXT') {
    getStorage().remove(CONTEXT_KEYS);
    sendResponse({ status: 'cleared' });
    return true;
  }

  if (message.type === 'INLINE_ANALYZE') {
    const text = message.text;
    if (!text || text.length < BAYAN.MIN_TEXT_LENGTH) {
      sendResponse({ error: 'Text too short' });
      return true;
    }
    if (text.length > BAYAN.MAX_TEXT_LENGTH) {
      sendResponse({ error: 'Text too long' });
      return true;
    }

    // Cache hit → zero network
    const cached = cacheGet(text);
    if (cached) {
      sendResponse({ data: cached, cached: true });
      return true;
    }

    // Network call with retry
    analyzeWithRetry(text)
      .then((data) => {
        if (data) cacheSet(text, data);
        sendResponse({ data: data || null });
      })
      .catch((err) => {
        console.warn('[Bayan BG] Analysis error:', err.message);
        sendResponse({ error: err.message });
      });

    return true;
  }

  if (message.type === 'INLINE_AUTOCOMPLETE') {
    const context = message.text || '';
    if (!context || context.trim().length < 3) {
      sendResponse({ suggestions: [] });
      return true;
    }

    fetchAutocomplete(context)
      .then((data) => sendResponse({ suggestions: (data && data.suggestions) || [] }))
      .catch((err) => {
        console.warn('[Bayan BG] Autocomplete error:', err.message);
        sendResponse({ suggestions: [] });
      });

    return true;
  }

  if (message.type === 'OPEN_SIDEPANEL') {
    const storage = getStorage();
    storage.set({
      contextAction: ACTIONS.CORRECT,
      contextText: message.text || '',
      contextTimestamp: Date.now(),
    });
    if (chrome.sidePanel && sender.tab) {
      chrome.sidePanel.open({ windowId: sender.tab.windowId }).catch(() => {
        chrome.tabs.create({ url: chrome.runtime.getURL(SIDE_PANEL_PATH) });
      });
    }
    sendResponse({ status: 'ok' });
    return true;
  }

  if (message.type === 'WRITE_BACK_TO_PAGE') {
    // Forward to the active tab's content script, which owns page DOM access.
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab) { sendResponse({ ok: false }); return; }
      chrome.tabs.sendMessage(tab.id, {
        type: 'BAYAN_WRITE_BACK',
        text: message.text,
        mode: message.mode || 'replaceAll',
        source: message.source,
        find: message.find || '',
      }, (resp) => sendResponse(resp || { ok: false }));
    });
    return true; // async
  }

  return false;
});

// ══════════════════════════════════════════════════════════
// Network: fetch with timeout + 1 retry
// ══════════════════════════════════════════════════════════

async function analyzeWithRetry(text, attempt = 0) {
  try {
    return await fetchWithTimeout(text);
  } catch (err) {
    if (attempt < BAYAN.MAX_RETRIES) {
      return analyzeWithRetry(text, attempt + 1);
    }
    throw err;
  }
}

async function fetchWithTimeout(text) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BAYAN.API_TIMEOUT_MS);

  try {
    const res = await fetch(`${BAYAN.API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timeout);
  }
}

// ══════════════════════════════════════════════════════════
// Network: autocomplete (no retry — best-effort, short timeout)
// ══════════════════════════════════════════════════════════

async function fetchAutocomplete(context) {
  const controller = new AbortController();
  // Autocomplete must feel instant — cap well below the analyze timeout.
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(`${BAYAN.API_BASE}/api/autocomplete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context, n: 1 }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timeout);
  }
}
