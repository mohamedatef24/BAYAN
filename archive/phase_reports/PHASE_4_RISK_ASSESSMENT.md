# Phase 4 — Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Phase 1 regression | High | No changes to renderer.js / selection.js; run test_renderer.js |
| XSS on import | High | escapeHtml() before setEditorHTML |
| Arabic PDF rendering | Medium | html2pdf + Cairo RTL clone node |
| DOCX RTL in Word | Medium | rightToLeft section + bidirectional paragraphs |
| Analyze >5000 chars | Medium | API gets substring; banner warns user |
| CDN offline | Medium | Local vendor copies in src/js/vendor/ |
| docx.js global missing | Low | Guard with typeof docx check + error toast |
| Large file memory | Low | 2MB client-side size limit |

## Critical path

TXT → DOCX import → DOCX export → PDF (highest visual risk last)
