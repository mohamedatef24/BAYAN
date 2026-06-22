# Chapter 5: Testing and Evaluation

## 5.1 Overview

This chapter describes the testing methodology, test infrastructure, and evaluation results for the Bayan system. Testing was conducted at four levels: unit testing of individual NLP components, integration testing of the API pipeline, end-to-end (E2E) testing of the Chrome extension inline engine, and a production readiness audit. All test results reported in this chapter represent the final state of the system after the Phase 7.1 stabilization sprint.

## 5.2 Testing Methodology

### 5.2.1 Test Framework and Infrastructure

| Component | Tool | Purpose |
|---|---|---|
| Backend Unit Tests | pytest | NLP pipeline, API endpoints |
| Extension E2E Tests | Playwright | Chrome extension inline engine |
| Production Audit | Custom Python scripts | Architecture audit, parity checks |
| Load Testing | Custom stress test scripts | API performance under load |
| Manual Testing | Browser DevTools | UI/UX verification |

### 5.2.2 Test File Inventory

| Test File | Scope | Tests |
|---|---|---|
| `tests/test_pipeline.py` | Pipeline hardening (PipelineContext, PatchSet, StageLocker, OffsetMapper) | 49 |
| `test_phase6.py` | Phase 6 inline engine integration | 8 |
| `test_dialect.py` | Dialect-to-MSA conversion | ~15 |
| `test_quran.py` | Quran search engine | ~20 |
| `test_quran_extended.py` | Extended Quran search scenarios | ~15 |
| `test_quran_final.py` | Final Quran verification | ~10 |
| `test_analyze_api.py` | `/api/analyze` endpoint | ~5 |
| `test_analyze_methods.py` | Analysis helper methods | ~5 |
| `test_model_load.py` | Model loading verification | ~3 |
| `summarization_test.py` | Summarization model quality | ~5 |
| `test_renderer.js` | Frontend renderer (Node.js) | ~10 |
| `extension/tests/` | Extension unit tests | ~15 |
| `verify_all.py` | Comprehensive verification suite | ~30 |

## 5.3 Unit Testing: Pipeline Hardening

### 5.3.1 Test Suite Structure

The pipeline hardening test suite (`tests/test_pipeline.py`) contains 49 test cases organized into four test classes:

```
tests/test_pipeline.py
├── TestOffsetMapper (12 tests)
│   ├── test_identity_mapping
│   ├── test_simple_replacement
│   ├── test_insertion
│   ├── test_deletion
│   ├── test_multiple_changes
│   ├── test_reverse_map_at_boundaries
│   ├── test_forward_map_identity
│   ├── test_forward_map_after_insertion
│   ├── test_forward_map_after_deletion
│   ├── test_monotonicity_guard
│   ├── test_empty_to_nonempty
│   └── test_nonempty_to_empty
├── TestStageLocker (10 tests)
│   ├── test_lock_and_check
│   ├── test_non_overlapping_not_locked
│   ├── test_partial_overlap_locked
│   ├── test_is_locked_by_returns_info
│   ├── test_is_locked_by_returns_none
│   ├── test_multiple_locks
│   ├── test_update_via_mapper_identity
│   ├── test_update_via_mapper_shift
│   ├── test_zero_width_lock
│   └── test_adjacent_locks_no_overlap
├── TestCorrectionPatch (12 tests)
│   ├── test_patch_creation
│   ├── test_patch_to_dict
│   ├── test_patchset_no_overlap
│   ├── test_patchset_overlap_priority
│   ├── test_patchset_overlap_confidence
│   ├── test_patchset_deterministic_ordering
│   ├── test_patchset_three_way_overlap
│   ├── test_patchset_adjacent_no_overlap
│   ├── test_patchset_empty
│   ├── test_patchset_identical_ranges
│   ├── test_patch_id_uniqueness
│   └── test_to_dict_excludes_current_coords
└── TestPipelineContext (15 tests)
    ├── test_init
    ├── test_map_to_original_no_mutations
    ├── test_map_to_original_after_mutation
    ├── test_add_patch_creates_both_coords
    ├── test_add_patch_locks_range
    ├── test_mutate_text_identity
    ├── test_mutate_text_updates_current
    ├── test_mutate_text_appends_mapper
    ├── test_full_pipeline_simulation
    ├── test_spelling_then_grammar_coords
    ├── test_three_stage_pipeline
    ├── test_locked_range_survives_mutation
    ├── test_overlap_resolution_after_pipeline
    ├── test_stage_priority_ordering
    └── test_pipeline_with_empty_stages
```

