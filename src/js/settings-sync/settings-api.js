// Phase 6.3 — Settings Cloud API
// Supabase upsert/read only. No DOM. Never throws.

function _getSettingsClient() {
  return (typeof getSupabaseClient === 'function') ? getSupabaseClient() : null;
}

function _getSettingsUserId() {
  return window.__bayanAuth && window.__bayanAuth.userId
    ? window.__bayanAuth.userId
    : null;
}

/**
 * Load settings from cloud for current user.
 * @returns {Promise<{ theme: string, preferences: object }|null>}
 */
async function loadSettings() {
  const client = _getSettingsClient();
  const userId = _getSettingsUserId();
  if (!client || !userId) return null;
  try {
    const { data, error } = await client
      .from('settings')
      .select('theme, preferences')
      .eq('user_id', userId)
      .single();
    if (error && error.code !== 'PGRST116') throw error; // PGRST116 = not found
    return data || null;
  } catch (err) {
    console.warn('[settings-api] loadSettings failed:', err.message);
    return null;
  }
}

/**
 * Save (upsert) settings to cloud.
 * @param {{ theme?: string, preferences?: object }} settings
 * @returns {Promise<boolean>}
 */
async function saveSettings(settings) {
  const client = _getSettingsClient();
  const userId = _getSettingsUserId();
  if (!client || !userId) return false;
  try {
    const { error } = await client
      .from('settings')
      .upsert({ user_id: userId, ...settings }, { onConflict: 'user_id' });
    if (error) throw error;
    return true;
  } catch (err) {
    console.warn('[settings-api] saveSettings failed:', err.message);
    return false;
  }
}
