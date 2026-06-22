# Chapter 3: System Design and Architecture

## 3.1 Overview

The Bayan system is a distributed, multi-tier architecture comprising four principal components: (1) a Python/Flask backend providing RESTful API endpoints for NLP model inference, (2) a single-page web application (SPA) frontend for direct text analysis, (3) a Chrome Manifest V3 browser extension for in-browser writing assistance, and (4) cloud infrastructure for deployment, authentication, and data persistence. This chapter presents the architectural design of each component, the data flow between components, and the key design decisions that shaped the system.

## 3.2 High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB["Web Application<br/>(index.html + JS modules)"]
        EXT_POPUP["Chrome Extension<br/>Popup UI"]
        EXT_SIDE["Chrome Extension<br/>Side Panel"]
        EXT_INLINE["Chrome Extension<br/>Inline Analysis Engine"]
    end

    subgraph "Extension Architecture"
        BG["Service Worker<br/>(background.js)"]
        CS["Content Script<br/>(content-inline.js)"]
        SHARED["Shared Modules<br/>(analysis-controller, bayan-api,<br/>bayan-patches, bayan-renderer,<br/>bayan-state, bayan-ui)"]
    end

    subgraph "Backend Layer"
        FLASK["Flask API Server<br/>(app.py)"]
        subgraph "NLP Pipeline"
            SPELL["Spelling<br/>(AraSpell)"]
            GRAM["Grammar<br/>(Gemma 3 + CAMeL)"]
            PUNC["Punctuation<br/>(PuncAra-v1)"]
            SUMM["Summarization<br/>(mBART)"]
            AUTO["Autocomplete<br/>(Bigram + AraGPT2)"]
            DIAL["Dialect<br/>(mT5)"]
            QURAN["Quran Search<br/>(SQLite)"]
        end
        ML["Model Loader<br/>(model_loader.py)"]
        HF["HF Inference<br/>Fallback"]
    end

    subgraph "Data Layer"
        SUPA["Supabase<br/>(Auth + Documents)"]
        SQLITE["quran_master.db<br/>(SQLite ~22MB)"]
        HFHUB["HuggingFace Hub<br/>(Model Weights)"]
    end

    WEB -->|"HTTP/JSON"| FLASK
    EXT_POPUP -->|"chrome.runtime.sendMessage"| BG
    EXT_SIDE -->|"chrome.runtime.sendMessage"| BG
    EXT_INLINE -->|"Content Script"| CS
    CS -->|"chrome.runtime.sendMessage"| BG
    BG -->|"fetch() proxy"| FLASK
    SHARED -.->|"imported by"| EXT_POPUP
    SHARED -.->|"imported by"| EXT_SIDE
    SHARED -.->|"imported by"| CS

    FLASK --> SPELL
    FLASK --> GRAM
    FLASK --> PUNC
    FLASK --> SUMM
    FLASK --> AUTO
    FLASK --> DIAL
    FLASK --> QURAN
    FLASK --> ML
    FLASK --> HF

    WEB -->|"Supabase JS Client"| SUPA
    QURAN --> SQLITE
    ML --> HFHUB
