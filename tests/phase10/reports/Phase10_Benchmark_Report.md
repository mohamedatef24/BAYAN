# Phase 10 — Benchmark Report

> **Date**: 2026-06-22 | **Target**: Production API | **Total Tests**: 270

---

## 1. Aggregate Metrics

| Metric | Value |
|---|---|
| **Total Tests** | 270 |
| **Pass Rate** | **25.6%** |
| **Precision** | 0.277 |
| **Recall** | 0.557 |
| **F1** | 0.370 |
| **FPR** | 0.939 |
| **FNR** | 0.443 |
| **Overcorrection Rate** | 57.0% |
| **Undercorrection Rate** | 17.4% |
| **Latency p50** | 4,162 ms |
| **Latency p95** | 12,942 ms |

| Verdict | Count | % |
|---|---|---|
| TP (correct fix) | 59 | 21.9% |
| TN (correct no-change) | 10 | 3.7% |
| FP (overcorrection) | **154** | **57.0%** |
| FN (undercorrection) | 47 | 17.4% |
| ERROR | 0 | 0% |

---

## 2. Per-Dataset Metrics

### 2.1 Spelling (80 tests)

| Metric | Value |
|---|---|
| Pass Rate | 42.5% |
| Precision | 0.667 |
| Recall | 0.540 |
| F1 | 0.597 |
| FPR | 1.000 |
| FNR | 0.460 |
| Latency p50 | 3,080 ms |
| Latency p95 | 5,352 ms |

**Breakdown by category:**

| Category | TP | FP | TN | FN |
|---|---|---|---|---|
| hamza | 13 | 0 | 0 | 12 |
| hamza_prefix | 2 | 0 | 0 | 3 |
| ta_marbuta | 8 | 0 | 0 | 2 |
| ta_marbuta_prefix | 3 | 0 | 0 | 2 |
| alif_maqsura | 3 | 0 | 0 | 5 |
| word_split | 0 | 0 | 0 | 7 |
| correct_text | 0 | 15 | 0 | 0 |
| multi_error | 5 | 2 | 0 | 0 |

> Key: Spelling model misses 48% of errors, and ALL correct text gets punctuation added (100% FPR on correct text).

---

### 2.2 Grammar (45 tests)

| Metric | Value |
|---|---|
| Pass Rate | 26.7% |
| Precision | 0.444 |
| Recall | 0.400 |
| F1 | 0.421 |
| FPR | 1.000 |
| FNR | 0.600 |
| Latency p50 | 3,263 ms |
| Latency p95 | 4,524 ms |

**Breakdown by category:**

| Category | TP | FP | TN | FN |
|---|---|---|---|---|
| sv_agree | 0 | 0 | 0 | 10 |
| gender | 5 | 0 | 0 | 0 |
| case | 0 | 0 | 0 | 5 |
| five_nouns | 2 | 0 | 0 | 2 |
| dual | 2 | 0 | 0 | 0 |
| nasb | 3 | 0 | 0 | 1 |
| correct | 0 | 15 | 0 | 0 |

> Key: **100% failure on SV agreement** (0/10) and **100% failure on case endings** (0/5). All 15 correct grammar sentences got punctuation added.

---

### 2.3 Punctuation (20 tests)

| Metric | Value |
|---|---|
| Pass Rate | **80.0%** |
| Precision | 0.765 |
| Recall | **1.000** |
| F1 | 0.867 |
| FPR | 0.571 |
| FNR | 0.000 |
| Latency p50 | 5,119 ms |
| Latency p95 | 9,531 ms |

> Key: Best performing model. Perfect recall but over-punctuates already-correct text (4/7 correct samples modified).

---

### 2.4 Entities (30 tests)

| Metric | Value |
|---|---|
| Pass Rate | **6.7%** |
| Overcorrection Rate | **93.3%** |
| Latency p50 | 4,076 ms |

> Key: 28/30 entity contexts modified. Primary cause: punctuation adding periods, not actual entity corruption.

---

### 2.5 Religious (30 tests)

| Metric | Value |
|---|---|
| Pass Rate | **10.0%** |
| Modification Rate | **90.0%** |
| Latency p50 | 5,863 ms |
| Latency p95 | 13,356 ms |

> Key: Only 3/30 religious texts preserved (Al-Fatiha L2, Ayat al-Kursi, Takbir).

---

### 2.6 Structured Content (35 tests)

| Metric | Value |
|---|---|
| Pass Rate | **5.7%** |
| Corruption Rate | **94.3%** |
| Latency p50 | 7,652 ms |
| Latency p95 | 14,014 ms |

> Key: Only 2/35 structured content samples preserved (one URL returned before API loaded, one filepath).

---

### 2.7 Hallucination (30 tests)

| Metric | Value |
|---|---|
| Pass Rate | **0.0%** |
| Hallucination Rate | **100%** |
| Latency p50 | 11,141 ms |
| Latency p95 | 15,728 ms |

> [!CAUTION]
> **100% hallucination rate.** Every single correctly-written text was modified. The system cannot distinguish correct text from incorrect text.

---

## 3. Latency Analysis

| Dataset | p50 | p95 | Avg Text Length |
|---|---|---|---|
| Spelling | 3,080 ms | 5,352 ms | ~25 chars |
| Grammar | 3,263 ms | 4,524 ms | ~30 chars |
| Punctuation | 5,119 ms | 9,531 ms | ~40 chars |
| Entities | 4,076 ms | 6,719 ms | ~30 chars |
| Religious | 5,863 ms | 13,356 ms | ~50 chars |
| Structured | 7,652 ms | 14,014 ms | ~40 chars |
| Hallucination | 11,141 ms | 15,728 ms | ~70 chars |

**Degradation curve**: Latency scales roughly linearly with text length, with ~150ms per character for longer texts.

---

## 4. Span Alignment

| Metric | Value |
|---|---|
| Total span checks | 270 |
| Span errors | **0** |
| Span validity rate | **100%** |

✅ All spans correctly aligned.

---

## 5. Regression Analysis

| Metric | Value |
|---|---|
| Total regressions | **2** |
| Fix lost | 2 |
| Reversals | 0 |
| New errors introduced | 0 |

---

## 6. Artifacts

| File | Description |
|---|---|
| [phase10_results.json](file:///e:/Atef's Shit/tests/phase10/reports/phase10_results.json) | Raw JSON with all 270 test results |
| [benchmark_runner.py](file:///e:/Atef's Shit/tests/phase10/benchmark_runner.py) | Benchmark execution script |
| [spelling.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/spelling.json) | 80 spelling test cases |
| [grammar.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/grammar.json) | 45 grammar test cases |
| [punctuation.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/punctuation.json) | 20 punctuation test cases |
| [entities.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/entities.json) | 30 entity test cases |
| [religious.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/religious.json) | 30 religious test cases |
| [structured_content.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/structured_content.json) | 35 structured content test cases |
| [hallucination.json](file:///e:/Atef's Shit/tests/phase10/gold_datasets/hallucination.json) | 30 hallucination test cases |
