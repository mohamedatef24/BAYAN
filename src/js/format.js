// src/js/format.js
// Rich text formatting commands for the editor

/**
 * Execute a formatting command on the current selection
 * @param {string} command - execCommand name
 * @param {string} [value] - optional value
 * @param {boolean} [keepSelection] - if true, don't collapse selection
 */
function execFormat(command, value, keepSelection) {
  pushUndoState(); // Save state before formatting
  document.execCommand(command, false, value !== undefined ? value : null);
  const editor = getEditorElement();
  if (editor) editor.focus();
  
  // Collapse selection after formatting so text doesn't stay highlighted
  if (!keepSelection) {
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0 && !sel.isCollapsed) {
      sel.collapseToEnd();
    }
  }
  
  updateFormatState();
}

/* ── Text style ── */
function formatBold() { execFormat('bold'); }
function formatItalic() { execFormat('italic'); }
function formatUnderline() { execFormat('underline'); }
function formatStrikethrough() { execFormat('strikethrough'); }

/* ── Undo / Redo (uses custom stack — same as Ctrl+Z/Y) ── */
function formatUndo() { editorUndo(); }
function formatRedo() { editorRedo(); }

/* ── Alignment (applies to paragraph containing selection/cursor) ── */
function formatAlignRight() { execFormat('justifyRight'); }
function formatAlignCenter() { execFormat('justifyCenter'); }
function formatAlignLeft() { execFormat('justifyLeft'); }


/* ── Font family ── */
function formatFont(fontName) {
  execFormat('fontName', fontName);
  // Update the dropdown label
  const label = document.getElementById('fmt-font-label');
  if (label) label.textContent = fontName;
  closeAllFmtDropdowns();
}

/* ── Font size ── */
function formatFontSize(size) {
  const sel = window.getSelection();
  if (!sel.rangeCount) return;

  const range = sel.getRangeAt(0);
  if (range.collapsed) {
    // No selection — size will apply to next typed text
    // Use a zero-width space trick
    const span = document.createElement('span');
    span.style.fontSize = size;
    span.textContent = '\u200B';
    range.insertNode(span);
    // Place cursor after the span
    const newRange = document.createRange();
    newRange.setStartAfter(span);
    newRange.collapse(true);
    sel.removeAllRanges();
    sel.addRange(newRange);
  } else {
    // Wrap selected text
    const span = document.createElement('span');
    span.style.fontSize = size;
    try {
      range.surroundContents(span);
    } catch (e) {
      // Fallback: use execCommand
      execFormat('fontSize', '4');
      const editor = getEditorElement();
      if (editor) {
        editor.querySelectorAll('font[size="4"]').forEach(f => {
          const s = document.createElement('span');
          s.style.fontSize = size;
          s.innerHTML = f.innerHTML;
          f.replaceWith(s);
        });
      }
    }
  }

  // Update label
  const label = document.getElementById('fmt-size-label');
  if (label) label.textContent = parseInt(size);
  
  // Update active item
  document.querySelectorAll('#fmt-size-menu .fmt-dropdown__item').forEach(item => {
    item.classList.toggle('fmt-dropdown__item--active', item.dataset.size === size);
  });

  closeAllFmtDropdowns();
  const editor = getEditorElement();
  if (editor) editor.focus();
  updateFormatState();
}

/**
 * Update toolbar button active states based on current selection
 */
function updateFormatState() {
  const btnMap = {
    'fmt-bold': 'bold',
    'fmt-italic': 'italic',
    'fmt-underline': 'underline',
    'fmt-strikethrough': 'strikeThrough',
  };

  Object.entries(btnMap).forEach(([id, command]) => {
    const btn = document.getElementById(id);
    if (btn) {
      btn.classList.toggle('fmt-active', document.queryCommandState(command));
    }
  });

  // Alignment — mutually exclusive
  const alignMap = {
    'fmt-align-right': 'justifyRight',
    'fmt-align-center': 'justifyCenter',
    'fmt-align-left': 'justifyLeft',
  };
  Object.entries(alignMap).forEach(([id, command]) => {
    const btn = document.getElementById(id);
    if (btn) {
      btn.classList.toggle('fmt-active', document.queryCommandState(command));
    }
  });
}

/**
 * Close all formatting dropdowns
 */
function closeAllFmtDropdowns() {
  document.querySelectorAll('.fmt-dropdown').forEach(d => d.classList.remove('open'));
}

/**
 * Toggle a specific dropdown
 */
function toggleFmtDropdown(wrapperId) {
  const wrap = document.getElementById(wrapperId);
  if (!wrap) return;
  const isOpen = wrap.classList.contains('open');
  closeAllFmtDropdowns();
  if (!isOpen) wrap.classList.add('open');
}

/**
 * Initialize formatting toolbar events
 */
