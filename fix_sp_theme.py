sp_light_css = """
/* Light Theme Variables for Side Panel */
[data-theme="light"] {
  --sp-bg: #f9fafb;
  --sp-surface: #ffffff;
  --sp-surface-hover: #f3f4f6;
  --sp-surface-active: #e5e7eb;
  --sp-border: #e5e7eb;
  --sp-border-light: #d1d5db;
  --sp-text: #111827;
  --sp-text-secondary: #4b5563;
  --sp-text-muted: #9ca3af;
  --sp-success: #16a34a;
  --sp-warning: #d97706;
}
"""

with open('extension/sidepanel/sidepanel.css', 'a', encoding='utf-8') as f:
    f.write('\n' + sp_light_css + '\n')

print("Fixed sidepanel CSS variables for light mode.")
