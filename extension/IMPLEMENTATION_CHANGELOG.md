# BAYAN Extension — Implementation Changelog

> **Session date:** 2026-06-27
> **Scope:** Chrome extension only (`extension/`). No backend, website, or Supabase changes.
> **Source of work:** Implementation of the extension-facing items from `BAYAN_COMPLETE_AUDIT.md`.

---

## ⚠️ Important context

While this work was in progress, **a second process was editing the same extension files in parallel**, implementing the same audit plan. To avoid corrupting files, this session was scoped to the **untouched gaps**. As a result, the changes below fall into two groups:

- **Authored in this session** — Phase 5 (TXT export), Phase 6 (English locale, `all_frames`, bug fixes B4/U1), and the **completion of the broken Phase 4** (inline ghost-text autocomplete).
- **Verified only** — Phases 1–3 (API client functions, popup/side-panel feature tabs) were written by the concurrent process; this session confirmed they are correct against the real backend (`src/app.py`) but did not author them.

This changelog documents **what was authored in this session**.

---

## Files changed

| File | Type | What changed |
|------|------|--------------|
| `extension/content-inline.js` | **Edited** | Implemented the missing inline ghost-text autocomplete engine (Phase 4); overlay reposition on resize (B4); tooltip viewport clamping (U1) |
| `extension/content-inline.css` | **Edited** | Styles for the ghost-text mirror + muted suffix |
| `extension/popup.js` | **Edited** | "Download as TXT" buttons for corrected text + summary (Phase 5 / H3) |
| `extension/sidepanel/sidepanel.js` | **Edited** | "Download as TXT" buttons for corrected text + summary (Phase 5 / H3) |
| `extension/manifest.json` | **Edited** | `all_frames: true` for iframe editor support (M2) |
| `extension/_locales/en/messages.json` | **Created** | English locale (L1) |

> `extension/shared/bayan-api.js`, `extension/popup.html`, `extension/sidepanel/sidepanel.html`, and the dialect/quran/autocomplete handlers in `popup.js` / `sidepanel.js` were authored by the **concurrent process**, not this session. They are listed in the "Verified only" section at the end.

---

## 1. Phase 4 — Inline ghost-text autocomplete (audit item H2)

**File:** `extension/content-inline.js`, `extension/content-inline.css`

### The bug this fixed (regression)

The concurrent process had added ghost-text **state variables** and a **call** to `scheduleGhost()` on every keystroke (in `onFieldInput`), but **never defined `scheduleGhost` or any ghost logic**. The content script therefore threw:

```
ReferenceError: scheduleGhost is not defined
```

…on **every keystroke in any editable field**, which silently broke inline analysis on every website. This was an active regression, not just a missing feature.

### What was implemented

A Tab-to-accept ghost-text engine for 3rd-party `<textarea>` / `<input>` fields, ported from the website's `src/js/autocomplete.js` behavior:

| Function | Role |
|----------|------|
| `ghostEligible()` | Only fires when the caret is collapsed **at the end** of the field, ≥3 chars, Arabic present |
| `scheduleGhost()` | 450 ms debounce; clears any stale ghost first |
| `fetchGhost(ctx)` | `POST {BAYAN.API_BASE}/api/autocomplete` with `{ context, n: 1 }`; staleness-guarded |
| `showGhost(base, suffix)` | Transparent-mirror overlay (same technique as the error overlay) painting the completion in muted grey at the caret |
| `acceptGhost()` | **Tab** appends the suggestion (+leading space if needed), moves caret to end, dispatches `input` to re-trigger analysis + next-word ghost |
| `clearGhost()` | Teardown — cancels timer, removes overlay, resets state |
| `syncGhostScroll()` | Keeps the ghost aligned with field scroll |
| `onFieldKeydown(e)` | **Tab** = accept, **Escape** = dismiss |

### Wiring added
- `keydown` → `onFieldKeydown` registered in `attachField()`, removed in `detachField()`.
- `clearGhost()` added to `detachField()` teardown.
- `syncOverlay()` now also calls `syncGhostScroll()`.
- The window `scroll` handler now repositions the ghost overlay (alongside the error overlay).

### Why a direct `fetch` (not `bayanAutocomplete`)
The content script only loads `shared/constants.js`, `shared/analysis-controller.js`, and `content-inline.js` — **not** `bayan-api.js`/`config.js`. So `bayanAutocomplete()`/`CONFIG` are out of scope. `BAYAN.API_BASE` (from `constants.js`) **is** in scope, and `host_permissions` already covers that host, so the call is made directly.

