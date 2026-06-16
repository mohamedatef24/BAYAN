// Phase 6.2 — Summaries Cloud API
// Supabase CRUD only. No DOM access. Never throws to caller.

function _getSummaryClient() {
  return (typeof getSupabaseClient === 'function') ? getSupabaseClient() : null;
}

function _getSummaryUserId() {
  return window.__bayanAuth && window.__bayanAuth.userId
    ? window.__bayanAuth.userId
    : null;
}

/**
 * Save a new summary.
 * @param {string} originalText
 * @param {string} summaryText
 * @returns {Promise<object|null>}
 */
async function saveSummary(originalText, summaryText) {
  const client = _getSummaryClient();
  const userId = _getSummaryUserId();
  if (!client || !userId) return null;
  try {
    const { data, error } = await client
      .from('summaries')
      .insert({ user_id: userId, original_text: originalText, summary_text: summaryText })
      .select('id, created_at')
      .single();
    if (error) throw error;
    return data;
  } catch (err) {
    console.warn('[summaries-api] saveSummary failed:', err.message);
    return null;
  }
}

/**
 * Load all summaries for current user, newest first.
 * @returns {Promise<Array>}
 */
async function loadSummaries() {
  const client = _getSummaryClient();
  const userId = _getSummaryUserId();
  if (!client || !userId) return [];
  try {
    const { data, error } = await client
      .from('summaries')
      .select('id, summary_text, original_text, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(50);
    if (error) throw error;
    return data || [];
  } catch (err) {
    console.warn('[summaries-api] loadSummaries failed:', err.message);
    return [];
  }
}

/**
 * Delete a summary by id.
 * @param {string} id
 * @returns {Promise<boolean>}
 */
async function deleteSummary(id) {
  const client = _getSummaryClient();
  if (!client) return false;
  try {
    const { error } = await client
      .from('summaries')
      .delete()
      .eq('id', id);
    if (error) throw error;
    return true;
  } catch (err) {
    console.warn('[summaries-api] deleteSummary failed:', err.message);
    return false;
  }
}
