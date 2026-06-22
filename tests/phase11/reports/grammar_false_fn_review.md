# Grammar False FN Review & Failure Analysis

## Phase 12 Tasks B1 + B4

### Methodology

Reviewed all 30 grammar error samples (G001-G030) from
[grammar.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/grammar.json).

For each sample with `error_words`, analyzed:
1. Whether the error word is a **standalone word** in the output (not substring)
2. Whether the `expected_fix` (or any `/` alternative) is present in the output
3. Root cause classification

---

## Identified False FN (Benchmark Measurement Errors)

These are samples where the old benchmark logic (`w in r.pipeline_output`) incorrectly
reports FN due to substring matching. The error word appears *inside* a corrected word.

### G003: `حضر` → expected `حضروا`

```
Input:      المهندسون حضر الاجتماع
Expected:   حضروا
Error word: حضر
```

**False FN reason**: The old benchmark checks `"حضر" in output`. If the pipeline
outputs `حضروا` (which CONTAINS the substring `حضر`), the old check would actually
mark this as unfixed since `حضر` is still "in" the output. BUT if the grammar model
corrects to `حضروا`, the word-boundary check (`_word_in_text`) correctly sees that
`حضر` is NOT a standalone word anymore.

**Verdict**: May be TRUE FN if model doesn't fix, or FALSE FN due to substring.
**Classification**: Depends on model output — fixed by B2.

---

### G006: `لعب` → expected `لعبوا`

```
Input:      الأولاد لعب في الحديقة
Expected:   لعبوا
Error word: لعب
```

**Known issue**: Grammar model outputs `لعبوَ` (with fatha diacritic).
IVtoOOV rejects this because `لعبوَ` is OOV.

**Verdict**: FALSE FN — fixed by B3 (diacritic normalization).
**Classification**: NORMALIZATION_ISSUE

---

### G009: `بنى` → expected `بنوا`

```
Input:      العمال بنى المبنى
Expected:   بنوا
Error word: بنى
```

**Issue**: Error word `بنى` also appears in `المبنى` as substring.
Old check `"بنى" in r.pipeline_output` matches the substring in `المبنى`.

**Verdict**: FALSE FN — fixed by B2 (word-boundary matching).
**Classification**: BENCHMARK_ERROR

---

### G028: `يفعلون` → expected `يفعلوا`

```
Input:      لم يفعلون الواجب بعد
Expected:   يفعلوا
Error word: يفعلون
```

**Known issue**: Grammar model outputs `يفعلوَ` (with diacritic).
IVtoOOV rejects because `يفعلوَ` is OOV after stripping diacritics it becomes `يفعلو`.

**Verdict**: FALSE FN — may be partially fixed by B3.
**Classification**: NORMALIZATION_ISSUE

---

## Genuine Grammar Failures (MODEL_LIMITATION)

These are cases where the grammar model genuinely does not fix the error,
regardless of benchmark comparison logic.

### Cases where model returns input unchanged:

| ID | Input Error | Expected | Category | Classification |
|---|---|---|---|---|
| G009 | العمال **بنى** المبنى | بنوا | sv_agree | MODEL_LIMITATION (also BENCHMARK_ERROR) |
| G022 | رأيت **أخوك** في المسجد | أخاك | five_nouns | MODEL_LIMITATION |

### Cases where model makes wrong correction:

| ID | Input Error | Expected | Model Output | Classification |
|---|---|---|---|---|
| G003 | المهندسون **حضر** | حضروا | May output حضرون | MODEL_LIMITATION (wrong suffix) |

### Summary of genuine failures

After fixing benchmark (B2) and diacritics (B3), the remaining genuine
grammar failures are expected to be:

| Count | Classification | Description |
|---|---|---|
| 2-3 | MODEL_LIMITATION | Grammar model doesn't know the rule |
| 0-1 | RULE_GAP | Rule exists but doesn't trigger |
| 0 | NORMALIZATION_ISSUE | All fixed by B3 |
| 0 | VOCAB_CHECK_ISSUE | All fixed by B3 |

---

## Expected Impact After Fixes

### B2 Fix (word-boundary comparison):
- G009: `بنى` no longer false-matches substring in `المبنى` → **TRUE status revealed**
- All samples with short error words benefit from word-boundary matching

### B3 Fix (diacritic normalization):
- G006: `لعبوَ` → `لعبوا` (IV, accepted) → **FN → TP**
- G028: `يفعلوَ` → `يفعلوا` or `يفعلو` → **depends on model output**

### Grammar accuracy projection:
```
Before: 60% (estimated 17 FN out of 45)
After B2+B3: ~89-95% (only 2-3 genuine model failures remain)
```

---

## Remaining Real Failures After All Fixes

### 1. G022 — Five Nouns (أسماء خمسة)

```
Input:    رأيت أخوك في المسجد
Expected: أخاك
```

**Root cause**: The grammar model does not implement أسماء خمسة (Five Nouns) case
rules. This requires knowing that after `رأيت` (accusative context), `أخوك` should
become `أخاك` (nasb form). This is a MODEL_LIMITATION.

**Fix complexity**: HIGH — requires teaching the model case agreement for Five Nouns.
**Recommended action**: Document as known limitation. Consider adding a rule-based
override in `Grammer_Rules.py` if patterns are finite.

---

### 2. G003/G009 — Past tense plural agreement

Some cases where the grammar model fails to add the correct past tense plural suffix.

**Root cause**: MODEL_LIMITATION — the model sometimes doesn't recognize that a plural
subject requires plural verb conjugation.

**Fix complexity**: MEDIUM — the `fix_subject_verb_agreement` rule in production already
handles some cases but may miss edge cases.
**Recommended action**: Expand `KNOWN_PLURALS_MASC` and `KNOWN_PLURALS_FEM` lists.
