# System Architecture — Bayan

> High-level component diagram showing all major subsystems and their relationships.

## Overview

Bayan is an Arabic writing assistant composed of three main subsystems:
1. **Flask Backend** — NLP pipeline with 6 ML models, REST API
2. **Web Frontend** — Single-page application served by Flask
3. **Chrome Extension** — Manifest V3 extension with inline analysis and side panel

```mermaid
graph TB
    subgraph Users["Users"]
        WebUser["Web App User"]
        ExtUser["Extension User"]
    end

    subgraph Frontend["Web Frontend (SPA)"]
        HTML["index.html"]
        JSBundle["bayan.bundle.js<br/>(33 modules bundled)"]
        Editor["Rich Text Editor"]
        AuthUI["Auth UI (Supabase)"]
        DocMgr["Document Manager"]
    end

    subgraph Extension["Chrome Extension (MV3)"]
        BG["background.js<br/>(Service Worker)"]
        CS["content-inline.js<br/>(Content Script)"]
        SP["sidepanel.js<br/>(Side Panel)"]
        Popup["popup.js<br/>(Popup)"]
        Shared["shared/<br/>(constants, config, API,<br/>renderer, patches, UI)"]
    end

    subgraph Backend["Flask Backend (src/)"]
        App["app.py<br/>(Flask + CORS + Rate Limit)"]
        Routes["routes/<br/>core.py, nlp.py"]
        Services["services/<br/>analysis_pipeline.py"]
        Pipeline["PipelineContext<br/>+ PatchSet + StageLocker"]

        subgraph Models["NLP Models (6)"]
            Spelling["AraSpell<br/>(AraBERT Enc-Dec)"]
            Grammar["Grammar<br/>(Gemma 3 + camel-tools)"]
            Punctuation["PuncAra-v1<br/>(EncoderDecoder)"]
            Summarization["Summarization<br/>(MBart, float16)"]
            Dialect["Dialect→MSA<br/>(mT5, float16)"]
            Autocomplete["Autocomplete<br/>(GPT-2)"]
        end
    end

    subgraph External["External Services"]
        Supabase["Supabase<br/>(Auth + DB)"]
        HFHub["HuggingFace Hub<br/>(Model Registry)"]
        QuranDB["quran_master.db<br/>(SQLite)"]
    end

    subgraph Deployment["Deployment"]
        Docker["Docker Container<br/>(python:3.12-slim)"]
        Gunicorn["Gunicorn<br/>(1 worker, 300s timeout)"]
        HFSpaces["HuggingFace Spaces<br/>(Hosting)"]
    end

    WebUser --> Frontend
    ExtUser --> Extension

    Frontend -->|"REST API"| Backend
    Extension -->|"REST API"| Backend
    AuthUI -->|"Auth"| Supabase
    DocMgr -->|"CRUD"| Supabase

    App --> Routes
    Routes --> Services
    Services --> Pipeline
    Pipeline --> Models

    Routes -->|"/api/quran"| QuranDB
    Backend -->|"Model download<br/>(build time)"| HFHub

    Docker --> Gunicorn
    Gunicorn --> App
    HFSpaces --> Docker

    CS <-->|"chrome.runtime<br/>.sendMessage"| BG
    SP <-->|"chrome.runtime<br/>.sendMessage"| BG
    BG <-->|"chrome.tabs<br/>.sendMessage"| CS
    SP --> Shared
    CS --> Shared
```

## API Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/api/analyze` | POST | 30/min | Unified pipeline: Spelling → Grammar → Punctuation |
| `/api/spelling` | POST | 30/min | Standalone spelling correction |
| `/api/grammar` | POST | 30/min | Standalone grammar correction |
| `/api/punctuation` | POST | 30/min | Standalone punctuation restoration |
| `/api/summarize` | POST | 10/min | Arabic text summarization |
| `/api/dialect` | POST | 10/min | Dialect → MSA conversion |
| `/api/quran` | POST | 20/min | Quran verse verification + translation |
| `/api/autocomplete` | POST | 60/min | Next-word prediction |
| `/api/health` | GET | — | Model status check |
| `/api/config` | GET | 30/min | Public Supabase config |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Flask 3.x + Flask-CORS + Flask-Limiter |
| ML Framework | PyTorch (CPU-only) + HuggingFace Transformers |
| NLP Libraries | camel-tools (Arabic morphology), AraBERT tokenizer |
| Database | Supabase (PostgreSQL), SQLite (Quran) |
| Authentication | Supabase Auth (JWT) |
| Deployment | Docker, Gunicorn, HuggingFace Spaces |
| Extension | Chrome Manifest V3, Service Worker, Side Panel API |
| Frontend | Vanilla JS (ES6+), CSS3, no framework |
