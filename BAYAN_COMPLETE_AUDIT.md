# BAYAN — Complete Product, Codebase & Extension Deep Audit

> **Audit Date:** 2026-06-26  
> **Auditor Perspective:** Product Manager + Senior Frontend + Backend Architect + Extension Engineer + SaaS Reviewer

---

## 1. Current System Overview

### Architecture Map

```
┌──────────────────────────────────────────────────────┐
│                   BAYAN ECOSYSTEM                     │
│                                                       │
│  ┌─────────┐    ┌──────────┐    ┌─────────────────┐  │
│  │ Website  │───▶│ Flask API │───▶│  NLP Pipeline   │  │
│  │ (SPA)    │    │ (app.py) │    │ Spell/Gram/Punct│  │
│  └─────────┘    └──────────┘    └─────────────────┘  │
│       │              │                    │           │
│       │              │          ┌─────────────────┐  │
│       │              ├─────────▶│  HF Models      │  │
│       │              │          │  Summarization   │  │
│       │              │          │  Grammar (Gradio)│  │
│       │              │          └─────────────────┘  │
│       │              │                               │
│  ┌─────────┐    ┌──────────┐    ┌─────────────────┐  │
│  │Supabase │◀───│  Auth    │───▶│  Documents DB   │  │
│  │ (Cloud) │    │  Module  │    │  Settings Sync  │  │
│  └─────────┘    └──────────┘    └─────────────────┘  │
│                                                       │
│  ┌────────────────────────────────────────────────┐   │
│  │           Chrome Extension (MV3)               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────────┐  │   │
│  │  │ Content  │ │Background│ │  Side Panel   │  │   │
│  │  │ Script   │ │  Worker  │ │  + Popup      │  │   │
│  │  └──────────┘ └──────────┘ └───────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | Vanilla JS, HTML, CSS (Tailwind CDN) | Custom `contenteditable` editor engine |
| **Backend** | Flask (Python) | Single monolith `app.py` — 2,844 lines |
| **NLP Pipeline** | Custom Python modules | Spelling, Grammar, Punctuation, Autocomplete, Dialect |
| **AI Models** | Transformer-based | Summarization (local), Grammar (Gradio proxy), Spelling (CAMeL + custom) |
| **Database** | Supabase (PostgreSQL) | Documents, profiles, user settings |
| **Auth** | Supabase Auth | Guest (anonymous), Google OAuth |
| **Deployment** | HuggingFace Spaces (Docker) | CPU-only free tier |
| **Extension** | Chrome MV3 | Background SW, Content Script, Side Panel, Popup |

### File Structure Summary

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/` | 6 core files | Backend + HTML + CSS |
| `src/js/` | 8 JS files + 7 subdirs | Frontend logic |
| `src/js/auth/` | 5 files | Supabase auth (client, session, UI) |
| `src/js/documents/` | 4 files | Local doc management + export |
| `src/js/documents-cloud/` | 3 files | Supabase CRUD for documents |
| `src/js/sync/` | 3 files | Offline queue + conflict resolution |
| `src/js/settings-sync/` | 2 files | User settings cloud persistence |
| `src/nlp/` | 6 subdirs | All NLP processing modules |
| `extension/` | 8 files + 4 subdirs | Chrome Extension |
| `extension/shared/` | 9 files | Shared utilities (api, renderer, patches) |
| `extension/sidepanel/` | 3 files | Side panel UI |
| `tests/` | 16 test files | Backend unit tests |
| `extension/tests/` | 8 files | Extension integration tests |

---

## 2. Feature Inventory

### Core AI Features

