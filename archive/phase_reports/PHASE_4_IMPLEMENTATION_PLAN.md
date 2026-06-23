# Phase 4 — Implementation Plan

**Date**: June 15, 2026  
**Scope**: Client-side document import/export (Vanilla JS)

## Approach

1. Add `loadDocumentText()` to `editor.js` — sole write path for imports
2. Add `documents/` module — import/export logic only
3. Truncate API analyze to first 5000 chars; render highlights on full text
4. Vendor libs in `src/js/vendor/` + CDN fallback in `index.html`
5. UI: Import button + Export dropdown in toolbar; mobile footer + sheet

## Implementation Order

| Step | Task | Files |
|------|------|-------|
| 1 | `doc-utils.js` — normalize, download, split paragraphs | documents/ |
| 2 | `loadDocumentText()` + analyze limit | editor.js, ui.js |
| 3 | TXT import/export | import.js, export.js |
| 4 | DOCX import (Mammoth) | import.js |
| 5 | DOCX export (docx.js) | export.js |
| 6 | PDF export (html2pdf) | export.js |
| 7 | UI wiring | documents.js, index.html, components.css |

## Untouched

- `renderer.js`, `selection.js`, `app.py`
