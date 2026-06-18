# NLP-3.5 — Suggestion Priority System

## Priority Map

```python
PRIORITY = {
    'grammar':      3,  # Highest — always wins
    'punctuation':  2,
    'spelling':     1,
    'autocomplete': 0,  # Lowest — reserved for NLP-4
}
```

## Rules

1. **Higher priority ALWAYS wins** when spans overlap
2. **One span = one highlight** — no multi-color stacking
3. **Partial overlaps**: higher priority span kept, lower dropped entirely
4. **Suggestions sorted by priority** before resolution (highest first)

## Collision Examples

### Case A: Grammar + Spelling overlap
```
[10:20] grammar  (priority 3)
[10:20] spelling (priority 1)
→ KEEP grammar, DROP spelling
```

### Case B: Grammar + Punctuation overlap  
```
[10:20] grammar     (priority 3)
[15:25] punctuation (priority 2)
→ KEEP grammar, DROP punctuation
```

### Case C: Punctuation + Spelling overlap
```
[10:20] punctuation (priority 2)
[10:20] spelling    (priority 1)
→ KEEP punctuation, DROP spelling
```

### Case D: Partial overlap
```
[10:20] grammar     (priority 3)
[15:25] spelling    (priority 1)
→ KEEP grammar [10:20], DROP spelling entirely
```

## Implementation

Located in `src/app.py`, inside the `analyze()` function, after all three pipeline stages complete.

```python
# Sort by priority (highest first)
suggestions.sort(key=lambda s: PRIORITY.get(s['type'], 0), reverse=True)

# Claim ranges, reject overlapping lower-priority spans
for s in suggestions:
    if not overlaps_with_claimed(s):
        resolved.append(s)
        claim(s.start, s.end)
    else:
        log(f"Dropped {s.type} — conflicts with higher priority")
```

## Future: AutoComplete (NLP-4)

AutoComplete will have priority 0 (lowest). It will never override spelling, grammar, or punctuation suggestions. If a word has a correction suggestion AND an autocomplete suggestion, the correction wins.
