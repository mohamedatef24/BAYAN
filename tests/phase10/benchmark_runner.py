"""
BAYAN Phase 10 — Unified Benchmark Runner
==========================================
Runs ALL gold datasets through raw models AND full pipeline.
Performs root cause attribution for every failure.
Generates regression analysis and stage interaction matrix.

Usage:
    python tests/phase10/benchmark_runner.py [--url URL] [--dataset NAMES] [--out DIR]
"""
import argparse, json, time, re, os, sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
import requests

DEFAULT_URL = "https://bayan10-bayan-api.hf.space"
GOLD_DIR = Path(__file__).parent / "gold_datasets"
REPORT_DIR = Path(__file__).parent / "reports"

# ═══════════════════════════════════════════════════════════════
# API Client
# ═══════════════════════════════════════════════════════════════
class API:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.s = requests.Session()
        self.s.headers['Content-Type'] = 'application/json'

    def _post(self, ep, payload, timeout=180):
        t0 = time.time()
        try:
            r = self.s.post(f"{self.base}{ep}", json=payload, timeout=timeout)
            ms = int((time.time()-t0)*1000)
            d = r.json(); d['_ms'] = ms; d['_status'] = r.status_code
            return d
        except requests.Timeout:
            return {'error':'TIMEOUT','_ms':int((time.time()-t0)*1000),'_status':0}
        except Exception as e:
            return {'error':str(e),'_ms':int((time.time()-t0)*1000),'_status':0}

    def analyze(self, text): return self._post('/api/analyze', {'text': text})
    def grammar(self, text): return self._post('/api/grammar', {'text': text})
    def punctuation(self, text): return self._post('/api/punctuation', {'text': text})

# ═══════════════════════════════════════════════════════════════
# Result Types
# ═══════════════════════════════════════════════════════════════
@dataclass
class BenchResult:
    id: str
    dataset: str
    category: str
    input: str
    expected: str = ""
    severity: str = ""
    # Pipeline results
    pipeline_output: str = ""
    pipeline_suggestions: list = field(default_factory=list)
    pipeline_timing: dict = field(default_factory=dict)
    pipeline_ms: int = 0
    # Raw model results
    grammar_raw_output: str = ""
    grammar_raw_ms: int = 0
    punctuation_raw_output: str = ""
    punctuation_raw_ms: int = 0
    # Verdicts
    pipeline_verdict: str = ""  # TP, FP, TN, FN, ERROR
    pipeline_detail: str = ""
    # Root cause
    root_cause_component: str = ""  # MODEL, RULE, PIPELINE, SPAN, UI, UNKNOWN
    root_cause_stage: str = ""      # spelling, grammar, punctuation, integration
    root_cause_detail: str = ""
    # Regression
    regression_type: str = ""  # fix_lost, reversal, introduced_error, none
    regression_detail: str = ""
    # Span check
    span_valid: bool = True
    span_detail: str = ""

def strip_punct_only(text):
    """Remove ONLY punctuation chars to compare word content."""
    return re.sub(r'[.,،؛؟!:;?!\s\u060C\u061B\u061F]+', ' ', text).strip()

def words(text):
    return re.sub(r'[.,،؛؟!:;?!\s]+', ' ', text).strip().split()

# ═══════════════════════════════════════════════════════════════
# Benchmark Modules
# ═══════════════════════════════════════════════════════════════

