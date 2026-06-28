# Chrome Extension Architecture — Bayan

> Manifest V3 extension with service worker, content script, side panel, and shared modules.

## Component Overview

```mermaid
graph TB
    subgraph Extension["Chrome Extension (MV3)"]
        subgraph Background["Background"]
            SW["background.js\n(Service Worker)"]
        end

        subgraph ContentScripts["Content Scripts"]
            CS["content-inline.js\n(Injected into pages)"]
            Overlay["Overlay System\n(Highlight + Tooltip)"]
        end

        subgraph UI["User Interface"]
            SP["sidepanel.js\n(Side Panel)"]
            Popup["popup.js\n(Popup)"]
            FAB["FAB Button\n(Floating Action)"]
        end

        subgraph SharedModules["shared/"]
            Constants["constants.js\n(MSG types, config)"]
            Config["config.js\n(API URL, settings)"]
            API["bayan-api.js\n(HTTP client)"]
            Renderer["renderer.js\n(Diff rendering)"]
            Patches["patches.js\n(Patch utilities)"]
            UIHelpers["ui.js\n(DOM helpers)"]
        end

        subgraph Tabs["Side Panel Tabs"]
            T1["Correct"]
            T2["Summarize"]
            T3["Dialect"]
            T4["Quran"]
            T5["Autocomplete"]
        end
    end

    subgraph ExternalPage["Host Web Page"]
        TextField["Text Fields\n(textarea, contenteditable)"]
        Selection["User Selection\n(window.getSelection)"]
    end

    FlaskAPI["Flask API\n(/api/*)"]

    CS --> TextField
    CS --> Selection
    CS --> Overlay

    CS <-->|"chrome.runtime\n.sendMessage"| SW
    SP <-->|"chrome.runtime\n.sendMessage"| SW
    SW <-->|"chrome.tabs\n.sendMessage"| CS

    SP --> T1
    SP --> T2
    SP --> T3
    SP --> T4
    SP --> T5

    SP --> SharedModules
    CS --> SharedModules

    API -->|"HTTPS"| FlaskAPI
```

## Message Flow

```mermaid
sequenceDiagram
    actor User
    participant CS as Content Script
    participant SW as Service Worker
    participant SP as Side Panel
    participant API as Flask API

    Note over CS,SP: Context Menu Flow
    User->>CS: Select text on page
    User->>SW: Click context menu item
    SW->>SW: Store in chrome.storage.session
    SW->>SP: Open side panel
    SP->>SP: Read pending action
    SP->>API: POST /api/analyze
    API-->>SP: Results
    SP-->>User: Show in Correct tab

    Note over CS,SP: Write-Back Flow
    User->>SP: Click "Apply"
    SP->>SW: WRITE_BACK_TO_PAGE
    SW->>CS: BAYAN_WRITE_BACK
    CS->>CS: writeTextToField()
    CS-->>SW: {ok: true}
    SW-->>SP: {ok: true}

    Note over CS,SP: Inline Analysis Flow
    User->>CS: Type in text field
    CS->>CS: Debounce input
    CS->>SW: BAYAN_ANALYZE
    SW->>API: POST /api/analyze
    API-->>SW: Results
    SW-->>CS: Results
    CS->>CS: Show overlay with highlights

    Note over CS,SP: FAB Flow
    User->>CS: Click FAB button
    CS->>CS: Get field text
    CS->>SW: BAYAN_ANALYZE
    SW->>SP: Open side panel with results
```

## Write-Back Logic

```mermaid
flowchart TD
    Start["User clicks Apply"]
    GetMode["Determine write mode"]

    Start --> GetMode

    GetMode -->|"replace"| Replace["Replace entire field content"]
    GetMode -->|"patch"| Patch["Apply individual patches"]
    GetMode -->|"smart"| Smart["Smart replacement"]

    Smart --> FindAnchor{"Find anchor text\n(indexOf)"}
    FindAnchor -->|"Found"| SubReplace["Replace substring\nat anchor position"]
    FindAnchor -->|"Not found"| Fallback{"Has pending\nselection?"}
    Fallback -->|"Yes"| UseSelection["Replace at\nselection range"]
    Fallback -->|"No"| ReplaceAll["replaceAll\n(last resort)"]

    SubReplace --> UpdateField["Update field value\nor innerHTML"]
    UseSelection --> UpdateField
    ReplaceAll --> UpdateField
    Replace --> UpdateField
    Patch --> UpdateField

    UpdateField --> DispatchEvents["Dispatch input +\nchange events"]
    DispatchEvents --> Notify["Show success toast"]
```

## Manifest V3 Configuration

```mermaid
graph LR
    subgraph Manifest["manifest.json"]
        Perms["permissions:\n- contextMenus\n- sidePanel\n- activeTab\n- storage"]
        HostPerms["host_permissions:\n- <all_urls>"]
        BG_entry["background:\n- background.js\n(service_worker)"]
        CS_entry["content_scripts:\n- content-inline.js\n(matches: <all_urls>)"]
        SP_entry["side_panel:\n- sidepanel.html\n(default_path)"]
        Popup_entry["action:\n- popup.html\n(default_popup)"]
    end

    subgraph Files["Extension Files"]
        BGFile["background.js"]
        CSFile["content-inline.js"]
        SPFile["sidepanel.html\n+ sidepanel.js"]
        PopupFile["popup.html\n+ popup.js"]
        SharedDir["shared/*.js"]
        Icons["icons/\n16, 48, 128 px"]
    end

    BG_entry --> BGFile
    CS_entry --> CSFile
    SP_entry --> SPFile
    Popup_entry --> PopupFile
```
