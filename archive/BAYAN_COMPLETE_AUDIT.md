# BAYAN — Complete Product, Codebase & Extension Deep Audit

> **Audit Date:** 2026-06-27  
> **Auditor Perspective:** Product Manager + Senior Frontend + Backend Architect + Extension Engineer + SaaS Reviewer  
> **Scope:** Website, Backend API, Chrome Extension, Auth/Database, AI Models, UX, Security, Performance, Code Quality

---

## 1. Current System Overview

### Architecture Map

```
┌────────────────────────────────────────────────────────────────┐
│                       BAYAN ECOSYSTEM                          │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │  Website SPA  │───▶│  Flask API   │───▶│  NLP Pipeline   │  │
│  │ (index.html)  │    │  (app.py)    │    │ Spell→Gram→Punct│  │
│  │ 33 JS files   │    │  2,844 lines │    │ PipelineContext  │  │
│  └──────┬───────┘    └──────┬───────┘    │ PatchSet/Locker  │  │
│         │                   │            └─────────────────┘  │
│         │                   │                                  │
│         │            ┌──────┴───────┐    ┌─────────────────┐  │
│         │            │ Local Models  │    │ Remote Grammar  │  │
│         │            │ Spelling      │    │ (Gradio Space)  │  │
│         │            │ Punctuation   │    │ Latency: 3-8s   │  │
│         │            │ Summarization │    └─────────────────┘  │
│         │            │ Dialect (mT5) │                         │
│         │            │ Autocomplete  │                         │
│         │            └──────────────┘                          │
│         │                                                      │
│  ┌──────┴───────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │   Supabase    │◀──│   Auth Module │──▶│ Documents DB     │  │
│  │   (Cloud)     │   │ Guest+Google  │   │ Settings Sync    │  │
│  │   Client-side │   │ PKCE OAuth    │   │ Summaries        │  │
│  └──────────────┘    └──────────────┘    └─────────────────┘  │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Chrome Extension (MV3 v2.1.0)             │    │
│  │  ┌───────────┐ ┌────────────┐ ┌─────────────────────┐ │    │
│  │  │ Content   │ │ Background │ │  Side Panel + Popup  │ │    │
│  │  │ Script    │ │  Worker    │ │  5 tabs each         │ │    │
│  │  │ Overlay+  │ │  Cache+    │ │  Correct/Summarize/  │ │    │
│  │  │ Ghost txt │ │  Retry     │ │  Dialect/Quran/Auto  │ │    │
│  │  └───────────┘ └────────────┘ └─────────────────────┘ │    │
│  │  NO AUTH │ NO DOCUMENTS │ NO SYNC │ NO EXPORT          │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | Vanilla JS, HTML, CSS (Tailwind CDN dev mode) | Custom `contenteditable` editor, 33 script tags, no bundler |
| **Backend** | Flask (Python) | Single monolith `app.py` — 2,844 lines |
| **NLP Pipeline** | Custom Python modules | 3-stage: Spelling → Grammar → Punctuation with PipelineContext/PatchSet/StageLocker |
| **AI Models** | 6 transformer-based models | Spelling (AraSpell), Grammar (remote Gradio), Punctuation (PuncAra-v1), Summarization (mBART), Dialect (mT5-300M), Autocomplete (AraBERT + AraGPT2) |
| **Database** | Supabase (PostgreSQL) | Documents, profiles, settings, summaries — all client-side only |
| **Auth** | Supabase Auth (PKCE) | Guest (anonymous) + Google OAuth, 8s timeout + offline fallback |
| **Deployment** | HuggingFace Spaces (Docker) | CPU-only free tier, ~60s cold start |
| **Extension** | Chrome MV3 | Background SW, Content Script (all sites), Side Panel, Popup |

### File Structure Summary

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/` | `app.py`, `hf_inference.py`, `model_loader.py` + HTML/CSS | Backend + serving |
| `src/js/` | 8 core JS files | Editor, renderer, selection, UI, theme, format, autocomplete, api |
| `src/js/auth/` | 5 files | Supabase auth (config, client, session, auth, auth-ui) |
| `src/js/documents/` | 4 files | Local doc management (documents, doc-utils, export, import) |
| `src/js/documents-cloud/` | 3 files | Supabase CRUD (api, state, ui) |
| `src/js/sync/` | 3 files | Offline queue (manager, queue, resolver) |
| `src/js/settings-sync/` | 2 files | User settings cloud persistence |
| `src/js/summaries/` | 2 files | Cloud summaries (api, ui) |
| `src/nlp/` | 6 subdirs | All NLP processing modules |
| `extension/` | 8 files + 4 subdirs | Chrome Extension |
| `extension/shared/` | 9 files | Shared utilities (api, renderer, patches, state, hash, ui, config, constants, analysis-controller) |
| `extension/sidepanel/` | 3 files | Side panel (HTML, JS, CSS) |
| `tests/` | 16+ test files | Backend unit/integration tests |
| `extension/tests/` | 8 files | Extension integration tests |

### NLP Pipeline Architecture

```
User Input → PipelineContext(text)
    │
    ├─[1] SPELLING  (if text ≤ 1000 chars && not religious && not URLs/hashtags)
    │   AraSpell seq2seq + beam search (5 beams)
    │   10-step postprocessing: hybrid alignment, MLM validation, bidirectional check
    │   20+ safety guards (edit distance, length ratio, first-letter, numeral, pronoun suffix...)
    │   ctx.mutate_text() → OffsetMapper chain
    │
    ├─[2] GRAMMAR   (if not religious text)
    │   Remote Gradio API → mohammedahmedezz2004/bayan_arabic_grammarly_correction
    │   ArabicGrammarGuard: 14 rule-based post-passes (camel-tools MLE disambiguator)
    │   Jaccard hallucination filter, directional blocks, 10+ safety guards
    │   StageLocker hierarchy: grammar(3) > spelling(2) > punctuation(1)
    │   ctx.mutate_text() → OffsetMapper chain
    │
    ├─[3] PUNCTUATION (if not religious && spelling+grammar made corrections)
    │   PuncAra-v1 local model (50-word chunks, beam=3)
    │   validate_punctuation_diff() safety layer
    │   Max 3 punctuation patches cap
    │   ctx.mutate_text() → OffsetMapper chain
    │
    └─ PatchSet.resolve_overlaps() → API Response
       Deterministic greedy: priority DESC, confidence DESC, start ASC
```