def run_spelling_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'spelling', s.get('category',''), s['input'],
                        s.get('expected',''), s.get('severity',''))
        # Pipeline
        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        r.pipeline_timing = resp.get('timing_ms', {})
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp['error']
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        original = resp.get('original', s['input'])
        changed = r.pipeline_output != original

        error_words = s.get('error_words', [])
        has_errors = len(error_words) > 0

        # Span check
        for sg in r.pipeline_suggestions:
            actual_slice = original[sg['start']:sg['end']]
            if actual_slice != sg.get('original', ''):
                r.span_valid = False
                r.span_detail = f"SPAN[{sg['start']}:{sg['end']}] exp='{sg.get('original','')}' got='{actual_slice}'"
                break

        if has_errors:
            unfixed = [w for w in error_words if w in r.pipeline_output]
            if unfixed:
                r.pipeline_verdict = "FN"
                r.pipeline_detail = f"Errors NOT fixed: {unfixed}"
            else:
                r.pipeline_verdict = "TP"
                r.pipeline_detail = f"{len(r.pipeline_suggestions)} fixes"
        else:
            if changed:
                # Check what changed
                sugg_types = [sg.get('type','') for sg in r.pipeline_suggestions]
                changes = [f"{sg.get('original','')}→{sg.get('correction','')}" for sg in r.pipeline_suggestions]
                r.pipeline_verdict = "FP"
                r.pipeline_detail = f"Overcorrected: {changes[:3]}"
                # Root cause: if only punctuation suggestions → punctuation model
                if all(t == 'punctuation' for t in sugg_types):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "punctuation"
                    r.root_cause_detail = "Punctuation model added marks to correct text"
                elif any(t == 'grammar' for t in sugg_types):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "grammar"
                    r.root_cause_detail = "Grammar model made unnecessary changes"
                else:
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "spelling"
                    r.root_cause_detail = "Spelling model overcorrected"
            else:
                r.pipeline_verdict = "TN"
                r.pipeline_detail = "Correctly unchanged"

        # Root cause for FN
        if r.pipeline_verdict == "FN":
            r.root_cause_component = "MODEL"
            r.root_cause_stage = "spelling"
            r.root_cause_detail = f"Spelling model missed: {s.get('error_words',[])}"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms)")
        results.append(r)
    return results

def _strip_diacritics(text):
    """Strip Arabic diacritics for comparison."""
    return re.sub(r'[\u064B-\u065F\u0670]', '', text)

def _word_in_text(word, text):
    """Check if word appears as a standalone word in text (not as substring of another word)."""
    # Strip diacritics for fair comparison
    word_clean = _strip_diacritics(word)
    text_clean = _strip_diacritics(text)
    text_words = text_clean.split()
    return word_clean in text_words

def _expected_fix_present(expected_fix, output):
    """Check if the expected fix (or any alternative) is present in the output.
    expected_fix can contain / for alternatives: 'ذهبن/ذهبت' """
    if not expected_fix:
        return False
    output_clean = _strip_diacritics(output)
    output_words = output_clean.split()
    alternatives = [_strip_diacritics(alt.strip()) for alt in expected_fix.split('/')]
    for alt in alternatives:
        if alt in output_words:
            return True
    return False

