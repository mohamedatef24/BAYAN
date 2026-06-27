/**
 * Bayan Chrome Extension — Auth Module
 *
 * Lightweight Supabase auth via REST API + chrome.identity.
 * No Supabase JS SDK required.
 *
 * Flow:
 *   1. Fetch Supabase config from /api/config
 *   2. Restore session from chrome.storage.local
 *   3. Google OAuth via chrome.identity.launchWebAuthFlow()
 *   4. Token refresh via Supabase REST /auth/v1/token
 */

const BayanAuth = (() => {
  const STORAGE_KEY = 'bayan_auth_session';
  const CONFIG_CACHE_KEY = 'bayan_supabase_config';
  const DISMISSED_WORDS_KEY = 'bayan_dismissed_words';
  const TOKEN_REFRESH_MARGIN_MS = 60_000;

  let _config = null;
  let _session = null;
  let _user = null;
  let _listeners = [];

  function _notify(event) {
    _listeners.forEach(fn => {
      try { fn(event, _user, _session); } catch (e) { console.warn('[BayanAuth] listener error:', e); }
    });
  }

  async function _fetchConfig() {
    if (_config) return _config;

    const storage = chrome.storage?.local;
    if (storage) {
      try {
        const cached = await storage.get([CONFIG_CACHE_KEY]);
        if (cached[CONFIG_CACHE_KEY] && cached[CONFIG_CACHE_KEY].supabase_url) {
          _config = cached[CONFIG_CACHE_KEY];
        }
      } catch {}
    }

    try {
      const apiBase = typeof BAYAN !== 'undefined' ? BAYAN.API_BASE : 'https://bayan10-bayan-api.hf.space';
      const res = await fetch(`${apiBase}/api/config`, { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        if (data.supabase_url && data.supabase_anon_key) {
          _config = data;
          if (storage) {
            storage.set({ [CONFIG_CACHE_KEY]: data }).catch(() => {});
          }
        }
      }
    } catch (e) {
      console.warn('[BayanAuth] Failed to fetch config:', e.message);
    }

    return _config;
  }

  function _parseHashParams(url) {
    try {
      const hash = new URL(url).hash.substring(1);
      return Object.fromEntries(new URLSearchParams(hash));
    } catch {
      return {};
    }
  }

  async function _fetchUser(accessToken) {
    if (!_config) return null;
    try {
      const res = await fetch(`${_config.supabase_url}/auth/v1/user`, {
        headers: {
          'apikey': _config.supabase_anon_key,
          'Authorization': `Bearer ${accessToken}`,
        },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  async function _refreshToken(refreshToken) {
    if (!_config) return null;
    try {
      const res = await fetch(`${_config.supabase_url}/auth/v1/token?grant_type=refresh_token`, {
        method: 'POST',
        headers: {
          'apikey': _config.supabase_anon_key,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  async function _saveSession(session) {
    _session = session;
    const storage = chrome.storage?.local;
    if (storage) {
      await storage.set({ [STORAGE_KEY]: session }).catch(() => {});
    }
  }

  async function _clearSession() {
    _session = null;
    _user = null;
    const storage = chrome.storage?.local;
    if (storage) {
      await storage.remove([STORAGE_KEY]).catch(() => {});
    }
  }

  async function _processTokens(accessToken, refreshToken, expiresIn) {
    const expiresAt = Date.now() + (expiresIn * 1000);
    const session = { access_token: accessToken, refresh_token: refreshToken, expires_at: expiresAt };
    await _saveSession(session);

    const user = await _fetchUser(accessToken);
    if (user && user.id) {
      _user = {
        id: user.id,
        email: user.email || '',
        name: user.user_metadata?.full_name || user.user_metadata?.name || '',
        avatar: user.user_metadata?.avatar_url || '',
        isAnonymous: user.is_anonymous || false,
      };
    }

    _scheduleRefresh();
    _notify('SIGNED_IN');
    return true;
  }

  let _refreshTimer = null;

  function _scheduleRefresh() {
    if (_refreshTimer) clearTimeout(_refreshTimer);
    if (!_session) return;

    const msUntilExpiry = _session.expires_at - Date.now();
    const refreshIn = Math.max(msUntilExpiry - TOKEN_REFRESH_MARGIN_MS, 5000);

    _refreshTimer = setTimeout(async () => {
      if (!_session?.refresh_token) return;
      const data = await _refreshToken(_session.refresh_token);
      if (data && data.access_token) {
        await _processTokens(data.access_token, data.refresh_token, data.expires_in || 3600);
      } else {
        await _clearSession();
        _notify('TOKEN_REFRESH_FAILED');
      }
    }, refreshIn);
  }

  // ── Public API ──

  async function init() {
    await _fetchConfig();

    const storage = chrome.storage?.local;
    if (!storage) return;

    try {
      const data = await storage.get([STORAGE_KEY]);
      const saved = data[STORAGE_KEY];
      if (!saved || !saved.access_token) return;

      if (saved.expires_at && saved.expires_at > Date.now()) {
        _session = saved;
        const user = await _fetchUser(saved.access_token);
        if (user && user.id) {
          _user = {
            id: user.id,
            email: user.email || '',
            name: user.user_metadata?.full_name || user.user_metadata?.name || '',
            avatar: user.user_metadata?.avatar_url || '',
            isAnonymous: user.is_anonymous || false,
          };
          _scheduleRefresh();
          _notify('RESTORED');
          return;
        }
      }

      if (saved.refresh_token) {
        const data = await _refreshToken(saved.refresh_token);
        if (data && data.access_token) {
          await _processTokens(data.access_token, data.refresh_token, data.expires_in || 3600);
          return;
        }
      }

      await _clearSession();
    } catch (e) {
      console.warn('[BayanAuth] init restore failed:', e);
    }
  }

  async function signInWithGoogle() {
    const config = await _fetchConfig();
    if (!config || !config.supabase_url) {
      console.warn('[BayanAuth] Supabase not configured');
      return { success: false, error: 'not_configured' };
    }

    const redirectUrl = chrome.identity.getRedirectURL();
    const authUrl = `${config.supabase_url}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUrl)}`;

    try {
      const responseUrl = await new Promise((resolve, reject) => {
        chrome.identity.launchWebAuthFlow(
          { url: authUrl, interactive: true },
          (url) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(url);
            }
          }
        );
      });

      const params = _parseHashParams(responseUrl);
      if (!params.access_token) {
        return { success: false, error: 'no_token' };
      }

      await _processTokens(params.access_token, params.refresh_token || '', parseInt(params.expires_in || '3600', 10));
      return { success: true };
    } catch (e) {
      console.error('[BayanAuth] Google sign-in failed:', e);
      return { success: false, error: e.message };
    }
  }

  async function signOut() {
    if (_session && _config) {
      try {
        await fetch(`${_config.supabase_url}/auth/v1/logout`, {
          method: 'POST',
          headers: {
            'apikey': _config.supabase_anon_key,
            'Authorization': `Bearer ${_session.access_token}`,
          },
        });
      } catch {}
    }

    if (_refreshTimer) clearTimeout(_refreshTimer);
    await _clearSession();
    _notify('SIGNED_OUT');
  }

  function getUser() { return _user; }

  function getAccessToken() {
    if (!_session) return null;
    if (_session.expires_at && _session.expires_at < Date.now()) return null;
    return _session.access_token;
  }

  function isAuthenticated() {
    return !!(_user && _user.id && getAccessToken());
  }

  function onAuthStateChange(fn) {
    _listeners.push(fn);
    return () => { _listeners = _listeners.filter(f => f !== fn); };
  }

  // ── Dismissed words persistence ──

  async function getDismissedWords() {
    const storage = chrome.storage?.local;
    if (!storage) return [];
    try {
      const data = await storage.get([DISMISSED_WORDS_KEY]);
      return data[DISMISSED_WORDS_KEY] || [];
    } catch {
      return [];
    }
  }

  async function addDismissedWord(word) {
    const words = await getDismissedWords();
    if (!words.includes(word)) {
      words.push(word);
      await chrome.storage.local.set({ [DISMISSED_WORDS_KEY]: words }).catch(() => {});
    }
  }

  async function removeDismissedWord(word) {
    const words = await getDismissedWords();
    const filtered = words.filter(w => w !== word);
    await chrome.storage.local.set({ [DISMISSED_WORDS_KEY]: filtered }).catch(() => {});
  }

  async function clearDismissedWords() {
    await chrome.storage.local.remove([DISMISSED_WORDS_KEY]).catch(() => {});
  }

  return {
    init,
    signInWithGoogle,
    signOut,
    getUser,
    getAccessToken,
    isAuthenticated,
    onAuthStateChange,
    getDismissedWords,
    addDismissedWord,
    removeDismissedWord,
    clearDismissedWords,
  };
})();