---

## 2. Feature Inventory

### Core AI Features

| Feature | Backend API | Website | Extension | Key Files |
|---------|------------|---------|-----------|-----------|
| **Spelling** | ✅ `/api/spelling` + `/api/analyze` | ✅ Inline highlights, suggestions, apply/dismiss | ✅ Content script overlay + Popup + SidePanel | `nlp/spelling/araspell_service.py`, `araspell_rules.py` |
| **Grammar** | ✅ `/api/grammar` + `/api/analyze` | ✅ Via remote Gradio proxy + 14 rule-based postprocessors | ✅ Content script overlay + Popup + SidePanel | `nlp/grammar/grammar_service.py`, `grammar_rules.py` |
| **Punctuation** | ✅ `/api/punctuation` + `/api/analyze` | ✅ PuncAra-v1 local model | ✅ Content script overlay + Popup + SidePanel | `nlp/punctuation/punctuation_service.py` |
| **Summarization** | ✅ `/api/summarize` | ✅ Editor tab with length slider + paragraph/bullets mode | ✅ Popup tab + SidePanel tab | `model_loader.py`, `summaries-api.js` |
| **Autocomplete** | ✅ `/api/autocomplete` | ✅ Ghost text + dropdown, word-boundary triggered | ⚠️ Ghost text for textarea/input only, button-click in popup/sidepanel | `autocomplete.js`, `content-inline.js` |
| **Dialect→MSA** | ✅ `/api/dialect` | ✅ Dedicated editor tab | ✅ Popup + SidePanel tabs | `nlp/dialect/dialect_service.py` |
| **Quran Verification** | ✅ `/api/quran` | ✅ Dedicated editor tab + 13-language translation | ✅ SidePanel (with translation), Popup | `quran.py`, `quran_master.db` |

### Platform Features

| Feature | Website | Extension Popup | Extension SidePanel | Extension Content Script |
|---------|---------|----------------|---------------------|-------------------------|
| **Authentication** | ✅ Guest + Google OAuth + linking | ❌ None | ❌ None | ❌ None |
| **Cloud Documents** | ✅ Full CRUD (create/load/save/rename/delete) | ❌ None | ❌ None | ❌ None |
| **Cloud Summaries** | ✅ Save/load/delete (Supabase) | ❌ None | ❌ None | ❌ None |
| **Offline Sync** | ✅ LocalStorage queue + auto-flush | ❌ None | ❌ None | ❌ None |
| **Settings Sync** | ✅ Theme synced to cloud | ❌ None | ❌ None | ❌ None |
| **Export** | ✅ TXT + DOCX + PDF | ✅ TXT only | ✅ TXT only | ❌ None |
| **Import** | ✅ TXT + DOCX (mammoth.js) | ❌ None | ❌ None | ❌ None |
| **Undo/Redo** | ✅ Custom 50-level stack | ❌ Browser default only | ❌ Browser default only | ❌ N/A |
| **Word Count Goal** | ✅ Configurable progress indicator | ❌ None | ❌ None | ❌ N/A |
| **Score Ring** | ✅ Animated SVG | ✅ Simplified SVG | ✅ Simplified SVG | ❌ None |
| **Dismissed Words** | ✅ Persisted in localStorage | ❌ None | ❌ None | ❌ None |
| **Theme Toggle** | ✅ Dark/Light + sync | ❌ Dark only | ❌ Dark only | N/A |
| **Keyboard Shortcuts** | ✅ Extensive (Alt+1-3, Ctrl+S, Ctrl+Q) | ❌ None | ❌ None | Tab for autocomplete only |
| **Rich Text Formatting** | ✅ Full toolbar (bold, italic, lists, links, etc.) | ❌ None | ❌ None | ❌ N/A |
| **Suggestion Feedback** | ✅ Thumbs up/down | ❌ None | ❌ None | ❌ None |
| **Draft Auto-save** | ✅ localStorage on every keystroke | ❌ Lost on close | ✅ chrome.storage.session | ❌ N/A |
| **Write-back to Page** | N/A | ❌ None | ✅ Selection-aware splice | ✅ Via background relay |
| **Quran Translation** | ✅ 13 languages | ❌ None | ✅ 13 languages | ❌ None |

---

## 3. Website vs Extension Comparison

### Authentication

| Aspect | Website | Extension | Gap |
|--------|---------|-----------|-----|
| Guest login | ✅ `signInAnonymously()` with 8s timeout | ❌ Zero auth code | **Critical** |
| Google OAuth | ✅ PKCE flow via Supabase | ❌ | **Critical** |
| Session restore | ✅ `getSession()` from localStorage | ❌ | **Critical** |
| Identity linking | ✅ Guest → Google upgrade | ❌ | **High** |
| Offline fallback | ✅ `enableOfflineAuthMode()` | ❌ | **High** |
| Auth-gated features | ✅ Documents, sync, settings | ❌ All features work without auth | **Critical** |

### AI Feature UX Comparison

| Feature | Website UX | Extension UX | Parity |
|---------|-----------|-------------|--------|
| Analyze (S+G+P) | Rich editor with inline colored highlights, suggestion sidebar with cards, popover tooltips, apply/dismiss per-suggestion, apply-all, score ring, error donut | **Content Script:** Transparent overlay with colored marks + tooltip on hover. **Popup/SidePanel:** Textarea input + suggestion cards + score ring | ⚠️ Functional but significant UX gap |
| Summarize | Editor tab with length slider, paragraph/bullets toggle, copy/export/save-to-cloud | Popup/SidePanel: textarea + radio buttons (short/medium/long) + copy + TXT download | ✅ Near parity |
| Autocomplete | Ghost text inside editor + dropdown, word-boundary triggered, 400ms debounce, Tab to accept | **Content Script:** Ghost text for textarea/input only (NOT contenteditable). **Popup/SidePanel:** Button-click only | ⚠️ Missing core inline UX on most web editors |
| Dialect | Dedicated tab, convert + copy + apply-to-editor | Popup/SidePanel: textarea + convert + copy | ✅ Near parity |
| Quran | Dedicated tab, verify + 13-language translation + modal + apply-to-editor (protected spans) | Popup: basic verify. SidePanel: full verify + 13-language translation + apply-to-page | ✅ SidePanel has full parity |

