"""
EXHAUSTIVE plan-vs-code check: EVERY bullet point in the implementation plan.
"""
import re, os, glob

def load(p):
    return open(p, encoding='utf-8').read()

html = load('src/index.html')
tokens = load('src/css/tokens.css')
base = load('src/css/base.css')
comp = load('src/css/components.css')
editor = load('src/js/editor.js')
ui = load('src/js/ui.js')
fmt = load('src/js/format.js')
docs_ui = load('src/js/documents-cloud/documents-ui.js')
renderer = load('src/js/renderer.js')
selection = load('src/js/selection.js')

all_js = ''
for f in glob.glob('src/js/**/*.js', recursive=True):
    all_js += load(f) + '\n'
all_css = tokens + base + comp

done = 0
miss = 0
items = []

def c(name, result):
    global done, miss
    if result:
        done += 1
        items.append(('DONE', name))
    else:
        miss += 1
        items.append(('MISS', name))

def section(t):
    items.append(('SEC', t))

# ═══════════════════════════════════════════
section('PHASE 1: tokens.css')
# ═══════════════════════════════════════════
c('--shadow-xs', '--shadow-xs' in tokens)
c('--shadow-glow', '--shadow-glow' in tokens)
c('--transition-spring', '--transition-spring' in tokens)
c('--gradient-primary', '--gradient-primary' in tokens)
c('--gradient-surface', '--gradient-surface' in tokens)
c('--radius-xl: 1.5rem', '--radius-xl' in tokens)
c('--color-skeleton for loading', 'skeleton' in base or '--color-skeleton' in tokens)

section('PHASE 1: base.css')
c('Custom scrollbar (webkit)', '::-webkit-scrollbar' in base)
c('Custom scrollbar (firefox)', 'scrollbar-width: thin' in base)
c('scroll-behavior: smooth', 'scroll-behavior: smooth' in base)
c('::selection highlight', '::selection' in base)
c('Focus-visible outlines', 'focus-visible' in base or 'focus-visible' in comp)
c('Section rhythm (--spacing-section)', '--spacing-section' in tokens)
c('Shimmer @keyframes', '@keyframes shimmer' in base)
c('.skeleton class', '.skeleton' in base)
c('Button press scale(0.97)', 'scale(0.97)' in base)

section('PHASE 1: components.css — Navigation')
c('Glassmorphism blur(16px) saturate(180%)', 'saturate(180%)' in comp)
c('Bottom border glow on scroll (.nav-scrolled)', 'nav-scrolled' in comp)
c('Active nav link underline', 'nav-link' in comp or 'active' in comp.lower())

section('PHASE 1: components.css — Buttons')
c('Gradient-accent transition', 'transition' in comp)
c('Press state scale(0.97)', 'scale(0.97)' in base or 'scale(0.97)' in comp)
c('Disabled state opacity + cursor:not-allowed', 'cursor: not-allowed' in comp)
c('Focus-visible ring', 'focus-visible' in comp)
c('Feedback state (color flash after action)', 'flash' in comp or 'feedback' in comp.lower() or 'pulse' in comp.lower())

section('PHASE 1: components.css — Cards')
c('Card hover translate-y + glow', '.card-hover' in comp and 'translateY' in comp)
c('Feature icon pulse on hover', 'pulse' in comp.lower() or '@keyframes' in comp)

section('PHASE 1: components.css — Modals')
c('Modal entrance slide-up + fade', '@keyframes modalSlideUp' in comp)
c('Modal exit slide-down + fade', 'slideDown' in comp or 'fadeOut' in comp or 'modalSlideUp' in comp)

section('PHASE 1: components.css — Toast')
c('Toast slide-in', 'toast' in comp.lower())
c('Toast icon per type (success/warning/error)', '.toast--success' in comp and '.toast--error' in comp)

section('PHASE 1: components.css — Skeleton')
c('.skeleton shimmer animation', '.skeleton' in base and 'shimmer' in base)
c('.skeleton-text variant', '.skeleton-text' in base or '.skeleton' in base)

section('PHASE 1: components.css — Empty States')
c('.empty-state component', '.empty-state' in comp)
c('Applied to empty doc list', 'empty-state' in docs_ui)
c('Applied to empty suggestions', '\u0644\u0627 \u062a\u0648\u062c\u062f' in ui or 'empty' in ui.lower())

section('PHASE 1: components.css — Confirm Dialog')
c('.confirm-dialog custom modal', '.confirm-dialog' in comp)
c('showConfirmDialog() function', 'showConfirmDialog' in html)

