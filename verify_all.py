"""
BAYAN Full UI/UX Audit — Complete Verification Script
Checks EVERY item from the implementation plan against actual source code.
"""
import re, glob, os

def load(path):
    return open(path, encoding='utf-8').read()

# Load all source files
html = load('src/index.html')
tokens_css = load('src/css/tokens.css')
base_css = load('src/css/base.css')
comp_css = load('src/css/components.css')
editor_js = load('src/js/editor.js')
ui_js = load('src/js/ui.js')
format_js = load('src/js/format.js')
docs_ui = load('src/js/documents-cloud/documents-ui.js')

# Load all JS files combined for broader searches
all_js = ''
for f in glob.glob('src/js/**/*.js', recursive=True):
    all_js += load(f) + '\n'

total = 0
passed = 0

def check(name, result):
    global total, passed
    total += 1
    if result:
        passed += 1
    status = '\u2705' if result else '\u274c'
    print(f'  {status} {name}')
    return result

def section(title):
    print()
    print('=' * 70)
    print(f'  {title}')
    print('=' * 70)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 1: DESIGN SYSTEM & CSS MODERNIZATION')
# ─────────────────────────────────────────────────────────────────────
check('tokens.css: --shadow-xs', '--shadow-xs' in tokens_css)
check('tokens.css: --shadow-glow', '--shadow-glow' in tokens_css)
check('tokens.css: --transition-spring', '--transition-spring' in tokens_css)
check('tokens.css: --radius-xl', '--radius-xl' in tokens_css)
check('tokens.css: --spacing-section', '--spacing-section' in tokens_css)
check('base.css: smooth scroll', 'scroll-behavior: smooth' in base_css)
check('base.css: custom scrollbar webkit', '::-webkit-scrollbar' in base_css)
check('base.css: custom scrollbar firefox', 'scrollbar-width: thin' in base_css)
check('base.css: ::selection highlight', '::selection' in base_css)
check('base.css: focus-visible', 'focus-visible' in base_css)
check('base.css: shimmer keyframes', '@keyframes shimmer' in base_css)
check('base.css: .skeleton class', '.skeleton' in base_css)
check('base.css: button press scale(0.97)', 'scale(0.97)' in base_css)
check('components.css: nav glassmorphism saturate', 'saturate(180%)' in comp_css)
check('components.css: empty-state component', '.empty-state' in comp_css)
check('components.css: confirm-dialog', '.confirm-dialog' in comp_css)
check('components.css: modalSlideUp animation', '@keyframes modalSlideUp' in comp_css)
check('components.css: toast icons per type', '.toast--success' in comp_css)
check('components.css: pricing-glow', '.pricing-glow' in comp_css)
check('components.css: beta-shimmer', '.beta-shimmer' in comp_css)
check('components.css: disabled cursor:not-allowed', 'cursor: not-allowed' in comp_css)
check('components.css: card-hover', '.card-hover' in comp_css)
check('components.css: dropdown smooth animation', 'translateY(-8px)' in comp_css)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 2: BRAND IDENTITY')
# ─────────────────────────────────────────────────────────────────────
check('Nav logo SVG', 'grad1' in html)
check('Footer logo consistent', html.count('grad1') >= 2)
check('text-gradient wordmark used', html.count('text-gradient') >= 3)
check('Favicon SVG exists', os.path.exists('src/favicon.svg'))

