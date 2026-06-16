// Phase 6.1 — Documents Cloud API
// Supabase CRUD only. No DOM access. Never throws to caller.

/**
 * @returns {import('@supabase/supabase-js').SupabaseClient|null}
 */
function _getClient() {
  return (typeof getSupabaseClient === 'function') ? getSupabaseClient() : null;
}

function _getUserId() {
  return window.__bayanAuth && window.__bayanAuth.userId
    ? window.__bayanAuth.userId
    : null;
}

/**
 * Create a new document in the cloud.
 * @param {string} title
 * @param {string} content
 * @returns {Promise<object|null>}
 */
async function createDocument(title = 'مستند جديد', content = '') {
  const client = _getClient();
  const userId = _getUserId();
  if (!client || !userId) return null;
  try {
    const { data, error } = await client
      .from('documents')
      .insert({ user_id: userId, title, content })
      .select('id, title, content, created_at, updated_at')
      .single();
    if (error) throw error;
    return data;
  } catch (err) {
    console.warn('[documents-api] createDocument failed:', err.message);
    return null;
  }
}

/**
 * Load list of documents (id, title, updated_at) for current user.
 * @returns {Promise<Array>}
 */
async function loadDocuments() {
  const client = _getClient();
  const userId = _getUserId();
  if (!client || !userId) return [];
  try {
    const { data, error } = await client
      .from('documents')
      .select('id, title, updated_at')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false });
    if (error) throw error;
    return data || [];
  } catch (err) {
    console.warn('[documents-api] loadDocuments failed:', err.message);
    return [];
  }
}

/**
 * Load a single document's full content.
 * @param {string} id
 * @returns {Promise<object|null>}
 */
async function loadDocument(id) {
  const client = _getClient();
  if (!client) return null;
  try {
    const { data, error } = await client
      .from('documents')
      .select('id, title, content, updated_at')
      .eq('id', id)
      .single();
    if (error) throw error;
    return data;
  } catch (err) {
    console.warn('[documents-api] loadDocument failed:', err.message);
    return null;
  }
}

/**
 * Save content to existing document.
 * @param {string} id
 * @param {string} content
 * @returns {Promise<boolean>}
 */
async function saveDocument(id, content) {
  const client = _getClient();
  if (!client) return false;
  try {
    const { error } = await client
      .from('documents')
      .update({ content })
      .eq('id', id);
    if (error) throw error;
    return true;
  } catch (err) {
    console.warn('[documents-api] saveDocument failed:', err.message);
    return false;
  }
}

/**
 * Rename a document.
 * @param {string} id
 * @param {string} title
 * @returns {Promise<boolean>}
 */
async function renameDocument(id, title) {
  const client = _getClient();
  if (!client) return false;
  try {
    const { error } = await client
      .from('documents')
      .update({ title })
      .eq('id', id);
    if (error) throw error;
    return true;
  } catch (err) {
    console.warn('[documents-api] renameDocument failed:', err.message);
    return false;
  }
}

/**
 * Delete a document permanently.
 * @param {string} id
 * @returns {Promise<boolean>}
 */
async function deleteDocument(id) {
  const client = _getClient();
  if (!client) return false;
  try {
    const { error } = await client
      .from('documents')
      .delete()
      .eq('id', id);
    if (error) throw error;
    return true;
  } catch (err) {
    console.warn('[documents-api] deleteDocument failed:', err.message);
    return false;
  }
}