```

## 3.3 Backend Architecture

### 3.3.1 Flask API Server

The backend is a Flask application (`src/app.py`, 1,717 lines) that exposes RESTful API endpoints for all NLP operations. The server is designed to run under Gunicorn with a single worker process to minimize RAM consumption on the free-tier HuggingFace Spaces deployment (16GB RAM limit).

**API Endpoints:**

| Endpoint | Method | Purpose | Model |
|---|---|---|---|
| `/api/health` | GET | Health check and model status | — |
| `/api/debug-models` | GET | Debug model loading diagnostics | — |
| `/api/spelling` | POST | Standalone spelling correction | AraSpell |
| `/api/grammar` | POST | Standalone grammar correction | Gemma 3 |
| `/api/punctuation` | POST | Standalone punctuation restoration | PuncAra-v1 |
| `/api/summarize` | POST | Text summarization | mBART |
| `/api/autocomplete` | POST | Next-word prediction | Bigram + AraGPT2 |
| `/api/dialect` | POST | Dialect-to-MSA conversion | mT5 |
| `/api/quran` | POST | Quranic text verification | SQLite |
| `/api/analyze` | POST | Multi-stage sequential analysis | AraSpell → Gemma 3 → PuncAra |

### 3.3.2 Model Loading Strategy

The model loading strategy (`src/model_loader.py`, 904 lines) is designed to handle the constraints of the free-tier deployment:

```mermaid
flowchart TD
    START["Server Startup"] --> CHECK["HF_API_TOKEN set?"]
    CHECK -->|"Yes"| HF_MODE["HF API Mode"]
    CHECK -->|"No"| LOCAL["Local Model Mode"]

    HF_MODE --> LOAD_SUMM["Load Summarization<br/>(mBART, always local)"]
    HF_MODE --> LAZY_SPELL["Lazy-load Spelling<br/>(on first request)"]
    HF_MODE --> LAZY_GRAM["Lazy-load Grammar<br/>(on first request)"]
    HF_MODE --> LAZY_PUNC["Lazy-load Punctuation<br/>(on first request)"]

    LOCAL --> LOAD_ALL["Load All Models<br/>(Summarization, Spelling,<br/>Grammar, Punctuation)"]

    LOAD_SUMM --> TRY_REMOTE["Try HF Hub Remote"]
    TRY_REMOTE -->|"Success"| READY["Model Ready"]
    TRY_REMOTE -->|"Fail"| TRY_LOCAL["Fallback to Local Path"]
    TRY_LOCAL --> READY
```

**Key Design Decisions:**

1. **Lazy Loading**: Spelling, grammar, punctuation, autocomplete, and dialect models are loaded on first request (singleton pattern), not at server startup. This avoids blocking the health check endpoint and reduces cold-start time.

2. **CPU-Only Inference**: All models run on CPU (`torch.device('cpu')`) in production. The grammar model explicitly forces CPU even when CUDA is available, to avoid GPU OOM on shared infrastructure.

3. **Float16 Precision**: Summarization and dialect models use `torch.float16` to halve memory consumption. Grammar uses `torch.float32` for stability on CPU.

4. **Pre-Downloaded Models**: The Dockerfile pre-downloads all model weights during the Docker build phase, caching them in the HuggingFace Hub local cache. At runtime, the container has no outbound DNS, so models must be available locally.

### 3.3.3 The `/api/analyze` Pipeline

The `/api/analyze` endpoint is the most architecturally complex component of the backend. It orchestrates a three-stage sequential pipeline: Spelling → Grammar → Punctuation. Each stage's output feeds into the next stage's input, and a sophisticated coordinate mapping system tracks character offsets through text mutations to produce suggestions aligned with the user's original input.

```mermaid
sequenceDiagram
    participant Client
    participant Flask as Flask /api/analyze
    participant Ctx as PipelineContext
    participant Spell as AraSpell
    participant Gram as Gemma 3 + CAMeL
    participant Punc as PuncAra-v1

    Client->>Flask: POST {text: "user input"}
    Flask->>Ctx: PipelineContext(original_text)
    Note over Ctx: original_text = IMMUTABLE

    rect rgb(230, 245, 255)
        Flask->>Spell: spell_checker.correct(current_text)
        Spell-->>Flask: corrected text
        Flask->>Flask: Word-level diff analysis
        Flask->>Flask: Filter: _is_small_spelling_change()
        Flask->>Ctx: ctx.add_patch('spelling', ...)
        Flask->>Ctx: ctx.mutate_text(safe_text, OffsetMapper)
        Note over Ctx: StageLocker locks spelling spans
    end

    rect rgb(255, 245, 230)
        Flask->>Gram: grammar_checker.correct(current_text)
        Gram-->>Flask: corrected text
        Flask->>Flask: Word-level diff (get_word_diffs)
        Flask->>Flask: StageLocker check (skip locked spans)
        Flask->>Flask: Hallucination filter (Jaccard < 0.3)
        Flask->>Flask: IV→OOV corruption guard
        Flask->>Ctx: ctx.add_patch('grammar', ...)
        Flask->>Ctx: ctx.mutate_text(corrected, OffsetMapper)
    end

    rect rgb(245, 255, 230)
        Flask->>Punc: punc_checker.correct(current_text)
        Punc-->>Flask: punctuated text
        Flask->>Flask: Word-level diff
        Flask->>Flask: StageLocker check (allow pure punct)
        Flask->>Flask: validate_punctuation_diff()
        Flask->>Ctx: ctx.add_patch('punctuation', ...)
        Flask->>Flask: Cap at 3 punctuation patches
        Flask->>Ctx: ctx.mutate_text(punctuated, OffsetMapper)
    end

    Flask->>Ctx: ctx.patches.to_list() (overlap resolution)
    Flask->>Flask: _apply_patches_to_original()
    Flask-->>Client: {original, corrected, suggestions[], timing_ms}
