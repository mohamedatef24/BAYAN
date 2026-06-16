// Session state helpers

let _currentSession = null;
let _authListenerUnsub = null;

/**
 * @returns {object|null}
 */
function getCurrentSession() {
  return _currentSession;
}

/**
 * @param {object|null} session
 */
function setCurrentSession(session) {
  _currentSession = session;
  syncBayanAuthFacade(session);
}

/**
 * Sync read-only facade for Phase 6
 * @param {object|null} session
 */
function syncBayanAuthFacade(session) {
  const user = session && session.user;
  window.__bayanAuth = {
    userId: user ? user.id : null,
    isGuest: user ? isGuestUser(user) : false,
    isGoogleUser: user ? isGoogleUser(user) : false,
    isOfflineMode: window.__bayanAuth?.isOfflineMode === true,
    getAccessToken: () => (session ? session.access_token : null)
  };
}

/**
 * @param {object} user
 * @returns {boolean}
 */
function isGuestUser(user) {
  if (!user) return false;
  if (user.is_anonymous === true) return true;
  const provider = getAuthProvider(user);
  return provider === 'anonymous';
}

/**
 * @param {object} user
 * @returns {boolean}
 */
function isGoogleUser(user) {
  if (!user) return false;
  if (isGuestUser(user)) return false;
  const provider = getAuthProvider(user);
  if (provider === 'google') return true;
  const identities = user.identities || [];
  return identities.some((id) => id.provider === 'google');
}

/**
 * @param {object} user
 * @returns {string}
 */
function getAuthProvider(user) {
  if (!user) return 'anonymous';
  if (user.is_anonymous) return 'anonymous';
  const meta = user.app_metadata || {};
  if (meta.provider === 'google') return 'google';
  const identities = user.identities || [];
  if (identities.length > 0) return identities[0].provider || 'unknown';
  return meta.provider || 'unknown';
}

/**
 * @param {object} user
 * @returns {string}
 */
function getDisplayName(user) {
  if (!user) return '';
  if (isGuestUser(user)) return 'ضيف';
  return user.user_metadata?.full_name
    || user.user_metadata?.name
    || user.email
    || 'مستخدم Google';
}

/**
 * @param {object} user
 * @returns {string|null}
 */
function getAvatarUrl(user) {
  if (!user || isGuestUser(user)) return null;
  return user.user_metadata?.avatar_url
    || user.user_metadata?.picture
    || null;
}

/**
 * Register auth state change listener
 * @param {function} callback
 */
function onAuthStateChange(callback) {
  const client = getSupabaseClient();
  if (!client) return;

  if (_authListenerUnsub) {
    _authListenerUnsub.unsubscribe();
  }

  const { data } = client.auth.onAuthStateChange((event, session) => {
    setCurrentSession(session);
    if (typeof callback === 'function') {
      callback(event, session);
    }
  });

  _authListenerUnsub = data.subscription;
}

/**
 * Restore session from storage
 * @returns {Promise<object|null>}
 */
async function restoreSession() {
  const client = getSupabaseClient();
  if (!client) return null;

  const { data, error } = await client.auth.getSession();
  if (error) {
    console.warn('getSession error:', error);
    return null;
  }

  setCurrentSession(data.session);
  return data.session;
}
