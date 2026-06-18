// Phase 6.1 — Documents UI
// All DOM interaction for the docs sidebar.
// Uses only: getEditorText(), loadDocumentText(), documents-api, documents-state.

let _renameDocId = null;

/* ── Initialization ── */

function initDocumentsCloud() {
  _renderSidebar();
  _bindSidebarToggle();
  _bindEditorDirty();
  _loadAndRenderList();

  // Listen to auth changes — reload list when user signs in
  window.addEventListener('bayan:docstate', () => _updateTitleBar());
  window.addEventListener('bayan:authchange', () => {
    _loadAndRenderList();
  });

  // Warn user if they try to refresh with unsaved changes
  window.addEventListener('beforeunload', (e) => {
    const state = getDocState();
    if (state.hasUnsavedChanges) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  // Sync Manager UI Updates
  window.addEventListener('bayan:syncstate', (e) => {
    const { state } = e.detail;
    const saveBtn = document.getElementById('doc-save-btn');
    if (!saveBtn) return;
    
    if (state === 'saving') {
      saveBtn.title = 'جاري الحفظ...';
      saveBtn.classList.add('is-saving');
      if (typeof showAutoSaveStatus === 'function') showAutoSaveStatus('جاري الحفظ...');
    } else if (state === 'saved') {
      saveBtn.title = 'تم الحفظ';
      if (typeof showAutoSaveStatus === 'function') showAutoSaveStatus('✓ تم الحفظ');
      saveBtn.classList.remove('is-saving', 'doc-save-btn--dirty');
      saveBtn.classList.add('is-saved');
      setTimeout(() => {
        saveBtn.classList.remove('is-saved');
        const currentState = getDocState();
        saveBtn.title = currentState.hasUnsavedChanges ? 'حفظ (يوجد تغييرات غير محفوظة)' : 'حفظ';
      }, 2000);
    } else if (state === 'saved_locally') {
      saveBtn.title = 'محفوظ محلياً (أنت غير متصل)';
      saveBtn.classList.add('doc-save-btn--dirty');
    } else if (state === 'error') {
      saveBtn.title = 'خطأ في الحفظ';
      saveBtn.classList.add('doc-save-btn--dirty');
    }
  });
}

/* ── Sidebar toggle ── */

function _bindSidebarToggle() {
  const toggleBtn = document.getElementById('docs-sidebar-toggle');
  const sidebar = document.getElementById('docs-sidebar');
  if (!toggleBtn || !sidebar) return;

  toggleBtn.addEventListener('click', () => {
    const isOpen = sidebar.classList.toggle('is-open');
    toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (sidebar && sidebar.classList.contains('is-open') &&
        !sidebar.contains(e.target) &&
        !toggleBtn.contains(e.target)) {
      sidebar.classList.remove('is-open');
      toggleBtn.setAttribute('aria-expanded', 'false');
    }
  });
}

/* ── Mark dirty on editor input ── */

function _bindEditorDirty() {
  const editor = document.getElementById('editor-container');
  if (!editor) return;
  editor.addEventListener('input', () => {
    if (hasOpenDocument()) {
      markDirty();
      const state = getDocState();
      const content = getEditorText();
      if (typeof SyncManager !== 'undefined') {
        SyncManager.queueChange(state.currentDocumentId, content);
      }
    }
  });
}

/* ── Autosave Removed (Handled by SyncManager) ── */

/* ── Load & render list ── */

async function _loadAndRenderList() {
  const listEl = document.getElementById('docs-list');
  if (!listEl) return;

  const isAuthenticated = window.__bayanAuth &&
    window.__bayanAuth.userId &&
    !window.__bayanAuth.isOfflineMode;

  console.log('[DEBUG_AUTH]', JSON.stringify(window.__bayanAuth));

  if (!isAuthenticated) {
    listEl.innerHTML = `
      <div class="docs-signin-prompt">
        <p class="docs-signin-text">سجّل دخولك لحفظ مستنداتك في السحابة</p>
        <button class="btn-primary docs-signin-btn" onclick="linkGoogle()" type="button">
          الدخول بـ Google
        </button>
      </div>`;
    return;
  }

  listEl.innerHTML = `<div class="docs-loading">جاري التحميل...</div>`;
  const docs = await loadDocuments();

  if (!docs.length) {
    listEl.innerHTML = `<p class="docs-empty">لا توجد مستندات بعد. أنشئ مستنداً جديداً!</p>`;
    return;
  }

  const state = getDocState();
  listEl.innerHTML = docs.map(doc => _buildDocItemHTML(doc, doc.id === state.currentDocumentId)).join('');
  _bindDocItemEvents(listEl);
}

function _buildDocItemHTML(doc, isActive) {
  const date = new Date(doc.updated_at).toLocaleDateString('ar-EG', {
    month: 'short', day: 'numeric'
  });
  return `
    <div class="doc-list-item${isActive ? ' doc-list-item--active' : ''}" data-doc-id="${doc.id}" role="listitem">
      <button class="doc-list-item__open" data-doc-id="${doc.id}" aria-label="فتح ${_escapeAttr(doc.title)}" type="button">
        <span class="doc-list-item__icon" aria-hidden="true">📄</span>
        <span class="doc-list-item__title">${_escapeHtml(doc.title)}</span>
        <span class="doc-list-item__date">${date}</span>
      </button>
      <div class="doc-list-item__actions">
        <button class="doc-list-item__action doc-rename-btn" data-doc-id="${doc.id}" data-doc-title="${_escapeAttr(doc.title)}" aria-label="إعادة تسمية" title="إعادة تسمية" type="button">✎</button>
        <button class="doc-list-item__action doc-delete-btn" data-doc-id="${doc.id}" data-doc-title="${_escapeAttr(doc.title)}" aria-label="حذف" title="حذف" type="button">✕</button>
      </div>
    </div>`;
}

function _bindDocItemEvents(container) {
  container.querySelectorAll('.doc-list-item__open').forEach(btn => {
    btn.addEventListener('click', () => _openDocument(btn.dataset.docId));
  });
  container.querySelectorAll('.doc-rename-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      _startRename(btn.dataset.docId, btn.dataset.docTitle);
    });
  });
  container.querySelectorAll('.doc-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      _confirmDelete(btn.dataset.docId, btn.dataset.docTitle);
    });
  });
}

