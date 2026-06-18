# 11 — Final Production Architecture

## Overview

This document represents the **FINAL production architecture** of BAYAN, with all five NLP modules fully deployed, integrated, and operational inside a single Docker container on HuggingFace Spaces.

## Production Architecture

```mermaid
graph TB
    subgraph "Client (Browser)"
        BROWSER["🌐 Browser<br/>HTML5 + CSS3 + ES6"]
        
        subgraph "Frontend SPA"
            LANDING["Landing Page"]
            FEATURES["Features Page"]
            EDITOR_PG["Editor Page"]
            PRICING["Pricing Page"]
            AUTH_GATE["Auth Gate"]
        end

        subgraph "Editor Engine"
            EDIT["editor.js — State & Analysis"]
            REND["renderer.js — Highlights"]
            SEL["selection.js — Caret"]
            FMT["format.js — Rich Text"]
        end

        subgraph "Client Services"
            AUTH_SVC["Auth Service"]
            DOC_SVC["Document Manager"]
            SYNC_SVC["Sync Engine"]
            SUMM_SVC["Summary Manager"]
            SET_SVC["Settings Manager"]
            EXPORT_SVC["Export (TXT/DOCX/PDF)"]
        end
    end

    subgraph "HuggingFace Spaces"
        subgraph "Docker: python:3.12-slim"
            subgraph "Gunicorn (Port 7860, 1 Worker)"
                subgraph "Flask Application"
                    STATIC["Static File Server<br/>HTML · CSS · JS · Assets"]

                    subgraph "REST API"
                        HEALTH["GET /api/health<br/>Status + Model Readiness"]
                        ANALYZE["POST /api/analyze<br/>Full Pipeline: Spell→Grammar→Punct"]
                        SPELL_EP["POST /api/spelling<br/>AraSpell Only"]
                        GRAMMAR_EP["POST /api/grammar<br/>Grammar Only"]
                        PUNCT_EP["POST /api/punctuation<br/>Punctuation Only"]
                        SUMM_EP["POST /api/summarize<br/>MBart Summarization"]
                        AUTO_EP["POST /api/autocomplete<br/>Word Completion"]
                        DEBUG["GET /api/debug/models<br/>Model Status"]
                    end
                end

                subgraph "Model Loader (Singleton)"
                    LOADER["ModelLoader<br/>Lazy Init · Error Recovery"]
                end

                subgraph "NLP Models (Pre-cached in Docker)"
                    ARASPELL["🔴 AraSpell<br/>AraBERT Encoder-Decoder<br/>+ last_model.pt<br/>+ ContextualCorrector (MLM)<br/>~220 MB"]
                    GRAMMAR["🟡 Bayan Grammar<br/>Rule Engine + ML<br/>~50 MB"]
                    PUNCTUATION["🔵 PuncAra-v1<br/>Sequence Labeling<br/>~100 MB"]
                    AUTOCOMPLETE["🟢 AutoComplete<br/>Language Model<br/>~100 MB"]
                    SUMMARIZATION["🟣 Summarization<br/>MBart (float16)<br/>~600 MB"]
                end

                subgraph "HF Inference Fallback"
                    HF_REMOTE["hf_inference.py<br/>Remote API when RAM limited"]
                end
            end
        end
    end

    subgraph "External Services"
        SUPABASE["🗄️ Supabase Cloud<br/>PostgreSQL + Auth + RLS"]
        GOOGLE_OAUTH["🔐 Google OAuth 2.0"]
        GITHUB["📦 GitHub<br/>Source Control"]
        GH_ACTIONS["⚙️ GitHub Actions<br/>CI/CD Pipeline"]
        HF_HUB["🤗 HuggingFace Hub<br/>Model Registry"]
    end

    %% Client to Server
    BROWSER --> STATIC
    EDIT -->|"POST"| ANALYZE
    EDIT -->|"POST"| AUTO_EP
    SUMM_SVC -->|"POST"| SUMM_EP

    %% API to Models
    ANALYZE --> LOADER
    SPELL_EP --> LOADER
    GRAMMAR_EP --> LOADER
    PUNCT_EP --> LOADER
    SUMM_EP --> LOADER
    AUTO_EP --> LOADER

    LOADER --> ARASPELL
    LOADER --> GRAMMAR
    LOADER --> PUNCTUATION
    LOADER --> AUTOCOMPLETE
    LOADER --> SUMMARIZATION
    LOADER -.->|"Fallback"| HF_REMOTE

    %% Client to External
    AUTH_SVC -->|"Supabase SDK"| SUPABASE
    DOC_SVC --> SUPABASE
    SYNC_SVC --> SUPABASE
    SUMM_SVC --> SUPABASE
    SET_SVC --> SUPABASE
    AUTH_SVC -->|"OAuth"| GOOGLE_OAUTH

    %% Infrastructure
    GITHUB --> GH_ACTIONS
    GH_ACTIONS -->|"Deploy"| HF_HUB

    %% Styling
    style ARASPELL fill:#EF4444,color:#fff
    style GRAMMAR fill:#F59E0B,color:#000
    style PUNCTUATION fill:#3B82F6,color:#fff
    style AUTOCOMPLETE fill:#10B981,color:#fff
    style SUMMARIZATION fill:#8B5CF6,color:#fff
    style LOADER fill:#7C3AED,color:#fff
    style SUPABASE fill:#3B82F6,color:#fff
    style GOOGLE_OAUTH fill:#DB4437,color:#fff
```

## Resource Budget

| Resource | Allocation | Notes |
|----------|-----------|-------|
| **RAM** | ~2.5 GB peak | 5 models loaded simultaneously |
| **Disk** | ~1.07 GB models + ~500 MB system | Pre-cached during Docker build |
| **CPU** | 2 vCPU (HF Spaces) | Single Gunicorn worker |
| **Network** | None at runtime | Models pre-downloaded |
| **Cold Start** | ~30-60 seconds | Model lazy loading |

## API Endpoint Summary

| Endpoint | Method | Purpose | Model(s) Used |
|----------|--------|---------|--------------|
| `/` | GET | Serve SPA + inject Supabase creds | — |
| `/api/health` | GET | Health check + model status | All (status check) |
| `/api/analyze` | POST | Full NLP pipeline | AraSpell → Grammar → Punctuation |
| `/api/spelling` | POST | Spelling correction only | AraSpell |
| `/api/grammar` | POST | Grammar check only | Grammar |
| `/api/punctuation` | POST | Punctuation restoration only | PuncAra-v1 |
| `/api/summarize` | POST | Text summarization | MBart |
| `/api/autocomplete` | POST | Word completion | AutoComplete |
| `/api/debug/models` | GET | Model debug info | All |

## Production Hardening

| Feature | Implementation |
|---------|---------------|
| **Error Recovery** | ModelLoader catches load failures; API returns 503 with details |
| **Timeout** | Gunicorn 120s timeout for long summarizations |
| **CORS** | Restricted to `/api/*` routes only |
| **Input Validation** | Max 5000 chars, min 10 chars for summarization |
| **Startup Errors** | Captured in `_startup_errors` array, exposed via `/api/health` |
| **HF Fallback** | Auto-routes to HF Inference API when `HF_API_TOKEN` is set |
| **Model Caching** | All models downloaded during `docker build`, not at runtime |
