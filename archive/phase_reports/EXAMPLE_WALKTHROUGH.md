# Example Walkthrough: Multiple Duplicates Rendering

## Example Input

```
Text: "ذهبو الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى"
```

## Step 1: Backend Analysis

When this text is sent to `/api/analyze`, the backend returns:

```json
{
  "original": "ذهبو الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى",
  "corrected": "ذهبوا الى المدرسة ثم ذهبوا الى البيت ثم ذهبوا مرة اخرى",
  "suggestions": [
    {
      "start": 0,
      "end": 4,
      "original": "ذهبو",
      "correction": "ذهبوا",
      "type": "spelling"
    },
    {
      "start": 20,
      "end": 24,
      "original": "ذهبو",
      "correction": "ذهبوا",
      "type": "spelling"
    },
    {
      "start": 38,
      "end": 42,
      "original": "ذهبو",
      "correction": "ذهبوا",
      "type": "spelling"
    }
  ],
  "status": "success"
}
```

## Step 2: Offset Verification

Character positions in the text:

```
Position:  0    5    10   15   20   25   30   35   40   45   50
Text:      ذ    ــ   ـ    م    ذ    ــ   ـ    ب    ذ    ــ   ى
           ذهبو الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى
           ^^^^              ^^^^              ^^^^
           0-4              20-24            38-42
```

## Step 3: Renderer Processing

### 3a. Sort Suggestions (already sorted)
```javascript
sorted = [
  {start: 0, end: 4, ...},   // First occurrence
  {start: 20, end: 24, ...}, // Second occurrence
  {start: 38, end: 42, ...}  // Third occurrence
]
```

### 3b. Create Segments
The text is split into segments at suggestion boundaries:

```javascript
segments = [
  {type: 'suggestion', text: 'ذهبو', suggestion: {...}},      // [0:4]
  {type: 'text', text: ' الى المدرسة ثم '},                    // [4:20]
  {type: 'suggestion', text: 'ذهبو', suggestion: {...}},      // [20:24]
  {type: 'text', text: ' الى البيت ثم '},                      // [24:38]
  {type: 'suggestion', text: 'ذهبو', suggestion: {...}},      // [38:42]
  {type: 'text', text: ' مرة اخرى'}                             // [42:51]
]
```

### 3c. Render Each Segment

**Segment 1** (suggestion):
```html
<span class="spelling-error" 
      data-suggestion-id="0"
      data-original="ذهبو"
      data-correction="ذهبوا"
      data-type="spelling"
      title="spelling: ذهبوا">
  ذهبو
</span>
```

**Segment 2** (text): `" الى المدرسة ثم "`

**Segment 3** (suggestion):
```html
<span class="spelling-error" 
      data-suggestion-id="1"
      data-original="ذهبو"
      data-correction="ذهبوا"
      data-type="spelling"
      title="spelling: ذهبوا">
  ذهبو
</span>
```

**Segment 4** (text): `" الى البيت ثم "`

**Segment 5** (suggestion):
```html
<span class="spelling-error" 
      data-suggestion-id="2"
      data-original="ذهبو"
      data-correction="ذهبوا"
      data-type="spelling"
      title="spelling: ذهبوا">
  ذهبو
</span>
```

**Segment 6** (text): `" مرة اخرى"`

## Step 4: Final Rendered Output

Complete HTML:

```html
<span class="spelling-error" data-suggestion-id="0" data-original="ذهبو" data-correction="ذهبوا" data-type="spelling" title="spelling: ذهبوا">ذهبو</span> الى المدرسة ثم <span class="spelling-error" data-suggestion-id="1" data-original="ذهبو" data-correction="ذهبوا" data-type="spelling" title="spelling: ذهبوا">ذهبو</span> الى البيت ثم <span class="spelling-error" data-suggestion-id="2" data-original="ذهبو" data-correction="ذهبوا" data-type="spelling" title="spelling: ذهبوا">ذهبو</span> مرة اخرى
```

