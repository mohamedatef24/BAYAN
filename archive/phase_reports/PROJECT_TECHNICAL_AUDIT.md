# Bayan — Deep Technical Audit & Readiness Assessment

**Date:** 2026-06-15  
**Scope:** Phase 1 stability, Phase 2 UX, Phase 4 document management (implemented), long-document behavior  
**Method:** Static code review — no refactors performed  

---

# Section 1 — Current Project State

## 1. Repository Overview

### Folder structure (tree)

```
BAYAN/
├── run_app.py                    # Entry: chdir to src/, loads Flask app
├── requirements.txt
├── test_renderer.js              # Phase 1 renderer unit tests
├── test_analyze_api.py
├── test_model_load.py
├── PHASE_*.md                    # Phase planning & status docs
├── VERIFICATION_*.md             # Phase 1 audit artifacts
├── src/
│   ├── index.html                # Single-page shell (marketing + editor)
│   ├── index.html.orig           # Backup (not served)
│   ├── app.py                    # Flask backend + /api/*
│   ├── model_loader.py           # HuggingFace / local model loading
│   ├── ara_spell.py
│   ├── README.md
│   ├── css/
│   │   ├── tokens.css            # Design tokens, dark/light themes
│   │   ├── base.css              # Typography, reset, a11y base
│   │   └── components.css        # Nav, editor, sidebar, documents UI
│   └── js/
│       ├── renderer.js           # ⚠️ SENSITIVE — offset highlight renderer
│       ├── selection.js          # ⚠️ SENSITIVE — cursor/selection API
│       ├── editor.js             # Editor orchestration, analyze, apply
│       ├── ui.js                 # Score, suggestions list, mobile UI
│       ├── theme.js              # Theme toggle + localStorage
│       ├── api.js                # ES module API helpers (NOT loaded in HTML)
│       ├── documents/
│       │   ├── documents.js      # Import/export UI wiring
│       │   ├── import.js         # TXT + DOCX import
│       │   ├── export.js         # TXT + DOCX + PDF export
│       │   └── doc-utils.js      # Normalize, download, validation
│       └── vendor/
│           ├── mammoth.browser.min.js
│           ├── docx.umd.js
│           ├── html2pdf.bundle.min.js
│           └── FileSaver.min.js
└── (root test/inspect scripts — dev utilities)
```

### Important JavaScript files

| File | Role |
|------|------|
| `src/js/selection.js` | `getEditorText()`, `setEditorHTML()`, offset save/restore |
| `src/js/renderer.js` | `render()`, `escapeHtml()`, segment-based highlights |
| `src/js/editor.js` | `initEditor()`, `analyzeText()`, apply flows, `loadDocumentText()` |
| `src/js/ui.js` | Score ring, suggestion cards, drawer/sheet, doc toasts/banner |
| `src/js/theme.js` | Dark/light theme, `localStorage` key `bayan-theme` |
| `src/js/documents/*` | Phase 4 import/export (post-implementation) |
| `src/js/api.js` | **Dead in production** — not referenced in `index.html` |

### Important CSS files

| File | Role |
|------|------|
| `src/css/tokens.css` | CSS variables, `[data-theme="dark|light"]` palettes |
| `src/css/base.css` | Cairo typography, `.sr-only`, `:focus-visible`, animations |
| `src/css/components.css` | All UI components (~1000 lines incl. Phase 4 doc UI) |

**Note:** Marketing pages still use **Tailwind CDN** inline classes in `index.html` alongside token-driven CSS.

### Backend structure

| File | Role |
|------|------|
| `run_app.py` | Adds `src/` to path, `os.chdir(src)`, runs Flask on port 5000 |
| `src/app.py` | Flask app, static files from `.`, CORS, model singletons |
| `src/model_loader.py` | Summarization, spelling, grammar, punctuation, autocomplete models |

**API routes (primary):**

