// Authentication actions — guest, Google, link, logout

/**
 * Promise with timeout
 * @param {Promise} promise
 * @param {number} ms
 * @param {string} message
 */
function withTimeout(promise, ms, message) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms))
  ]);
}

/**
 * Sign in as anonymous guest
 * @returns {Promise<{ success: boolean, offline?: boolean, error?: string }>}
 */
async function signInAsGuest() {
  const client = getSupabaseClient();
  if (!client) {
    enableOfflineAuthMode();
    return { success: false, offline: true, error: 'not_configured' };
  }

  try {
    const { data, error } = await withTimeout(
      client.auth.signInAnonymously(),
      AUTH_SIGN_IN_TIMEOUT_MS,
      'timeout'
    );

    if (error) throw error;

    setCurrentSession(data.session);
    clearOfflineAuthMode();
    return { success: true };
  } catch (err) {
    console.warn('Guest sign-in failed:', err);
    enableOfflineAuthMode();
    return { success: false, offline: true, error: err.message || 'failed' };
  }
}

/**
 * Sign in with Google OAuth
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
async function signInWithGoogle() {
  const client = getSupabaseClient();
  if (!client) {
    if (typeof showDocToast === 'function') {
      showDocToast('خدمة المصادقة غير مهيأة. راجع إعدادات Supabase.', 'error');
    }
    return { success: false, error: 'not_configured' };
  }

  const redirectTo = window.location.origin + window.location.pathname;

  try {
    const { error } = await client.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo,
        queryParams: { prompt: 'select_account' }
      }
    });

    if (error) throw error;
    return { success: true };
  } catch (err) {
    console.error('Google sign-in failed:', err);
    if (typeof showDocToast === 'function') {
      showDocToast('تعذر بدء تسجيل الدخول عبر Google', 'error');
    }
    return { success: false, error: err.message };
  }
}

/**
 * Link Google identity to current anonymous user
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
async function linkGoogle() {
  const client = getSupabaseClient();
  const session = getCurrentSession();

  if (!client || !session) {
    return signInWithGoogle();
  }

  const redirectTo = window.location.origin + window.location.pathname;

  try {
    if (typeof client.auth.linkIdentity === 'function') {
      const { error } = await client.auth.linkIdentity({
        provider: 'google',
        options: { redirectTo }
      });
      if (error) throw error;
      return { success: true };
    }

    return signInWithGoogle();
  } catch (err) {
    console.error('Link Google failed:', err);
    if (typeof showDocToast === 'function') {
      showDocToast('تعذر ربط حساب Google', 'error');
    }
    return { success: false, error: err.message };
  }
}

/**
 * Sign out current user
 * @returns {Promise<void>}
 */
async function signOut() {
  const client = getSupabaseClient();
  clearOfflineAuthMode();

  if (client) {
    try {
      await client.auth.signOut();
    } catch (err) {
      console.warn('signOut error:', err);
    }
  }

  setCurrentSession(null);
  showAuthGate();
  updateAuthUI(null);
}

/**
 * Enable offline / degraded auth mode — editor still usable
 */
function enableOfflineAuthMode() {
  window.__bayanAuth = window.__bayanAuth || {};
  window.__bayanAuth.isOfflineMode = true;
  window.__bayanAuth.userId = null;
  hideAuthGate();
  showAuthOfflineBanner(true);
  if (typeof showDocToast === 'function') {
    showDocToast(
      'تعذر الاتصال بخدمة المصادقة. يمكنك متابعة استخدام المحرر والمحاولة لاحقاً.',
      'info'
    );
  }
}

function clearOfflineAuthMode() {
  if (window.__bayanAuth) {
    window.__bayanAuth.isOfflineMode = false;
  }
  showAuthOfflineBanner(false);
}

/**
 * Initialize authentication — non-blocking for editor
 * @returns {Promise<void>}
 */
async function initAuth() {
  window.__bayanAuth = {
    userId: null,
    isGuest: false,
    isGoogleUser: false,
    isOfflineMode: false,
    getAccessToken: () => null
  };

  bindAuthUIEvents();

  const config = getSupabaseConfig();
  if (!config.isConfigured) {
    enableOfflineAuthMode();
    return;
  }

  onAuthStateChange((event, session) => {
    updateAuthUI(session && session.user ? session.user : null);

    if (event === 'SIGNED_IN' && session) {
      hideAuthGate();
      clearOfflineAuthMode();
    }

    if (event === 'SIGNED_OUT') {
      showAuthGate();
    }
  });

  const session = await restoreSession();

  if (session && session.user) {
    hideAuthGate();
    updateAuthUI(session.user);
    return;
  }

  showAuthGate();
}
