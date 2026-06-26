// src/js/editor.js
// Editor management and state

let analyzeTimeout;
let analyzeAbortController = null;
let _lastInputTime = 0;
const ANALYZE_DEBOUNCE_MS = 1000;
const MAX_ANALYZE_LENGTH = 5000;

// Pipeline Hardening v3.3: Guard to prevent input events during suggestion apply
let _isApplyingSuggestion = false;

// ── Custom Undo/Redo Stack ──
const _undoStack = [];
const _redoStack = [];
const _MAX_UNDO = 50;

function pushUndoState() {
  const editor = getEditorElement();
  if (!editor) return;
  const html = editor.innerHTML;
  // Avoid duplicate consecutive entries
  if (_undoStack.length > 0 && _undoStack[_undoStack.length - 1] === html) return;
  _undoStack.push(html);
  if (_undoStack.length > _MAX_UNDO) _undoStack.shift();
  _redoStack.length = 0; // Clear redo on new action
}

function editorUndo() {
  const editor = getEditorElement();
  if (!editor || _undoStack.length === 0) return false;
  _redoStack.push(editor.innerHTML);
  editor.innerHTML = _undoStack.pop();
  updateEditorStats();
  updatePlaceholder();
  analyzeTextDelayed();
  return true;
}

function editorRedo() {
  const editor = getEditorElement();
  if (!editor || _redoStack.length === 0) return false;
  _undoStack.push(editor.innerHTML);
  editor.innerHTML = _redoStack.pop();
  updateEditorStats();
  updatePlaceholder();
  analyzeTextDelayed();
  return true;
}

// Dismissed words whitelist — words the user chose to keep as-is
const _dismissedWords = new Set(
  JSON.parse(localStorage.getItem('bayan_dismissed_words') || '[]')
);

function _saveDismissedWords() {
  try {
    localStorage.setItem('bayan_dismissed_words', JSON.stringify([..._dismissedWords]));
  } catch (e) {}
}

/**
 * Initialize the editor
 */
function initEditor() {
  const editor = getEditorElement();
  if (!editor) {
    console.warn('Editor element not found');
    return;
  }

  // Restore draft if no document was explicitly loaded yet
  try {
    const draft = localStorage.getItem('bayan_editor_draft');
    if (draft && !editor.innerHTML.trim()) {
      editor.innerHTML = draft;
      // Trigger analysis on load
      setTimeout(analyzeTextDelayed, 500);
    }
  } catch (e) {}

  // Debounced undo push — saves state after 500ms of no typing
  let _undoInputTimer = null;
  editor.addEventListener('input', () => {
    // Pipeline Hardening v3.3: Skip re-analysis when programmatically applying suggestions
    if (_isApplyingSuggestion) return;
    _lastInputTime = Date.now();
    updateEditorStats();
    updatePlaceholder();
    analyzeTextDelayed();
    // Push undo state after typing pauses
    clearTimeout(_undoInputTimer);
    _undoInputTimer = setTimeout(pushUndoState, 500);
    try {
      localStorage.setItem('bayan_editor_draft', editor.innerHTML);
    } catch (e) {}
  });

  // Strip formatting on paste — prevent rich HTML (colors, opacity, fonts)
  // from being carried over when pasting from chat, web pages, etc.
  editor.addEventListener('paste', (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    if (!text) return;

    // Insert plain text at cursor position
    const selection = window.getSelection();
    if (!selection.rangeCount) return;

    const range = selection.getRangeAt(0);
    range.deleteContents();

    // Split by newlines to preserve paragraph structure
    const lines = text.split(/\r?\n/);
    const fragment = document.createDocumentFragment();
    lines.forEach((line, i) => {
      if (i > 0) fragment.appendChild(document.createElement('br'));
      fragment.appendChild(document.createTextNode(line));
    });

    range.insertNode(fragment);

    // Move cursor to end of pasted content
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);

    // Trigger editor update
    updateEditorStats();
    updatePlaceholder();
    analyzeTextDelayed();
    try {
      localStorage.setItem('bayan_editor_draft', editor.innerHTML);
    } catch (e) {}
  });

  editor.addEventListener('click', (e) => {
    handleEditorClick(e);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideTooltip();
  });

  // Custom Undo/Redo — on editor only, capture phase to beat browser native undo
  // Uses e.code instead of e.key so shortcuts work with any keyboard language
  editor.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.code === 'KeyZ' && !e.shiftKey) {
      if (_undoStack.length > 0) {
        e.preventDefault();
        e.stopImmediatePropagation();
        editorUndo();
        return;
      }
    }
    if ((e.ctrlKey || e.metaKey) && (e.code === 'KeyY' || (e.code === 'KeyZ' && e.shiftKey))) {
      if (_redoStack.length > 0) {
        e.preventDefault();
        e.stopImmediatePropagation();
        editorRedo();
        return;
      }
    }
  }, true);

  document.addEventListener('click', (e) => {
    const popover = document.getElementById('editor-tooltip');
    if (popover && popover.classList.contains('show') &&
        !popover.contains(e.target) &&
        !e.target.classList.contains('spelling-error') &&
        !e.target.classList.contains('grammar-error') &&
        !e.target.classList.contains('punctuation-suggestion')) {
      hideTooltip();
    }
  });

  const applyAllBtn = document.getElementById('apply-all-btn');
  const applyAllSheet = document.getElementById('apply-all-sheet');
  if (applyAllBtn) applyAllBtn.addEventListener('click', applyAllSuggestions);
  if (applyAllSheet) applyAllSheet.addEventListener('click', applyAllSuggestions);

  updatePlaceholder();
}

