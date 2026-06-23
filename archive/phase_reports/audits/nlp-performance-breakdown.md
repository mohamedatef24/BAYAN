# NLP-3.5 — Per-Stage Performance Breakdown

**Date:** 2026-06-18

## AraSpell (Spelling)

| Metric | Value |
|--------|-------|
| Avg latency/word | ~700ms |
| Total for 50 chars | 4,767ms |
| Total for 100 chars | 9,236ms |
| Total for 250 chars | 26,000ms |
| Max text before skip | 300 chars |
| Processing | Word-by-word beam search |

> AraSpell is the primary bottleneck. It uses an encoder-decoder model with beam search, processing each word individually. ~700ms per word adds up quickly.

## Grammar (Gradio Client)

| Metric | Value |
|--------|-------|
| Short text (50 chars) | 2,294ms |
| Medium text (250 chars) | 6,351ms |
| Long text (1000 chars) | 15,678ms |
| Max observed | 18,505ms |
| Processing | Full-text via Gradio API |

> Grammar scales sub-linearly. It sends the full text to the Gradio Space in one call. Network latency dominates.

## PuncAra-v1 (Punctuation)

| Metric | Value |
|--------|-------|
| Short text (50 chars) | 867ms |
| Medium text (250 chars) | 4,007ms |
| Long text (1000 chars) | 11,619ms |
| Max observed | 11,765ms |
| Processing | Stride-chunking encoder-decoder |

> PuncAra-v1 uses stride-based chunking for long texts. Scales roughly linearly but stays under 12s for 2000 chars.

## Combined Pipeline

| Text Size | Spelling | Grammar | Punctuation | Overhead | Total |
|-----------|----------|---------|-------------|----------|-------|
| 50 chars | 4,767ms | 2,294ms | 867ms | 1ms | 7,929ms |
| 100 chars | 9,236ms | 1,650ms | 1,410ms | 3ms | 12,299ms |
| 250 chars | 26,000ms | 6,351ms | 4,007ms | 2ms | 36,360ms |
| 500 chars | SKIP | 17,122ms | 10,496ms | 4ms | 27,622ms |
| 1000 chars | SKIP | 15,678ms | 11,619ms | 7ms | 27,304ms |
| 2000 chars | SKIP | 18,505ms | 11,765ms | 14ms | 30,284ms |
