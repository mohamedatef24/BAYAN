/**
 * Bayan Chrome Extension — Cloud Documents API
 *
 * REST-based Supabase document CRUD (no JS SDK).
 * Mirrors src/js/documents-cloud/documents-api.js using direct REST calls.
 *
 * Auth: Uses BayanAuth.getAccessToken() + cached Supabase config.
 * Table: public.documents (id, user_id, title, content, deleted_at, created_at, updated_at)
 */

const BayanDocuments = (() => {
  const CONFIG_CACHE_KEY = 'bayan_supabase_config';

  async function _getConfig() {
    try {
      const data = await chrome.storage.local.get([CONFIG_CACHE_KEY]);
      if (data[CONFIG_CACHE_KEY] && data[CONFIG_CACHE_KEY].supabase_url) {
        return data[CONFIG_CACHE_KEY];
      }
    } catch {}

    try {
      const apiBase = typeof BAYAN !== 'undefined' ? BAYAN.API_BASE : 'https://bayan10-bayan-api.hf.space';
      const res = await fetch(`${apiBase}/api/config`, { method: 'GET' });
      if (res.ok) {
        const cfg = await res.json();
        if (cfg.supabase_url && cfg.supabase_anon_key) {
          chrome.storage.local.set({ [CONFIG_CACHE_KEY]: cfg }).catch(() => {});
          return cfg;
        }
      }
    } catch {}

    return null;
  }

  function _headers(config, accessToken) {
    return {
      'apikey': config.supabase_anon_key,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    };
  }

  function _restUrl(config, params = '') {
    return `${config.supabase_url}/rest/v1/documents${params}`;
  }

  async function _authedRequest(method, params, body, extraHeaders) {
    const config = await _getConfig();
    const token = typeof BayanAuth !== 'undefined' ? BayanAuth.getAccessToken() : null;
    if (!config || !token) return null;

    const opts = {
      method,
      headers: { ..._headers(config, token), ...extraHeaders },
    };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(_restUrl(config, params), opts);
    return res;
  }

  /**
   * Create a new document.
   * @returns {Promise<object|null>} { id, title, content, created_at, updated_at }
   */
  async function createDocument(title = 'مستند جديد', content = '') {
    try {
      const user = typeof BayanAuth !== 'undefined' ? BayanAuth.getUser() : null;
      if (!user || !user.id) return null;

      const res = await _authedRequest('POST', '?select=id,title,content,created_at,updated_at', {
        user_id: user.id,
        title,
        content,
      }, { 'Prefer': 'return=representation' });

      if (!res || !res.ok) return null;
      const data = await res.json();
      return Array.isArray(data) ? data[0] : data;
    } catch (e) {
      console.warn('[BayanDocuments] createDocument failed:', e.message);
      return null;
    }
  }

  /**
   * Load list of documents for current user.
   * @returns {Promise<Array>} [{ id, title, updated_at }, ...]
   */
  async function loadDocuments() {
    try {
      const user = typeof BayanAuth !== 'undefined' ? BayanAuth.getUser() : null;
      if (!user || !user.id) return [];

      const params = `?select=id,title,updated_at&user_id=eq.${user.id}&deleted_at=is.null&order=updated_at.desc`;
      const res = await _authedRequest('GET', params);
      if (!res || !res.ok) return [];
      return await res.json();
    } catch (e) {
      console.warn('[BayanDocuments] loadDocuments failed:', e.message);
      return [];
    }
  }

  /**
   * Load a single document's full content.
   * @returns {Promise<object|null>} { id, title, content, updated_at }
   */
  async function loadDocument(id) {
    try {
      const user = typeof BayanAuth !== 'undefined' ? BayanAuth.getUser() : null;
      if (!user || !user.id) return null;

      const params = `?select=id,title,content,updated_at&id=eq.${id}&user_id=eq.${user.id}&deleted_at=is.null`;
      const res = await _authedRequest('GET', params);
      if (!res || !res.ok) return null;
      const data = await res.json();
      return data && data.length > 0 ? data[0] : null;
    } catch (e) {
      console.warn('[BayanDocuments] loadDocument failed:', e.message);
      return null;
    }
  }

  /**
   * Save content to an existing document.
   * @returns {Promise<boolean>}
   */
  async function saveDocument(id, content) {
    try {
      const user = typeof BayanAuth !== 'undefined' ? BayanAuth.getUser() : null;
      if (!user || !user.id) return false;

      const params = `?id=eq.${id}&user_id=eq.${user.id}`;
      const res = await _authedRequest('PATCH', params, { content });
      return res && res.ok;
    } catch (e) {
      console.warn('[BayanDocuments] saveDocument failed:', e.message);
      return false;
    }
  }

  /**
   * Rename a document.
   * @returns {Promise<boolean>}
   */
  async function renameDocument(id, title) {
    try {
      const user = typeof BayanAuth !== 'undefined' ? BayanAuth.getUser() : null;
      if (!user || !user.id) return false;

      const params = `?id=eq.${id}&user_id=eq.${user.id}`;
      const res = await _authedRequest('PATCH', params, { title });
      return res && res.ok;
    } catch (e) {
      console.warn('[BayanDocuments] renameDocument failed:', e.message);
      return false;
    }
  }

  /**
   * Soft-delete a document.
   * @returns {Promise<boolean>}
   */
  async function deleteDocument(id) {
    try {
      const user = typeof BayanAuth !== 'undefined' ? BayanAuth.getUser() : null;
      if (!user || !user.id) return false;

      const params = `?id=eq.${id}&user_id=eq.${user.id}`;
      const res = await _authedRequest('PATCH', params, { deleted_at: new Date().toISOString() });
      return res && res.ok;
    } catch (e) {
      console.warn('[BayanDocuments] deleteDocument failed:', e.message);
      return false;
    }
  }

  return {
    createDocument,
    loadDocuments,
    loadDocument,
    saveDocument,
    renameDocument,
    deleteDocument,
  };
})();