### Documents & Data

| Aspect | Website | Extension | Gap |
|--------|---------|-----------|-----|
| Create document | ✅ `createDocument()` via Supabase | ❌ No Supabase integration | **Critical** |
| List/search documents | ✅ Sidebar panel with search | ❌ | **Critical** |
| Auto-save + sync | ✅ 2.5s debounced via SyncManager | ❌ | **Critical** |
| Offline queue | ✅ LocalStorage persistence, auto-flush on reconnect | ❌ | **High** |
| Export PDF/DOCX | ✅ docx.js + html2pdf | ❌ TXT download only | **Medium** |
| Import TXT/DOCX | ✅ FileReader + mammoth.js | ❌ | **Low** |
| Conflict resolution | ✅ Last-write-wins timestamp comparison | ❌ N/A | N/A |

---

## 4. Missing Features

### Critical (Blocks Production Use)

| # | Feature | Impact | Recommended Solution |
|---|---------|--------|---------------------|
| C1 | **No API rate limiting** | Any client can overwhelm the free-tier HF Space with unlimited requests to compute-intensive NLP endpoints | Add Flask-Limiter: 30 req/min/IP for `/api/analyze`, 10/min for `/api/summarize` |
| C2 | **CORS wildcard `origins: "*"`** (`app.py:94`) | Any website can proxy through Bayan's API, enabling compute theft and abuse | Restrict to `["https://bayan10-bayan-api.hf.space", "chrome-extension://<ext-id>"]` |
| C3 | **Extension has zero authentication** | Extension users cannot access cloud documents, settings, or history — breaks SaaS value proposition | Implement Supabase auth via `chrome.identity.launchWebAuthFlow()` for Google OAuth |

### High (Important Feature Gap)

| # | Feature | Impact | Recommended Solution |
|---|---------|--------|---------------------|
| H1 | **Missing Supabase migration files** for `documents`, `summaries`, `settings` tables | Only `001_profiles.sql` exists. RLS policies are documented but not version-controlled. Database cannot be recreated from migrations. | Create `002_documents.sql`, `003_summaries.sql`, `004_settings.sql` with RLS |
| H2 | **Extension content script lacks autocomplete ghost text on contenteditable** | The flagship ghost-text feature only works on `<textarea>`/`<input>`, not on contenteditable elements (which most web editors use) | Port autocomplete logic to work with contenteditable in `content-inline.js` |
| H3 | **No document versioning or history** | Each cloud save overwrites previous content. Hard delete with no recovery. No revision history. | Add `document_versions` table or soft-delete with `deleted_at` column |
| H4 | **Backend monolith: `app.py` is 2,844 lines** | `analyze_text()` alone is 1,224 lines. Extremely difficult to maintain, test, or extend. | Split into `routes/`, `services/`, `middleware/` modules |
| H5 | **Extension popup/sidepanel have no DOCX/PDF export** | Users can only download as TXT from extension | Add at minimum "Copy as formatted text"; ideally add DOCX export |

### Medium (Improvement Needed)

| # | Feature | Impact | Recommended Solution |
|---|---------|--------|---------------------|
| M1 | **Grammar model depends on external Gradio Space** | Hard dependency on `mohammedahmedezz2004/bayan_arabic_grammarly_correction`. If Space sleeps (HF free tier), first request has 10-30s cold start. If down, grammar breaks entirely. | Host grammar model directly on Bayan Space, or add rule-only fallback |
| M2 | **No Content Security Policy** | Neither the website nor extension manifest declares a CSP. Website serves no CSP headers from Flask. | Add CSP headers in Flask and explicit CSP in extension manifest |
| M3 | **Extension dismissed-words whitelist missing** | Users must dismiss the same false-positive words repeatedly across sessions | Persist dismissed words in `chrome.storage.local` |
| M4 | **No i18n framework on website** | All strings hardcoded in Arabic HTML. Adding English support requires rewriting HTML. | Add simple i18n JSON loader (extension already has `_locales/ar/`) |
| M5 | **Sync conflict resolution is lossy** | Last-write-wins silently discards the losing version with no user notification, no merge attempt. Clock skew between client `Date.now()` and server `updated_at` can cause wrong winner. | Show conflict notification to user, or implement operational transform |
| M6 | **Only theme is synced in settings** | `settings_sync.js` only syncs `theme`. Other potential settings (font size, word goal, autocomplete toggle) are not synced. | Extend `preferences` JSONB column to include all user settings |

### Low (Nice to Have)

| # | Feature | Impact | Recommended Solution |
|---|---------|--------|---------------------|
| L1 | Extension only has Arabic locale | Cannot target non-Arabic Chrome Web Store users | Add `_locales/en/messages.json` |
| L2 | No analytics or telemetry | No visibility into usage patterns, error rates, or feature adoption | Add lightweight privacy-respecting event tracking |
| L3 | Vendor libraries loaded synchronously | `mammoth.browser.min.js` (340KB), `docx.umd.js` (1.2MB), `html2canvas.min.js` (210KB) block initial render even if never used | Lazy-load on first export action |
| L4 | No service worker for website | No offline caching for static assets | Add basic SW for asset caching |
| L5 | No onboarding flow | First-time users see empty editor with no guidance | Add sample text + guided tooltips |

---

## 5. Bugs Found

### Active Bugs

