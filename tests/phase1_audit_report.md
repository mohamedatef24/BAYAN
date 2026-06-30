# Phase 1: Full Frontend Inventory — Bayan Website vs Chrome Extension

## Executive Summary

The Bayan Chrome Extension has **significant design system divergence** from the website, primarily in `popup.css` which uses a completely different color palette and font family. The sidepanel is properly aligned. There is one **syntax-breaking bug** in `sidepanel.js`, duplicated dead code in `ext-init.js`, and mixed old/new color systems in `content-inline.css`.

---

## 1. Design Token Comparison

| Token | Website (`tokens.css`) | Popup (`popup.css`) | Sidepanel (`sidepanel.css`) | Content Inline |
|-------|----------------------|--------------------|-----------------------------|----------------|
| Primary | `#6BA3E0` (blue) | `#6366f1` (indigo) ❌ | `var(--color-primary)` ✅ | `#6366f1` ❌ |
| Background | `#12141A` | `#0f0f14` ❌ | `var(--color-bg)` ✅ | `#0f0f14` ❌ |
| Surface | `#1A1D26` | `#1a1a24` ❌ | `var(--color-surface)` ✅ | `#1a1a24` ❌ |
| Text | `#E0DCD4` | `#e4e4e7` ❌ | `var(--color-text)` ✅ | `#e4e4e7` ❌ |
| Font | `Cairo, Tajawal` | `Segoe UI, SF Pro` ❌ | `Cairo, Tajawal` ✅ | system fonts ❌ |
| Spelling Error | `#E88A8A` | `#ef4444` ❌ | `#E88A8A` ✅ | Mixed ⚠️ |
| Grammar Error | `#E4B35A` | `#f59e0b` ❌ | `#E4B35A` ✅ | Mixed ⚠️ |
| Punctuation | `#6BC98A` | `#22c55e` ❌ | `#6BC98A` ✅ | `#6BC98A` ✅ |

### Verdict
- **Popup CSS**: Fully divergent — needs complete token realignment
- **Sidepanel CSS**: Properly aligned via `var()` references
- **Content Inline CSS**: Mixed — newer "UI Sync" section uses correct colors, older sections use wrong ones

---

## 2. Component Inventory

### Website Components
| Component | CSS Class | Status |
|-----------|-----------|--------|
| Navigation bar | `.nav` | Website only |
| Mobile drawer | `.mobile-nav-drawer` | Website only |
| Editor shell | `.editor-shell` | Website only |
| Format toolbar | `.format-toolbar` | Website only |
| Editor surface | `.editor-surface` | Website only |
| Score ring | `.score-ring-wrap` | Both ✅ |
| Suggestion cards | `.suggestion-card` | Both ✅ |
| Suggestion popover | `.suggestion-popover` | Website only |
| Error highlights | `.error-highlight` | Both ✅ |
| Summarize panel | `.summarize-panel` | Both ✅ |
| Dialect panel | `.dialect-panel` | Both ✅ |
| Auth gate modal | `.auth-gate-modal` | Website only |
| Documents panel | `.docs-panel-desktop` | Website only |
| Cloud sync badge | `.cloud-sync-badge` | Website only |
| Autocomplete dropdown | `.autocomplete-dropdown` | Website only |
| Ghost text | `.ghost-text` | Both ✅ |
| Quran modal | `.quran-check-modal` | Website only |
| Toast | `.toast` | Both ✅ |
| Bottom sheet (mobile) | `.bottom-sheet` | Website only |
| Analyzing indicator | `.analyzing-indicator` | Both ✅ |

### Extension-Only Components
| Component | Location | Class prefix |
|-----------|----------|-------------|
| FAB button | content-inline | `bayan-il-fab` |
| Inline tooltip | content-inline | `bayan-il-tooltip` |
| Inline modal | content-inline | `bayan-il-modal` |
| Tab system | popup/sidepanel | `bayan-tab`/`sp-tab` |
| Health status | popup/sidepanel | `bayan-status`/`sp-status` |
| Theme toggle | popup/sidepanel | `bayan-theme-toggle`/`sp-theme-toggle` |
| Apply to Page button | sidepanel | `sp-apply-page-btn` |

---

## 3. Feature Parity Matrix

