# BAYAN Extension — Implementation Plan: Apply-to-Field, Context Menu Features & Smart Re-Analysis

> **For:** the coding agent implementing these changes.
> **Scope:** Chrome extension only (`extension/`). No backend changes.
> **Read this whole file before editing.** Each change lists the exact files, the current behavior, the target behavior, and the wiring required. Implement the three changes in order — Change 1 builds the messaging channel that Change 3 reuses.

---

## Background: how the pieces currently connect

- **`content-inline.js`** — injected into every page. Detects editable fields (`textarea`, `input`, `contenteditable`), analyzes them, and renders an overlay + tooltip. It **already writes corrections back** to the page field via `applyFix()`. It currently has **no `chrome.runtime.onMessage` listener** (it only *sends* messages).
- **`background.js`** — service worker. Owns the context menu and the API bridge. Registers exactly two menu items: `bayan-correct`, `bayan-summarize`. On click it opens the side panel and stashes `{contextAction, contextText}` in `chrome.storage.session`.
- **`sidepanel/sidepanel.js`** — reads that stashed context on open, switches to the matching tab, and auto-runs. It has `correct`, `summarize`, `dialect`, `quran`, `autocomplete` tabs and handlers. Its apply / apply-all buttons currently **only edit the side panel's own textarea** — they do **not** touch the page field.
- **`popup.js`** — same apply logic as the side panel, also only editing its own textarea.

Key gap for Changes 1 & 3: **the panel surfaces have no link back to the page field the text came from.** We must establish that link.

---

## CHANGE 1 — "Apply" / "Apply all" writes the result into the user's actual text field

### Current behavior
- **Inline tooltip apply** (`content-inline.js` → `applyFix`): ✅ already writes back to the page field and dispatches an `input` event. No change needed here.
- **Side panel & popup apply / apply-all**: ❌ only mutate the panel's own `<textarea id="input-text">`. The user's text field on the page is untouched.

### Target behavior
When the user clicks **Apply** (single suggestion) or **Apply all** in the **side panel** (and popup where applicable), the corrected text is written into the **original page field** that the text came from — replacing the selection, or the whole field if appropriate — and an `input` event is dispatched so the host page registers the change.

### Why this needs a messaging channel
The side panel is a separate document; it cannot touch the page DOM directly. It must send a message → background → content script → content script writes into the field.

### Implementation

**1.1 — `content-inline.js`: track the "source field" and expose a write-back handler**

- Add module state: `let lastInteractedField = null;`
- In `attachField(field)` (or `focusin`), set `lastInteractedField = field;` whenever a real editable field is focused. (Keep `activeField` semantics as-is; `lastInteractedField` persists even after focus moves to the side panel, which `activeField`/`detachField` would clear.)
- When the FAB sends `OPEN_SIDEPANEL` (existing code ~line 548), also include a stable identifier so we can re-find the field. Simplest robust approach: **tag the field** with a data attribute when opening the panel:
  ```js
  // before sending OPEN_SIDEPANEL
  if (lastInteractedField) lastInteractedField.dataset.bayanSource = '1';
  ```
- Add a **`chrome.runtime.onMessage` listener** (the content script currently has none):
  ```js
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'BAYAN_WRITE_BACK') {
      const field = lastInteractedField
        || document.querySelector('[data-bayan-source="1"]')
        || (isEditableField(document.activeElement) ? document.activeElement : null);
      if (!field) { sendResponse({ ok: false, reason: 'no_field' }); return true; }
      writeTextToField(field, msg.text, msg.mode); // mode: 'replaceAll' | 'replaceSelection'
      sendResponse({ ok: true });
      return true;
    }
    return false;
  });
  ```
