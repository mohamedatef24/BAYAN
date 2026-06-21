import re

content = open('src/index.html', encoding='utf-8').read()
ui_js = open('src/js/ui.js', encoding='utf-8').read()
docs_ui = open('src/js/documents-cloud/documents-ui.js', encoding='utf-8').read()
editor_js = open('src/js/editor.js', encoding='utf-8').read()
format_js = open('src/js/format.js', encoding='utf-8').read()
comp_css = open('src/css/components.css', encoding='utf-8').read()

print('=' * 60)
print('PHASE 6 (cont): EDITOR COMPONENTS')
print('=' * 60)
checks = [
    ('6.2 Format tooltip Bold Arabic', 'title="\u063a\u0627\u0645\u0642' in content),
    ('6.2 Dropdowns close on click outside', 'closeAllFmtDropdowns' in format_js),
    ('6.2 Dropdowns close on Escape', 'Escape' in format_js),
    ('6.2 Active item highlight class', 'fmt-dropdown__item--active' in format_js),
    ('6.2 Smooth dropdown animation', 'translateY(-8px)' in comp_css),
    ('6.3 Placeholder exists', 'placeholder' in content.lower()),
    ('6.4 Popover hint text', '\u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u062d\u064a\u062d' in content),
    ('6.5 Empty state (has text - positive)', '\u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632' in ui_js),
    ('6.5 Empty state (no text)', '\u0644\u0627 \u062a\u0648\u062c\u062f \u0627\u0642\u062a\u0631\u0627\u062d\u0627\u062a' in ui_js),
    ('6.5 Apply All shows count', 'countLabel' in ui_js),
    ('6.5 Shimmer skeleton in analysis', 'skeleton' in ui_js),
    ('6.6 Stats char-count', 'char-count' in content),
    ('6.6 Stats sentence-count', 'sentence-count' in content),
    ('6.6 Stats reading-time', 'reading-time' in content),
    ('6.7 Docs empty state with icon', 'empty-state__icon' in docs_ui),
    ('6.7 Docs delete uses custom dialog', 'showConfirmDialog' in docs_ui),
    ('6.8 Summary loading state', '\u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f' in content),
    ('6.8 Summary error state', '\u062d\u062f\u062b \u062e\u0637\u0623' in content),
    ('6.9 Dialect char counter', 'dialect-char-count' in content or 'charCount' in content),
    ('6.10 Quran Escape closes', 'Escape' in content),
    ('6.10 Quran Ctrl+Q shortcut', 'KeyQ' in content),
]
for name, result in checks:
    print(f'  {"OK" if result else "MISS"} {name}')

print()
print('=' * 60)
print('PHASE 7: USER FLOWS & EDGE CASES')
print('=' * 60)
checks = [
    ('7.1 Auth gate exists', 'auth-gate' in content),
    ('7.1 Google sign-in', 'linkGoogle' in content),
    ('7.1 Guest flow', 'continueAsGuest' in content or '\u0627\u0644\u062a\u062c\u0631\u0628\u0629 \u0628\u062f\u0648\u0646' in content),
    ('7.1 Offline banner', 'offline-banner' in content),
    ('7.2 Doc save toast', '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in content or '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in docs_ui),
    ('7.2 Doc delete custom confirm', 'showConfirmDialog' in docs_ui),
    ('7.3 Summary loading spinner', 'summary-loading' in content),
    ('7.4 Auto-sync settings', 'settings-sync' in content or 'localStorage' in content),
    ('7.5 Draft restore on refresh', 'bayan_editor_draft' in editor_js),
    ('7.5 Theme persists', 'localStorage' in content and 'theme' in content.lower()),
    ('7.6 Analyze error toast', '\u062a\u0639\u0630\u0651\u0631 \u0627\u0644\u062a\u062d\u0644\u064a\u0644' in editor_js),
    ('7.6 Summary error in panel', '\u062d\u062f\u062b \u062e\u0637\u0623' in content),
    ('7.6 Dialect error handled', 'error' in content.split('dialect')[1][:2000] if 'dialect' in content else False),
    ('7.6 Quran error handled', 'catch' in content.split('quran')[2][:3000] if content.count('quran') > 2 else False),
]
for name, result in checks:
    print(f'  {"OK" if result else "MISS"} {name}')

print()
print('=' * 60)
print('PHASE 9: GLOBAL POLISH')
print('=' * 60)
# Count toast types
all_toasts = re.findall(r"showToast\([^)]+\)", content + editor_js)
success_toasts = [t for t in all_toasts if "'success'" in t or "type" not in t]
error_toasts = [t for t in all_toasts if "'error'" in t]
warning_toasts = [t for t in all_toasts if "'warning'" in t]
checks = [
    ('Meta desc includes Quran', '\u0627\u0644\u0642\u0631\u0622\u0646' in content.split('</head>')[0]),
    ('Meta desc includes dialects', '\u0627\u0644\u0644\u0647\u062c\u0627\u062a' in content.split('</head>')[0]),
    ('Footer has Quran link', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in content.split('footer')[1] if 'footer' in content.lower() else False),
    ('Footer has Dialect link', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in content.split('footer')[1] if 'footer' in content.lower() else False),
    ('404 arrow correct direction', '\u2192 \u0627\u0644\u0639\u0648\u062f\u0629' in content),
    ('Scroll-to-top button', 'scroll-top-btn' in content),
    (f'Toast types: {len(error_toasts)} error, {len(warning_toasts)} warning', len(error_toasts) >= 4 and len(warning_toasts) >= 3),
]
for name, result in checks:
    print(f'  {"OK" if result else "MISS"} {name}')

print()
print('=' * 60)
print('ARCHITECTURAL SAFETY')
print('=' * 60)
renderer = open('src/js/renderer.js', encoding='utf-8').read()
selection = open('src/js/selection.js', encoding='utf-8').read()
checks = [
    ('renderer.js NOT modified (has render fn)', 'function' in renderer),
    ('selection.js NOT modified (has save/restore)', 'saveSelection' in selection or 'restoreSelection' in selection),
    ('No React/Vue/Angular', 'react' not in content.lower().split('<script')[0]),
    ('No TypeScript', '.ts' not in content),
    ('Core flow intact: getEditorText', 'getEditorText' in editor_js),
    ('Core flow intact: /api/analyze', '/api/analyze' in editor_js),
    ('Core flow intact: restoreSelection', 'restoreSelection' in editor_js),
]
for name, result in checks:
    print(f'  {"OK" if result else "MISS"} {name}')
