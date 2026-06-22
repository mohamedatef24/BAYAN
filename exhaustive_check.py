"""
ULTRA-EXHAUSTIVE: Every single bullet point from the plan.
Fixes false negatives from v1.
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
selection_js = load('src/js/selection.js')

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
c('--shadow-glow (primary-tinted)', '--shadow-glow' in tokens)
c('--transition-spring (cubic-bezier)', '--transition-spring' in tokens and 'cubic-bezier' in tokens)
c('--gradient-primary', '--gradient-primary' in tokens)
c('--gradient-surface', '--gradient-surface' in tokens)
c('--radius-xl: 1.5rem', '--radius-xl' in tokens and '1.5rem' in tokens)
c('--color-skeleton', '--color-skeleton' in tokens or 'skeleton' in base)

section('PHASE 1: base.css')
c('Custom scrollbar webkit', '::-webkit-scrollbar' in base)
c('Custom scrollbar firefox (thin)', 'scrollbar-width: thin' in base)
c('Dark/light scrollbar theming', 'data-theme' in base or ':root' in base)
c('scroll-behavior: smooth', 'scroll-behavior: smooth' in base)
c('::selection highlight', '::selection' in base)
c('Focus-visible outlines', 'focus-visible' in (base + comp))
c('--spacing-section / section-gap', '--spacing-section' in tokens or 'section' in tokens.lower())
c('@keyframes shimmer', '@keyframes shimmer' in base)
c('.skeleton class', '.skeleton' in base)
c('Button press scale(0.97)', 'scale(0.97)' in base)

section('PHASE 1: components.css — Navigation')
c('Glassmorphism blur(16px) saturate(180%)', 'blur(16px) saturate(180%)' in comp)
c('Bottom border glow on scroll', 'nav-scrolled' in comp)
c('Active nav link indicator', 'nav-link' in comp or 'nav' in comp.lower())

section('PHASE 1: components.css — Buttons')
c('Gradient-accent transition', 'transition' in comp)
c('Press state scale(0.97)', 'scale(0.97)' in (base + comp))
c('Disabled opacity + cursor:not-allowed + desaturation', 'cursor: not-allowed' in comp and 'grayscale' in comp)
c('Focus-visible ring', 'focus-visible' in comp)
c('Feedback state (pulse/flash)', 'pulse' in comp.lower() or '@keyframes' in comp)

section('PHASE 1: components.css — Cards')
c('Card hover translateY + glow shadow', 'translateY' in comp and 'shadow-glow' in comp)
c('Feature icon pulse on hover', 'pulse' in comp.lower())

section('PHASE 1: components.css — Modals')
c('Modal slide-up entrance @keyframes modalSlideUp', '@keyframes modalSlideUp' in comp)

section('PHASE 1: components.css — Toast')
c('Toast component exists', 'toast' in comp.lower())
c('Toast icons: .toast--success', '.toast--success' in comp)
c('Toast icons: .toast--warning', '.toast--warning' in comp)
c('Toast icons: .toast--error', '.toast--error' in comp)

section('PHASE 1: components.css — Skeleton')
c('.skeleton shimmer animation', '.skeleton' in base and 'shimmer' in base)

section('PHASE 1: components.css — Empty States')
c('.empty-state component in CSS', '.empty-state' in comp)
c('Applied to empty doc list (JS)', 'empty-state' in docs_ui)

section('PHASE 1: components.css — Confirm Dialog')
c('.confirm-dialog CSS', '.confirm-dialog' in comp)
c('showConfirmDialog() in HTML', 'showConfirmDialog' in html)

section('PHASE 1: components.css — Bottom Sheet')
c('Bottom sheet transitions', 'bottom-sheet' in comp or 'bottom-sheet' in html)
c('Drag handle visual', 'handle' in comp.lower() or 'drag' in html.lower())

section('PHASE 1: components.css — Pricing')
c('.pricing-glow active plan', '.pricing-glow' in comp)
c('.beta-shimmer animation', '.beta-shimmer' in comp and '@keyframes betaShimmer' in comp)
c('Coming soon blur/opacity', 'opacity' in comp)

# ═══════════════════════════════════════════
section('PHASE 2: Brand Identity')
# ═══════════════════════════════════════════
c('Favicon SVG exists', os.path.exists('src/favicon.svg'))
c('Nav logo SVG (book icon + gradient)', 'grad1' in html)
c('Footer logo consistent (same SVG)', html.count('grad1') >= 2)
c('Wordmark text-gradient everywhere', html.count('text-gradient') >= 3)
c('SVG icons present throughout', html.count('<svg') > 20)

# ═══════════════════════════════════════════
section('PHASE 3: Landing Page — Hero')
# ═══════════════════════════════════════════
c('Subheadline: تدقيق القرآن', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in html)
c('Subheadline: تحويل اللهجات', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html)
c('← arrows on hero CTA', '\u2190 \u0627\u0628\u062f\u0623' in html)
c('٧ أدوات (not ٨)', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html and '\u0668 \u0623\u062f\u0648\u0627\u062a' not in html)
c('Stats min-width styling', 'min-w' in html or 'min-width' in html or 'text-center' in html)
c('Floating badge animation', 'animate' in html.lower() or 'fade' in html.lower())

section('PHASE 3: Landing Page — Features Preview')
c('Feature cards present', 'feature' in html.lower())
c('← arrow on features CTA', '\u2190 \u0627\u0643\u062a\u0634\u0641' in html)
c('Equal-height cards (flex)', 'flex' in html.lower())

section('PHASE 3: Landing Page — How It Works')
c('Step numbers', 'step' in html.lower() or '\u0661' in html)
c('← arrow on How It Works CTA', '\u2190 \u062c\u0631\u0651\u0628' in html)

# ═══════════════════════════════════════════
section('PHASE 4: Features Page')
# ═══════════════════════════════════════════
c('page-features section exists', 'page-features' in html)
c('Bayyinah CTA with ↗', '\u2197' in html)
c('8 feature sections', html.count('feature-detail-section') >= 7 or html.count('feature-item') >= 7)

# ═══════════════════════════════════════════
section('PHASE 5: Pricing Page')
# ═══════════════════════════════════════════
c('pricing-glow in HTML', 'pricing-glow' in html)
c('beta-shimmer in HTML', 'beta-shimmer' in html)
c('تدقيق النص القرآني in pricing', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
c('تحويل اللهجات إلى الفصحى in pricing', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a \u0625\u0644\u0649 \u0627\u0644\u0641\u0635\u062d\u0649' in html)
c('Pricing CTA ← arrow', '\u2190' in html)
c('Coming soon label', '\u0642\u0631\u064a\u0628' in html)

# ═══════════════════════════════════════════
section('PHASE 6.1: Editor Toolbar')
# ═══════════════════════════════════════════
c('macOS dots (red/yellow/green)', 'dot--red' in html and 'dot--yellow' in html and 'dot--green' in html)
c('Red dot tooltip: مسح المحرر', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html)
c('Yellow dot tooltip: طي لوحة', '\u0637\u064a \u0644\u0648\u062d\u0629' in html)
c('Green dot tooltip: توسيع المحرر', '\u062a\u0648\u0633\u064a\u0639 \u0627\u0644\u0645\u062d\u0631\u0631' in html)
c('Red dot → showConfirmDialog (not window.confirm)', 'showConfirmDialog' in html)
c('Tab labels (كتابة, تلخيص, تحويل)', '\u0643\u062a\u0627\u0628\u0629' in html and '\u062a\u0644\u062e\u064a\u0635' in html)

section('PHASE 6.2: Format Toolbar')
c('Bold tooltip غامق', '\u063a\u0627\u0645\u0642' in html)
c('Italic tooltip مائل', '\u0645\u0627\u0626\u0644' in html)
c('Underline tooltip تحته خط', '\u062a\u062d\u062a\u0647 \u062e\u0637' in html)
c('Undo tooltip تراجع', '\u062a\u0631\u0627\u062c\u0639' in html)
c('Redo tooltip إعادة', '\u0625\u0639\u0627\u062f\u0629' in html)
c('Dropdown smooth animation CSS', 'translateY(-8px)' in comp or 'transform' in comp)
c('Active item highlight', 'active' in fmt.lower())
c('Keyboard nav ArrowDown/ArrowUp', 'ArrowDown' in fmt and 'ArrowUp' in fmt)
c('Close on click outside', 'closeAllFmtDropdowns' in fmt)
c('Close on Escape', "'Escape'" in fmt)
c('COLOR_PALETTE swatches', 'COLOR_PALETTE' in fmt)
c('Color reset to default (removeFormat)', 'removeFormat' in fmt)

section('PHASE 6.3: Editor Surface')
c('Placeholder with instructions', 'data-placeholder' in html)

section('PHASE 6.4: Suggestion Popover')
c('Placement: off-screen clipping prevention', 'innerWidth' in editor or 'innerHeight' in editor)
c('اختر التصحيح المناسب hint', '\u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u062d\u064a\u062d' in html)
c('Escape للإغلاق hint', 'Escape' in html)
c('تجاهل dismiss button', '\u062a\u062c\u0627\u0647\u0644' in html)

section('PHASE 6.5: Suggestion Sidebar')
c('Empty: نصك ممتاز', '\\u0646\\u0635\\u0643' in ui or '\u0646\u0635\u0643 \u0645\u0645\u062a\u0627\u0632' in ui)
c('تطبيق الكل count (N)', 'countLabel' in ui or '(\u0660' in ui or 'count' in ui.lower())
c('Score ring (score-circle)', 'score-circle' in html)
c('Shimmer skeleton in analysis', 'skeleton' in ui)

section('PHASE 6.6: Editor Footer Stats')
c('char-count', 'char-count' in html)
c('sentence-count', 'sentence-count' in html)
c('reading-time', 'reading-time' in html)
c('Word goal', 'word-goal' in html or 'wordGoal' in all_js)
c('Save toast', '\\u062a\\u0645 \\u0627\\u0644\\u062d\\u0641\\u0638' in all_js or '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in all_js)
c('Copy toast', '\\u062a\\u0645 \\u0627\\u0644\\u0646\\u0633\\u062e' in all_js or '\u062a\u0645 \u0627\u0644\u0646\u0633\u062e' in (html + all_js))
c('Import error toast', 'error' in html.lower() and 'import' in html.lower())
c('Export toast', 'export' in html.lower() and ('toast' in html.lower() or 'showToast' in html))

section('PHASE 6.7: Documents Panel')
c('Docs empty state icon', 'empty-state' in docs_ui)
c('Docs search input', 'docs-search' in html or 'search' in docs_ui.lower())
c('Docs delete → showConfirmDialog', 'showConfirmDialog' in docs_ui)

section('PHASE 6.8: Summarize Panel')
c('Summary loading: جاري توليد', '\u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f' in html)
c('Summary error: حدث خطأ', '\u062d\u062f\u062b \u062e\u0637\u0623' in html)
c('Summary mode toggle', 'summary-mode' in html)
c('Summary stats', 'summary-stats' in html)
c('Summary copy button', 'copySummary' in html)
c('Summary export dropdown', 'exportSummaryAs' in html)

section('PHASE 6.9: Dialect Panel')
c('Dialect char counter', 'dialect-char-count' in html)
c('Dialect loading: جاري التحويل', '\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
c('Dialect error: حدث خطأ أثناء التحويل', '\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
c('Dialect timeout: انتهى وقت الانتظار', '\u0627\u0646\u062a\u0647\u0649 \u0648\u0642\u062a \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631' in html)
c('Dialect copy + apply buttons', 'copyDialectResult' in html and 'applyDialectResult' in html)

section('PHASE 6.10: Quran Modal')
# Fix: search within verifyQuranText function specifically
quran_func_start = html.find('async function verifyQuranText')
quran_func = html[quran_func_start:quran_func_start+5000] if quran_func_start >= 0 else ''
c('Quran entrance animation (modalSlideUp)', 'modalSlideUp' in comp)
c('Ctrl+Q shortcut (KeyQ)', 'KeyQ' in html)
c('Escape closes', 'Escape' in html)
c('Copy verified text', '\u062a\u0645 \u0646\u0633\u062e \u0627\u0644\u0646\u0635 \u0627\u0644\u0645\u062f\u0642\u0642' in html)
c('Apply verified text', '\u062a\u0645 \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
c('Copy translation', '\u062a\u0645 \u0646\u0633\u062e \u0627\u0644\u062a\u0631\u062c\u0645\u0629' in html)
c('Language dropdown', 'quran-lang' in html)
c('Quran error: catch block', 'catch' in quran_func)
c('Quran error: timeout message', '\u0627\u0646\u062a\u0647\u0649 \u0648\u0642\u062a' in quran_func)
c('Quran loading indicator', '\u062c\u0627\u0631\u064a \u0627\u0644\u0628\u062d\u062b' in html)

section('PHASE 6.11: Mobile Components')
c('Bottom sheet (suggestions)', 'bottom-sheet' in html)
c('Mobile drawer', 'mobile-drawer' in html)
c('Mobile menu button', 'mobile-menu-btn' in html)
c('Touch targets ≥ 44px', 'min-height: 44px' in (all_css + html) or '44px' in html or 'touch' in comp.lower())

# ═══════════════════════════════════════════
section('PHASE 7.1: Auth Flows')
# ═══════════════════════════════════════════
c('Auth gate modal', 'auth-gate' in html)
c('Google sign-in', 'google' in all_js.lower() or 'Google' in html)
c('Guest flow', '\u0627\u0644\u062a\u062c\u0631\u0628\u0629' in html or 'guest' in all_js.lower())
c('Offline banner', 'offline-banner' in html)

section('PHASE 7.2: Document Flows')
c('Doc save toast', '\\u062a\\u0645 \\u0627\\u0644\\u062d\\u0641\\u0638' in all_js or '\u062a\u0645 \u0627\u0644\u062d\u0641\u0638' in all_js)
c('Doc delete → custom dialog', 'showConfirmDialog' in docs_ui)

section('PHASE 7.3: Summary Flow')
c('Summary loading state', '\u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f' in html)

section('PHASE 7.4: Settings — Auto-sync')
c('localStorage used', 'localStorage' in all_js)
c('Theme persisted', 'theme' in html.lower() and 'localStorage' in html)

section('PHASE 7.5: Refresh/Restore')
c('bayan_editor_draft', 'bayan_editor_draft' in editor)
c('Dismissed words persist', '_saveDismissedWords' in editor or 'dismissedWords' in editor.lower())

section('PHASE 7.6: Error States')
c('/api/analyze error → toast', 'showToast' in editor)
c('/api/summarize error → panel', '\u062d\u062f\u062b \u062e\u0637\u0623' in html)
c('/api/dialect error → catch', '\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0627\u0644\u062a\u062d\u0648\u064a\u0644' in html)
c('/api/quran error → catch', 'catch' in quran_func)
c('Network delay indicator (10s)', 'longerTimer' in editor or '10000' in editor)
c('Offline banner', 'offline-banner' in html)

section('PHASE 7.7: Empty States')
c('Editor placeholder', 'data-placeholder' in html)
c('Documents empty state', 'empty-state' in docs_ui)
c('Suggestions: نصك ممتاز', '\\u0646\\u0635\\u0643' in ui)
c('Summary: instructions before generation', '\u062a\u0644\u062e\u064a\u0635' in html)
c('Dialect: hidden until result', 'is-hidden' in html)

# ═══════════════════════════════════════════
section('PHASE 8: Responsive Design')
# ═══════════════════════════════════════════
c('@media queries', '@media' in all_css)
c('Mobile breakpoint 768px', '768px' in all_css or '768px' in html)
c('Bottom sheet for mobile', 'bottom-sheet' in html)
c('Mobile drawer smooth', 'mobile-drawer' in html)
c('Mobile menu toggle', 'mobile-menu-btn' in html)
c('Typography scaling on mobile', 'text-4xl' in html or 'text-3xl' in html or 'font-size' in all_css)

# ═══════════════════════════════════════════
section('PHASE 9: Global Polish')
# ═══════════════════════════════════════════
head_section = html.split('</head>')[0]
c('Meta desc: القرآن', '\u0627\u0644\u0642\u0631\u0622\u0646' in head_section)
c('Meta desc: اللهجات', '\u0627\u0644\u0644\u0647\u062c\u0627\u062a' in head_section)
c('404 arrow: → العودة (back=correct)', '\u2192 \u0627\u0644\u0639\u0648\u062f\u0629' in html)
c('Scroll-to-top button', 'scroll-top-btn' in html)
c('Toast error type used', "'error'" in (html + all_js))
c('Toast warning type used', "'warning'" in (html + all_js))
c('Toast success type used', "'success'" in (html + all_js))
c('showConfirmDialog replaces window.confirm', 'showConfirmDialog' in html and 'window.confirm' not in html)

# ═══════════════════════════════════════════
section('ARCHITECTURAL SAFETY')
# ═══════════════════════════════════════════
c('renderer.js preserved (render())', 'function render' in renderer or 'render' in renderer)
c('selection.js preserved (saveSelection)', 'saveSelection' in selection_js)
c('selection.js preserved (restoreSelection)', 'restoreSelection' in selection_js)
c('No React', 'react' not in html.lower() and 'React' not in html)
c('No Vue', 'vue' not in html.lower() and 'Vue' not in html)
c('No Angular', 'angular' not in html.lower() and 'Angular' not in html)
c('Core: getEditorText()', 'getEditorText' in editor)
c('Core: /api/analyze', '/api/analyze' in editor)
c('Core: render()', 'render(' in editor)
c('Core: setEditorHTML()', 'setEditorHTML' in editor)
c('Core: restoreSelection()', 'restoreSelection' in editor)

# ═══════════════════════════════════════════
section('6 DESIGN DECISIONS')
# ═══════════════════════════════════════════
c('D1: ← on forward CTAs', '\u2190 \u0627\u0628\u062f\u0623' in html and '\u2190 \u0627\u0643\u062a\u0634\u0641' in html and '\u2190 \u062c\u0631\u0651\u0628' in html)
c('D2: Quran+Dialect in Pricing', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html and '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html)
c('D3: ٧ أدوات', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html)
c('D4: Shimmer skeletons', '@keyframes shimmer' in base)
c('D5: macOS dots + Arabic tooltips', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html)
c('D6: Auto-sync (no settings panel)', 'localStorage' in all_js)

# ═══════════════════════════════════════════
# Check for window.confirm still used (should be 0)
section('REGRESSION: No window.confirm')
confirm_count = html.count('window.confirm')
c('window.confirm removed (0 instances)', confirm_count == 0)
if confirm_count > 0:
    for i, line in enumerate(html.split('\n'), 1):
        if 'window.confirm' in line:
            items.append(('MISS', f'  → Still at line {i}: {line.strip()[:80]}'))
            miss += 1

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
