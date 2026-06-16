// Phase 6.1 — Documents State
// In-memory state only. No DOM access. No Supabase.

const _docState = {
  currentDocumentId: null,
  currentDocumentTitle: 'مستند جديد',
  hasUnsavedChanges: false
};

/** @returns {{ currentDocumentId, currentDocumentTitle, hasUnsavedChanges }} */
function getDocState() {
  return { ..._docState };
}

/**
 * Update state fields and fire bayan:docstate event.
 * @param {Partial<typeof _docState>} updates
 */
function setDocState(updates) {
  Object.assign(_docState, updates);
  window.dispatchEvent(new CustomEvent('bayan:docstate', { detail: { ..._docState } }));
}

/** Mark document as having unsaved changes. */
function markDirty() {
  if (!_docState.hasUnsavedChanges) {
    setDocState({ hasUnsavedChanges: true });
  }
}

/** Mark document as clean (saved). */
function markClean() {
  setDocState({ hasUnsavedChanges: false });
}

/** True when a cloud document is currently open. */
function hasOpenDocument() {
  return !!_docState.currentDocumentId;
}