/* ── Open document ── */

async function _openDocument(id) {
  const doc = await loadDocument(id);
  if (!doc) {
    if (typeof showDocToast === 'function') showDocToast('تعذّر تحميل المستند', 'error');
    return;
  }

  let contentToLoad = doc.content;
  if (typeof SyncManager !== 'undefined') {
    contentToLoad = await SyncManager.loadAndResolveDocument(id);
    if (contentToLoad === null) return;
  }

  loadDocumentText(contentToLoad, { analyze: true });
  setDocState({
    currentDocumentId: doc.id,
    currentDocumentTitle: doc.title,
    hasUnsavedChanges: false
  });
  _updateTitleBar();
  _refreshActiveItem(id);

  // Navigate to editor
  if (typeof showPage === 'function') showPage('editor');

  // Close sidebar on mobile
  const sidebar = document.getElementById('docs-sidebar');
  if (sidebar && window.innerWidth < 1024) {
    sidebar.classList.remove('is-open');
  }
}

/* ── Create document ── */

async function _createNewDocument() {
  const isAuthenticated = window.__bayanAuth &&
    window.__bayanAuth.userId &&
    !window.__bayanAuth.isOfflineMode;
  if (!isAuthenticated) {
    if (typeof showDocToast === 'function') showDocToast('سجّل دخولك لحفظ المستندات', 'info');
    return;
  }

  const content = getEditorText();
  const titleInput = prompt('اسم المستند الجديد:', 'مستند جديد');
  if (titleInput === null) return; // User pressed Cancel
  const title = titleInput.trim() || 'مستند جديد';
  const doc = await createDocument(title, content);
  if (!doc) {
    if (typeof showDocToast === 'function') showDocToast('تعذّر إنشاء المستند', 'error');
    return;
  }

  setDocState({
    currentDocumentId: doc.id,
    currentDocumentTitle: doc.title,
    hasUnsavedChanges: false
  });
  _updateTitleBar();
  await _loadAndRenderList();
  if (typeof showDocToast === 'function') showDocToast('تم إنشاء المستند ✓', 'success');
}

