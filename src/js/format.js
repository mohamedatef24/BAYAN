// src/js/format.js
// Rich text formatting commands for the editor

/**
 * Execute a formatting command on the current selection
 */
function execFormat(command, value) {
  document.execCommand(command, false, value || null);
  const editor = getEditorElement();
  if (editor) editor.focus();
  updateFormatState();
}

/* ── Text style ── */
function formatBold() { execFormat('bold'); }
function formatItalic() { execFormat('italic'); }
function formatUnderline() { execFormat('underline'); }
function formatStrikethrough() { execFormat('strikethrough'); }

/* ── Undo / Redo (handles both typing and formatting) ── */
function formatUndo() { execFormat('undo'); }
function formatRedo() { execFormat('redo'); }

/* ── Alignment (applies to paragraph containing selection) ── */
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
}