function updateEditorStats() {
  const text = getEditorText();
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const wordCountEl = document.getElementById('word-count');
  if (wordCountEl) {
    wordCountEl.textContent = words.toLocaleString('ar-EG');
  }

  // Word count goal
  const goalEl = document.getElementById('word-goal-indicator');
  if (goalEl) {
    try {
      const goal = parseInt(localStorage.getItem('bayan_word_goal') || '0', 10);
      if (goal > 0) {
        const pct = Math.min(Math.round((words / goal) * 100), 100);
        goalEl.style.display = 'inline-block';
        goalEl.textContent = `${pct.toLocaleString('ar-EG')}% من ${goal.toLocaleString('ar-EG')}`;
        goalEl.classList.toggle('goal-reached', pct >= 100);
      } else {
        goalEl.style.display = 'none';
      }
    } catch(e) { goalEl.style.display = 'none'; }
  }

  // Item 4: Enhanced stats
  if (typeof updateEnhancedStats === 'function') {
    updateEnhancedStats();
  }
}

function updatePlaceholder() {
  const editor = getEditorElement();
  if (!editor) return;

  const text = (editor.textContent || '').trim();
  if (!text || text.length === 0) {
    editor.setAttribute('data-empty', 'true');
  } else {
    editor.removeAttribute('data-empty');
  }
}

function analyzeTextDelayed() {
  clearTimeout(analyzeTimeout);
  // Abort any in-flight request so it doesn't overwrite while user types
  if (analyzeAbortController) {
    analyzeAbortController.abort();
  }
  analyzeTimeout = setTimeout(() => {
    // Double-check user hasn't typed in the last DEBOUNCE period
    const timeSinceLastInput = Date.now() - _lastInputTime;
    if (timeSinceLastInput >= ANALYZE_DEBOUNCE_MS - 100) {
      analyzeText();
    }
  }, ANALYZE_DEBOUNCE_MS);
}

function findSuggestionById(id) {
  // Pipeline Hardening v3.3: UUID-based lookup instead of index
  const suggestions = window.currentSuggestions || [];
  return suggestions.find(s => s.id === id) || null;
}

function findSuggestionElement(id) {
  return document.querySelector(`[data-suggestion-id="${id}"]`);
}

