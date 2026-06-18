# BAYAN — Pipeline Locking System (DANG)

## Directed Acyclic NLP Graph

```
Spelling (LOCK) → Grammar (LOCK) → Punctuation (LOCK) → Final Output
```

No cycles. No feedback loops. No reprocessing.

---

## Architecture

### StageLockManager

Located at: `src/nlp/stage_lock.py`

```python
class StageLockManager:
    def begin_stage(stage_name)   # Validate execution order
    def end_stage(stage_name)     # Mark stage as completed (no re-entry)
    def lock_span(start, end, source)  # Register immutable span
    def is_locked(start, end)     # Check if span is locked
    def filter_suggestions(...)   # Remove backward-mutation attempts
```

### Execution Order (Enforced)

```python
STAGE_ORDER = {
    'spelling': 1,      # Runs FIRST
    'grammar': 2,       # Runs SECOND, on spelling output only
    'punctuation': 3,   # Runs THIRD, on grammar output only
    'autocomplete': 4,  # Future NLP-4
}
```

### Hard Rules

| Rule | Description |
|------|-------------|
| **Write Once** | Once a stage modifies a span, it becomes LOCKED |
| **Forward Only** | Each stage reads ONLY from the previous stage's output |
| **No Backward Mutation** | Later stages cannot re-trigger earlier ones |
| **Order Validation** | `begin_stage()` raises `ValueError` if out-of-order |

---

## Pipeline Execution Flow

```
1. lock_manager = StageLockManager()

2. lock_manager.begin_stage('spelling')
   → AraSpell runs on raw input
   → Spelling suggestions generated
   → lock_manager.end_stage('spelling')
   → Spelling spans LOCKED ❄️

3. lock_manager.begin_stage('grammar')
   → Grammar runs on spelling-corrected text
   → Grammar suggestions generated
   → lock_manager.end_stage('grammar')
   → Grammar spans LOCKED ❄️

4. lock_manager.begin_stage('punctuation')
   → PuncAra-v1 runs on grammar-corrected text
   → Punctuation suggestions generated
   → lock_manager.end_stage('punctuation')
   → Punctuation spans LOCKED ❄️

5. Global Overlap Resolver
   → Priority: grammar(3) > punctuation(2) > spelling(1)
   → One span = one highlight

6. Response
   → suggestions + timing_ms + pipeline metadata
```

---

## Forbidden Behaviors

| ❌ Forbidden | Why |
|-------------|-----|
| Grammar output → Spelling | Backward flow |
| Punctuation output → Grammar | Backward flow |
| Punctuation output → Spelling | Backward flow |
| Re-analysis of corrected text | Would cause oscillation |
| Grammar re-run after punctuation | Stage already locked |

---

## API Response (New `pipeline` Field)

```json
{
  "pipeline": {
    "stages_completed": ["spelling", "grammar", "punctuation"],
    "locked_spans": 7,
    "flow": "spelling → grammar → punctuation"
  }
}
```

---

## Distinction: Priority vs Order

| Concept | Purpose | Values |
|---------|---------|--------|
| **Execution Order** | Which stage runs first | spelling(1) → grammar(2) → punctuation(3) |
| **UI Priority** | Which suggestion wins on overlap | grammar(3) > punctuation(2) > spelling(1) |

These are INDEPENDENT. Priority affects display, not execution.
