// L4 — Service worker registration
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(function() {});
}

// Toast notification system
function showToast(message, type = 'success', duration = 2500) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast toast--' + type;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('toast-out');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Custom confirmation dialog (replaces window.confirm)
function showConfirmDialog(title, message, onConfirm) {
  var overlay = document.createElement('div');
  overlay.className = 'confirm-dialog-overlay';
  var dialog = document.createElement('div');
  dialog.className = 'confirm-dialog';
  dialog.dir = 'rtl';
  var titleEl = document.createElement('div');
  titleEl.className = 'confirm-dialog__title';
  titleEl.textContent = title;
  var msgEl = document.createElement('div');
  msgEl.className = 'confirm-dialog__message';
  msgEl.textContent = message;
  var actions = document.createElement('div');
  actions.className = 'confirm-dialog__actions';
  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'confirm-dialog__btn';
  cancelBtn.textContent = 'إلغاء';
  var okBtn = document.createElement('button');
  okBtn.className = 'confirm-dialog__btn confirm-dialog__btn--danger';
  okBtn.textContent = 'تأكيد';
  actions.appendChild(cancelBtn);
  actions.appendChild(okBtn);
  dialog.appendChild(titleEl);
  dialog.appendChild(msgEl);
  dialog.appendChild(actions);
  overlay.appendChild(dialog);
  document.body.appendChild(overlay);
  cancelBtn.onclick = function() { overlay.remove(); };
  okBtn.onclick = function() { overlay.remove(); if (onConfirm) onConfirm(); };
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.addEventListener('keydown', function _esc(e) {
    if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', _esc); }
  });
}

// Scroll to top
(function() {
  const btn = document.getElementById('scroll-top-btn');
  const sc = document.querySelector('.h-full.overflow-auto') || document.documentElement;
  if (!btn) return;
  const target = sc === document.documentElement ? window : sc;
  (sc === document.documentElement ? window : sc).addEventListener('scroll', () => {
    const st = sc === document.documentElement ? window.scrollY : sc.scrollTop;
    btn.classList.toggle('visible', st > 400);
    const nav = document.querySelector('.site-nav');
    if (nav) nav.classList.toggle('nav-scrolled', st > 20);
  });
  btn.addEventListener('click', () => {
    (sc === document.documentElement ? window : sc).scrollTo({ top: 0, behavior: 'smooth' });
  });
})();

// Default configuration
const defaultConfig = {
  brand_name: 'بيان',
  hero_headline: 'اكتب العربية بثقة واحتراف',
  hero_subheadline: 'منصة ذكاء اصطناعي متكاملة لتصحيح الإملاء والنحو والترقيم وتلخيص النصوص والإكمال التلقائي — مصمّمة خصيصًا للغة العربية.',
  cta_primary: 'ابدأ الكتابة مجانًا',
  primary_color: '#6BA3E0',
  secondary_color: '#A594E8',
  font_family: 'Cairo',
  font_size: 16
};

let config = { ...defaultConfig };

// Page navigation
function showPage(pageId) {
  document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');

  document.querySelectorAll('.nav-link, .mobile-drawer-link').forEach(link => {
    link.classList.remove('active');
  });

  document.querySelectorAll(`[data-page="${pageId}"]`).forEach(link => {
    link.classList.add('active');
  });

  try {
    sessionStorage.setItem('bayan_current_page', pageId);
  } catch (e) {}

  window.scrollTo(0, 0);
}


function switchTab(tab) {
  const tabs = ['write', 'summarize', 'dialect', 'quran'];
  const formatToolbar = document.getElementById('format-toolbar');
  tabs.forEach(function(t) {
    var tabEl = document.getElementById(t + '-tab');
    var areaEl = document.getElementById(t + '-area') || document.getElementById(t === 'write' ? 'write-area' : t + '-area');
    if (tabEl) tabEl.classList.remove('active');
    if (areaEl) areaEl.classList.add('is-hidden');
  });
  var activeTab = document.getElementById(tab + '-tab');
  var activeArea = document.getElementById(tab === 'write' ? 'write-area' : tab + '-area');
  if (activeTab) activeTab.classList.add('active');
  if (activeArea) activeArea.classList.remove('is-hidden');
  if (formatToolbar) formatToolbar.style.display = (tab === 'write') ? '' : 'none';
  var sidebar = document.querySelector('.sidebar-panel.sidebar-desktop');
  if (sidebar) sidebar.style.display = (tab === 'write') ? '' : 'none';
  var mobileTrigger = document.getElementById('mobile-sheet-trigger');
  if (mobileTrigger) mobileTrigger.style.display = (tab === 'write') ? '' : 'none';
  var docsPanel = document.querySelector('.docs-panel-desktop');
  if (docsPanel) docsPanel.style.display = (tab === 'write') ? '' : 'none';
  var editorLayout = document.querySelector('.editor-layout');
  if (editorLayout) {
    if (tab === 'write') {
      editorLayout.classList.remove('tools-mode');
    } else {
      editorLayout.classList.add('tools-mode');
    }
  }
}

/* ═══════════════════════════════════════════
   Summarize — File Import
   ═══════════════════════════════════════════ */
window._summarySource = 'custom';
function setSummarySource() {}

