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

/* ── Text Direction (RTL/LTR) ── */
function setDirection(dir) {
  const editor = getEditorElement();
  if (!editor) return;
  const sel = window.getSelection();
  if (sel && sel.rangeCount > 0) {
    const range = sel.getRangeAt(0);
    let block = range.startContainer;
    if (block.nodeType === 3) block = block.parentNode;
    while (block && block !== editor && !['DIV','P','H1','H2','H3','H4','H5','H6','LI','BLOCKQUOTE'].includes(block.tagName)) {
      block = block.parentNode;
    }
    if (block && block !== editor) {
      block.setAttribute('dir', dir);
      block.style.direction = dir;
      block.style.textAlign = dir === 'rtl' ? 'right' : 'left';
    } else {
      editor.setAttribute('dir', dir);
      editor.style.direction = dir;
    }
  }
  updateFormatState();
}

/* ── Insert Link ── */
function insertLink() {
  const sel = window.getSelection();
  if (!sel || !sel.rangeCount) return;
  const selectedText = sel.toString();
  const url = prompt('أدخل الرابط (URL):', 'https://');
  if (!url || url === 'https://') return;
  if (selectedText) {
    execFormat('createLink', url);
  } else {
    const link = document.createElement('a');
    link.href = url;
    link.textContent = url;
    link.target = '_blank';
    const range = sel.getRangeAt(0);
    range.insertNode(link);
    range.setStartAfter(link);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }
}

/* ── Line Height Cycling ── */
var _currentLineHeight = 1.8;
function cycleLineHeight() {
  const editor = getEditorElement();
  if (!editor) return;
  const heights = [1.5, 2.0, 2.5, 1.8];
  const idx = heights.indexOf(_currentLineHeight);
  _currentLineHeight = heights[(idx + 1) % heights.length];
  editor.style.lineHeight = _currentLineHeight;
  const btn = document.getElementById('fmt-line-height');
  if (btn) {
    btn.setAttribute('data-tooltip', 'ارتفاع السطر: ' + _currentLineHeight);
  }
}

/* ── Blockquote ── */
function formatBlockquote() {
  execFormat('formatBlock', 'blockquote');
}

/* ── Paragraph Spacing ── */
var _paragraphSpacing = 'normal';
function cycleParagraphSpacing() {
  const editor = getEditorElement();
  if (!editor) return;
  const modes = { tight: '0.3em', normal: '0.8em', wide: '1.5em' };
  const order = ['tight', 'normal', 'wide'];
  const idx = order.indexOf(_paragraphSpacing);
  _paragraphSpacing = order[(idx + 1) % order.length];
  const val = modes[_paragraphSpacing];
  editor.style.setProperty('--paragraph-spacing', val);
  editor.querySelectorAll('div,p').forEach(el => {
    el.style.marginBottom = val;
  });
}

/* ── Find & Replace ── */
var _findMatches = [];
var _findIdx = -1;

function openFindReplace() {
  const bar = document.getElementById('find-replace-bar');
  if (bar) {
    bar.style.display = 'block';
    document.getElementById('find-input')?.focus();
  }
}

function closeFindReplace() {
  const bar = document.getElementById('find-replace-bar');
  if (bar) bar.style.display = 'none';
  clearHighlights();
  _findMatches = [];
  _findIdx = -1;
  const countEl = document.getElementById('find-count');
  if (countEl) countEl.textContent = '0/0';
}

function toggleReplace() {
  const row = document.getElementById('replace-row');
  if (row) row.style.display = row.style.display === 'none' ? 'flex' : 'none';
}

function doFind() {
  const query = document.getElementById('find-input')?.value;
  if (!query) { clearHighlights(); return; }
  const editor = getEditorElement();
  if (!editor) return;
  clearHighlights();
  const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, null, false);
  _findMatches = [];
  let node;
  while (node = walker.nextNode()) {
    let idx = node.textContent.indexOf(query);
    while (idx !== -1) {
      _findMatches.push({ node, idx, len: query.length });
      idx = node.textContent.indexOf(query, idx + 1);
    }
  }
  // Highlight all matches
  for (let i = _findMatches.length - 1; i >= 0; i--) {
    const m = _findMatches[i];
    const range = document.createRange();
    range.setStart(m.node, m.idx);
    range.setEnd(m.node, m.idx + m.len);
    const span = document.createElement('span');
    span.className = 'find-highlight';
    range.surroundContents(span);
  }
  // Re-collect highlighted spans
  _findMatches = Array.from(editor.querySelectorAll('.find-highlight'));
  _findIdx = _findMatches.length > 0 ? 0 : -1;
  updateFindCount();
  if (_findIdx >= 0) highlightCurrent();
}

