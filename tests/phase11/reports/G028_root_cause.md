# G028 Root Cause Investigation

## Input

```
لم يفعلون الواجب بعد
```

## Expected Output

```
لم يفعلون الواجب بعد
```

## Pipeline Output

```
لم يفعلون الواجب بعد
```

## Pass/Fail: ✅ PASS

## Telemetry Events (in order)

| # | Event | Details |
|---|---|---|
| 1 | grammar_raw_output | input=`لم يفعلون الواجب بعد` output=`لم يفعلوَ الواجب بعد` |
| 2 | grammar_diffs_extracted | {"count": 1, "event": "grammar_diffs_extracted", "sample_id": "G028", "dataset": |
| 3 | grammar_diff | `يفعلون` → `يفعلوَ` [3-9] |
| 4 | **REJECT** | **IVtoOOV**: `يفعلون` → `يفعلوَ` |

## Phase 10 Benchmark Data

- **Verdict**: FN
- **Root cause stage**: integration
- **Root cause detail**: Grammar model fixed it but pipeline lost the fix
- **Suggestions**: 0

## Root Cause Determination

**ROOT CAUSE: FILTER_FAILURE** — Grammar model produced the correct fix but filters rejected it.

- Rejected by: IVtoOOV
- `يفعلون` → `يفعلوَ` (filter: IVtoOOV)
