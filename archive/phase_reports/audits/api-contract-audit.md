# BAYAN — API Contract Documentation

## Base URL
```
https://bayan10-bayan-api.hf.space
```

---

## GET /api/health

**Purpose:** Production health check and model status.

**Request:** No body required.

**Response:**
```json
{
  "status": "healthy",
  "mode": "hf_spaces_local",
  "models": {
    "summarization": true,
    "spelling": true,
    "grammar": true,
    "punctuation": true,
    "autocomplete": false
  },
  "supabase": {
    "configured": true
  },
  "environment": "huggingface_spaces"
}
```

> [!NOTE]
> NLP models use lazy loading. `spelling`, `grammar`, `punctuation` report `false` until first inference request triggers model loading. After first call, they report `true` for the lifetime of the process.

---

## POST /api/analyze

**Purpose:** Full NLP pipeline (Spelling → Grammar → Punctuation). Primary endpoint used by the editor.

**Request:**
```json
{
  "text": "Arabic text to analyze"
}
```

**Response:**
```json
{
  "status": "success",
  "original": "input text",
  "corrected": "fully corrected text",
  "suggestions": [
    {
      "start": 0,
      "end": 5,
      "original": "word",
      "correction": "corrected_word",
      "type": "spelling|grammar|punctuation",
      "alternatives": ["alt1", "alt2"]
    }
  ]
}
```

**Error (400):** Empty or missing text
**Error (500):** Server error

**Suggestion Types & Colors:**
| Type | Color |
|------|-------|
| `spelling` | 🔴 Red `#ef4444` |
| `grammar` | 🟡 Yellow `#eab308` |
| `punctuation` | 🟢 Green `#22c55e` |

**Max Text Length:** 5000 characters

---

## POST /api/spelling

**Purpose:** Standalone spelling correction.

**Request:**
```json
{
  "text": "Arabic text with spelling errors"
}
```

**Response:**
```json
{
  "status": "success",
  "original_text": "input text",
  "corrected_text": "corrected text"
}
```

**Error (400):** Empty text, text > 5000 chars
**Error (503):** Model unavailable

---

## POST /api/grammar

**Purpose:** Standalone grammar correction.

**Request:**
```json
{
  "text": "Arabic text with grammar errors"
}
```

**Response:**
```json
{
  "status": "success",
  "original_text": "input text",
  "corrected_text": "corrected text"
}
```

**Error (503):** Model/Gradio Space unavailable

---

## POST /api/punctuation

**Purpose:** Standalone punctuation restoration.

**Request:**
```json
{
  "text": "Arabic text without punctuation"
}
```

**Response:**
```json
{
  "status": "success",
  "original_text": "input text",
  "corrected_text": "punctuated text"
}
```

**Error (503):** Model unavailable

---

## POST /api/summarize

**Purpose:** Arabic text summarization.

**Request:**
```json
{
  "text": "Long Arabic text to summarize (min 10 chars)"
}
```

**Response:**
```json
{
  "status": "success",
  "summary": "summarized text",
  "original_length": 500,
  "summary_length": 120
}
```

**Error (400):** Text too short (< 10 chars) or too long (> 5000 chars)

---

## Error Response Schema

All endpoints return errors in this format:
```json
{
  "status": "error",
  "error": "Human-readable error message"
}
```

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (missing/invalid input) |
| 500 | Internal server error |
| 503 | Model unavailable |