| # | Bug | Severity | Location | Details |
|---|-----|----------|----------|---------|
| B1 | **`/api/punctuation` has no `MAX_TEXT_LENGTH` check** | **High** | `app.py:596-647` | All other text endpoints enforce `MAX_TEXT_LENGTH = 5000`. Punctuation endpoint accepts unlimited input, allowing resource exhaustion via a single large request. |
| B2 | **Race condition in `_isApplyingSuggestion` timing** | **High** | `editor.js` | Guard resets after 400ms but `analyzeText()` is called after 300ms. 100ms window where a suggestion application triggers recursive analysis, corrupting state. |
| B3 | **Undo stack captures error overlay HTML** | **Medium** | `editor.js` | `pushUndoState()` saves `editor.innerHTML` including colored suggestion `<span>` elements. Undoing restores stale suggestion markup that doesn't correspond to current analysis. |
| B4 | **`getEditorText()` clones entire DOM on every keystroke** | **Medium** | `selection.js` | `editor.cloneNode(true)` called on every `input` event via `updateEditorStats()`. For large documents, this is a significant performance hit. |
| B5 | **Zero-width space from `formatFontSize` causes offset errors** | **Medium** | `format.js:126` | Inserts `​` (zero-width space) when selection is collapsed. This invisible character is counted in text offsets, causing off-by-one errors in suggestion positions. |
| B6 | **`restoreSelection` broken for non-collapsed selections** | **Medium** | `selection.js` | For range selections, the start Range is created but never added to the Selection object. `getRangeAt(0)` then operates on the browser's stale selection state. |
| B7 | **Color picker reset removes ALL formatting** | **Medium** | `format.js:335` | Reset button calls `removeFormat` which strips ALL formatting (bold, italic, etc.), not just the color. |
| B8 | **`overlaySuggestions` skips `.quran-applied` check on rebuilds** | **Medium** | `renderer.js:349-351` | Initial text node walk (line 253-256) skips `.quran-applied` nodes, but the per-suggestion rebuild at line 349 does NOT, causing protected Quran text to be modified. |
| B9 | **`/api/quran` bypasses Content-Type check** | **Low** | `app.py` | Uses `request.get_json(force=True)` which accepts any Content-Type. All other endpoints properly check `request.is_json` first. |
| B10 | **`/api/quran` inconsistent response format** | **Low** | `app.py` | Returns bare `jsonify(result)` without wrapping in `{'status': 'success', ...}` format used by all other endpoints. |
| B11 | **`/api/autocomplete` `n` parameter unbounded** | **Low** | `app.py` | `n` is cast to int without bounds checking. `n=1000000` would attempt to generate a million suggestions. |
| B12 | **`updateSummaryLength()` is a no-op** | **Low** | `index.html:~1920` | Empty function body — the summary length slider label never updates to reflect the selected value. |
| B13 | **Extension overlay position breaks in scrollable containers** | **Medium** | `content-inline.js` | Overlay positioned with `getBoundingClientRect() + window.scrollY` (absolute). Breaks when text field is inside a scrollable `<div>` rather than the window. Tracks window scroll but not ancestor scroll. |
| B14 | **Infinite retry loop in autocomplete init** | **Low** | `autocomplete.js:31` | `setTimeout(init, 500)` with no retry limit if `#editor-container` is not found. |
| B15 | **Settings sync circular write** | **Low** | `settings-sync.js` | When cloud settings are loaded, `setTheme()` dispatches `bayan:themechange`, which triggers `onSettingsChanged()`, which saves the same theme back to cloud — wasteful round-trip. |
| B16 | **Sync queue not cleared on logout** | **Low** | `auth.js:128-156` | `signOut()` does not call `SyncQueue.clear()`. Pending queue entries (containing document content) persist for the next user. |
| B17 | **`_escapeSummaryAttr()` incomplete HTML escaping** | **Medium** | `summaries-ui.js` | Only escapes `"`, not `&`, `<`, `>`. Potential stored XSS vector if summary text contains HTML characters. |
| B18 | **`summaries-ui.js` null crash risk** | **Low** | `summaries-ui.js:87` | `item.summary_text.length` will throw TypeError if `summary_text` is null/undefined. |

### Previously Fixed Bugs

| # | Bug | Status |
|---|-----|--------|
| B-F1 | Score sparkline renders with only 2 data points | ✅ Fixed |
| B-F2 | `dismissAllFiltered()` only removed DOM without updating `window.currentSuggestions` | ✅ Fixed |

---

## 6. Security Issues

