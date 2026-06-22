# Benchmark Expansion Plan (Phase 12)

> [!NOTE]
> Design document only. No implementation in Phase 11.

## Current Benchmark Weaknesses

| Gap | Current | Impact |
|---|---|---|
| No real user data | 0/270 from users | Benchmark may not represent production |
| No Arabic entities | Only Latin names protected | عبدالله, المدينة unprotected |
| No mixed Arabic-English | 0 samples | Common in tech writing |
| No JSON/HTML/Markdown | Only code blocks | Web content untested |
| No partial Quran | Only exact phrases | Real-world usage untested |
| No noisy Quran | Only clean quotes | Typos in religious text untested |
| No severity weighting | All errors equal | URL corruption = tanween fix |

## Proposed New Datasets

### Dataset 8: Arabic Named Entities (30 samples)

```text
Categories:
- Person names with prepositions (عبد الله, محمد بن سلمان)
- Place names (المدينة المنورة, جبل الطور)
- Organization names (جامعة القاهرة, الأمم المتحدة)
- Historical/cultural names (صلاح الدين, ابن خلدون)
- Names with spelling errors in surrounding text

Expected behavior: Entity must remain unchanged.
```

### Dataset 9: Mixed Arabic-English (25 samples)

```text
Categories:
- Technical text with English terms (استخدمت Python لبرمجة)
- Brand names embedded (يعمل على نظام Windows)
- Academic citations with English
- Code variables in Arabic context
- Email/URL with Arabic description

Expected behavior: English portions unchanged, Arabic corrected.
```

### Dataset 10: Structured Formats (20 samples)

```text
Categories:
- JSON with Arabic values
- HTML with Arabic content
- Markdown with Arabic text
- CSV with Arabic columns
- XML/config files

Expected behavior: Structure preserved, Arabic within correctable.
```

### Dataset 11: Noisy Religious Text (20 samples)

```text
Categories:
- Quran with missing diacritics
- Quran with hamza errors
- Truncated mid-verse fragments
- Mixed religious + regular text
- Hadith with common misspellings

Expected behavior:
- Clean quotes → no modification
- Quotes with errors → correction of errors only
- Structure preserved
```

### Dataset 12: Real User Samples (30 samples)

```text
Sources:
- HF Spaces API logs (anonymized)
- Social media Arabic text (Twitter/X)
- Student essays
- Professional correspondence
- Academic writing

Expected behavior: Based on expert annotation.
```

### Dataset 13: Severity-Weighted Test Cases (20 samples)

```text
Categories by severity:
- Critical: Data corruption (dates, numbers, URLs) — weight 5.0
- High: Meaning change (word substitution, tense change) — weight 3.0
- Medium: Grammar errors (agreement, case) — weight 2.0
- Low: Style issues (tanween, spacing) — weight 1.0

Expected behavior: Weighted pass rate replaces flat accuracy.
```

## Benchmark Infrastructure Changes

### Severity Scoring

```python
SEVERITY_WEIGHTS = {
    'data_corruption': 5.0,
    'meaning_change': 3.0,
    'grammar_error': 2.0,
    'style_issue': 1.0,
}

weighted_score = sum(w * pass for w, pass in results) / sum(weights)
```

### Regression Detection

Compare new results against baseline:
- Alert if any previously-passing test now fails
- Alert if weighted score drops > 1%

### Coverage Metrics

Track which pipeline paths are exercised:
- Spelling only
- Grammar only
- Punctuation only
- Full pipeline
- Religious skip
- Structured protection
- StageLocker blocks

## Implementation Timeline

| Week | Task |
|---|---|
| 1 | Create datasets 8-10 (entities, mixed, structured) |
| 2 | Create datasets 11-12 (religious, real user) |
| 3 | Implement severity scoring + regression detection |
| 4 | Run expanded benchmark, establish new baseline |

## Total Expanded Benchmark

| Dataset | Current | New | Total |
|---|---|---|---|
| Spelling | 80 | 0 | 80 |
| Grammar | 45 | 0 | 45 |
| Punctuation | 20 | 0 | 20 |
| Entities | 30 | 30 | 60 |
| Religious | 30 | 20 | 50 |
| Structured | 35 | 20 | 55 |
| Hallucination | 30 | 0 | 30 |
| Mixed Ar-En | 0 | 25 | 25 |
| Real User | 0 | 30 | 30 |
| Severity | 0 | 20 | 20 |
| **Total** | **270** | **145** | **415** |
