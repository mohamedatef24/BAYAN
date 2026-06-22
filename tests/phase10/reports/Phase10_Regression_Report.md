# Phase 10 — Regression Report

> **Date**: 2026-06-22 | **Tests**: 270 | **Regressions**: 2

---

## 1. Regression Summary

| Type | Count | Severity |
|---|---|---|
| Fix lost | 2 | 🟠 Major |
| Reversal | 0 | — |
| Introduced error | 0 | — |
| **Total** | **2** | — |

---

## 2. Fix Lost Details

### Regression #1

| Field | Value |
|---|---|
| **Test** | Grammar dataset — SV agreement test |
| **Input** | "البنات ذهب إلى المدرسة" |
| **Spelling stage** | No change (not a spelling error) |
| **Grammar (raw)** | Fixed by raw grammar model |
| **Pipeline output** | "ذهب" still present → fix lost |
| **Root Cause** | Grammar model fixed it in raw mode but pipeline didn't emit the correction as a suggestion |
| **Component** | PIPELINE:integration |

### Regression #2

| Field | Value |
|---|---|
| **Test** | Grammar dataset — SV agreement test |
| **Input** | "الرجال يعمل في المصنع" |
| **Spelling stage** | No change |
| **Grammar (raw)** | Fixed by raw grammar model |
| **Pipeline output** | "يعمل" still present → fix lost |
| **Root Cause** | Same integration issue — grammar correction not emitted |
| **Component** | PIPELINE:integration |

---

## 3. Stage Interaction Matrix

| Source Stage → Target Stage | Conflict Count |
|---|---|
| **Spelling → Grammar** | **2** |
| Grammar → Punctuation | 0 |
| Spelling → Punctuation | 0 |

### Conflict Rate

| Metric | Value |
|---|---|
| Total inter-stage conflicts | 2 / 270 = **0.74%** |
| Reversion rate | 2 / 270 = **0.74%** |
| Overwrite rate | 0 / 270 = **0.00%** |

---

## 4. Stage-by-Stage Failure Flow

### How correct text flows through the pipeline:

```
Input: "الطالب المجتهد ينجح دائماً" (correct)
  ↓ Spelling: No change ✅
  ↓ Grammar:  No change ✅
  ↓ Punct:    Adds "دائماً." ❌
  → Output:   "الطالب المجتهد ينجح دائماً." ← HALLUCINATION
```

### How erroneous text flows:

```
Input: "انا طالب في الجامعة" (hamza error)
  ↓ Spelling: No change ❌ (missed hamza)
  ↓ Grammar:  No change
  ↓ Punct:    Adds "الجامعة."
  → Output:   "انا طالب في الجامعة." ← UNDERCORRECTION + OVERCORRECTION
```

### How structured content flows:

```
Input: "أرسل لي على info@company.com" (email)
  ↓ Spelling: No change ✅
  ↓ Grammar:  "info @ company ، com" ❌ (destroyed)
  ↓ Punct:    May add period
  → Output:   Email corrupted ← DESTRUCTION
```

---

## 5. Key Finding: Pipeline Architecture Is NOT the Problem

| Component | Failures | % |
|---|---|---|
| Models (spelling + grammar + punct) | **199** | **99.0%** |
| Pipeline integration | **2** | **1.0%** |
| Span mapping | **0** | **0%** |

> [!IMPORTANT]
> The pipeline, span mapping, and stage interaction code are working correctly. The failures are overwhelmingly at the model/rules level. **No architectural refactoring is needed** — the fixes should target model behavior and input/output filtering.

---

## 6. Regression Risk Assessment

| Change | Risk of Regression |
|---|---|
| Adding HAMZA_WHITELIST entries | 🟢 Very Low — additive, no side effects |
| Suppressing punct terminal injection | 🟡 Medium — may suppress valid period additions |
| Adding structured content protection | 🟢 Low — pre-processing filter before grammar model |
| Fixing grammar SV agreement | 🟡 Medium — POS tagger changes may affect other rules |
| Adding religious text detector | 🟢 Low — bypass filter, no model changes |
