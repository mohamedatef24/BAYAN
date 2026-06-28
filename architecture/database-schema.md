# Database Schema — Bayan

> All data storage layers: Supabase (PostgreSQL), SQLite (Quran), localStorage, and Chrome extension storage.

## Database Overview

```mermaid
graph TB
    subgraph Cloud["Supabase (PostgreSQL)"]
        AuthUsers["auth.users\n(Supabase managed)"]
        Documents["documents"]
        Summaries["summaries"]
        SettingsTable["settings"]
    end

    subgraph Local["SQLite (quran_master.db)"]
        Verses["verses\n(6,236 rows)"]
        Suras["suras_translated\n(114 rows)"]
    end

    subgraph BrowserStorage["localStorage (Web App)"]
        Draft["bayan_editor_draft"]
        Theme["bayan_theme"]
        Lang["bayan_lang"]
        Dismissed["bayan_dismissed_words"]
        FontSize["bayan_font_size"]
        WordGoal["bayan_word_goal"]
        SummaryMode["bayan_summary_mode"]
        SyncQueue["bayan_sync_queue"]
        Onboarded["bayan_onboarded"]
        AnalysisCache["bayan_cache_{hash}"]
    end

    subgraph ExtStorage["chrome.storage (Extension)"]
        ConfigCache["config_cache\n(chrome.storage.local)"]
        DismissedExt["dismissed_words\n(chrome.storage.local)"]
        PendingAction["pending context menu action\n(chrome.storage.session)"]
    end

    AuthUsers -->|"user_id FK"| Documents
    AuthUsers -->|"user_id FK"| Summaries
    AuthUsers -->|"user_id FK"| SettingsTable
    Suras -->|"sura_number -> sura_num"| Verses
```

## Supabase Schema (PostgreSQL)

### Entity Relationship Diagram

```mermaid
erDiagram
    AUTH_USERS {
        uuid id PK
        string email
        string encrypted_password
        timestamp created_at
        timestamp updated_at
        json raw_user_meta_data
    }

    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        text title
        text content
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    SUMMARIES {
        uuid id PK
        uuid user_id FK
        text original_text
        text summary_text
        timestamp created_at
    }

    SETTINGS {
        uuid user_id PK
        text theme
        jsonb preferences
    }

    AUTH_USERS ||--o{ DOCUMENTS : "owns"
    AUTH_USERS ||--o{ SUMMARIES : "owns"
    AUTH_USERS ||--o| SETTINGS : "has"
```

### Table Details

#### `documents`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PK, auto | Document identifier |
| `user_id` | uuid | FK -> auth.users | Document owner |
| `title` | text | NOT NULL | Document title (default: "مستند جديد") |
| `content` | text | | HTML content from the editor |
| `created_at` | timestamptz | auto | Creation timestamp |
| `updated_at` | timestamptz | auto | Last modification |
| `deleted_at` | timestamptz | nullable | Soft-delete timestamp (null = active) |

**Operations:** `insert`, `select`, `update` (content, title, deleted_at). No hard deletes.
**Access pattern:** Always filtered by `user_id` and `deleted_at IS NULL`. Ordered by `updated_at DESC`.

#### `summaries`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PK, auto | Summary identifier |
| `user_id` | uuid | FK -> auth.users | Summary owner |
| `original_text` | text | NOT NULL | Source text that was summarized |
| `summary_text` | text | NOT NULL | Generated summary |
| `created_at` | timestamptz | auto | Creation timestamp |

**Operations:** `insert`, `select`, `delete`. Max 50 per user query.
**Access pattern:** Filtered by `user_id`. Ordered by `created_at DESC`. Limited to 50.

#### `settings`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | uuid | PK, unique | Settings owner (one row per user) |
| `theme` | text | | UI theme: `"light"` or `"dark"` |
| `preferences` | jsonb | | User preferences object |

**Preferences JSON structure:**
```json
{
  "font_size": "16",
  "word_goal": "0",
  "summary_mode": "paragraph"
}
```

**Operations:** `select`, `upsert` (on conflict: `user_id`). Single row per user.

---

## SQLite Schema (quran_master.db)

### Entity Relationship Diagram

```mermaid
erDiagram
    VERSES {
        integer sura_num PK
        integer aya_num PK
        text text_clean
        text text_uthmani
        text lang_bn
        text lang_bs
        text lang_en
        text lang_fr
        text lang_de
        text lang_id
        text lang_ms
        text lang_fa
        text lang_pt
        text lang_ru
        text lang_es
        text lang_tr
        text lang_uz
    }

    SURAS_TRANSLATED {
        integer sura_number PK
        text ar
        text lang_bn
        text lang_bs
        text lang_en
        text lang_fr
        text lang_de
        text lang_id
        text lang_ms
        text lang_fa
        text lang_pt
        text lang_ru
        text lang_es
        text lang_tr
        text lang_uz
    }

    SURAS_TRANSLATED ||--o{ VERSES : "sura_number -> sura_num"
```

### Table Details