### 5.3.2 Test Results

```
================================= test session starts ==================================
platform win32 -- Python 3.12.x
collected 49 items

tests/test_pipeline.py::TestOffsetMapper::test_identity_mapping PASSED
tests/test_pipeline.py::TestOffsetMapper::test_simple_replacement PASSED
tests/test_pipeline.py::TestOffsetMapper::test_insertion PASSED
tests/test_pipeline.py::TestOffsetMapper::test_deletion PASSED
...
tests/test_pipeline.py::TestPipelineContext::test_three_stage_pipeline PASSED
tests/test_pipeline.py::TestPipelineContext::test_stage_priority_ordering PASSED
tests/test_pipeline.py::TestPipelineContext::test_pipeline_with_empty_stages PASSED

================================ 49 passed in 0.42s ===================================
```

**Result: 49/49 tests passed (100%).**

### 5.3.3 Key Test Scenarios

**OffsetMapper — Monotonicity Guard:**
```python
def test_monotonicity_guard(self):
    """Forward-mapped range must never be inverted (start > end)."""
    mapper = OffsetMapper("ABCDE", "AXE")  # BCE deleted, B→X
    new_start, new_end = mapper.forward_map_range(1, 4)
    assert new_start <= new_end  # Monotonicity guaranteed
```

**PatchSet — Three-Way Overlap Resolution:**
```python
def test_patchset_three_way_overlap(self):
    """When 3 patches overlap the same range, highest priority wins."""
    ps = PatchSet()
    ps.add(CorrectionPatch(stage='spelling', priority=1, ...))    # Range [0:5]
    ps.add(CorrectionPatch(stage='grammar', priority=3, ...))     # Range [2:7]
    ps.add(CorrectionPatch(stage='punctuation', priority=2, ...)) # Range [3:8]
    resolved = ps.resolve_overlaps()
    assert len(resolved) == 1
    assert resolved[0].stage == 'grammar'  # Highest priority wins
```

**PipelineContext — Full Pipeline Simulation:**
```python
def test_three_stage_pipeline(self):
    """Simulate Spelling → Grammar → Punctuation with coordinate mapping."""
    ctx = PipelineContext("هذة المدرسه جميله")
    # Spelling: هذة → هذه
    ctx.add_patch('spelling', 0, 3, 'هذه', confidence=0.9)
    ctx.mutate_text("هذه المدرسه جميله", OffsetMapper)
    # Grammar: المدرسه → المدرسة
    ctx.add_patch('grammar', 4, 11, 'المدرسة', confidence=1.0)
    ctx.mutate_text("هذه المدرسة جميله", OffsetMapper)
    # Verify original coordinates
    suggestions = ctx.patches.to_list()
    assert all(s['start'] >= 0 for s in suggestions)
```

## 5.4 Integration Testing: API Endpoints

### 5.4.1 Spelling API Tests

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Basic hamza correction | "انا طالب" | "أنا طالب" | ✅ |
| Ta marbuta fix | "المدرسه" | "المدرسة" | ✅ |
| Word split | "فيالمدرسة" | "في المدرسة" | ✅ |
| Numeral protection | "عام 2024" | "عام 2024" (unchanged) | ✅ |
| Directional block | "كان" → "كأن" blocked | Input preserved | ✅ |
| Pronoun suffix guard | "فتأملته" → "فتأملتة" blocked | Input preserved | ✅ |
| IV→IV guard | "وكان" → "وكأن" blocked | Input preserved | ✅ |

### 5.4.2 Grammar API Tests

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Preposition case marking | "في المهندسون" | "في المهندسين" | ✅ |
| Gender agreement | "هذان الطالبتان" | "هاتان الطالبتان" | ✅ |
| Five nouns after إنّ | "إن أبوك" | "إن أباك" | ✅ |
| Number preservation | "عدد 15 طالب" | Digits unchanged | ✅ |
| Hallucination rejection | Jaccard < 0.3 rejected | Original preserved | ✅ |

### 5.4.3 Punctuation API Tests

| Test Case | Input | Expected | Status |
|---|---|---|---|
| Period insertion | "ذهبت إلى المدرسة" | "ذهبت إلى المدرسة." | ✅ |
| Non-punct change strip | Model changes word → reverted | Only punct kept | ✅ |
| Aggregate cap | >3 punct patches | Capped to 3 | ✅ |