function importSummaryFile(inputEl) {
  if (!inputEl || !inputEl.files || !inputEl.files[0]) return;
  var file = inputEl.files[0];
  var ta = document.getElementById('summary-custom-input');
  if (!ta) return;

  if (file.name.endsWith('.txt')) {
    var reader = new FileReader();
    reader.onload = function(e) {
      ta.value = e.target.result;
      if (typeof showToast === 'function') showToast('✓ تم استيراد الملف');
    };
    reader.readAsText(file, 'UTF-8');
  } else if (file.name.endsWith('.docx')) {
    loadVendorScript('/js/vendor/mammoth.browser.min.js').then(function() {
      var reader = new FileReader();
      reader.onload = function(e) {
        mammoth.extractRawText({ arrayBuffer: e.target.result })
          .then(function(result) { ta.value = result.value; if (typeof showToast === 'function') showToast('✓ تم استيراد الملف'); })
          .catch(function() { if (typeof showToast === 'function') showToast('خطأ في قراءة الملف', 'error'); });
      };
      reader.readAsArrayBuffer(file);
    }).catch(function() {
      if (typeof showToast === 'function') showToast('تعذّر تحميل مكتبة Word', 'error');
    });
  }
  inputEl.value = '';
}

/* ═══════════════════════════════════════════
   Floating Selection Toolbar
   ═══════════════════════════════════════════ */
(function() {
  var selBar = null;
  var hideTimer = null;
  function showSelectionBar() {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) { hideSelectionBar(); return; }
    var editor = document.getElementById('editor-container');
    if (!editor || !editor.contains(sel.anchorNode)) { hideSelectionBar(); return; }
    if (!selBar) selBar = document.getElementById('selection-toolbar');
    if (!selBar) return;
    var range = sel.getRangeAt(0);
    var rect = range.getBoundingClientRect();
    selBar.style.top = (rect.top + window.scrollY - 48) + 'px';
    selBar.style.left = (rect.left + rect.width / 2) + 'px';
    selBar.classList.remove('is-hidden');
  }
  function hideSelectionBar() {
    if (!selBar) selBar = document.getElementById('selection-toolbar');
    if (selBar) selBar.classList.add('is-hidden');
  }
  document.addEventListener('selectionchange', function() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function() {
      var sel = window.getSelection();
      if (sel && !sel.isCollapsed && sel.toString().trim().length > 2) {
        var editor = document.getElementById('editor-container');
        if (editor && editor.contains(sel.anchorNode)) { showSelectionBar(); return; }
      }
      hideSelectionBar();
    }, 300);
  });
  document.addEventListener('mousedown', function(e) {
    if (!selBar) selBar = document.getElementById('selection-toolbar');
    if (selBar && !selBar.contains(e.target)) hideSelectionBar();
  });
})();

function selectionToolAction(tool) {
  var sel = window.getSelection();
  var text = sel ? sel.toString().trim() : '';
  if (!text) { if (typeof showToast === 'function') showToast('حدد نصًا أولاً', 'warning'); return; }
  var selBar = document.getElementById('selection-toolbar');
  if (selBar) selBar.classList.add('is-hidden');
  if (tool === 'summarize') {
    switchTab('summarize');
    var ta = document.getElementById('summary-custom-input');
    if (ta) { ta.value = text; }
  } else if (tool === 'dialect') {
    switchTab('dialect');
    var ta = document.getElementById('dialect-input');
    if (ta) { ta.value = text; if (typeof updateDialectCharCount === 'function') updateDialectCharCount(); }
  } else if (tool === 'quran') {
    switchTab('quran');
    var ta = document.getElementById('quran-input');
    if (ta) ta.value = text;
  }
}

/* ═══════════════════════════════════════════
   Quran Standalone Panel Functions
   ═══════════════════════════════════════════ */
let _quranInlineVerse = '';
let _quranInlineRef = '';
let _quranInlineQuery = '';

async function searchQuranStandalone() {
  if (typeof _bayanAnalytics !== 'undefined') _bayanAnalytics.track('quran');
  var input = document.getElementById('quran-input').value.trim();
  if (!input) { if (typeof showToast === 'function') showToast('الرجاء كتابة نص قرآني أولاً', 'warning'); return; }
  _quranInlineQuery = input;
  var resultDiv = document.getElementById('quran-inline-result');
  var uthmaniEl = document.getElementById('quran-inline-uthmani');
  var refEl = document.getElementById('quran-inline-reference');
  var searchBtn = document.getElementById('quran-search-btn');
  uthmaniEl.innerHTML = '<span class="text-secondary">⏳ جاري البحث...</span>';
  refEl.textContent = '';
  resultDiv.classList.remove('is-hidden');
  document.getElementById('quran-inline-translation').classList.add('is-hidden');
  document.getElementById('quran-inline-lang').value = '';
  if (searchBtn) { searchBtn.disabled = true; searchBtn.textContent = '⏳ جاري البحث...'; }
  var _abortCtrl = new AbortController();
  var _timeout = setTimeout(function(){ _abortCtrl.abort(); }, 30000);
  try {
    var res = await fetch('/api/quran', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input, language: 'تدقيق الايات' }),
      signal: _abortCtrl.signal
    });
    var data = await res.json();
    if (data.error) {
      uthmaniEl.innerHTML = '<span class="text-secondary">' + data.error.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</span>';
      return;
    }
    var seg = data.matched_segment || '';
    var refMatch = seg.match(/【([^】]+)】/);
    var verseText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
    var reference = refMatch ? refMatch[1] : '';
    _quranInlineVerse = verseText;
    _quranInlineRef = reference;
    uthmaniEl.textContent = verseText;
    refEl.textContent = reference ? '[' + reference + ']' : '';
  } catch (err) {
    var msg = err.name === 'AbortError' ? 'انتهى وقت الانتظار — حاول مرة أخرى' : 'حدث خطأ أثناء البحث — تأكد من الاتصال';
    uthmaniEl.innerHTML = '<span class="text-secondary">' + msg + '</span>';
  } finally {
    clearTimeout(_timeout);
    if (searchBtn) { searchBtn.disabled = false; searchBtn.textContent = 'بحث وتدقيق'; }
  }
}

