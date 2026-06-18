# 06 — Deployment Diagram

## Overview

BAYAN's final production deployment runs as a Dockerized Flask application on HuggingFace Spaces, with Supabase for database/auth and Google OAuth as an identity provider.

## Deployment Diagram

```mermaid
graph TB
    subgraph "User Environment"
        BROWSER["🌐 User Browser<br/>Chrome · Firefox · Safari"]
    end

    subgraph "GitHub"
        REPO["📦 GitHub Repository<br/>mohamedatef24/BAYAN"]
        CI["⚙️ GitHub Actions<br/>CI/CD Pipeline"]
    end

    subgraph "HuggingFace Spaces"
        subgraph "Docker Container (python:3.12-slim)"
            GUNICORN["Gunicorn<br/>WSGI Server<br/>1 Worker · Port 7860"]

            subgraph "Flask Application"
                FLASK_APP["Flask App<br/>CORS · Static Files"]
                
                subgraph "Static Assets"
                    HTML["index.html"]
                    CSS_DIR["css/<br/>main.css · components.css"]
                    JS_DIR["js/<br/>28 JS modules"]
                    VENDOR["vendor/<br/>docx.min.js · jspdf"]
                end

                subgraph "API Endpoints"
                    EP1["GET / — SPA Entry"]
                    EP2["GET /api/health"]
                    EP3["POST /api/analyze"]
                    EP4["POST /api/spelling"]
                    EP5["POST /api/grammar"]
                    EP6["POST /api/punctuation"]
                    EP7["POST /api/summarize"]
                    EP8["POST /api/autocomplete"]
                    EP9["GET /api/debug/models"]
                end
            end

            subgraph "NLP Models (Pre-cached)"
                M1["AraSpell<br/>AraBERT Encoder-Decoder<br/>+ last_model.pt checkpoint<br/>~220MB"]
                M2["Grammar Engine<br/>Rule-based + ML<br/>~50MB"]
                M3["PuncAra-v1<br/>Punctuation Model<br/>~100MB"]
                M4["AutoComplete<br/>Language Model<br/>~100MB"]
                M5["Summarization<br/>MBart (float16)<br/>~600MB"]
            end

            ML_LOADER["ModelLoader<br/>Lazy Init · Singleton"]
        end
    end

    subgraph "External Services"
        SUPABASE["🗄️ Supabase<br/>PostgreSQL + Auth + RLS<br/>ap-southeast-1"]
        GOOGLE["🔐 Google OAuth<br/>Identity Provider"]
        HF_HUB["🤗 HuggingFace Hub<br/>Model Registry"]
    end

    BROWSER -->|"HTTPS"| GUNICORN
    GUNICORN --> FLASK_APP
    FLASK_APP --> EP1 & EP2 & EP3 & EP4 & EP5 & EP6 & EP7 & EP8 & EP9
    EP3 & EP4 & EP5 & EP6 & EP7 & EP8 --> ML_LOADER
    ML_LOADER --> M1 & M2 & M3 & M4 & M5

    BROWSER -->|"Supabase JS SDK"| SUPABASE
    BROWSER -->|"OAuth Redirect"| GOOGLE
    GOOGLE -->|"Token"| SUPABASE

    REPO -->|"Push to main"| CI
    CI -->|"Deploy"| HF_HUB

    style GUNICORN fill:#059669,color:#fff
    style SUPABASE fill:#3B82F6,color:#fff
    style GOOGLE fill:#DB4437,color:#fff
    style ML_LOADER fill:#7C3AED,color:#fff
    style HF_HUB fill:#FF9D00,color:#fff
```

## Container Specifications

| Parameter | Value |
|-----------|-------|
| **Base Image** | `python:3.12-slim` |
| **Port** | `7860` |
| **WSGI Server** | Gunicorn (1 worker, 120s timeout) |
| **PyTorch** | CPU-only (saves ~1.5GB vs CUDA) |
| **Total Model Size** | ~1.07 GB |
| **Estimated RAM** | ~2.5 GB (peak during inference) |

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `SUPABASE_URL` | Database endpoint | HF Spaces Secrets |
| `SUPABASE_ANON_KEY` | Public API key | HF Spaces Secrets |
| `HF_API_TOKEN` | Remote inference fallback | HF Spaces Secrets |
| `SUMMARIZATION_REPO_ID` | Model repo path | Default: `bayan10/summarization-model` |
| `PORT` | Server port | Default: `7860` |
| `DEBUG` | Debug mode | Default: `False` |

## CI/CD Pipeline

```mermaid
graph LR
    A["Developer Push<br/>to main"] --> B["GitHub Actions<br/>Triggered"]
    B --> C["Lint & Validate<br/>Flask imports · Routes"]
    C --> D["Build Script<br/>Inject Supabase creds"]
    D --> E["Push to HF Spaces<br/>via git remote"]
    E --> F["Docker Build<br/>on HF Spaces"]
    F --> G["Pre-download Models<br/>During Build"]
    G --> H["Container Start<br/>Gunicorn"]
    H --> I["Health Check<br/>/api/health"]

    style A fill:#4F46E5,color:#fff
    style H fill:#059669,color:#fff
    style I fill:#22C55E,color:#fff
```

## Scaling Considerations

- **Single Worker**: Minimizes RAM; ML models are not thread-safe.
- **Model Pre-caching**: Docker builds download models once; no runtime network needed.
- **HF Inference Fallback**: When `HF_API_TOKEN` is set, uses remote HF Inference API to avoid local RAM limits.
- **Float16 Models**: Summarization model loaded in half-precision to halve memory.
