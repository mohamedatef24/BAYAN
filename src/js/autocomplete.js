/**
 * AutoComplete Module — Ghost Text + Dropdown for Arabic autocomplete.
 *
 * COMPLETELY INDEPENDENT from the correction pipeline.
 * This module has ZERO interaction with:
 * - editor.js correction/highlight logic
 * - renderer.js span rendering
 * - ui.js suggestion sidebar
 * - /api/analyze
 *
 * It only talks to: /api/autocomplete (its own endpoint)
 */

(function () {
  'use strict';

  // ─── Configuration ───────────────────────────────────────────────
  const DEBOUNCE_MS = 400;
  const MIN_CONTEXT_LEN = 3;
  const MAX_SUGGESTIONS = 5;
  const CONTEXT_CHARS = 200;

  // ─── State ───────────────────────────────────────────────────────
  let ghostEl = null;
  let dropdownEl = null;
  let selectedIndex = -1;
  let currentSuggestions = [];
  let debounceTimer = null;
  let isComposing = false;
  let editorEl = null;

  // ─── Initialization ──────────────────────────────────────────────
  function init() {
    editorEl = document.getElementById('editor-container');
    if (!editorEl) {
      // Retry after DOM is ready
      setTimeout(init, 500);
      return;
    }

    createGhostElement();
    createDropdownElement();
    bindEvents();
    console.log('[AutoComplete] Initialized');
  }

  // ─── Ghost Text Element ──────────────────────────────────────────
  function createGhostElement() {
    ghostEl = document.createElement('div');
    ghostEl.id = 'autocomplete-ghost';
    ghostEl.setAttribute('aria-hidden', 'true');
    // Position relative to editor's parent
    const editorParent = editorEl.parentElement;
    if (editorParent) {
      editorParent.style.position = 'relative';
      editorParent.appendChild(ghostEl);
    }
  }

  // ─── Dropdown Element ────────────────────────────────────────────
  function createDropdownElement() {
    dropdownEl = document.createElement('div');
    dropdownEl.id = 'autocomplete-dropdown';
    dropdownEl.setAttribute('role', 'listbox');
    dropdownEl.setAttribute('aria-label', 'اقتراحات الإكمال التلقائي');
    dropdownEl.style.display = 'none';
    document.body.appendChild(dropdownEl);
  }

  // ─── Event Binding ───────────────────────────────────────────────
  function bindEvents() {
    // Typing → debounced autocomplete
    editorEl.addEventListener('input', onInput);

    // Composition events (IME)
    editorEl.addEventListener('compositionstart', () => { isComposing = true; });
    editorEl.addEventListener('compositionend', () => { isComposing = false; });

    // Keyboard: TAB accept, ESC dismiss, arrow navigation
    editorEl.addEventListener('keydown', onKeyDown);

    // Cursor movement / selection change → dismiss
    document.addEventListener('selectionchange', onSelectionChange);

    // Click outside → dismiss
    document.addEventListener('mousedown', function (e) {
      if (dropdownEl && !dropdownEl.contains(e.target) && e.target !== editorEl) {
        dismiss();
      }
    });

    // Scroll → reposition
    editorEl.addEventListener('scroll', dismiss);

    // Window resize → dismiss
    window.addEventListener('resize', dismiss);
  }

  // ─── Input Handler ───────────────────────────────────────────────
  function onInput() {
    if (isComposing) return;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchSuggestions, DEBOUNCE_MS);
  }

  // ─── Selection Change → Dismiss ──────────────────────────────────
  function onSelectionChange() {
    const sel = window.getSelection();
    if (!sel || !sel.isCollapsed) {
      dismiss();
      return;
    }
    // If cursor moved (not from typing), dismiss
    // We rely on the debounce to re-trigger if user is still typing
  }

  // ─── Keyboard Handler ───────────────────────────────────────────
  function onKeyDown(e) {
    if (!isVisible()) return;

    switch (e.key) {
      case 'Tab':
        e.preventDefault();
        acceptSuggestion();
        break;

      case 'Escape':
        e.preventDefault();
        dismiss();
        break;

      case 'ArrowDown':
        e.preventDefault();
        navigateDropdown(1);
        break;

      case 'ArrowUp':
        e.preventDefault();
        navigateDropdown(-1);
        break;

      default:
        // Any other key → will trigger onInput → new debounce
        // Dismiss current ghost immediately for responsiveness
        hideGhost();
        break;
    }
  }

  // ─── Fetch Suggestions ───────────────────────────────────────────
  async function fetchSuggestions() {
    const sel = window.getSelection();
    if (!sel || !sel.isCollapsed || !sel.rangeCount) {
      dismiss();
      return;
    }

    // Check the editor has text
    const text = editorEl.innerText || editorEl.textContent || '';
    if (text.trim().length < MIN_CONTEXT_LEN) {
      dismiss();
      return;
    }

    // Extract context: text before cursor (last N chars)
    const context = getTextBeforeCursor(CONTEXT_CHARS);
    if (!context || context.trim().length < MIN_CONTEXT_LEN) {
      dismiss();
      return;
    }

    try {
      const resp = await fetch('/api/autocomplete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: context,
          n: MAX_SUGGESTIONS
        })
      });

      if (!resp.ok) {
        dismiss();
        return;
      }

      const data = await resp.json();
      if (data.status !== 'success' || !data.suggestions || !data.suggestions.length) {
        dismiss();
        return;
      }

      showSuggestions(data.suggestions);

    } catch (err) {
      console.warn('[AutoComplete] Fetch error:', err);
      dismiss();
    }
  }

  // ─── Get Text Before Cursor ──────────────────────────────────────
  function getTextBeforeCursor(maxChars) {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return '';

    try {
      const range = sel.getRangeAt(0);
      const preRange = document.createRange();
      preRange.selectNodeContents(editorEl);
      preRange.setEnd(range.startContainer, range.startOffset);
      const text = preRange.toString();
      preRange.detach();

      if (text.length <= maxChars) return text;
      return text.slice(-maxChars);
    } catch (e) {
      return '';
    }
  }

  // ─── Show Suggestions ────────────────────────────────────────────
  function showSuggestions(suggestions) {
    currentSuggestions = suggestions;
    selectedIndex = 0; // Pre-select first

    // Show ghost text (best suggestion)
    showGhost(suggestions[0]);

    // Build dropdown
    dropdownEl.innerHTML = '';
    suggestions.forEach(function (word, idx) {
      const item = document.createElement('div');
      item.className = 'ac-dropdown-item' + (idx === 0 ? ' ac-selected' : '');
      item.setAttribute('role', 'option');
      item.textContent = word;
      item.addEventListener('mousedown', function (e) {
        e.preventDefault();
        selectedIndex = idx;
        acceptSuggestion();
      });
      item.addEventListener('mouseenter', function () {
        selectedIndex = idx;
        updateDropdownSelection();
      });
      dropdownEl.appendChild(item);
    });

    // Position dropdown near caret
    positionDropdown();
    dropdownEl.style.display = 'block';
  }

  // ─── Ghost Text ──────────────────────────────────────────────────
  function showGhost(text) {
    if (!ghostEl || !text) return;

    // Get caret position relative to editor
    const caretPos = getCaretCoordinates();
    if (!caretPos) {
      hideGhost();
      return;
    }

    ghostEl.textContent = text;
    ghostEl.style.display = 'block';

    // Position ghost at caret
    const editorRect = editorEl.getBoundingClientRect();
    const parentRect = editorEl.parentElement.getBoundingClientRect();

    // RTL: ghost appears to the LEFT of the caret
    ghostEl.style.top = (caretPos.top - parentRect.top) + 'px';
    ghostEl.style.right = (parentRect.right - caretPos.left + 4) + 'px';
    ghostEl.style.left = 'auto';
  }

  function hideGhost() {
    if (ghostEl) {
      ghostEl.style.display = 'none';
      ghostEl.textContent = '';
    }
  }

  // ─── Dropdown Position ───────────────────────────────────────────
  function positionDropdown() {
    const caretPos = getCaretCoordinates();
    if (!caretPos) return;

    const lineHeight = parseInt(getComputedStyle(editorEl).lineHeight) || 24;

    // Position below caret
    dropdownEl.style.position = 'fixed';
    dropdownEl.style.top = (caretPos.bottom + 4) + 'px';

    // RTL: align to the right of caret
    dropdownEl.style.right = (window.innerWidth - caretPos.left) + 'px';
    dropdownEl.style.left = 'auto';

    // Ensure dropdown doesn't go off-screen
    const rect = dropdownEl.getBoundingClientRect();
    if (rect.bottom > window.innerHeight - 20) {
      // Show above caret instead
      dropdownEl.style.top = (caretPos.top - rect.height - 4) + 'px';
    }
  }

  // ─── Dropdown Navigation ─────────────────────────────────────────
  function navigateDropdown(direction) {
    if (!currentSuggestions.length) return;

    selectedIndex += direction;
    if (selectedIndex < 0) selectedIndex = currentSuggestions.length - 1;
    if (selectedIndex >= currentSuggestions.length) selectedIndex = 0;

    updateDropdownSelection();
    showGhost(currentSuggestions[selectedIndex]);
  }

  function updateDropdownSelection() {
    const items = dropdownEl.querySelectorAll('.ac-dropdown-item');
    items.forEach(function (item, idx) {
      item.classList.toggle('ac-selected', idx === selectedIndex);
    });

    // Scroll selected item into view
    const selected = dropdownEl.querySelector('.ac-selected');
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' });
    }
  }

  // ─── Accept Suggestion ───────────────────────────────────────────
  function acceptSuggestion() {
    if (selectedIndex < 0 || selectedIndex >= currentSuggestions.length) {
      dismiss();
      return;
    }

    const word = currentSuggestions[selectedIndex];

    // Insert the word at cursor position
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) {
      dismiss();
      return;
    }

    // Insert with a space before the word
    const textToInsert = word + ' ';
    const range = sel.getRangeAt(0);
    range.deleteContents();
    const textNode = document.createTextNode(textToInsert);
    range.insertNode(textNode);

    // Move caret to end of inserted text
    range.setStartAfter(textNode);
    range.setEndAfter(textNode);
    sel.removeAllRanges();
    sel.addRange(range);

    dismiss();

    // Trigger input event so the editor knows text changed
    editorEl.dispatchEvent(new Event('input', { bubbles: true }));
  }

  // ─── Dismiss ─────────────────────────────────────────────────────
  function dismiss() {
    hideGhost();
    currentSuggestions = [];
    selectedIndex = -1;
    if (dropdownEl) {
      dropdownEl.style.display = 'none';
      dropdownEl.innerHTML = '';
    }
  }

  // ─── Helpers ─────────────────────────────────────────────────────
  function isVisible() {
    return dropdownEl && dropdownEl.style.display !== 'none';
  }

  function getCaretCoordinates() {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;

    try {
      const range = sel.getRangeAt(0).cloneRange();
      range.collapse(true);

      // Use a zero-width space to get coordinates
      const span = document.createElement('span');
      span.textContent = '\u200B';
      range.insertNode(span);

      const rect = span.getBoundingClientRect();
      const coords = {
        top: rect.top,
        left: rect.left,
        bottom: rect.bottom,
        right: rect.right
      };

      // Clean up
      span.parentNode.removeChild(span);

      // Restore selection
      sel.removeAllRanges();
      sel.addRange(range);

      return coords;
    } catch (e) {
      return null;
    }
  }

  // ─── Initialize on DOM ready ─────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