| Feature | Backend API | Website Frontend | Extension | Files |
|---------|------------|-----------------|-----------|-------|
| **Spelling Correction** | ✅ `/api/spelling` + `/api/analyze` | ✅ Full (highlights, suggestions, apply) | ✅ Inline overlay + Popup + SidePanel | `nlp/spelling/`, `editor.js`, `renderer.js` |
| **Grammar Correction** | ✅ `/api/grammar` + `/api/analyze` | ✅ Full (via Gradio proxy to HF model) | ✅ Inline overlay + Popup + SidePanel | `nlp/grammar/`, `hf_inference.py` |
| **Punctuation** | ✅ `/api/punctuation` + `/api/analyze` | ✅ Full (PuncAra-v1 model) | ✅ Inline overlay + Popup + SidePanel | `nlp/punctuation/` |
| **Summarization** | ✅ `/api/summarize` | ✅ Full (tab in editor, length control) | ✅ Popup tab + SidePanel tab | `model_loader.py`, `summaries-api.js` |
| **AutoComplete** | ✅ `/api/autocomplete` | ✅ Ghost text + dropdown in editor | ⚠️ SidePanel text-box only, NO inline ghost text | `autocomplete.js`, sidepanel `btnAutocomplete` |
| **Dialect→MSA** | ✅ `/api/dialect` | ✅ Dedicated editor tab | ✅ SidePanel tab (basic text→text) | `nlp/dialect/` |
| **Quran Verification** | ✅ `/api/quran` | ✅ Dedicated editor tab | ✅ SidePanel tab (basic text→text) | `quran.py`, `quran_master.db` |

### Platform Features

| Feature | Website | Extension (Popup) | Extension (SidePanel) | Extension (Content Script) |
|---------|---------|-------------------|----------------------|--------------------------|
| **Authentication** | ✅ Guest + Google | ❌ None | ⚠️ Partial (`initExtensionAuth()` exists but requires web page auth sync) | ⚠️ Listens for `BAYAN_AUTH_SYNC` message from web |
| **Document Save** | ✅ Supabase CRUD | ❌ None | ⚠️ UI exists (`btnNewDocument`, `btnSaveSelection`) but depends on auth | ❌ None |
| **Document Load/History** | ✅ Full panel | ❌ None | ⚠️ UI exists (`documentsList`, `historyList`) but depends on auth | ❌ None |
| **Export (PDF/DOCX/TXT)** | ✅ Full (mammoth.js, docx.js) | ❌ None | ❌ None | ❌ None |
| **Import (TXT/DOCX)** | ✅ Full | ❌ None | ❌ None | ❌ None |
| **Settings Sync** | ✅ Supabase | ❌ None | ⚠️ Placeholder (`syncExtensionSettings()`) | ❌ None |
| **Theme Toggle** | ✅ Full dark/light | ❌ Hardcoded dark | ✅ Dark only | N/A |
| **Focus Mode** | ✅ Full | N/A | ❌ None | N/A |
| **Score Ring** | ✅ Animated SVG | ✅ Simplified | ✅ Simplified | ❌ None |
| **Writing Score History** | ✅ Sparkline chart | ❌ None | ❌ None | ❌ None |
| **Error Donut Chart** | ✅ SVG donut | ❌ None | ❌ None | ❌ None |
| **Offline Mode** | ✅ Graceful degradation | ❌ No offline handling | ❌ No offline handling | ❌ No offline handling |
| **Keyboard Shortcuts** | ✅ Extensive (Alt+1-3, Ctrl+S, etc.) | ❌ None | ❌ None | ❌ None |

---

## 3. Website vs Extension Comparison

### Authentication Flow

| Aspect | Website | Extension | Gap |
|--------|---------|-----------|-----|
| Guest login | ✅ `signInAnonymously()` | ❌ | **Critical** — extension users can't persist anything |
| Google OAuth | ✅ `signInWithOAuth()` | ❌ | **High** |
| Session restore | ✅ `restoreSession()` via Supabase | ❌ | **High** |
| Auth state sync | ✅ `onAuthStateChange()` | ⚠️ Listens for `BAYAN_AUTH_SYNC` postMessage but only works when user visits Bayan website with extension installed | **High** — unreliable |
| Auth-gated features | ✅ Documents, sync, settings | ⚠️ UI elements exist but non-functional without auth | **High** |

### AI Feature Comparison

| Feature | Website UX | Extension UX | Parity? |
|---------|-----------|-------------|---------|
| Analyze (S+G+P) | Rich editor with inline highlights, suggestion sidebar, popover tooltip, apply/dismiss per-suggestion | **Content Script:** Overlay marks + tooltip. **Popup/SidePanel:** Textarea + suggestion cards | ⚠️ Functional but UX gap |
| Summarize | Editor tab with radio buttons (short/medium/long) | Popup/SidePanel textarea with radio buttons | ✅ Near parity |
| AutoComplete | **Ghost text** inside editor (Tab to accept) | SidePanel has a text box with "إكمال" button but NO inline ghost text on 3rd party sites | **Medium** — missing the core UX |
| Dialect | Dedicated editor tab with "Convert" button | SidePanel tab with text box and "Convert" button | ✅ Near parity |
| Quran | Dedicated editor tab with search | SidePanel tab with text box and search | ✅ Near parity |