/* ── Save current document manually ── */

async function saveCurrentDocument() {
  const state = getDocState();
  if (!state.currentDocumentId) {
    await _createNewDocument();
    return;
  }

  const content = getEditorText();
  if (typeof SyncManager !== 'undefined') {
    SyncManager.queueChange(state.currentDocumentId, content);
    await SyncManager.syncNow();
    if (typeof showDocToast === 'function') showDocToast('تم الحفظ ✓', 'success');
  } else {
    const ok = await saveDocument(state.currentDocumentId, content);
    if (ok) {
      markClean();
      _updateTitleBar();
      await _loadAndRenderList();
      if (typeof showDocToast === 'function') showDocToast('تم الحفظ ✓', 'success');
    } else {
      if (typeof showDocToast === 'function') showDocToast('تعذّر الحفظ', 'error');
    }
  }
}

/* ── Rename ── */

function _startRename(id, currentTitle) {
  const newTitle = prompt('الاسم الجديد للمستند:', currentTitle);
  if (!newTitle || newTitle === currentTitle) return;
  _doRename(id, newTitle);
}

async function _doRename(id, newTitle) {
  const ok = await renameDocument(id, newTitle);
  if (!ok) {
    if (typeof showDocToast === 'function') showDocToast('تعذّر إعادة التسمية', 'error');
    return;
  }
  const state = getDocState();
  if (state.currentDocumentId === id) {
    setDocState({ currentDocumentTitle: newTitle });
    _updateTitleBar();
  }
  await _loadAndRenderList();
}

/* ── Delete ── */

async function _confirmDelete(id, title) {
  if (!confirm(`هل تريد حذف "${title}"؟ لا يمكن التراجع عن هذا الإجراء.`)) return;

  const ok = await deleteDocument(id);
  if (!ok) {
    if (typeof showDocToast === 'function') showDocToast('تعذّر الحذف', 'error');
    return;
  }

  const state = getDocState();
  if (state.currentDocumentId === id) {
    setDocState({ currentDocumentId: null, currentDocumentTitle: 'مستند جديد', hasUnsavedChanges: false });
    _updateTitleBar();
  }
  await _loadAndRenderList();
  if (typeof showDocToast === 'function') showDocToast('تم حذف المستند', 'success');
}

/* ── Title bar ── */

function _updateTitleBar() {
  const titleEl = document.getElementById('doc-current-title');
  const saveBtn = document.getElementById('doc-save-btn');
  if (!titleEl) return;

  const state = getDocState();
  titleEl.textContent = state.currentDocumentTitle;

  if (saveBtn) {
    const unsaved = state.hasUnsavedChanges && state.currentDocumentId;
    saveBtn.classList.toggle('doc-save-btn--dirty', !!unsaved);
    const isTempState = saveBtn.classList.contains('is-saving') || saveBtn.classList.contains('is-saved');
    if (!isTempState) {
      saveBtn.title = unsaved ? 'حفظ (يوجد تغييرات غير محفوظة)' : 'حفظ';
    }
  }
}

/* ── Refresh active item in list without full reload ── */

function _refreshActiveItem(activeId) {
  document.querySelectorAll('.doc-list-item').forEach(el => {
    el.classList.toggle('doc-list-item--active', el.dataset.docId === activeId);
  });
}

/* ── Render sidebar HTML into DOM ── */

function _renderSidebar() {
  // The sidebar div is already in HTML — just wire the new-doc button
  const newDocBtn = document.getElementById('docs-new-btn');
  if (newDocBtn) {
    newDocBtn.addEventListener('click', _createNewDocument);
  }

  const saveBtn = document.getElementById('doc-save-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', saveCurrentDocument);
  }
}

/* ── Helpers ── */

function _escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _escapeAttr(str) {
  return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