let _quranInlineTransText = '';
let _quranInlineTransRef = '';

async function translateQuranInline() {
  var lang = document.getElementById('quran-inline-lang').value;
  if (!lang || !_quranInlineQuery) return;
  var resultDiv = document.getElementById('quran-inline-translation');
  var textEl = document.getElementById('quran-inline-trans-text');
  var refEl = document.getElementById('quran-inline-trans-ref');
  var actionsEl = document.getElementById('quran-inline-trans-actions');
  textEl.innerHTML = '<span class="text-secondary">⏳ جاري الترجمة...</span>';
  if (refEl) refEl.style.display = 'none';
  if (actionsEl) actionsEl.style.display = 'none';
  resultDiv.classList.remove('is-hidden');
  var _abortCtrl = new AbortController();
  var _timeout = setTimeout(function(){ _abortCtrl.abort(); }, 30000);
  try {
    var res = await fetch('/api/quran', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: _quranInlineQuery, language: lang }),
      signal: _abortCtrl.signal
    });
    var data = await res.json();
    if (data.error) {
      textEl.innerHTML = '<span class="text-secondary">' + data.error.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</span>';
      return;
    }
    var seg = data.matched_segment || '';
    var refMatch = seg.match(/【([^】]+)】/);
    var transText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
    var transRef = refMatch ? refMatch[1] : '';
    _quranInlineTransText = transText;
    _quranInlineTransRef = transRef;
    textEl.textContent = transText;
    if (refEl && transRef) { refEl.textContent = '[' + transRef + ']'; refEl.style.display = ''; }
    if (actionsEl) actionsEl.style.display = '';
  } catch (err) {
    var msg = err.name === 'AbortError' ? 'انتهى وقت الانتظار' : 'حدث خطأ في الترجمة';
    textEl.innerHTML = '<span class="text-secondary">' + msg + '</span>';
  } finally { clearTimeout(_timeout); }
}

function copyQuranInlineResult() {
  var text = (_quranInlineVerse || '') + (_quranInlineRef ? ' [' + _quranInlineRef + ']' : '');
  if (!text.trim()) return;
  navigator.clipboard.writeText(text).then(function() {
    if (typeof showToast === 'function') showToast('✓ تم نسخ النص المدقق');
  });
}

function copyQuranInlineTranslation() {
  var text = (_quranInlineTransText || '') + (_quranInlineTransRef ? ' [' + _quranInlineTransRef + ']' : '');
  if (!text.trim()) return;
  navigator.clipboard.writeText(text).then(function() {
    if (typeof showToast === 'function') showToast('✓ تم نسخ الترجمة');
  });
}

function _replaceQueryInEditor(newText, ref) {
  var editor = document.getElementById('editor-container');
  if (!editor) return false;
  var plain = editor.textContent || '';
  var query = _quranInlineQuery || '';
  var idx = plain.indexOf(query);
  if (idx === -1) return false;
  if (typeof pushUndoState === 'function') pushUndoState();
  var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  var before = plain.substring(0, idx);
  var after = plain.substring(idx + query.length);
  var refHTML = ref ? ' <span class="quran-ref-inline">[' + esc(ref) + ']</span>' : '';
  editor.innerHTML = esc(before) +
    '<span class="quran-applied" contenteditable="false" data-quran="true">' +
    esc(newText) + refHTML + '</span>' + esc(after);
  editor.focus();
  editor.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
}

function applyQuranInlineResult() {
  if (!_quranInlineVerse) return;
  var editor = document.getElementById('editor-container');
  if (!editor) return;
  if (_quranInlineQuery && _replaceQueryInEditor(_quranInlineVerse, _quranInlineRef)) {
    switchTab('write');
    if (typeof showToast === 'function') showToast('✓ تم استبدال النص بالنص القرآني المدقق');
  } else {
    if (typeof pushUndoState === 'function') pushUndoState();
    var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
    var refHTML = _quranInlineRef ? ' <span class="quran-ref-inline">[' + esc(_quranInlineRef) + ']</span>' : '';
    var existing = editor.innerHTML;
    editor.innerHTML = existing + (existing ? '<br>' : '') +
      '<span class="quran-applied" contenteditable="false" data-quran="true">' +
      esc(_quranInlineVerse) + refHTML + '</span>';
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    switchTab('write');
    if (typeof showToast === 'function') showToast('✓ تم إضافة النص القرآني في المحرر');
  }
}

