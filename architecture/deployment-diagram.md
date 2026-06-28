# Deployment Diagram — Bayan

> Infrastructure and deployment architecture on HuggingFace Spaces.

## Deployment Architecture

```mermaid
graph TB
    subgraph HFSpaces["HuggingFace Spaces"]
        subgraph DockerContainer["Docker Container (python:3.12-slim)"]
            subgraph Runtime["Runtime"]
                Gunicorn["Gunicorn\n1 worker, 300s timeout\nPort 7860"]
                Flask["Flask App\n(app.py)"]
            end

            subgraph ModelCache["Model Cache (/home/appuser/.cache)"]
                M1["AraSpell\n(AraBERT Enc-Dec)"]
                M2["Gemma 3\n(CausalLM)"]
                M3["PuncAra-v1\n(EncDec)"]
                M4["MBart\n(float16)"]
                M5["mT5\n(float16)"]
                M6["GPT-2"]
                CamelData["camel-tools data"]
            end

            subgraph StaticFiles["Static Files (/app/static)"]
                JSBundle["bayan.bundle.js"]
                CSS["styles.css"]
                Assets["images, fonts"]
            end

            subgraph Database["Embedded Database"]
                QuranDB["quran_master.db\n(SQLite, 6236 verses)"]
            end

            Gunicorn --> Flask
            Flask --> ModelCache
            Flask --> StaticFiles
            Flask --> Database
        end
    end

    subgraph ExternalServices["External Services"]
        Supabase["Supabase\n(Auth + PostgreSQL)"]
        HFHub["HuggingFace Hub\n(Model Downloads)"]
    end

    subgraph Clients["Clients"]
        Browser["Web Browser\n(SPA)"]
        Extension["Chrome Extension\n(MV3)"]
    end

    Browser -->|"HTTPS"| Gunicorn
    Extension -->|"HTTPS"| Gunicorn
    Flask -->|"Auth + CRUD"| Supabase
    DockerContainer -->|"Build-time\nmodel download"| HFHub
```

## Build Process

```mermaid
graph LR
    subgraph BuildStage["Docker Build"]
        Base["python:3.12-slim"]
        Deps["pip install\nrequirements.txt"]
        Models["Download models\nfrom HuggingFace Hub"]
        Camel["Copy camel-tools\ndata to appuser home"]
        Static["Copy static/\nto /app"]
        Copy["Copy src/\nto /app"]
    end

    subgraph RuntimeStage["Docker Run"]
        Env["ENV: PORT=7860\nHF_HOME=/home/appuser/.cache"]
        Start["CMD: gunicorn\n--bind 0.0.0.0:7860\n--timeout 300\n--workers 1"]
    end

    Base --> Deps --> Models --> Camel --> Static --> Copy --> Env --> Start
```

## Environment Configuration

| Variable | Value | Description |
|----------|-------|-------------|
| `PORT` | `7860` | HuggingFace Spaces required port |
| `HF_HOME` | `/home/appuser/.cache` | Model cache directory |
| `SUPABASE_URL` | (secret) | Supabase project URL |
| `SUPABASE_KEY` | (secret) | Supabase anon key |
| `GUNICORN_WORKERS` | `1` | Single worker (memory constraint) |
| `GUNICORN_TIMEOUT` | `300` | 5-minute timeout for large texts |

## Resource Requirements

| Resource | Specification |
|----------|--------------|
| RAM | ~8 GB (6 models loaded) |
| Disk | ~4 GB (models + dependencies) |
| CPU | Multi-core recommended |
| GPU | Not required (CPU inference) |
| Network | Outbound HTTPS to Supabase |
