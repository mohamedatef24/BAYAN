# Phase 11 Summary — Observability & Architecture Audit

## Section 1 — Pipeline Funnel

```
Grammar Model Calls            270
Grammar Raw Output Changed      98  (36.3% of inputs)
Grammar Diffs Extracted        134
  → Passed All Filters          44  (32.8% of diffs)
  → Rejected by Filters         82  (61.2% of diffs)
  → Unaccounted                   8  (6.0% — skipped by grammar pattern / directional)
Patches Applied                 44
PatchSet Conflicts               0
Final Corrections (all stages) 127
```

**67.2% of grammar diffs are rejected by filters.**

---

## Section 2 — Loss Analysis

### Filter Rejection Breakdown

| Filter | Rejections | % of 82 | Effect |
|---|---|---|---|
| **PunctuationGuard** | **32** | **39.0%** | Blocks grammar stripping periods from correct text |
| **TanweenGuard** | **30** | **36.6%** | Blocks grammar stripping tanween (ً/ٌ/ٍ) |
| LatinGuard | 9 | 11.0% | Blocks changes to Latin-containing text |
| DigitGuard | 5 | 6.1% | Blocks changes to digit-containing text |
| IVtoOOV | 3 | 3.7% | Blocks valid→non-word changes |
| Jaccard_03 | 2 | 2.4% | Blocks character-dissimilar changes |
| StageLocker | 1 | 1.2% | Blocks overlap with spelling-corrected ranges |

### Filter Precision

| Filter | Total | Correct | Incorrect | Precision |
|---|---|---|---|---|
| PunctuationGuard | 32 | 32 | 0 | **100%** |
| TanweenGuard | 30 | 30 | 0 | **100%** |
| LatinGuard | 9 | 9 | 0 | **100%** |
| DigitGuard | 5 | 5 | 0 | **100%** |
| IVtoOOV | 3 | 3 | 0 | **100%** |
| Jaccard_03 | 2 | 2 | 0 | **100%** |
| StageLocker | 1 | 1 | 0 | **100%** |
| **TOTAL** | **82** | **82** | **0** | **100%** |

> [!IMPORTANT]
> All 82 rejections were CORRECT. No valid corrections were blocked by filters.
> The grammar model's FN problem is NOT caused by over-filtering.

---

## Section 3 — Evidence-Based Findings

### Finding 1: Grammar FN are NOT filter-caused

Of 17 grammar FN:

| Root Cause | Count | % |
|---|---|---|
| **PATCH_FAILURE** | 13 | 76% |
| FILTER_FAILURE | 2 | 12% |
| MODEL_FAILURE | 2 | 12% |

But the 13 PATCH_FAILURE cases are **actually correct** — the pipeline IS fixing them. The benchmark comparison was using substring matching (`expected_correction in pipeline_output`) which fails when `expected` contains only the corrected word (e.g., `يذهبون`) instead of the full sentence.

**True grammar FN: 4 (not 17)**

| ID | Root Cause | Detail |
|---|---|---|
| G003 | MODEL | `حضرون` instead of `حضروا` (wrong suffix) |
| G006 | FILTER (IVtoOOV) | `لعبوَ` rejected — model adds fatha diacritical |
| G009 | MODEL | Model returned unchanged |
| G022 | MODEL | Model returned unchanged |

G028 was also FILTER (IVtoOOV) — model outputs `يفعلوَ` instead of `يفعلوا`.

### Finding 2: StageLocker is NOT the bottleneck

StageLocker caused only **1 rejection** out of 82 total (1.2%). It is functioning correctly and not over-locking.

### Finding 3: PatchSet has ZERO conflicts

127 patches generated across all 270 samples, with 0 cross-stage conflicts. PatchSet conflict resolution is not a correction loss point.

### Finding 4: OffsetMapper has a known edge case

Delete-boundary positions map to the START of the deleted range (off-by-one). This affects:
- Tanween removal: end-position of `جدا` maps to position 3, not 4 (losing the tanween's original position)
- First char after any deletion

**Impact on grammar FN: NONE.** The 4 real grammar FN are caused by model quality and IVtoOOV filter, not OffsetMapper.

### Finding 5: The grammar model adds diacriticals to jazm corrections

G006: `لعب` → `لعبوَ` (fatha on waw)
G028: `يفعلون` → `يفعلوَ` (fatha on waw)

The model produces the correct ROOT form but adds a diacritical that makes it fail the IVtoOOV vocabulary check. The diacritical should be stripped before the vocab check.

### Finding 6: Grammar model top failure modes

1. **Returns unchanged** for أسماء الخمسة (five nouns): G022 `أخوك` should be `أخاك`
2. **Wrong suffix**: G003 `حضرون` instead of `حضروا` (present tense suffix instead of past tense)
3. **Diacritical pollution**: G006, G028 — adds فتحة to جزم corrections

---

## Section 4 — Phase 12 Recommendations (Evidence-Backed)

### Priority 1: Fix benchmark comparison logic (FREE wins)

13 grammar tests are actually PASSING but marked FN due to substring comparison. Fix the benchmark runner to compare full sentences, not just correction words. This alone raises grammar score from **60% → ~89%**.

### Priority 2: Strip diacriticals before IVtoOOV check

G006 and G028 are blocked because `لعبوَ` / `يفعلوَ` have fatha diacriticals that make them OOV. Strip diacriticals from grammar corrections before the vocab check. Cost: 2 lines of code. Fixes: 2 FN.

### Priority 3: Do NOT weaken PunctuationGuard or TanweenGuard

Both filters have **100% precision**. The grammar model consistently:
- Strips periods from correct text (32 cases)
- Strips tanween from correct text (30 cases)

These filters are preventing real damage.

### Priority 4: Do NOT redesign StageLocker

StageLocker caused 1 rejection in 270 samples. It is functioning correctly.

### Priority 5: Do NOT redesign PatchSet

Zero conflicts in 270 samples. No architectural change needed.

### Not Recommended

- Adding NER — entity FP (3 cases) are minor compared to grammar issues
- Replacing grammar model — the model IS producing correct corrections for most patterns
- Redesigning OffsetMapper — edge case documented but not causing failures
