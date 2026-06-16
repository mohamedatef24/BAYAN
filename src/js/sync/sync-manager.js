// Phase 7: Sync Manager
// Central orchestrator for all document synchronization.
// Combines debounce, queueing, offline detection, and resolving.

const SYNC_DEBOUNCE_MS = 2500; // Wait 2.5s after typing stops before syncing
let _syncDebounceTimer = null;
let _isSyncing = false;

const SyncManager = {
  init() {
    window.addEventListener('online', () => {
      this._updateUIState('online');
      this.flushChanges();
    });
    
    window.addEventListener('offline', () => {
      this._updateUIState('offline');
    });

    // Attempt an initial flush in case of lingering queued items
    if (navigator.onLine) {
      setTimeout(() => this.flushChanges(), 1000);
    }
  },

  /**
   * Queue a change to be synced to the cloud. Debounces repeated calls.
   * @param {string} docId 
   * @param {string} content 
   */
  queueChange(docId, content) {
    if (!docId) return;

    // Immediately enqueue locally (durably)
    if (typeof SyncQueue !== 'undefined') {
      SyncQueue.enqueue(docId, content);
    }

    if (!navigator.onLine) {
      this._updateUIState('saved_locally');
      return;
    }

    this._updateUIState('saving');

    // Debounce the actual cloud sync
    if (_syncDebounceTimer) clearTimeout(_syncDebounceTimer);
    _syncDebounceTimer = setTimeout(() => {
      this.flushChanges();
    }, SYNC_DEBOUNCE_MS);
  },

  /**
   * Force an immediate sync of the queue without waiting for debounce.
   */
  async syncNow() {
    if (_syncDebounceTimer) clearTimeout(_syncDebounceTimer);
    await this.flushChanges();
  },

  /**
   * Process all items in the queue and send them to Supabase.
   */
  async flushChanges() {
    if (!navigator.onLine || typeof SyncQueue === 'undefined' || typeof saveDocument === 'undefined') return;
    if (_isSyncing) return; // Prevent concurrent flushes

    const queue = SyncQueue.getAll();
    if (queue.length === 0) {
      this._updateUIState('saved');
      return;
    }

    _isSyncing = true;
    this._updateUIState('saving');

    let allSuccess = true;

    for (const item of queue) {
      try {
        // If we want conflict resolution, we could fetch first.
        // But for typing updates, usually we just overwrite. 
        // We will do a direct save here for efficiency. 
        // SyncResolver is primarily used when opening/loading a document.
        
        const success = await saveDocument(item.docId, item.content);
        if (success) {
          SyncQueue.remove(item.id);
        } else {
          allSuccess = false;
          SyncQueue.incrementRetry(item.id);
        }
      } catch (e) {
        console.error('Sync error:', e);
        allSuccess = false;
        SyncQueue.incrementRetry(item.id);
      }
    }

    _isSyncing = false;

    if (allSuccess) {
      this._updateUIState('saved');
      if (typeof markClean === 'function') markClean();
    } else {
      this._updateUIState('error');
    }
  },

  /**
   * Fetch a document and resolve conflicts if a local draft exists.
   * @param {string} docId 
   * @returns {Promise<string|null>} The resolved content
   */
  async loadAndResolveDocument(docId) {
    if (typeof loadDocument === 'undefined' || typeof SyncResolver === 'undefined') {
      return null;
    }

    const serverDoc = await loadDocument(docId);
    if (!serverDoc) return null;

    // Check if we have a pending change in the queue for this doc
    const queue = SyncQueue.getAll();
    const localDraft = queue.find(q => q.docId === docId);

    if (localDraft) {
      const winner = SyncResolver.resolveConflict(localDraft, serverDoc);
      if (winner === 'local') {
        // Local is newer. Return local content and queue an immediate sync to update the server.
        setTimeout(() => this.flushChanges(), 500);
        return localDraft.content;
      } else {
        // Server is newer. Discard local draft.
        SyncQueue.remove(localDraft.id);
        return serverDoc.content;
      }
    }

    return serverDoc.content;
  },

  /**
   * Internal helper to dispatch UI state changes
   * @param {'saving'|'saved'|'saved_locally'|'offline'|'online'|'error'} state 
   */
  _updateUIState(state) {
    window.dispatchEvent(new CustomEvent('bayan:syncstate', { detail: { state } }));
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SyncManager, SYNC_DEBOUNCE_MS };
}