Visual representation:
```
[ذهبو] الى المدرسة ثم [ذهبو] الى البيت ثم [ذهبو] مرة اخرى
(red)                  (red)                 (red)
```

## Step 5: User Interaction

### User clicks on first "ذهبو" (red underline)

1. Click event fired on `<span role="0">`
2. Tooltip appears showing:
   - Error type: "خطأ إملائي"
   - Correction: "ذهبوا"
3. User can click to apply correction

### When user applies correction:

**Before**:
```
ذهبو الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى
```

**After** (1st corrected):
```
ذهبوا الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى
```

**Key**: Only the clicked occurrence changes. The other two remain.

**Important**: 
- ✅ Cursor position is preserved
- ✅ Selection is preserved
- ✅ Text is re-analyzed immediately
- ✅ New highlights appear with updated offsets

## Advantages Over Old System

### Old System (replace-based)
```javascript
// Try to find and replace first occurrence
text.replace("ذهبو", "ذهبوا")
// Result: ALL occurrences get replaced (or just first depending on regex)
// Problem: Can't target specific occurrence
// Problem: Duplicate words fail silently
```

### New System (offset-based)
```javascript
// Render all occurrences with specific offsets
render({
  text: "ذهبو الى ... ذهبو الى ... ذهبو مرة",
  suggestions: [
    {start: 0, end: 4, ...},   // Exact position 1
    {start: 20, end: 24, ...}, // Exact position 2
    {start: 38, end: 42, ...}  // Exact position 3
  ]
})
// Result: 3 independent spans, each clickable/correctable
// Advantage: Precise, no ambiguity, no silent failures
```

## Code Flow Diagram

```
User Text Input
    ↓
┌─────────────────────────────────┐
│ saveSelection() from selection.js│
│ Stores: {selectionStart, end}   │
└────────────────┬────────────────┘
                 ↓
┌─────────────────────────────────┐
│ analyzeText() from editor.js     │
│ Calls: POST /api/analyze        │
└────────────────┬────────────────┘
                 ↓
          API Response
    {original, corrected,
     suggestions with offsets}
                 ↓
┌─────────────────────────────────┐
│ render() from renderer.js        │
│ Input: text + suggestions[]      │
│ - Sort by offset                │
│ - Create segments               │
│ - Escape HTML                   │
│ - Generate spans with metadata  │
│ Output: Safe HTML string        │
└────────────────┬────────────────┘
                 ↓
┌─────────────────────────────────┐
│ setEditorHTML() from selection.js│
│ Updates DOM                      │
└────────────────┬────────────────┘
                 ↓
┌─────────────────────────────────┐
│ restoreSelection() from selection│
│ Restores {selectionStart, end}  │
│ Cursor back where it was!       │
└──────────────────────────────────┘
```

## Per-Occurrence Data

Each `<span>` carries its own suggestion:

**Span 1**:
- `data-suggestion-id="0"` - First in suggestions array
- `data-original="ذهبو"`
- `data-correction="ذهبوا"`
- Spans characters [0:4]

**Span 2**:
- `data-suggestion-id="1"` - Second in suggestions array
- `data-original="ذهبو"` (same original, different position)
- `data-correction="ذهبوا"` (same correction)
- Spans characters [20:24]

**Span 3**:
- `data-suggestion-id="2"` - Third in suggestions array
- `data-original="ذهبو"` (same original, different position)
- `data-correction="ذهبوا"` (same correction)
- Spans characters [38:42]

**Result**: No confusion. Each occurrence is independent.

---

## Summary

✅ **All 3 occurrences are highlighted**  
✅ **Each is independently identifiable**  
✅ **User can click any one to see/apply correction**  
✅ **Cursor/selection preserved through re-renders**  
✅ **XSS-safe (all user content escaped)**  
✅ **No regex or string replacement needed**