#### `verses` (6,236 rows)
| Column | Type | Description |
|--------|------|-------------|
| `sura_num` | INTEGER | Sura number (1-114), composite PK |
| `aya_num` | INTEGER | Verse number within sura, composite PK |
| `text_clean` | TEXT | Normalized text (no diacritics) -- used for search |
| `text_uthmani` | TEXT | Uthmani script with full diacritics -- used for display |
| `lang_bn` | TEXT | Bengali translation |
| `lang_bs` | TEXT | Bosnian translation |
| `lang_en` | TEXT | English translation |
| `lang_fr` | TEXT | French translation |
| `lang_de` | TEXT | German translation |
| `lang_id` | TEXT | Indonesian translation |
| `lang_ms` | TEXT | Malay translation |
| `lang_fa` | TEXT | Persian translation |
| `lang_pt` | TEXT | Portuguese translation |
| `lang_ru` | TEXT | Russian translation |
| `lang_es` | TEXT | Spanish translation |
| `lang_tr` | TEXT | Turkish translation |
| `lang_uz` | TEXT | Uzbek translation |

**Query patterns:**
- `LIKE '%anchor%'` search on `text_clean` for fuzzy verse matching
- `JOIN suras_translated` for sura names in target language
- Dynamic column selection: `v.lang_{code}` and `s.lang_{code}` based on requested language

#### `suras_translated` (114 rows)
| Column | Type | Description |
|--------|------|-------------|
| `sura_number` | INT | Sura number (1-114) |
| `ar` | TEXT | Arabic sura name (e.g., "الفاتحة") |
| `lang_*` | TEXT | Translated sura names (14 languages) |

---

## localStorage Schema (Web App)

```mermaid
graph TB
    subgraph EditorState["Editor State"]
        D["bayan_editor_draft\ntype: HTML string\nAuto-saved on typing"]
        DW["bayan_dismissed_words\ntype: JSON array of strings\nWords user marked as correct"]
    end

    subgraph UserPrefs["User Preferences"]
        T["bayan_theme\ntype: light / dark"]
        L["bayan_lang\ntype: ar / en"]
        F["bayan_font_size\ntype: string (e.g. 16)"]
        WG["bayan_word_goal\ntype: string (e.g. 500)"]
        SM["bayan_summary_mode\ntype: paragraph / bullets"]
    end

    subgraph AppState["App State"]
        O["bayan_onboarded\ntype: 1 / null\nOnboarding tour shown"]
        SQ["bayan_sync_queue\ntype: JSON array\nPending sync operations"]
    end

    subgraph Cache["Analysis Cache"]
        AC["bayan_cache_{hash}\ntype: JSON t: timestamp, d: data\nTTL-based API response cache"]
    end
```

| Key | Type | Description |
|-----|------|-------------|
| `bayan_editor_draft` | HTML string | Auto-saved editor content |
| `bayan_dismissed_words` | JSON array | Words dismissed from spell check |
| `bayan_theme` | `"light"` \| `"dark"` | UI theme preference |
| `bayan_lang` | `"ar"` \| `"en"` | Interface language |
| `bayan_font_size` | string number | Editor font size |
| `bayan_word_goal` | string number | Daily word count goal |
| `bayan_summary_mode` | `"paragraph"` \| `"bullets"` | Summary display format |
| `bayan_onboarded` | `"1"` \| null | Whether onboarding tour was shown |
| `bayan_sync_queue` | JSON array | Queued sync operations for offline support |
| `bayan_cache_{hash}` | JSON `{t, d}` | Cached analysis results with TTL |

---

## Chrome Extension Storage

| Store | Key | Type | Description |
|-------|-----|------|-------------|
| `chrome.storage.local` | `config_cache` | object | Cached server config (Supabase URL, etc.) |
| `chrome.storage.local` | `dismissed_words` | string[] | Words user marked as correct |
| `chrome.storage.session` | pending action data | object | Context menu selection pending side panel open |

---

## Data Flow Between Storage Layers

```mermaid
flowchart LR
    subgraph WritePath["Write Path"]
        EditorTyping["Editor typing"]
        LS["localStorage\n(bayan_editor_draft)"]
        SQS["localStorage\n(bayan_sync_queue)"]
    end

    SupaDocs["Supabase\n(documents table)"]

    subgraph ReadPath["Read Path"]
        WebApp["Web App"]
    end

    Supa2["Supabase\n(documents)"]
    QuranDBRead["SQLite\n(quran_master.db)"]
    FlaskAPI["Flask API"]
    LS2["localStorage\n(draft)"]

    subgraph SettingsSync["Settings Sync"]
        LSTheme["localStorage\n(theme, font, etc.)"]
    end

    SupaSettings["Supabase\n(settings table)"]

    EditorTyping -->|"auto-save"| LS
    EditorTyping -->|"save button"| SQS
    SQS -->|"SyncManager"| SupaDocs

    Supa2 -->|"loadDocuments()"| WebApp
    LS2 -->|"on page load"| WebApp
    QuranDBRead -->|"search_bayan()"| FlaskAPI

    LSTheme <-->|"SettingsSync"| SupaSettings
```
