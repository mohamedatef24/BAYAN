# Bayan (بيان) — Phase 1 Editor Stabilization Refactor Plan (Revised)

## Goal

Refactor the current editor architecture to solve the core technical problems while avoiding unnecessary complexity.

This phase is strictly focused on editor stability and maintainability.

### Success Criteria

* Cursor position is preserved after analysis updates.
* Text selection is preserved.
* Multiple occurrences of the same word are highlighted correctly.
* Suggestions use exact character offsets instead of string replacement.
* Rendering is XSS-safe.
* Editor code becomes modular and easier to extend.
* Future features (DOCX import, export, database persistence) remain possible without major rewrites.

---

# Scope

## Included

* Cursor preservation
* Selection preservation
* Offset-based highlighting
* Duplicate occurrence handling
* Secure rendering
* Editor code modularization

## Excluded

* DOCX Import
* TXT Import
* DOCX Export
* PDF Export
* Supabase
* Authentication
* Autosave
* Database integration
* Deployment work

These belong to later phases.

---

# Architectural Strategy

## Keep Existing contenteditable

We will continue using a single contenteditable editor.

Current:

```html
<div id="editor-container" contenteditable="true"></div>
```

No dual-layer editor.

No transparent text layer.

No click-forwarding system.

No overlay synchronization.

---

# Why

The current project is a graduation project, not a full-scale IDE.

Keeping contenteditable provides:

* Lower complexity
* Faster implementation
* Fewer bugs
* Easier maintenance
* Faster delivery

while still solving all current issues.

---

# Milestone 1 — Modularize Editor Logic

## Objective

Separate editor concerns from UI and networking logic.

### New Structure

```text
src/
│
├── js/
│   ├── api.js
│   ├── editor.js
│   ├── renderer.js
│   ├── selection.js
│   └── ui.js
│
├── index.html
```

---

## Responsibilities

### api.js

Handles:

* /api/analyze
* /api/spelling
* /api/autocomplete
* /api/summarize

No DOM manipulation.

---

### editor.js

Handles:

* Reading editor text
* Writing editor text
* Editor events
* Debouncing

---

### renderer.js

Handles:

* Highlight rendering
* Safe HTML generation
* Offset mapping

---

### selection.js

Handles:

* Save selection
* Restore selection
* Caret positioning

---

### ui.js

Handles:

* Tooltips
* Panels
* Buttons
* Notifications

---

# Milestone 2 — Selection Preservation

## Problem

Current rendering rewrites the editor DOM.

Result:

* Cursor jumps
* Selection disappears
* Focus is lost

---

## Solution

Before rendering:

```js
const selection = saveSelection();
```

After rendering:

```js
restoreSelection(selection);
```

---

## Required Functions

```js
saveSelection()
restoreSelection()
getCaretOffset()
setCaretOffset()
```

---

## Expected Result

User can:

* Type continuously
* Select text
* Accept suggestions

without cursor jumps.

---

# Milestone 3 — Backend Offset Support

## Current Problem

Suggestions identify words only.

Example:

```json
{
  "original": "ذهبو",
  "correction": "ذهبوا"
}
```

This fails when the same word appears multiple times.

---

## Required Change

Update backend responses.

Example:

```json
{
  "suggestions": [
    {
      "start": 12,
      "end": 17,
      "original": "ذهبو",
      "correction": "ذهبوا",
      "type": "spelling"
    }
  ]
}
```

---

## Benefits

* Exact positioning
* No ambiguity
* Faster rendering
* Supports duplicate words

---

# Milestone 4 — Offset-Based Rendering

## Current Problem

Rendering uses:

```js
text.replace(...)
```

which only affects the first occurrence.

---

## New Strategy

Use character offsets.

Example:

```json
{
  "start": 45,
  "end": 50
}
```

Rendering process:

1. Split text into segments.
2. Create normal text nodes.
3. Create highlighted spans.
4. Assemble output safely.

---

## Result

Every occurrence is highlighted correctly.

---

# Milestone 5 — Secure Rendering

## Current Problem

Direct innerHTML generation creates XSS risk.

---

## Solution

Escape all user-generated content.

Example:

```js
escapeHtml(text)
```

before inserting into DOM.

---

## Requirements

Never inject:

```js
userInput
suggestionText
apiResponse
```

directly into HTML.

Always sanitize first.

---

# Milestone 6 — Highlight Engine Refactor

## Objective

Create a reusable rendering pipeline.

### Input

```json
{
  "text": "...",
  "suggestions": [...]
}
```

### Output

Safe highlighted HTML.

---

## Responsibilities

The renderer must support:

* Spelling highlights
* Grammar highlights
* Punctuation highlights

without changing editor logic.

---

# Milestone 7 — Tooltip Mapping

## Strategy

Each highlight receives:

```html
<span
  class="error-highlight"
  data-suggestion-id="42">
</span>
```

Clicking a span retrieves:

```js
currentSuggestions[id]
```

and opens the tooltip.

---

## Benefits

* Cleaner architecture
* Easier debugging
* Future extensibility

---

# Deliverables

At the end of Phase 1:

## Functional Deliverables

* Stable editor
* Cursor preservation
* Selection preservation
* Duplicate-word support
* Offset-based highlighting
* Secure rendering
* Modular editor code

---

## Technical Deliverables

```text
api.js
editor.js
renderer.js
selection.js
ui.js
```

---

## Explicitly Deferred

The following are NOT part of this phase:

* Light/Dark Theme
* UI Redesign
* TXT Import/Export
* DOCX Import/Export
* PDF Export
* Authentication
* Supabase
* Database Storage
* Autosave
* Deployment

These will be implemented in later phases.