function applyQuranInlineTranslation() {
  if (!_quranInlineTransText) return;
  var editor = document.getElementById('editor-container');
  if (!editor) return;
  if (_quranInlineQuery) {
    var plain = editor.textContent || '';
    var idx = plain.indexOf(_quranInlineQuery);
    if (idx !== -1) {
      if (typeof pushUndoState === 'function') pushUndoState();
      var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
      var before = plain.substring(0, idx);
      var after = plain.substring(idx + _quranInlineQuery.length);
      var refHTML = _quranInlineTransRef ? ' <span class="quran-ref-inline">[' + esc(_quranInlineTransRef) + ']</span>' : '';
      editor.innerHTML = esc(before) + esc(_quranInlineTransText) + refHTML + esc(after);
      editor.focus();
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      switchTab('write');
      if (typeof showToast === 'function') showToast('✓ تم تطبيق الترجمة في المحرر');
      return;
    }
  }
  if (typeof pushUndoState === 'function') pushUndoState();
  var esc2 = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  var existing = editor.innerHTML;
  editor.innerHTML = existing + (existing ? '<br>' : '') + esc2(_quranInlineTransText);
  editor.dispatchEvent(new Event('input', { bubbles: true }));
  switchTab('write');
  if (typeof showToast === 'function') showToast('✓ تم إضافة الترجمة في المحرر');
}

let _dialectResult = '';
let _dialectInput = '';

async function convertDialect() {
  if (typeof _bayanAnalytics !== 'undefined') _bayanAnalytics.track('dialect');
  var input = document.getElementById('dialect-input').value.trim();
  if (!input) { if (typeof showToast === 'function') showToast('الرجاء كتابة نص أولاً', 'warning'); return; }
  _dialectInput = input;

  var resultCard = document.getElementById('dialect-result-card');
  var resultDiv = document.getElementById('dialect-result');
  var applyBtn = document.getElementById('dialect-apply-btn');
  var convertBtn = document.getElementById('dialect-convert-btn');
  resultDiv.innerHTML = '<p class="text-secondary text-center">⏳ جاري التحويل...</p>';
  resultCard.classList.remove('is-hidden');
  if (applyBtn) applyBtn.classList.add('is-hidden');
  if (convertBtn) { convertBtn.disabled = true; convertBtn.textContent = '⏳ جاري التحويل...'; }

  var _abortCtrl = new AbortController();
  var _timeout = setTimeout(function(){ _abortCtrl.abort(); }, 30000);
  try {
    var resp = await fetch('/api/dialect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input }),
      signal: _abortCtrl.signal
    });
    var data = await resp.json();
    if (data.status === 'success' && data.converted_text) {
      _dialectResult = data.converted_text;
      var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
      resultDiv.innerHTML = '<p style="font-size:20px; line-height:2; direction:rtl; text-align:center;">' + esc(data.converted_text) + '</p>';
      if (applyBtn) applyBtn.classList.remove('is-hidden');
    } else {
      _dialectResult = '';
      var errMsg = (data.error || 'حدث خطأ أثناء التحويل').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      resultDiv.innerHTML = '<p class="text-secondary text-center">' + errMsg + '</p>';
    }
  } catch (err) {
    _dialectResult = '';
    var msg = err.name === 'AbortError' ? 'انتهى وقت الانتظار — حاول مرة أخرى' : 'حدث خطأ — تأكد من الاتصال';
    resultDiv.innerHTML = '<p class="text-secondary text-center">' + msg + '</p>';
  } finally {
    clearTimeout(_timeout);
    if (convertBtn) { convertBtn.disabled = false; convertBtn.textContent = 'تحويل إلى الفصحى'; }
  }
}

function copyDialectResult() {
  if (!_dialectResult) { var t = document.getElementById('dialect-result'); if (t) navigator.clipboard.writeText(t.innerText); }
  else navigator.clipboard.writeText(_dialectResult);
  if (typeof showToast === 'function') showToast('✓ تم النسخ');
}

function applyDialectResult() {
  if (!_dialectResult) return;
  var editor = document.getElementById('editor-container');
  if (!editor) return;
  pushUndoState();
  var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  if (_dialectInput) {
    var plain = editor.textContent || '';
    var idx = plain.indexOf(_dialectInput);
    if (idx !== -1) {
      var before = plain.substring(0, idx);
      var after = plain.substring(idx + _dialectInput.length);
      editor.innerHTML = esc(before) + esc(_dialectResult) + esc(after);
      editor.focus();
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      switchTab('write');
      if (typeof showToast === 'function') showToast('✓ تم استبدال النص بالفصحى');
      return;
    }
  }
  editor.innerHTML = esc(_dialectResult);
  editor.dispatchEvent(new Event('input', { bubbles: true }));
  switchTab('write');
  if (typeof showToast === 'function') showToast('✓ تم تطبيق النص الفصيح في المحرر');
}

function updateDialectCharCount() {
  var input = document.getElementById('dialect-input');
  var counter = document.getElementById('dialect-char-count');
  if (!input || !counter) return;
  var len = input.value.length;
  var arabicLen = len.toLocaleString('ar-EG');
  counter.textContent = arabicLen + ' / ٥٬٠٠٠ حرف';
  counter.style.color = len > 5000 ? '#ef4444' : 'var(--text-secondary)';
}

/* ═══════════════════════════════════════════
   Quran Verification & Translation
   ═══════════════════════════════════════════ */
let _quranCurrentQuery = '';
let _quranSavedRange = null;
let _quranVerseClean = '';
let _quranTransClean = '';
let _quranRef = '';
let _quranTransRef = '';

