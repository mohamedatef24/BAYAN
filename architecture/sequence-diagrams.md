# Sequence Diagrams — Bayan

> Key interaction flows showing message passing between system components.

## 1. Text Analysis Pipeline (Web App)

The main correction flow when a user submits text for full analysis.

```mermaid
sequenceDiagram
    actor User
    participant Frontend as Web Frontend<br/>(bayan.bundle.js)
    participant Flask as Flask API<br/>(routes/nlp.py)
    participant Pipeline as PipelineContext<br/>(pipeline_context.py)
    participant Spelling as AraSpell<br/>(spelling_service.py)
    participant Grammar as Gemma 3<br/>(grammar_service.py)
    participant Punctuation as PuncAra-v1<br/>(punctuation_service.py)

    User->>Frontend: Enter text + click "تصحيح"
    Frontend->>Flask: POST /api/analyze {text}
    
    Flask->>Pipeline: PipelineContext(text)
    
    Note over Flask: Pre-checks: text length,<br/>Arabic ratio, religious text,<br/>URLs/emails/hashtags

    rect rgb(230, 245, 255)
        Note over Flask,Spelling: Stage 1: Spelling (≤1000 chars)
        Flask->>Spelling: _run_spelling_stage(ctx)
        Spelling->>Spelling: AraSpell seq2seq inference
        Spelling->>Spelling: Post-filters + OOV cleanup
        Spelling->>Spelling: Bidirectional validation
        Spelling-->>Flask: ctx.current_text updated
    end

    rect rgb(255, 245, 230)
        Note over Flask,Grammar: Stage 2: Grammar
        Flask->>Grammar: _run_grammar_stage(ctx)
        Grammar->>Grammar: Gemma 3 CausalLM inference<br/>(30s timeout)
        Grammar->>Grammar: Safety guards<br/>(Jaccard, tanween, entity, digit)
        Grammar-->>Flask: ctx.current_text updated
    end

    rect rgb(230, 255, 230)
        Note over Flask,Punctuation: Stage 3: Punctuation
        Flask->>Punctuation: _run_punctuation_stage(ctx)
        Punctuation->>Punctuation: PuncAra-v1 inference
        Punctuation->>Punctuation: Validation + 3-patch cap
        Punctuation-->>Flask: ctx.current_text updated
    end

    Flask->>Pipeline: ctx.patches.to_list()
    Pipeline-->>Flask: suggestions[] with<br/>original-text coordinates
    Flask->>Flask: _apply_patches_to_original()
    Flask-->>Frontend: {original, corrected,<br/>suggestions[], timing_ms}
    Frontend->>Frontend: Render inline suggestions<br/>(renderer.js)
    Frontend-->>User: Show highlighted corrections
```

## 2. Chrome Extension — Context Menu Flow

When a user right-clicks selected text on any webpage.

```mermaid
sequenceDiagram
    actor User
    participant Page as Web Page
    participant CS as Content Script<br/>(content-inline.js)
    participant BG as Service Worker<br/>(background.js)
    participant SP as Side Panel<br/>(sidepanel.js)
    participant API as Flask API

    User->>Page: Select text + right-click
    User->>BG: Click "صحّح مع بيان"<br/>(context menu item)
    
    BG->>BG: Store selection in<br/>chrome.storage.session
    BG->>BG: chrome.sidePanel.open()
    
    SP->>SP: onload → check storage<br/>for pending action
    SP->>SP: sourceSelectionText = text
    SP->>API: POST /api/analyze {text}
    API-->>SP: {corrected, suggestions[]}
    SP->>SP: Render results in<br/>"correct" tab
    
    User->>SP: Click "تطبيق" (Apply)
    SP->>BG: WRITE_BACK_TO_PAGE<br/>{text, mode, source, find}
    BG->>CS: BAYAN_WRITE_BACK<br/>{text, mode, source, find}
    
    CS->>CS: writeTextToField(field,<br/>text, mode, source, find)
    
    alt find anchor found
        CS->>CS: indexOf(find) →<br/>replace substring only
    else fallback
        CS->>CS: Use pendingSelection<br/>or replaceAll
    end
    
    CS-->>BG: {ok: true}
    BG-->>SP: {ok: true}
    SP->>SP: sourceSelectionText = text<br/>(update anchor)
    SP-->>User: "تم تطبيق التغييرات"
```