```

## 3.4 Pipeline Hardening Architecture

### 3.4.1 PipelineContext

The `PipelineContext` class (`src/nlp/pipeline_context.py`) carries all shared state through the three-stage pipeline. It enforces the following invariants:

1. **`original_text` is IMMUTABLE** — never reassigned after construction.
2. **`_offset_mappers` is APPEND-ONLY** — past mappers are never mutated or removed.
3. **`map_to_original()` is READ-ONLY** — deterministic coordinate transforms.
4. **All coordinate transforms go through `OffsetMapper` public API** — no direct access to internal opcodes.

### 3.4.2 CorrectionPatch and PatchSet

The `CorrectionPatch` dataclass (`src/nlp/correction_patch.py`) represents a single correction suggestion with dual coordinate spaces:

- **ORIGINAL coordinates** (`start_original`, `end_original`): Used for API response and overlap resolution. These coordinates refer to the user's original input text.
- **CURRENT coordinates** (`start_current`, `end_current`): Used by the `StageLocker` for pipeline-internal range checking. These coordinates refer to the pipeline's working copy, which is mutated by each stage.

The `PatchSet` class implements deterministic overlap resolution using a greedy first-fit strategy:

```
Sort order: priority DESC → confidence DESC → start ASC → id ASC
Strategy: First non-overlapping patch wins its range. One range = one owner.
```

**Priority hierarchy:**

| Stage | Priority |
|---|---|
| Grammar | 3 (highest) |
| Punctuation | 2 |
| Spelling | 1 |
| Autocomplete | 0 (lowest) |

### 3.4.3 OffsetMapper

The `OffsetMapper` class (`src/app.py`) provides bidirectional coordinate transformation between consecutive text versions using `difflib.SequenceMatcher`:

- **`reverse_map_offset(pos)`**: Maps a position from `text_after` → `text_before` (used to walk back to original coordinates).
- **`forward_map_range(start, end)`**: Maps a range from `text_before` → `text_after` (used by `StageLocker` to update locked spans after mutations).
- **Monotonicity guard**: If independent point mapping produces an inverted range (start > end), the end is clamped to `max(new_start, new_end)`.

### 3.4.4 StageLocker

The `StageLocker` (`src/nlp/stage_locker.py`) prevents later pipeline stages from modifying text ranges that were already corrected by earlier stages. When the spelling stage corrects a word, the `StageLocker` locks that character range. When the grammar stage subsequently proposes a correction overlapping with a locked range, the correction is rejected (unless it is a pure punctuation change).

```mermaid
flowchart LR
    SPELL["Spelling corrects<br/>'هذة' → 'هذه'<br/>at [10:14]"]
    LOCK["StageLocker.lock(10, 14, 'spelling')"]
    GRAM["Grammar proposes<br/>change at [10:14]"]
    CHECK["StageLocker.is_locked(10, 14)?"]
    BLOCK["BLOCKED ✗"]

    SPELL --> LOCK
    GRAM --> CHECK
    CHECK -->|"Yes"| BLOCK
```

## 3.5 NLP Model Architecture

### 3.5.1 AraSpell Spelling Correction Pipeline

```mermaid
flowchart TD
    INPUT["Input Text"] --> PREPROCESS["Preprocessing<br/>• Remove diacritics<br/>• Remove tatweel<br/>• Normalize special chars<br/>• Collapse repeated chars<br/>• Fix char substitutions"]
    PREPROCESS --> CLASSIFY["Error Classification<br/>• CHAR_REPETITION<br/>• WORD_MERGE<br/>• CHAR_SUBSTITUTION<br/>• MIXED<br/>• CLEAN"]
    CLASSIFY --> RULES["Rules-Based Correction<br/>• Keyboard proximity<br/>• Recursive word splitting<br/>• Fragment joining"]
    RULES --> MODEL["Neural Correction<br/>• AraBERT Encoder-Decoder<br/>• Beam search (num_beams=5)<br/>• max_length=128"]
    MODEL --> VALIDATE["Output Validation<br/>• Length ratio check<br/>• Character preservation (Jaccard)<br/>• Word count check<br/>• Hallucination detection"]
    VALIDATE --> ALIGN["Word Alignment<br/>• IV/OOV-based word selection<br/>• Hybrid word construction<br/>• ه→ة preference for IV-IV"]
    ALIGN --> CONTEXT["Contextual Refinement<br/>• BERT MLM reranking<br/>• Top-k mask filling<br/>• Vocabulary validation"]
    CONTEXT --> POST["Post-Processing<br/>• Remove hallucinations<br/>• Fix hamza (whitelist)<br/>• Fix ta marbuta<br/>• Merge fragments<br/>• Normalize spaces"]
    POST --> OUTPUT["Corrected Text"]