- `GET /` → `index.html`
- `POST /api/analyze` → sequential spelling → grammar → punctuation
- `POST /api/summarize` → summarization (enforces `MAX_TEXT_LENGTH`)
- `POST /api/spelling|grammar|punctuation|autocomplete` → individual endpoints

---

## 2. Editor Entry Points

| Location | Function | Responsibility |
|----------|----------|----------------|
| `src/index.html` | `DOMContentLoaded` handler | Calls `initTheme()`, `initUI()`, `initEditor()`, `initDocuments()` |
| `src/js/editor.js` | `initEditor()` | Registers `input`, `click`, `keydown`, apply-all listeners on `#editor-container` |
| `src/js/documents/documents.js` | `initDocuments()` | Import button, export dropdown, mobile export sheet |
| `src/js/ui.js` | `initUI()` | Mobile nav drawer, suggestions bottom sheet |
| `src/js/theme.js` | `initTheme()` | Theme toggle button |

**Main editor file:** `src/js/editor.js` (orchestration). Core primitives live in `selection.js` + `renderer.js`.

**Event registration:**

- **Typing → analyze:** `editor.addEventListener('input', analyzeTextDelayed)` in `initEditor()`
- **Highlight click → popover:** `handleEditorClick()` → `showTooltip()`
- **Apply single:** `applyCorrection()` / `applySuggestionByIndex()` via popover or sidebar
- **Apply all:** `#apply-all-btn`, `#apply-all-sheet` → `applyAllSuggestions()`
- **Document import:** `#doc-import-input` change → `handleImportFile()` → `loadDocumentText()`

**Analysis trigger flow:**

```
input event
  → analyzeTextDelayed()          [editor.js:71]
  → setTimeout 500ms
  → analyzeText()                 [editor.js:87]
  → getEditorText()
  → truncate to MAX_ANALYZE_LENGTH (5000) for API
  → saveSelection() + getCaretOffset()
  → fetch POST /api/analyze
  → sortSuggestions()
  → render({ text, suggestions }) [renderer.js:198]
  → setEditorHTML(highlightedHtml)  [selection.js:198]
  → restoreSelection() OR setCaretOffset()
  → updateSuggestionCounts / updateWritingScore / updateSuggestionsList
```

---

## 3. Current Text Flow

```
User Types (contenteditable #editor-container)
    ↓
input event → analyzeTextDelayed() [debounce 500ms]
    ↓
getEditorText()                    [selection.js:187 — innerText/textContent]
    ↓
analyzeText()                      [editor.js:87]
    ↓
textForApi = text.slice(0, 5000)   [if len > MAX_ANALYZE_LENGTH]
    ↓
saveSelection()                    [selection.js:9 — character offsets]
getCaretOffset()                   [selection.js:117]
    ↓
POST /api/analyze { text: textForApi }
    ↓
window.currentSuggestions = sortSuggestions(data.suggestions)
    ↓
render({ text: FULL_TEXT, suggestions })   [renderer.js — uses FULL editor text]
    ↓
setEditorHTML(highlightedHtml)     [selection.js — innerHTML assignment]
    ↓
restoreSelection(savedSelection)   [selection.js:53]
  OR setCaretOffset(currentCaretOffset)
    ↓
updateSuggestionsList()            [ui.js — sidebar + bottom sheet]
```

**Import flow (Phase 4):**

```
File → importTxtFile / importDocxFile
    ↓
normalizeImportedText()            [doc-utils.js]
    ↓
loadDocumentText()                 [editor.js:303]
    ↓
escapeHtml() → setEditorHTML()
    ↓
analyzeTextDelayed()
```

**Export flow (Phase 4):**

```
getEditorText() → exportTxtFile | exportDocxFile | exportPdfFile
```

---

# Section 2 — Phase 1 Stability Verification

## 4. Selection System (`selection.js`)

### How selections are saved

`saveSelection()` clones the current DOM Range, walks `#editor-container` text nodes, and computes **character offsets** from the start of the editor:

```37:41:src/js/selection.js
    return {
      selectionStart,
      selectionEnd,
      isCollapsed
    };
```

