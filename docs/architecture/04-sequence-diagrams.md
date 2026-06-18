# 04 — Sequence Diagrams

## A. Typing + NLP Analysis Flow

```mermaid
sequenceDiagram
    participant U as User
    participant E as Editor (editor.js)
    participant API as api.js
    participant F as Flask (/api/analyze)
    participant SP as AraSpell
    participant GR as Grammar
    participant PU as Punctuation
    participant R as Renderer

    U->>E: Types text
    E->>E: Debounce (1000ms)
    E->>E: updateEditorStats()
    E->>E: Save draft to localStorage

    E->>API: POST /api/analyze {text}
    API->>F: HTTP POST

    F->>F: Validate text length (≤5000 chars)
    F->>SP: correct(text)
    SP-->>F: {corrections[], corrected_text}

    F->>GR: check(corrected_text)
    GR-->>F: {grammar_errors[]}

    F->>PU: restore(corrected_text)
    PU-->>F: {punctuated_text, punctuation_changes[]}

    F->>F: Merge all suggestions
    F->>F: Map offsets back to original text
    F-->>API: {suggestions[], score}
    API-->>E: JSON Response

    E->>R: highlightErrors(editor, suggestions)
    R->>R: Create <span> elements with error classes
    E->>E: updateSuggestionCounts()
    E->>E: updateWritingScore()
    R->>R: renderSuggestionsList() in sidebar
```

---

## B. AutoComplete Flow

```mermaid
sequenceDiagram
    participant U as User
    participant E as Editor
    participant API as api.js
    participant F as Flask (/api/autocomplete)
    participant AC as AutoComplete Model

    U->>E: Types partial word
    E->>E: Detect word boundary
    E->>API: POST /api/autocomplete {text, cursor_position}
    API->>F: HTTP POST

    F->>AC: complete(prefix_text)
    AC->>AC: Generate top-k suggestions
    AC-->>F: {suggestions: ["word1", "word2", "word3"]}

    F-->>API: JSON Response
    API-->>E: Suggestions array

    E->>E: Show autocomplete dropdown
    U->>E: Select suggestion (click/Tab)
    E->>E: Insert selected text at cursor
    E->>E: Close dropdown
```

---

## C. Summarization Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as SummaryUI
    participant API as api.js
    participant F as Flask (/api/summarize)
    participant SM as Summarization Model (MBart)
    participant SA as summaries-api.js
    participant SB as Supabase

    U->>UI: Click "تلخيص" tab
    U->>UI: Click "لخّص النص"
    UI->>UI: Get editor text

    UI->>API: POST /api/summarize {text, max_length}
    API->>F: HTTP POST

    F->>F: Validate text length (≥10 chars)
    F->>SM: summarize(text, max_length=512)
    SM->>SM: Tokenize (ar_AR)
    SM->>SM: Generate summary (beam search)
    SM-->>F: {summary_text}

    F-->>API: JSON {summary, word_count, compression_ratio}
    API-->>UI: Response

    UI->>UI: Display summary in panel
    UI->>SA: createSummary(docId, original, summary)
    SA->>SB: INSERT INTO summaries
    SB-->>SA: {id, created_at}
    SA-->>UI: Success

    U->>UI: Click "تصدير TXT"
    UI->>UI: Download summary as .txt file
```

---

## D. Document Save Flow

```mermaid
sequenceDiagram
    participant U as User
    participant E as Editor
    participant SM as SyncManager
    participant SQ as SyncQueue
    participant DA as documents-api.js
    participant SB as Supabase

    U->>E: Types / Edits text
    E->>E: Save to localStorage (draft)
    E->>SM: scheduleSave()
    SM->>SM: Debounce (2000ms)

    SM->>SM: Check isAuthenticated
    alt Authenticated
        SM->>DA: saveDocument(docId, content)
        DA->>SB: UPDATE documents SET content WHERE id
        SB-->>DA: Success
        DA-->>SM: true
        SM->>SM: showAutoSaveStatus("تم الحفظ")
    else Offline
        SM->>SQ: enqueue({type: "save", docId, content})
        SQ->>SQ: Store in memory
        SM->>SM: showAutoSaveStatus("سيتم الحفظ عند الاتصال")
    end
```

---

## E. Offline Recovery Flow

```mermaid
sequenceDiagram
    participant SM as SyncManager
    participant SQ as SyncQueue
    participant SR as SyncResolver
    participant DA as documents-api.js
    participant SB as Supabase

    Note over SM: User comes back online

    SM->>SM: handleOnline() triggered
    SM->>SQ: isEmpty()?

    alt Queue has pending operations
        loop For each queued operation
            SQ->>SM: dequeue() → operation
            SM->>DA: loadDocument(op.docId)
            DA->>SB: SELECT content FROM documents WHERE id
            SB-->>DA: {remote_content, updated_at}

            SM->>SR: resolve(local_content, remote_content)
            alt No conflict
                SR-->>SM: Use local version
            else Conflict detected
                SR->>SR: lastWriteWins(local, remote)
                SR-->>SM: Resolved content
            end

            SM->>DA: saveDocument(docId, resolved_content)
            DA->>SB: UPDATE documents
            SB-->>DA: Success
        end
        SM->>SM: showToast("تم مزامنة المستندات")
    end
```

## Design Rationale

1. **Debounced Analysis**: 1-second debounce prevents API flooding during fast typing.
2. **Sequential NLP Pipeline**: Spelling → Grammar → Punctuation ensures each stage works on corrected text.
3. **Offline-First**: All changes saved to localStorage immediately; Supabase sync is eventual.
4. **Conflict Resolution**: Last-write-wins strategy with timestamp comparison.
