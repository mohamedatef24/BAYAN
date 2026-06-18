// Bayan theme system — dark/light with localStorage persistence

const THEME_KEY = 'bayan-theme';

function getPreferredTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function updateThemeToggleIcon(theme) {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;

  const isDark = theme === 'dark';
  btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
  btn.setAttribute(
    'aria-label',
    isDark ? 'التبديل إلى الوضع الفاتح' : 'التبديل إلى الوضع الداكن'
  );
  // CSS handles the sun/moon icon transitions via [data-theme] selectors
}

function clearThemePaletteOverrides() {
  const root = document.documentElement;
  const themeManaged = [
    '--color-bg', '--color-surface', '--color-surface-elevated', '--color-editor',
    '--color-text-primary', '--color-text-secondary', '--color-text-muted',
    '--background-color', '--surface-color', '--text-color', '--text-secondary'
  ];
  themeManaged.forEach((prop) => root.style.removeProperty(prop));
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  clearThemePaletteOverrides();
  updateThemeToggleIcon(theme);
  // Notify settings-sync so the change can be persisted to cloud
  window.dispatchEvent(new CustomEvent('bayan:themechange', { detail: { theme } }));
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  setTheme(current === 'dark' ? 'light' : 'dark');
}

function initTheme() {
  setTheme(getPreferredTheme());

  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.addEventListener('click', toggleTheme);
  }
}

// Apply theme before paint to avoid flash
(function applyThemeEarly() {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    const theme = stored === 'light' || stored === 'dark'
      ? stored
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  } catch (_) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
