// Phase 7: Sync Queue
// Handles persistent queueing of document changes for offline support

const QUEUE_KEY = 'bayan_sync_queue';

const SyncQueue = {
  /**
   * Get all pending items in the queue
   * @returns {Array<{id: string, docId: string, content: string, timestamp: number, retries: number}>}
   */
  getAll() {
    try {
      const data = localStorage.getItem(QUEUE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.warn('Failed to read sync queue', e);
      return [];
    }
  },

  /**
   * Save the entire queue
   * @param {Array} queue 
   */
  _save(queue) {
    try {
      localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
    } catch (e) {
      console.warn('Failed to save sync queue', e);
    }
  },

  /**
   * Add a new change to the queue, replacing any existing pending change for the same doc
   * @param {string} docId 
   * @param {string} content 
   */
  enqueue(docId, content) {
    if (!docId) return;
    const queue = this.getAll();
    
    // Remove existing entry for the same doc to prevent duplicate redundant writes
    const filteredQueue = queue.filter(item => item.docId !== docId);
    
    filteredQueue.push({
      id: Date.now().toString() + '_' + Math.random().toString(36).substr(2, 5),
      docId,
      content,
      timestamp: Date.now(),
      retries: 0
    });

    this._save(filteredQueue);
  },

  /**
   * Remove a specific item from the queue after successful sync
   * @param {string} id 
   */
  remove(id) {
    const queue = this.getAll().filter(item => item.id !== id);
    this._save(queue);
  },

  /**
   * Increment retry count for a failed sync attempt
   * @param {string} id 
   */
  incrementRetry(id) {
    const queue = this.getAll();
    const item = queue.find(i => i.id === id);
    if (item) {
      item.retries += 1;
      this._save(queue);
    }
  },

  /**
   * Clear the entire queue
   */
  clear() {
    try {
      localStorage.removeItem(QUEUE_KEY);
    } catch (e) {}
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SyncQueue };
}