- Implement `writeTextToField(field, text, mode)`:
  - For `textarea`/`input`: if `mode === 'replaceSelection'` and `selectionStart !== selectionEnd`, splice into `field.value` at the selection; else set `field.value = text`. Then `field.setSelectionRange(end, end)` and dispatch `new Event('input', { bubbles: true })`.
  - For `contenteditable`: focus the field and use `document.execCommand('insertText', false, text)` when there's a live selection inside it; otherwise set `field.textContent = text` and dispatch `input`. (Mirror the overlay-safe approach already used in `applyFix`.)
  - **Set the suppression flag from Change 3** right before dispatching `input` (see Change 3) when the write came from a non-correction model. For Change 1's correction apply-back, do **not** suppress — corrected text re-analyzing is harmless/expected.
  - Clear `data-bayan-source` after writing.

**1.2 — `background.js`: relay panel → content script**

- Add a message handler branch:
  ```js
  if (message.type === 'WRITE_BACK_TO_PAGE') {
    // forward to the active tab's content script
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab) { sendResponse({ ok: false }); return; }
      chrome.tabs.sendMessage(tab.id, {
        type: 'BAYAN_WRITE_BACK', text: message.text, mode: message.mode || 'replaceAll', source: message.source
      }, (resp) => sendResponse(resp || { ok: false }));
    });
    return true; // async
  }
  ```

**1.3 — `sidepanel/sidepanel.js`: send write-back after apply / apply-all**

- Add a helper:
  ```js
  function writeBackToPage(text, mode = 'replaceAll', source = 'correct') {
    chrome.runtime.sendMessage(
      { type: 'WRITE_BACK_TO_PAGE', text, mode, source },
      (resp) => {
        if (resp && resp.ok) showToast('✓ تم تطبيق التغييرات في الصفحة');
        else showToast('تعذّر الكتابة في الصفحة — انسخ النص يدوياً');
      }
    );
  }
  ```
- In the existing **apply-all** handler (after `analyzedText = applyAllPatches(...)`), call `writeBackToPage(analyzedText, 'replaceAll', 'correct');`.
- In the single-suggestion **apply** path (after `applyAndRebase` updates `analyzedText`), call `writeBackToPage(analyzedText, 'replaceAll', 'correct');`. (Whole-field replace is simplest and avoids offset drift between the panel copy and the live field.)

**1.4 — `popup.js`** (optional, lower priority)
- The popup closes when it loses focus, so write-back is less reliable there. Apply the same `writeBackToPage` helper **only if** product wants it; otherwise leave the popup apply editing its own textarea and rely on copy/download. Document the decision in a comment.

### Acceptance criteria
- Select/focus a page `<textarea>`, open the side panel via the FAB, click **Apply all** → the page textarea content is replaced with the corrected text and the host page sees an `input` event.
- Works for a single **Apply** too.
- If the source field can't be found, the user gets a clear toast (no silent failure).

---

## CHANGE 2 — Add "لهجات" and "قرآن" to the right-click context menu

### Current behavior
`background.js` registers only:
- `bayan-correct` → "تصحيح مع بيان"
- `bayan-summarize` → "تلخيص مع بيان"

### Target behavior
The selection context menu shows **four** Bayan items:
- تصحيح مع بيان (existing)
- تلخيص مع بيان (existing)
- **تحويل اللهجة إلى الفصحى مع بيان** (new)
- **تدقيق الآية مع بيان** (new)

Clicking a new item opens the side panel, switches to the matching tab, fills the selected text, and auto-runs that model.

### Implementation

**2.1 — `background.js`**
- Extend the actions map:
  ```js
  const ACTIONS = { CORRECT: 'correct', SUMMARIZE: 'summarize', DIALECT: 'dialect', QURAN: 'quran' };
  ```
- In `chrome.runtime.onInstalled` add two `chrome.contextMenus.create(...)` calls:
  ```js
  chrome.contextMenus.create({ id: 'bayan-dialect',
    title: chrome.i18n.getMessage('contextMenuDialect') || 'تحويل اللهجة إلى الفصحى مع بيان',
    contexts: ['selection'] });
  chrome.contextMenus.create({ id: 'bayan-quran',
    title: chrome.i18n.getMessage('contextMenuQuran') || 'تدقيق الآية مع بيان',
    contexts: ['selection'] });
  ```
