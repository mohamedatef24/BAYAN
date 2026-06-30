# Bayan Extension Parity Audit — Final Report

## Changes Made

### 1. sidepanel.js — P0 Syntax Error + Missing Handlers
**File:** `extension/sidepanel/sidepanel.js`

- **Fixed orphaned function body** at line 759: Added missing `function addApplyPageButton(anchorBtn, getText, source) {` declaration
- **Then removed the dead function entirely** — it was an abandoned programmatic approach; the actual buttons exist in sidepanel.html
- **Added missing `btnApplySummary` click handler** — button was referenced and unhidden on success but never had an event listener
- **Added missing `btnApplyQuran` click handler** — same issue

### 2. popup.css — Design System Realignment
**File:** `extension/popup.css`

Remapped all `--bayan-*` tokens from hardcoded indigo/harsh-red values to website `tokens.css` references:

| Token | Before | After |
|-------|--------|-------|
| `--bayan-primary` | `#6366f1` (indigo) | `var(--color-primary, #6BA3E0)` (blue) |
| `--bayan-primary-dark` | `#4f46e5` | `#5A8FCA` |
| `--bayan-primary-glow` | `rgba(99,102,241,0.25)` | `var(--focus-ring)` |
| `--bayan-spelling` | `#ef4444` | `var(--highlight-spelling-border, #E88A8A)` |
| `--bayan-grammar` | `#f59e0b` | `var(--highlight-grammar-border, #E4B35A)` |
| `--bayan-success` | `#22c55e` | `var(--color-success, #6BC98A)` |
| `--bayan-warning` | `#f59e0b` | `var(--color-warning, #E4B35A)` |
| `--bayan-error` | `#ef4444` | `var(--color-error, #E88A8A)` |
| `--bayan-text-muted` | `#6b6b80` | `var(--color-text-muted, #8A939F)` |
| `--bayan-font-arabic` | `'Noto Sans Arabic', 'Segoe UI'` | `var(--font-family-primary, 'Cairo', 'Tajawal')` |

Fixed hardcoded `rgba()` values in error highlights, badges, and button shadows to match website palette.

Added `--color-surface-hover` alias (maps to `--color-surface-elevated`).

### 3. popup.html — Added tokens.css + Cairo Font
**File:** `extension/popup.html`

- Added `<link rel="stylesheet" href="shared/css/tokens.css">` before popup.css — enables proper theme token resolution and dark/light switching
- Added Google Fonts preconnect + Cairo font import

### 4. sidepanel.html — Added tokens.css + Cairo Font
**File:** `extension/sidepanel/sidepanel.html`

- Same additions as popup.html — now both extension views load the shared design tokens

### 5. content-inline.css — Full Color Palette Alignment
**File:** `extension/content-inline.css`

Bulk-replaced all divergent colors across the entire file (~50 occurrences):

| Before | After | Count |
|--------|-------|-------|
| `#ef4444` → | `#E88A8A` | All spelling error colors |
| `#f59e0b` → | `#E4B35A` | All grammar error colors |
| `#6366f1` → | `#6BA3E0` | All primary/accent colors |
| `#4f46e5` → | `#5A8FCA` | All primary-dark variants |
| `#22c55e` → | `#6BC98A` | All success colors |
| `#818cf8` → | `#8BB8E8` | Primary-light variant |
| `rgba(239,68,68,*)` → | `rgba(232,138,138,*)` | Spelling rgba |
| `rgba(245,158,11,*)` → | `rgba(228,179,90,*)` | Grammar rgba |
| `rgba(99,102,241,*)` → | `rgba(107,163,224,*)` | Primary rgba |
| `#1a1a24` → | `#1A1D26` | Surface color |
| `#22222e` → | `#242833` | Elevated surface |
| `#f0f0f5` → | `#ECEEF2` | Text color |
| `#6b6b80` → | `#8A939F` | Muted text |
| `#9898ad` → | `#B4BBC6` | Secondary text |

Added Cairo as first-choice font in tooltip/modal font stacks.

### 6. popup.js — Dead Code Cleanup
**File:** `extension/popup.js`

- Removed unused `btnApplySummary`, `btnApplyDialect`, `btnApplyQuran` declarations (elements don't exist in popup.html)
- Removed dead `btnApplyDialect` click handler that referenced undefined `writeBackToPage` and `sourceSelectionText`
- Removed dead `btnApplySummary.classList.remove('is-hidden')` and `btnApplyDialect.classList.remove('is-hidden')` calls

---

## Files Modified

| File | Changes |
|------|---------|
| `extension/sidepanel/sidepanel.js` | Fixed syntax error, added missing handlers, removed dead function |
| `extension/popup.css` | Full design token realignment to website palette |
| `extension/popup.html` | Added tokens.css + Cairo font loading |
| `extension/sidepanel/sidepanel.html` | Added tokens.css + Cairo font loading |
| `extension/content-inline.css` | Replaced ~50 hardcoded color values with website-matching palette |
| `extension/popup.js` | Removed dead code referencing non-existent elements/functions |

## Files NOT Modified (by design)

| File | Reason |
|------|--------|
| `src/js/renderer.js` | Per user constraint — do not touch |
| `src/js/selection.js` | Per user constraint — do not touch |
| `src/css/tokens.css` | Source of truth — no changes needed |
| `extension/sidepanel/sidepanel.css` | Already properly aligned with website tokens |
| `extension/background.js` | Clean, no issues found |
| `extension/manifest.json` | Clean, properly configured |
| `extension/shared/*` | Identical to website files — no changes needed |

## Remaining Considerations

1. **ext-init.js** (both copies) — Dead untracked files referencing non-existent elements. Not loaded by any HTML or manifest entry. Can be deleted at will.
2. **popup.js / sidepanel.js duplication** — ~60% shared logic. A future refactor could extract shared functions into a module, but this is a P3 concern that doesn't affect functionality.
3. **Content script Cairo font** — Added as first-choice but depends on host page having it loaded. Degrades gracefully to system fonts.
