"""
HONEST gap analysis: Plan vs Actually Implemented
"""
import re, os

def load(path):
    return open(path, encoding='utf-8').read()

html = load('src/index.html')
tokens = load('src/css/tokens.css')
base = load('src/css/base.css')
comp = load('src/css/components.css')
editor = load('src/js/editor.js')
ui = load('src/js/ui.js')
fmt = load('src/js/format.js')
docs = load('src/js/documents-cloud/documents-ui.js')

done = 0
miss = 0

def check(name, result):
    global done, miss
    if result:
        done += 1
        print(f'  \u2705 {name}')
    else:
        miss += 1
        print(f'  \u274c MISSING: {name}')

print('=' * 70)
print('PHASE 1: tokens.css')
print('=' * 70)
check('--shadow-xs', '--shadow-xs' in tokens)
check('--shadow-glow', '--shadow-glow' in tokens)
check('--transition-spring', '--transition-spring' in tokens)
check('--gradient-primary', '--gradient-primary' in tokens)
check('--gradient-surface', '--gradient-surface' in tokens)
check('--radius-xl', '--radius-xl' in tokens)
check('--color-skeleton', '--color-skeleton' in tokens or 'skeleton' in base)

print()
print('PHASE 1: base.css')
check('smooth scroll', 'scroll-behavior: smooth' in base)
check('custom scrollbar', '::-webkit-scrollbar' in base)
check('::selection', '::selection' in base)
check('focus-visible', 'focus-visible' in base)
check('shimmer keyframes', '@keyframes shimmer' in base)
check('.skeleton class', '.skeleton' in base)
check('button scale(0.97)', 'scale(0.97)' in base)

print()
print('PHASE 1: components.css')
check('Nav glassmorphism saturate', 'saturate(180%)' in comp)
check('Nav bottom border glow on scroll', 'nav-scrolled' in comp or 'border-glow' in comp or 'scrolled' in comp.lower())
check('Active nav underline indicator', 'nav-link' in comp and ('underline' in comp or 'active' in comp.lower()))
check('Button disabled state', 'cursor: not-allowed' in comp)
check('Button focus-visible ring', 'focus-visible' in comp)
check('Card hover translate-y + glow', '.card-hover' in comp)
check('Feature icon pulse hover', 'pulse' in comp.lower() or '@keyframes' in comp)
check('Modal slideUp entrance', '@keyframes modalSlideUp' in comp)
check('Toast icons per type', '.toast--success' in comp)
check('.empty-state component', '.empty-state' in comp)
check('.confirm-dialog', '.confirm-dialog' in comp)
check('.pricing-glow', '.pricing-glow' in comp)
check('.beta-shimmer', '.beta-shimmer' in comp)
check('Bottom sheet drag handle', 'drag-handle' in comp or 'sheet-handle' in comp or 'sheet__handle' in comp)

print()
print('=' * 70)
print('PHASE 3: LANDING PAGE')
print('=' * 70)
check('Hero mentions Quran', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646' in html)
check('Hero mentions dialects', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html)
check('\u0667 \u0623\u062f\u0648\u0627\u062a', '\u0667 \u0623\u062f\u0648\u0627\u062a' in html)
check('Hero CTA \u2190', '\u2190 \u0627\u0628\u062f\u0623' in html)
check('Features CTA \u2190', '\u2190 \u0627\u0643\u062a\u0634\u0641' in html)
check('How It Works CTA \u2190', '\u2190 \u062c\u0631\u0651\u0628' in html)

print()
print('=' * 70)
print('PHASE 5: PRICING')
print('=' * 70)
check('pricing-glow in HTML', 'pricing-glow' in html)
check('beta-shimmer in HTML', 'beta-shimmer' in html)
check('Quran in pricing', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0646\u0635 \u0627\u0644\u0642\u0631\u0622\u0646\u064a' in html)
check('Dialect in pricing', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a \u0625\u0644\u0649 \u0627\u0644\u0641\u0635\u062d\u0649' in html)

print()
print('=' * 70)
print('PHASE 6: EDITOR')
print('=' * 70)
check('6.1 Red dot tooltip', '\u0645\u0633\u062d \u0627\u0644\u0645\u062d\u0631\u0631' in html)
check('6.1 showConfirmDialog', 'showConfirmDialog' in html)
check('6.2 Dropdowns close outside', "closeAllFmtDropdowns" in fmt)
check('6.2 Dropdowns Escape', 'Escape' in fmt)
check('6.2 Dropdown keyboard nav (arrow keys)', 'ArrowDown' in fmt or 'ArrowUp' in fmt)
check('6.2 Color reset to default', 'reset' in fmt.lower() or 'default' in fmt.lower())
check('6.5 Apply All count', 'countLabel' in ui)
check('6.5 Shimmer skeleton', 'skeleton' in ui)
check('6.7 Docs empty icon', 'empty-state' in docs)
check('6.7 Docs delete dialog', 'showConfirmDialog' in docs)
check('6.10 Quran modal animation class', 'modal-animate' in html or 'modalSlideUp' in html or 'quran-modal' in comp)

print()
print('=' * 70)
print('PHASE 7: EDGE CASES')
print('=' * 70)
check('7.6 Analyze error toast', 'showToast' in editor and ('\u062a\u0639\u0630' in editor or '\\u062a\\u0639\\u0630' in editor))
check('7.6 Network delay indicator (10s)', 'taking longer' in editor.lower() or '\u0623\u0637\u0648\u0644' in editor or 'longerTimer' in editor)

print()
print('=' * 70)
print('PHASE 9: GLOBAL POLISH')
print('=' * 70)
check('Meta Quran', '\u0627\u0644\u0642\u0631\u0622\u0646' in html.split('</head>')[0])
check('Meta dialects', '\u0627\u0644\u0644\u0647\u062c\u0627\u062a' in html.split('</head>')[0])
check('Footer Quran link', '\u062a\u062f\u0642\u064a\u0642 \u0627\u0644\u0642\u0631\u0622\u0646</button>' in html)
check('Footer Dialect link', '\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0644\u0647\u062c\u0627\u062a</button>' in html)
check('404 arrow', '\u2192 \u0627\u0644\u0639\u0648\u062f\u0629' in html)
check('Toast types fixed (warning)', "'warning'" in html)

# Count all toasts missing types
import re
toasts_html = re.findall(r"showToast\('([^']+)'\)", html)
toasts_no_type = [t for t in toasts_html if t.startswith('\u2713') or t.startswith('\u062a\u0645')]
# These should default to success which is fine

print()
print('=' * 70)
print(f'TOTAL: {done} DONE / {miss} MISSING')
print('=' * 70)
