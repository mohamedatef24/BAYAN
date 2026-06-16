// Single Supabase client instance

let _supabaseClient = null;

/**
 * Get or create Supabase client
 * @returns {object|null}
 */
function getSupabaseClient() {
  if (_supabaseClient) return _supabaseClient;

  const config = getSupabaseConfig();
  if (!config.isConfigured) {
    console.warn('Supabase not configured — set meta tags supabase-url and supabase-anon-key');
    return null;
  }

  if (typeof supabase === 'undefined' || !supabase.createClient) {
    console.warn('Supabase library not loaded');
    return null;
  }

  _supabaseClient = supabase.createClient(config.url, config.anonKey, {
    auth: {
      detectSessionInUrl: true,
      persistSession: true,
      autoRefreshToken: true,
      flowType: 'pkce'
    }
  });

  return _supabaseClient;
}