Uses `Range.toString().length` — **offset-based**, not DOM node references.

### How selections are restored

`restoreSelection()` walks the editor DOM tree, counting characters in `TEXT_NODE`s until `selectionStart` / `selectionEnd` match, then sets a new `Range`.

Fallback: `setCaretOffset(offset)` when `savedSelection` is null (used after analyze when selection save fails).

### Offsets vs DOM references

**Offsets only.** No saved Range objects or node IDs persist across renders.

### Known weaknesses

| Weakness | Severity |
|----------|----------|
| Offset math uses `toString()` — can diverge from `innerText` in edge cases (e.g. `<br>` handling) | Medium |
| `restoreSelection()` tree walk assumes text nodes only inside spans — works with current renderer output | Low |
| No selection restore after `applySuggestionAtOffsets()` — cursor jumps to start/end unpredictably | Medium |
| `loadDocumentText()` does not preserve cursor (resets content) | Expected for import |
| Highlight spans split text nodes — restore works because walk is post-render | Low |

---

## 5. Rendering System (`renderer.js`)

### How highlights are rendered

1. `sortSuggestions()` by `start` offset  
2. `createSegments()` splits text into plain + suggestion segments  
3. `renderHighlightedText()` builds HTML string with escaped text + `<span class="spelling-error|grammar-error|punctuation-suggestion">`  

### Full innerHTML rewrites?

**Yes.** Every successful analyze calls:

```144:144:src/js/editor.js
    setEditorHTML(highlightedHtml);
```

which assigns `editor.innerHTML = html` (`selection.js:201`).

This is intentional Phase 1 architecture — full rewrite on each analyze cycle.

### Suggestion span generation

```177:181:src/js/renderer.js
      html += `<span class="${errorClass}" data-suggestion-id="${suggestionId}" data-original="${escapeHtml(
        suggestion.original
      )}" data-correction="${escapeHtml(
        suggestion.correction
      )}" data-type="${suggestion.type}" title="${suggestion.type}: ${suggestion.correction}">${escapedText}</span>`;
```

`data-suggestion-id` is **array index** (0, 1, 2…), not a stable UUID.

### Rendering stability

| Aspect | Status |
|--------|--------|
| XSS via user text | Mitigated — `escapeHtml()` on all text segments |
| Overlapping suggestions | Handled via segment builder (sequential non-overlap assumed from API) |
| Duplicate word occurrences | Independent spans per offset range ✅ |
| Re-render during typing | Debounced + `AbortController` reduces race conditions ✅ |
| `renderWithoutSuggestions()` | Uses `textContent` (safe) not innerHTML |

**Automated test:** `node test_renderer.js` — 3/3 highlights, XSS escape, overlapping — **PASS**.

---

## 6. Suggestion Application

### Apply single suggestion

```
applyCorrection() / applySuggestionByIndex(index)
  → applySuggestionAtOffsets(suggestion)     [editor.js:250]
  → getEditorText()
  → splice: before + correction + after
  → setEditorHTML(escapeHtml(newText))         [no re-render yet]
  → analyzeTextDelayed()                     [triggers full render cycle]
```

### Apply all

```
applyAllSuggestions()                        [editor.js:272]
  → sort suggestions by start DESC
  → apply each correction to plain text string
  → setEditorHTML(escapeHtml(text))
  → analyzeTextDelayed()
