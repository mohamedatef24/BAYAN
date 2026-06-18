# 08 — NLP Pipeline Diagram (Final Production State)

## Overview

The BAYAN NLP layer consists of three independent pipelines: **Text Correction** (sequential), **AutoComplete** (parallel), and **Summarization** (independent). All five models are fully deployed and operational.

---

## Main Correction Pipeline

```mermaid
graph TD
    subgraph "Input"
        TEXT["📝 User Input Text<br/>(Arabic, up to 5000 chars)"]
    end

    subgraph "Stage 1: Spelling Correction"
        TOKENIZE["1.1 Word Tokenization<br/>Split into Arabic tokens"]
        SPELL_CHECK["1.2 AraSpell Check<br/>AraBERT Encoder-Decoder"]
        ALT_GEN["1.3 Alternative Generation<br/>Top-K Candidates"]
        SPELL_OUT["1.4 Spelling Corrections<br/>{original, correction, alternatives, start, end}"]
    end

    subgraph "Stage 2: Grammar Checking"
        CORRECTED_TEXT["2.0 Spelling-Corrected Text"]
        GRAM_RULES["2.1 Grammar Rules Engine<br/>Subject-Verb Agreement<br/>Case Marking<br/>Definiteness"]
        GRAM_ML["2.2 ML Grammar Model<br/>Contextual Analysis"]
        GRAM_OUT["2.3 Grammar Errors<br/>{original, correction, type: grammar}"]
    end

    subgraph "Stage 3: Punctuation Restoration"
        CLEAN_TEXT["3.0 Grammar-Corrected Text"]
        PUNCT_MODEL["3.1 PuncAra-v1<br/>Sequence Labeling"]
        PUNCT_OUT["3.2 Punctuation Suggestions<br/>{position, punctuation_mark}"]
    end

    subgraph "Stage 4: Result Merging"
        OFFSET_MAP["4.1 Offset Mapper<br/>Map corrected → original positions"]
        MERGE["4.2 Merge All Suggestions<br/>spelling + grammar + punctuation"]
        SCORE["4.3 Writing Score Calculation<br/>100 - (errors × weight)"]
    end

    subgraph "Output"
        RESULT["📊 Unified Response<br/>{suggestions[], score, counts}"]
    end

    TEXT --> TOKENIZE
    TOKENIZE --> SPELL_CHECK
    SPELL_CHECK --> ALT_GEN
    ALT_GEN --> SPELL_OUT

    SPELL_OUT --> CORRECTED_TEXT
    CORRECTED_TEXT --> GRAM_RULES
    CORRECTED_TEXT --> GRAM_ML
    GRAM_RULES --> GRAM_OUT
    GRAM_ML --> GRAM_OUT

    GRAM_OUT --> CLEAN_TEXT
    CLEAN_TEXT --> PUNCT_MODEL
    PUNCT_MODEL --> PUNCT_OUT

    SPELL_OUT --> OFFSET_MAP
    GRAM_OUT --> OFFSET_MAP
    PUNCT_OUT --> OFFSET_MAP
    OFFSET_MAP --> MERGE
    MERGE --> SCORE
    SCORE --> RESULT

    style SPELL_CHECK fill:#EF4444,color:#fff
    style GRAM_RULES fill:#F59E0B,color:#000
    style PUNCT_MODEL fill:#3B82F6,color:#fff
    style SCORE fill:#22C55E,color:#fff
```

---

## Smart Dependency Logic