| Feature | Website | Popup | Sidepanel | Content Script |
|---------|---------|-------|-----------|----------------|
| Text correction | ✅ | ✅ | ✅ | ✅ |
| Summarization | ✅ | ✅ | ✅ | ❌ |
| Dialect→MSA | ✅ | ✅ | ✅ | ❌ |
| Quran verification | ✅ | ✅ | ✅ | ❌ |
| Quran translation | ❌ | ❌ | ✅ | ❌ |
| Autocomplete (ghost) | ✅ | ❌ | ❌ | ✅ |
| Autocomplete (button) | ❌ | ✅ | ✅ | ❌ |
| Score ring | ✅ | ✅ | ✅ | ❌ |
| Rich text editor | ✅ | ❌ | ❌ | ❌ |
| Format toolbar | ✅ | ❌ | ❌ | ❌ |
| Auth (Supabase) | ✅ | ❌ | ❌ | ❌ |
| Document management | ✅ | ❌ | ❌ | ❌ |
| Cloud sync | ✅ | ❌ | ❌ | ❌ |
| File export | ✅ | ❌ | ❌ | ❌ |
| File import | ✅ | ❌ | ❌ | ❌ |
| Settings sync | ✅ | ❌ | ❌ | ❌ |
| Theme toggle | ✅ | ✅ | ✅ | ✅ |
| Context menu | ❌ | ✅ | ✅ | ❌ |
| Write back to page | ❌ | ❌ | ✅ | ❌ |
| Inline analysis | ❌ | ❌ | ❌ | ✅ |
| FAB button | ❌ | ❌ | ❌ | ✅ |

---

## 4. File Architecture

### Shared Code (extension/shared/)
- `css/tokens.css`, `css/base.css`, `css/components.css` — **IDENTICAL** to website `src/css/` ✅
- `js/` — Full mirror of website JS modules (auth, documents, sync, vendor, etc.)
- These shared files are loaded in popup.html and sidepanel.html but are **largely non-functional** in the extension context (no Supabase auth, no contenteditable editor)

### Extension-Specific Code
| File | Lines | Purpose |
|------|-------|---------|
| `popup.html` | 306 | 5-tab UI with textarea |
| `popup.css` | 822 | **Divergent** design system |
| `popup.js` | 723 | Tab switching, analysis, suggestions |
| `sidepanel/sidepanel.html` | 342 | 5-tab UI with textarea + translation |
| `sidepanel/sidepanel.css` | 773 | **Aligned** with website tokens |
| `sidepanel/sidepanel.js` | 922 | Similar to popup + persistence + write-back |
| `content-inline.css` | 1170 | Inline styles with !important isolation |
| `content-inline.js` | ~1600 | IIFE content script controller |
| `background.js` | 265 | Service worker + context menu + cache |
| `ext-init.js` | 92 | Dead code (references non-existent elements) |
| `sidepanel/ext-init.js` | 92 | Identical dead copy |

---

## 5. Critical Issues Found

### P0 — Syntax Error
- **`sidepanel/sidepanel.js:759`** — Orphaned function body. The `function addApplyPageButton(anchorBtn, getText, source) {` declaration line is missing; only the body (`if (!anchorBtn || !anchorBtn.parentElement) return;`) exists. This causes a runtime syntax error.

### P1 — Design System Divergence
- **`popup.css`** uses completely different tokens (#6366f1 indigo palette, Segoe UI font) vs website (#6BA3E0 blue palette, Cairo font)
- **`content-inline.css`** has mixed old (#ef4444) and new (#E88A8A) color values

### P2 — Dead Code
- **`ext-init.js`** (both copies) references `editor-container` and `.editor-actions` which don't exist in popup or sidepanel HTML
- **`extension/shared/js/`** contains full website modules (auth, documents, sync) that cannot function in extension context

### P3 — Code Duplication
- `popup.js` and `sidepanel.js` share ~60% identical logic (tab switching, analysis, suggestions, score ring, toast)
- `ext-init.js` exists as identical files in two locations

---

## 6. Recommended Fix Priority

1. Fix `sidepanel.js` syntax error (P0)
2. Realign `popup.css` tokens to match website design system (P1)
3. Fix `content-inline.css` mixed color values (P1)
4. Add Cairo font to popup (P1)
5. Remove dead `ext-init.js` files (P2)
6. Unify popup.js/sidepanel.js shared logic (P3 — future phase)