| # | Issue | Severity | Location | Details |
|---|-------|----------|----------|---------|
| S1 | **CORS wildcard `origins: "*"`** | **Critical** | `app.py:94` | `CORS(app, resources={r"/api/*": {"origins": "*"}})` allows any origin to call all API endpoints. Enables compute theft, DDoS via free proxy, third-party scraping of NLP capabilities. |
| S2 | **No API authentication on any endpoint** | **Critical** | `app.py`, all `/api/*` routes | No JWT, API key, session check, or rate limiting on any endpoint. Combined with wildcard CORS, any HTTP client can consume compute resources without limits. |
| S3 | **Debug endpoint publicly accessible** | **High** | `app.py:243-277` | `/api/debug-models` requires no authentication. Exposes: model load status, startup error messages, system memory usage (`/proc/meminfo` contents), HF_API_TOKEN existence. |
| S4 | **`trust_remote_code=True` for grammar model** | **High** | `model_loader.py:706` | Grammar model loaded with `trust_remote_code=True`, allowing arbitrary code execution from the HF model repository. All other models correctly use `False`. |
| S5 | **Unsafe pickle deserialization** | **High** | `autocomplete_service.py:100` | `pickle.load(f)` on a file downloaded from HuggingFace Hub. Pickle can execute arbitrary code during deserialization. |
| S6 | **Unsafe torch checkpoint loading** | **High** | `araspell_service.py:72` | `torch.load(model_path, weights_only=False)` disables PyTorch's safe loading, allowing arbitrary code execution via crafted checkpoint files. |
| S7 | **Missing RLS migration files for core tables** | **High** | `supabase/migrations/` | Only `001_profiles.sql` exists. `documents`, `summaries`, `settings` tables have RLS documented but not version-controlled. Cannot verify RLS is enabled in production from codebase. |
| S8 | **XSS risk in document content** | **Medium** | `documents-ui.js:196` | Document content stored as HTML and loaded into the editor. If `loadDocumentText()` uses `innerHTML` without sanitization, stored XSS is possible. `_escapeHtml()` helper exists but is only used for document list rendering, not content loading. |
| S9 | **Document CRUD relies solely on RLS** | **Medium** | `documents-api.js:68-148` | `loadDocument()`, `saveDocument()`, `renameDocument()`, `deleteDocument()` filter only by document `id`, not by `user_id`. If RLS were misconfigured, any authenticated user could access any user's documents. |
| S10 | **HTML injection risk in meta tag injection** | **Medium** | `app.py:189` | `f'<meta name="supabase-url" content="{SUPABASE_URL}">'` — if `SUPABASE_URL` contains `">`, it could break the HTML structure. No HTML escaping applied. |
| S11 | **Telemetry data leaked to clients** | **Medium** | `app.py:~2745` | `_tel_events` list containing internal pipeline diagnostics (filter rejections, grammar diffs, Jaccard scores) is returned in the API response. Exposes internal processing details. |
| S12 | **Extension Trusted Types passthrough** | **Low** | `content-inline.js:32-39` | `trustedTypes.createPolicy()` uses identity transform `(input) => input` — passes CSP enforcement but provides zero sanitization. All callers must ensure safety independently. |
| S13 | **Auth tokens in localStorage (no CSP)** | **Low** | `auth/client.js:27` | Supabase tokens stored in localStorage, vulnerable to XSS. No Content Security Policy configured in Flask to mitigate XSS risks. Standard Supabase pattern, but defense-in-depth gap. |
| S14 | **`DEBUG_TRACE = True` hardcoded** | **Low** | `app.py:90` | Verbose trace logging enabled unconditionally in production. May expose sensitive processing details in log aggregators. |

---

## 7. Performance Issues

| # | Issue | Severity | Location | Details |
|---|-------|----------|----------|---------|
| P1 | **Grammar model is a remote API call** | **High** | `grammar_service.py:97-100` | Every grammar correction requires a round-trip to an external Gradio Space. If the Space sleeps (HF free tier), first request has 10-30s cold start. 3 retries with exponential backoff, but latency is fundamentally unpredictable (3-8s typical). |
| P2 | **Duplicate morphological analysis in grammar rules** | **High** | `grammar_rules.py` | 7 separate grammar rule functions each call `self.mle.disambiguate(tokens)` independently: `fix_number_and_gender_agreement`, `fix_verbs_nasb_and_jazm`, `fix_subject_verb_agreement`, `fix_conditional_sentences`, `fix_demonstrative_agreement`, `fix_noun_adjective_agreement_advanced`, `fix_kana_and_inna`. For a 50-word sentence, this is 7 full morphological analysis passes that could be done once. |
| P3 | **MLM scoring per word in spelling** | **High** | `araspell_rules.py`, ContextualCorrector | `score_with_mlm` runs a full AraBERT forward pass for each OOV word. `refine_sentence_with_mask` calls `score_with_mlm` twice + `predict_masked_token` per OOV word. For a 20-word sentence with 5 OOV words, this is ~15 BERT forward passes. |
| P4 | **Tailwind CDN dev mode in production** | **Medium** | `index.html` | Full Tailwind CSS (~3MB uncompressed) downloaded via CDN development script on every page load. Should use a production build with purged CSS. |
| P5 | **`analyze_text()` is a 1,224-line function** | **Medium** | `app.py:1534-2758` | Contains entire 3-stage pipeline with all guards, filters, and telemetry inline. Cold start loads all imports. `_is_small_spelling_change()` is 513 lines. |
| P6 | **12+ `import re as _re_*` statements inside function body** | **Medium** | `app.py` | 12 separate `import re as _re_spell_guard`, `import re as _re_strip`, `import re as _re_emoji`, etc. inside `analyze_text()`. While Python caches modules, these are called on every request. Should be module-level. |
| P7 | **`getEditorText()` clones entire DOM per keystroke** | **Medium** | `selection.js` | Called on every `input` event via `updateEditorStats()`. `editor.cloneNode(true)` for large documents is expensive. |
| P8 | **Vendor JS loaded synchronously** | **Medium** | `index.html` | mammoth (340KB), docx.js (1.2MB), html2canvas (210KB) all block initial render even if never used. |
| P9 | **`overlaySuggestions` is O(N×M)** | **Medium** | `renderer.js:349` | Rebuilds text node map after EVERY suggestion application, where N = suggestions, M = text nodes. |
| P10 | **No API response caching on website** | **Medium** | `editor.js` | Every keystroke after 1s debounce triggers a full `/api/analyze` call. Extension background worker has LRU cache (20 entries, 5min TTL), but website doesn't cache at all. |
| P11 | **Extension content script injected on ALL sites** | **Medium** | `manifest.json:43-55` | `matches: ["https://*/*", "http://*/*"]` — content script loads on every page, even non-Arabic sites. |
| P12 | **Undo stack stores 50 full innerHTML snapshots** | **Low** | `editor.js` | For large documents with formatting, each snapshot can be 100KB+. 50 snapshots = 5MB+ of memory. |
| P13 | **CSS not minified** | **Low** | `components.css` | Single file at 3,639+ lines (~90KB). No CSS modules, no scoping, no minification. |
| P14 | **Draft auto-save serializes full editor HTML per keystroke** | **Low** | `editor.js` | `localStorage.setItem('bayan_editor_draft', editor.innerHTML)` on every input event. |

---