def run_grammar_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'grammar', s.get('category',''), s['input'],
                        s.get('expected_fix',''), s.get('severity',''))

        # Raw grammar
        resp_g = api.grammar(s['input'])
        r.grammar_raw_ms = resp_g.get('_ms', 0)
        r.grammar_raw_output = resp_g.get('corrected_text', resp_g.get('corrected', ''))

        # Pipeline
        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        r.pipeline_timing = resp.get('timing_ms', {})
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp.get('error','')
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        original = resp.get('original', s['input'])
        changed = r.pipeline_output != original
        error_words = s.get('error_words', [])
        has_errors = len(error_words) > 0
        expected_fix = s.get('expected_fix', '')

        # Span check
        for sg in r.pipeline_suggestions:
            actual_slice = original[sg['start']:sg['end']]
            if actual_slice != sg.get('original', ''):
                r.span_valid = False
                r.span_detail = f"SPAN mismatch"
                break

        if has_errors:
            # ── Phase 12 (B2): Improved grammar comparison ──
            # Use word-boundary matching instead of substring matching.
            # Also check if expected_fix is present in output (sentence-level validation).
            unfixed = [w for w in error_words if _word_in_text(w, r.pipeline_output)]

            # Secondary check: even if error word seems present,
            # check if the expected fix is ALSO present (grammar may have
            # added the fix while the error word exists in context)
            fix_present = _expected_fix_present(expected_fix, r.pipeline_output) if expected_fix else False

            if unfixed and not fix_present:
                r.pipeline_verdict = "FN"
                r.pipeline_detail = f"Errors NOT fixed: {unfixed}"
                # Root cause: did raw grammar fix it?
                raw_unfixed = [w for w in error_words if _word_in_text(w, r.grammar_raw_output)]
                raw_fixed = len(raw_unfixed) == 0
                if raw_fixed:
                    r.root_cause_component = "PIPELINE"
                    r.root_cause_stage = "integration"
                    r.root_cause_detail = "Grammar model fixed it but pipeline lost the fix"
                else:
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "grammar"
                    r.root_cause_detail = f"Grammar model did not fix: {unfixed}"
            else:
                r.pipeline_verdict = "TP"
                if fix_present:
                    r.pipeline_detail = f"Fixed (expected fix present)"
                else:
                    r.pipeline_detail = f"Fixed (error word removed)"
        else:
            if changed:
                sugg_types = [sg.get('type','') for sg in r.pipeline_suggestions]
                changes = [f"{sg.get('original','')}→{sg.get('correction','')}" for sg in r.pipeline_suggestions]
                r.pipeline_verdict = "FP"
                r.pipeline_detail = f"Overcorrected: {changes[:3]}"
                if all(t == 'punctuation' for t in sugg_types):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "punctuation"
                    r.root_cause_detail = "Punctuation over-injection on correct grammar text"
                else:
                    raw_changed = r.grammar_raw_output != s['input']
                    if raw_changed:
                        r.root_cause_component = "MODEL"
                        r.root_cause_stage = "grammar"
                        r.root_cause_detail = f"Grammar model hallucinated"
                    else:
                        r.root_cause_component = "MODEL"
                        r.root_cause_stage = "punctuation"
                        r.root_cause_detail = "Punctuation model caused FP"
            else:
                r.pipeline_verdict = "TN"
                r.pipeline_detail = "Correctly unchanged"

        # Regression: did grammar fix get lost in pipeline?
        if has_errors and r.grammar_raw_output != s['input']:
            raw_fixed_words = [w for w in error_words if not _word_in_text(w, r.grammar_raw_output)]
            pipeline_fixed = [w for w in error_words if not _word_in_text(w, r.pipeline_output)]
            lost = set(raw_fixed_words) - set(pipeline_fixed)
            if lost:
                r.regression_type = "fix_lost"
                r.regression_detail = f"Grammar fixed {raw_fixed_words} but pipeline lost {list(lost)}"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms) raw_g={r.grammar_raw_ms}ms")
        results.append(r)
    return results

def run_punctuation_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'punctuation', s.get('category',''), s['input'],
                        severity=s.get('severity',''))

        # Raw punctuation
        resp_p = api.punctuation(s['input'])
        r.punctuation_raw_ms = resp_p.get('_ms', 0)
        r.punctuation_raw_output = resp_p.get('corrected_text', resp_p.get('corrected', ''))

        # Pipeline
        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp.get('error','')
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])

        should_add = s.get('should_add_punct', False)
        word_pres = s.get('expected_words_unchanged', False)

        # Check word preservation
        if word_pres or s.get('category') == 'word_preservation':
            orig_words = strip_punct_only(s['input'])
            raw_words = strip_punct_only(r.punctuation_raw_output)
            if orig_words != raw_words:
                r.pipeline_verdict = "FP"
                r.pipeline_detail = f"WORD CHANGE in punct: '{orig_words[:50]}' → '{raw_words[:50]}'"
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "punctuation"
                r.root_cause_detail = "Punctuation model changed words"
            else:
                r.pipeline_verdict = "TN"
                r.pipeline_detail = "Words preserved"
        elif should_add:
            if r.punctuation_raw_output != s['input']:
                r.pipeline_verdict = "TP"; r.pipeline_detail = "Punctuation added"
            else:
                r.pipeline_verdict = "FN"; r.pipeline_detail = "No punctuation added"
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "punctuation"
                r.root_cause_detail = "Model failed to add punctuation"
        else:
            if r.punctuation_raw_output != s['input']:
                r.pipeline_verdict = "FP"
                r.pipeline_detail = f"Over-punctuated: '{r.punctuation_raw_output[:60]}'"
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "punctuation"
                r.root_cause_detail = "Model modified already-punctuated text"
            else:
                r.pipeline_verdict = "TN"; r.pipeline_detail = "Correctly unchanged"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.punctuation_raw_ms}ms)")
        results.append(r)
    return results