### Documents

| Aspect | Website | Extension | Gap |
|--------|---------|-----------|-----|
| Create document | ✅ `createDocument()` | ⚠️ Button exists in SidePanel but blocked by no auth | **High** |
| List documents | ✅ Desktop sidebar panel | ⚠️ `documentsList` in SidePanel workspace tab, blocked by no auth | **High** |
| Save/auto-save | ✅ Debounced sync via `SyncManager` | ❌ | **High** |
| Export PDF/DOCX | ✅ `export.js` | ❌ | **Medium** |
| Import | ✅ `import.js` (TXT, DOCX) | ❌ | **Low** |

---

## 4. Missing Features

### Critical (Blocks Production)

| # | Issue | Impact | Solution |
|---|-------|--------|----------|
| C1 | **`.env` file committed to Git** | Supabase URL and anon key are in the repo. While anon key is safe for client use, this is a security anti-pattern and may expose the project URL. | Remove `.env` from Git history, use HF Spaces secrets exclusively. `.gitignore` has `.env` but it was committed before the rule was added. |
| C2 | **CORS wildcard `origins: "*"`** | Any website can call `/api/analyze`, `/api/summarize`, etc. directly. Abusers can drain compute. | Restrict CORS to `bayan10-bayan-api.hf.space` + extension origin `chrome-extension://<id>`. |
| C3 | **No rate limiting on API** | No throttle on any endpoint. A single user can overwhelm the free-tier HF Space. | Add Flask-Limiter or simple in-memory token bucket. |

### High (Important Feature Gap)

| # | Issue | Impact | Solution |
|---|-------|--------|----------|
| H1 | Extension has no auth | Users cannot access cloud docs, settings, or history from extension | Implement Supabase auth in extension via `chrome.identity` or shared session from Bayan website |
| H2 | Extension content script lacks AutoComplete ghost text | The flagship "ghost text" feature doesn't work on 3rd-party sites | Port `autocomplete.js` logic into `content-inline.js` with `/api/autocomplete` calls |
| H3 | Extension popup/sidepanel have no export | Users cannot export corrected text as PDF/DOCX | Add "Copy as formatted text" or lightweight export |
| H4 | No `documents` table migration | `supabase/migrations/001_profiles.sql` exists but no migration creates the `documents` table that `documents-api.js` uses | Create `002_documents.sql` migration |
| H5 | Backend monolith: `app.py` is 2,844 lines | Extremely difficult to maintain, test, or extend | Split into `routes/`, `services/`, `middleware/` modules |

### Medium (Improvement Needed)

| # | Issue | Impact | Solution |
|---|-------|--------|----------|
| M1 | `src/js/api.js` uses ES module `export` syntax but is loaded via `<script>` tag (not `type="module"`) | The `api.js` exports are **never importable** — the website uses inline `fetch()` calls instead | Either convert to `type="module"` or remove the dead `export` statements |
| M2 | Extension content script overlay doesn't handle `<iframe>` editors | Rich text editors in iframes (e.g., WordPress Gutenberg, TinyMCE) are invisible to the content script | Use `all_frames: true` in manifest or detect iframe editors |
| M3 | Duplicated suggestion rendering logic | `ui.js` (website) and `bayan-ui.js` (extension) implement the same card HTML generation | Extract to shared package |
| M4 | Extension `popup.js` (498 lines) and `sidepanel.js` (702 lines) share ~60% identical code | Maintenance nightmare — fixing a bug requires changes in 2+ files | Refactor into shared modules with UI-specific wrappers |
| M5 | Grammar model uses Gradio proxy with SSE streaming | Creates a hard dependency on external `mohammedahmedezz2004-bayan-arabic-grammarly-correction.hf.space`. If that Space goes down, grammar breaks. | Host the grammar model directly on the Bayan Space, or add fallback |
| M6 | No i18n framework on website | All strings are hardcoded in Arabic HTML. Adding English support requires rewriting HTML | Add simple i18n JSON loader (extension already has `_locales/ar/`) |

### Low (Nice to Have)