async function verifyQuranText() {
  const sel = window.getSelection();
  const text = sel ? sel.toString().trim() : '';
  if (!text) {
    if (typeof showToast === 'function') showToast('علّم على النص القرآني أولاً', 'warning');
    return;
  }
  _quranSavedRange = (sel.rangeCount > 0) ? sel.getRangeAt(0).cloneRange() : null;
  _quranCurrentQuery = text;
  _quranVerseClean = '';

  const modal = document.getElementById('quran-modal');
  document.getElementById('quran-input-display').textContent = text;
  document.getElementById('quran-uthmani-text').innerHTML = '<span class="text-secondary">⏳ جاري البحث...</span>';
  document.getElementById('quran-reference').textContent = '';
  document.getElementById('quran-translation-result').classList.add('is-hidden');
  document.getElementById('quran-lang-select').value = '';
  var _applyBtn = document.getElementById('quran-apply-btn');
  var _copyBtn = document.getElementById('quran-copy-btn');
  if (_applyBtn) _applyBtn.classList.add('is-hidden');
  if (_copyBtn) _copyBtn.classList.add('is-hidden');
  modal.classList.remove('is-hidden');
  document.body.style.overflow = 'hidden';

  var _qAbort = new AbortController();
  var _qTimeout = setTimeout(function(){ _qAbort.abort(); }, 30000);
  try {
    const res = await fetch('/api/quran', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, language: 'تدقيق الايات' }),
      signal: _qAbort.signal
    });
    const data = await res.json();

    if (data.error) {
      var _escErr = data.error.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      document.getElementById('quran-uthmani-text').innerHTML =
        '<span class="text-secondary">' + _escErr + '</span>';
      return;
    }

    const seg = data.matched_segment || '';
    const refMatch = seg.match(/【([^】]+)】/);
    const verseText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
    const reference = refMatch ? refMatch[1] : '';

    _quranVerseClean = verseText;
    _quranRef = reference;
    document.getElementById('quran-uthmani-text').textContent = verseText;
    document.getElementById('quran-reference').textContent = reference ? '[' + reference + ']' : '';
    document.getElementById('quran-apply-btn').classList.remove('is-hidden');
    document.getElementById('quran-copy-btn').classList.remove('is-hidden');

  } catch (err) {
    var _qMsg = err.name === 'AbortError' ? 'انتهى وقت الانتظار — حاول مرة أخرى' : 'حدث خطأ أثناء البحث — تأكد من الاتصال';
    document.getElementById('quran-uthmani-text').innerHTML =
      '<span class="text-secondary">' + _qMsg + '</span>';
  } finally {
    clearTimeout(_qTimeout);
  }
}

async function translateQuranVerse() {
  const lang = document.getElementById('quran-lang-select').value;
  if (!lang || !_quranCurrentQuery) return;

  const resultDiv = document.getElementById('quran-translation-result');
  const textEl = document.getElementById('quran-translation-text');
  textEl.innerHTML = '<span class="text-secondary">⏳ جاري الترجمة...</span>';
  resultDiv.classList.remove('is-hidden');
  var _applyTransBtn = document.getElementById('quran-apply-trans-btn');
  var _copyTransBtn = document.getElementById('quran-copy-trans-btn');
  if (_applyTransBtn) _applyTransBtn.classList.add('is-hidden');
  if (_copyTransBtn) _copyTransBtn.classList.add('is-hidden');

  var _tAbort = new AbortController();
  var _tTimeout = setTimeout(function(){ _tAbort.abort(); }, 30000);
  try {
    const res = await fetch('/api/quran', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: _quranCurrentQuery, language: lang }),
      signal: _tAbort.signal
    });
    const data = await res.json();

    if (data.error) {
      var _escTErr = data.error.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      textEl.innerHTML = '<span class="text-secondary">' + _escTErr + '</span>';
      return;
    }

    const seg = data.matched_segment || '';
    const refMatch = seg.match(/【([^】]+)】/);
    const transText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
    const transRef = refMatch ? refMatch[1] : '';

    textEl.textContent = transText;
    _quranTransClean = transText;
    _quranTransRef = transRef;
    const refEl = document.getElementById('quran-translation-ref');
    if (refEl) {
      refEl.textContent = transRef ? '[' + transRef + ']' : '';
      refEl.style.display = transRef ? '' : 'none';
    }
    document.getElementById('quran-apply-trans-btn').classList.remove('is-hidden');
    document.getElementById('quran-copy-trans-btn').classList.remove('is-hidden');

  } catch (err) {
    var _tMsg = err.name === 'AbortError' ? 'انتهى وقت الانتظار' : 'حدث خطأ في الترجمة';
    textEl.innerHTML = '<span class="text-secondary">' + _tMsg + '</span>';
  } finally {
    clearTimeout(_tTimeout);
  }
}

function closeQuranModal() {
  document.getElementById('quran-modal').classList.add('is-hidden');
  document.body.style.overflow = '';
}

function copyQuranResult() {
  const verse = _quranVerseClean || '';
  const ref = _quranRef ? ' [' + _quranRef + ']' : '';
  const text = verse + ref;
  if (!text.trim()) return;
  navigator.clipboard.writeText(text).then(() => {
    if (typeof showToast === 'function') showToast('✓ تم نسخ النص المدقق');
    const btn = document.getElementById('quran-copy-btn');
    if (btn) { btn.textContent = '✅'; setTimeout(() => { btn.textContent = '📋'; }, 1500); }
  });
}

