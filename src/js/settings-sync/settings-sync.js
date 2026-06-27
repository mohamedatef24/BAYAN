// Phase 6.3 — Settings Sync (M5 conflict notification + M6 extended sync)
// Loads cloud settings on login and pushes changes with debounce.
// localStorage is always applied first; cloud overrides only when authenticated.

const SETTINGS_PUSH_DEBOUNCE_MS = 1500;
let _settingsPushTimer = null;

let _syncingFromCloud = false;

const _PREF_KEYS = ['font_size', 'word_goal', 'summary_mode'];

function _getLocalPreferences() {
  return {
    font_size: localStorage.getItem('bayan_font_size') || '16',
    word_goal: localStorage.getItem('bayan_word_goal') || '0',
    summary_mode: localStorage.getItem('bayan_summary_mode') || 'paragraph',
  };
}

function _applyPreferences(prefs) {
  if (!prefs) return;
  if (prefs.font_size) {
    localStorage.setItem('bayan_font_size', prefs.font_size);
    var editor = document.getElementById('editor-container');
    if (editor) editor.style.fontSize = prefs.font_size + 'px';
  }
  if (prefs.word_goal !== undefined) {
    localStorage.setItem('bayan_word_goal', String(prefs.word_goal));
    if (typeof updateEditorStats === 'function') updateEditorStats();
  }
  if (prefs.summary_mode) {
    localStorage.setItem('bayan_summary_mode', prefs.summary_mode);
    window._summaryMode = prefs.summary_mode;
  }
}

async function syncSettings() {
  const isAuthenticated = window.__bayanAuth &&
    window.__bayanAuth.userId &&
    !window.__bayanAuth.isOfflineMode;

  if (!isAuthenticated) return;

  const settings = await loadSettings();
  if (!settings) return;

  _syncingFromCloud = true;
  var changed = false;

  if (settings.theme && typeof setTheme === 'function') {
    var localTheme = localStorage.getItem('bayan_theme') || 'dark';
    if (settings.theme !== localTheme) {
      setTheme(settings.theme);
      changed = true;
    }
  }

  if (settings.preferences) {
    var local = _getLocalPreferences();
    var cloud = settings.preferences;
    for (var i = 0; i < _PREF_KEYS.length; i++) {
      var k = _PREF_KEYS[i];
      if (cloud[k] !== undefined && String(cloud[k]) !== String(local[k])) {
        changed = true;
        break;
      }
    }
    _applyPreferences(cloud);
  }

  _syncingFromCloud = false;

  if (changed && typeof showToast === 'function') {
    showToast('تم تحديث الإعدادات من السحابة', 'success');
  }
}

function onSettingsChanged(key, value) {
  if (_syncingFromCloud) return;
  if (_settingsPushTimer) clearTimeout(_settingsPushTimer);
  _settingsPushTimer = setTimeout(async () => {
    const isAuthenticated = window.__bayanAuth &&
      window.__bayanAuth.userId &&
      !window.__bayanAuth.isOfflineMode;
    if (!isAuthenticated) return;

    if (_PREF_KEYS.indexOf(key) !== -1) {
      var prefs = _getLocalPreferences();
      prefs[key] = value;
      await saveSettings({ preferences: prefs });
    } else {
      await saveSettings({ [key]: value });
    }
  }, SETTINGS_PUSH_DEBOUNCE_MS);
}

function _bindSettingsListeners() {
  window.addEventListener('bayan:themechange', (e) => {
    if (e.detail && e.detail.theme) {
      onSettingsChanged('theme', e.detail.theme);
    }
  });

  window.addEventListener('bayan:authchange', () => {
    syncSettings();
  });

  window.addEventListener('bayan:settingchange', (e) => {
    if (e.detail && e.detail.key) {
      onSettingsChanged(e.detail.key, e.detail.value);
    }
  });
}

async function initSettingsSync() {
  _bindSettingsListeners();
  await syncSettings();
}