```

**Architecture details of AraSpell:**

| Component | Class | Lines |
|---|---|---|
| Post-Processor | `AraSpellPostProcessor` | ~360 |
| Error Classifier | `ErrorClassifier` | ~40 |
| Rules-Based Corrector | `RulesBasedCorrector` | ~100 |
| Output Validator | `OutputValidator` | ~60 |
| Vocabulary Manager | `VocabularyManager` | ~80 |
| Word Aligner | `WordAligner` | ~65 |
| Split/Merge Specialist | `SplitMergeSpecialist` | ~100 |
| Contextual Corrector | `ContextualCorrector` | ~100 |
| Edit Distance Corrector | `EditDistanceCorrector` | ~150 |
| Main Spell Checker | `ArabicSpellChecker` | ~200 |
| **Total** | | **~1,507** |

### 3.5.2 Grammar Correction Architecture

```mermaid
flowchart LR
    INPUT["Input Text"] --> GRADIO["Gradio Client<br/>(Gemma 3 Inference)"]
    GRADIO --> CAMEL["ArabicGrammarGuard<br/>(CAMeL Tools)"]
    CAMEL --> OUTPUT["Corrected Text"]

    subgraph "ArabicGrammarGuard Rules"
        R1["preserve_numbers()"]
        R2["fix_number_and_gender_agreement()"]
        R3["smart_asmaa_khamsa_fix()"]
        R4["fix_verbs_nasb_and_jazm()"]
        R5["fix_gender_agreement()"]
        R6["fix_prepositions_advanced()"]
        R7["fix_subject_verb_agreement()"]
        R8["regex_rules_fallback()"]
    end

    CAMEL --> R1 --> R2 --> R3 --> R4 --> R5 --> R6 --> R7 --> R8
```

### 3.5.3 Punctuation Restoration Architecture

```mermaid
flowchart TD
    INPUT["Input Text"] --> SPLIT["Split into Paragraphs"]
    SPLIT --> CHUNK["Windowed Chunking<br/>(50 words/window,<br/>non-overlapping stride)"]
    CHUNK --> PREPROC["arabic_preprocessing()<br/>• Remove diacritics<br/>• Normalize"]
    PREPROC --> MODEL["PuncAra-v1 Inference<br/>• EncoderDecoderModel<br/>• num_beams=3<br/>• repetition_penalty=1.2"]
    MODEL --> STRIP["Strip Non-Punct Changes<br/>(Fix P1: preserve only<br/>punctuation modifications)"]
    STRIP --> POST["arabic_postprocessing()<br/>• Typographic cleanup<br/>• Space normalization"]
    POST --> OUTPUT["Punctuated Text"]
```

### 3.5.4 Autocomplete Architecture

```mermaid
flowchart TD
    INPUT["User Context<br/>(last ~200 chars)"] --> CHECK["GPT-2 Available?"]
    CHECK -->|"Yes"| HYBRID["Hybrid Prediction"]
    CHECK -->|"No"| BIGRAM["Bigram-Only Prediction"]

    HYBRID --> STAT["Statistical (Bigram)<br/>• Last word → next word<br/>• Frequency-based ranking"]
    HYBRID --> NEURAL["Neural (AraGPT2)<br/>• Full sentence context<br/>• Sampling (top_k=50, top_p=0.9)<br/>• 15 return sequences<br/>• Extract first Arabic word"]

    STAT --> SCORE["Hybrid Scoring<br/>score = 0.4 × stat + 0.6 × neural"]
    NEURAL --> SCORE
    SCORE --> FILTER["Filter & Deduplicate<br/>• merge_similar_predictions()<br/>• Threshold ≥ 0.05<br/>• Return top-N"]
    FILTER --> OUTPUT["Suggestions[]"]

    BIGRAM --> LOOKUP["Bigram Lookup<br/>• Last word as key<br/>• Fallback to unigram"]
    LOOKUP --> FILTER