async function analyzeText() {
  const text = getEditorText();
  updateEditorStats();
  updatePlaceholder();

  if (!text || text.trim().length === 0) {
    renderWithoutSuggestions(text);
    updateSuggestionCounts(0, 0, 0);
    updateWritingScore(0, 0, 0);
    updateSuggestionsList([]);
    window.currentSuggestions = [];
    updateAnalysisLimitBanner(false);
    return;
  }

  const isTruncated = text.length > MAX_ANALYZE_LENGTH;
  const textForApi = isTruncated ? text.substring(0, MAX_ANALYZE_LENGTH) : text;
  updateAnalysisLimitBanner(isTruncated);

  if (analyzeAbortController) {
    analyzeAbortController.abort();
  }
  analyzeAbortController = new AbortController();

  setAnalyzingState(true);

  try {
    const savedSelection = saveSelection();

    // Network delay indicator: show message if API takes > 10s
    const longerTimer = setTimeout(() => {
      if (typeof showToast === 'function') showToast('\u0627\u0644\u062a\u062d\u0644\u064a\u0644 \u064a\u0623\u062e\u0630 \u0648\u0642\u062a\u064b\u0627 \u0623\u0637\u0648\u0644...', 'warning');
    }, 10000);

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: textForApi }),
      signal: analyzeAbortController.signal
    });

    clearTimeout(longerTimer);

    if (!response.ok) {
      console.error('Analyze API error:', response.status);
      renderWithoutSuggestions(text);
      return;
    }

    const data = await response.json();

    if (data.status !== 'success' || !data.suggestions) {
      renderWithoutSuggestions(text);
      return;
    }

    // Filter out dismissed (whitelisted) words
    const rawSuggestions = sortSuggestions(data.suggestions || []);
    window.currentSuggestions = rawSuggestions.filter(
      s => !_dismissedWords.has(s.original)
    );

    // Use DOM overlay instead of innerHTML replacement to preserve formatting
    const editor = getEditorElement();
    overlaySuggestions(editor, window.currentSuggestions);

    if (savedSelection) {
      restoreSelection(savedSelection);
    }

    const spellingCount = window.currentSuggestions.filter((s) => s.type === 'spelling').length;
    const grammarCount = window.currentSuggestions.filter((s) => s.type === 'grammar').length;
    const punctuationCount = window.currentSuggestions.filter((s) => s.type === 'punctuation').length;

    updateSuggestionCounts(spellingCount, grammarCount, punctuationCount);
    updateWritingScore(spellingCount, grammarCount, punctuationCount);
    updateSuggestionsList(window.currentSuggestions);
  } catch (error) {
    if (error.name === 'AbortError') return;
    console.error('Analysis error:', error);
    renderWithoutSuggestions(text);
    if (typeof showToast === 'function') showToast('\u062a\u0639\u0630\u0651\u0631 \u0627\u0644\u062a\u062d\u0644\u064a\u0644 \u2014 \u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0627\u062a\u0635\u0627\u0644', 'error');
  } finally {
    setAnalyzingState(false);
  }
}

function renderWithoutSuggestions(text) {
  const editor = getEditorElement();
  if (!editor) return;
  // Just clear overlays, don't replace content (preserves formatting)
  clearOverlays(editor);
  updatePlaceholder();
}

function updateSuggestionCounts(spelling, grammar, punctuation) {
  const spellingEl = document.getElementById('spelling-count');
  const grammarEl = document.getElementById('grammar-count');
  const punctuationEl = document.getElementById('punctuation-count');

  if (spellingEl) spellingEl.textContent = spelling.toLocaleString('ar-EG');
  if (grammarEl) grammarEl.textContent = grammar.toLocaleString('ar-EG');
  if (punctuationEl) punctuationEl.textContent = punctuation.toLocaleString('ar-EG');
}

function handleEditorClick(e) {
  const target = e.target;
  if (target.classList.contains('spelling-error') ||
      target.classList.contains('grammar-error') ||
      target.classList.contains('punctuation-suggestion')) {
    showTooltip(target);
  }
}

