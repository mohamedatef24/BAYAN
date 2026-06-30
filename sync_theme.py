import re

# 1. Update content-inline.css for light mode
light_css = """
/* ── Light Theme Overrides for Inline UI ── */
.bayan-il-fab[data-bayan-theme="light"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
}

.bayan-il-fab[data-bayan-theme="light"] svg path {
    fill: #6366f1 !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(99, 102, 241, 0.1) !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-header {
    background: #f9fafb !important;
    border-bottom: 1px solid #e5e7eb !important;
    color: #4b5563 !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-body {
    background: #ffffff !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-original {
    color: #4b5563 !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-correction {
    color: #111827 !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-actions {
    border-top: 1px solid #e5e7eb !important;
    background: #f9fafb !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-ignore {
    color: #4b5563 !important;
}

.bayan-il-tooltip[data-bayan-theme="light"] .bayan-il-tooltip-ignore:hover {
    background: #e5e7eb !important;
    color: #111827 !important;
}
"""

with open('extension/content-inline.css', 'a', encoding='utf-8') as f:
    f.write('\n' + light_css + '\n')

# 2. Add storage listener to popup.js and sidepanel.js
listener_js = """
  // Sync theme changes instantly across all views
  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.theme) {
      document.documentElement.setAttribute('data-theme', changes.theme.newValue);
    }
  });
"""

for filepath in ['extension/popup.js', 'extension/sidepanel/sidepanel.js']:
    with open(filepath, 'r', encoding='utf-8') as f:
        js = f.read()
    
    # We will inject the listener right after we get the initial theme
    js = js.replace("document.documentElement.setAttribute('data-theme', currentTheme);\n  });", 
                    "document.documentElement.setAttribute('data-theme', currentTheme);\n  });\n" + listener_js)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(js)

# 3. Add theme logic to content-inline.js
# We need to set data-bayan-theme on floatingBtn and tooltip when they are created, and listen for changes.
content_theme_js = """

  // ── Theme Sync for Inline UI ──
  let currentBayanTheme = 'dark';
  chrome.storage.local.get(['theme'], (res) => {
    currentBayanTheme = res.theme || 'dark';
    if (typeof tooltip !== 'undefined' && tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
    if (typeof floatingBtn !== 'undefined' && floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
  });
  
  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.theme) {
      currentBayanTheme = changes.theme.newValue;
      if (typeof tooltip !== 'undefined' && tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
      if (typeof floatingBtn !== 'undefined' && floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
    }
  });
"""

with open('extension/content-inline.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Append to the end of the IIFE
js = js.replace("})();", content_theme_js + "\n})();")

# We also need to make sure tooltip and floatingBtn have the attribute right when they are created.
js = js.replace("tooltip = document.createElement('div');", "tooltip = document.createElement('div');\n    tooltip.setAttribute('data-bayan-theme', currentBayanTheme);")
js = js.replace("floatingBtn = document.createElement('div');", "floatingBtn = document.createElement('div');\n      floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);")

with open('extension/content-inline.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("Theme syncing added to all files successfully.")