function findNext() {
  if (_findMatches.length === 0) { doFind(); return; }
  _findIdx = (_findIdx + 1) % _findMatches.length;
  updateFindCount();
  highlightCurrent();
}

function findPrev() {
  if (_findMatches.length === 0) { doFind(); return; }
  _findIdx = (_findIdx - 1 + _findMatches.length) % _findMatches.length;
  updateFindCount();
  highlightCurrent();
}

function highlightCurrent() {
  _findMatches.forEach((el, i) => {
    el.classList.toggle('find-highlight--active', i === _findIdx);
  });
  if (_findMatches[_findIdx]) {
    _findMatches[_findIdx].scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
}

function updateFindCount() {
  const el = document.getElementById('find-count');
  if (el) el.textContent = _findMatches.length > 0 ? `${_findIdx + 1}/${_findMatches.length}` : '0/0';
}

function replaceCurrent() {
  if (_findIdx < 0 || !_findMatches[_findIdx]) return;
  const replaceVal = document.getElementById('replace-input')?.value || '';
  _findMatches[_findIdx].textContent = replaceVal;
  _findMatches[_findIdx].className = '';
  _findMatches.splice(_findIdx, 1);
  if (_findIdx >= _findMatches.length) _findIdx = 0;
  updateFindCount();
  if (_findMatches.length > 0) highlightCurrent();
}

function replaceAll() {
  const replaceVal = document.getElementById('replace-input')?.value || '';
  _findMatches.forEach(el => {
    el.textContent = replaceVal;
    el.className = '';
  });
  _findMatches = [];
  _findIdx = -1;
  updateFindCount();
}

function clearHighlights() {
  const editor = getEditorElement();
  if (!editor) return;
  editor.querySelectorAll('.find-highlight').forEach(el => {
    const parent = el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent), el);
    parent.normalize();
  });
}

/* ── Focus Mode ── */
var _focusMode = false;
function toggleFocusMode() {
  _focusMode = !_focusMode;
  document.body.classList.toggle('focus-mode', _focusMode);
  const btn = document.getElementById('focus-mode-btn');
  if (btn) btn.classList.toggle('fmt-active', _focusMode);
}

/* ── Typewriter Mode ── */
var _typewriterMode = false;
function toggleTypewriterMode() {
  _typewriterMode = !_typewriterMode;
  const editor = getEditorElement();
  if (!editor) return;
  editor.classList.toggle('typewriter-mode', _typewriterMode);
  if (_typewriterMode) {
    editor.addEventListener('input', typewriterScroll);
    editor.addEventListener('click', typewriterScroll);
  } else {
    editor.removeEventListener('input', typewriterScroll);
    editor.removeEventListener('click', typewriterScroll);
  }
}
function typewriterScroll() {
  const sel = window.getSelection();
  if (!sel.rangeCount) return;
  const range = sel.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  const editor = getEditorElement();
  if (!editor) return;
  const editorRect = editor.getBoundingClientRect();
  const middle = editorRect.height / 2;
  const offset = rect.top - editorRect.top - middle;
  editor.scrollTop += offset;
}

/* ── Version History ── */
function saveVersion() {
  const editor = getEditorElement();
  if (!editor) return;
  const versions = JSON.parse(localStorage.getItem('bayan_versions') || '[]');
  versions.push({
    timestamp: Date.now(),
    content: editor.innerHTML,
    preview: editor.textContent.substring(0, 50)
  });
  // Keep last 20 versions
  if (versions.length > 20) versions.shift();
  localStorage.setItem('bayan_versions', JSON.stringify(versions));
}