## 8. UX Problems

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| U1 | **Native `prompt()`/`confirm()` dialogs mixed with custom UI** | **Medium** | `insertLink()` uses `prompt()`, `clearEditor()` uses `confirm()`, `_createNewDocument()`/`_startRename()` use `prompt()`, `setWordGoalUI()` uses `prompt()`. These break visual consistency and cannot be styled. `_confirmDelete()` correctly uses custom `showConfirmDialog`. |
| U2 | **Extension content script tooltip clips at viewport edge** | **Medium** | Tooltip for highlighted errors can overflow off-screen on narrow viewports. No boundary detection or repositioning logic. |
| U3 | **No loading skeleton on initial editor page** | **Medium** | Editor page shows blank white space during model initialization (~60s cold start on HF Spaces). No skeleton/shimmer to indicate loading state. |
| U4 | **Extension popup loses all state on close** | **Medium** | Popup has no state persistence. Clicking away destroys all analysis results. SidePanel correctly persists via `chrome.storage.session`. |
| U5 | **Extension ghost-text autocomplete only works on textarea/input** | **Medium** | Most web editors (Gmail compose, WordPress, Medium, Discourse, Slack) use contenteditable. Ghost text autocomplete is disabled on all of these. |
| U6 | **Inconsistent branding between popup and sidepanel** | **Low** | Popup uses `.bayan-*` class prefix, SidePanel uses `.sp-*`. Different color palettes and CSS variable naming (`--bayan-*` vs `--sp-*`). |
| U7 | **Mobile bottom-sheet for suggestions lacks smooth gestures** | **Low** | Website has responsive breakpoints but the suggestion panel bottom-sheet on mobile has no drag-to-dismiss or smooth gesture handling. |
| U8 | **Summary length slider label never updates** | **Low** | `updateSummaryLength()` is an empty function. Slider works but the label always shows "medium" regardless of position. |
| U9 | **Missing accessibility features** | **Low** | No skip navigation link, no focus trap in Quran modal, no keyboard navigation for suggestion cards (only Enter key), no `aria-live` regions for dynamic score updates. |
| U10 | **Protected sites disable contenteditable analysis entirely** | **Low** | Gmail, Google Docs, Notion, Sheets, Slides — contenteditable is disabled by protection list. Only `<textarea>`/`<input>` elements work on these sites. Expected but not communicated to users. |

---

## 9. Technical Debt

### Backend

| # | Item | Severity | Details |
|---|------|----------|---------|
| TD1 | **`analyze_text()`: 1,224-line function** | **High** | Contains entire 3-stage pipeline with all guards, filters, offset mapping, telemetry, and error handling. Should be decomposed into per-stage functions. |
| TD2 | **`_is_small_spelling_change()`: 513-line function** | **High** | Single function with deeply nested conditionals implementing 20+ safety guards. |
| TD3 | **Dead code: `SpellingModel`/`AutocompleteModel`/`GrammarModel`/`PunctuationModel` classes** | **Medium** | `model_loader.py:385-903`: Imported in `app.py:45-56` but NEVER instantiated. All models loaded through their respective service modules. The globals `spelling_model`, `autocomplete_model`, `grammar_model`, `punctuation_model` (lines 102-106) are always `None`. |
| TD4 | **Dead code: `hf_inference.py`** | **Medium** | All functions are stubs that return input unchanged or empty lists. Imported in `app.py:65` but functions are never called in the pipeline. |
| TD5 | **Two `RulesBasedCorrector` class definitions** | **Medium** | `araspell_rules.py`: First class at line ~38 with `KEYBOARD_NEIGHBORS`, second class at line ~540 with identical `KEYBOARD_NEIGHBORS`. Second class overwrites the first. |
| TD6 | **Question mark cue words defined 5 times** | **Medium** | `_EXCL_CUES = {'هل', 'أين', ...}` defined at 5 separate locations in `punctuation_service.py` and `punctuation_rules.py`. |
| TD7 | **12+ `import re` aliased inside function body** | **Medium** | `import re as _re_spell_guard`, `import re as _re_strip`, `import re as _re_emoji`, etc. — 12 aliased re imports inside `analyze_text()` instead of one module-level import. |
| TD8 | **`Grammrar` typo in path** | **Low** | `model_loader.py:36`: `GRAMMAR_PATH = MODEL_BASE_PATH / "Grammrar" / "Model"` — misspelled directory name. Works only because the actual directory has the same typo. |
| TD9 | **`ENABLE_*_MODEL` flags never checked** | **Low** | `app.py:59-63`: `ENABLE_DIALECT_MODEL`, `ENABLE_PUNCTUATION_MODEL`, etc. declared but never referenced. Features use lazy-loading regardless. |
| TD10 | **12+ test files at project root** | **Low** | `test_camel.py`, `test_colon.py`, `test_grammar_fast.py`, `test_mapper.py`, `debug_pc002.py`, etc. scattered in root instead of `tests/`. |
| TD11 | **`import json as _tel_json` and `import re as _re_struct` inside function** | **Low** | `app.py:2209, 2186`: Imports inside `analyze_text()` function body instead of module level. |

### Frontend (Website)

| # | Item | Severity | Details |
|---|------|----------|---------|
| TD12 | **`src/js/api.js` is dead code** | **Medium** | Uses ES6 `export` syntax but loaded via `<script>` tag (not `type="module"`). Exports are never imported. Website uses inline `fetch()` calls in `editor.js`. |
| TD13 | **`applySuggestionAtOffsets` and `applyAlternativeCorrection` ~90% identical** | **Medium** | `editor.js`: Nearly identical DOM manipulation, filtering, and count-updating code. Should be a single function with a correction text parameter. |
| TD14 | **`_sendFeedback()` defined but never called** | **Low** | `editor.js`: Feedback function exists but no UI element invokes it. |
| TD15 | **`renderer.js` `createSegments()` first pass unused** | **Low** | Lines 42-93: Event timeline with `events`/`activeSuggestions` produces `segments` that are never used. Only `finalSegments` from the second pass (lines 96-131) is returned. |
| TD16 | **33 script tags with implicit load-order dependency** | **Medium** | No module system, no dependency declaration. Mixed patterns: `api.js` uses ES6 `export`, `renderer.js`/`selection.js` use CommonJS guards, everything else is plain globals. |
| TD17 | **~1,124 lines of inline JavaScript in `index.html`** | **Medium** | Page navigation, tab switching, Quran/dialect/summarization logic, Element SDK integration, DOMContentLoaded init — all inline instead of in separate files. |
| TD18 | **CSS duplication and inconsistency** | **Low** | Multiple duplicate declarations in `components.css`: `.skeleton`, `input[type="range"]`, `.empty-state`, `.editor-stats`, `.footer-bar`, `.card-hover:hover`, `@keyframes fadeIn`. Legacy `--primary-color` coexists with canonical `--color-primary`. Undefined variables `--font-size-sm` and `--font-size-base` referenced. |
| TD19 | **No build system** | **Low** | No bundler, no tree-shaking, no code-splitting. All JS loaded via `<script>` tags. No asset hashing for cache busting. |