document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.code === 'KeyQ') {
    e.preventDefault();
    var sel = window.getSelection();
    var text = sel ? sel.toString().trim() : '';
    switchTab('quran');
    if (text) {
      var ta = document.getElementById('quran-input');
      if (ta) ta.value = text;
    }
  }
  if (e.key === 'Escape') {
    var modal = document.getElementById('quran-modal');
    if (modal && !modal.classList.contains('is-hidden')) {
      closeQuranModal();
    }
  }
});

function copyQuranTranslation() {
  const trans = _quranTransClean || '';
  const ref = _quranTransRef ? ' [' + _quranTransRef + ']' : '';
  const text = trans + ref;
  if (!text.trim()) return;
  navigator.clipboard.writeText(text).then(() => {
    if (typeof showToast === 'function') showToast('✓ تم نسخ الترجمة');
    const btn = document.getElementById('quran-copy-trans-btn');
    if (btn) { btn.textContent = '✅'; setTimeout(() => { btn.textContent = '📋'; }, 1500); }
  });
}

function _replaceInEditor(newText, ref) {
  var editor = document.getElementById('editor-container');
  if (!editor || !_quranCurrentQuery) return false;
  pushUndoState();
  closeQuranModal();
  var plain = editor.textContent || '';
  var idx = plain.indexOf(_quranCurrentQuery);
  if (idx === -1) return false;
  var before = plain.substring(0, idx);
  var after = plain.substring(idx + _quranCurrentQuery.length);
  var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  var refHTML = ref ? ' <span class="quran-ref-inline">[' + esc(ref) + ']</span>' : '';
  editor.innerHTML = esc(before) +
    '<span class="quran-applied" contenteditable="false" data-quran="true">' +
    esc(newText) + refHTML + '</span>' +
    esc(after);
  editor.focus();
  editor.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
}

function applyQuranText() {
  if (!_quranVerseClean || !_quranCurrentQuery) {
    if (typeof showToast === 'function') showToast('لا يوجد نص للتطبيق', 'warning');
    return;
  }
  if (_replaceInEditor(_quranVerseClean, _quranRef)) {
    if (typeof showToast === 'function') showToast('✓ تم تطبيق النص القرآني المدقق');
  } else {
    if (typeof showToast === 'function') showToast('لم يتم العثور على النص الأصلي', 'error');
  }
}

function applyQuranTranslation() {
  if (!_quranTransClean || !_quranCurrentQuery) {
    if (typeof showToast === 'function') showToast('لا يوجد ترجمة للتطبيق', 'warning');
    return;
  }
  if (_replaceInEditor(_quranTransClean, _quranTransRef)) {
    if (typeof showToast === 'function') showToast('✓ تم تطبيق الترجمة');
  } else {
    if (typeof showToast === 'function') showToast('لم يتم العثور على النص الأصلي', 'error');
  }
}


// Summarization functions
function updateSummaryLength() {
  var slider = document.getElementById('summary-length');
  var label = document.getElementById('summary-length-text');
  if (!slider || !label) return;
  var labels = { '1': 'طويل', '2': 'متوسط', '3': 'قصير' };
  label.textContent = labels[slider.value] || 'متوسط';
  slider.setAttribute('aria-valuetext', label.textContent);
}

let _summaryInput = '';
let _summaryResult = '';

async function generateSummary(event) {
  if (typeof _bayanAnalytics !== 'undefined') _bayanAnalytics.track('summarize');
  var customInput = document.getElementById('summary-custom-input');
  let text = customInput ? customInput.value.trim() : '';

  if (!text) {
    const summaryText = document.getElementById('summary-text');
    summaryText.innerHTML = '<p class="text-secondary text-center">الرجاء كتابة أو لصق نص في مربع الإدخال أولاً</p>';
    document.getElementById('summary-preview').classList.add('show');
    return;
  }
  _summaryInput = text;

  const lengthValue = document.getElementById('summary-length').value;
  const isFullText = false;
  const generateButton = event ? event.target : document.getElementById('generate-summary-btn');
  const summaryText = document.getElementById('summary-text');
  const summaryPreview = document.getElementById('summary-preview');

  const originalButtonText = generateButton.textContent;
  generateButton.textContent = 'جاري التوليد...';
  generateButton.disabled = true;
  summaryText.innerHTML = '<div class="summary-loading"><span class="summary-loading__spinner" aria-hidden="true"></span><p class="summary-loading__text">جاري توليد الملخص...</p></div>';
  summaryPreview.classList.add('show');

  try {
    const response = await fetch('/api/summarize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: text,
        length: parseInt(lengthValue),
        full_text: isFullText
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'حدث خطأ أثناء توليد الملخص');
    }

    if (data.status === 'success' && data.summary) {
      let summaryContent = data.summary;

      if (window._summaryMode === 'bullets') {
        const sentences = summaryContent.split(/[.،؛]\s*/).filter(s => s.trim().length > 2);
        const ul = document.createElement('ul');
        ul.style.cssText = 'list-style: disc; padding-right: 1.5rem; direction: rtl; text-align: right;';
        sentences.forEach(s => {
          const li = document.createElement('li');
          li.textContent = s.trim();
          li.style.marginBottom = '8px';
          ul.appendChild(li);
        });
        summaryText.textContent = '';
        summaryText.appendChild(ul);
      } else {
        const p = document.createElement('p');
        p.textContent = summaryContent;
        summaryText.textContent = '';
        summaryText.appendChild(p);
      }

      if (typeof updateSummaryStats === 'function') {
        updateSummaryStats(summaryContent);
      }
      _summaryResult = summaryContent;
      var applyBtn = document.getElementById('summary-apply-btn');
      if (applyBtn) applyBtn.style.display = '';
    } else {
      throw new Error(data.error || 'لم يتم توليد ملخص');
    }

  } catch (error) {
    console.error('Error generating summary:', error);
    const safeMsg = typeof escapeHtml === 'function'
      ? escapeHtml(error.message || 'تعذر توليد الملخص. يرجى المحاولة مرة أخرى.')
      : String(error.message || 'تعذر توليد الملخص. يرجى المحاولة مرة أخرى.');
    summaryText.innerHTML =
      '<div class="summary-loading">' +
        '<p class="summary-error">⚠️ حدث خطأ</p>' +
        '<p class="text-secondary text-caption">' + safeMsg + '</p>' +
        '<p class="text-muted text-label mt-2">تأكد من أن الخادم يعمل وأن النموذج محمّل بشكل صحيح.</p>' +
      '</div>';
  } finally {
    generateButton.textContent = originalButtonText;
    generateButton.disabled = false;
  }
}