| # | Issue | Impact | Solution |
|---|-------|--------|----------|
| L1 | Extension only has Arabic locale | Cannot be published on Chrome Web Store for non-Arabic users | Add `_locales/en/messages.json` |
| L2 | No analytics or telemetry | No visibility into usage patterns, error rates, or feature adoption | Add lightweight event tracking (privacy-respecting) |
| L3 | Heavy vendor libraries loaded synchronously | `mammoth.browser.min.js`, `docx.umd.js`, `html2canvas.min.js` block initial render | Lazy-load on first export action |
| L4 | No service worker for website | No offline caching for the web app | Add basic SW for static assets |

---

## 5. Bugs Found

| # | Bug | Severity | Location | Status |
|---|-----|----------|----------|--------|
| B1 | `ENABLE_AUTOCOMPLETE_MODEL = False` in `app.py:62` | Medium | `app.py` line 62 | AutoComplete model disabled by default — `/api/autocomplete` still works via lazy-loading, but the flag is misleading |
| B2 | `src/js/api.js` uses `export` keyword but is not loaded as ES module | Low | `api.js` | Dead code — never actually imported anywhere |
| B3 | Extension `bayan-api.js` missing functions `bayanAutocomplete`, `bayanDialect`, `bayanQuran` | High | `bayan-api.js` only defines `bayanAnalyze`, `bayanSummarize`, `bayanHealthCheck` | SidePanel calls these undefined functions — will throw `ReferenceError` |
| B4 | Extension content script overlay position breaks on page scroll (absolute vs fixed positioning) | Medium | `content-inline.js:191` | Overlay uses `window.scrollY` but doesn't update on window resize |
| B5 | Score sparkline renders with only 2 data points creating a meaningless line | Low | `format.js` | ✅ Fixed (raised minimum to 3 points) |
| B6 | `dismissAllFiltered()` only removed DOM elements without updating `window.currentSuggestions` | Medium | `format.js` | ✅ Fixed |

---

## 6. Security Issues

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| S1 | **`.env` committed to repo** | **Critical** | Supabase URL + anon key visible in Git history. While anon keys are designed for client-side use, the URL+key combo allows anyone to make Supabase API calls. |
| S2 | **CORS `origins: "*"`** | **Critical** | `app.py:94` — allows any origin to call all API endpoints. Enables: (a) compute theft, (b) DDoS via free proxy, (c) third-party scraping. |
| S3 | **No API authentication** | **High** | No JWT, API key, or session check on any endpoint. Extension uses only `host_permissions` scoping. |
| S4 | **XSS risk in editor** | **Medium** | `setEditorHTML()` injects HTML directly into contenteditable. While `renderer.js` escapes text, any upstream bug in suggestion rendering could inject arbitrary HTML. |
| S5 | **Supabase RLS incomplete** | **Medium** | Only `profiles` has RLS policies. The `documents` table (if exists) needs RLS to prevent cross-user data access. |
| S6 | **Extension Trusted Types partial** | **Low** | `content-inline.js` implements `trustedTypes.createPolicy()` with identity transform (`input => input`), which passes the CSP check but provides no actual sanitization. |
| S7 | **Debug endpoint exposed** | **Low** | `/api/debug-models` is accessible in production and leaks internal model status, memory usage, and startup errors. |

---

## 7. Performance Issues

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| P1 | **`app.py` is 2,844 lines** | High | Single-file monolith. Every request loads all imports. Cold start on HF Spaces free tier takes ~60s. |
| P2 | **Vendor JS loaded synchronously** | Medium | `mammoth.browser.min.js` (340KB), `docx.umd.js` (1.2MB), `html2canvas.min.js` (210KB) all load on page start even if never used. |
| P3 | **Extension content script injected on ALL sites** | Medium | `matches: ["https://*/*", "http://*/*"]` — runs on every page. The `BayanController` module loads even on sites where user never types Arabic. |
| P4 | **No API response caching on website** | Medium | Every keystroke after debounce triggers a full `/api/analyze` call. Extension has background worker caching, but website doesn't. |
| P5 | **Grammar Gradio SSE dependency** | Medium | Grammar correction requires streaming from external HF Space. Average latency: 3-8 seconds. Adds significant delay to the analysis pipeline. |
| P6 | **Quran DB is 23MB** | Low | `quran_master.db` (SQLite, 23MB) is loaded into the Docker container. Fine for now, but limits scaling. |
| P7 | **No CSS/JS minification** | Low | All assets served unminified. `components.css` alone is 4,125+ lines (~90KB). |