### Extension

| # | Item | Severity | Details |
|---|------|----------|---------|
| TD20 | **60-70% code duplication between `popup.js` and `sidepanel.js`** | **High** | `updateCounts()`, `showToast()`, `setLoading()`, `downloadTxt()`, tab switching, `renderSuggestions()`, summarize/dialect/quran/autocomplete handlers — all nearly identical in both files. Any bug fix must be applied in both places. |
| TD21 | **Dead code: `content.js`** | **Low** | 12-line stub file, not loaded by manifest. |
| TD22 | **Dead code: `bayan-state.js`** | **Low** | 127-line WeakRef-based field tracking module, not loaded by manifest or any HTML file. Content script uses local variables instead. |
| TD23 | **Dual API paths: background.js vs direct fetch** | **Medium** | Content script inline analysis goes through `background.js` (with caching, retry, timeout). Popup/SidePanel call `bayan-api.js` directly via `fetch()` (no caching, no retry, no timeout). Ghost-text autocomplete in content script also calls `fetch()` directly, bypassing background. |
| TD24 | **No timeouts on popup/sidepanel API calls** | **Medium** | `bayan-api.js` functions accept an optional `AbortSignal` but no caller passes one. If the API hangs, the loading overlay blocks indefinitely. |
| TD25 | **CSS variable duplication** | **Low** | Popup uses `--bayan-*` variables, sidepanel uses `--sp-*` variables, both defining the same color values. |

---

## 10. Recommended Roadmap

### Phase 1: Security Hardening (Critical — Before Any Growth)

**Timeline: 1-2 days** | **Priority: CRITICAL**

| # | Task | Effort |
|---|------|--------|
| 1 | **Restrict CORS** — Change `origins: "*"` to allowlist `["https://bayan10-bayan-api.hf.space", "chrome-extension://<ext-id>"]` | 30 min |
| 2 | **Add rate limiting** — Flask-Limiter: 30 req/min/IP for `/api/analyze`, 10/min for others | 1 hour |
| 3 | **Disable debug endpoint** — Guard `/api/debug-models` behind `app.debug` flag or remove | 15 min |
| 4 | **Fix `trust_remote_code`** — Change to `False` at `model_loader.py:706` | 5 min |
| 5 | **Add `MAX_TEXT_LENGTH` check to `/api/punctuation`** and `/api/analyze` | 15 min |
| 6 | **Bound `/api/autocomplete` `n` parameter** — Cap at `n=10` | 5 min |
| 7 | **Set `DEBUG_TRACE = False`** in production, or gate behind env var | 5 min |
| 8 | **Stop leaking telemetry** — Remove `_tel_events` from API response (or gate behind debug flag) | 15 min |
| 9 | **Escape HTML in meta tag injection** — Use `html.escape()` for Supabase URL/key injection | 10 min |
| 10 | **Clear sync queue on logout** — Add `SyncQueue.clear()` to `signOut()` | 10 min |

### Phase 2: Database & Migration Integrity (High)

**Timeline: 1-2 days** | **Priority: HIGH**

| # | Task | Effort |
|---|------|--------|
| 1 | **Create `002_documents.sql`** with proper schema + RLS policies | 2 hours |
| 2 | **Create `003_summaries.sql`** and `004_settings.sql` with RLS | 1 hour |
| 3 | **Add `user_id` filter to single-document operations** — defense-in-depth alongside RLS | 30 min |
| 4 | **Add soft-delete to documents** — `deleted_at` column instead of hard delete | 1 hour |

### Phase 3: Extension Auth Unification (High)

**Timeline: 3-5 days** | **Priority: HIGH**

| # | Task | Effort |
|---|------|--------|
| 1 | **Add Supabase client to extension** — UMD bundle in `shared/` | 1 day |
| 2 | **Implement auth flow** — `chrome.identity.launchWebAuthFlow()` for Google OAuth | 1 day |
| 3 | **Session persistence** — Store refresh token in `chrome.storage.local` | 4 hours |
| 4 | **Enable cloud documents in extension** — Wire up existing SidePanel document UI | 1 day |
| 5 | **Sync dismissed words** — Persist to `chrome.storage.local` and optionally to cloud | 2 hours |

### Phase 4: Backend Refactoring (High)

**Timeline: 5-7 days** | **Priority: HIGH**

| # | Task | Effort |
|---|------|--------|
| 1 | **Decompose `analyze_text()`** into `spelling_stage()`, `grammar_stage()`, `punctuation_stage()` | 2 days |
| 2 | **Cache morphological analysis** — Run `mle.disambiguate()` once, pass result to all 7 grammar rules | 4 hours |
| 3 | **Move 12+ `import re` to module level** — Single `import re` at top of file | 30 min |
| 4 | **Delete dead code** — `hf_inference.py` stubs, unused `model_loader.py` classes, `ENABLE_*` flags | 1 hour |
| 5 | **Split `app.py`** into `routes/`, `services/`, `middleware/` | 2 days |
| 6 | **Move root-level test files** into `tests/` | 30 min |

### Phase 5: Extension Code Quality (Medium)

**Timeline: 3-4 days** | **Priority: MEDIUM**