function copySummary() {
  const text = document.getElementById('summary-text').innerText;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('[onclick="copySummary()"]');
    if (btn) {
      const originalText = btn.textContent;
      btn.textContent = 'تم النسخ!';
      if (typeof showToast === 'function') showToast('✓ تم نسخ الملخص');
      setTimeout(() => btn.textContent = originalText, 2000);
    }
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  });
}

function applySummaryToEditor() {
  if (!_summaryResult) return;
  var editor = document.getElementById('editor-container');
  if (!editor) return;
  if (typeof pushUndoState === 'function') pushUndoState();
  var esc = function(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  if (_summaryInput) {
    var plain = editor.textContent || '';
    var idx = plain.indexOf(_summaryInput);
    if (idx !== -1) {
      var before = plain.substring(0, idx);
      var after = plain.substring(idx + _summaryInput.length);
      editor.innerHTML = esc(before) + esc(_summaryResult) + esc(after);
      editor.focus();
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      switchTab('write');
      if (typeof showToast === 'function') showToast('✓ تم استبدال النص بالملخص');
      return;
    }
  }
  var existing = editor.innerHTML;
  editor.innerHTML = existing + (existing ? '<br>' : '') + esc(_summaryResult);
  editor.dispatchEvent(new Event('input', { bubbles: true }));
  switchTab('write');
  if (typeof showToast === 'function') showToast('✓ تم إضافة الملخص في المحرر');
}

function exportSummaryAsTxt() {
  exportSummaryAs('txt');
}

function getSummaryText() {
  return (document.getElementById('summary-text')?.innerText || '').trim();
}

async function exportSummaryAs(format) {
  const text = getSummaryText();
  if (!text) {
    if (typeof showToast === 'function') showToast('لا يوجد ملخص للتصدير', 'error');
    return;
  }

  if (format === 'txt') {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ملخص-بيان.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (typeof showToast === 'function') showToast('✓ تم تصدير الملخص');
  } else if (format === 'docx') {
    try {
      if (typeof docx === 'undefined') await loadVendorScript('/js/vendor/docx.umd.js');
      const paragraphs = text.split(/\n+/).filter(p => p.trim());
      const children = paragraphs.map(block =>
        new docx.Paragraph({
          bidirectional: true,
          alignment: docx.AlignmentType.RIGHT,
          children: [new docx.TextRun({ text: block, rightToLeft: true, font: 'Arial' })]
        })
      );
      const doc = new docx.Document({ sections: [{ properties: { rightToLeft: true }, children }] });
      const blob = await docx.Packer.toBlob(doc);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ملخص-بيان.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      if (typeof showToast === 'function') showToast('✓ تم تصدير الملخص كـ Word');
    } catch (err) {
      console.error('Summary DOCX export error:', err);
      if (typeof showToast === 'function') showToast('تعذر تصدير ملف Word', 'error');
    }
  } else if (format === 'pdf') {
    try {
      if (typeof html2pdf === 'undefined') await loadVendorScript('/js/vendor/html2pdf.bundle.min.js');
      if (typeof showToast === 'function') showToast('جاري تصدير PDF...');
      const html = buildPdfHtmlString(text);
      await html2pdf().set({
        margin: [15, 15, 15, 15],
        filename: 'ملخص-بيان.pdf',
        image: { type: 'jpeg', quality: 0.95 },
        html2canvas: { scale: 1.5, useCORS: true, backgroundColor: '#ffffff', logging: false, foreignObjectRendering: false },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      }).from(html, 'string').save();
      if (typeof showToast === 'function') showToast('✓ تم تصدير الملخص كـ PDF');
    } catch (err) {
      console.error('Summary PDF export error:', err);
      if (typeof showToast === 'function') showToast('تعذر تصدير PDF', 'error');
    }
  }

  const menu = document.getElementById('summary-export-menu');
  if (menu) menu.classList.remove('show');
}

function showAutoSaveStatus(msg) {
  const el = document.getElementById('auto-save-status');
  if (!el) return;
  el.textContent = msg;
  el.style.opacity = '1';
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.opacity = '0'; }, 3000);
}