```

## 3.6 Frontend Architecture (Web Application)

### 3.6.1 Single-Page Application Structure

The web application is a single HTML file (`src/index.html`, 147,459 bytes) with modular JavaScript:

```mermaid
graph TD
    HTML["index.html<br/>(147KB)"]
    HTML --> EDITOR["editor.js<br/>(30KB, WYSIWYG editor)"]
    HTML --> RENDERER["renderer.js<br/>(12KB, results display)"]
    HTML --> UI["ui.js<br/>(13KB, UI management)"]
    HTML --> API["api.js<br/>(1.6KB, API client)"]
    HTML --> FORMAT["format.js<br/>(12.7KB, formatting toolbar)"]
    HTML --> SELECTION["selection.js<br/>(6.7KB, text selection)"]
    HTML --> THEME["theme.js<br/>(2.4KB, theme management)"]
    HTML --> AUTOCOMPLETE["autocomplete.js<br/>(15.5KB, autocomplete UI)"]
    HTML --> AUTH["auth/ module<br/>(authentication)"]
    HTML --> DOCS["documents/ module<br/>(local document management)"]
    HTML --> DOCS_CLOUD["documents-cloud/ module<br/>(cloud sync via Supabase)"]
    HTML --> SUMMARIES["summaries/ module<br/>(summary display)"]
```

### 3.6.2 Editor Architecture

The WYSIWYG editor is built on a `contenteditable` `<div>` element with custom JavaScript logic for:

- **Rich text formatting**: Bold, italic, underline, font family, font size, text alignment (right-to-left default for Arabic), text color, and highlight color.
- **Real-time analysis**: Debounced analysis requests sent to `/api/analyze` as the user types.
- **Autocomplete dropdown**: Context-aware suggestions triggered by text input, positioned near the cursor.
- **Inline highlighting**: Color-coded underlines for spelling (red), grammar (blue), and punctuation (green) suggestions.
- **Document management**: Create, save, load, rename, and delete documents with local storage persistence and optional Supabase cloud sync.

## 3.7 Chrome Extension Architecture

### 3.7.1 Manifest V3 Component Model

```mermaid
graph TD
    subgraph "Browser Chrome"
        POPUP["Popup<br/>(popup.html)"]
        SIDE["Side Panel<br/>(sidepanel.html)"]
        BG["Service Worker<br/>(background.js)"]
    end

    subgraph "Web Page"
        CS["Content Script<br/>(content-inline.js)"]
        OVERLAY["Highlight Overlay<br/>(CSS positioned spans)"]
        FAB["Floating Action Button<br/>(bayan-fab)"]
        TOOLTIP["Suggestion Tooltip<br/>(bayan-tooltip)"]
    end

    subgraph "Shared Modules"
        CTRL["analysis-controller.js"]
        BAPI["bayan-api.js"]
        PATCHES["bayan-patches.js"]
        RENDER["bayan-renderer.js"]
        STATE["bayan-state.js"]
        BAYAN_UI["bayan-ui.js"]
        CONFIG["config.js"]
        CONST["constants.js"]
        HASH["hash.js"]
    end

    POPUP -->|"sendMessage"| BG
    SIDE -->|"sendMessage"| BG
    CS -->|"sendMessage"| BG
    BG -->|"fetch()"| API["Backend API"]

    POPUP -.-> CTRL
    POPUP -.-> BAPI
    POPUP -.-> RENDER
    CS -.-> CONST
    CS -.-> CTRL