def run_entity_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'entities', s.get('category',''), s['input'],
                        severity=s.get('severity',''))

        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp.get('error','')
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        entity = s.get('entity', '')

        if entity and entity not in r.pipeline_output:
            r.pipeline_verdict = "FP"
            r.pipeline_detail = f"ENTITY CORRUPTED: '{entity}' missing from output"
            r.root_cause_component = "MODEL"
            # Check which stage corrupted it
            sugg_types = [sg.get('type','') for sg in r.pipeline_suggestions]
            if 'grammar' in sugg_types:
                r.root_cause_stage = "grammar"
            elif 'spelling' in sugg_types:
                r.root_cause_stage = "spelling"
            else:
                r.root_cause_stage = "punctuation"
            r.root_cause_detail = f"Entity '{entity}' was modified"
        elif r.pipeline_output != resp.get('original', s['input']):
            changes = [f"{sg.get('original','')}→{sg.get('correction','')}" for sg in r.pipeline_suggestions]
            if changes:
                r.pipeline_verdict = "FP"
                r.pipeline_detail = f"Text modified: {changes[:3]}"
                if all(sg.get('type') == 'punctuation' for sg in r.pipeline_suggestions):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "punctuation"
                    r.root_cause_detail = "Punctuation added to entity context"
                else:
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "grammar"
                    r.root_cause_detail = "Grammar modified entity context"
            else:
                r.pipeline_verdict = "TN"; r.pipeline_detail = "Entity preserved"
        else:
            r.pipeline_verdict = "TN"; r.pipeline_detail = "Entity preserved"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms)")
        results.append(r)
    return results

def run_religious_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'religious', s.get('category',''), s['input'],
                        severity=s.get('severity',''))

        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp.get('error','')
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        original = resp.get('original', s['input'])

        if r.pipeline_output != original:
            changes = [f"{sg.get('original','')}→{sg.get('correction','')}" for sg in r.pipeline_suggestions]
            r.pipeline_verdict = "FP"
            r.pipeline_detail = f"RELIGIOUS TEXT MODIFIED: {changes[:3]}"
            sugg_types = [sg.get('type','') for sg in r.pipeline_suggestions]
            if all(t == 'punctuation' for t in sugg_types):
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "punctuation"
                r.root_cause_detail = "Punctuation model modified religious text"
            elif any(t == 'grammar' for t in sugg_types):
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "grammar"
                r.root_cause_detail = "Grammar model rewrote religious text"
            else:
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "spelling"
                r.root_cause_detail = "Spelling model modified religious text"
        else:
            r.pipeline_verdict = "TN"; r.pipeline_detail = "Religious text preserved"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms)")
        results.append(r)
    return results

def run_structured_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'structured', s.get('category',''), s['input'],
                        severity=s.get('severity',''))

        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp.get('error','')
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        protected = s.get('protected', '')

        if protected and protected not in r.pipeline_output:
            r.pipeline_verdict = "FP"
            r.pipeline_detail = f"STRUCTURED CORRUPTED: '{protected}' destroyed"
            r.root_cause_component = "MODEL"
            r.root_cause_stage = "grammar"
            r.root_cause_detail = f"Grammar model destroyed: {s.get('category','')}"
        elif r.pipeline_output != resp.get('original', s['input']):
            changes = [f"{sg.get('original','')}→{sg.get('correction','')}" for sg in r.pipeline_suggestions]
            r.pipeline_verdict = "FP"
            r.pipeline_detail = f"Modified: {changes[:3]}"
            if all(sg.get('type') == 'punctuation' for sg in r.pipeline_suggestions):
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "punctuation"
            else:
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "grammar"
            r.root_cause_detail = f"Model corrupted structured content: {s.get('category','')}"
        else:
            r.pipeline_verdict = "TN"; r.pipeline_detail = "Structured content preserved"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms)")
        results.append(r)
    return results