function showVersionHistory() {
  const versions = JSON.parse(localStorage.getItem('bayan_versions') || '[]');
  if (!versions.length) { alert('لا توجد نسخ سابقة'); return; }
  let msg = 'اختر نسخة للاستعادة:\n\n';
  versions.forEach((v, i) => {
    const date = new Date(v.timestamp);
    msg += `${i + 1}. ${date.toLocaleString('ar-EG')} — "${v.preview}..."\n`;
  });
  const choice = prompt(msg + '\nأدخل رقم النسخة:');
  if (!choice) return;
  const idx = parseInt(choice) - 1;
  if (idx >= 0 && idx < versions.length) {
    const editor = getEditorElement();
    if (editor) {
      pushUndoState();
      editor.innerHTML = versions[idx].content;
    }
  }
}

/* ── Collaboration Hints (last edit timestamp) ── */
var _lastEditTime = null;
function updateLastEditTime() {
  _lastEditTime = Date.now();
  updateCollabHint();
}
function updateCollabHint() {
  const el = document.getElementById('last-edit-hint');
  if (!el || !_lastEditTime) return;
  const diff = Math.floor((Date.now() - _lastEditTime) / 1000);
  if (diff < 5) el.textContent = 'الآن';
  else if (diff < 60) el.textContent = `منذ ${diff} ثانية`;
  else if (diff < 3600) el.textContent = `منذ ${Math.floor(diff/60)} دقيقة`;
  else el.textContent = `منذ ${Math.floor(diff/3600)} ساعة`;
}

/* ── Tashkeel (Diacritics) ── */
function addTashkeel() {
  // This adds basic tashkeel placeholder — real implementation needs NLP
  alert('ميزة التشكيل التلقائي قيد التطوير. سيتم إضافتها قريباً.');
}
function removeTashkeel() {
  const editor = getEditorElement();
  if (!editor) return;
  pushUndoState();
  const diacritics = /[\u064B-\u065F\u0670\u06D6-\u06ED]/g;
  // Walk through text nodes only
  const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, null, false);
  let node;
  while (node = walker.nextNode()) {
    const cleaned = node.textContent.replace(diacritics, '');
    if (cleaned !== node.textContent) {
      node.textContent = cleaned;
    }
  }
}

/* ── Number Conversion (Arabic ↔ Hindi) ── */
function convertToHindiNumerals() {
  const editor = getEditorElement();
  if (!editor) return;
  pushUndoState();
  const map = {'0':'٠','1':'١','2':'٢','3':'٣','4':'٤','5':'٥','6':'٦','7':'٧','8':'٨','9':'٩'};
  fmtWalkTextNodes(editor, text => text.replace(/[0-9]/g, d => map[d]));
}
function convertToArabicNumerals() {
  const editor = getEditorElement();
  if (!editor) return;
  pushUndoState();
  const map = {'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9'};
  fmtWalkTextNodes(editor, text => text.replace(/[٠-٩]/g, d => map[d]));
}
function fmtWalkTextNodes(root, fn) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
  let node;
  while (node = walker.nextNode()) {
    const result = fn(node.textContent);
    if (result !== node.textContent) node.textContent = result;
  }
}

/* ── Text Cleanup ── */
function cleanupText() {
  const editor = getEditorElement();
  if (!editor) return;
  pushUndoState();
  fmtWalkTextNodes(editor, text => {
    return text
      .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, '') // Remove diacritics
      .replace(/\u200C/g, '') // Remove ZWNJ
      .replace(/\u200D/g, '') // Remove ZWJ
      .replace(/\u00A0/g, ' ') // NBSP → space
      .replace(/ {2,}/g, ' ') // Multiple spaces → one
      .replace(/\n{3,}/g, '\n\n'); // Multiple newlines → two
  });
}

/* ── Error Badge Update ── */
function updateErrorBadge() {
  const badge = document.getElementById('error-badge');
  if (!badge) return;
  const s = parseInt(document.getElementById('spelling-count')?.textContent) || 0;
  const g = parseInt(document.getElementById('grammar-count')?.textContent) || 0;
  const p = parseInt(document.getElementById('punctuation-count')?.textContent) || 0;
  const total = s + g + p;
  if (total > 0) {
    badge.textContent = total;
    badge.style.display = 'inline-flex';
  } else {
    badge.style.display = 'none';
  }
}

