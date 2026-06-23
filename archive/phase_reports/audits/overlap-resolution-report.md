# NLP-3.5 — Overlap Resolution Report

## Problem

Before hardening, the pipeline had a partial dedup system that ONLY handled:
- Spelling vs Grammar (exact position match)

Missing cases:
- Grammar vs Punctuation overlap ❌
- Punctuation vs Spelling overlap ❌  
- Partial overlaps (ranges that partially intersect) ❌

## Solution: Global Overlap Resolver

### Algorithm

1. Sort all suggestions by priority (highest first)
2. Process each suggestion in priority order
3. Check if the suggestion's `[start, end)` range overlaps with any already-claimed range
4. If no overlap → add to resolved list, claim the range
5. If overlap → drop the suggestion (log it)

### Overlap Detection

Two spans `[a, b)` and `[c, d)` overlap if:
```
a < d AND b > c
```

This catches:
- Exact overlaps: `[10,20]` vs `[10,20]`
- Partial overlaps: `[10,20]` vs `[15,25]`
- Contained spans: `[10,20]` vs `[12,18]`

## Test Results (Post-Hardening)

| Test | Suggestions | Overlaps | Status |
|------|-------------|----------|--------|
| المهندسون يعملوا...الأجتماع | 3 | 0 | ✅ CLEAN |
| اناا ذهبت الي المدرسه | 4 | 0 | ✅ CLEAN |
| هو ذهبوا الي المكتبه | 4 | 0 | ✅ CLEAN |
| الطقص جميل اليوم | 3 | 0 | ✅ CLEAN |

## Before vs After

The sentence `المهندسون يعملوا في المصنع والطالبات حضروا الأجتماع` previously produced a grammar+punctuation overlap at position `[43,51]`. After the global resolver, only the grammar suggestion (priority 3) is kept.

## UI Guarantee

The frontend is now guaranteed:
- ❌ No word has red + yellow + green simultaneously
- ❌ No stacked highlights
- ❌ No duplicate spans
- ✅ Deterministic rendering (one span = one color)
