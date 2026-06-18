# 01 — High-Level System Architecture

## Overview

BAYAN is a full-stack Arabic NLP web application that provides intelligent writing assistance: spelling correction (AraSpell), grammar checking, punctuation restoration (PuncAra-v1), autocomplete suggestions, and text summarization. The system is deployed as a containerized Flask application on HuggingFace Spaces, with Supabase as the backend database and Google OAuth for authentication.

## Architecture Diagram

```mermaid
graph TD
    subgraph "Client Layer"
        U["👤 User (Browser)"]
        UI["UI Layer<br/>Landing · Features · Editor · Pricing"]
        EDITOR["Editor Engine<br/>editor.js · renderer.js · selection.js"]
        AUTH["Auth Module<br/>Guest · Google OAuth · Supabase Auth"]
        SYNC["Sync Engine<br/>SyncManager · SyncQueue · SyncResolver"]
        DOCS["Documents Manager<br/>documents-api · documents-ui"]
        SUMM_UI["Summaries UI<br/>summaries-api · summaries-ui"]
        SETTINGS["Settings Sync<br/>settings-api · settings-sync"]
        EXPORT["Export System<br/>TXT · DOCX · PDF"]
    end

    subgraph "API Layer (Flask)"
        API["Flask REST API<br/>Gunicorn · CORS"]
        HEALTH["/api/health"]
        ANALYZE["/api/analyze"]
        SPELL["/api/spelling"]
        GRAMMAR["/api/grammar"]
        PUNCT["/api/punctuation"]
        SUMMARY["/api/summarize"]
        AUTOCOMPLETE["/api/autocomplete"]
    end

    subgraph "NLP Layer (Models)"
        ML["ModelLoader"]
        ARASPELL["AraSpell<br/>AraBERT Encoder-Decoder"]
        GRAM_MODEL["Bayan Grammar<br/>Grammar Rules Engine"]
        PUNC_MODEL["PuncAra-v1<br/>Punctuation Restoration"]
        AUTO_MODEL["AutoComplete<br/>Language Model"]
        SUMM_MODEL["Summarization<br/>MBart Fine-tuned"]
    end

    subgraph "Data Layer"
        SUPA["Supabase (PostgreSQL)"]
        PROFILES["profiles"]
        DOCUMENTS["documents"]
        SUMMARIES["summaries"]
        SETTINGS_DB["settings"]
        LOCAL["localStorage<br/>Drafts · Dismissed Words"]
    end

    subgraph "Infrastructure"
        HF["HuggingFace Spaces"]
        DOCKER["Docker Container"]
        GH["GitHub Repository"]
        CI["GitHub Actions CI/CD"]
        GOOGLE["Google OAuth Provider"]
    end

    U --> UI
    UI --> EDITOR
    UI --> AUTH
    EDITOR --> SYNC
    EDITOR --> DOCS
    EDITOR --> SUMM_UI
    EDITOR --> SETTINGS
    EDITOR --> EXPORT

    EDITOR -->|"POST /api/analyze"| API
    SUMM_UI -->|"POST /api/summarize"| API
    AUTH -->|"Supabase SDK"| SUPA

    API --> HEALTH
    API --> ANALYZE
    API --> SPELL
    API --> GRAMMAR
    API --> PUNCT
    API --> SUMMARY
    API --> AUTOCOMPLETE

    ANALYZE --> ML
    SPELL --> ML
    GRAMMAR --> ML
    PUNCT --> ML
    SUMMARY --> ML
    AUTOCOMPLETE --> ML

    ML --> ARASPELL
    ML --> GRAM_MODEL
    ML --> PUNC_MODEL
    ML --> AUTO_MODEL
    ML --> SUMM_MODEL

    SYNC --> SUPA
    DOCS --> SUPA
    SUMM_UI --> SUPA
    SETTINGS --> SUPA

    SUPA --> PROFILES
    SUPA --> DOCUMENTS
    SUPA --> SUMMARIES
    SUPA --> SETTINGS_DB

    EDITOR --> LOCAL

    HF --> DOCKER
    DOCKER --> API
    GH --> CI
    CI -->|"Deploy"| HF
    AUTH --> GOOGLE

    style U fill:#4F46E5,stroke:#312E81,color:#fff
    style API fill:#059669,stroke:#064E3B,color:#fff
    style SUPA fill:#3B82F6,stroke:#1E3A8A,color:#fff
    style HF fill:#FF9D00,stroke:#92400E,color:#fff
    style ML fill:#7C3AED,stroke:#4C1D95,color:#fff
```

## Layer Descriptions

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| **Client** | HTML/CSS/JS SPA | User interface, editor, auth gate, document management |
| **API** | Flask + Gunicorn | REST endpoints, request validation, model orchestration |
| **NLP** | 5 ML models | Spelling, grammar, punctuation, autocomplete, summarization |
| **Data** | Supabase + localStorage | Persistent storage, auth, offline drafts |
| **Infrastructure** | Docker + HF Spaces + CI | Containerization, deployment, monitoring |

## Design Rationale

1. **Single-Page Application (SPA)**: No framework overhead — pure HTML/CSS/JS for minimal bundle size and fast load.
2. **Flask API**: Lightweight Python backend, ideal for ML model serving.
3. **Supabase**: Managed PostgreSQL with built-in auth, RLS, and realtime — eliminates custom backend for CRUD.
4. **Docker**: Ensures model dependencies are pre-cached at build time (no runtime downloads).
5. **HuggingFace Spaces**: Free GPU/CPU hosting optimized for ML model serving.

## Extension Points

- Additional NLP models can be added via `ModelLoader` without changing the API structure.
- New Supabase tables follow the same RLS pattern.
- Frontend pages follow a `showPage()` pattern for easy addition.
