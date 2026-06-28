# Data Flow Diagram — Bayan

> How data moves through the system from user input to processed output.

## Full Analysis Data Flow

```mermaid
flowchart TD
    Input["User Text Input"]

    subgraph PreProcessing["Pre-Processing"]
        Validate["Validate Input"]
        Arabic["Check Arabic Ratio"]
        Religious["Detect Religious Text"]
        Protect["Protect URLs / Emails / Hashtags"]
    end

    subgraph Pipeline["3-Stage Pipeline"]
        direction TB
        S1["Stage 1: Spelling\n(AraSpell seq2seq)"]
        S2["Stage 2: Grammar\n(Gemma 3 CausalLM)"]
        S3["Stage 3: Punctuation\n(PuncAra-v1)"]
    end

    subgraph PostProcessing["Post-Processing"]
        Merge["Merge PatchSet"]
        Coords["Map to Original\nCoordinates"]
        Build["Build Response JSON"]
    end

    subgraph Output["Output"]
        Accept["User Accepts\nSuggestion"]
        Reject["User Dismisses\nSuggestion"]
    end

    Input --> Validate
    Validate --> Arabic
    Arabic -->|">30% Arabic"| Religious
    Arabic -->|"<30% Arabic"| ErrorResp["Return Error"]
    Religious --> Protect
    Protect --> S1

    S1 -->|"ctx.current_text"| S2
    S2 -->|"ctx.current_text"| S3

    S3 --> Merge
    Merge --> Coords
    Coords --> Build

    Build --> Accept
    Build --> Reject

    Accept -->|"Apply correction"| FinalText["Updated Text"]
    Reject -->|"Keep original"| FinalText
```

## Data Flow Legend

| Stage | Input | Processing | Output |
|-------|-------|-----------|--------|
| Pre-Processing | Raw text string | Validation, Arabic detection, religious text spans, URL/email protection | Clean text + protected spans |
| Spelling | Clean text (max 1000 chars) | AraSpell inference, post-filters, OOV cleanup, bidirectional validation | Patches + updated text |
| Grammar | Text from Stage 1 | Gemma 3 prompt, inference (30s timeout), safety guards (Jaccard, tanween, entity, digit) | Patches + updated text |
| Punctuation | Text from Stage 2 | PuncAra-v1 inference, validation, 3-patch cap | Patches + updated text |
| Post-Processing | All patches | Merge overlapping, map to original-text coordinates | JSON response |
