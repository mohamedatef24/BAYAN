# NLP-3.5 — Text Processing Strategy

## Problem

AraSpell processes text word-by-word with beam search decoding.
Each word takes ~700ms. This means:

| Text Size | Words | AraSpell Time | Feasible? |
|-----------|-------|---------------|-----------|
| 50 chars | 7 | 4.8s | ✅ |
| 100 chars | 14 | 9.2s | ✅ |
| 250 chars | 35 | 26.0s | ⚠️ Slow |
| 500 chars | 70 | ~49s (est.) | ❌ Too slow |
| 1000 chars | 140 | ~98s (est.) | ❌ Timeout risk |
| 5000 chars | 700 | ~490s (est.) | ❌ Impossible |

## Solution: Adaptive Processing

### Short Text (0–300 chars)

Full pipeline:
```
AraSpell → Grammar → Punctuation
```

All three models run. Maximum expected latency: ~40s.

### Medium Text (300–1000 chars)

Skip AraSpell:
```
Grammar → Punctuation
```

Grammar and Punctuation handle the text. Expected latency: ~28s.

### Large Text (1000+ chars)

Skip AraSpell:
```
Grammar → Punctuation
```

Same strategy as medium. Expected latency: ~30-34s.

## Implementation

```python
# In /api/analyze
text_len = len(current_text)
run_spelling = text_len <= 300
if not run_spelling:
    logger.info(f"Text length {text_len} > 300 — skipping AraSpell")
```

## Rationale

- Grammar catches most errors that AraSpell would find in long texts
- Punctuation is independent of spelling
- Users get fast feedback on long texts instead of timeouts
- Short texts still get full spelling correction

## Results

| Text Size | Before | After |
|-----------|--------|-------|
| 500 chars | >180s TIMEOUT | 28.2s ✅ |
| 1000 chars | Would timeout | 28.1s ✅ |
| 2000 chars | Would timeout | 33.8s ✅ |
