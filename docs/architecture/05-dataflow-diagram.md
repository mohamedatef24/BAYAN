# 05 — Data Flow Diagram (DFD)

## Overview

This diagram traces how data flows through the BAYAN system — from user input to final storage, through all NLP processing stages.

## Level 0 — Context Diagram

```mermaid
graph LR
    USER["👤 User"] -->|"Arabic Text"| BAYAN["🔵 BAYAN System"]
    BAYAN -->|"Corrections · Summaries · Documents"| USER
    BAYAN <-->|"Auth · Data"| SUPABASE["🗄️ Supabase"]
    BAYAN <-->|"Models"| HUGGINGFACE["🤗 HuggingFace"]
```

## Level 1 — System DFD

```mermaid
graph TD
    subgraph "Data Sources"
        INPUT["📝 User Input Text"]
        IMPORT["📥 Imported File<br/>(TXT / DOCX / PDF)"]
    end

    subgraph "1.0 Text Correction Pipeline"
        SPELL["1.1 AraSpell<br/>Spelling Correction"]
        GRAMMAR["1.2 Grammar Check<br/>Bayan Grammar"]
        PUNCT["1.3 Punctuation<br/>PuncAra-v1"]
        MERGE["1.4 Merge Results<br/>Offset Mapping"]
    end

    subgraph "2.0 Display Pipeline"
        HIGHLIGHT["2.1 Error Highlighting<br/>renderer.js"]
        SIDEBAR["2.2 Suggestions Panel<br/>ui.js"]
        SCORE["2.3 Writing Score<br/>Calculation"]
        STATS["2.4 Editor Stats<br/>Words · Chars · Sentences"]
    end

    subgraph "3.0 Summarization Pipeline"
        SUMM_IN["3.1 Extract Clean Text"]
        SUMM_MODEL["3.2 MBart Summarization"]
        SUMM_OUT["3.3 Summary Display"]
    end

    subgraph "4.0 AutoComplete Pipeline"
        AC_IN["4.1 Cursor Context"]
        AC_MODEL["4.2 AutoComplete Model"]
        AC_OUT["4.3 Dropdown Suggestions"]
    end

    subgraph "5.0 Storage"
        LOCAL["5.1 localStorage<br/>Draft · Dismissed Words"]
        DOCUMENTS_DB["5.2 Supabase: documents"]
        SUMMARIES_DB["5.3 Supabase: summaries"]
        SETTINGS_DB["5.4 Supabase: settings"]
        PROFILES_DB["5.5 Supabase: profiles"]
    end

    subgraph "6.0 Export"
        EXPORT_TXT["6.1 Export TXT"]
        EXPORT_DOCX["6.2 Export DOCX"]
        EXPORT_PDF["6.3 Export PDF"]
    end

    INPUT --> SPELL
    IMPORT --> SPELL
    SPELL -->|"Corrected tokens"| GRAMMAR
    GRAMMAR -->|"Grammar-checked text"| PUNCT
    PUNCT -->|"Punctuated text"| MERGE
    MERGE -->|"All suggestions + offsets"| HIGHLIGHT
    MERGE --> SIDEBAR
    MERGE --> SCORE
    INPUT --> STATS

    INPUT --> SUMM_IN
    SUMM_IN --> SUMM_MODEL
    SUMM_MODEL --> SUMM_OUT
    SUMM_OUT --> SUMMARIES_DB

    INPUT --> AC_IN
    AC_IN --> AC_MODEL
    AC_MODEL --> AC_OUT

    INPUT --> LOCAL
    LOCAL -->|"Sync"| DOCUMENTS_DB

    INPUT --> EXPORT_TXT
    INPUT --> EXPORT_DOCX
    INPUT --> EXPORT_PDF

    style SPELL fill:#EF4444,color:#fff
    style GRAMMAR fill:#F59E0B,color:#000
    style PUNCT fill:#3B82F6,color:#fff
    style SUMM_MODEL fill:#8B5CF6,color:#fff
    style AC_MODEL fill:#10B981,color:#fff
```

## Data Stores Summary

| Store | Type | Data | Access Pattern |
|-------|------|------|----------------|
| `localStorage` | Client-side | Draft HTML, dismissed words, word goal, theme | Read/write on every input |
| `documents` | Supabase | id, user_id, title, content, timestamps | CRUD per user (RLS) |
| `summaries` | Supabase | id, document_id, user_id, original, summary | Append-mostly |
| `settings` | Supabase | id, user_id, preferences JSON | Read on login, write on change |
| `profiles` | Supabase | id, display_name, avatar_url, auth_provider | Auto-created on signup |

## Data Transformation Chain

```
Raw Arabic Text
  │
  ├──→ AraSpell ──→ Corrected words (with alternatives)
  │         │
  │         ▼
  │    Grammar Engine ──→ Grammar errors (with suggestions)
  │         │
  │         ▼
  │    Punctuation ──→ Punctuation insertions
  │         │
  │         ▼
  │    Offset Mapper ──→ Maps corrected offsets → original offsets
  │         │
  │         ▼
  │    Unified Suggestions Array
  │         │
  │         ├──→ Error Spans (renderer.js)
  │         ├──→ Sidebar Cards (ui.js)
  │         └──→ Score Calculation
  │
  ├──→ AutoComplete Model ──→ Top-K word suggestions
  │
  └──→ MBart Summarizer ──→ Compressed summary text
```
