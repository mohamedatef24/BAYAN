// src/js/selection.js
// Selection and cursor position preservation

/**
 * Saves the current selection state in the document
 * Works with contenteditable elements
 * @returns {Object|null} - Selection state object or null if no selection
 */
function saveSelection() {
  const selection = window.getSelection();
  if (selection.rangeCount === 0) {
    return null;
  }

  const range = selection.getRangeAt(0);
  const editor = document.getElementById('editor-container');

  // Get offsets relative to the editor
  try {
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(editor);
    preCaretRange.setEnd(range.endContainer, range.endOffset);

    const offset = preCaretRange.toString().length;
    const isCollapsed = range.collapsed;

    let selectionStart = offset;
    let selectionEnd = offset;

    if (!isCollapsed) {
      const preCaretRangeStart = range.cloneRange();
      preCaretRangeStart.selectNodeContents(editor);
      preCaretRangeStart.setEnd(range.startContainer, range.startOffset);
      selectionStart = preCaretRangeStart.toString().length;
    }

    return {
      selectionStart,
      selectionEnd,
      isCollapsed
    };
  } catch (e) {
    console.warn('saveSelection failed:', e);
    return null;
  }
}

/**
 * Restores a previously saved selection state
 * Works with contenteditable elements
 * @param {Object} savedSelection - Selection state from saveSelection()
 */
function restoreSelection(savedSelection) {
  if (!savedSelection) return;

  const editor = document.getElementById('editor-container');
  const selection = window.getSelection();

  try {
    let charCount = 0;
    let nodeStack = [editor];
    let node, foundStart = false, foundEnd = false;

    while (!foundEnd && (node = nodeStack.pop())) {
      if (node.nodeType === Node.TEXT_NODE) {
        const nextCharCount = charCount + node.length;

        if (
          !foundStart &&
          savedSelection.selectionStart >= charCount &&
          savedSelection.selectionStart <= nextCharCount
        ) {
          const range = document.createRange();
          range.setStart(node, savedSelection.selectionStart - charCount);
          foundStart = true;

          if (savedSelection.isCollapsed) {
            range.collapse(true);
            selection.removeAllRanges();
            selection.addRange(range);
            return;
          }
        }

        if (
          foundStart &&
          savedSelection.selectionEnd >= charCount &&
          savedSelection.selectionEnd <= nextCharCount
        ) {
          const range = selection.getRangeAt(0);
          range.setEnd(node, savedSelection.selectionEnd - charCount);
          foundEnd = true;
        }

        charCount = nextCharCount;
      } else {
        let i = node.childNodes.length;
        while (i--) {
          nodeStack.push(node.childNodes[i]);
        }
      }
    }

    if (foundStart && foundEnd) {
      selection.removeAllRanges();
      selection.addRange(selection.getRangeAt(0));
    }
  } catch (e) {
    console.warn('restoreSelection failed:', e);
  }
}

/**
 * Gets the current caret offset in the editor
 * @returns {number} - Character offset of the cursor
 */
function getCaretOffset() {
  const selection = window.getSelection();
  if (selection.rangeCount === 0) {
    return 0;
  }

  const range = selection.getRangeAt(0);
  const editor = document.getElementById('editor-container');

  try {
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(editor);
    preCaretRange.setEnd(range.endContainer, range.endOffset);
    return preCaretRange.toString().length;
  } catch (e) {
    console.warn('getCaretOffset failed:', e);
    return 0;
  }
}

/**
 * Sets the caret position in the editor
 * @param {number} offset - Character offset to position cursor at
 */
function setCaretOffset(offset) {
  const editor = document.getElementById('editor-container');
  const selection = window.getSelection();

  try {
    let charCount = 0;
    let nodeStack = [editor];
    let node;
    const range = document.createRange();
    range.setStart(editor, 0);

    while ((node = nodeStack.pop())) {
      if (node.nodeType === Node.TEXT_NODE) {
        const nextCharCount = charCount + node.length;

        if (offset >= charCount && offset <= nextCharCount) {
          range.setStart(node, offset - charCount);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
          return;
        }

        charCount = nextCharCount;
      } else {
        let i = node.childNodes.length;
        while (i--) {
          nodeStack.push(node.childNodes[i]);
        }
      }
    }

    // If offset is beyond content, set to end
    range.selectNodeContents(editor);
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);
  } catch (e) {
    console.warn('setCaretOffset failed:', e);
  }
}

/**
 * Gets the text content of the editor
 * Masks quran-applied text with spaces to exclude from analysis
 * @returns {string} - Plain text content (quran regions replaced with spaces)
 */
function getEditorText() {
  const editor = document.getElementById('editor-container');
  if (!editor) return '';
  // Clone the editor to mask quran text without modifying the DOM
  const clone = editor.cloneNode(true);
  clone.querySelectorAll('.quran-applied').forEach(function(el) {
    // Replace quran text with spaces of the same length to preserve offsets
    var len = (el.textContent || '').length;
    el.textContent = ' '.repeat(len);
  });
  return clone.textContent || '';
}

/**
 * Sets the editor HTML with proper text content
 * WARNING: Use this only with sanitized/escaped HTML
 * @param {string} html - HTML to insert
 */
function setEditorHTML(html) {
  const editor = document.getElementById('editor-container');
  if (!editor) return;
  editor.innerHTML = html;
  try {
    localStorage.setItem('bayan_editor_draft', html);
  } catch (e) {}
}

/**
 * Gets the editor element
 * @returns {HTMLElement} - Editor element
 */
function getEditorElement() {
  return document.getElementById('editor-container');
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    saveSelection,
    restoreSelection,
    getCaretOffset,
    setCaretOffset,
    getEditorText,
    setEditorHTML,
    getEditorElement
  };
}