def run_hallucination_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} {s.get('category','')}... ", end="", flush=True)
        r = BenchResult(s['id'], 'hallucination', s.get('category',''), s['input'],
                        severity=s.get('severity',''))

        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        if 'error' in resp:
            r.pipeline_verdict = "ERROR"; r.pipeline_detail = resp.get('error','')
            print(f"💥 ERROR"); results.append(r); continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        original = resp.get('original', s['input'])

        if r.pipeline_output != original:
            changes = [f"{sg.get('original','')}→{sg.get('correction','')}" for sg in r.pipeline_suggestions]
            r.pipeline_verdict = "FP"
            r.pipeline_detail = f"HALLUCINATION: {changes[:3]}"
            word_orig = strip_punct_only(original)
            word_corr = strip_punct_only(r.pipeline_output)
            if word_orig == word_corr:
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "punctuation"
                r.root_cause_detail = "Punctuation-only hallucination"
            else:
                sugg_types = [sg.get('type','') for sg in r.pipeline_suggestions]
                if any(t == 'grammar' for t in sugg_types):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "grammar"
                    r.root_cause_detail = "Grammar model hallucinated on correct text"
                elif any(t == 'spelling' for t in sugg_types):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "spelling"
                    r.root_cause_detail = "Spelling model hallucinated"
                else:
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "punctuation"
                    r.root_cause_detail = "Punctuation model hallucinated"
        else:
            r.pipeline_verdict = "TN"; r.pipeline_detail = "No hallucination"

        icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}.get(r.pipeline_verdict,"?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms)")
        results.append(r)
    return results

