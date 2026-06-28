# Use Case Diagram — Bayan

> All user interactions with the system across web app and Chrome extension.

## 1. Web App Use Cases

```mermaid
graph LR
    EndUser["End User"]
    AuthUser["Authenticated User"]
    Dev["Developer / Maintainer"]

    subgraph BayanSystem["Bayan System (Web App)"]
        UC_Analyze(["Analyze Text"])
        UC_Apply(["Apply / Dismiss\nSuggestion"])
        UC_Summarize(["Summarize Text"])
        UC_Autocomplete(["Autocomplete"])
        UC_Dialect(["Dialect to MSA"])
        UC_Quran(["Verify Quran Verse"])
        UC_QuranTranslate(["Translate Quran Verse"])
        UC_Auth(["Authenticate"])
        UC_Bayena(["Ask Bayena\n(Islamic QA)"])
        UC_Edit(["Edit Text in\nRich Editor"])
        UC_Suggestions(["View Inline\nSuggestions"])
        UC_Export(["Export as\nPDF / TXT / DOCX"])
        UC_Import(["Import Document"])
        UC_Docs(["Manage Documents"])
        UC_Sync(["Sync / Offline\nRecovery"])
        UC_Health(["Inspect Health /\nModels"])
    end

    EXT_HF["Hugging Face\nModels / Inference"]
    EXT_Supa["Supabase\n(Auth + Database)"]
    EXT_RAG["Bayena\n(RAG Subsystem)"]

    EndUser --> UC_Analyze
    EndUser --> UC_Summarize
    EndUser --> UC_Autocomplete
    EndUser --> UC_Dialect
    EndUser --> UC_Quran
    EndUser --> UC_Auth
    EndUser --> UC_Bayena
    EndUser --> UC_Edit
    EndUser --> UC_Suggestions
    EndUser --> UC_Apply
    EndUser --> UC_Export
    EndUser --> UC_Import

    AuthUser --> UC_Docs
    AuthUser --> UC_Sync

    Dev --> UC_Health

    UC_Analyze -.->|"include"| UC_Apply
    UC_Quran -.->|"include"| UC_QuranTranslate
    UC_Docs -.->|"extend"| UC_Sync

    UC_Analyze --> EXT_HF
    UC_Summarize --> EXT_HF
    UC_Dialect --> EXT_HF
    UC_Autocomplete --> EXT_HF
    UC_Auth --> EXT_Supa
    UC_Docs --> EXT_Supa
    UC_Sync --> EXT_Supa
    UC_Bayena --> EXT_RAG
```

## 2. Chrome Extension Use Cases

```mermaid
graph LR
    ExtUser["Extension User"]

    subgraph BayanSystem["Bayan System (Chrome Extension)"]
        UC_ContextMenu(["Right-Click\nCorrect Selection"])
        UC_InlineAnalysis(["Inline Analysis\non Any Webpage"])
        UC_SidePanel(["View Results\nin Side Panel"])
        UC_WriteBack(["Apply Corrections\nto Page"])
        UC_FAB(["Quick Analysis\nvia FAB"])
        UC_Analyze(["Analyze Text"])
        UC_Summarize(["Summarize Text"])
        UC_Dialect(["Dialect to MSA"])
        UC_Quran(["Verify Quran Verse"])
        UC_Autocomplete(["Autocomplete"])
    end

    EXT_HF["Hugging Face\nModels / Inference"]

    ExtUser --> UC_ContextMenu
    ExtUser --> UC_InlineAnalysis
    ExtUser --> UC_SidePanel
    ExtUser --> UC_WriteBack
    ExtUser --> UC_FAB
    ExtUser --> UC_Analyze
    ExtUser --> UC_Summarize
    ExtUser --> UC_Dialect
    ExtUser --> UC_Quran
    ExtUser --> UC_Autocomplete

    UC_Analyze --> EXT_HF
    UC_Summarize --> EXT_HF
    UC_Dialect --> EXT_HF
    UC_Autocomplete --> EXT_HF
```

## Use Case Details

| # | Use Case | Actor | API Endpoint | Description |
|---|----------|-------|-------------|-------------|
| 1 | Correct Text | Both | `POST /api/analyze` | Runs unified 3-stage pipeline (Spelling, Grammar, Punctuation) |
| 2 | Correct Spelling | Both | `POST /api/spelling` | Standalone AraSpell correction |
| 3 | Correct Grammar | Both | `POST /api/grammar` | Standalone Gemma 3 + camel-tools correction |
| 4 | Add Punctuation | Both | `POST /api/punctuation` | Standalone PuncAra-v1 punctuation restoration |
| 5 | Summarize Text | Both | `POST /api/summarize` | MBart-based Arabic summarization (3 lengths) |
| 6 | Convert Dialect | Both | `POST /api/dialect` | mT5-based dialect-to-MSA conversion |
| 7 | Verify Quran | Both | `POST /api/quran` | Search in quran_master.db (SQLite) |
| 8 | Translate Quran | Both | `POST /api/quran` | Get verse translation (language param) |
| 9 | Autocomplete | Both | `POST /api/autocomplete` | GPT-2 next-word prediction |
| 10 | Edit Text | Web | — | Rich text editor in SPA |
| 11 | View Suggestions | Web | — | Inline highlighted suggestions |
| 12 | Apply/Reject | Web | — | Per-suggestion accept/reject |
| 13 | Export | Web | — | PDF, TXT, DOCX generation client-side |
| 14 | Import | Web | — | Load text/HTML/DOCX files |
| 15 | Manage Docs | Web | Supabase | Create, read, update, delete documents |
| 16 | Sync to Cloud | Web | Supabase | Real-time document sync |
| 17 | Auth | Web | Supabase | Email/password authentication |
| 20 | Context Menu | Ext | — | Right-click selected text, analyze |
| 21 | Inline Analysis | Ext | — | Auto-analyze on typing in text fields |
| 22 | Side Panel | Ext | — | Persistent workspace for all features |
| 23 | Write Back | Ext | — | Apply corrections directly to page content |
| 24 | FAB | Ext | — | Floating action button for quick access |
