# src/ — Source Code

## Structure

```
src/
├── app.py                  # Flask application — routes + pipeline orchestration
├── model_loader.py         # Model loading (Spelling, Grammar, Summarization, Autocomplete)
├── hf_inference.py         # HuggingFace API inference wrappers
├── index.html              # Main web UI (single-page app)
├── favicon.svg             # Site icon
├── css/                    # Stylesheets
│   ├── tokens.css          # Design tokens (colors, spacing)
│   ├── base.css            # Base styles
│   └── components.css      # Component styles
├── js/                     # Frontend JavaScript modules
│   ├── editor.js           # Editor logic, events, debouncing
│   ├── renderer.js         # Offset-based highlight rendering
│   ├── selection.js        # Cursor/selection save & restore
│   ├── ui.js               # Tooltips, suggestion lists, scores
│   ├── api.js              # Backend API fetch wrappers
│   ├── format.js           # Text formatting
│   ├── theme.js            # Theme switching
│   ├── autocomplete.js     # Autocomplete UI
│   ├── auth/               # Authentication (Supabase)
│   ├── documents/          # Local document management
│   ├── documents-cloud/    # Cloud document sync
│   ├── summaries/          # Text summarization UI
│   ├── settings-sync/      # Settings sync
│   ├── sync/               # Real-time sync engine
│   └── vendor/             # Third-party libraries
└── nlp/                    # NLP pipeline modules
    ├── spelling/            # AraSpell spelling correction
    │   ├── araspell_rules.py
    │   └── araspell_service.py
    ├── grammar/             # Grammar correction
    │   ├── grammar_rules.py
    │   └── grammar_service.py
    ├── punctuation/         # Punctuation restoration
    │   ├── punctuation_rules.py
    │   └── punctuation_service.py
    ├── autocomplete/        # Text autocomplete
    ├── dialect/             # Dialect detection
    ├── pipeline_context.py  # Shared pipeline state
    ├── stage_locker.py      # Cross-stage text locking
    └── correction_patch.py  # Correction patch utilities
```

## API Contract

- **Input**: Arabic text string (UTF-8)
- **Output**: JSON with `corrected`, `suggestions[]` (each with `start`, `end`, `replacement`, `explanation`), and `timing_ms`

## Running

```bash
cd src && gunicorn app:app --bind 0.0.0.0:7860 --timeout 120 --workers 1
```