# ═══════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════
def calc_metrics(results: List[BenchResult]) -> dict:
    tp = sum(1 for r in results if r.pipeline_verdict == "TP")
    fp = sum(1 for r in results if r.pipeline_verdict == "FP")
    tn = sum(1 for r in results if r.pipeline_verdict == "TN")
    fn = sum(1 for r in results if r.pipeline_verdict == "FN")
    err = sum(1 for r in results if r.pipeline_verdict == "ERROR")
    total = len(results)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2*prec*rec/(prec+rec) if (prec+rec) > 0 else 0
    lats = sorted([r.pipeline_ms for r in results if r.pipeline_ms > 0])
    return {
        "total": total, "TP": tp, "FP": fp, "TN": tn, "FN": fn, "ERROR": err,
        "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
        "fpr": round(fp/(fp+tn) if (fp+tn)>0 else 0, 4),
        "fnr": round(fn/(fn+tp) if (fn+tp)>0 else 0, 4),
        "pass_rate": round((tp+tn)/max(1,total), 4),
        "overcorrection_rate": round(fp/max(1,total), 4),
        "undercorrection_rate": round(fn/max(1,total), 4),
        "latency_p50": lats[len(lats)//2] if lats else 0,
        "latency_p95": lats[int(len(lats)*0.95)] if lats else 0,
    }

def root_cause_summary(results: List[BenchResult]) -> dict:
    failures = [r for r in results if r.pipeline_verdict in ("FP","FN")]
    by_component = {}
    by_stage = {}
    for r in failures:
        comp = r.root_cause_component or "UNKNOWN"
        stage = r.root_cause_stage or "unknown"
        by_component[comp] = by_component.get(comp, 0) + 1
        key = f"{comp}:{stage}"
        by_stage[key] = by_stage.get(key, 0) + 1
    return {
        "total_failures": len(failures),
        "by_component": dict(sorted(by_component.items(), key=lambda x: -x[1])),
        "by_stage": dict(sorted(by_stage.items(), key=lambda x: -x[1])),
    }

def stage_interaction_matrix(results: List[BenchResult]) -> dict:
    conflicts = {"spelling→grammar": 0, "grammar→punctuation": 0, "spelling→punctuation": 0}
    reversions = 0
    for r in results:
        if r.regression_type == "fix_lost":
            reversions += 1
            if "grammar" in r.regression_detail.lower():
                conflicts["spelling→grammar"] += 1
    return {"conflicts": conflicts, "reversions": reversions}

# ═══════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--dataset", nargs="*", default=["ALL"])
    parser.add_argument("--out", default=str(REPORT_DIR))
    args = parser.parse_args()

    api = API(args.url)
    run_all = "ALL" in [d.upper() for d in args.dataset]
    os.makedirs(args.out, exist_ok=True)

    print(f"[P10] Target: {args.url}")
    print(f"[P10] Datasets: {args.dataset}")
    all_results = []
    all_metrics = {}

    DATASETS = {
        "spelling":     (GOLD_DIR/"spelling.json",     run_spelling_benchmark),
        "grammar":      (GOLD_DIR/"grammar.json",      run_grammar_benchmark),
        "punctuation":  (GOLD_DIR/"punctuation.json",   run_punctuation_benchmark),
        "entities":     (GOLD_DIR/"entities.json",      run_entity_benchmark),
        "religious":    (GOLD_DIR/"religious.json",     run_religious_benchmark),
        "structured":   (GOLD_DIR/"structured_content.json", run_structured_benchmark),
        "hallucination":(GOLD_DIR/"hallucination.json", run_hallucination_benchmark),
    }

    for name, (path, runner) in DATASETS.items():
        if not run_all and name.upper() not in [d.upper() for d in args.dataset]:
            continue
        if not path.exists():
            print(f"\n⚠️ {name}: {path} not found — skipping")
            continue
        with open(path, 'r', encoding='utf-8') as f:
            samples = json.load(f)
        print(f"\n{'='*60}")
        print(f"DATASET: {name.upper()} ({len(samples)} samples)")
        print(f"{'='*60}")
        results = runner(api, samples)
        m = calc_metrics(results)
        all_metrics[name] = m
        all_results.extend(results)
        print(f"\n  Pass={m['pass_rate']:.1%} Prec={m['precision']:.3f} Rec={m['recall']:.3f} F1={m['f1']:.3f}")
        print(f"  FPR={m['fpr']:.3f} FNR={m['fnr']:.3f} p50={m['latency_p50']}ms p95={m['latency_p95']}ms")

    # ── Aggregate ──
    print(f"\n{'='*60}")
    print("AGGREGATE RESULTS")
    print(f"{'='*60}")
    agg = calc_metrics(all_results)
    rc = root_cause_summary(all_results)
    sim = stage_interaction_matrix(all_results)

    print(f"  Total: {agg['total']} | Pass: {agg['pass_rate']:.1%}")
    print(f"  TP={agg['TP']} TN={agg['TN']} FP={agg['FP']} FN={agg['FN']} ERR={agg['ERROR']}")
    print(f"\n  Root Cause by Component: {rc['by_component']}")
    print(f"  Root Cause by Stage: {rc['by_stage']}")
    print(f"  Stage Conflicts: {sim}")

    # ── Save ──
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": args.url,
        "aggregate_metrics": agg,
        "per_dataset_metrics": all_metrics,
        "root_cause_summary": rc,
        "stage_interactions": sim,
        "total_span_errors": sum(1 for r in all_results if not r.span_valid),
        "total_regressions": sum(1 for r in all_results if r.regression_type),
        "results": [asdict(r) for r in all_results],
    }
    out_path = os.path.join(args.out, "phase10_results.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[P10] Results → {out_path}")

if __name__ == "__main__":
    main()