- In `chrome.contextMenus.onClicked`, add routing:
  ```js
  if (info.menuItemId === 'bayan-dialect')  action = ACTIONS.DIALECT;
  if (info.menuItemId === 'bayan-quran')    action = ACTIONS.QURAN;
  ```
  The rest of the handler (open side panel + stash context) already works generically.

**2.2 — `sidepanel/sidepanel.js`** — handle the two new context actions on pickup
- The side panel already reads `contextAction` and, for `correct`/`summarize`, switches tab + auto-runs. Extend **both** pickup paths (`tryPickupContext` AND the `storage.onChanged` listener) to handle the new actions:
  ```js
  } else if (action === 'dialect') {
    dialectInput.value = text; updateCounts(dialectInput, dialectCharCount, null);
    document.querySelector('[data-tab="dialect"]')?.click();
    setTimeout(() => btnDialect.click(), 120);
  } else if (action === 'quran') {
    quranInput.value = text; updateCounts(quranInput, quranCharCount, null);
    document.querySelector('[data-tab="quran"]')?.click();
    setTimeout(() => btnQuran.click(), 120);
  }
  ```
  (Hoist `dialectInput`, `btnDialect`, `quranInput`, `btnQuran`, etc. so they're in scope of the pickup functions, or wrap the pickup dispatch in a small `runContextAction(action, text)` function declared after all element refs.)
- Update the `TAB` constant if it's used for validation: `const TAB = { CORRECT:'correct', SUMMARIZE:'summarize', DIALECT:'dialect', QURAN:'quran' };`

**2.3 — Locales** — add the two new menu strings
- `_locales/ar/messages.json`:
  ```json
  "contextMenuDialect": { "message": "تحويل اللهجة إلى الفصحى مع بيان", "description": "Context menu: dialect→MSA" },
  "contextMenuQuran":   { "message": "تدقيق الآية مع بيان", "description": "Context menu: Quran verify" }
  ```
- `_locales/en/messages.json`:
  ```json
  "contextMenuDialect": { "message": "Convert dialect to MSA with Bayan", "description": "Context menu: dialect→MSA" },
  "contextMenuQuran":   { "message": "Verify verse with Bayan", "description": "Context menu: Quran verify" }
  ```

### Acceptance criteria
- Right-clicking selected Arabic text shows all four Bayan items.
- "تحويل اللهجة…" opens the side panel on the **لهجة** tab with the text filled and converted.
- "تدقيق الآية…" opens the side panel on the **قرآن** tab with the text filled and checked.
- Existing correct/summarize items are unchanged.

---

## CHANGE 3 — After applying summarize / dialect / quran output into a field, do NOT auto-run the correction model on it

### The problem
`content-inline.js` analyzes editable fields on every keystroke and on programmatic `input` events. If text written back into the field came from the **summarize**, **dialect**, or **quran** model (Change 1's write-back for those flows), the correction pipeline would immediately re-analyze it — which the user does **not** want (a summary/MSA/verse is the intended final text, not something to "correct").

> Note: for the **correction** apply-back (Change 1), re-analysis is fine/expected and must stay enabled.

### Target behavior
When a write-back originates from a **non-correction** model (`summarize` / `dialect` / `quran`), the content script must **suppress correction analysis** for that field until the **user makes a genuine manual edit** (a real keystroke), at which point normal analysis resumes.

### Implementation (`content-inline.js`)

- Add module state:
  ```js
  let analysisSuppressed = false; // true after non-correction model write-back
  ```
- Extend `writeTextToField(field, text, mode)` (from Change 1) to accept the `source`/`mode` info, and:
  - If the write-back `source` is one of `summarize|dialect|quran`, set `analysisSuppressed = true;` **before** dispatching the `input` event.
  - If the `source` is `correct` (or inline correction apply), leave `analysisSuppressed = false`.
- In `onFieldInput()` (the input handler), **gate the analysis** but distinguish programmatic vs. human input. The cleanest signal: the synthetic `input` event we dispatch is not trusted. So:
  ```js
  function onFieldInput(e) {
    if (paused || !activeField) return;

    const programmatic = e && e.isTrusted === false;
    // A genuine user keystroke clears suppression and re-enables analysis.
    if (!programmatic && analysisSuppressed) analysisSuppressed = false;

    // Ghost-text autocomplete still runs (it's not the correction model).
    scheduleGhost();

    if (analysisSuppressed) {       // model output just written — skip correction
      clearHighlights();
      updateBadge(0);
      return;
    }
    // ...existing analysis path unchanged...
  }
  ```
  - Ensure `onFieldInput` is registered so it receives the event object (it's added via `field.addEventListener('input', onFieldInput)` — the handler already receives `e`).
  - The write-back's dispatched event uses `new Event('input', {bubbles:true})`, whose `isTrusted` is `false` — this is the reliable discriminator between "we wrote this" and "the user typed."
- Edge cases to handle:
  - **Badge state:** when suppressed, show the clean/✓ badge (0), not the analyzing spinner.
  - **Decide on ghost-text:** keep autocomplete ghost active (it's a separate, opt-in feature) OR also suppress it for summarize/quran outputs if product prefers a fully "frozen" result. Default: keep ghost on; add a one-line comment noting the choice.
  - **Re-enable correctness:** the very next real keystroke must restore analysis. Verify by typing one character after a dialect write-back → underlines should come back.

### Acceptance criteria
- Apply a **dialect** (or summarize/quran) result into a page field via Change 1 → the field shows the model output with **no correction underlines** and the FAB badge is not in an error/analyzing state.
- Type one character in that field → correction analysis resumes normally.
- Applying a **correction** result still re-analyzes as before (suppression must NOT trigger for `source: 'correct'`).

---

## Suggested implementation order & testing

1. **Change 2** first (self-contained, no messaging) — fastest win, easy to verify.
2. **Change 1** (build the messaging channel: content-script `onMessage` + `writeTextToField` + background relay + side-panel `writeBackToPage`).
3. **Change 3** (reuses Change 1's `writeTextToField` + `source` flag).

### Manual test pass (Chrome, `chrome://extensions` → Load unpacked → `extension/`)
- Reload the extension after editing the service worker / manifest (context menus only re-register on install/update — use the reload button).
- **Change 2:** right-click selected Arabic text → confirm 4 items → click لهجات and قرآن → correct tab opens + auto-runs.
- **Change 1:** focus a page `<textarea>`, open side panel via FAB, Apply / Apply all → page field updates + host page sees the change.
- **Change 3:** send a dialect result back to the field → no correction underlines → type one char → underlines return. Confirm a correction apply-back still re-analyzes.

### Files touched (summary)
| File | Change 1 | Change 2 | Change 3 |
|------|:---:|:---:|:---:|
| `extension/content-inline.js` | ✅ onMessage + `writeTextToField` + `lastInteractedField` | — | ✅ `analysisSuppressed` gate |
| `extension/background.js` | ✅ `WRITE_BACK_TO_PAGE` relay | ✅ 2 menu items + routing | — |
| `extension/sidepanel/sidepanel.js` | ✅ `writeBackToPage` on apply/apply-all | ✅ pickup for dialect/quran | ✅ pass correct `source` |
| `extension/popup.js` | ⚠️ optional | — | — |
| `extension/_locales/ar/messages.json` | — | ✅ 2 strings | — |
| `extension/_locales/en/messages.json` | — | ✅ 2 strings | — |

### Guardrails
- Don't break the existing inline `applyFix` write-back — it already works; reuse its patterns, don't replace it.
- All cross-document communication goes panel → `background.js` → content script. The side panel must never assume direct page DOM access.
- Use `event.isTrusted === false` (not a custom flag on the event) to detect programmatic input — it's tamper-proof and requires no host-page cooperation.
- Keep every new code path guarded (`if (!field) ...`, `resp || {ok:false}`) so a missing field or closed tab degrades to a toast, never an uncaught error.