async function setWordGoalUI() {
  const current = localStorage.getItem('bayan_word_goal') || '0';
  const input = await bayanPrompt('حدد هدف عدد الكلمات (أدخل ٠ لإلغاء الهدف):', current);
  if (input === null) return;
  const goal = parseInt(input, 10);
  if (isNaN(goal) || goal < 0) return;
  localStorage.setItem('bayan_word_goal', String(goal));
  if (typeof updateEditorStats === 'function') updateEditorStats();
  if (goal > 0) {
    if (typeof showToast === 'function') showToast('✓ تم تحديد الهدف: ' + goal + ' كلمة');
  } else {
    if (typeof showToast === 'function') showToast('تم إلغاء هدف الكلمات');
    const el = document.getElementById('word-goal-indicator');
    if (el) el.style.display = 'none';
  }
}

// Element SDK Integration
async function onConfigChange(cfg) {
  config = { ...defaultConfig, ...cfg };

  const primary = config.primary_color || defaultConfig.primary_color;
  const secondary = config.secondary_color || defaultConfig.secondary_color;
  document.documentElement.style.setProperty('--color-primary', primary);
  document.documentElement.style.setProperty('--color-secondary', secondary);
  document.documentElement.style.setProperty('--primary-color', primary);
  document.documentElement.style.setProperty('--secondary-color', secondary);

  const brandName = config.brand_name || defaultConfig.brand_name;
  const navBrand = document.getElementById('nav-brand');
  const footerBrand = document.getElementById('footer-brand');
  if (navBrand) navBrand.textContent = brandName;
  if (footerBrand) footerBrand.textContent = brandName;

  const heroHeadline = config.hero_headline || defaultConfig.hero_headline;
  const headlineEl = document.getElementById('hero-headline');
  if (headlineEl) {
    const parts = heroHeadline.split('\n');
    if (parts.length > 1) {
      headlineEl.innerHTML = parts[0] + '<br/><span class="text-gradient">' + parts[1] + '</span>';
    } else {
      headlineEl.innerHTML = heroHeadline.replace('بثقة واحتراف', '<span class="text-gradient">بثقة واحتراف</span>');
    }
  }

  const heroSubheadline = document.getElementById('hero-subheadline');
  if (heroSubheadline) {
    heroSubheadline.textContent = config.hero_subheadline || defaultConfig.hero_subheadline;
  }

  const ctaPrimary = config.cta_primary || defaultConfig.cta_primary;
  const navCta = document.getElementById('nav-cta');
  const heroCta = document.getElementById('hero-cta-primary');
  if (navCta) navCta.textContent = ctaPrimary;
  if (heroCta) heroCta.textContent = ctaPrimary;

  const fontFamily = config.font_family || defaultConfig.font_family;
  const fontSize = config.font_size || defaultConfig.font_size;
  document.body.style.fontFamily = `${fontFamily}, 'Cairo', sans-serif`;
  document.body.style.fontSize = `${fontSize}px`;
}

function mapToCapabilities(cfg) {
  return {
    recolorables: [
      {
        get: () => cfg.primary_color || defaultConfig.primary_color,
        set: (value) => { cfg.primary_color = value; window.elementSdk.setConfig({ primary_color: value }); }
      },
      {
        get: () => cfg.secondary_color || defaultConfig.secondary_color,
        set: (value) => { cfg.secondary_color = value; window.elementSdk.setConfig({ secondary_color: value }); }
      }
    ],
    borderables: [],
    fontEditable: {
      get: () => cfg.font_family || defaultConfig.font_family,
      set: (value) => { cfg.font_family = value; window.elementSdk.setConfig({ font_family: value }); }
    },
    fontSizeable: {
      get: () => cfg.font_size || defaultConfig.font_size,
      set: (value) => { cfg.font_size = value; window.elementSdk.setConfig({ font_size: value }); }
    }
  };
}

function mapToEditPanelValues(cfg) {
  return new Map([
    ['brand_name', cfg.brand_name || defaultConfig.brand_name],
    ['hero_headline', cfg.hero_headline || defaultConfig.hero_headline],
    ['hero_subheadline', cfg.hero_subheadline || defaultConfig.hero_subheadline],
    ['cta_primary', cfg.cta_primary || defaultConfig.cta_primary]
  ]);
}

// Initialize SDK
if (window.elementSdk) {
  window.elementSdk.init({
    defaultConfig,
    onConfigChange,
    mapToCapabilities,
    mapToEditPanelValues
  });
} else {
  onConfigChange(defaultConfig);
}

document.addEventListener('DOMContentLoaded', async () => {
  await initAuth();
  initTheme();
  initUI();
  initEditor();
  if (typeof initFormatToolbar === 'function') initFormatToolbar();
  if (typeof initDocSearch === 'function') initDocSearch();
  initDocuments();
  updateSuggestionsList([]);
  if (typeof SyncManager !== 'undefined') SyncManager.init();

  await initSettingsSync();
  initDocumentsCloud();
  initSummaries();
  if (typeof initOnboarding === 'function') initOnboarding();

  try {
    const savedPage = sessionStorage.getItem('bayan_current_page');
    if (savedPage) {
      showPage(savedPage);
    } else if (window.location.hash === '#/editor') {
      showPage('editor');
    } else {
      showPage('home');
    }
  } catch (e) {
    if (window.location.hash === '#/editor') {
      showPage('editor');
    } else {
      showPage('home');
    }
  }
});
