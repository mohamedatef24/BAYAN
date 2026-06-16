// Phase 6.2 — Summaries UI
// Handles save-summary button and summary history panel.

function initSummaries() {
  _bindSaveSummaryBtn();
  _bindHistoryTab();
}

/* ── Save button (appears after generating a summary) ── */

function _bindSaveSummaryBtn() {
  const btn = document.getElementById('save-summary-btn');
  if (!btn) return;
  btn.addEventListener('click', _handleSaveSummary);
}

async function _handleSaveSummary() {
  const summaryEl = document.getElementById('summary-text');
  const editorText = (typeof getEditorText === 'function') ? getEditorText() : '';
  const summaryText = summaryEl ? (summaryEl.innerText || summaryEl.textContent || '').trim() : '';

  if (!summaryText) {
    if (typeof showDocToast === 'function') showDocToast('لا يوجد ملخص لحفظه', 'info');
    return;
  }

  const isAuthenticated = window.__bayanAuth &&
    window.__bayanAuth.userId &&
    !window.__bayanAuth.isOfflineMode;

  if (!isAuthenticated) {
    if (typeof showDocToast === 'function') showDocToast('سجّل دخولك لحفظ الملخصات', 'info');
    return;
  }

  const result = await saveSummary(editorText, summaryText);
  if (result) {
    if (typeof showDocToast === 'function') showDocToast('تم حفظ الملخص ✓', 'success');
    await _loadAndRenderHistory();
  } else {
    if (typeof showDocToast === 'function') showDocToast('تعذّر حفظ الملخص', 'error');
  }
}

/* ── History tab toggle ── */

function _bindHistoryTab() {
  const toggleBtn = document.getElementById('summary-history-toggle');
  const panel = document.getElementById('summary-history-panel');
  if (!toggleBtn || !panel) return;

  toggleBtn.addEventListener('click', async () => {
    const isOpen = panel.classList.toggle('is-open');
    toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    if (isOpen) await _loadAndRenderHistory();
  });
}

/* ── Load & render history ── */

async function _loadAndRenderHistory() {
  const listEl = document.getElementById('summary-history-list');
  if (!listEl) return;

  const isAuthenticated = window.__bayanAuth &&
    window.__bayanAuth.userId &&
    !window.__bayanAuth.isOfflineMode;

  if (!isAuthenticated) {
    listEl.innerHTML = `<p class="summary-history-empty">سجّل دخولك لعرض سجل الملخصات</p>`;
    return;
  }

  listEl.innerHTML = `<p class="summary-history-empty">جاري التحميل...</p>`;
  const items = await loadSummaries();

  if (!items.length) {
    listEl.innerHTML = `<p class="summary-history-empty">لم يتم حفظ أي ملخصات بعد</p>`;
    return;
  }

  listEl.innerHTML = items.map(item => _buildHistoryItemHTML(item)).join('');
  _bindHistoryItemEvents(listEl);
}

function _buildHistoryItemHTML(item) {
  const preview = (item.summary_text || '').slice(0, 80) + (item.summary_text.length > 80 ? '...' : '');
  const date = new Date(item.created_at).toLocaleDateString('ar-EG', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });
  return `
    <div class="summary-history-item" data-summary-id="${item.id}" role="listitem">
      <div class="summary-history-item__body">
        <p class="summary-history-item__preview">${_escapeSummaryHtml(preview)}</p>
        <span class="summary-history-item__date">${date}</span>
      </div>
      <div class="summary-history-item__actions">
        <button class="summary-open-btn" data-summary-text="${_escapeSummaryAttr(item.summary_text)}" aria-label="عرض الملخص" type="button">عرض</button>
        <button class="summary-delete-btn" data-summary-id="${item.id}" aria-label="حذف الملخص" type="button">✕</button>
      </div>
    </div>`;
}

function _bindHistoryItemEvents(container) {
  container.querySelectorAll('.summary-open-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const summaryTextEl = document.getElementById('summary-text');
      if (summaryTextEl) {
        summaryTextEl.textContent = btn.dataset.summaryText;
        // Show the preview panel
        const preview = document.getElementById('summary-preview');
        if (preview) preview.classList.add('show');
      }
    });
  });

  container.querySelectorAll('.summary-delete-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm('هل تريد حذف هذا الملخص؟')) return;
      const ok = await deleteSummary(btn.dataset.summaryId);
      if (ok) {
        if (typeof showDocToast === 'function') showDocToast('تم حذف الملخص', 'success');
        await _loadAndRenderHistory();
      }
    });
  });
}

function _escapeSummaryHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function _escapeSummaryAttr(str) {
  return String(str || '').replace(/"/g, '&quot;');
}