function initFormatToolbar() {
  const editor = getEditorElement();
  if (!editor) return;

  // Update button states on selection change
  document.addEventListener('selectionchange', () => {
    if (editor.contains(document.activeElement) || editor === document.activeElement) {
      updateFormatState();
    }
  });

  // Font dropdown trigger
  const fontTrigger = document.getElementById('fmt-font-trigger');
  if (fontTrigger) {
    fontTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFmtDropdown('fmt-font-wrap');
    });
  }

  // Font items
  document.querySelectorAll('#fmt-font-menu .fmt-dropdown__item').forEach(item => {
    item.addEventListener('click', () => {
      formatFont(item.dataset.font);
    });
  });

  // Size dropdown trigger
  const sizeTrigger = document.getElementById('fmt-size-trigger');
  if (sizeTrigger) {
    sizeTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFmtDropdown('fmt-size-wrap');
    });
  }

  // Size items
  document.querySelectorAll('#fmt-size-menu .fmt-dropdown__item').forEach(item => {
    item.addEventListener('click', () => {
      formatFontSize(item.dataset.size);
    });
  });

  // Close dropdowns when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.fmt-dropdown')) {
      closeAllFmtDropdowns();
    }
  });

  // Close dropdowns on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllFmtDropdowns();
  });

  // Item 8: Color pickers
  initColorPicker('fmt-textcolor', 'foreColor', 'fmt-textcolor-bar');
  initColorPicker('fmt-highlight', 'hiliteColor', 'fmt-highlight-bar');
}

/* ── Item 8: Color Picker ── */
const COLOR_PALETTE = [
  '#ECEEF2', '#E88A8A', '#E4B35A', '#6BC98A', '#6BA3E0', '#A594E8',
  '#F5F5F5', '#FF6B6B', '#FFD93D', '#51CF66', '#339AF0', '#845EF7',
  '#ADB5BD', '#C92A2A', '#F08C00', '#2B8A3E', '#1864AB', '#5F3DC4',
  '#495057', '#862E2E', '#B7791F', '#1B5E20', '#0D47A1', '#311B92',
  '#212529', '#000000', '#5D4037', '#004D40', '#1A237E', '#4A148C',
];

function initColorPicker(prefix, command, barId) {
  const trigger = document.getElementById(prefix + '-trigger');
  const wrap = document.getElementById(prefix + '-wrap');
  const grid = document.getElementById(prefix + '-grid');
  if (!trigger || !wrap || !grid) return;

  // Build swatches
  COLOR_PALETTE.forEach(color => {
    const swatch = document.createElement('button');
    swatch.type = 'button';
    swatch.className = 'fmt-color-swatch';
    swatch.style.background = color;
    swatch.title = color;
    swatch.addEventListener('click', () => {
      document.execCommand(command, false, color);
      const bar = document.getElementById(barId);
      if (bar) bar.style.background = color;
      closeAllFmtDropdowns();
      const editor = getEditorElement();
      if (editor) editor.focus();
    });
    grid.appendChild(swatch);
  });

  // Toggle
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleFmtDropdown(prefix + '-wrap');
  });
}

/* ── Item 4: Enhanced Stats ── */
function updateEnhancedStats() {
  const text = getEditorText();
  const charCount = text.length;
  
  // Count sentences: split on Arabic/Latin sentence endings + newlines
  const words = text.trim().split(/\s+/).filter(w => w.length > 0).length;
  let sentences = 0;
  if (text.trim().length > 0) {
    // Split by: . ! ? ؟ ، ؛ and newlines
    sentences = text.split(/[.!?؟\n]+/).filter(s => s.trim().length > 2).length;
    if (sentences === 0) sentences = 1; // at least 1 if there's text
  }
  
  // Reading time: ~180 words/min for Arabic, show actual minutes
  const readingTimeMinutes = words === 0 ? 0 : Math.max(1, Math.round(words / 180));

  const charEl = document.getElementById('char-count');
  const sentEl = document.getElementById('sentence-count');
  const readEl = document.getElementById('reading-time');

  if (charEl) charEl.textContent = charCount.toLocaleString('ar-EG');
  if (sentEl) sentEl.textContent = sentences.toLocaleString('ar-EG');
  if (readEl) readEl.textContent = readingTimeMinutes.toLocaleString('ar-EG');
}

/* ── Item 6: Summary Stats ── */
function updateSummaryStats(summaryText) {
  const originalText = getEditorText();
  const summaryWords = summaryText.trim().split(/\s+/).filter(w => w.length > 0).length;
  const originalWords = originalText.trim().split(/\s+/).filter(w => w.length > 0).length;
  const compression = originalWords > 0 ? Math.round((1 - summaryWords / originalWords) * 100) : 0;

  const statsEl = document.getElementById('summary-stats');
  const wordCountEl = document.getElementById('summary-word-count');
  const compressionEl = document.getElementById('summary-compression');

  if (statsEl) statsEl.style.display = 'flex';
  if (wordCountEl) wordCountEl.textContent = summaryWords;
  if (compressionEl) compressionEl.textContent = compression + '%';
}

/* ── Item 11: Summary Mode ── */
window._summaryMode = 'paragraph';

function setSummaryMode(mode) {
  window._summaryMode = mode;
  document.querySelectorAll('.summary-mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.id === 'summary-mode-' + mode);
  });
}

/* ── Item 3: Empty States ── */
function renderEmptyState(container, icon, title, desc) {
  if (!container) return;
  container.innerHTML = `
    <div class="empty-state">
      <div class="empty-state__icon">${icon}</div>
      <div class="empty-state__title">${title}</div>
      <div class="empty-state__desc">${desc}</div>
    </div>
  `;
}

/* ── Item 7: Document Search ── */
function initDocSearch() {
  const searchInput = document.getElementById('docs-search-input');
  if (!searchInput) return;

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.trim().toLowerCase();
    const items = document.querySelectorAll('.doc-list-item');
    items.forEach(item => {
      const title = (item.querySelector('.doc-list-item__title')?.textContent || '').toLowerCase();
      item.style.display = title.includes(query) || !query ? '' : 'none';
    });
  });
}
