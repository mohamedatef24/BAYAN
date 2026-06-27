/**
 * Bayan Chrome Extension — Shared Core Utilities
 *
 * Functions extracted from popup.js and sidepanel.js to eliminate duplication.
 * Loaded via <script> before popup.js / sidepanel.js in their respective HTML.
 */

const BAYAN_SCORE_CIRCUMFERENCE = 440;

function updateCounts(textarea, charEl, wordEl) {
  const text = textarea.value;
  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  if (charEl) charEl.textContent = chars.toLocaleString('ar-EG');
  if (wordEl) wordEl.textContent = words.toLocaleString('ar-EG');
}

function showToast(message, duration = 2500) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('is-visible');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('is-visible'), duration);
}

function downloadTxt(text, filename) {
  if (!text) { showToast('لا يوجد نص للتنزيل'); return; }
  try {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast('✓ تم تنزيل الملف');
  } catch (e) {
    console.error('[Bayan] Download error:', e);
    showToast('تعذّر التنزيل');
  }
}

function downloadDocx(text, filename) {
  if (!text) { showToast('لا يوجد نص للتنزيل'); return; }
  try {
    var paragraphs = text.split(/\n+/).filter(function(p) { return p.trim(); });
    var xmlParts = paragraphs.map(function(p) {
      var escaped = p.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return '<w:p><w:pPr><w:bidi/><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:rtl/></w:rPr><w:t xml:space="preserve">' + escaped + '</w:t></w:r></w:p>';
    });
    var docXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
      '<w:body>' + xmlParts.join('') + '</w:body></w:document>';
    var contentTypes =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
      '</Types>';
    var rels =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
      '</Relationships>';

    if (typeof JSZip === 'undefined') {
      var script = document.createElement('script');
      script.src = chrome.runtime.getURL('vendor/jszip.min.js');
      script.onload = function() { _buildDocxZip(docXml, contentTypes, rels, filename); };
      document.head.appendChild(script);
    } else {
      _buildDocxZip(docXml, contentTypes, rels, filename);
    }
  } catch (e) {
    console.error('[Bayan] DOCX export error:', e);
    showToast('تعذّر تصدير Word');
  }
}

function _buildDocxZip(docXml, contentTypes, rels, filename) {
  var zip = new JSZip();
  zip.file('[Content_Types].xml', contentTypes);
  zip.folder('_rels').file('.rels', rels);
  zip.folder('word').file('document.xml', docXml);
  zip.generateAsync({ type: 'blob', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    .then(function(blob) {
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
      showToast('✓ تم تصدير Word');
    });
}

function updateScore(spelling, grammar, punctuation) {
  const score = calculateWritingScore(spelling, grammar, punctuation);
  const total = spelling + grammar + punctuation;

  const section = document.getElementById('score-section');
  const valueEl = document.getElementById('score-value');
  const circle = document.getElementById('score-circle');
  const hint = document.getElementById('score-hint');
  const cSpelling = document.getElementById('count-spelling');
  const cGrammar = document.getElementById('count-grammar');
  const cPunctuation = document.getElementById('count-punctuation');

  if (section) section.classList.remove('is-hidden');
  if (valueEl) valueEl.textContent = score > 0 || total > 0 ? score.toLocaleString('ar-EG') : '--';
  if (circle) {
    const offset = BAYAN_SCORE_CIRCUMFERENCE - (score / 100) * BAYAN_SCORE_CIRCUMFERENCE;
    circle.style.strokeDashoffset = String(offset);
  }
  if (hint) hint.textContent = getScoreHint(score, total);
  if (cSpelling) cSpelling.textContent = spelling.toLocaleString('ar-EG');
  if (cGrammar) cGrammar.textContent = grammar.toLocaleString('ar-EG');
  if (cPunctuation) cPunctuation.textContent = punctuation.toLocaleString('ar-EG');
}

function updateExtAuthUI(user) {
  const loginBtn = document.getElementById('btn-auth-login');
  const userInfo = document.getElementById('auth-user-info');
  const nameEl = document.getElementById('auth-name');
  const avatar = document.getElementById('auth-avatar');

  if (user && user.id) {
    if (loginBtn) loginBtn.classList.add('is-hidden');
    if (userInfo) userInfo.classList.remove('is-hidden');
    if (nameEl) nameEl.textContent = user.name || user.email || 'مستخدم';
    if (avatar && user.avatar) {
      avatar.src = user.avatar;
      avatar.classList.remove('is-hidden');
    } else if (avatar) {
      avatar.classList.add('is-hidden');
    }
  } else {
    if (loginBtn) loginBtn.classList.remove('is-hidden');
    if (userInfo) userInfo.classList.add('is-hidden');
  }
}

function bayanInitAuth() {
  const loginBtn = document.getElementById('btn-auth-login');
  const logoutBtn = document.getElementById('btn-auth-logout');

  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage({ type: 'AUTH_SIGN_IN_GOOGLE' }, (result) => {
        if (result && result.success) {
          chrome.runtime.sendMessage({ type: 'AUTH_GET_STATE' }, (state) => {
            updateExtAuthUI(state?.user);
          });
          showToast('تم تسجيل الدخول');
        } else {
          showToast('تعذّر تسجيل الدخول');
        }
      });
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage({ type: 'AUTH_SIGN_OUT' }, () => {
        updateExtAuthUI(null);
        showToast('تم تسجيل الخروج');
      });
    });
  }

  chrome.runtime.sendMessage({ type: 'AUTH_GET_STATE' }, (state) => {
    if (state) updateExtAuthUI(state.user);
  });
}