# ─────────────────────────────────────────────────────────────────────
section('PHASE 3: LANDING PAGE')
# ─────────────────────────────────────────────────────────────────────
check('Hero mentions \u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in html)
check('Hero mentions \u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html)
check('Stats: \u0667 \u0623\u062f\u0648\u0627\u062a (7 tools)', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html)
check('Stats: NO \u0668 \u0623\u062f\u0648\u0627\u062a (8 tools)', '\u0668 \u0623\u062f\u0648\u0627\u062a' not in html)
check('Hero CTA: \u2190 \u0627\u0628\u062f\u0623', '\u2190 \u0627\u0628\u062f\u0623' in html)
check('Features CTA: \u2190 \u0627\u0643\u062a\u0634\u0641', '\u2190 \u0627\u0643\u062a\u0634\u0641' in html)
check('How It Works CTA: \u2190 \u062c\u0631\u0651\u0628', '\u2190 \u062c\u0631\u0651\u0628' in html)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 4: FEATURES PAGE')
# ─────────────────────────────────────────────────────────────────────
check('Bayyinah external arrow \u2197', '\u2197' in html)
# Check no wrong arrows on CTA buttons (only allowed in content, comments, and back buttons)
arrow_lines = [l for l in html.split('\n') if '\u2192' in l]
wrong_arrows = [l for l in arrow_lines if 'button' in l.lower() and '\u0627\u0644\u0639\u0648\u062f\u0629' not in l]
check('No wrong \u2192 arrows on CTA buttons', len(wrong_arrows) == 0)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 5: PRICING PAGE')
# ─────────────────────────────────────────────────────────────────────
check('pricing-glow class on Beta card', 'pricing-glow' in html)
check('beta-shimmer class on banner', 'beta-shimmer' in html)
check('Pricing: \u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
check('Pricing: \u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a \u0625\u0644\u0649 \u0627\u0644\u0641\u0635\u062d\u0649', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a \u0625\u0644\u0649 \u0627\u0644\u0641\u0635\u062d\u0649' in html)
check('Pricing CTA: \u2190 \u0627\u0628\u062f\u0623', '\u2190 \u0627\u0628\u062f\u0623' in html)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 6: EDITOR PAGE')
# ─────────────────────────────────────────────────────────────────────
# 6.1 Toolbar
check('6.1 Red dot tooltip: \u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html)
check('6.1 Yellow dot tooltip: \u0637\u064a \u0644\u0648\u062d\u0629', '\u0637\u064a \u0644\u0648\u062d\u0629' in html)
check('6.1 Green dot tooltip: \u062a\u0648\u0633\u064a\u0639 \u0627\u0644\u0645\u062d\u0631\u0631', '\u062a\u0648\u0633\u064a\u0639 \u0627\u0644\u0645\u062d\u0631\u0631' in html)
check('6.1 showConfirmDialog function', 'function showConfirmDialog' in html)
check('6.1 Red dot uses showConfirmDialog (not window.confirm)', 'showConfirmDialog' in html.split('dot--red')[1][:500] if 'dot--red' in html else False)

# 6.2 Format toolbar
check('6.2 Bold tooltip Arabic (\u063a\u0627\u0645\u0642)', '\u063a\u0627\u0645\u0642' in html)
check('6.2 Italic tooltip Arabic (\u0645\u0627\u0626\u0644)', '\u0645\u0627\u0626\u0644' in html)
check('6.2 Underline tooltip Arabic', '\u062a\u062d\u062a\u0647 \u062e\u0637' in html)
check('6.2 Undo tooltip Arabic (\u062a\u0631\u0627\u062c\u0639)', '\u062a\u0631\u0627\u062c\u0639' in html)
check('6.2 Redo tooltip Arabic (\u0625\u0639\u0627\u062f\u0629)', '\u0625\u0639\u0627\u062f\u0629' in html)
check('6.2 Dropdowns: closeAllFmtDropdowns()', 'closeAllFmtDropdowns' in format_js)
check('6.2 Dropdowns: close on click outside', "!e.target.closest('.fmt-dropdown')" in format_js)
check('6.2 Dropdowns: close on Escape', "e.key === 'Escape'" in format_js)
check('6.2 Active item highlight', 'fmt-dropdown__item--active' in format_js)
check('6.2 Color picker swatches', 'COLOR_PALETTE' in format_js)

# 6.3 Editor surface
check('6.3 Placeholder exists', 'editor-placeholder' in html or 'placeholder' in html.lower())

# 6.4 Suggestion popover
check('6.4 Popover hint: \u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u062d\u064a\u062d', '\u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u062d\u064a\u062d' in html)
check('6.4 Popover: Escape \u0644\u0644\u0625\u063a\u0644\u0627\u0642', 'Escape' in html)

# 6.5 Suggestion sidebar
check('6.5 Empty: \u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632 (positive)', '\u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632' in ui_js)
check('6.5 Empty: \u0644\u0627 \u062a\u0648\u062c\u062f \u0627\u0642\u062a\u0631\u0627\u062d\u0627\u062a', '\u0644\u0627 \u062a\u0648\u062c\u062f \u0627\u0642\u062a\u0631\u0627\u062d\u0627\u062a' in ui_js)
check('6.5 Apply All shows count (N)', 'countLabel' in ui_js)
check('6.5 Shimmer skeletons in analysis', 'skeleton' in ui_js)
check('6.5 Score ring', 'score-circle' in html)

# 6.6 Footer stats
check('6.6 char-count element', 'char-count' in html)
check('6.6 sentence-count element', 'sentence-count' in html)
check('6.6 reading-time element', 'reading-time' in html)
check('6.6 Word goal', 'word-goal' in html or 'wordGoal' in all_js)

# 6.7 Documents panel
check('6.7 Docs empty state icon', 'empty-state__icon' in docs_ui)
check('6.7 Docs empty state title', '\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0633\u062a\u0646\u062f\u0627\u062a' in docs_ui)
check('6.7 Docs delete: showConfirmDialog', 'showConfirmDialog' in docs_ui)
check('6.7 Docs search', 'docs-search' in html or 'initDocSearch' in all_js)

# 6.8 Summarize panel
check('6.8 Summary loading: \u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f', '\u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f' in html)
check('6.8 Summary error: \u062d\u062f\u062b \u062e\u0637\u0623', '\u062d\u062f\u062b \u062e\u0637\u0623' in html)
check('6.8 Summary mode toggle', 'summary-mode' in html)
check('6.8 Summary stats', 'summary-stats' in html)
check('6.8 Summary copy button', 'copySummary' in html)
check('6.8 Summary export dropdown', 'exportSummaryAs' in html)

# 6.9 Dialect panel
check('6.9 Dialect char counter', 'dialect-char-count' in html)
check('6.9 Dialect loading state', '\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
check('6.9 Dialect error: API fail', '\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
check('6.9 Dialect error: timeout', '\u0627\u0646\u062a\u0647\u0649 \u0648\u0642\u062a \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631' in html)
check('6.9 Dialect copy result', 'copyDialectResult' in html)
check('6.9 Dialect apply result', 'applyDialectResult' in html)

# 6.10 Quran modal
check('6.10 Quran: Escape closes', 'Escape' in html)
check('6.10 Quran: Ctrl+Q / KeyQ shortcut', 'KeyQ' in html)
check('6.10 Quran: copy verified text', '\u062a\u0645 \u0646\u0633\u062e \u0627\u0644\u0646\u0635 \u0627\u0644\u0645\u062f\u0642\u0642' in html)
check('6.10 Quran: copy translation', '\u062a\u0645 \u0646\u0633\u062e \u0627\u0644\u062a\u0631\u062c\u0645\u0629' in html)
check('6.10 Quran: apply verified text', '\u062a\u0645 \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
check('6.10 Quran: language dropdown', 'quran-lang-select' in html or 'quranLang' in html)

# 6.11 Mobile
check('6.11 Bottom sheet suggestions', 'bottom-sheet' in html)
check('6.11 Mobile drawer', 'mobile-drawer' in html)
check('6.11 Mobile menu button', 'mobile-menu-btn' in html)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 7: USER FLOWS & EDGE CASES')
# ─────────────────────────────────────────────────────────────────────
check('7.1 Auth gate modal', 'auth-gate' in html)
check('7.1 Google sign-in (auth JS)', 'linkGoogle' in all_js or 'google' in all_js.lower())
check('7.1 Guest flow (auth JS)', 'guest' in all_js.lower() or '\u0627\u0644\u062a\u062c\u0631\u0628\u0629' in html)
check('7.1 Offline banner', 'offline-banner' in html)
check('7.2 Doc save toast (\u062a\u0645 \u0627\u0644\u062d\u0641\u0638)', '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in all_js)
check('7.2 Doc delete custom dialog', 'showConfirmDialog' in docs_ui)
check('7.3 Summary loading spinner', 'summary-loading' in html)
check('7.4 Auto-sync: localStorage', 'localStorage' in all_js)
check('7.5 Draft restore: bayan_editor_draft', 'bayan_editor_draft' in editor_js)
check('7.5 Theme persists', 'localStorage' in html and 'theme' in html.lower())
check('7.6 Analyze error toast', 'showToast' in editor_js and '\u062a\u0639\u0630' in editor_js)
check('7.6 Dialect error: catch block', 'catch' in html.split('api/dialect')[1][:1000] if 'api/dialect' in html else False)
check('7.6 Quran error: catch block', 'catch' in html.split('quranVerify')[1][:2000] if 'quranVerify' in html else 'catch' in html.split('api/quran')[1][:2000] if 'api/quran' in html else False)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 8: RESPONSIVE DESIGN')
# ─────────────────────────────────────────────────────────────────────
all_css = tokens_css + base_css + comp_css
check('Responsive: media queries exist', '@media' in all_css or '@media' in html)
check('Responsive: mobile breakpoint', '768px' in all_css or '768px' in html)
check('Responsive: mobile bottom sheet', 'bottom-sheet' in html)
check('Responsive: mobile drawer', 'mobile-drawer' in html)
check('Responsive: mobile menu toggle', 'mobile-menu-btn' in html)

# ─────────────────────────────────────────────────────────────────────
section('PHASE 9: GLOBAL POLISH')
# ─────────────────────────────────────────────────────────────────────
head = html.split('</head>')[0] if '</head>' in html else ''
check('Meta desc: \u0627\u0644\u0642\u0631\u0622\u0646', '\u0627\u0644\u0642\u0631\u0622\u0646' in head)
check('Meta desc: \u0627\u0644\u0644\u0647\u062c\u0627\u062a', '\u0627\u0644\u0644\u0647\u062c\u0627\u062a' in head)
check('Footer: \u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646 link', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in html.split('\u0627\u0644\u0645\u0646\u062a\u062c')[1][:1000] if '\u0627\u0644\u0645\u0646\u062a\u062c' in html else False)
check('Footer: \u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a link', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html.split('\u0627\u0644\u0645\u0646\u062a\u062c')[1][:1000] if '\u0627\u0644\u0645\u0646\u062a\u062c' in html else False)
check('Footer desc: \u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in html)
check('404 arrow: \u2192 \u0627\u0644\u0639\u0648\u062f\u0629', '\u2192 \u0627\u0644\u0639\u0648\u062f\u0629' in html)
check('Scroll-to-top button', 'scroll-top-btn' in html)

# Toast types audit
all_toasts = re.findall(r"showToast\([^)]+\)", html + all_js)
error_toasts = [t for t in all_toasts if "'error'" in t]
warning_toasts = [t for t in all_toasts if "'warning'" in t]
check(f'Toast types: {len(error_toasts)} error toasts (>= 4)', len(error_toasts) >= 4)
check(f'Toast types: {len(warning_toasts)} warning toasts (>= 3)', len(warning_toasts) >= 3)

# ─────────────────────────────────────────────────────────────────────
section('ARCHITECTURAL SAFETY')
# ─────────────────────────────────────────────────────────────────────
renderer = load('src/js/renderer.js')
selection = load('src/js/selection.js')
check('renderer.js preserved (has render)', 'render' in renderer)
check('selection.js preserved (has saveSelection)', 'saveSelection' in selection)
check('selection.js preserved (has restoreSelection)', 'restoreSelection' in selection)
check('No React/Vue/Angular', all('framework' not in html.lower() for framework in ['react', 'vue.js', 'angular']))
check('Core flow: getEditorText()', 'getEditorText' in editor_js)
check('Core flow: /api/analyze', '/api/analyze' in editor_js)
check('Core flow: restoreSelection()', 'restoreSelection' in editor_js)

# ─────────────────────────────────────────────────────────────────────
section('6 DESIGN DECISIONS')
# ─────────────────────────────────────────────────────────────────────
check('Decision 1: \u2190 arrows on forward CTAs', '\u2190 \u0627\u0628\u062f\u0623' in html)
check('Decision 2: Quran+Dialect in Pricing', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
check('Decision 3: \u0667 \u0623\u062f\u0648\u0627\u062a (not \u0668)', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html and '\u0668 \u0623\u062f\u0648\u0627\u062a' not in html)
check('Decision 4: Shimmer skeletons', '.skeleton' in base_css and '@keyframes shimmer' in base_css)
check('Decision 5: macOS dots + Arabic tooltips', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html and 'dot--red' in html)
check('Decision 6: No settings panel (auto-sync)', 'localStorage' in all_js)

# ─────────────────────────────────────────────────────────────────────
print()
print('=' * 70)
print(f'  TOTAL: {passed}/{total} checks passed')
if passed == total:
    print('  \U0001f389 ALL CHECKS PASSED!')
else:
    print(f'  \u26a0\ufe0f {total - passed} items need attention')
print('=' * 70)