```

### Functions that modify editor text

| Function | File | Method |
|----------|------|--------|
| `setEditorHTML()` | selection.js | `innerHTML =` |
| `renderWithoutSuggestions()` | editor.js | `textContent =` |
| `applySuggestionAtOffsets()` | editor.js | escape + setEditorHTML |
| `applyAllSuggestions()` | editor.js | escape + setEditorHTML |
| `clearEditor()` | editor.js | setEditorHTML('') |
| `loadDocumentText()` | editor.js | escape + setEditorHTML |

### Cursor preservation on apply

**Not preserved.** Apply paths do not call `saveSelection()` / `restoreSelection()`. User cursor typically resets; next `analyzeText()` may restore if user hasn't moved.

### Coupling with renderer

**Tight indirect coupling:** apply modifies plain text → analyze re-fetches suggestions → `render()` rebuilds all spans. Offsets in `window.currentSuggestions` are invalidated after each apply (correct — re-analyze replaces them).

---

## 7. Regression Risk Analysis

| Risk area | Risk | Cause |
|-----------|------|-------|
| Cursor preservation during analyze | **Low** | save/restore in `analyzeText()` — proven in Phase 1 verification |
| Cursor preservation during apply | **Medium** | No restore after apply |
| Selection restoration | **Low–Medium** | Offset-based; fails silently on DOM structure change |
| Highlight rendering | **Low** | Stable renderer; sorted suggestions |
| Suggestion application | **Low** | Offset splice + re-analyze |
| Document import breaking editor | **Low** | Uses `loadDocumentText()` + escapeHtml |
| Long doc + full render | **Medium** | Highlights computed on full text, API on 5000 chars — offset mismatch beyond 5000 |
| PDF export Arabic | **High** | html2canvas RTL shaping limitations (known post-Phase 4) |
| Summarize tab XSS | **Medium** | `summaryText.innerHTML = \`<p>${data.summary}</p>\`` unescaped |

---

# Section 3 — Phase 2 Verification

## 8. UI Architecture Review

| Asset | Exists? | Used? | Dead code? |
|-------|---------|-------|------------|
| `tokens.css` | ✅ | ✅ Linked in `index.html` | No |
| `base.css` | ✅ | ✅ | No |
| `components.css` | ✅ | ✅ | No |
| `theme.js` | ✅ | ✅ `initTheme()` on DOMContentLoaded | No |
| `ui.js` | ✅ | ✅ Score, cards, drawer, sheet, doc toast/banner | No |
| `api.js` | ✅ | ❌ Not loaded in HTML | **Yes — entire file unused in browser** |
| Tailwind CDN | ✅ | ✅ Marketing sections only | Partial overlap with tokens |

---

## 9. Theme System

| Question | Answer |
|----------|--------|
| Toggle implementation | `#theme-toggle` → `toggleTheme()` in `theme.js` |
| Persistence | `localStorage.setItem('bayan-theme', theme)` |
| Default theme | Stored value, else `prefers-color-scheme`, else `'dark'` on error |
| Early paint | IIFE in `theme.js` sets `data-theme` before DOMContentLoaded |
| Dark mode stability | ✅ Fixed — `clearThemePaletteOverrides()` prevents SDK inline vars breaking light theme |
| Light mode readability | ✅ Warm paper palette in `tokens.css` |

---

## 10. Mobile Readiness

| Area | Status | Notes |
|------|--------|-------|
| Responsive layout | ✅ Mostly | `editor-layout` grid, breakpoints in `components.css` |
| Sidebar | ✅ | Hidden `<1024px`; bottom sheet replaces |
| Drawer (nav) | ✅ | RTL slide-in, backdrop, Escape closes |
| Bottom sheet (suggestions) | ✅ | `#bottom-sheet` + `#mobile-sheet-trigger` |
| Bottom sheet (export) | ✅ | `#doc-export-sheet` (Phase 4) |
| Document toolbar mobile | ✅ | Import/export in `editor-footer` |

**Remaining issues:**

- No formal breakpoint QA matrix
- No focus trap in mobile drawer
- External link (Bayyinah) in nav — works on desktop; mobile drawer uses anchor (no `data-page` conflict) ✅
- PDF export may flash capture overlay briefly

---

## 11. Accessibility Audit

