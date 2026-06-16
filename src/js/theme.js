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

  btn.innerHTML = isDark
    ? '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>'
    : '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';
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