| # | Task | Effort |
|---|------|--------|
| 1 | **Extract shared logic** from `popup.js` and `sidepanel.js` into `shared/bayan-core.js` | 1.5 days |
| 2 | **Unify API path** — Route popup/sidepanel API calls through background.js for consistent caching/retry/timeout | 1 day |
| 3 | **Delete dead files** — `content.js`, `bayan-state.js` | 15 min |
| 4 | **Add AbortController timeouts** to `bayan-api.js` functions (60s default) | 2 hours |
| 5 | **Add English locale** — `_locales/en/messages.json` | 2 hours |

### Phase 6: Frontend Fixes & Polish (Medium)

**Timeline: 3-4 days** | **Priority: MEDIUM**

| # | Task | Effort |
|---|------|--------|
| 1 | **Fix `_isApplyingSuggestion` race condition** — Increase guard timeout from 400ms to 600ms, or use a completion callback instead of timer | 30 min |
| 2 | **Fix `restoreSelection` for range selections** — Add range to selection after creation | 30 min |
| 3 | **Fix undo stack** — Strip suggestion overlay spans before saving innerHTML snapshot | 1 hour |
| 4 | **Replace native `prompt()`/`confirm()` with custom dialogs** | 4 hours |
| 5 | **Fix color picker reset** — Only remove color/highlight, not all formatting | 30 min |
| 6 | **Switch Tailwind to production build** — Purge unused CSS, save ~3MB per page load | 2 hours |
| 7 | **Lazy-load vendor libs** — mammoth, docx, html2canvas on first use | 2 hours |
| 8 | **Delete dead `api.js`** and unused `createSegments()` first pass | 30 min |

### Phase 7: Performance Optimization (Low)

**Timeline: 2-3 days** | **Priority: LOW**

| # | Task | Effort |
|---|------|--------|
| 1 | **Add website-side API caching** — localStorage TTL cache like extension background worker | 4 hours |
| 2 | **Optimize `getEditorText()`** — Extract text without full DOM clone | 2 hours |
| 3 | **Fix `overlaySuggestions` O(N×M)** — Build text node map once, update incrementally | 4 hours |
| 4 | **Add CSS/JS minification** to Docker build | 2 hours |
| 5 | **Add loading skeletons** for editor page cold start | 2 hours |
| 6 | **Add `content_security_policy`** to extension manifest | 30 min |

---

## Summary Matrix

| Category | Critical | High | Medium | Low | Total |
|----------|---------|------|--------|-----|-------|
| **Missing Features** | 3 (C1-C3) | 5 (H1-H5) | 6 (M1-M6) | 5 (L1-L5) | **19** |
| **Bugs** | 0 | 2 (B1-B2) | 8 (B3-B8, B13, B17) | 6 (B9-B12, B14-B16, B18) | **18** |
| **Security** | 2 (S1-S2) | 4 (S3-S6, S7) | 4 (S8-S11) | 3 (S12-S14) | **14** |
| **Performance** | 0 | 3 (P1-P3) | 7 (P4-P10, P11) | 3 (P12-P14) | **14** |
| **UX** | 0 | 0 | 5 (U1-U5) | 5 (U6-U10) | **10** |
| **Tech Debt** | 0 | 3 (TD1-TD2, TD20) | 10 | 12 | **25** |
| **TOTAL** | **5** | **17** | **40** | **34** | **100** |

---

## Final Verdict

Bayan is a technically impressive Arabic NLP platform with a well-designed multi-stage correction pipeline (Spelling → Grammar → Punctuation), sophisticated offset mapping via PipelineContext/OffsetMapper/StageLocker, a mature contenteditable editor engine, and a Chrome extension that correctly follows Manifest V3 best practices.

### What Bayan Does Well

- **NLP Pipeline Architecture**: PipelineContext + PatchSet + StageLocker provide deterministic multi-stage coordination with overlap resolution and hierarchical locking. 20+ safety guards prevent hallucinations.
- **Editor Engine**: Custom contenteditable with character-offset-based selection save/restore, reverse-order suggestion processing to avoid offset invalidation, and overlay-only rendering that never modifies user DOM.
- **Extension Design**: Minimal permissions, proper HTML escaping throughout, thoughtful protected-site handling, LRU cache with collision-safe hashing, overlay-only rendering on 3rd-party sites.
- **Auth Architecture**: Clean layered design (config → client → session → auth → UI) with PKCE flow, guest-to-Google upgrade path, `window.__bayanAuth` facade for decoupled downstream consumption, and graceful offline degradation.
- **Sync System**: Offline-first with persistent localStorage queue, debounced flush, mutex-guarded sync, and automatic reconnection.
- **Benchmark Coverage**: 320 tests across 8 datasets (spelling, grammar, punctuation, entities, religious, structured, hallucination, collision) at 94.37% pass rate.

### What Must Be Fixed Before Growth

1. **Security** (5 critical/high items): Wildcard CORS + zero rate limiting + zero API auth = anyone can abuse compute. Debug endpoint leaks internals. `trust_remote_code=True` and `weights_only=False` allow arbitrary code execution from model repos.
2. **Extension Auth Gap**: Extension users cannot access cloud documents, settings, or history — breaks the SaaS value proposition entirely.
3. **Database Integrity**: No migration files for 3 of 4 core tables. RLS policies documented but unverifiable from codebase.
4. **Performance Bottleneck**: Grammar stage does 7 redundant morphological analysis passes. Spelling stage runs O(N) BERT forward passes for MLM scoring. Grammar depends on an external Gradio Space with unpredictable latency.
5. **Code Architecture**: `analyze_text()` at 1,224 lines and `_is_small_spelling_change()` at 513 lines are unmaintainable. 60-70% popup/sidepanel duplication means every bug fix must be applied twice.

### Bottom Line

Bayan is **80% of the way to a production-grade SaaS product**. The NLP pipeline, editor engine, and extension architecture are solid foundations. The remaining 20% is:

- **Week 1**: Security hardening (CORS, rate limiting, debug endpoint, model loading) + database migrations with RLS
- **Week 2**: Extension authentication + cloud document access
- **Week 3**: Backend decomposition + grammar performance optimization + extension code deduplication

Total estimated effort: **3-4 focused weeks** to reach production readiness.