| Criterion | Status |
|-----------|--------|
| Keyboard navigation | ⚠️ Partial — Escape dismisses popover/dropdown; Enter on suggestion card applies |
| Focus visibility | ✅ `:focus-visible` in `base.css` |
| ARIA on editor | ✅ `role="textbox"`, `aria-multiline`, `aria-busy` during analyze |
| ARIA on suggestions | ✅ `role="list"`, `aria-live="polite"` |
| Screen reader testing | ❌ Not performed |
| Tab order through suggestions | ❌ Not implemented |
| Popover keyboard apply | ❌ Click only (hint says Enter but not wired on popover) |
| Focus trap in drawer | ❌ |

**Remaining gaps:** Full keyboard nav, SR testing, WCAG contrast audit, drawer focus trap.

---

# Section 4 — Document Management Readiness

> **Note:** Phase 4 is **implemented**. This section validates the architecture that was planned and now exists.

## 12. Editor Read API — `getEditorText()`

| Property | Value |
|----------|-------|
| **File** | `src/js/selection.js:187` |
| **Behavior** | Returns `#editor-container` `.innerText \|\| .textContent \|\| ''` |
| **Side effects** | None — read-only |

**Safe for TXT/DOCX import without modification?** ✅ Yes — already used by export, analyze, summarize, apply.

---

## 13. Editor Write API

| Question | Answer |
|----------|--------|
| Does `loadDocumentText()` exist? | **Yes** — `src/js/editor.js:303` |
| Safest implementation point? | `loadDocumentText()` — sole import entry; wraps normalize + escape + state reset + analyze |
| Alternative before Phase 4? | Would have been new function calling `setEditorHTML(escapeHtml(text))` + `analyzeTextDelayed()` |

**Recommendation (implemented):** All imports MUST call `loadDocumentText()` — current code complies.

---

## 14. Safe Import Path

**Confirmed flow:**

```
Import (TXT/DOCX)
    ↓
normalizeImportedText()     [doc-utils.js — BOM, line endings]
    ↓
loadDocumentText()        [editor.js — escapeHtml + setEditorHTML]
    ↓
analyzeTextDelayed()
```

**Insertion point:** `import.js` → `loadDocumentText()` — ✅ correct.

---

## 15. XSS Audit

### Editor insertion points

| API | File | Safe? |
|-----|------|-------|
| `setEditorHTML(html)` | selection.js | ⚠️ **Unsafe if caller skips escape** |
| `loadDocumentText()` | editor.js | ✅ Always `escapeHtml()` first |
| `applySuggestionAtOffsets()` | editor.js | ✅ `escapeHtml(newText)` |
| `applyAllSuggestions()` | editor.js | ✅ `escapeHtml(text)` |
| `render()` output → setEditorHTML | editor.js | ✅ Renderer escapes all segments |
| `renderWithoutSuggestions()` | editor.js | ✅ Uses `textContent` |

### innerHTML usage outside editor

| Location | Risk |
|----------|------|
| `ui.js` — suggestion cards | ✅ User strings passed through `escapeHtml()` |
| `index.html` — `generateSummary()` | ⚠️ **`data.summary` injected unescaped** into `#summary-text` |
| `index.html` — SDK config | ⚠️ Marketing headline innerHTML from config |
| `theme.js` — toggle icon | ✅ Static SVG strings |

### Required fixes (pre-import was satisfied; remaining)

1. ✅ Editor import path — **fixed in Phase 4** via `loadDocumentText()`
2. ⚠️ Summarize output — should use `textContent` or `escapeHtml(data.summary)`
3. ⚠️ Never call `setEditorHTML()` with raw imported content — **enforced by architecture**

---

# Section 5 — Long Document Readiness

## 16. Backend Limits

| Constant | File | Value | Enforcement |
|----------|------|-------|-------------|
| `MAX_TEXT_LENGTH` | `src/app.py:46` | **5000** | `/api/summarize` (line 150) — returns 400 if exceeded |
| `MAX_ANALYZE_LENGTH` | `src/js/editor.js:7` | **5000** | Frontend truncates before `/api/analyze` |
| `MAX_IMPORT_BYTES` | `doc-utils.js:3` | **2 MB** | Import validation |