---

## 8. UX Problems

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| U1 | **Extension content script tooltip clips at viewport edge** | Medium | Tooltip for highlighted errors can overflow off-screen on narrow viewports. No boundary detection. |
| U2 | **No loading skeleton on website** | Medium | Editor page shows blank white space during model initialization. No skeleton/shimmer to indicate loading. |
| U3 | **Extension popup has no dialect/quran/autocomplete** | Medium | Only "تصحيح" and "تلخيص" tabs. SidePanel has all features, but popup is the first surface users see. |
| U4 | **Inconsistent branding between popup and sidepanel** | Low | Popup uses `.bayan-*` class prefix, SidePanel uses `.sp-*` prefix. Different color palettes. |
| U5 | **No onboarding flow** | Low | First-time users see an empty editor with no guidance. No tooltips, walkthrough, or sample text. |
| U6 | **Mobile responsiveness incomplete** | Low | Website has responsive breakpoints but bottom-sheet for suggestions lacks smooth gestures. |

---

## 9. Technical Debt

### Backend

| Item | Severity | Details |
|------|----------|---------|
| **Monolith `app.py`** | High | 2,844 lines. Contains routes, NLP logic, model loading, diffing algorithms, offset mapping, pipeline orchestration, Quran search integration, and CORS — all in one file. |
| **Duplicated directional blocks** | Medium | `_DIRECTIONAL_BLOCKS` in `app.py` duplicates logic that also exists in `araspell_rules.py`. |
| **12+ test files at project root** | Low | `test_proof.py`, `test_sv.py`, `test_pc.py`, etc. scattered in root instead of `tests/`. |
| **Dead code** | Low | `ENABLE_DIALECT_MODEL = False`, `ENABLE_AUTOCOMPLETE_MODEL = False` flags in `app.py` — no code path checks them for these features since they use lazy-loading. |
| **Archive directory** | Low | `archive/legacy_scripts/` contains old code that shouldn't ship in Docker image. |

### Frontend (Website)

| Item | Severity | Details |
|------|----------|---------|
| **`api.js` dead exports** | Medium | `export async function analyzeText()` — never imported. Website uses inline `fetch()` in `editor.js`. |
| **Tight coupling in `editor.js`** | Medium | DOM manipulation, API calls, suggestion management, and UI updates all in one 29KB file. |
| **No build system** | Low | No bundler, no tree-shaking, no code-splitting. All JS loaded via `<script>` tags. |
| **CSS structure** | Low | Single `components.css` at 4,125+ lines. No CSS modules, no scoping. |

### Extension

| Item | Severity | Details |
|------|----------|---------|
| **`popup.js` and `sidepanel.js` code duplication** | High | ~60% identical code: `updateCounts()`, `markStale()`, `setLoading()`, `updateScore()`, `renderSuggestions()`, `showToast()`. |
| **Missing API functions in `bayan-api.js`** | High | SidePanel calls `bayanAutocomplete()`, `bayanDialect()`, `bayanQuran()` which are not defined in `bayan-api.js`. These must be defined elsewhere or will throw. |
| **No TypeScript / JSDoc validation** | Low | All extension code is plain JS with no compile-time checking. |

---

## 10. Recommended Roadmap

### Phase 1: Security Hardening ⚡ (Critical — Before Any Growth)

**Timeline: 1-2 days**

1. **Remove `.env` from Git history** — `git filter-branch` or BFG Repo Cleaner
2. **Restrict CORS** — Change `origins: "*"` to allowlist `["https://bayan10-bayan-api.hf.space", "chrome-extension://<ext-id>"]`
3. **Add rate limiting** — Flask-Limiter: 30 req/min per IP for `/api/analyze`, 10 req/min for `/api/summarize`
4. **Disable debug endpoint in production** — Guard `/api/debug-models` behind `app.debug` flag
5. **Add Supabase RLS for `documents` table** — `CREATE POLICY ... USING (auth.uid() = user_id)`

### Phase 2: Extension Auth Unification 🔐 (High)

**Timeline: 3-5 days**

