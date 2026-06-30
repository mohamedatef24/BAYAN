import re

# 1. CSS Injection
css_to_add = """
/* Light Theme Variables */
[data-theme="light"] {
  --bayan-bg: #f9fafb;
  --bayan-surface: #ffffff;
  --bayan-surface-hover: #f3f4f6;
  --bayan-surface-active: #e5e7eb;
  --bayan-border: #e5e7eb;
  --bayan-border-light: #d1d5db;
  --bayan-text: #111827;
  --bayan-text-secondary: #4b5563;
  --bayan-text-muted: #9ca3af;
  --bayan-success: #16a34a;
  --bayan-warning: #d97706;
}

/* Theme Toggle Button Styles */
.theme-toggle-animated {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: var(--bayan-surface-hover);
  color: var(--bayan-text-secondary);
  cursor: pointer;
  transition: background 0.3s ease, transform 0.3s ease, color 0.3s ease;
  position: relative;
  overflow: hidden;
  margin-right: 8px;
}

.theme-toggle-animated:hover {
  background: var(--bayan-primary);
  color: #fff;
  transform: rotate(15deg);
}

.theme-toggle-animated svg {
  transition: transform 0.4s ease, opacity 0.3s ease;
  position: absolute;
}

[data-theme="dark"] .theme-icon-sun {
  transform: rotate(90deg) scale(0);
  opacity: 0;
}

[data-theme="dark"] .theme-icon-moon {
  transform: rotate(0) scale(1);
  opacity: 1;
}

[data-theme="light"] .theme-icon-moon {
  transform: rotate(-90deg) scale(0);
  opacity: 0;
}

[data-theme="light"] .theme-icon-sun {
  transform: rotate(0) scale(1);
  opacity: 1;
}
"""

def append_to_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('\n' + content + '\n')

append_to_file('extension/popup.css', css_to_add)
append_to_file('extension/sidepanel/sidepanel.css', css_to_add)

# 2. HTML Injection
btn_html = """
    <button id="ext-theme-toggle" class="theme-toggle-animated" aria-label="تبديل السمة" type="button">
      <svg class="theme-icon-sun" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
      <svg class="theme-icon-moon" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
    </button>
"""

def insert_html_button(filepath, pattern):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # We want to put the button next to the status indicator.
    # The pattern will match the <div class="bayan-header-status"...> (or sp-) and inject the button right before it
    new_html = re.sub(pattern, btn_html + r'\1', html)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_html)

insert_html_button('extension/popup.html', r'(<div class="bayan-header-status")')
insert_html_button('extension/sidepanel/sidepanel.html', r'(<div class="sp-header-status")')

# 3. JS Logic Injection
js_to_add = """
// ── Theme Toggle Logic ──
document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('ext-theme-toggle');
  
  // Load theme from storage
  chrome.storage.local.get(['theme'], (result) => {
    const currentTheme = result.theme || 'dark'; // default to dark
    document.documentElement.setAttribute('data-theme', currentTheme);
  });

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      let theme = document.documentElement.getAttribute('data-theme') || 'dark';
      let targetTheme = theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', targetTheme);
      chrome.storage.local.set({ theme: targetTheme });
    });
  }
});
"""

append_to_file('extension/popup.js', js_to_add)
append_to_file('extension/sidepanel/sidepanel.js', js_to_add)

print("Theme toggle added successfully.")
