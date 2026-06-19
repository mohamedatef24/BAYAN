# 09 — Sync Engine Diagram

## Overview

The Sync Engine ensures documents are saved reliably, supporting offline editing with automatic recovery and conflict resolution when connectivity is restored.

## Sync Architecture

```mermaid
graph TD
    subgraph "Editor Layer"
        EDITOR["📝 Editor<br/>contenteditable div"]
        INPUT["User Input Event"]
        DRAFT["💾 localStorage Draft<br/>Immediate save"]
    end

    subgraph "Sync Manager (sync-manager.js)"
        DEBOUNCE["⏱ Debounce Timer<br/>2000ms"]
        ONLINE_CHECK["📶 Online Status<br/>navigator.onLine"]
        SCHEDULE["scheduleSave()"]
        SYNC_NOW["syncNow()"]
    end

    subgraph "Sync Queue (sync-queue.js)"
        QUEUE["📋 Operation Queue<br/>[{type, docId, content, timestamp}]"]
        ENQUEUE["enqueue()"]
        DEQUEUE["dequeue()"]
        FLUSH["flush()"]
    end

    subgraph "Conflict Resolver (sync-resolver.js)"
        RESOLVE["resolve(local, remote)"]
        LWW["lastWriteWins()"]
        MERGE["mergeConflict()"]
    end

    subgraph "Cloud Storage"
        DOC_API["documents-api.js"]
        SUPABASE["🗄️ Supabase<br/>documents table"]
    end

    subgraph "UI Feedback"
        TOAST["🔔 Toast Notification"]
        STATUS["Auto-save Status<br/>'تم الحفظ' / 'سيتم الحفظ'"]
    end

    INPUT --> EDITOR
    EDITOR --> DRAFT
    EDITOR --> SCHEDULE

    SCHEDULE --> DEBOUNCE
    DEBOUNCE --> ONLINE_CHECK

    ONLINE_CHECK -->|"Online"| SYNC_NOW
    ONLINE_CHECK -->|"Offline"| ENQUEUE
    ENQUEUE --> QUEUE

    SYNC_NOW --> DOC_API
    DOC_API --> SUPABASE
    SUPABASE --> STATUS

    QUEUE -->|"Back Online"| FLUSH
    FLUSH --> DEQUEUE
    DEQUEUE --> RESOLVE
    RESOLVE --> LWW
    RESOLVE --> MERGE
    LWW --> DOC_API
    MERGE --> DOC_API

    DOC_API --> TOAST

    style DRAFT fill:#F59E0B,color:#000
    style QUEUE fill:#EF4444,color:#fff
    style SUPABASE fill:#3B82F6,color:#fff
    style RESOLVE fill:#8B5CF6,color:#fff
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> Editing : User types
    Editing --> Debouncing : Input stops
    Debouncing --> Editing : More input
    Debouncing --> CheckOnline : Timer expires (2s)

    CheckOnline --> Saving : Online
    CheckOnline --> Queued : Offline

    Saving --> Saved : Success
    Saving --> Queued : Network error
    Saved --> Idle : Status shown

    Queued --> Flushing : Connection restored
    Flushing --> ConflictCheck : Load remote
    ConflictCheck --> Resolved : No conflict
    ConflictCheck --> Merging : Conflict detected
    Merging --> Resolved : Last-write-wins
    Resolved --> Saving : Save merged
```

## Module API Reference

### SyncManager (`sync-manager.js`)

```javascript
// Initialize sync engine
initSync()

// Schedule a debounced save
scheduleSave()

// Immediately sync current document
async syncNow() → Promise<boolean>

// Handle browser online event
handleOnline()

// Handle browser offline event
handleOffline()
```

### SyncQueue (`sync-queue.js`)

```javascript
// Add operation to queue
enqueue({ type: 'save', docId: string, content: string })

// Remove and return next operation
dequeue() → Operation | null

// Check if queue is empty
isEmpty() → boolean

// Process all queued operations
async flush() → Promise<void>
```

### SyncResolver (`sync-resolver.js`)

```javascript
// Resolve local vs remote versions
resolve(local: Document, remote: Document) → ResolvedDocument

// Timestamp-based resolution
lastWriteWins(a: Document, b: Document) → Document

// Content merge (future: OT-based)
mergeConflict(localContent: string, remoteContent: string) → string
```

## Conflict Resolution Strategy

```mermaid
graph TD
    A["Local Change<br/>timestamp: T1"] --> C{Compare Timestamps}
    B["Remote Change<br/>timestamp: T2"] --> C

    C -->|"T1 > T2"| D["Use Local<br/>(More recent)"]
    C -->|"T2 > T1"| E["Use Remote<br/>(More recent)"]
    C -->|"T1 = T2"| F["Content Diff"]

    F -->|"Same content"| G["No Action"]
    F -->|"Different"| H["Last Write Wins<br/>(Remote preferred)"]

    style D fill:#22C55E,color:#fff
    style E fill:#3B82F6,color:#fff
    style H fill:#F59E0B,color:#000
```

## Design Rationale

1. **localStorage First**: Every keystroke saves to localStorage — zero data loss on crash/close.
2. **2-Second Debounce**: Prevents excessive Supabase writes during fast typing.
3. **Queue-Based Offline**: Operations queue in memory; flushed when connectivity returns.
4. **Last-Write-Wins**: Simple, predictable resolution — the most recent change wins.
5. **Browser Events**: `online`/`offline` events trigger queue flush and status updates.
