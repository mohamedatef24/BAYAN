# BAYAN — Architecture Consistency Audit

**Date:** 2026-06-18

---

## Methodology

Compare the architecture documentation (`docs/architecture/01-system-overview.md`) against the actual deployed codebase to identify any drift.

---

## Client Layer

| Documented | Code | Status |
|-----------|------|--------|
| Landing Page | `index.html` → `showPage('landing')` | ✅ Match |
| Features Page | `showPage('features')` | ✅ Match |
| Editor Page | `showPage('editor')` | ✅ Match |
| Pricing Page | `showPage('pricing')` | ✅ Match |
| Editor Engine (`editor.js`) | `src/js/editor.js` (637 lines) | ✅ Match |
| Renderer (`renderer.js`) | `src/js/renderer.js` | ✅ Match |
| Selection (`selection.js`) | `src/js/selection.js` | ✅ Match |
| Auth Module | `src/js/auth.js` (Guest + Google) | ✅ Match |
| Sync Engine | `src/js/sync/` | ✅ Match |
| Documents | `src/js/documents/` | ✅ Match |
| Summaries | `src/js/summaries/` | ✅ Match |
| Settings | `src/js/settings/` | ✅ Match |
| Export (TXT/DOCX/PDF) | `src/js/export.js` | ✅ Match |

**Client Layer: 13/13 match** ✅

---

## API Layer

| Documented | Code | Status |
|-----------|------|--------|
| `/api/health` | `app.py:147` | ✅ Match |
| `/api/analyze` | `app.py:820` | ✅ Match |
| `/api/spelling` | `app.py:253` | ✅ Match |
| `/api/grammar` | `app.py:420` | ✅ Match |
| `/api/punctuation` | `app.py:516` | ✅ Match |
| `/api/summarize` | `app.py:580` | ✅ Match |
| `/api/autocomplete` | Documented but NOT YET IMPLEMENTED | ⬜ Expected (NLP-4) |
| Flask + Gunicorn | `Dockerfile` CMD | ✅ Match |
| CORS | `CORS(app, ...)` line 68 | ✅ Match |

**API Layer: 8/8 match** (autocomplete planned for NLP-4) ✅

---

## NLP Layer

| Documented | Code | Status | Notes |
|-----------|------|--------|-------|
| AraSpell (AraBERT) | `src/nlp/spelling/araspell_service.py` | ✅ Match | |
| Grammar Rules Engine | `src/nlp/grammar/grammar_rules.py` | ✅ Match | |
| Grammar Service (Gradio) | `src/nlp/grammar/grammar_service.py` | ✅ Match | |
| PuncAra-v1 | `src/nlp/punctuation/punctuation_service.py` | ✅ Match | |
| Summarization (MBart) | `model_loader.py` | ✅ Match | |
| AutoComplete | NOT YET IMPLEMENTED | ⬜ Expected | NLP-4 |
| ModelLoader orchestration | Doc says centralized; Code uses lazy singletons per module | ⚠️ Drift | Minor — lazy singletons are better |

> [!NOTE]
> The architecture doc mentions a centralized `ModelLoader` but the actual implementation uses per-module lazy singletons (`get_spelling_model()`, `get_grammar_checker()`, `get_punctuation_model()`). This is actually a **better** pattern because each model loads independently and doesn't block others. The documentation should be updated to reflect this.

**NLP Layer: 5/6 match** (1 minor drift, 1 not yet) ✅

---

## Data Layer

| Documented | Code | Status |
|-----------|------|--------|
| Supabase (PostgreSQL) | Frontend SDK calls | ✅ Match |
| `profiles` table | Referenced in auth | ✅ Match |
| `documents` table | Referenced in documents-api | ✅ Match |
| `summaries` table | Referenced in summaries-api | ✅ Match |
| `settings` table | Referenced in settings-api | ✅ Match |
| localStorage (drafts) | `editor.js` line 85 | ✅ Match |
| localStorage (dismissed) | `editor.js` line 49 | ✅ Match |

**Data Layer: 7/7 match** ✅

---

## Infrastructure

| Documented | Code | Status |
|-----------|------|--------|
| HuggingFace Spaces | Deployed at `bayan10/bayan-api` | ✅ Match |
| Docker | `Dockerfile` (76 lines) | ✅ Match |
| GitHub Repository | `mohamedatef24/BAYAN` | ✅ Match |
| GitHub Actions CI/CD | NOT FOUND | ❌ Drift |
| Google OAuth Provider | Supabase + Google Client ID | ✅ Match |

> [!WARNING]
> The architecture doc mentions GitHub Actions CI/CD, but no `.github/workflows/` directory exists. Deployment is done via manual git push to HF Spaces. This should either be implemented or removed from the documentation.

**Infrastructure: 4/5 match** ⚠️

---

## Pipeline Flow

### Documented:
```
Input → AraSpell → Grammar → Punctuation → Output
```

### Actual (`app.py` lines 853-932):
```
Input → AraSpell (Step 1) → Grammar (Step 2) → Punctuation (Step 3) → Dedup → Output
```

**✅ Match** — Pipeline order exactly as documented, with dedup as a bonus.

---

## Drift Summary

| Area | Issue | Severity | Action |
|------|-------|----------|--------|
| ModelLoader | Doc says centralized; code uses lazy singletons | Low | Update docs |
| CI/CD | Doc mentions GitHub Actions; none exist | Medium | Add or remove from docs |

**Total Consistency: 37/39 (95%)** ✅

---

## Recommendation

Update `docs/architecture/01-system-overview.md` to:
1. Replace `ModelLoader` with "Lazy-loaded Singleton Services"
2. Remove GitHub Actions CI/CD or add `planned` label
3. Add note about dedup layer in pipeline
