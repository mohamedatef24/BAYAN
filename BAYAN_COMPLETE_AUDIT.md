# BAYAN — Complete Product, Codebase & Extension Deep Audit

## 1. Current System Overview

Bayan is a full-featured Arabic AI writing assistant deployed across two primary surfaces: a web application and a Chrome extension. 
The core architecture is built around a centralized Flask API hosted on Hugging Face Spaces (`bayan10-bayan-api.hf.space`), which serves NLP models for spelling, grammar, punctuation, summarization, dialect conversion, and Quranic validation.

**Website Architecture:**
- **Frontend:** Vanilla JS, HTML, CSS (Tailwind via CDN). Uses a custom `contenteditable` editor engine.
- **Backend:** Flask API handling model inference.
- **Database/Auth:** Supabase for cloud persistence, document sync, and authentication (Guest & Google).

**Extension Architecture:**
- **Framework:** Manifest V3.
- **Components:** Background Service Worker (`background.js`), Content Scripts (`content-inline.js`), Sidepanel, and Popup.
- **Communication:** Background worker acts as the single network boundary to the HF API.

---

## 2. Feature Inventory

| Feature | Website | Extension | Status | Required Action |
|---------|---------|-----------|--------|-----------------|
| **Spelling/Grammar/Punctuation** | ✅ Exists | ✅ Exists | Parity | None |
| **Summarization** | ✅ Exists | ✅ Exists | Parity | None |
| **AutoComplete** | ✅ Exists | ❌ Missing | Gap | Implement inline text prediction in `content-inline.js` |
| **Dialect Conversion** | ✅ Exists | ❌ Missing | Gap | Add to Extension Sidepanel |
| **Quran Validation** | ✅ Exists | ❌ Missing | Gap | Add to Extension Sidepanel |
| **Document Cloud Save** | ✅ Exists | ❌ Missing | Gap | Integrate Supabase into Extension |
| **Authentication** | ✅ Exists | ❌ Missing | Gap | Implement shared auth state via cookies/Supabase |
| **Settings Sync** | ✅ Exists | ❌ Missing | Gap | Share user preferences via Supabase |

---

## 3. Website vs Extension Comparison

### Authentication
- **Website:** Supports Guest login and Google login via Supabase. State is maintained via `auth.js`.
- **Extension:** Uses isolated `chrome.storage.local/session`. **Does not share sessions** with the website. 
- **Priority:** **High**. Users cannot access their cloud documents or synced preferences from the extension.

### AI Features
- **Website:** Full suite (Analyze, Summarize, AutoComplete, Dialect, Quran).
- **Extension:** Only uses `/api/analyze` (Correct) and `/api/summarize`. Missing AutoComplete, Dialect, and Quran validation.
- **Priority:** **Medium**. Core features are present, but advanced features are missing.

### Documents
- **Website:** Full document management (Save, Load, Export PDF/DOCX, Sync Queue).
- **Extension:** Cannot save, load, or access document history.
- **Priority:** **High**. Destroys the omnichannel UX.

---

## 4. Missing Features & Gaps

1. **Shared Authentication:** The extension operates anonymously. Needs Supabase integration in `background.js` to share JWTs.
2. **Missing Editor Tools in Extension:** "Dialect" and "Quran" tabs are missing from the sidepanel.
3. **AutoComplete in Extension:** The website's ghost-text autocomplete is highly valuable but entirely absent from textareas on the web via the extension.

---

## 5. Bugs & Architectural Issues Found

1. **Duplicated Logic:** UI rendering logic for suggestion cards is duplicated between `src/js/ui.js` (website) and `extension/shared/bayan-ui.js` (extension).
2. **Cache Consistency:** The extension implements its own LRU cache (`_cache` in `background.js`), whereas the website relies on network or different caching strategies.
3. **Editor Brittle-ness:** The website relies heavily on DOM-based offset replacements (`setEditorHTML`, `restoreSelection`). Any changes to HTML sanitization risk breaking cursor positions. (Must strictly adhere to "DO NOT break existing editor architecture").

---

## 6. Security Issues

1. **API Exposure:** The Hugging Face endpoints (`/api/*`) are public. If they lack rate-limiting or CORS whitelisting, they are vulnerable to abuse by third parties.
2. **Token Handling:** The extension uses `chrome.storage.local` which is fine, but since it lacks Supabase RLS context, it cannot securely fetch user documents yet.

---

## 7. Performance Issues

1. **Website:** Bundle size is relatively small due to Vanilla JS, but loading heavy libraries like `mammoth.browser.min.js` and `docx.umd.js` synchronously in `index.html` blocks render. These should be lazy-loaded.
2. **Extension:** `content-inline.js` attaches listeners to `input`/`keyup` events. If not properly debounced on heavy sites (e.g., Google Docs, WordPress), it can cause severe input lag.

---

## 8. UX Problems

1. **Inconsistent Wording:** The website uses "مستنداتي" (My Documents) while the extension lacks this concept entirely.
2. **Flow Disconnect:** A user correcting text in the extension cannot save that text to their Bayan account to continue editing on the website later.
3. **Loading States:** The extension's sidepanel lacks the polished "Focus Mode" and "SVG Donut Charts" available on the web editor.

---

## 9. Technical Debt

1. **Separation of Concerns:** The website's JS files (e.g., `editor.js`, `format.js`) tightly couple DOM manipulation with business logic.
2. **Extension Architecture:** The extension duplicates `constants.js`, `hash.js`, and `analysis-controller.js` instead of importing from a shared monorepo workspace package.

---

## 10. Recommended Roadmap (Prioritized)

### Phase 1: Authentication Unification (Critical)
- **Goal:** Share Supabase session between Website and Extension.
- **Action:** Implement `chrome.cookies` or message passing to inject the Supabase JWT into the extension.

### Phase 2: Document Sync in Extension (High)
- **Goal:** Allow extension users to save selected text directly to their Bayan documents.
- **Action:** Add "Save to Bayan" in the context menu and sidepanel, hitting the Supabase DB.

### Phase 3: Parity of AI Tools (Medium)
- **Goal:** Bring AutoComplete, Dialect, and Quran features to the extension.
- **Action:** Update the sidepanel UI and `background.js` routing to support `/api/dialect` and `/api/quran`.

### Phase 4: Performance & Code Sharing (Low)
- **Goal:** Reduce tech debt.
- **Action:** Refactor `shared/` folder to act as a true submodule for both web and extension. Lazy load heavy vendor scripts on the web.
