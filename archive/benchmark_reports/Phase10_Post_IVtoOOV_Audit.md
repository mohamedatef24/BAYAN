# Phase 10 Benchmark Audit — Post IVtoOOV Removal

> **Date**: 2026-06-24
> **Action**: Removed `IVtoOOV` filter and added advanced `camel-tools` POS tagging for dual/plural noun-adjective agreement.

## 1. Top-Level Aggregate Metrics

| Metric | Score | Notes |
|---|---|---|
| **Overall Pass Rate** | **56.2%** | Massive improvement (previously ~25%) |
| Total Tests | 320 | |
| True Positives (TP) | 95 | Successfully fixed real errors |
| True Negatives (TN) | 85 | Successfully ignored correct text |
| False Positives (FP) | 79 | Hallucinations or overcorrections |
| False Negatives (FN) | 61 | Failed to fix real errors |

### Root Cause Analysis (61 FN + 79 FP = 140 Failures)
- **Punctuation Model (`MODEL:punctuation`)**: 64 failures
- **Integration/Collisions (`PIPELINE:integration`)**: 32 failures
- **Spelling Model (`MODEL:spelling`)**: 21 failures
- **Grammar Model (`MODEL:grammar`)**: 18 failures

---

## 2. Per-Dataset Breakdown

### Grammar Dataset
* **Pass Rate:** 57.8% (up from 26.7%)
* **Recall:** 80.0% (up from 40.0%)
* **Analysis:** Removing `IVtoOOV` successfully unblocked valid grammatical structural changes. The recall doubled.
* **Remaining Issue:** High False Positive Rate on the `correct...` category. The model hallucinates changes on already perfect text.

### Spelling Dataset
* **Pass Rate:** 63.7% (up from 42.5%)
* **Recall:** 79.4%
* **Remaining Issue:** Still missing some Hamza errors and complex word splits (`عندالباب` -> `عند الباب`).

### Structured Content & Religious Datasets
* **Structured Pass Rate:** 82.9% (up from 5.7%)
* **Religious Pass Rate:** 90.0% (up from 10.0%)
* **Analysis:** The `DigitGuard` and punctuation bypass rules are working incredibly well to protect specialized text.

### Pipeline Collision Dataset
* **Pass Rate:** 16.0% (Terrible)
* **False Negative Rate:** 84.0%
* **Analysis:** When a spelling error is adjacent to a grammar error, `StageLocker` is locking the word and preventing the grammar model from seeing or fixing the grammatical context.

### Entities Dataset
* **Pass Rate:** 13.3%
* **Analysis:** The models (especially punctuation and spelling) are aggressively modifying named entities (people, places).

---

## 3. Strategic Action Plan for Enhancements

To push the pass rate from **56.2%** to **>80%**, we must address the following critical areas:

### A. Tame the "StageLocker" (Fix Pipeline Collisions)
The `StageLocker` in `app.py` enforces a rigid "Spelling locks word X, Grammar cannot touch word X" rule. This breaks multi-stage corrections.
**Solution:** Relax the `StageLocker`. Allow the grammar model to operate on tokens that were modified by spelling, provided the grammatical change doesn't completely revert the spelling correction (e.g., checking Jaccard distance or allowing suffix-only changes to locked words).

### B. Stop Punctuation Hallucinations
The punctuation model causes **64 failures**, mostly by adding periods `.` or question marks `؟` to the end of short sentences or entities where they don't belong.
**Solution:** Implement a strict `TerminalPunctuationGuard`. If the original text is < 5 words and doesn't end in punctuation, automatically strip any trailing punctuation added by the model.

### C. Implement Named Entity Recognition (NER) Bypass
Entities (Person names, Cities) are failing at an 86% rate.
**Solution:** Integrate `camel-tools` NER (Named Entity Recognition). Scan the input text for `LOC`, `PERS`, and `ORG`. If a word is an entity, add it to a dynamic whitelist so the Spelling and Grammar models skip it entirely.

### D. Tame Grammar Hallucinations on Correct Text
The grammar model hallucinates on perfectly correct text.
**Solution:** Use a POS-based confidence score. If the grammar model attempts to change a noun into a verb, or completely alters the POS structure of an already valid sentence, reject the change. Alternatively, enforce stricter `Jaccard_05` checks for non-structural changes.