/* ── Paragraph Count ── */
function updateParagraphCount() {
  const editor = getEditorElement();
  if (!editor) return;
  const text = editor.textContent || '';
  const paras = text.split(/\n\s*\n/).filter(p => p.trim().length > 0);
  const count = text.trim().length > 0 ? Math.max(1, paras.length) : 0;
  const el = document.getElementById('paragraph-count');
  if (el) el.textContent = count.toLocaleString('ar-EG');
}

/* ── Tab Keyboard Shortcuts ── */
function initTabShortcuts() {
  document.addEventListener('keydown', (e) => {
    if (e.altKey && !e.ctrlKey) {
      if (e.key === '1') { e.preventDefault(); switchTab('write'); }
      else if (e.key === '2') { e.preventDefault(); switchTab('summarize'); }
      else if (e.key === '3') { e.preventDefault(); switchTab('dialect'); }
      else if (e.key === '4') { e.preventDefault(); switchTab('quran'); }
    }
    // Ctrl+H for Find & Replace
    if (e.ctrlKey && e.key === 'h') {
      e.preventDefault();
      openFindReplace();
    }
    // Ctrl+Shift+F for Focus Mode
    if (e.ctrlKey && e.shiftKey && e.key === 'F') {
      e.preventDefault();
      toggleFocusMode();
    }
    // Ctrl+K for link
    if (e.ctrlKey && e.key === 'k') {
      e.preventDefault();
      insertLink();
    }
  });
}

/* ── Font Hover Preview ── */
function initFontHoverPreview() {
  document.querySelectorAll('#fmt-font-menu .fmt-dropdown__item').forEach(item => {
    item.addEventListener('mouseenter', () => {
      const label = document.getElementById('fmt-font-label');
      if (label) label.style.fontFamily = item.dataset.font;
    });
    item.addEventListener('mouseleave', () => {
      const label = document.getElementById('fmt-font-label');
      if (label) label.style.fontFamily = '';
    });
  });
}

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

  // Lists
  const listMap = {
    'fmt-ul': 'insertUnorderedList',
    'fmt-ol': 'insertOrderedList',
  };
  Object.entries(listMap).forEach(([id, command]) => {
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

  // Close dropdowns on Escape + keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllFmtDropdowns();

    // ArrowDown/ArrowUp navigation inside open dropdowns
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const openDropdown = document.querySelector('.fmt-dropdown.open .fmt-dropdown__menu');
      if (!openDropdown) return;
      e.preventDefault();
      const items = Array.from(openDropdown.querySelectorAll('.fmt-dropdown__item'));
      if (!items.length) return;
      const focused = document.activeElement;
      const idx = items.indexOf(focused);
      let next;
      if (e.key === 'ArrowDown') {
        next = idx < items.length - 1 ? idx + 1 : 0;
      } else {
        next = idx > 0 ? idx - 1 : items.length - 1;
      }
      items[next].focus();
    }
  });

  // Item 8: Color pickers
  initColorPicker('fmt-textcolor', 'foreColor', 'fmt-textcolor-bar');
  initColorPicker('fmt-highlight', 'hiliteColor', 'fmt-highlight-bar');

  // Tab keyboard shortcuts (Alt+1/2/3/4, Ctrl+H, Ctrl+Shift+F, Ctrl+K)
  initTabShortcuts();

  // Font hover preview
  initFontHoverPreview();

  // Find input listener
  const findInput = document.getElementById('find-input');
  if (findInput) {
    findInput.addEventListener('input', doFind);
    findInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.shiftKey ? findPrev() : findNext(); }
      if (e.key === 'Escape') closeFindReplace();
    });
  }

  // Auto-save version every 2 minutes
  setInterval(() => {
    const ed = getEditorElement();
    if (ed && ed.textContent.trim().length > 10) saveVersion();
  }, 120000);

  // Collaboration hint updater every 30s
  setInterval(updateCollabHint, 30000);

  // Hook editor input for error badge + paragraph count + last edit time
  if (editor) {
    const origInputHandler = editor.oninput;
    editor.addEventListener('input', () => {
      updateParagraphCount();
      updateLastEditTime();
      // Delay badge update to let analysis finish
      setTimeout(updateErrorBadge, 2000);
    });
  }
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

  // Build swatches — add reset button first
  const resetSwatch = document.createElement('button');
  resetSwatch.type = 'button';
  resetSwatch.className = 'fmt-color-swatch fmt-color-swatch--reset';
  resetSwatch.title = '\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0627\u0641\u062a\u0631\u0627\u0636\u064a';
  resetSwatch.textContent = '\u00d7';
  resetSwatch.addEventListener('click', () => {
    document.execCommand('removeFormat', false, null);
    const bar = document.getElementById(barId);
    if (bar) bar.style.background = command === 'foreColor' ? '#ECEEF2' : 'transparent';
    closeAllFmtDropdowns();
    const editor = getEditorElement();
    if (editor) editor.focus();
  });
  grid.appendChild(resetSwatch);

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

