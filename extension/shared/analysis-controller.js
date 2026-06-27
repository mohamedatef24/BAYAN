/**
 * Bayan — Analysis Controller (Phase 7.1 Simplified)
 *
 * Responsibilities (ONLY):
 *   - Adaptive debounce (2-tier: normal / large text)
 *   - Stale request cancellation
 *   - Text validation
 *   - Message passing to background.js
 *
 * Does NOT own:
 *   - Caching (background.js)
 *   - Retry logic (background.js)
 *   - Timeout (background.js)
 *   - Network (background.js)
 *
 * Requires: BAYAN (shared/constants.js)
 */

// eslint-disable-next-line no-unused-vars
const BayanController = (() => {
  'use strict';

  // ── Debounce config ──
  const DEBOUNCE_NORMAL = 500;
  const DEBOUNCE_LARGE = 1000;
  const LARGE_TEXT_THRESHOLD = 2000;

  // ── State ──
  let _debounceTimer = null;
  let _inflight = false;

  // ── Protected site check ──
  const _isProtected = BAYAN.PROTECTED_HOSTS.includes(window.location.hostname);

  // ══════════════════════════════════════════════════════════
  // Text validation
  // ══════════════════════════════════════════════════════════

  function hasArabic(text) {
    if (!text || text.length < BAYAN.MIN_TEXT_LENGTH) return false;
    const arabicChars = (text.match(/[\u0600-\u06FF]/g) || []).length;
    return arabicChars >= BAYAN.MIN_ARABIC_CHARS;
  }

  function validateText(text) {
    if (!text) return { valid: false, reason: 'empty' };
    if (text.length < BAYAN.MIN_TEXT_LENGTH) return { valid: false, reason: 'too_short' };
    if (text.length > BAYAN.MAX_TEXT_LENGTH) return { valid: false, reason: 'too_long' };
    if (!hasArabic(text)) return { valid: false, reason: 'no_arabic' };
    return { valid: true };
  }

  // ══════════════════════════════════════════════════════════
  // Core: debounced analysis via background bridge
  // ══════════════════════════════════════════════════════════

  /**
   * Schedule a debounced analysis.
   * Background.js owns caching, retry, and timeout.
   *
   * @param {string} text
   * @param {function(Object|null): void} onResult
   * @param {function(): string} getCurrentText — staleness checker
   */
  function scheduleAnalysis(text, onResult, getCurrentText) {
    if (_debounceTimer) {
      clearTimeout(_debounceTimer);
      _debounceTimer = null;
    }

    if (!validateText(text).valid) {
      onResult(null);
      return;
    }

    const delay = text.length > LARGE_TEXT_THRESHOLD ? DEBOUNCE_LARGE : DEBOUNCE_NORMAL;

    _debounceTimer = setTimeout(() => {
      _debounceTimer = null;

      // Staleness check: text changed during debounce
      if (getCurrentText() !== text) return;

      executeAnalysis(text, onResult, getCurrentText);
    }, delay);
  }

  /**
   * Send analysis request to background.js.
   * No timeout, no retry, no cache — background handles all of that.
   */
  function executeAnalysis(text, onResult, getCurrentText) {
    _inflight = true;

    chrome.runtime.sendMessage({ type: 'INLINE_ANALYZE', text }, (response) => {
      _inflight = false;

      // Extension context invalidated (e.g., extension reloaded)
      if (chrome.runtime.lastError) {
        console.warn('[Bayan Controller]', chrome.runtime.lastError.message);
        onResult(null);
        return;
      }

      // Staleness check: text changed during fetch
      if (getCurrentText() !== text) return;

      if (!response || response.error) {
        onResult(null);
        return;
      }

      onResult(response.data);
    });
  }

  // ══════════════════════════════════════════════════════════
  // Cancellation
  // ══════════════════════════════════════════════════════════

  function cancelAll() {
    if (_debounceTimer) {
      clearTimeout(_debounceTimer);
      _debounceTimer = null;
    }
    _inflight = false;
  }

  function destroy() {
    cancelAll();
  }

  // ══════════════════════════════════════════════════════════
  // Public API
  // ══════════════════════════════════════════════════════════

  return {
    scheduleAnalysis,
    cancelAll,
    destroy,
    validateText,
    hasArabic,
    isProtectedSite() { return _isProtected; },
    isInFlight() { return _inflight; },
  };
})();
