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
  let _suppressSelectionChange = false;
  let _lastFetchId = 0;

  // ─── Initialization ──────────────────────────────────────────────
  function init() {
    editorEl = document.getElementById('editor-container');
    if (!editorEl) {
      setTimeout(init, 500);
      return;
    }

    createGhostElement();
    createDropdownElement();
    bindEvents();
    console.log('[AutoComplete] Initialized — editor element found');
  }

  // ─── Ghost Text Element ──────────────────────────────────────────
  function createGhostElement() {
    ghostEl = document.createElement('div');
    ghostEl.id = 'autocomplete-ghost';
    ghostEl.setAttribute('aria-hidden', 'true');
    // Append to editor's parent for relative positioning
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
    editorEl.addEventListener('input', onInput);
    editorEl.addEventListener('compositionstart', function () { isComposing = true; });
    editorEl.addEventListener('compositionend', function () { isComposing = false; });
    editorEl.addEventListener('keydown', onKeyDown);

    // Click outside → dismiss
    document.addEventListener('mousedown', function (e) {
      if (dropdownEl && !dropdownEl.contains(e.target) && e.target !== editorEl) {
        dismiss();
      }
    });

    // Scroll/resize → dismiss
    editorEl.addEventListener('scroll', dismiss);
    window.addEventListener('resize', dismiss);

    // Focus lost → dismiss
    editorEl.addEventListener('blur', function () {
      // Small delay to allow dropdown click to register
      setTimeout(function () {
        if (document.activeElement !== editorEl) {
          dismiss();
        }
      }, 200);
    });
  }

  // ─── Input Handler ───────────────────────────────────────────────
  function onInput() {
    if (isComposing) return;

    // Clear previous debounce
    clearTimeout(debounceTimer);

    // Hide ghost immediately while typing (but keep dropdown state for debounce)
    hideGhost();

    debounceTimer = setTimeout(fetchSuggestions, DEBOUNCE_MS);
  }

  // ─── Keyboard Handler ───────────────────────────────────────────
  function onKeyDown(e) {
    if (!isVisible()) return;

    switch (e.key) {
      case 'Tab':
        e.preventDefault();
        e.stopPropagation();
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

      // Don't dismiss on other keys — let onInput handle the debounce cycle
    }
  }

  // ─── Fetch Suggestions ───────────────────────────────────────────
  async function fetchSuggestions() {
    const fetchId = ++_lastFetchId;

    const sel = window.getSelection();
    if (!sel || !sel.isCollapsed || !sel.rangeCount) {
      dismiss();
      return;
    }

    // Check editor has enough text
    const fullText = editorEl.innerText || editorEl.textContent || '';
    if (fullText.trim().length < MIN_CONTEXT_LEN) {
      dismiss();
      return;
    }

    // Extract context before cursor
    const context = getTextBeforeCursor(CONTEXT_CHARS);
    if (!context || context.trim().length < MIN_CONTEXT_LEN) {
      dismiss();
      return;
    }

    try {
      const resp = await fetch('/api/autocomplete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: context, n: MAX_SUGGESTIONS })
      });

      // Stale response check — if another fetch started, ignore this one
      if (fetchId !== _lastFetchId) return;

      if (!resp.ok) {
        dismiss();
        return;
      }

      const data = await resp.json();
      if (fetchId !== _lastFetchId) return;

      if (data.status !== 'success' || !data.suggestions || !data.suggestions.length) {
        dismiss();
        return;
      }

      console.log('[AutoComplete] Showing suggestions:', data.suggestions);
      showSuggestions(data.suggestions);

    } catch (err) {
      console.warn('[AutoComplete] Fetch error:', err);
      if (fetchId === _lastFetchId) dismiss();
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
    selectedIndex = 0;

    // Build dropdown items
    dropdownEl.innerHTML = '';
    suggestions.forEach(function (word, idx) {
      var item = document.createElement('div');
      item.className = 'ac-dropdown-item' + (idx === 0 ? ' ac-selected' : '');
      item.setAttribute('role', 'option');
      item.textContent = word;
      item.addEventListener('mousedown', function (e) {
        e.preventDefault();
        e.stopPropagation();
        selectedIndex = idx;
        acceptSuggestion();
      });
      item.addEventListener('mouseenter', function () {
        selectedIndex = idx;
        updateDropdownSelection();
      });
      dropdownEl.appendChild(item);
    });

    // Position and show dropdown
    positionDropdown();
    dropdownEl.style.display = 'block';

    // Show ghost text
    showGhost(suggestions[0]);
  }

  // ─── Ghost Text ──────────────────────────────────────────────────
  function showGhost(text) {
    if (!ghostEl || !text) return;

    var caretPos = getCaretCoordinatesSimple();
    if (!caretPos) {
      hideGhost();
      return;
    }

    ghostEl.textContent = text;
    ghostEl.style.display = 'block';

    var parentRect = editorEl.parentElement.getBoundingClientRect();

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
    var caretPos = getCaretCoordinatesSimple();
    if (!caretPos) return;

    // Position below caret
    dropdownEl.style.position = 'fixed';
    dropdownEl.style.top = (caretPos.bottom + 6) + 'px';

    // RTL: align to the right of caret
    dropdownEl.style.right = (window.innerWidth - caretPos.left) + 'px';
    dropdownEl.style.left = 'auto';

    // Force layout to get actual dimensions
    var rect = dropdownEl.getBoundingClientRect();

    // If dropdown goes off-screen bottom, show above caret
    if (rect.bottom > window.innerHeight - 20) {
      dropdownEl.style.top = (caretPos.top - rect.height - 6) + 'px';
    }

    // If dropdown goes off-screen right (RTL), adjust
    if (rect.left < 10) {
      dropdownEl.style.right = 'auto';
      dropdownEl.style.left = '10px';
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
    var items = dropdownEl.querySelectorAll('.ac-dropdown-item');
    items.forEach(function (item, idx) {
      item.classList.toggle('ac-selected', idx === selectedIndex);
    });

    var selected = dropdownEl.querySelector('.ac-selected');
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

    var word = currentSuggestions[selectedIndex];

    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) {
      dismiss();
      return;
    }

    // Insert word + space at cursor
    var textToInsert = word + ' ';
    var range = sel.getRangeAt(0);
    range.deleteContents();
    var textNode = document.createTextNode(textToInsert);
    range.insertNode(textNode);

    // Move caret after inserted text
    range.setStartAfter(textNode);
    range.setEndAfter(textNode);
    sel.removeAllRanges();
    sel.addRange(range);

    dismiss();

    // Notify editor that content changed
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

  /**
   * Get caret coordinates using Range.getClientRects() — NO DOM mutation.
   * This avoids triggering input/selectionchange events that would dismiss
   * the dropdown immediately.
   */
  function getCaretCoordinatesSimple() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;

    try {
      var range = sel.getRangeAt(0).cloneRange();
      range.collapse(true);

      // Try getClientRects first (works when caret is inside a text node)
      var rects = range.getClientRects();
      if (rects.length > 0) {
        var r = rects[0];
        return { top: r.top, left: r.left, bottom: r.bottom, right: r.right };
      }

      // Fallback: use the range's bounding rect
      var bRect = range.getBoundingClientRect();
      if (bRect && bRect.top !== 0) {
        return { top: bRect.top, left: bRect.left, bottom: bRect.bottom, right: bRect.right };
      }

      // Last resort: use editor position + some offset
      var editorRect = editorEl.getBoundingClientRect();
      return {
        top: editorRect.top + 20,
        left: editorRect.right - 20,
        bottom: editorRect.top + 44,
        right: editorRect.right
      };
    } catch (e) {
      return null;
    }
  }

  // ─── Initialize on DOM ready ─────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // Script runs in <head>, editor might not exist yet
    // Wait for DOM to be fully ready
    setTimeout(init, 100);
  }

})();