/* ── Error Filtering (Sidebar tabs) ── */
var _currentErrorFilter = 'all';
function filterErrors(type) {
  _currentErrorFilter = type;
  // Update tab active state
  document.querySelectorAll('.error-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.filter === type);
  });
  // Filter suggestion items
  document.querySelectorAll('#suggestions-list .suggestion-item, #suggestions-list .sugg-card').forEach(item => {
    if (type === 'all') {
      item.style.display = '';
    } else {
      const itemType = item.dataset.type || item.getAttribute('data-error-type') || '';
      item.style.display = itemType.includes(type) ? '' : 'none';
    }
  });
  // Show/hide dismiss button
  const dismissBtn = document.getElementById('dismiss-filtered-btn');
  if (dismissBtn) dismissBtn.classList.toggle('is-hidden', type === 'all');
}

function dismissAllFiltered() {
  const type = _currentErrorFilter;
  if (type === 'all') return;
  document.querySelectorAll('#suggestions-list .suggestion-item, #suggestions-list .sugg-card').forEach(item => {
    const itemType = item.dataset.type || item.getAttribute('data-error-type') || '';
    if (itemType.includes(type)) {
      item.remove();
    }
  });
}

/* ── Error Breakdown Chart (SVG Donut) ── */
function renderErrorChart() {
  const container = document.getElementById('error-chart');
  if (!container) return;
  const s = parseInt(document.getElementById('spelling-count')?.textContent) || 0;
  const g = parseInt(document.getElementById('grammar-count')?.textContent) || 0;
  const p = parseInt(document.getElementById('punctuation-count')?.textContent) || 0;
  const total = s + g + p;
  if (total === 0) {
    container.innerHTML = '';
    return;
  }
  const r = 30, cx = 40, cy = 40, c = 2 * Math.PI * r;
  const segments = [
    { val: s, color: '#ef4444', label: 'إملائي' },
    { val: g, color: '#f59e0b', label: 'نحوي' },
    { val: p, color: '#22c55e', label: 'ترقيم' },
  ].filter(seg => seg.val > 0);
  let offset = 0;
  let paths = '';
  segments.forEach(seg => {
    const pct = seg.val / total;
    const dash = c * pct;
    const gap = c - dash;
    paths += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${seg.color}" stroke-width="8" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-offset}" opacity="0.85"/>`;
    offset += dash;
  });
  let legend = segments.map(seg => `<span class="chart-legend-item"><span class="chart-dot" style="background:${seg.color}"></span>${seg.label}: ${seg.val}</span>`).join('');
  container.innerHTML = `<svg width="80" height="80" viewBox="0 0 80 80" class="error-donut">${paths}<text x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="central" fill="var(--color-text-primary)" font-size="14" font-weight="700">${total}</text></svg><div class="chart-legend">${legend}</div>`;
}

/* ── Score History (Sparkline) ── */
var _scoreHistory = [];
function trackScore(score) {
  _scoreHistory.push(score);
  if (_scoreHistory.length > 20) _scoreHistory.shift();
  renderSparkline();
}
function renderSparkline() {
  const container = document.getElementById('score-sparkline');
  if (!container || _scoreHistory.length < 2) return;
  const w = 120, h = 30;
  const max = Math.max(..._scoreHistory, 100);
  const min = Math.min(..._scoreHistory, 0);
  const range = max - min || 1;
  const points = _scoreHistory.map((v, i) => {
    const x = (i / (_scoreHistory.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(' ');
  container.innerHTML = `<svg width="${w}" height="${h}" class="sparkline"><polyline points="${points}" fill="none" stroke="var(--color-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
