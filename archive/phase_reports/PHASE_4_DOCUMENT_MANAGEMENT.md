# Phase 4 — Document Management

**Status**: Architecture Plan (Pre-Implementation)  
**Date**: June 15, 2026  
**Goal**: Transform Bayan from a text editor into a document editor with import/export  
**Prerequisites**: Phase 1 editor engine complete; Phase 2 theme system in place

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Plan](#2-architecture-plan)
3. [Required Libraries](#3-required-libraries)
4. [File Structure Changes](#4-file-structure-changes)
5. [Feature Specifications](#5-feature-specifications)
6. [UI Design](#6-ui-design)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Risk Analysis](#8-risk-analysis)
9. [Testing Checklist](#9-testing-checklist)
10. [Approval Gate](#10-approval-gate)

---

## 1. Executive Summary

Phase 4 adds **client-side document I/O** without changing the Phase 1 highlight pipeline. All import paths produce **plain text** loaded through existing `selection.js` APIs. All export paths read **plain text** via `getEditorText()`. The offset-based renderer, cursor preservation, and analyze flow remain untouched.

| Format | Direction | Library | Complexity |
|--------|-----------|---------|------------|
| `.txt` | Import + Export | Native `FileReader` + Blob | Low |
| `.docx` | Import | Mammoth.js | Medium |
| `.docx` | Export | docx.js | Medium–High (RTL) |
| `.pdf` | Export | html2pdf.js (recommended) | Medium–High (Arabic) |

**Out of scope for Phase 4**: Server-side conversion, cloud storage, auth, database persistence, `.doc` (legacy binary), rich formatting preservation, images/tables in DOCX.

---

## 2. Architecture Plan

### 2.1 Current Editor Data Flow (unchanged)

```
User types → contenteditable #editor-container
           → getEditorText()                    [selection.js]
           → /api/analyze
           → render({ text, suggestions })        [renderer.js]
           → setEditorHTML(html)                [selection.js]
           → restoreSelection()                 [selection.js]
```

Phase 4 inserts a **parallel I/O layer** that only talks to the editor through two public seams:

| Seam | Function | Owner |
|------|----------|-------|
| Read | `getEditorText()` | `selection.js` — **do not modify** |
| Write | `setEditorHTML(escapeHtml(text))` + trigger analysis | via new `loadDocumentText()` in `editor.js` |

### 2.2 Proposed Document Layer

```
┌─────────────────────────────────────────────────────────────┐
│  UI: Import button · Export dropdown · hidden <input type=file>│
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   documents.js (facade)  │
              │   initDocuments()        │
              └────────────┬────────────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
    │  import.js  │ │  export.js  │ │  utils.js │
    │  · importTxt│ │  · exportTxt│ │  · download│
    │  · importDocx│ │ · exportDocx│ │  · filename│
    └──────┬──────┘ │  · exportPdf│ └───────────┘
           │        └──────┬──────┘
           │               │
           └───────┬───────┘
                   ▼
         loadDocumentText(plainText)     getEditorText()
                   │                         ▲
                   ▼                         │
              editor.js ─────────────────────┘
         (new wrapper only — no renderer changes)
                   │
                   ▼
              selection.js  ·  renderer.js  (UNTOUCHED)
```

### 2.3 `loadDocumentText()` Contract (new in `editor.js`)

Single entry point for all imports. Keeps renderer/selection logic isolated.

```javascript
/**
 * Load plain text into editor — used by document import only.
 * @param {string} text - UTF-8 plain text
 * @param {object} options - { analyze: true, filename: 'doc.txt' }
 */
function loadDocumentText(text, options = {}) {
  const normalized = normalizeImportedText(text); // CRLF → LF, trim BOM
  setEditorHTML(escapeHtml(normalized));
  window.currentSuggestions = [];
  updatePlaceholder();
  updateEditorStats();
  updateSuggestionCounts(0, 0, 0);
  updateWritingScore(0, 0, 0);
  updateSuggestionsList([]);
  hideTooltip();
  if (options.analyze !== false) {
    analyzeTextDelayed();
  }
}
```

**Rules:**
- Always pass through `escapeHtml()` before `setEditorHTML()` (XSS safety)
- Never call `render()` directly from import layer
- After load, debounced `analyzeText()` runs as if user typed

### 2.4 Paragraph Model

Internal representation remains **plain text with `\n` paragraph breaks**:

| Source | Paragraph handling |
|--------|-------------------|
| TXT | Preserve `\n` as-is |
| DOCX import (Mammoth) | `mammoth.extractRawText()` — paragraphs separated by `\n\n` |
| DOCX export (docx.js) | Split on `\n\n` or `\n` → one `Paragraph` per block |
| PDF export | Render editor DOM or text block with `dir="rtl"` |

### 2.5 Backend Constraint

`/api/analyze` enforces `MAX_TEXT_LENGTH = 5000` characters (`app.py`). Imports may load longer documents for **editing/export**, but analysis will only process what the API accepts. Phase 4 should:

1. Show a non-blocking warning if imported text exceeds 5000 chars
2. Still load full text into editor (export works on full content)
3. Optionally analyze first 5000 chars only — **defer to Phase 4.1** if needed

---

## 3. Required Libraries

### 3.1 Recommended Versions (CDN for Vanilla JS)

| Library | Version | Purpose | CDN |
|---------|---------|---------|-----|
| **Mammoth.js** | 1.8.x | DOCX → text | `https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js` |
| **docx** | 8.5.x | Build DOCX | `https://unpkg.com/docx@8.5.0/build/index.umd.js` |
| **file-saver** | 2.0.5 | Trigger download | `https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js` |
| **html2pdf.js** | 0.10.2 | PDF via HTML render | `https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.2/html2pdf.bundle.min.js` |

### 3.2 Library Evaluation

#### Mammoth.js (DOCX Import) — **Selected**

```javascript
mammoth.extractRawText({ arrayBuffer })
  .then(result => result.value); // plain text, paragraphs as \n\n
```

- Ignores styling, tables, images by design (`extractRawText`)
- Works in browser with `FileReader.readAsArrayBuffer`
- No server required

#### docx.js (DOCX Export) — **Selected**

```javascript
const doc = new docx.Document({
  sections: [{
    properties: { rightToLeft: true },
    children: paragraphs
  }]
});
docx.Packer.toBlob(doc).then(blob => saveAs(blob, 'document.docx'));
```

- Native RTL section support via `rightToLeft: true`
- Paragraph-level Arabic text
- Requires mapping `\n` splits to `docx.Paragraph` + `docx.TextRun`

#### PDF Export — **html2pdf.js (recommended over raw jsPDF)**

| Approach | Arabic support | Searchable text | Effort |
|----------|---------------|-----------------|--------|
| jsPDF alone | Poor (no Arabic glyphs) | Yes | High (embed Amiri font) |
| jsPDF + custom Arabic font | Good | Yes | High (~500KB font) |
| **html2pdf.js** (html2canvas + jsPDF) | **Good** (browser renders Cairo) | No (image-based) | Medium |
| Browser print dialog | Good | Yes | Low UX |

**Recommendation**: Start with **html2pdf.js** rendering a cloned off-screen RTL div with editor plain text + Cairo font. Upgrade to jsPDF + Amiri font in Phase 4.1 if searchable PDF is required.

### 3.3 No New Python Dependencies

All conversion is client-side. Flask continues to serve static files only.

---

## 4. File Structure Changes

```
src/
├── js/
│   ├── renderer.js          (unchanged)
│   ├── selection.js         (unchanged)
│   ├── editor.js            (+ loadDocumentText, export hook)
│   ├── documents/
│   │   ├── documents.js     # init, UI event wiring
│   │   ├── import.js        # importTxt, importDocx
│   │   ├── export.js        # exportTxt, exportDocx, exportPdf
│   │   └── doc-utils.js     # normalizeText, downloadBlob, defaultFilename
│   ├── theme.js
│   └── ui.js
├── css/
│   └── components.css       (+ .doc-dropdown, .doc-menu-item)
└── index.html               (+ script tags, toolbar UI, hidden file input)
```

### 4.1 New Files

| File | ~Lines | Responsibility |
|------|--------|----------------|
| `documents/documents.js` | 80 | `initDocuments()`, wire buttons |
| `documents/import.js` | 120 | TXT + DOCX import |
| `documents/export.js` | 180 | TXT + DOCX + PDF export |
| `documents/doc-utils.js` | 60 | Shared helpers |

### 4.2 Modified Files

| File | Change |
|------|--------|
| `editor.js` | Add `loadDocumentText()` only (~25 lines) |
| `index.html` | Toolbar UI, CDN scripts, `initDocuments()` call |
| `components.css` | Dropdown + import button styles (~80 lines) |

### 4.3 Untouched Files

- `renderer.js` — no changes
- `selection.js` — no changes
- `app.py` — no changes (optional future: raise `MAX_TEXT_LENGTH`)

---

## 5. Feature Specifications

### 5.1 TXT Import

```javascript
function importTxt(file) {
  const reader = new FileReader();
  reader.onload = (e) => loadDocumentText(e.target.result, { filename: file.name });
  reader.readAsText(file, 'UTF-8');
}
```

| Requirement | Implementation |
|-------------|----------------|
| Upload `.txt` | Hidden `<input accept=".txt,text/plain">` |
| FileReader | `readAsText(file, 'UTF-8')` |
| Load into editor | `loadDocumentText()` |
| Preserve architecture | No renderer/selection changes |
| BOM handling | Strip `\uFEFF` prefix in `normalizeImportedText()` |

### 5.2 TXT Export

```javascript
function exportTxt() {
  const text = getEditorText();
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  downloadBlob(blob, defaultFilename('txt'));
}
```

| Requirement | Implementation |
|-------------|----------------|
| UTF-8 | `Blob` with `charset=utf-8` |
| Arabic preserved | UTF-8 encoding (no `escape` on export) |
| Download | `file-saver` `saveAs()` or `<a download>` + `URL.createObjectURL` |

### 5.3 DOCX Import

```javascript
async function importDocx(file) {
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  if (result.messages.length) console.warn('Mammoth warnings:', result.messages);
  loadDocumentText(result.value, { filename: file.name });
}
```

| Requirement | Implementation |
|-------------|----------------|
| Mammoth.js | `extractRawText` only |
| Text only | No `convertToHtml` |
| Ignore tables/images | Default Mammoth raw text behavior |
| Paragraphs | Normalize `\n\n` → preserve |

**Accept attribute**: `.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document`

### 5.4 DOCX Export

```javascript
async function exportDocx() {
  const text = getEditorText();
  const paragraphs = text.split(/\n\s*\n/).filter(Boolean).map(block =>
    new docx.Paragraph({
      bidirectional: true,
      children: [new docx.TextRun({ text: block, rightToLeft: true, font: 'Arial' })],
      alignment: docx.AlignmentType.RIGHT
    })
  );
  const doc = new docx.Document({
    sections: [{ properties: { rightToLeft: true }, children: paragraphs }]
  });
  const blob = await docx.Packer.toBlob(doc);
  saveAs(blob, defaultFilename('docx'));
}
```

| Requirement | Implementation |
|-------------|----------------|
| docx.js | `Document`, `Paragraph`, `TextRun`, `Packer` |
| Paragraphs | Split on double newline (fallback: single `\n`) |
| RTL | `rightToLeft: true` on section + `bidirectional: true` on paragraphs |
| Font | Arial or Traditional Arabic (Word-safe) |

### 5.5 PDF Export

```javascript
async function exportPdf() {
  const text = getEditorText();
  const el = buildPdfExportNode(text); // off-screen div, dir=rtl, Cairo font
  await html2pdf().set({
    margin: 15,
    filename: defaultFilename('pdf'),
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  }).from(el).save();
}
```

| Requirement | Implementation |
|-------------|----------------|
| Arabic rendering | Clone styled RTL node with Cairo font |
| Content source | `getEditorText()` (plain text, not highlighted HTML) |
| Theme | Export node uses light theme tokens for readability |

---

## 6. UI Design

### 6.1 Toolbar Layout (proposed)

```
┌──────────────────────────────────────────────────────────────────┐
│ [كتابة] [تلخيص]  │  [↑ استيراد]  [↓ تصدير ▾]  │  جاري... │ ١٢٣ كلمة │
└──────────────────────────────────────────────────────────────────┘
```

**Import button** (`btn-ghost`):
- Label: `استيراد`
- Icon: upload arrow
- Opens file picker (`.txt,.docx`)
- `aria-label="استيراد ملف نصي أو Word"`

**Export dropdown** (`btn-ghost` + menu):
```
تصدير ▾
  ├── ملف نصي (.txt)
  ├── Word (.docx)
  └── PDF (.pdf)
```

### 6.2 Design System Compliance

| Element | Classes |
|---------|---------|
| Import button | `.btn-ghost`, `.doc-btn` |
| Export trigger | `.btn-ghost`, `.doc-dropdown__trigger` |
| Menu panel | `.surface-card`, `.doc-dropdown__menu` |
| Menu items | `.doc-dropdown__item` |
| Focus | `:focus-visible` via existing tokens |
| Theme | `var(--color-surface)`, `var(--color-border)`, `var(--color-text-primary)` |

### 6.3 Mobile

- Import + Export move to editor footer alongside `مسح الكل` / `نسخ النص`
- Export dropdown opens as bottom sheet on `<640px` (reuse Phase 2 pattern)

### 6.4 User Feedback

| Event | Feedback |
|-------|----------|
| Import success | Toast: `تم تحميل الملف` |
| Import error | Toast: `تعذر قراءة الملف` |
| Export success | Browser download (implicit) |
| File too large for analysis | Banner: `النص أطول من ٥٠٠٠ حرف — التحليل على الجزء الأول فقط` |
| Empty export | Disable export items when editor empty |

---

## 7. Implementation Roadmap

### Phase 4.1 — Foundation (1 day)

| Task | Verify |
|------|--------|
| Create `documents/doc-utils.js` | Unit: `normalizeImportedText`, `downloadBlob` |
| Add `loadDocumentText()` to `editor.js` | Import "مرحبا" → editor shows text, analyze runs |
| Add CDN scripts to `index.html` | Libraries load without console errors |

### Phase 4.2 — TXT I/O (0.5 day)

| Task | Verify |
|------|--------|
| `importTxt()` + file input | Arabic .txt round-trips correctly |
| `exportTxt()` | Downloaded file opens in Notepad with correct Arabic |

### Phase 4.3 — DOCX Import (1 day)

| Task | Verify |
|------|--------|
| Integrate Mammoth.js | Sample .docx loads as plain text |
| Error handling | Corrupt file shows user message |
| Paragraph breaks | Multi-paragraph doc preserves structure |

### Phase 4.4 — DOCX Export (1 day)

| Task | Verify |
|------|--------|
| Integrate docx.js | File opens in Word |
| RTL verification | Arabic aligns right in Word |
| Paragraph mapping | Blank lines → new paragraphs |

### Phase 4.5 — PDF Export (1–2 days)

| Task | Verify |
|------|--------|
| html2pdf.js integration | PDF downloads |
| Arabic visual check |-glyphs render correctly |
| Multi-page | Long text paginates |

### Phase 4.6 — UI + Polish (1 day)

| Task | Verify |
|------|--------|
| Toolbar import/export buttons | Matches design system both themes |
| Mobile layout | Footer placement works |
| Empty state / loading states | Disabled when appropriate |
| Toast notifications | Success/error feedback |

### Phase 4.7 — QA (0.5 day)

| Task | Verify |
|------|--------|
| Full testing checklist | All pass |
| `node test_renderer.js` | Still passes (no regression) |
| Manual Phase 1 tests | Duplicate highlights, cursor, XSS |

**Total estimate**: 6–7 working days

---

## 8. Risk Analysis

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| R1 | **Arabic PDF garbled** | High | Medium | Use html2pdf with Cairo font on RTL clone; fallback Phase 4.1: jsPDF + Amiri |
| R2 | **DOCX export RTL broken in Word** | Medium | Medium | Test `rightToLeft` section + `bidirectional` paragraphs; use Word-safe font |
| R3 | **Mammoth loses complex DOCX structure** | Low | High | Expected — document "text only" scope; show warning if messages |
| R4 | **Import XSS** | High | Low | Always `escapeHtml()` before `setEditorHTML()` |
| R5 | **Import breaks cursor/offsets** | Medium | Low | Use `loadDocumentText()` → `setEditorHTML` + fresh analyze (same as clear+type) |
| R6 | **File > 5000 chars breaks analyze** | Medium | High | Warn user; full text still editable/exportable |
| R7 | **CDN library unavailable offline** | Medium | Medium | Vendor copies in `src/js/vendor/` for graduation demo |
| R8 | **docx.js UMD global name mismatch** | Low | Medium | Verify `window.docx` after script load in dev |
| R9 | **Large file memory** | Low | Low | Client-side limit ~2MB; reject with message |
| R10 | **Phase 1 regression** | High | Low | Do not touch `renderer.js` / `selection.js`; run existing tests |

### 8.1 Critical Path

```
TXT import/export (low risk, validates architecture)
    → DOCX import (Mammoth)
    → DOCX export (RTL)
    → PDF export (Arabic rendering)  ← highest risk, schedule last
```

---

## 9. Testing Checklist

### 9.1 TXT

- [ ] Import UTF-8 Arabic `.txt` — text appears correctly in editor
- [ ] Import UTF-8 with BOM — BOM stripped, text correct
- [ ] Import Windows-1256 file — detect mojibake or reject gracefully
- [ ] Export `.txt` — re-import round-trip preserves content
- [ ] Export empty editor — button disabled or shows error
- [ ] Import triggers `analyzeTextDelayed()` — highlights appear

### 9.2 DOCX Import

- [ ] Import simple Arabic `.docx` — text loads
- [ ] Multi-paragraph document — paragraph breaks preserved
- [ ] DOCX with images/tables — text extracted, no crash
- [ ] Invalid/corrupt file — error toast, editor unchanged
- [ ] `.doc` (legacy) — rejected by accept filter

### 9.3 DOCX Export

- [ ] Export opens in Microsoft Word without error
- [ ] Export opens in LibreOffice Writer
- [ ] Arabic text is right-aligned
- [ ] Paragraph breaks match editor
- [ ] Empty lines preserved as empty paragraphs
- [ ] Re-import exported DOCX — content matches (round-trip via Mammoth)

### 9.4 PDF Export

- [ ] PDF downloads with correct filename
- [ ] Arabic glyphs render correctly (visual inspection)
- [ ] Multi-page document paginates
- [ ] Long Arabic text (2000+ chars) exports without truncation
- [ ] Empty editor — export disabled

### 9.5 UI / Theme

- [ ] Import button visible in dark theme
- [ ] Import button visible in light theme
- [ ] Export dropdown readable in both themes
- [ ] Keyboard: Tab reaches import/export controls
- [ ] Mobile: buttons accessible in footer
- [ ] `aria-label` on import and export controls

### 9.6 Phase 1 Regression (must pass)

- [ ] `node test_renderer.js` — all tests pass
- [ ] Type in editor after import — cursor preserved on analyze
- [ ] Duplicate word highlights (`ذهبو` ×3) — independent spans
- [ ] Click highlight → popover → apply correction
- [ ] `<script>` in imported text — escaped, not executed
- [ ] Sidebar suggestions update after import + analyze

### 9.7 Edge Cases

- [ ] Import 10,000 char file — loads; warning shown for analyze limit
- [ ] Import while analysis in progress — AbortController cancels prior request
- [ ] Switch theme during export — export still works
- [ ] Arabic filename in download — `document.txt` default used if problematic

---

## 10. Approval Gate

**No implementation until this plan is reviewed.**

Please confirm:

1. **PDF approach**: html2pdf.js (visual, easier Arabic) vs jsPDF + embedded Amiri font (searchable, harder)?
2. **Analyze limit**: Warn only, or truncate analysis to first 5000 chars automatically?
3. **CDN vs vendored libs**: CDN for dev, copy to `src/js/vendor/` for offline demo?
4. **Default export filename**: `بيان-مستند.txt` or `bayan-document.txt`?
5. **Proceed with implementation** after approval?

---

## Related Documents

| Document | Role |
|----------|------|
| [`PHASE_1_COMPLETE_VERIFICATION.md`](PHASE_1_COMPLETE_VERIFICATION.md) | Editor engine constraints |
| [`PHASE_2_STATUS.md`](PHASE_2_STATUS.md) | UI / theme context |
| [`THEME_SYSTEM.md`](THEME_SYSTEM.md) | Design tokens for new UI |

---

*Preserves Phase 1 architecture: `renderer.js` and `selection.js` remain untouched. All document I/O flows through `getEditorText()` / `loadDocumentText()`.*