```

### 3.7.2 Background Service Worker

The background service worker (`extension/background.js`, 6,213 bytes) serves three purposes:

1. **Network Proxy**: Content scripts cannot make cross-origin requests to the Bayan API. The service worker receives `BAYAN_ANALYZE` messages and proxies them via `fetch()`.

2. **Context Menu Registration**: Creates the right-click context menu item "✍️ تحليل مع بيان" that allows users to analyze selected text.

3. **Side Panel Management**: Responds to `OPEN_SIDE_PANEL` messages by calling `chrome.sidePanel.open()`.

### 3.7.3 Content Script — Inline Analysis Engine

The content-inline.js script (20,208 bytes) implements the Grammarly-style inline analysis:

```mermaid
statechart-v2
    [*] --> Idle
    Idle --> Detecting : User focuses editable field
    Detecting --> Observing : Editable field detected
    Observing --> Analyzing : Text changed (debounced 800ms)
    Analyzing --> Rendering : API response received
    Rendering --> Observing : Highlights rendered
    Observing --> Idle : User blurs field

    state Analyzing {
        [*] --> SendMessage
        SendMessage --> WaitResponse : chrome.runtime.sendMessage
        WaitResponse --> ProcessPatches : Response.suggestions[]
        ProcessPatches --> [*]
    }

    state Rendering {
        [*] --> ClearOverlay
        ClearOverlay --> CreateHighlights
        CreateHighlights --> PositionOverlay
        PositionOverlay --> [*]
    }
```

**Key Design Features:**

- **MutationObserver**: Detects dynamically created editable fields on SPAs.
- **Debounced Analysis**: 800ms debounce prevents excessive API calls during rapid typing.
- **Content Hash Check**: Uses FNV-1a hashing (`shared/hash.js`) to skip re-analysis if text content hasn't changed.
- **Protected Site Detection**: Skips injection on `chrome://`, `chrome-extension://`, and Chrome Web Store domains.
- **Error Recovery Mode**: On API failure, enters a backoff state rather than repeatedly failing.

### 3.7.4 Shared Module Architecture

The shared modules implement a clean separation of concerns:

| Module | Responsibility |
|---|---|
| `constants.js` | API URL, version string |
| `config.js` | Configuration management |
| `hash.js` | FNV-1a content hashing |
| `bayan-api.js` | API client with error handling |
| `bayan-state.js` | Analysis state management |
| `bayan-patches.js` | Patch data model and operations |
| `bayan-renderer.js` | Result rendering (shared by popup/sidepanel) |
| `bayan-ui.js` | UI helper functions |
| `analysis-controller.js` | Orchestration: hash check → API call → state update → render |

## 3.8 Deployment Architecture

### 3.8.1 Docker Container

```mermaid
flowchart TD
    subgraph "Docker Build Phase"
        BASE["python:3.12-slim"]
        DEPS["Install system deps<br/>(build-essential)"]
        PIP["Install Python deps<br/>(CPU-only PyTorch)"]
        DL_SUMM["Pre-download:<br/>Summarization (mBART)"]
        DL_SPELL["Pre-download:<br/>Spelling (AraSpell + AraBERT)"]
        DL_GRAM["Pre-download:<br/>Grammar (CAMeL data)"]
        DL_PUNC["Pre-download:<br/>Punctuation (PuncAra-v1)"]
        DL_DIAL["Pre-download:<br/>Dialect (mT5)"]
        COPY["Copy src/, quran.py,<br/>quran_master.db, .env"]
    end

    subgraph "Runtime"
        GUNICORN["gunicorn --chdir src app:app<br/>--bind 0.0.0.0:7860<br/>--timeout 300<br/>--workers 1"]
        PORT["Expose 7860"]
    end

    BASE --> DEPS --> PIP
    PIP --> DL_SUMM --> DL_SPELL --> DL_GRAM --> DL_PUNC --> DL_DIAL
    DL_DIAL --> COPY --> GUNICORN --> PORT
```

**Key Parameters:**
- **Workers**: 1 (to minimize RAM on free tier)
- **Timeout**: 300s (to accommodate full pipeline: spelling ~50s + grammar ~8s + punctuation ~30s + cold start)
- **Port**: 7860 (HuggingFace Spaces default)

### 3.8.2 Authentication and Data Flow

```mermaid
sequenceDiagram
    participant User
    participant WebApp
    participant Supabase
    participant Flask as Bayan API

    User->>WebApp: Login with email/password
    WebApp->>Supabase: signInWithPassword()
    Supabase-->>WebApp: JWT token + user profile
    WebApp->>WebApp: Store session locally

    User->>WebApp: Save document
    WebApp->>Supabase: INSERT into documents table
    Supabase-->>WebApp: Saved confirmation

    User->>WebApp: Analyze text
    WebApp->>Flask: POST /api/analyze {text}
    Flask-->>WebApp: {original, corrected, suggestions[]}
    WebApp->>WebApp: Render results
```