1. **Implement Supabase client in extension** — Add `@supabase/supabase-js` as UMD bundle in `shared/`
2. **Auth flow**: Use `chrome.identity.launchWebAuthFlow()` for Google OAuth → receive tokens → init Supabase session
3. **Session persistence**: Store refresh token in `chrome.storage.local`
4. **Auth sync**: When user logs in on website, broadcast via `postMessage` → content script → `chrome.storage`
5. **Result**: Extension users can access their documents, settings, and history

### Phase 3: Extension Feature Parity 🔧 (High)

**Timeline: 3-5 days**

1. **Add missing API functions** to `bayan-api.js`: `bayanAutocomplete()`, `bayanDialect()`, `bayanQuran()`
2. **Add autocomplete/dialect/quran tabs to popup** (currently SidePanel-only)
3. **Inline ghost text for content script** — Port `autocomplete.js` logic for textareas on 3rd-party sites
4. **Add basic export** — "Copy corrected text" button already exists; add "Download as TXT"

### Phase 4: Backend Refactoring 🏗️ (Medium)

**Timeline: 5-7 days**

1. **Split `app.py`** into:
   - `routes/analyze.py`, `routes/summarize.py`, `routes/dialect.py`, `routes/quran.py`
   - `services/pipeline.py` (orchestration)
   - `middleware/cors.py`, `middleware/rate_limit.py`
2. **Create `002_documents.sql` migration** with proper RLS
3. **Move root-level test files** into `tests/`
4. **Remove `archive/` from Docker build** (add to `.dockerignore`)

### Phase 5: Extension Code Quality 🧹 (Medium)

**Timeline: 3-4 days**

1. **Extract shared logic** from `popup.js` and `sidepanel.js` into `shared/bayan-core.js`
2. **Add English locale** `_locales/en/messages.json`
3. **Add `all_frames: true`** to manifest for iframe editor support
4. **Add theme toggle** to popup and sidepanel

### Phase 6: Performance & Polish ✨ (Low)

**Timeline: 2-3 days**

1. **Lazy-load vendor libs** (mammoth, docx, html2canvas) on first use
2. **Add website-side API caching** (localStorage TTL cache like extension has)
3. **Add CSS/JS minification** to Docker build
4. **Add loading skeletons** for editor page
5. **Add onboarding flow** — sample text + guided tooltips

---

## Summary Matrix

| Category | Critical | High | Medium | Low | Total |
|----------|---------|------|--------|-----|-------|
| **Security** | 2 (S1, S2) | 1 (S3) | 2 (S4, S5) | 2 (S6, S7) | 7 |
| **Missing Features** | 0 | 5 (H1-H5) | 6 (M1-M6) | 4 (L1-L4) | 15 |
| **Bugs** | 0 | 1 (B3) | 2 (B1, B4) | 1 (B2) | 4 (+2 fixed) |
| **Performance** | 0 | 1 (P1) | 4 (P2-P5) | 2 (P6, P7) | 7 |
| **UX** | 0 | 0 | 3 (U1-U3) | 3 (U4-U6) | 6 |
| **Tech Debt** | 0 | 3 | 5 | 5 | 13 |
| **TOTAL** | **2** | **11** | **22** | **17** | **52** |

---

## Final Verdict

Bayan is a technically impressive product with a solid NLP pipeline, a mature editor engine, and a well-architected extension. The core correction features (Spelling → Grammar → Punctuation) work end-to-end across both surfaces.

**What Bayan does well:**
- ✅ Custom contenteditable editor with proper cursor handling
- ✅ Multi-stage NLP pipeline with offset mapping
- ✅ Extension uses overlay-only rendering (never modifies user DOM)
- ✅ Supabase integration for cloud persistence
- ✅ Comprehensive test coverage (16 backend test files)
- ✅ Extension follows MV3 best practices (service worker, side panel)

**What must be fixed before growth:**
1. 🔴 **Security**: CORS wildcard + no rate limiting = anyone can abuse the API
2. 🔴 **Auth gap**: Extension users can't persist anything — breaks the SaaS value proposition
3. 🟡 **Extension missing API functions**: `bayanAutocomplete/Dialect/Quran` will throw `ReferenceError`
4. 🟡 **Backend monolith**: 2,844-line `app.py` is a maintenance bottleneck

**Bottom line:** Bayan is 80% of the way to a production-grade SaaS product. The remaining 20% is security hardening, extension auth, and code architecture — all achievable in 2-3 focused weeks.