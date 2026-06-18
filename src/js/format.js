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

/* ── Undo / Redo ── */
function formatUndo() { execFormat('undo'); }
function formatRedo() { execFormat('redo'); }

/* ── Alignment ── */
function formatAlignRight() { execFormat('justifyRight'); }
function formatAlignCenter() { execFormat('justifyCenter'); }
function formatAlignLeft() { execFormat('justifyLeft'); }

/* ── Font family ── */
function formatFont(fontName) {
  execFormat('fontName', fontName);
}

/* ── Font size ── */
// execCommand fontSize only supports 1-7, so we use CSS instead
function formatFontSize(size) {
  const sel = window.getSelection();
  if (!sel.rangeCount) return;

  const range = sel.getRangeAt(0);
  if (range.collapsed) return; // no selection

  // Wrap selected text in a span with the font size
  const span = document.createElement('span');
  span.style.fontSize = size;
  try {
    range.surroundContents(span);
  } catch (e) {
    // If selection crosses elements, use execCommand as fallback
    execFormat('fontSize', '4');
    // Then find the font element and fix the size
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
    'fmt-align-right': 'justifyRight',
    'fmt-align-center': 'justifyCenter',
    'fmt-align-left': 'justifyLeft',
  };

  Object.entries(btnMap).forEach(([id, command]) => {
    const btn = document.getElementById(id);
    if (btn) {
      const isActive = document.queryCommandState(command);
      btn.classList.toggle('fmt-active', isActive);
    }
  });

  // Font family
  const fontSelect = document.getElementById('fmt-font-family');
  if (fontSelect) {
    const currentFont = document.queryCommandValue('fontName').replace(/['"]/g, '');
    if (currentFont) {
      // Try to match
      for (let i = 0; i < fontSelect.options.length; i++) {
        if (fontSelect.options[i].value === currentFont) {
          fontSelect.selectedIndex = i;
          break;
        }
      }
    }
  }
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

  // Font family change
  const fontSelect = document.getElementById('fmt-font-family');
  if (fontSelect) {
    fontSelect.addEventListener('change', () => {
      formatFont(fontSelect.value);
    });
  }

  // Font size change
  const sizeSelect = document.getElementById('fmt-font-size');
  if (sizeSelect) {
    sizeSelect.addEventListener('change', () => {
      formatFontSize(sizeSelect.value);
    });
  }
}
