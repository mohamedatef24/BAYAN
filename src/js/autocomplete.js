/**
 * autocomplete.js — Arabic Autocomplete UI for Bayan Editor
 *
 * Features:
 *  - Fires 300ms after user stops typing (debounced)
 *  - Calls /api/autocomplete with current editor text
 *  - Shows a floating RTL dropdown near cursor with up to 5 suggestions
 *  - Keyboard: Tab / ↑↓ to navigate, Enter to accept, Escape to dismiss
 *  - Click to accept any suggestion
 *  - Hides on blur, click-outside, or after acceptance
 *  - Inserts accepted suggestion as the completion of the last partial word
 */

(function () {
  'use strict';

  // ── Configuration ──────────────────────────────────────────────────────────
  const AC_DEBOUNCE_MS = 300;
  const AC_MAX_SUGGESTIONS = 5;
  const AC_MIN_WORD_LENGTH = 1; // minimum partial word length to trigger

  // ── State ──────────────────────────────────────────────────────────────────
  let _acTimeout = null;
  let _acAbortController = null;
  let _acVisible = false;
  let _acSuggestions = [];
  let _acActiveIndex = -1;
  let _acPartialWord = '';
  let _acEnabled = true;

  // ── DOM references ─────────────────────────────────────────────────────────
  function getDropdown() {
    return document.getElementById('autocomplete-dropdown');
  }

  function getEditor() {
    return typeof getEditorElement === 'function'
      ? getEditorElement()
      : document.getElementById('editor');
  }

  // ── Arabic text helpers ────────────────────────────────────────────────────

  /**
   * Returns true if the character is an Arabic letter/diacritic.
   */
  function isArabicChar(ch) {
    const code = ch.charCodeAt(0);
    return (code >= 0x0600 && code <= 0x06FF) ||
           (code >= 0xFB50 && code <= 0xFDFF) ||
           (code >= 0xFE70 && code <= 0xFEFF);
  }

  /**
   * Extract the last partial word from text (Arabic chars at the tail).
   * Returns '' if the text ends with a space or non-Arabic character.
   */
  function extractLastPartialWord(text) {
    if (!text) return '';
    let i = text.length - 1;
    while (i >= 0 && isArabicChar(text[i])) {
      i--;
    }
    const partial = text.slice(i + 1);
    // Only trigger if last char is Arabic (i.e. user is mid-word)
    if (!partial || !isArabicChar(partial[partial.length - 1])) {
      return '';
    }
    return partial;
  }

  /**
   * Get the caret (cursor) bounding rect inside the editor.
   * Used to position the dropdown below the cursor.
   */
  function getCaretRect() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return null;
    const range = sel.getRangeAt(0).cloneRange();
    range.collapse(true);
    const rect = range.getBoundingClientRect();
    // getBoundingClientRect can return zero-sized rect for collapsed ranges in some browsers
    if (rect.width === 0 && rect.height === 0) {
      // Fallback: use a temporary span
      const span = document.createElement('span');
      span.appendChild(document.createTextNode('\u200B')); // zero-width space
      range.insertNode(span);
      const fallbackRect = span.getBoundingClientRect();
      span.parentNode.removeChild(span);
      return fallbackRect;
    }
    return rect;
  }

  // ── Dropdown rendering ─────────────────────────────────────────────────────

  function renderDropdown(suggestions, partial) {
    const dropdown = getDropdown();
    if (!dropdown) return;

    if (!suggestions || suggestions.length === 0) {
      hideDropdown();
      return;
    }

    _acSuggestions = suggestions;
    _acActiveIndex = -1;

    // Build inner HTML
    let html = '';
    suggestions.forEach((word, i) => {
      // Highlight the matching prefix
      const partialLen = partial.length;
      const matchPart = word.slice(0, partialLen);
      const restPart = word.slice(partialLen);
      const displayHTML = partialLen > 0 && word.startsWith(partial)
        ? `<span class="ac-match">${escapeHtmlAC(matchPart)}</span>${escapeHtmlAC(restPart)}`
        : escapeHtmlAC(word);

      html += `<div class="ac-item" data-ac-index="${i}" role="option" aria-selected="false">
        <span class="ac-word">${displayHTML}</span>
        <span class="ac-tab-hint">Tab ↵</span>
      </div>`;
    });

    dropdown.innerHTML = html;

    // Bind click events
    dropdown.querySelectorAll('.ac-item').forEach(item => {
      item.addEventListener('mousedown', (e) => {
        e.preventDefault(); // prevent blur on editor
        const idx = parseInt(item.dataset.acIndex, 10);
        acceptSuggestion(idx);
      });
      item.addEventListener('mouseover', () => {
        const idx = parseInt(item.dataset.acIndex, 10);
        setActiveItem(idx);
      });
    });

    // Position dropdown near cursor
    positionDropdown(dropdown);
    dropdown.classList.add('ac-visible');
    dropdown.setAttribute('aria-hidden', 'false');
    _acVisible = true;
  }

  function positionDropdown(dropdown) {
    const rect = getCaretRect();
    if (!rect) return;

    const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;

    let top = rect.bottom + scrollY + 4;
    let left = rect.left + scrollX;

    // Clamp to viewport
    const dropW = 260;
    const vpW = window.innerWidth;
    if (left + dropW > vpW - 8) {
      left = vpW - dropW - 8;
    }
    if (left < 8) left = 8;

    // If dropdown would go below viewport, show above cursor
    const dropH = Math.min(_acSuggestions.length * 44 + 16, 260);
    if (top + dropH > window.innerHeight + scrollY - 8) {
      top = rect.top + scrollY - dropH - 4;
    }

    dropdown.style.top = `${top}px`;
    dropdown.style.left = `${left}px`;
  }

  function hideDropdown() {
    const dropdown = getDropdown();
    if (dropdown) {
      dropdown.classList.remove('ac-visible');
      dropdown.setAttribute('aria-hidden', 'true');
      dropdown.innerHTML = '';
    }
    _acVisible = false;
    _acSuggestions = [];
    _acActiveIndex = -1;
    _acPartialWord = '';
  }

  function setActiveItem(index) {
    const dropdown = getDropdown();
    if (!dropdown) return;
    const items = dropdown.querySelectorAll('.ac-item');
    items.forEach((item, i) => {
      item.classList.toggle('ac-item--active', i === index);
      item.setAttribute('aria-selected', i === index ? 'true' : 'false');
    });
    _acActiveIndex = index;
  }

  // ── Suggestion acceptance ──────────────────────────────────────────────────

  function acceptSuggestion(index) {
    if (index < 0 || index >= _acSuggestions.length) return;
    const word = _acSuggestions[index];
    if (!word) return;

    insertCompletion(word);
    hideDropdown();
  }

  /**
   * Insert the selected word as a completion of the partial word already typed.
   * Removes the partial word already typed and inserts the full suggestion.
   */
  function insertCompletion(fullWord) {
    const editor = getEditor();
    if (!editor) return;

    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;

    const range = sel.getRangeAt(0);

    // We need to delete the partial word that was already typed
    // and replace it with the full suggestion word.
    // Strategy: collapse range to caret, then extend backwards by _acPartialWord.length
    const partialLen = _acPartialWord.length;

    if (partialLen > 0) {
      // Extend range backwards by partialLen characters
      try {
        range.setStart(range.startContainer, Math.max(0, range.startOffset - partialLen));
      } catch (e) {
        // If we can't extend backward (cross-node), just insert at caret
      }
    }

    range.deleteContents();

    // Insert the full word + a trailing space
    const textNode = document.createTextNode(fullWord + ' ');
    range.insertNode(textNode);

    // Move cursor after inserted text
    const newRange = document.createRange();
    newRange.setStartAfter(textNode);
    newRange.collapse(true);
    sel.removeAllRanges();
    sel.addRange(newRange);

    // Notify editor of change
    if (typeof updateEditorStats === 'function') updateEditorStats();
    if (typeof updatePlaceholder === 'function') updatePlaceholder();
    if (typeof analyzeTextDelayed === 'function') analyzeTextDelayed();

    // Save draft
    try {
      localStorage.setItem('bayan_editor_draft', editor.innerHTML);
    } catch (e) {}
  }

  // ── API call ───────────────────────────────────────────────────────────────

  async function fetchSuggestions(text) {
    // Abort any in-flight request
    if (_acAbortController) {
      _acAbortController.abort();
    }
    _acAbortController = new AbortController();

    try {
      const response = await fetch('/api/autocomplete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, n: AC_MAX_SUGGESTIONS }),
        signal: _acAbortController.signal
      });

      const data = await response.json();
      return (data && Array.isArray(data.suggestions)) ? data.suggestions : [];
    } catch (err) {
      if (err.name === 'AbortError') return null; // silently cancelled
      console.warn('[Autocomplete] API call failed:', err.message);
      return [];
    }
  }

  // ── Trigger logic ──────────────────────────────────────────────────────────

  function triggerAutocomplete() {
    clearTimeout(_acTimeout);
    _acTimeout = setTimeout(async () => {
      if (!_acEnabled) return;

      const editor = getEditor();
      if (!editor || document.activeElement !== editor) return;

      // Get current text
      const text = typeof getEditorText === 'function'
        ? getEditorText()
        : editor.innerText || editor.textContent || '';

      if (!text || !text.trim()) {
        hideDropdown();
        return;
      }

      // Extract the last partial Arabic word
      const partial = extractLastPartialWord(text);
      if (!partial || partial.length < AC_MIN_WORD_LENGTH) {
        hideDropdown();
        return;
      }

      _acPartialWord = partial;

      // Fetch suggestions
      const suggestions = await fetchSuggestions(text);
      if (suggestions === null) return; // aborted

      // Filter out exact matches (user already typed the full word)
      const filtered = (suggestions || []).filter(s => s !== partial);

      if (filtered.length === 0) {
        hideDropdown();
        return;
      }

      renderDropdown(filtered, partial);
    }, AC_DEBOUNCE_MS);
  }

  // ── Keyboard navigation ────────────────────────────────────────────────────

  function handleKeyDown(e) {
    if (!_acVisible) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveItem(Math.min(_acActiveIndex + 1, _acSuggestions.length - 1));
        break;

      case 'ArrowUp':
        e.preventDefault();
        setActiveItem(Math.max(_acActiveIndex - 1, 0));
        break;

      case 'Tab':
        e.preventDefault();
        if (_acActiveIndex >= 0) {
          acceptSuggestion(_acActiveIndex);
        } else if (_acSuggestions.length > 0) {
          acceptSuggestion(0); // Tab always accepts first suggestion
        }
        break;

      case 'Enter':
        if (_acActiveIndex >= 0) {
          e.preventDefault();
          acceptSuggestion(_acActiveIndex);
        }
        // If no item selected, let Enter work normally (new line)
        break;

      case 'Escape':
        e.stopPropagation();
        hideDropdown();
        break;

      default:
        break;
    }
  }

  // ── HTML escaping helper ───────────────────────────────────────────────────

  function escapeHtmlAC(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ── Initialization ─────────────────────────────────────────────────────────

  function initAutocomplete() {
    const editor = getEditor();
    if (!editor) {
      // Editor not ready yet — retry after short delay
      setTimeout(initAutocomplete, 200);
      return;
    }

    // Trigger on input
    editor.addEventListener('input', () => {
      triggerAutocomplete();
    });

    // Keyboard navigation (capture phase so we intercept Tab before browser)
    editor.addEventListener('keydown', handleKeyDown, true);

    // Hide dropdown when clicking outside
    document.addEventListener('mousedown', (e) => {
      const dropdown = getDropdown();
      if (_acVisible && dropdown && !dropdown.contains(e.target) && e.target !== editor) {
        hideDropdown();
      }
    });

    // Hide on editor blur
    editor.addEventListener('blur', () => {
      // Small delay so mousedown on dropdown item fires first
      setTimeout(() => {
        if (!document.activeElement || document.activeElement !== editor) {
          hideDropdown();
        }
      }, 150);
    });

    console.log('[Autocomplete] Initialized successfully');
  }

  // ── Public API (for testing / manual control) ──────────────────────────────
  window.bayanAutocomplete = {
    init: initAutocomplete,
    hide: hideDropdown,
    enable: () => { _acEnabled = true; },
    disable: () => { _acEnabled = false; hideDropdown(); },
    isVisible: () => _acVisible,
  };

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutocomplete);
  } else {
    // DOM already loaded — wait for editor to be initialized
    setTimeout(initAutocomplete, 500);
  }

})();
