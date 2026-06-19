// Phase 6.3 — Settings Sync
// Loads cloud settings on login and pushes changes with debounce.
// localStorage is always applied first; cloud overrides only when authenticated.

const SETTINGS_PUSH_DEBOUNCE_MS = 1500;
let _settingsPushTimer = null;

/**
 * Load settings from cloud and apply them locally.
 * Called once after auth is initialized.
 */
async function syncSettings() {
  const isAuthenticated = window.__bayanAuth &&
    window.__bayanAuth.userId &&
    !window.__bayanAuth.isOfflineMode;

  if (!isAuthenticated) return;

  const settings = await loadSettings();
  if (!settings) return;

  // Apply theme from cloud (overrides localStorage when authenticated)
  if (settings.theme && typeof setTheme === 'function') {
    setTheme(settings.theme);
  }
}

/**
 * Push a settings change to cloud after a debounce delay.
 * @param {string} key - e.g. 'theme'
 * @param {string|object} value
 */
function onSettingsChanged(key, value) {
  if (_settingsPushTimer) clearTimeout(_settingsPushTimer);
  _settingsPushTimer = setTimeout(async () => {
    const isAuthenticated = window.__bayanAuth &&
      window.__bayanAuth.userId &&
      !window.__bayanAuth.isOfflineMode;
    if (!isAuthenticated) return;
    await saveSettings({ [key]: value });
  }, SETTINGS_PUSH_DEBOUNCE_MS);
}

/**
 * Listen to theme changes from theme.js and push to cloud.
 */
function _bindSettingsListeners() {
  window.addEventListener('bayan:themechange', (e) => {
    if (e.detail && e.detail.theme) {
      onSettingsChanged('theme', e.detail.theme);
    }
  });

  // Re-sync when user signs in (auth state change)
  window.addEventListener('bayan:authchange', () => {
    syncSettings();
  });
}

/**
 * Initialize settings sync. Called once in DOMContentLoaded.
 */
async function initSettingsSync() {
  _bindSettingsListeners();
  await syncSettings();
}