```mermaid
graph LR
    subgraph "Token-Level Pipeline"
        T1["Token 1<br/>'الكتابه'"]
        T2["Token 2<br/>'الصحيحه'"]
        T3["Token 3<br/>'مهمة'"]
        T4["Token 4<br/>'جدا'"]
    end

    subgraph "AraSpell"
        S1["❌ الكتابه → الكتابة"]
        S2["❌ الصحيحه → الصحيحة"]
        S3["✅ مهمة (clean)"]
        S4["✅ جدا (clean)"]
    end

    subgraph "Grammar Engine"
        G3["✅ مهمة<br/>(processed immediately)"]
        G4["✅ جداً<br/>(processed immediately)"]
        G1["⏳ الكتابة<br/>(waits for correction)"]
        G2["⏳ الصحيحة<br/>(waits for correction)"]
    end

    subgraph "Punctuation"
        P["PuncAra processes<br/>final corrected sentence"]
    end

    T1 --> S1
    T2 --> S2
    T3 --> S3
    T4 --> S4

    S3 --> G3
    S4 --> G4
    S1 -.->|"after correction"| G1
    S2 -.->|"after correction"| G2

    G1 & G2 & G3 & G4 --> P

    style S1 fill:#EF4444,color:#fff
    style S2 fill:#EF4444,color:#fff
    style S3 fill:#22C55E,color:#fff
    style S4 fill:#22C55E,color:#fff
```

### Dependency Rules

1. **Clean tokens** bypass the spelling wait and are sent to grammar immediately.
2. **Misspelled tokens** are corrected first; grammar waits only for those specific tokens.
3. **Punctuation** executes last on the fully corrected sentence.
4. **Offset mapping** traces every change back to the original text positions.

---

## AutoComplete Pipeline

```mermaid
graph TD
    TYPING["⌨️ User Typing<br/>Partial word detected"]
    CONTEXT["Extract Context<br/>Last 50 tokens + cursor position"]
    AC_MODEL["AutoComplete Model<br/>Language Model Inference"]
    RANKING["Suggestion Ranking<br/>Score + Frequency + Relevance"]
    FILTER["Arabic-Only Filter<br/>Remove non-Arabic candidates"]
    DROPDOWN["📋 Dropdown Display<br/>Top 3-5 suggestions"]
    INSERT["Insert Selected<br/>Replace partial word"]

    TYPING --> CONTEXT
    CONTEXT --> AC_MODEL
    AC_MODEL --> RANKING
    RANKING --> FILTER
    FILTER --> DROPDOWN
    DROPDOWN -->|"User selects"| INSERT

    style AC_MODEL fill:#10B981,color:#fff
```

---

## Summarization Pipeline

```mermaid
graph TD
    SOURCE["📄 Source Text<br/>(from editor or document)"]
    VALIDATE["Validate<br/>≥10 chars, ≤5000 chars"]
    TOKENIZE["MBart Tokenizer<br/>src_lang=ar_AR"]
    GENERATE["MBart Generation<br/>beam_search, max_tokens=512"]
    DECODE["Decode Output<br/>skip_special_tokens"]
    METRICS["Calculate Metrics<br/>word_count, compression_ratio"]
    DISPLAY["📊 Display Summary<br/>Summary tab UI"]
    STORE["💾 Save to Supabase<br/>summaries table"]

    SOURCE --> VALIDATE
    VALIDATE --> TOKENIZE
    TOKENIZE --> GENERATE
    GENERATE --> DECODE
    DECODE --> METRICS
    METRICS --> DISPLAY
    METRICS --> STORE

    style GENERATE fill:#8B5CF6,color:#fff
```

---

## Models Reference Table

| Model | Architecture | Size | Input | Output |
|-------|-------------|------|-------|--------|
| **AraSpell** | AraBERT Encoder-Decoder + Checkpoint | ~220MB | Misspelled word | Corrected word + alternatives |
| **Grammar** | Rule Engine + ML Classifier | ~50MB | Corrected text | Grammar errors + suggestions |
| **PuncAra-v1** | Sequence Labeling Model | ~100MB | Unpunctuated text | Punctuated text |
| **AutoComplete** | Language Model | ~100MB | Text prefix | Next word candidates |
| **Summarization** | MBart (float16) | ~600MB | Arabic text | Compressed summary |

## Design Rationale

1. **Sequential Pipeline**: Spelling must run first because grammar and punctuation analysis on misspelled words produces false positives.
2. **Offset Mapping**: Critical for mapping corrected positions back to original text (where the user sees highlights).
3. **HF Inference Fallback**: When RAM is limited, the system can route to HuggingFace Inference API remotely.
4. **Float16**: Summarization model uses half-precision to halve memory footprint without quality loss.