**Important:** `/api/analyze` does **not** enforce `MAX_TEXT_LENGTH` server-side — relies on frontend truncation.

---

## 17. Large Document Behavior

| Import size | UI | Rendering | Suggestions | Backend |
|-------------|-----|-----------|-------------|---------|
| **10,000 chars** | Banner shown | Full text in contenteditable; highlights on full text | Only first 5000 analyzed — **highlights beyond 5000 may be wrong/missing** | Analyze receives 5000 chars |
| **25,000 chars** | Same | Browser handles contenteditable; possible scroll perf lag | Same offset mismatch risk | Same |
| **50,000 chars** | Same | DOM size grows; analyze debounce still fires on every input | Sidebar card count bounded by API response (~5000 char scope) | Summarize would reject full text unless truncated client-side |

**Bottlenecks:**

1. **Offset mismatch:** API suggestions reference first 5000 chars; renderer applies to full text — correct for overlapping region, absent beyond 5000  
2. **Full innerHTML rewrite** on each analyze — O(n) HTML string build + DOM parse  
3. **contenteditable** with very large text — browser-dependent typing lag  
4. **Summarize tab** sends full `getEditorText()` — may hit backend 5000 limit  

---

## 18. Performance Review

| Operation | Estimate | Notes |
|-----------|----------|-------|
| Typing | Good up to ~10–15k chars | Debounce 500ms helps |
| Analysis | ~0–5s (model/GPU dependent) | Aborted on rapid typing |
| Rendering | O(n) per analyze | Full HTML rebuild |
| Safe document size (editing) | **~10,000–20,000 chars** practical | Beyond that: UX degradation, not crashes |
| Safe analyze size | **5,000 chars** (hard limit) | By design |

---

# Section 6 — Phase 4 Architecture Validation

> Phase 4 **implemented** — validation confirms design.

## 19. Proposed Folder Structure

```
src/js/documents/
  documents.js    ✅ UI wiring
  import.js       ✅ TXT + DOCX
  export.js       ✅ TXT + DOCX + PDF
  doc-utils.js    ✅ Shared utilities
```

| Question | Answer |
|----------|--------|
| Conflicts? | None — globals loaded via script tags in order |
| Better placement? | Current placement is correct — keeps `editor.js` as orchestrator |
| Dependency concerns | Depends on `escapeHtml` from renderer.js, editor/selection globals — matches existing non-module pattern |

---

## 20. Integration Points

**Read:** `getEditorText()` — ✅ used by export, analyze, summarize, apply  

**Write:** `loadDocumentText()` — ✅ sole import path  

**Additional interfaces used (not violating architecture):**

| Function | Purpose | Acceptable? |
|----------|---------|-------------|
| `updateExportButtonStates()` | Disable export when empty | ✅ UI only |
| `updateAnalysisLimitBanner()` | Long doc warning | ✅ UI only |
| `showDocToast()` | Import/export feedback | ✅ UI only |
| `normalizeImportedText()` | Pre-write normalization | ✅ Called inside import → loadDocumentText chain |

**Verdict:** Core contract holds. UI helpers are appropriate extensions.

---

## 21. Library Compatibility Check

| Library | Compatible? | Concerns |
|---------|-------------|----------|
| **Mammoth.js** | ✅ | Text-only via `extractRawText()` — no formatting. 2MB import cap. |
| **docx.js** | ✅ | RTL via `rightToLeft`, `bidirectional`, `AlignmentType.RIGHT`. Arial fallback font. |
| **html2pdf.js** | ⚠️ Partial | Works for non-empty PDF; **Arabic letter reordering** in legacy mode; `foreignObjectRendering` inconsistent across browsers. Canvas-based — not searchable PDF text. |
| **file-saver** | ✅ | Used with `<a download>` fallback in `downloadBlob()` — helpful, not strictly required. |

**Vendor copies:** Present under `src/js/vendor/` for offline demo reliability ✅

---

# Section 7 — Phase 2 Polish Status

