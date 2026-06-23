# BAYAN v2.0 — Task List

## Phase A: Test Infrastructure ✅
- [x] Create `tests/v2/test_level1_raw.py` — Raw model tests with TP/FP/FN/TN verdicts
- [x] Create `tests/v2/test_level2_solo.py` — Solo API endpoint tests
- [x] Create `tests/v2/test_level3_integrated.py` — Full pipeline tests
- [x] Create `tests/v2/benchmark_matrix.py` — Master comparison runner
- [x] Fix verdict logic (strip terminal punctuation before comparison)
- [x] Run baseline on entities + spelling datasets
- [ ] Run full 320-test baseline across all 3 levels

## Phase A.1: Project Cleanup ✅
- [x] Archive legacy scripts (AraSpell.py, Grammer_Rules.py, PuncAra.py)
- [x] Archive 36 old phase/verification reports
- [x] Archive 23 old test files + 8 phase10 helpers
- [x] Delete 35 orphaned debug/temp files
- [x] Fix .gitignore corruption (binary null bytes)
- [x] Fix PROJECT_DESCRIPTION.md stale reference
- [x] Archive docs/audit + docs/audits

## Phase B: Extract Stages (NOT STARTED)
- [ ] Create `src/nlp/stages/spelling_stage.py`
- [ ] Create `src/nlp/stages/grammar_stage.py`
- [ ] Create `src/nlp/stages/punctuation_stage.py`
- [ ] Each stage wraps: model call → filter → verdict
- [ ] Hash (comment out) old inline stage code in `app.py`
- [ ] Re-run v2 benchmark → must match Phase A baseline

## Phase C: Extract Filters (NOT STARTED)
- [ ] Create `src/nlp/filters/` module
- [ ] Extract overlap resolution, religious guard, entity guard
- [ ] Hash old filter code in `app.py`
- [ ] Re-run v2 benchmark → must match baseline

## Phase D: Extract Preprocessors (NOT STARTED)
- [ ] Create `src/nlp/preprocessors/` module
- [ ] Extract text normalization, diacritic handling, chunk splitting
- [ ] Hash old preprocessor code in `app.py`
- [ ] Re-run v2 benchmark → must match baseline

## Phase E: Create Pipeline Orchestrator (NOT STARTED)
- [ ] Create `src/nlp/pipeline.py` — orchestrates stages via PipelineContext
- [ ] Wire `app.py` /api/analyze to use `pipeline.run(text)`
- [ ] Hash old monolithic analyze code in `app.py`
- [ ] Re-run v2 benchmark → must match baseline

## Phase F: Clean app.py (NOT STARTED)
- [ ] Move helpers (get_word_positions, OffsetMapper, etc.) to utility modules
- [ ] Remove all hashed (commented) code blocks
- [ ] app.py should only contain: Flask routes + pipeline.run() calls
- [ ] Final v2 benchmark → must match baseline
- [ ] Target: app.py < 500 lines
