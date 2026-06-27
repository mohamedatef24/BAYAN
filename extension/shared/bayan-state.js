/**
 * Bayan Chrome Extension — Unified State Manager
 *
 * Phase 7: Production Hardening
 *
 * Single source of truth for runtime state across the inline engine.
 * Loaded as a content script BEFORE content-inline.js.
 *
 * Responsibilities:
 *   - Track active field reference (WeakRef for GC safety)
 *   - Store last analyzed text + response
 *   - Track active mode
 *   - Provide clean teardown
 */

// eslint-disable-next-line no-unused-vars
const BayanState = (() => {
  'use strict';

  /** @type {WeakRef<HTMLElement>|null} */
  let _fieldRef = null;
  let _lastText = '';
  let _lastHash = '';
  let _lastResponse = null;
  /** @type {Array} */
  let _suggestions = [];
  let _mode = 'idle'; // idle | inline | sidepanel | contextmenu
  let _paused = false;
  let _pauseReason = '';

  /**
   * Simple FNV-1a hash for text deduplication.
   * 32-bit, fast, zero dependencies.
   * @param {string} str
   * @returns {string}
   */
  function hash(str) {
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    return (h >>> 0).toString(36);
  }

  return {
    // ── Field management ──
    /** @param {HTMLElement} field */
    setField(field) {
      _fieldRef = field ? new WeakRef(field) : null;
    },

    /** @returns {HTMLElement|null} */
    getField() {
      return _fieldRef?.deref() ?? null;
    },

    hasField() {
      return !!(_fieldRef?.deref());
    },

    // ── Text + hash ──
    setLastText(text) {
      _lastText = text;
      _lastHash = hash(text);
    },
    getLastText() { return _lastText; },
    getLastHash() { return _lastHash; },

    /**
     * Check if given text is identical to last analyzed text.
     * Uses hash comparison (O(1)) instead of string equality (O(n)).
     */
    isDuplicate(text) {
      return hash(text) === _lastHash && text === _lastText;
    },

    // ── Response cache ──
    setLastResponse(data) { _lastResponse = data; },
    getLastResponse() { return _lastResponse; },

    // ── Suggestions ──
    setSuggestions(suggestions) { _suggestions = suggestions || []; },
    getSuggestions() { return _suggestions; },

    // ── Mode ──
    setMode(mode) { _mode = mode; },
    getMode() { return _mode; },

    // ── Pause state ──
    pause(reason) {
      _paused = true;
      _pauseReason = reason || 'unknown';
    },
    resume() {
      _paused = false;
      _pauseReason = '';
    },
    isPaused() { return _paused; },
    getPauseReason() { return _pauseReason; },

    // ── Clean teardown ──
    reset() {
      _fieldRef = null;
      _lastText = '';
      _lastHash = '';
      _lastResponse = null;
      _suggestions = [];
      _mode = 'idle';
      _paused = false;
      _pauseReason = '';
    },

    // ── Debug ──
    toJSON() {
      return {
        hasField: !!(_fieldRef?.deref()),
        textLength: _lastText.length,
        hash: _lastHash,
        suggestions: _suggestions.length,
        mode: _mode,
        paused: _paused,
        pauseReason: _pauseReason,
      };
    },
  };
})();
