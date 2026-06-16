// Supabase configuration — loaded from meta tags or window env

const AUTH_SIGN_IN_TIMEOUT_MS = 8000;

/**
 * Read Supabase config from meta tags
 * @returns {{ url: string, anonKey: string, isConfigured: boolean }}
 */
function getSupabaseConfig() {
  const urlMeta = document.querySelector('meta[name="supabase-url"]');
  const keyMeta = document.querySelector('meta[name="supabase-anon-key"]');

  const url = (urlMeta && urlMeta.getAttribute('content') || '').trim();
  const anonKey = (keyMeta && keyMeta.getAttribute('content') || '').trim();

  return {
    url,
    anonKey,
    isConfigured: !!(url && anonKey && !url.includes('YOUR_PROJECT'))
  };
}
