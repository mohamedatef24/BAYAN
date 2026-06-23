# NLP-3.5 — Analyze Stress Test Results

**Date:** 2026-06-18

## Test Configuration

- **API:** `https://bayan10-bayan-api.hf.space/api/analyze`
- **Timeout:** 300s
- **Base text:** Repeated Arabic sentence about AI

## Results

| Chars | Latency | Spelling | Grammar | Punctuation | Total | Suggestions | AraSpell |
|-------|---------|----------|---------|-------------|-------|-------------|----------|
| 50 | 8.7s | 4,767ms | 2,294ms | 867ms | 7,929ms | 2 | ✅ Ran |
| 100 | 12.9s | 9,236ms | 1,650ms | 1,410ms | 12,299ms | 1 | ✅ Ran |
| 250 | 37.0s | 26,000ms | 6,351ms | 4,007ms | 36,360ms | 11 | ✅ Ran |
| 500 | 28.2s | 0ms | 17,122ms | 10,496ms | 27,622ms | 8 | ⬜ Skipped |
| 1000 | 28.1s | 0ms | 15,678ms | 11,619ms | 27,304ms | 4 | ⬜ Skipped |
| 2000 | 33.8s | 0ms | 18,505ms | 11,765ms | 30,284ms | 4 | ⬜ Skipped |

## Analysis

### AraSpell is the bottleneck

- 50 chars (7 words): 4.8s → ~685ms/word
- 100 chars (14 words): 9.2s → ~660ms/word
- 250 chars (35 words): 26.0s → ~743ms/word

### Smart processing eliminates timeouts

For 500+ chars, AraSpell is skipped. Grammar + Punctuation handle the text:
- Grammar: 15-18s for 500-2000 chars
- Punctuation: 10-12s for 500-2000 chars
- Total: ~28-34s (well within 300s timeout)

### All sizes pass ✅

No timeouts. No errors. No crashes.
