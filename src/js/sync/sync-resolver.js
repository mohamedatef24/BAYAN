// Phase 7: Sync Resolver
// Resolves conflicts between local and server versions of documents

const SyncResolver = {
  /**
   * Resolves a conflict between a local document draft and the server document.
   * Rule: Latest timestamp wins. Fallback: Server wins.
   * 
   * @param {object} localDoc - The local pending change or draft object (needs timestamp)
   * @param {object} serverDoc - The document fetched from Supabase (needs updated_at)
   * @returns {'local' | 'server'} - Which version won
   */
  resolveConflict(localDoc, serverDoc) {
    if (!localDoc || !localDoc.content) return 'server';
    if (!serverDoc || !serverDoc.content) return 'local';

    const localTime = localDoc.timestamp ? new Date(localDoc.timestamp).getTime() : 0;
    const serverTime = serverDoc.updated_at ? new Date(serverDoc.updated_at).getTime() : 0;

    // If both times are valid, latest wins
    if (localTime > 0 && serverTime > 0) {
      if (localTime >= serverTime) {
        return 'local';
      } else {
        return 'server';
      }
    }

    // Fallback: Server wins
    return 'server';
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SyncResolver };
}
