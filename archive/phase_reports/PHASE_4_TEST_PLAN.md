# Phase 4 — Test Plan

## Automated

- [ ] `node test_renderer.js` — all pass (no regression)

## TXT

- [ ] Import UTF-8 Arabic .txt → editor shows text
- [ ] Import with BOM → BOM stripped
- [ ] Export → `bayan-document.txt` downloads
- [ ] Round-trip: export → re-import preserves content
- [ ] Import triggers analysis

## DOCX

- [ ] Import .docx via Mammoth → plain text in editor
- [ ] Export .docx → opens in Word, RTL Arabic
- [ ] Corrupt file → error toast, no crash

## PDF

- [ ] Export PDF → `bayan-document.pdf` downloads
- [ ] Arabic renders in PDF (visual)
- [ ] No highlight markup in export

## Long document

- [ ] Import >5000 chars → full text loaded
- [ ] Banner shown
- [ ] Export uses full text

## Phase 1 regression

- [ ] Cursor preserved after import + analyze
- [ ] Duplicate highlights work
- [ ] `<script>` in import escaped

## UI

- [ ] Import/Export in dark + light theme
- [ ] Empty editor disables export
- [ ] aria-labels present