### Safety properties
- Overlay-only: never mutates the field while typing — only on explicit **Tab**.
- Best-effort: network/render errors are swallowed; the analysis path is never affected.
- Respects protected sites and is gated to `textarea`/`input` only.

### CSS added (`content-inline.css`)
```css
.bayan-il-ghost        { background: transparent !important; pointer-events: none !important; }
.bayan-il-ghost-suffix { color: rgba(120,120,130,0.75) !important; opacity: 0.9; }
```
(The suffix needs an explicit color because the mirror parent is `color: transparent`.)

---

## 2. Phase 5 — Download corrected text / summary as TXT (audit item H3)

**Files:** `extension/popup.js`, `extension/sidepanel/sidepanel.js`

- Added a self-contained `downloadTxt(text, filename)` helper (Blob + object URL + cleanup).
- Download buttons are **injected programmatically** next to the existing copy buttons — no HTML edits, to minimize conflict with the concurrent writer.
- Popup: downloads `bayan-corrected.txt` and `bayan-summary.txt`.
- Side panel: same, anchored to the existing copy buttons' parent containers.

---

## 3. Phase 6 — Polish & bug fixes

### B4 — Overlay reposition on resize (`content-inline.js`)
The window `resize` handler previously repositioned only the floating button. It now also **re-renders the error overlay** when suggestions are present, so highlights stay aligned after a viewport resize.

### U1 — Tooltip viewport clamping (`content-inline.js`)
The error tooltip previously clamped only the right edge. It now also:
- clamps the **left** edge if it overflows,
- **flips above** the highlighted mark when it would overflow the **bottom** of the viewport (falling back to pinning at the top edge if there's no room above).

### M2 — iframe editor support (`manifest.json`)
Added `"all_frames": true` to the content-script registration so editors inside `<iframe>` (TinyMCE, Gutenberg, etc.) are reachable.

### L1 — English locale (`_locales/en/messages.json`, new file)
Created an English `messages.json` mirroring the Arabic keys (`extName`, `extDescription`, `contextMenuCorrect`, `contextMenuSummarize`) so the extension is publishable for non-Arabic users.

---

## Verification performed

- `node --check` passed on all edited JS files: `content-inline.js`, `popup.js`, `sidepanel/sidepanel.js`, `shared/bayan-api.js`.
- JSON validated: `manifest.json`, `_locales/en/messages.json`, `_locales/ar/messages.json`.
- Confirmed all eight ghost-text functions are defined, so the previously-orphaned `scheduleGhost()` call now resolves.

### NOT verified (no runtime/browser test in this session)
- The extension was **not** loaded in Chrome. Caret-position rendering of ghost text across real sites, the new tabs, downloads, and iframe behavior are unverified by execution. See the testing guide below.

---

## How to test (manual, in Chrome)

The backend (`bayan10-bayan-api.hf.space`) is already live, so no local server is needed.

1. **Load:** `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select `extension/`. Confirm no errors on the card; open the **service worker** console and confirm it's clean.
2. **Popup tabs:** open the popup → expect 5 tabs (تصحيح · تلخيص · لهجة · قرآن · إكمال). Exercise each.
3. **Export:** analyze text → click the download (↓) icon in the result header → `bayan-corrected.txt` downloads.
4. **Ghost text (H2):** in a plain `<textarea>` (e.g. `extension/tests/test_inline.html`), type a few Arabic words ending in a space → grey ghost text appears after ~0.5 s → **Tab** inserts, **Esc** dismisses. Confirm **no** `scheduleGhost is not defined` error in the page console.
5. **Regression checks:** resize the window with errors highlighted (B4 — stays aligned); click an error near the bottom (U1 — tooltip flips up); try a textarea inside an iframe (M2).

---

## Authored by the concurrent process (verified, not authored here)

For completeness — these extension changes exist but were **not** written in this session:

- `extension/shared/bayan-api.js` — `bayanDialect()`, `bayanQuran()`, `bayanAutocomplete()` (audit B3).
- `extension/popup.html` + `extension/popup.js` — dialect / quran / autocomplete tabs + handlers (U3).
- `extension/sidepanel/sidepanel.html` + `extension/sidepanel/sidepanel.js` — same three feature tabs + handlers.

---

## Out of scope (NOT done — still open from the 52-item audit)

This session covered extension items only. The following remain **open**: all Critical/Security backend items (C1–C3, S1–S7), extension auth (H1), the `002_documents.sql` migration (H4), the `app.py` split (H5), and the bulk of the Medium/Low backend, website, and performance items. See `BAYAN_COMPLETE_AUDIT.md` for the full list.
