// src/js/editor.js
// Editor management and state

let analyzeTimeout;
let analyzeAbortController = null;
let _lastInputTime = 0;
const ANALYZE_DEBOUNCE_MS = 1000;
const MAX_ANALYZE_LENGTH = 5000;

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

  editor.addEventListener('input', () => {
    _lastInputTime = Date.now();
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

    // Custom Undo/Redo — capture phase on document fires BEFORE browser native undo
    // Must be on document (not editor) so it works after tooltip clicks steal focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
      if (_undoStack.length > 0) {
        e.preventDefault();
        e.stopImmediatePropagation();
        editorUndo();
        editor.focus();
        return;
      }
    }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
      if (_redoStack.length > 0) {
        e.preventDefault();
        e.stopImmediatePropagation();
        editorRedo();
        editor.focus();
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

  const text = getEditorText();
  if (!text || text.trim().length === 0) {
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
  const suggestions = window.currentSuggestions || [];
  return suggestions[parseInt(id, 10)] || null;
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

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: textForApi }),
      signal: analyzeAbortController.signal
    });

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
    spelling: 'خطأ إملائي',
    grammar: 'خطأ نحوي',
    punctuation: 'علامات ترقيم'
  };

  if (typeEl) {
    typeEl.textContent = typeMap[suggestion.type] || suggestion.type;
    typeEl.className = `popover-type popover-type--${suggestion.type}`;
  }

  if (originalEl) {
    originalEl.textContent = suggestion.original;
  }

  // Render alternatives
  if (alternativesEl) {
    const alts = suggestion.alternatives || [suggestion.correction, suggestion.original];
    let html = '';
    // Render corrections first (non-keep)
    alts.forEach((alt, i) => {
      const isKeep = alt === suggestion.original;
      if (isKeep) return; // render keep button last
      const isMain = i === 0;
      const btnClass = isMain ? 'popover-alt-btn popover-alt-main' : 'popover-alt-btn';
      html += `<button class="${btnClass}" data-alt-correction="${escapeHtml(alt)}" type="button">${escapeHtml(alt)}</button>`;
    });
    // Render keep button at end
    html += `<button class="popover-alt-btn popover-alt-keep" data-alt-correction="${escapeHtml(suggestion.original)}" type="button">إبقاء كما هي</button>`;
    alternativesEl.innerHTML = html;

    // Bind click events
    alternativesEl.querySelectorAll('.popover-alt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const correctionText = btn.dataset.altCorrection;
        if (correctionText === suggestion.original) {
          // "Keep as-is" — just dismiss the suggestion
          dismissSuggestion(suggestion);
        } else {
          // Apply this alternative correction
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
  pushUndoState(); // Save state before correction
  // Find the error span in the DOM and replace its text content
  // This preserves formatting (bold, italic, etc.) around/inside the span
  const idx = (window.currentSuggestions || []).indexOf(suggestion);
  const errorSpan = idx >= 0 ? document.querySelector(`[data-suggestion-id="${idx}"]`) : null;

  if (errorSpan) {
    // Replace the error span's text content with the correction
    // while keeping it inside its formatting parent
    const parent = errorSpan.parentNode;
    const correctedNode = document.createTextNode(suggestion.correction);
    parent.insertBefore(correctedNode, errorSpan);
    parent.removeChild(errorSpan);
    parent.normalize();
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
    }
  }
  hideTooltip();
  analyzeTextDelayed();
}

function applyCorrection() {
  if (!window.currentApplySuggestion) return;
  applySuggestionAtOffsets(window.currentApplySuggestion);
  if (typeof showToast === 'function') showToast('✓ تم التصحيح');
}

function applyAlternativeCorrection(suggestion, correctionText) {
  pushUndoState(); // Save state before correction
  const idx = (window.currentSuggestions || []).indexOf(suggestion);
  const errorSpan = idx >= 0 ? document.querySelector(`[data-suggestion-id="${idx}"]`) : null;

  if (errorSpan) {
    const parent = errorSpan.parentNode;
    const correctedNode = document.createTextNode(correctionText);
    parent.insertBefore(correctedNode, errorSpan);
    parent.removeChild(errorSpan);
    parent.normalize();
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
        found = true;
      }
    });
    if (!found) {
      const text = getEditorText();
      const before = text.substring(0, suggestion.start);
      const after = text.substring(suggestion.end);
      const newText = before + correctionText + after;
      setEditorHTML(escapeHtml(newText));
    }
  }
  hideTooltip();
  analyzeTextDelayed();
}

function dismissSuggestion(suggestion) {
  pushUndoState(); // Save state before dismiss
  // Add the word to dismissed whitelist so it's never flagged again
  if (suggestion.original) {
    _dismissedWords.add(suggestion.original);
    _saveDismissedWords();
  }

  // Remove the error highlight but keep the text as-is
  const idx = (window.currentSuggestions || []).indexOf(suggestion);
  const errorSpan = idx >= 0 ? document.querySelector(`[data-suggestion-id="${idx}"]`) : null;

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
      s => !(s.start === suggestion.start && s.end === suggestion.end)
    );

    const spellingCount = window.currentSuggestions.filter(s => s.type === 'spelling').length;
    const grammarCount = window.currentSuggestions.filter(s => s.type === 'grammar').length;
    const punctuationCount = window.currentSuggestions.filter(s => s.type === 'punctuation').length;
    updateSuggestionCounts(spellingCount, grammarCount, punctuationCount);
    updateWritingScore(spellingCount, grammarCount, punctuationCount);
    updateSuggestionsList(window.currentSuggestions);
  }
  hideTooltip();
}

function applySuggestionByIndex(index) {
  const suggestions = window.currentSuggestions || [];
  const suggestion = suggestions[index];
  if (!suggestion) return;
  applySuggestionAtOffsets(suggestion);
}

function applyAllSuggestions() {
  const suggestions = [...(window.currentSuggestions || [])].sort((a, b) => b.start - a.start);
  if (suggestions.length === 0) return;
  if (!confirm('هل تريد تطبيق جميع التصحيحات (' + suggestions.length + ')؟')) return;
  pushUndoState(); // Save state before applying all

  let text = getEditorText();
  suggestions.forEach((s) => {
    text = text.substring(0, s.start) + s.correction + text.substring(s.end);
  });

  setEditorHTML(escapeHtml(text));
  hideTooltip();
  analyzeTextDelayed();
  if (typeof showToast === 'function') showToast('✓ تم تطبيق ' + suggestions.length + ' تصحيح');
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
    applySuggestionByIndex,
    applyAllSuggestions
  };
}
