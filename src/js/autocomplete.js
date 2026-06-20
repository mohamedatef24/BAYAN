/**
 * AutoComplete Module — Ghost Text + Dropdown for Arabic autocomplete.
 *
 * COMPLETELY INDEPENDENT from the correction pipeline.
 * It only talks to: /api/autocomplete (its own endpoint)
 */

(function () {
  'use strict';

  // ─── Configuration ───────────────────────────────────────────────
  const DEBOUNCE_MS = 400;
  const MIN_CONTEXT_LEN = 3;
  const MAX_SUGGESTIONS = 3;
  const CONTEXT_CHARS = 200;

  // ─── State ───────────────────────────────────────────────────────
  let ghostEl = null;
  let dropdownEl = null;
  let selectedIndex = -1;
  let currentSuggestions = [];
  let debounceTimer = null;
  let isComposing = false;
  let editorEl = null;
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
    console.log('[AutoComplete] Initialized');
  }

  // ─── Ghost Text Element ──────────────────────────────────────────
  function createGhostElement() {
    ghostEl = document.createElement('div');
    ghostEl.id = 'autocomplete-ghost';
    ghostEl.setAttribute('aria-hidden', 'true');
    var editorParent = editorEl.parentElement;
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

    // Focus lost → dismiss (with delay for dropdown clicks)
    editorEl.addEventListener('blur', function () {
      setTimeout(function () {
        if (document.activeElement !== editorEl) dismiss();
      }, 200);
    });
  }

  // ─── Input Handler ───────────────────────────────────────────────
  function onInput() {
    if (isComposing) return;
    clearTimeout(debounceTimer);
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
      case 'Enter':
        // If dropdown is visible, accept on Enter too
        if (isVisible() && selectedIndex >= 0) {
          e.preventDefault();
          e.stopPropagation();
          acceptSuggestion();
        }
        break;
    }
  }

  // ─── Fetch Suggestions ───────────────────────────────────────────
  async function fetchSuggestions() {
    var fetchId = ++_lastFetchId;

    var sel = window.getSelection();
    if (!sel || !sel.isCollapsed || !sel.rangeCount) {
      dismiss();
      return;
    }

    // CRITICAL: Only show autocomplete when cursor is at END of text
    // or at the end of a word (after a space or at document end)
    var textAfterCursor = getTextAfterCursor();
    if (textAfterCursor.length > 0 && textAfterCursor[0] !== ' ' && textAfterCursor[0] !== '\n') {
      // Cursor is in the MIDDLE of a word — don't show autocomplete
      dismiss();
      return;
    }

    // Get context (text before cursor)
    var context = getTextBeforeCursor(CONTEXT_CHARS);
    if (!context || context.trim().length < MIN_CONTEXT_LEN) {
      dismiss();
      return;
    }

    // Must end with a word (not just spaces)
    var trimmed = context.trimEnd();
    if (!trimmed || trimmed.length < MIN_CONTEXT_LEN) {
      dismiss();
      return;
    }

    try {
      var resp = await fetch('/api/autocomplete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: trimmed, n: MAX_SUGGESTIONS })
      });

      if (fetchId !== _lastFetchId) return;
      if (!resp.ok) { dismiss(); return; }

      var data = await resp.json();
      if (fetchId !== _lastFetchId) return;

      if (data.status !== 'success' || !data.suggestions || !data.suggestions.length) {
        dismiss();
        return;
      }

      console.log('[AutoComplete] Suggestions for last word:', data.suggestions);
      showSuggestions(data.suggestions);

    } catch (err) {
      console.warn('[AutoComplete] Fetch error:', err);
      if (fetchId === _lastFetchId) dismiss();
    }
  }

  // ─── Get Text Before Cursor ──────────────────────────────────────
  function getTextBeforeCursor(maxChars) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return '';

    try {
      var range = sel.getRangeAt(0);
      var preRange = document.createRange();
      preRange.selectNodeContents(editorEl);
      preRange.setEnd(range.startContainer, range.startOffset);
      var text = preRange.toString();
      preRange.detach();
      if (text.length <= maxChars) return text;
      return text.slice(-maxChars);
    } catch (e) {
      return '';
    }
  }

  // ─── Get Text After Cursor ───────────────────────────────────────
  function getTextAfterCursor() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return '';

    try {
      var range = sel.getRangeAt(0);
      var postRange = document.createRange();
      postRange.selectNodeContents(editorEl);
      postRange.setStart(range.endContainer, range.endOffset);
      var text = postRange.toString();
      postRange.detach();
      return text;
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

    // Position and show dropdown BELOW the caret, aligned to caret position
    positionDropdown();
    dropdownEl.style.display = 'block';

    // Show ghost text inline
    showGhost(suggestions[0]);
  }

  // ─── Ghost Text ──────────────────────────────────────────────────
  function showGhost(text) {
    if (!ghostEl || !text) return;

    var caretPos = getCaretCoordinates();
    if (!caretPos) { hideGhost(); return; }

    ghostEl.textContent = text;
    ghostEl.style.display = 'block';

    var parentRect = editorEl.parentElement.getBoundingClientRect();

    // Position ghost at caret — for RTL, text appears to the LEFT of caret
    ghostEl.style.top = (caretPos.top - parentRect.top) + 'px';
    // Use left positioning (place ghost just left of the caret in RTL)
    ghostEl.style.left = 'auto';
    ghostEl.style.right = (parentRect.right - caretPos.right + 2) + 'px';
  }

  function hideGhost() {
    if (ghostEl) {
      ghostEl.style.display = 'none';
      ghostEl.textContent = '';
    }
  }

  // ─── Dropdown Position ───────────────────────────────────────────
  function positionDropdown() {
    var caretPos = getCaretCoordinates();
    if (!caretPos) return;

    // Use fixed positioning relative to viewport
    dropdownEl.style.position = 'fixed';

    // Place BELOW the caret line
    var topPos = caretPos.bottom + 6;
    dropdownEl.style.top = topPos + 'px';

    // For RTL: align dropdown's RIGHT edge to the caret position
    // Use LEFT positioning to place the dropdown starting at the caret X
    var leftPos = caretPos.left - 160; // dropdown is ~160px wide, align right edge to caret
    if (leftPos < 10) leftPos = 10;
    dropdownEl.style.left = leftPos + 'px';
    dropdownEl.style.right = 'auto';

    // Check if dropdown goes off-screen bottom
    requestAnimationFrame(function () {
      var rect = dropdownEl.getBoundingClientRect();
      if (rect.bottom > window.innerHeight - 20) {
        dropdownEl.style.top = (caretPos.top - rect.height - 6) + 'px';
      }
    });
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
    if (selected) selected.scrollIntoView({ block: 'nearest' });
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

    // Determine if we need a space before the word
    var textBefore = getTextBeforeCursor(10);
    var needsSpaceBefore = textBefore.length > 0 && !textBefore.endsWith(' ') && !textBefore.endsWith('\n');

    // Build the text to insert: [optional space] + word + space
    var textToInsert = (needsSpaceBefore ? ' ' : '') + word + ' ';

    // Use execCommand for reliable insertion in contenteditable
    // This preserves undo history and handles cursor position correctly
    document.execCommand('insertText', false, textToInsert);

    dismiss();
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
   */
  function getCaretCoordinates() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;

    try {
      var range = sel.getRangeAt(0).cloneRange();
      range.collapse(true);

      // Try getClientRects first
      var rects = range.getClientRects();
      if (rects.length > 0) {
        var r = rects[0];
        return { top: r.top, left: r.left, bottom: r.bottom, right: r.right };
      }

      // Fallback: use getBoundingClientRect
      var bRect = range.getBoundingClientRect();
      if (bRect && (bRect.top !== 0 || bRect.left !== 0)) {
        return { top: bRect.top, left: bRect.left, bottom: bRect.bottom, right: bRect.right };
      }

      // Last resort: use editor position
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

  // ─── Initialize ──────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 100);
  }

})();