## 3. Chrome Extension — Inline Analysis Flow

Automatic text analysis when the user types in a text field.

```mermaid
sequenceDiagram
    actor User
    participant Field as Text Field<br/>(textarea / contenteditable)
    participant CS as Content Script<br/>(content-inline.js)
    participant BG as Service Worker<br/>(background.js)
    participant API as Flask API

    User->>Field: Type Arabic text
    Field->>CS: focus event detected
    CS->>CS: InlineAnalyzer.attach(field)

    User->>Field: Pause typing (debounce)
    CS->>CS: Debounce timer fires
    CS->>BG: BAYAN_ANALYZE<br/>{text, tabId}
    
    BG->>BG: Check API cache
    
    alt Cache hit
        BG-->>CS: Cached response
    else Cache miss
        BG->>API: POST /api/analyze {text}
        API-->>BG: {corrected, suggestions[]}
        BG->>BG: Store in cache
        BG-->>CS: {corrected, suggestions[]}
    end

    CS->>CS: Create overlay div<br/>(positioned above field)
    CS->>CS: Render highlighted<br/>suggestions in overlay
    CS-->>User: Show inline underlines<br/>+ tooltip on hover

    User->>CS: Click suggestion
    CS->>CS: Apply correction to<br/>field.value / innerHTML
    CS->>CS: Update overlay
```

## 4. Autocomplete — Ghost Text Flow

Real-time next-word prediction as the user types.

```mermaid
sequenceDiagram
    actor User
    participant Editor as Text Editor
    participant AC as autocomplete.js
    participant API as Flask API
    participant GPT2 as GPT-2 Model

    User->>Editor: Type text (input event)
    Editor->>AC: onInput handler
    AC->>AC: Debounce (300ms)
    AC->>AC: extractContext(text, 200)
    AC->>API: POST /api/autocomplete<br/>{context, n: 3}
    
    API->>GPT2: predict(context, n=3)
    GPT2->>GPT2: Generate next tokens
    GPT2-->>API: suggestions[]
    API-->>AC: {suggestions: ["word1", "word2", "word3"]}
    
    AC->>Editor: Render ghost text<br/>(first suggestion, grayed)
    
    alt User presses Tab
        User->>AC: Tab keydown
        AC->>Editor: Accept suggestion →<br/>insert into text
    else User keeps typing
        User->>Editor: Continue typing
        AC->>AC: Cancel current ghost text
        AC->>AC: New debounce cycle
    end
```

## 5. Document Sync Flow

Cloud synchronization of documents via Supabase.

```mermaid
sequenceDiagram
    actor User
    participant App as Web App
    participant SyncMgr as SyncManager<br/>(sync-manager.js)
    participant Queue as SyncQueue<br/>(sync-queue.js)
    participant Resolver as SyncResolver<br/>(sync-resolver.js)
    participant Supabase as Supabase<br/>(PostgreSQL)

    User->>App: Edit document
    App->>SyncMgr: Document changed
    SyncMgr->>Queue: Enqueue change
    
    Queue->>Queue: Debounce (auto-save)
    Queue->>Supabase: Upsert document
    
    alt Conflict detected
        Supabase-->>Queue: Conflict (409)
        Queue->>Resolver: Resolve conflict
        Resolver->>Resolver: Compare timestamps
        Resolver-->>Queue: Resolved version
        Queue->>Supabase: Retry upsert
    end
    
    Supabase-->>Queue: Success
    Queue-->>SyncMgr: Sync complete
    SyncMgr-->>App: Update UI status
```