## 3.9 Data Models

### 3.9.1 Analysis API Response

```json
{
  "original": "النص الأصلي",
  "corrected": "النص المصحح",
  "suggestions": [
    {
      "id": "uuid",
      "start": 0,
      "end": 5,
      "original": "الأصلي",
      "correction": "الأصلية",
      "type": "spelling",
      "priority": 1,
      "confidence": 0.9,
      "locked": true,
      "alternatives": ["الأصلية", "الأصلي"]
    }
  ],
  "timing_ms": {
    "spelling_ms": 1200,
    "grammar_ms": 800,
    "punctuation_ms": 500,
    "total_ms": 2500
  },
  "status": "success"
}
```

### 3.9.2 CorrectionPatch Data Model

```mermaid
classDiagram
    class CorrectionPatch {
        +str stage
        +int start_original
        +int end_original
        +int start_current
        +int end_current
        +str original
        +str replacement
        +int priority
        +float confidence
        +bool locked
        +list alternatives
        +str id
        +dict to_dict()
    }

    class PatchSet {
        +list patches
        +add(patch)
        +resolve_overlaps() list
        +to_list() list
    }

    class PipelineContext {
        +str original_text
        +str current_text
        +PatchSet patches
        +list _offset_mappers
        +StageLocker stage_locker
        +map_to_original(start, end) tuple
        +add_patch(stage, start, end, replacement, ...)
        +mutate_text(text_after, OffsetMapperClass)
    }

    class StageLocker {
        +list _locked_ranges
        +lock(start, end, owner)
        +is_locked(start, end) bool
        +is_locked_by(start, end) tuple
        +update_via_mapper(mapper)
    }

    class OffsetMapper {
        -str _text_before
        -str _text_after
        -list _opcodes
        +reverse_map_offset(pos) int
        +forward_map_range(start, end) tuple
    }

    PipelineContext --> PatchSet
    PipelineContext --> StageLocker
    PipelineContext --> OffsetMapper
    PatchSet --> CorrectionPatch
```

## 3.10 Security Considerations

### 3.10.1 Input Sanitization

The `/api/analyze` endpoint performs input sanitization:

1. **HTML Tag Stripping**: `re.sub(r'<[^>]*>', '', text)` removes HTML tags to prevent AraSpell from processing tag characters.
2. **Arabic Content Threshold**: Inputs with less than 30% Arabic characters (relative to total alphabetic characters) are returned without analysis, preventing code/markup from reaching the NLP models.
3. **Maximum Length**: All endpoints enforce a `MAX_TEXT_LENGTH = 5,000` character limit.

### 3.10.2 CORS Policy

```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

CORS is restricted to `/api/*` routes only. Static file serving does not include CORS headers.

### 3.10.3 Chrome Extension Permissions

The manifest declares the minimum required permissions:

```json
"permissions": ["contextMenus", "activeTab", "storage", "sidePanel"],
"host_permissions": ["https://bayan10-bayan-api.hf.space/*"]
```

- No `<all_urls>` permission — only the Bayan API domain is allowed for network requests.
- `activeTab` provides temporary access to the current tab only when the user explicitly interacts with the extension.
- Content scripts are injected via the `content_scripts` manifest key (not programmatic injection), matching `https://*/*` and `http://*/*`.

## 3.11 Design Patterns Summary

| Pattern | Usage | Location |
|---|---|---|
| Singleton (Lazy-Loaded) | Model instances loaded on first request | All service modules |
| Pipeline | Sequential Spelling → Grammar → Punctuation processing | `/api/analyze` |
| Observer (MutationObserver) | Dynamic editable field detection | `content-inline.js` |
| Proxy | Service worker proxies API calls for content scripts | `background.js` |
| Strategy | Hybrid scoring selects between bigram and GPT-2 | `autocomplete_service.py` |
| Flyweight | Content hash avoids re-analysis of unchanged text | `analysis-controller.js` |
| Chain of Responsibility | OffsetMapper chain for coordinate transforms | `PipelineContext` |
| Greedy Algorithm | PatchSet overlap resolution | `correction_patch.py` |