### 5.4.4 `/api/analyze` Pipeline Tests

| Test Case | Scenario | Status |
|---|---|---|
| Empty text | Returns error 400 | ✅ |
| HTML injection | Tags stripped | ✅ |
| Non-Arabic text | Ratio < 0.3 → no analysis | ✅ |
| Short text (<300 chars) | Full pipeline runs | ✅ |
| Medium text (300-1000) | Spelling skipped | ✅ |
| Stage failure recovery | Partial result returned | ✅ |
| Overlap resolution | Grammar wins over spelling | ✅ |

## 5.5 End-to-End Testing: Chrome Extension

### 5.5.1 Inline Engine Test Suite

The inline engine E2E tests verify the content script behavior on real web pages using Playwright:

| Test | Description | Status |
|---|---|---|
| Field Detection | Detects `<textarea>` elements | ✅ |
| ContentEditable Detection | Detects `[contenteditable]` elements | ✅ |
| Dynamic Field Detection | MutationObserver catches new fields | ✅ |
| Debounced Analysis | Analysis triggers after 800ms idle | ✅ |
| Hash Deduplication | No re-analysis for unchanged text | ✅ |
| Protected Site Skip | No injection on chrome:// pages | ✅ |
| Highlight Rendering | Overlay spans positioned correctly | ✅ |
| Error Recovery | Backoff on API failure | ✅ |

### 5.5.2 Popup/Side Panel Parity

A parity audit verified that the popup and side panel produce identical outputs:

```
Parity Check Results:
  ✅ Same API call format
  ✅ Same response parsing
  ✅ Same renderer (bayan-renderer.js)
  ✅ Same suggestion display format
  ✅ Same apply/reject behavior
```

## 5.6 Production Readiness Audit

### 5.6.1 Audit Methodology

A comprehensive architectural audit was conducted during Phase 7, examining all source files for:

- Architecture flaws
- Browser compatibility issues
- MV3 violations
- Memory leaks
- Race conditions
- Duplicated logic
- Dead code
- Maintainability problems

### 5.6.2 Critical Findings (Resolved)

| ID | Finding | Severity | Resolution |
|---|---|---|---|
| F01 | `Promise.race` timeout timer never cleared in `analysis-controller.js` | Critical | Timer cleanup added |
| F02 | Duplicated retry layers (API, analysis-controller, bayan-api) | Major | Consolidated to single layer |
| F03 | Duplicated cache layers (hash check in 3 places) | Major | Consolidated to `hash.js` |
| F04 | Duplicated API URL definitions (constants.js, config.js, bayan-api.js) | Major | Single source of truth in `constants.js` |
| F05 | Version string drift (manifest.json vs constants.js) | Minor | Single canonical version |
| F06 | Dead code in bayan-state.js | Minor | Removed |

### 5.6.3 Stabilization Sprint Results

The Phase 7.1 stabilization sprint addressed all findings:

```
Code Changes:
  Lines Removed: 458
  Lines Added: 112
  Net Reduction: 346 lines

Systems Consolidated:
  ✅ Retry: 3 layers → 1 layer
  ✅ Cache: 3 checks → 1 check
  ✅ Hash: 2 implementations → 1 (shared/hash.js)
  ✅ API URL: 3 definitions → 1 (constants.js)
  ✅ Version: 2 definitions → 1 (manifest.json)

Tests After Cleanup:
  49/49 unit tests passed
  E2E inline engine tests passed
  Popup/sidepanel parity confirmed
```

## 5.7 Model Evaluation

### 5.7.1 Spelling Correction Evaluation

The AraSpell model was evaluated on a test set of Arabic text with known spelling errors:

**Guard Effectiveness:**

| Guard | Purpose | False Positives Prevented |
|---|---|---|
| Numeral Protection | Prevents digit hallucination | 100% of numeral-containing inputs |
| Directional Blocks | Prevents meaning-changing substitutions | كان↔كأن, هذه↔هذة, etc. |
| IV→IV Guard | Prevents valid word → valid word changes | ~40% of model proposals |
| Pronoun Suffix | Prevents ته → تة corruption | 100% of ته patterns |
| Levenshtein Filter | Prevents root-changing corrections | dist > 2 or ratio > 50% |
| Orthographic Filter | Only allows ه↔ة, ا↔أ↔إ↔آ, ي↔ى changes | All non-orthographic blocked |

### 5.7.2 Summarization Evaluation

The summarization model was evaluated qualitatively:

- **Faithful summaries**: Greedy decoding (num_beams=1) produced summaries with high lexical overlap with source text.
- **Hallucination detection**: The `_needs_fallback()` function (overlap_ratio < 0.35 OR SequenceMatcher ratio < 0.22) successfully identified and fell back on hallucinated outputs.
- **Length control**: Three-tier length system (short/medium/long) produced appropriately sized summaries.

### 5.7.3 Grammar Correction Evaluation

The grammar model (Gemma 3 + CAMeL Tools post-processing) was evaluated on common Arabic grammar error patterns:

| Error Category | Detection Rate | Notes |
|---|---|---|
| Preposition case marking | High | Regex-based, deterministic |
| Gender agreement (demonstratives) | High | Pattern matching |
| Five nouns declension | High | Rule-based |
| Verb nasb/jazm | Moderate | Requires POS accuracy |
| Subject-verb agreement (SVO) | Moderate | Requires plural confirmation |

### 5.7.4 Punctuation Evaluation

The PuncAra-v1 model was evaluated for:

- **Precision of punctuation insertion**: High — the Fix P1 layer strips non-punctuation changes.
- **Safety**: The `validate_punctuation_diff()` function ensures only punctuation characters are modified.
- **Aggregate cap**: Maximum 3 punctuation patches per response prevents over-punctuation.

## 5.8 Performance Benchmarks

### 5.8.1 API Response Times

| Endpoint | Typical Latency | Notes |
|---|---|---|
| `/api/health` | < 10ms | No model inference |
| `/api/spelling` | 1–5s | Depends on text length |
| `/api/grammar` | 2–8s | Gradio round-trip |
| `/api/punctuation` | 0.5–3s | Local model, windowed |
| `/api/summarize` | 1–3s | mBART greedy |
| `/api/analyze` (short) | 3–15s | Full pipeline |
| `/api/analyze` (medium) | 2–10s | Grammar + Punctuation only |
| `/api/autocomplete` | 0.5–2s | Hybrid scoring |
| `/api/dialect` | 1–3s | mT5 beam search |
| `/api/quran` | < 100ms | SQLite query |

### 5.8.2 Memory Usage

| Model | Approximate RAM |
|---|---|
| Summarization (mBART, float16) | ~600MB |
| Spelling (AraBERT Enc-Dec) | ~500MB |
| Grammar (Gemma 3, float32) | ~2GB |
| Punctuation (PuncAra-v1) | ~400MB |
| Autocomplete (AraGPT2-Base) | ~500MB |
| Dialect (mT5, float16) | ~300MB |
| CAMeL Tools (MLE data) | ~200MB |
| **Total (all loaded)** | **~4.5GB** |

### 5.8.3 Gunicorn Configuration

```python
# Single worker to minimize RAM
# Timeout 300s: full pipeline can take up to 90s
CMD ["gunicorn", "--chdir", "src", "app:app",
     "--bind", "0.0.0.0:7860",
     "--timeout", "300",
     "--workers", "1"]
```

## 5.9 Known Limitations

### 5.9.1 Spelling

- **AraSpell skipped for texts > 300 characters** due to performance constraints.
- **Shadda duplication in isolation**: AraSpell duplicates shadda-bearing words in isolation (إنّ→إن إن), but handles them correctly in sentence context.
- **Confidence dampening for rare words**: OOV→IV corrections receive dampened confidence (0.5 instead of 0.9), which may under-flag genuine spelling errors on rare vocabulary.

### 5.9.2 Grammar

- **Gradio dependency**: Grammar correction requires network access to the Gradio Space, adding latency and a single point of failure.
- **Transient rate limiting**: Gradio Spaces may rate-limit under heavy usage (429 responses).
- **CAMeL Tools MLE accuracy**: The MLE disambiguator has ~90% POS accuracy, leading to occasional incorrect rule application.

### 5.9.3 Punctuation

- **Over-punctuation tendency**: The PuncAra model occasionally inserts excessive punctuation, mitigated by the 3-patch aggregate cap.
- **Trained on corrected data**: The model's training data contained spelling/grammar corrections alongside punctuation, necessitating the Fix P1 stripping layer.

### 5.9.4 Extension

- **Chrome-only**: The extension requires a Chromium-based browser (Chrome, Edge, Brave).
- **Protected pages**: Cannot inject on chrome://, chrome-extension://, or Chrome Web Store pages.
- **Shadow DOM**: Cannot access text fields inside Shadow DOM boundaries.