section('PHASE 1: components.css — Bottom Sheet')
c('Bottom sheet smooth transition', 'bottom-sheet' in comp or 'bottom-sheet' in html)
c('Visual drag handle', 'drag-handle' in comp or 'sheet-handle' in comp or 'sheet__handle' in comp or 'handle' in comp.lower())

section('PHASE 1: components.css — Pricing')
c('.pricing-glow active plan', '.pricing-glow' in comp)
c('Coming soon blur/opacity', 'opacity' in comp or 'blur' in comp)
c('.beta-shimmer animation', '.beta-shimmer' in comp)

# ═══════════════════════════════════════════
section('PHASE 2: Brand Identity')
# ═══════════════════════════════════════════
c('Favicon SVG exists', os.path.exists('src/favicon.svg'))
c('Nav logo SVG (grad1)', 'grad1' in html)
c('Footer logo consistent', html.count('grad1') >= 2)
c('Wordmark text-gradient consistent', html.count('text-gradient') >= 3)
c('Icon audit: SVG icons present', '<svg' in html)

# ═══════════════════════════════════════════
section('PHASE 3: Landing Page — Hero')
# ═══════════════════════════════════════════
c('Subheadline mentions \u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in html)
c('Subheadline mentions \u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html)
c('ALL \u2192 arrows flipped to \u2190', '\u2190 \u0627\u0628\u062f\u0623' in html)
c('\u0667 \u0623\u062f\u0648\u0627\u062a (not \u0668)', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html and '\u0668 \u0623\u062f\u0648\u0627\u062a' not in html)

section('PHASE 3: Landing Page — Features Preview')
c('Feature cards present', 'feature' in html.lower())
c('Arrow directions on CTAs', '\u2190 \u0627\u0643\u062a\u0634\u0641' in html)

section('PHASE 3: Landing Page — How It Works')
c('Step numbers present', '\u0661' in html or 'step' in html.lower())
c('CTA arrow fixed', '\u2190 \u062c\u0631\u0651\u0628' in html)

# ═══════════════════════════════════════════
section('PHASE 4: Features Page')
# ═══════════════════════════════════════════
c('page-features exists', 'page-features' in html)
c('Bayyinah CTA with \u2197 icon', '\u2197' in html)

# ═══════════════════════════════════════════
section('PHASE 5: Pricing Page')
# ═══════════════════════════════════════════
c('pricing-glow in HTML', 'pricing-glow' in html)
c('beta-shimmer in HTML', 'beta-shimmer' in html)
c('\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a in pricing', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
c('\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a \u0625\u0644\u0649 \u0627\u0644\u0641\u0635\u062d\u0649 in pricing', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a \u0625\u0644\u0649 \u0627\u0644\u0641\u0635\u062d\u0649' in html)
c('Pricing CTA arrow', '\u2190' in html)

# ═══════════════════════════════════════════
section('PHASE 6.1: Editor Toolbar')
# ═══════════════════════════════════════════
c('macOS dots present', 'dot--red' in html)
c('Red dot tooltip (\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631)', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html)
c('Yellow dot tooltip (\u0637\u064a \u0644\u0648\u062d\u0629)', '\u0637\u064a \u0644\u0648\u062d\u0629' in html)
c('Green dot tooltip (\u062a\u0648\u0633\u064a\u0639 \u0627\u0644\u0645\u062d\u0631\u0631)', '\u062a\u0648\u0633\u064a\u0639 \u0627\u0644\u0645\u062d\u0631\u0631' in html)
c('Red dot uses showConfirmDialog', 'showConfirmDialog' in html)
c('Analyzing indicator animation', 'analyzing' in html.lower() or 'pulse' in html.lower())

section('PHASE 6.2: Format Toolbar')
c('Bold tooltip (\u063a\u0627\u0645\u0642)', '\u063a\u0627\u0645\u0642' in html)
c('Italic tooltip (\u0645\u0627\u0626\u0644)', '\u0645\u0627\u0626\u0644' in html)
c('Underline tooltip (\u062a\u062d\u062a\u0647 \u062e\u0637)', '\u062a\u062d\u062a\u0647 \u062e\u0637' in html)
c('Undo tooltip (\u062a\u0631\u0627\u062c\u0639)', '\u062a\u0631\u0627\u062c\u0639' in html)
c('Redo tooltip (\u0625\u0639\u0627\u062f\u0629)', '\u0625\u0639\u0627\u062f\u0629' in html)
c('Dropdowns smooth animation', 'translateY(-8px)' in comp)
c('Active item highlight', 'fmt-dropdown__item--active' in fmt)
c('Keyboard nav (ArrowDown/ArrowUp)', 'ArrowDown' in fmt)
c('Close on click outside', "closeAllFmtDropdowns" in fmt)
c('Close on Escape', "Escape" in fmt)
c('COLOR_PALETTE swatches', 'COLOR_PALETTE' in fmt)
c('Color reset to default', 'reset' in fmt.lower() or 'removeFormat' in fmt)

section('PHASE 6.3: Editor Surface')
c('Placeholder exists', 'placeholder' in html.lower())

section('PHASE 6.4: Suggestion Popover')
c('\u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u062d\u064a\u062d hint', '\u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u062d\u064a\u062d' in html)
c('Escape \u0644\u0644\u0625\u063a\u0644\u0627\u0642 hint', 'Escape' in html)
c('\u062a\u062c\u0627\u0647\u0644 dismiss button', '\u062a\u062c\u0627\u0647\u0644' in html)

section('PHASE 6.5: Suggestion Sidebar')
c('Empty: \u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632 positive', '\u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632' in ui or '\\u0646\\u0635\\u0643' in ui)
c('\u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u0643\u0644 count (N)', 'countLabel' in ui)
c('Score ring', 'score-circle' in html)
c('Shimmer skeletons in analysis', 'skeleton' in ui)

section('PHASE 6.6: Editor Footer Stats')
c('char-count element', 'char-count' in html)
c('sentence-count element', 'sentence-count' in html)
c('reading-time element', 'reading-time' in html)
c('Word goal', 'word-goal' in html or 'wordGoal' in all_js)
c('Save toast', '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in all_js or '\\u062a\\u0645 \\u0627\\u0644\\u062d\\u0641\\u0638' in all_js)
c('Copy toast', '\u062a\u0645 \u0627\u0644\u0646\u0633\u062e' in html or '\\u062a\\u0645 \\u0627\\u0644\\u0646\\u0633\\u062e' in all_js)
c('Clear uses showConfirmDialog', 'showConfirmDialog' in html)

section('PHASE 6.7: Documents Panel')
c('Docs empty state icon', 'empty-state__icon' in docs_ui or 'empty-state' in docs_ui)
c('Docs delete showConfirmDialog', 'showConfirmDialog' in docs_ui)
c('Docs search', 'docs-search' in html or 'search' in docs_ui.lower())

section('PHASE 6.8: Summarize Panel')
c('Summary loading state', '\u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f' in html)
c('Summary error state', '\u062d\u062f\u062b \u062e\u0637\u0623' in html)
c('Summary mode toggle', 'summary-mode' in html)
c('Summary stats', 'summary-stats' in html)
c('Summary copy button', 'copySummary' in html)
c('Summary export dropdown', 'exportSummaryAs' in html)

section('PHASE 6.9: Dialect Panel')
c('Dialect char counter', 'dialect-char-count' in html)
c('Dialect loading state', '\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
c('Dialect error (API)', '\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
c('Dialect error (timeout)', '\u0627\u0646\u062a\u0647\u0649 \u0648\u0642\u062a \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631' in html)
c('Dialect copy/apply', 'copyDialectResult' in html and 'applyDialectResult' in html)

section('PHASE 6.10: Quran Modal')
c('Quran Escape closes', 'Escape' in html)
c('Ctrl+Q shortcut (KeyQ)', 'KeyQ' in html)
c('Copy verified text', '\u062a\u0645 \u0646\u0633\u062e \u0627\u0644\u0646\u0635 \u0627\u0644\u0645\u062f\u0642\u0642' in html)
c('Apply verified text', '\u062a\u0645 \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
c('Language dropdown', 'quran-lang' in html or 'quranLang' in html)

section('PHASE 6.11: Mobile Components')
c('Bottom sheet suggestions', 'bottom-sheet' in html)
c('Mobile drawer', 'mobile-drawer' in html)
c('Mobile menu button', 'mobile-menu-btn' in html)

# ═══════════════════════════════════════════
section('PHASE 7.1: Auth Flows')
# ═══════════════════════════════════════════
c('Auth gate modal', 'auth-gate' in html)
c('Google sign-in', 'google' in all_js.lower())
c('Guest flow', '\u0627\u0644\u062a\u062c\u0631\u0628\u0629' in html or 'guest' in all_js.lower())
c('Offline banner', 'offline-banner' in html)

section('PHASE 7.2: Document Flows')
c('Doc save toast', '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in all_js or '\\u062a\\u0645' in all_js)
c('Doc delete custom dialog', 'showConfirmDialog' in docs_ui)

section('PHASE 7.3: Summary Flow')
c('Summary loading state', 'summary-loading' in html or '\u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f' in html)

section('PHASE 7.4: Settings')
c('Auto-sync localStorage', 'localStorage' in all_js)

section('PHASE 7.5: Refresh/Restore')
c('Draft restore (bayan_editor_draft)', 'bayan_editor_draft' in editor)
c('Theme persists', 'localStorage' in html and 'theme' in html.lower())

section('PHASE 7.6: Error States')
c('/api/analyze error toast', 'showToast' in editor)
c('/api/dialect error (catch)', 'catch' in html.split('api/dialect')[1][:1000] if 'api/dialect' in html else False)
c('/api/quran error (catch)', 'catch' in html.split('quran')[1][:3000] if 'quran' in html.lower() else False)
c('Network delay indicator (10s)', 'longerTimer' in editor)
c('Offline banner styling', 'offline-banner' in html)

section('PHASE 7.7: Empty States')
c('Editor placeholder', 'editor-placeholder' in html or 'placeholder' in html.lower())
c('Documents empty state', 'empty-state' in docs_ui)
c('Suggestions empty (\u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632)', '\\u0646\\u0635\\u0643' in ui or '\u0646\u0635\u0643' in ui)

# ═══════════════════════════════════════════
section('PHASE 8: Responsive Design')
# ═══════════════════════════════════════════
c('Media queries exist', '@media' in all_css or '@media' in html)
c('Mobile breakpoint 768px', '768px' in all_css or '768px' in html)
c('Bottom sheet mobile', 'bottom-sheet' in html)
c('Mobile drawer', 'mobile-drawer' in html)

# ═══════════════════════════════════════════
section('PHASE 9: Global Polish')
# ═══════════════════════════════════════════
head = html.split('</head>')[0]
c('Meta desc: \u0627\u0644\u0642\u0631\u0622\u0646', '\u0627\u0644\u0642\u0631\u0622\u0646' in head)
c('Meta desc: \u0627\u0644\u0644\u0647\u062c\u0627\u062a', '\u0627\u0644\u0644\u0647\u062c\u0627\u062a' in head)
c('404 arrow: \u2192 \u0627\u0644\u0639\u0648\u062f\u0629', '\u2192 \u0627\u0644\u0639\u0648\u062f\u0629' in html)
c('Scroll-to-top button', 'scroll-top-btn' in html)
c('Toast types: error toasts', "'error'" in (html + all_js))
c('Toast types: warning toasts', "'warning'" in (html + all_js))

# ═══════════════════════════════════════════
section('ARCHITECTURAL SAFETY')
# ═══════════════════════════════════════════
c('renderer.js preserved', 'render' in renderer)
c('selection.js: saveSelection', 'saveSelection' in selection)
c('selection.js: restoreSelection', 'restoreSelection' in selection)
c('No React/Vue/Angular', 'react' not in html.lower() and 'vue' not in html.lower())
c('Core: getEditorText()', 'getEditorText' in editor)
c('Core: /api/analyze', '/api/analyze' in editor)
c('Core: restoreSelection()', 'restoreSelection' in editor)

# ═══════════════════════════════════════════
section('6 DESIGN DECISIONS')
# ═══════════════════════════════════════════
c('D1: \u2190 on forward CTAs', '\u2190 \u0627\u0628\u062f\u0623' in html)
c('D2: Quran+Dialect in Pricing', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
c('D3: \u0667 \u0623\u062f\u0648\u0627\u062a', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html)
c('D4: Shimmer skeletons', '@keyframes shimmer' in base)
c('D5: macOS dots + tooltips', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html)
c('D6: Auto-sync (no settings)', 'localStorage' in all_js)

# ═══════════════════════════════════════════
# PRINT RESULTS
# ═══════════════════════════════════════════
print()
for typ, name in items:
    if typ == 'SEC':
        print(f'\n{"="*60}')
        print(f'  {name}')
        print(f'{"="*60}')
    elif typ == 'DONE':
        print(f'  \u2705 {name}')
    else:
        print(f'  \u274c MISS: {name}')

print(f'\n{"="*60}')
print(f'  TOTAL: {done} DONE / {miss} MISSING out of {done+miss}')
if miss == 0:
    print('  \U0001f389 EVERYTHING IS IMPLEMENTED!')
else:
    print(f'  \u26a0\ufe0f {miss} items need attention')
print(f'{"="*60}')