| Task | Status |
|------|--------|
| Editor as default landing page | **Not Started** — `#page-home` still `active`; `#/editor` hash supported |
| Mobile QA | **Partial** — UI built, no formal test matrix |
| Keyboard navigation | **Partial** — Escape + card Enter only |
| Accessibility audit | **Partial** — ARIA basics, no SR testing |
| Screenshot generation | **Not Started** — `docs/screenshots/phase2/` not created |
| Horizontal scrolling audit | **Partial** — CSS guards, not device-tested |
| Regression testing | **Partial** — `test_renderer.js` only; no E2E import/export automation |
| Tailwind CDN removal | **Not Started** |
| Virtualize suggestion list (>50) | **Not Started** |
| Phase 4 document management | **Completed** |

---

# Section 8 — Final Assessment

## 23. Phase Readiness Score

| Area | Score | Rationale |
|------|-------|-----------|
| **Phase 1 Stability** | **9/10** | Offset renderer + selection restore proven; apply-cursor gap; long-doc offset mismatch |
| **Phase 2 Completion** | **7/10** | Core UX done; polish, a11y, default landing, Tailwind cleanup remain |
| **Document Management Readiness** | **8/10** | TXT/DOCX import-export working; PDF Arabic quality still imperfect |
| **Overall Project Readiness** | **8/10** | Demo-ready for writing + import/export; PDF + long-doc analyze scope are known limits |

---

## 24. Blocking Issues

> Phase 4 is implemented. These are **remaining issues**, not pre-Phase-4 blockers.

| Issue | Blocker? | Notes |
|-------|----------|-------|
| PDF Arabic garbling (html2canvas) | **Product quality**, not crash | foreignObject fallback chain in `export.js` |
| Highlights beyond 5000 chars | **Feature gap** | By design — banner warns user |
| Summarize innerHTML XSS | **Security** — low risk (model output) | Should escape before Phase 5 / public deploy |
| `api.js` unused | No | Dead code cleanup optional |
| `_sdk/*.js` 404 in logs | No | SDK stubs missing — config fallbacks work |

**No architectural blockers** prevent continued use of document management.

---

## 25. Recommended Next Action

### **B) Complete Phase 2 Polish first** — with targeted Phase 4 PDF fix

**Justify with evidence:**

1. **Phase 4 core is shipped** — import/export paths work; `loadDocumentText()` / `getEditorText()` contract satisfied; `renderer.js` / `selection.js` untouched ✅  
2. **PDF Arabic** remains a user-visible defect — requires polish (alternative: server-side PDF or accept image-based export with disclaimer), not architecture rework  
3. **Phase 2 gaps** still affect daily demo quality: home vs editor landing, keyboard nav, summarize XSS hardening, formal mobile QA  
4. **Phase 1 is stable** — no need for option C (architecture fixes)

**Priority order:**

1. Fix summarize XSS (`escapeHtml` on summary output)  
2. PDF export — document known limitation or pursue server-side Arabic PDF  
3. Set editor as default page (or redirect for demo)  
4. Keyboard navigation + drawer focus trap  
5. Remove dead `api.js` or wire as module  

---

# Appendix — Key Code References

| Concern | Reference |
|---------|-----------|
| Editor init | `src/js/editor.js:12` — `initEditor()` |
| Analyze + restore | `src/js/editor.js:87–150` |
| Load document | `src/js/editor.js:303–325` |
| getEditorText | `src/js/selection.js:187–191` |
| setEditorHTML | `src/js/selection.js:198–202` |
| saveSelection | `src/js/selection.js:9–46` |
| render | `src/js/renderer.js:198–201` |
| escapeHtml | `src/js/renderer.js:9–18` |
| Script load order | `src/index.html:25–32` |
| DOMContentLoaded | `src/index.html:875–891` |
| MAX_TEXT_LENGTH backend | `src/app.py:46` |
| MAX_ANALYZE_LENGTH frontend | `src/js/editor.js:7` |

---

*Audit performed by static analysis. No code was modified during this assessment.*