function showTooltip(element) {
  const id = element.dataset.suggestionId;
  const suggestion = findSuggestionById(id);

  if (!suggestion) return;

  const tooltip = document.getElementById('editor-tooltip');
  if (!tooltip) return;

  const typeEl = document.getElementById('tooltip-type');
  const originalEl = document.getElementById('tooltip-original');
  const alternativesEl = document.getElementById('tooltip-alternatives');

  const typeMap = {
    spelling: { label: 'خطأ إملائي' },
    grammar: { label: 'خطأ نحوي' },
    punctuation: { label: 'علامات ترقيم' }
  };

  if (typeEl) {
    const typeInfo = typeMap[suggestion.type] || { label: suggestion.type };
    typeEl.innerHTML = typeInfo.label;
    typeEl.className = `popover-type popover-type--${suggestion.type}`;
  }

  if (originalEl) {
    originalEl.innerHTML = `<span class="popover-original-word" style="text-decoration:line-through; opacity:0.6;">${escapeHtml(suggestion.original)}</span> <span class="popover-arrow">←</span> <span class="popover-correction-word" style="color:var(--color-success); font-weight:600;">${escapeHtml(suggestion.correction)}</span>`;
  }

  // Render alternatives
  if (alternativesEl) {
    // Use shared helper (defined in ui.js, loaded before editor.js)
    const alts = (typeof resolveAlternatives === 'function')
      ? resolveAlternatives(suggestion)
      : (suggestion.alternatives && suggestion.alternatives.length > 0)
        ? suggestion.alternatives
        : [suggestion.correction, suggestion.original];
    let html = '';
    // Render corrections first (non-keep)
    alts.forEach((alt, i) => {
      const isKeep = alt === suggestion.original;
      if (isKeep) return; // render keep button last
      const isMain = i === 0;
      const btnClass = isMain ? 'popover-alt-btn popover-alt-main' : 'popover-alt-btn';
      html += `<button class="${btnClass}" data-alt-correction="${escapeHtml(alt)}" type="button">${isMain ? '✓ ' : ''}${escapeHtml(alt)}</button>`;
    });
    // No separate "keep" button — the "تجاهل" popover button handles dismissal
    alternativesEl.innerHTML = html;

    // Bind click events for alternatives
    alternativesEl.querySelectorAll('.popover-alt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const correctionText = btn.dataset.altCorrection;
        if (correctionText === suggestion.original) {
          dismissSuggestion(suggestion);
        } else {
          applyAlternativeCorrection(suggestion, correctionText);
        }
      });
    });
  }

  const rect = element.getBoundingClientRect();
  let top = rect.bottom + 10;
  let left = rect.left;

  if (left + 320 > window.innerWidth) {
    left = window.innerWidth - 330;
  }
  if (top + 150 > window.innerHeight) {
    top = rect.top - 150;
  }

  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${Math.max(8, left)}px`;
  tooltip.classList.add('show');

  window.currentApplySuggestion = suggestion;
  window.currentSuggestionElement = element;
  window.currentSuggestionId = id;
}

function hideTooltip() {
  const tooltip = document.getElementById('editor-tooltip');
  if (tooltip) {
    tooltip.classList.remove('show');
  }
  window.currentApplySuggestion = null;
  window.currentSuggestionElement = null;
}

function applySuggestionAtOffsets(suggestion) {
  _isApplyingSuggestion = true;
  try {
    pushUndoState(); // Save state before correction
    // Pipeline Hardening v3.3: UUID-based span lookup
    const suggestionId = suggestion.id;
    const errorSpan = suggestionId ? document.querySelector(`[data-suggestion-id="${suggestionId}"]`) : null;

    if (errorSpan) {
      const parent = errorSpan.parentNode;
      const correctedNode = document.createTextNode(suggestion.correction);
      parent.insertBefore(correctedNode, errorSpan);
      parent.removeChild(errorSpan);
      parent.normalize();
      // Place cursor right after the corrected text
      try {
        const sel = window.getSelection();
        const r = document.createRange();
        r.setStartAfter(correctedNode);
        r.collapse(true);
        sel.removeAllRanges();
        sel.addRange(r);
      } catch(e) {}
    } else {
      // Fallback: find span by matching original text
      const allErrorSpans = document.querySelectorAll('.spelling-error, .grammar-error, .punctuation-suggestion');
      let found = false;
      allErrorSpans.forEach(span => {
        if (!found && span.textContent === suggestion.original) {
          const p = span.parentNode;
          const correctedNode = document.createTextNode(suggestion.correction);
          p.insertBefore(correctedNode, span);
          p.removeChild(span);
          p.normalize();
          // Place cursor right after the corrected text
          try {
            const sel = window.getSelection();
            const r = document.createRange();
            r.setStartAfter(correctedNode);
            r.collapse(true);
            sel.removeAllRanges();
            sel.addRange(r);
          } catch(e) {}
          found = true;
        }
      });
      if (!found) {
        // Last resort: offset-based replacement
        const text = getEditorText();
        const before = text.substring(0, suggestion.start);
        const after = text.substring(suggestion.end);
        const newText = before + suggestion.correction + after;
        setEditorHTML(escapeHtml(newText));
        // Place cursor after the inserted correction
        setCaretOffset(suggestion.start + suggestion.correction.length);
      }
    }
    hideTooltip();
    // Re-focus editor so Ctrl+Z works immediately after tooltip correction
    const _ed = getEditorElement(); if (_ed) _ed.focus();

    // Remove applied suggestion from list (UUID-based, no re-indexing needed)
    if (window.currentSuggestions) {
      window.currentSuggestions = window.currentSuggestions.filter(
        s => s.id !== suggestion.id
      );

      const spellingCount = window.currentSuggestions.filter(s => s.type === 'spelling').length;
      const grammarCount = window.currentSuggestions.filter(s => s.type === 'grammar').length;
      const punctuationCount = window.currentSuggestions.filter(s => s.type === 'punctuation').length;
      updateSuggestionCounts(spellingCount, grammarCount, punctuationCount);
      updateWritingScore(spellingCount, grammarCount, punctuationCount);
      updateSuggestionsList(window.currentSuggestions);
    }
    // Pipeline Hardening v3.3: Do NOT call analyzeTextDelayed() — prevents recursive re-analysis
  } finally {
    // FIX-32: Delay guard reset until AFTER re-analysis fires,
    // preventing normalize()/input events from triggering double analysis.
    setTimeout(() => { _isApplyingSuggestion = false; }, 400);
  }
  // P2/User Request: Auto re-analyze after applying suggestion
  // Calls analyzeText() DIRECTLY (not delayed) for instant re-analysis.
  setTimeout(() => { analyzeText(); }, 300);
}

function applyCorrection() {
  if (!window.currentApplySuggestion) return;
  applySuggestionAtOffsets(window.currentApplySuggestion);
  if (typeof showToast === 'function') showToast('✓ تم التصحيح');
}

function applyAlternativeCorrection(suggestion, correctionText) {
  _isApplyingSuggestion = true;
  try {
    pushUndoState(); // Save state before correction
    // Pipeline Hardening v3.3: UUID-based span lookup
    const suggestionId = suggestion.id;
    const errorSpan = suggestionId ? document.querySelector(`[data-suggestion-id="${suggestionId}"]`) : null;

    if (errorSpan) {
      const parent = errorSpan.parentNode;
      const correctedNode = document.createTextNode(correctionText);
      parent.insertBefore(correctedNode, errorSpan);
      parent.removeChild(errorSpan);
      parent.normalize();
      // Place cursor right after the corrected text
      try {
        const sel = window.getSelection();
        const r = document.createRange();
        r.setStartAfter(correctedNode);
        r.collapse(true);
        sel.removeAllRanges();
        sel.addRange(r);
      } catch(e) {}
    } else {
      const allErrorSpans = document.querySelectorAll('.spelling-error, .grammar-error, .punctuation-suggestion');
      let found = false;
      allErrorSpans.forEach(span => {
        if (!found && span.textContent === suggestion.original) {
          const p = span.parentNode;
          const correctedNode = document.createTextNode(correctionText);
          p.insertBefore(correctedNode, span);
          p.removeChild(span);
          p.normalize();
          // Place cursor right after the corrected text
          try {
            const sel = window.getSelection();
            const r = document.createRange();
            r.setStartAfter(correctedNode);
            r.collapse(true);
            sel.removeAllRanges();
            sel.addRange(r);
          } catch(e) {}
          found = true;
        }
      });
      if (!found) {
        const text = getEditorText();
        const before = text.substring(0, suggestion.start);
        const after = text.substring(suggestion.end);
        const newText = before + correctionText + after;
        setEditorHTML(escapeHtml(newText));
        // Place cursor after the inserted correction
        setCaretOffset(suggestion.start + correctionText.length);
      }
    }
    hideTooltip();
    // Re-focus editor so Ctrl+Z works immediately after tooltip correction
    const _ed2 = getEditorElement(); if (_ed2) _ed2.focus();
    // Remove applied suggestion (UUID-based, no re-indexing needed)
    if (window.currentSuggestions) {
      window.currentSuggestions = window.currentSuggestions.filter(
        s => s.id !== suggestion.id
      );

      const spellingCount = window.currentSuggestions.filter(s => s.type === 'spelling').length;
      const grammarCount = window.currentSuggestions.filter(s => s.type === 'grammar').length;
      const punctuationCount = window.currentSuggestions.filter(s => s.type === 'punctuation').length;
      updateSuggestionCounts(spellingCount, grammarCount, punctuationCount);
      updateWritingScore(spellingCount, grammarCount, punctuationCount);
      updateSuggestionsList(window.currentSuggestions);
    }
    // Pipeline Hardening v3.3: Do NOT call analyzeTextDelayed() — prevents recursive re-analysis
  } finally {
    // FIX-32: Delay guard reset until AFTER re-analysis fires.
    setTimeout(() => { _isApplyingSuggestion = false; }, 400);
  }
  // P2/User Request: Auto re-analyze after applying alternative correction
  setTimeout(() => { analyzeText(); }, 300);
}

function dismissSuggestion(suggestion) {
  pushUndoState(); // Save state before dismiss
  // Add the word to dismissed whitelist so it's never flagged again
  if (suggestion.original) {
    _dismissedWords.add(suggestion.original);
    _saveDismissedWords();
  }

  // Remove the error highlight but keep the text as-is
  // Pipeline Hardening v3.3: UUID-based span lookup
  const suggestionId = suggestion.id;
  const errorSpan = suggestionId ? document.querySelector(`[data-suggestion-id="${suggestionId}"]`) : null;

  if (errorSpan) {
    // Unwrap: replace span with its text content
    const parent = errorSpan.parentNode;
    while (errorSpan.firstChild) {
      parent.insertBefore(errorSpan.firstChild, errorSpan);
    }
    parent.removeChild(errorSpan);
    parent.normalize();
  }

  if (window.currentSuggestions) {
    window.currentSuggestions = window.currentSuggestions.filter(
      s => s.id !== suggestion.id
    );
    // Pipeline Hardening v3.3: No re-indexing needed — UUID-based

    const spellingCount = window.currentSuggestions.filter(s => s.type === 'spelling').length;
    const grammarCount = window.currentSuggestions.filter(s => s.type === 'grammar').length;
    const punctuationCount = window.currentSuggestions.filter(s => s.type === 'punctuation').length;
    updateSuggestionCounts(spellingCount, grammarCount, punctuationCount);
    updateWritingScore(spellingCount, grammarCount, punctuationCount);
    updateSuggestionsList(window.currentSuggestions);
  }
  hideTooltip();
  // Re-focus editor so Ctrl+Z works immediately
  const _ed3 = getEditorElement(); if (_ed3) _ed3.focus();
}

window.dismissAndReRenderAll = function(type) {
  if (!window.currentSuggestions || window.currentSuggestions.length === 0) return;
  pushUndoState();
  const toDismiss = type === 'all' ? window.currentSuggestions : window.currentSuggestions.filter(s => s.type === type);
  
  toDismiss.forEach(s => {
    if (s.original) _dismissedWords.add(s.original);
  });
  _saveDismissedWords();
  
  window.currentSuggestions = window.currentSuggestions.filter(s => 
    type === 'all' ? false : s.type !== type
  );
  
  const editor = getEditorElement();
  clearOverlays(editor);
  overlaySuggestions(editor, window.currentSuggestions);
  
  const spellingCount = window.currentSuggestions.filter(s => s.type === 'spelling').length;
  const grammarCount = window.currentSuggestions.filter(s => s.type === 'grammar').length;
  const punctuationCount = window.currentSuggestions.filter(s => s.type === 'punctuation').length;

  updateSuggestionCounts(spellingCount, grammarCount, punctuationCount);
  updateWritingScore(spellingCount, grammarCount, punctuationCount);
  updateSuggestionsList(window.currentSuggestions);
  
  // Update sidebar button visibility via global format.js function if it exists
  if (typeof window.renderSuggestionsSidebar === 'function') {
    window.renderSuggestionsSidebar(window.currentSuggestions);
  }
};

function applySuggestionById(id) {
  // Pipeline Hardening v3.3: UUID-based lookup
  const suggestion = findSuggestionById(id);
  if (!suggestion) return;
  applySuggestionAtOffsets(suggestion);
}

function applyAllSuggestions() {
  // CRITICAL: Sort in REVERSE order (highest start offset first).
  const suggestions = [...(window.currentSuggestions || [])].sort((a, b) => b.start - a.start);
  if (suggestions.length === 0) return;
  _isApplyingSuggestion = true;
  try {
    pushUndoState(); // Save state before applying all

    // FIX-32: Use PURE TEXT-BASED approach to avoid DOM/offset mismatch.
    // The old mixed DOM+fallback approach caused word duplication because
    // after DOM-based fixes shifted the text, the fallback's stale offsets
    // would insert corrections at wrong positions.
    // Reverse-order text replacement is safe — each patch's offsets are
    // valid because we haven't modified anything before them yet.
    let text = getEditorText();
    suggestions.forEach((s) => {
      if (s.start >= 0 && s.end <= text.length && s.start <= s.end) {
        text = text.substring(0, s.start) + s.correction + text.substring(s.end);
      }
    });
    setEditorHTML(escapeHtml(text));

    // Place cursor at end of editor content
    const editor = getEditorElement();
    if (editor) {
      try {
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(editor);
        range.collapse(false);
        sel.removeAllRanges();
        sel.addRange(range);
      } catch(e) {}
      editor.focus();
    }

    hideTooltip();

    // Clear suggestions
    window.currentSuggestions = [];
    updateSuggestionCounts(0, 0, 0);
    updateWritingScore(0, 0, 0);
    updateSuggestionsList([]);
    if (typeof showToast === 'function') showToast('✓ تم تطبيق ' + suggestions.length + ' تصحيح');
  } finally {
    // FIX-32: Delay guard reset
    setTimeout(() => { _isApplyingSuggestion = false; }, 400);
  }
  // FIX-34: Do NOT auto-re-analyze after Apply All.
  // This caused an infinite loop when spelling/grammar disagree.
  // User can click "Analyze" manually if they want to re-check.
}

function clearEditor() {
  // Don't prompt if editor is already empty
  const text = getEditorText();
  if (text.trim().length > 0) {
    if (!confirm('هل أنت متأكد من مسح كل المحتوى؟')) return;
  }
  setEditorHTML('');
  window.currentSuggestions = [];
  updateSuggestionCounts(0, 0, 0);
  updateWritingScore(0, 0, 0);
  updateSuggestionsList([]);
  updateEditorStats();
  updatePlaceholder();
  updateAnalysisLimitBanner(false);
  if (typeof updateExportButtonStates === 'function') updateExportButtonStates();
}

/**
 * Load plain text into editor — sole entry point for document import
 * @param {string} text - UTF-8 plain text
 * @param {object} options - { analyze: true, filename: string }
 */
function loadDocumentText(text, options = {}) {
  const normalized = typeof normalizeImportedText === 'function'
    ? normalizeImportedText(text)
    : String(text || '').replace(/^\uFEFF/, '');

  setEditorHTML(escapeHtml(normalized));
  window.currentSuggestions = [];
  hideTooltip();
  updatePlaceholder();
  updateEditorStats();
  updateSuggestionCounts(0, 0, 0);
  updateWritingScore(0, 0, 0);
  updateSuggestionsList([]);
  updateAnalysisLimitBanner(normalized.length > MAX_ANALYZE_LENGTH);

  if (typeof updateExportButtonStates === 'function') {
    updateExportButtonStates();
  }

  if (options.analyze !== false) {
    analyzeTextDelayed();
  }
}

function copyText() {
  const text = getEditorText();
  navigator.clipboard.writeText(text).then(() => {
    if (typeof showToast === 'function') showToast('✓ تم نسخ النص');
  }).catch(() => {
    const temp = document.createElement('textarea');
    temp.value = text;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    if (typeof showToast === 'function') showToast('✓ تم نسخ النص');
  });
}

// ── Feedback API (P2) ──
function _sendFeedback(suggestion, helpful) {
  const apiBase = window.BAYAN_API_BASE || '';
  fetch(`${apiBase}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      suggestion_id: suggestion.id || '',
      helpful: helpful,
      original: suggestion.original || '',
      correction: suggestion.correction || '',
      text: (document.getElementById('editor-container')?.textContent || '').substring(0, 200),
    })
  }).catch(err => console.warn('[Feedback] Failed:', err));
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initEditor,
    analyzeText,
    analyzeTextDelayed,
    clearEditor,
    copyText,
    loadDocumentText,
    updateEditorStats,
    showTooltip,
    hideTooltip,
    applyCorrection,
    applySuggestionById,
    applyAllSuggestions
  };
}
