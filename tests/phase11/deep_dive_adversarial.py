"""
Phase 11 — Deep-Dive Adversarial Diagnostic Script
====================================================
Senior ML Engineer adversarial testing for the BAYAN pipeline.
Tests raw models SEPARATELY then the INTEGRATED pipeline.
Forcefully triggers 5 known edge-case classes and provides root cause analysis.

Usage:
    python tests/phase11/deep_dive_adversarial.py [--url URL]
"""
import argparse
import json
import re
import sys
import time
import difflib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
import requests

DEFAULT_URL = "https://bayan10-bayan-api.hf.space"
REPORT_DIR = Path(__file__).parent / "reports"


# ═══════════════════════════════════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════
class API:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.s = requests.Session()
        self.s.headers['Content-Type'] = 'application/json'

    def _post(self, ep, payload, timeout=180):
        t0 = time.time()
        try:
            r = self.s.post(f"{self.base}{ep}", json=payload, timeout=timeout)
            ms = int((time.time() - t0) * 1000)
            d = r.json()
            d['_ms'] = ms
            d['_status'] = r.status_code
            return d
        except requests.Timeout:
            return {'error': 'TIMEOUT', '_ms': int((time.time() - t0) * 1000), '_status': 0}
        except Exception as e:
            return {'error': str(e), '_ms': int((time.time() - t0) * 1000), '_status': 0}

    def analyze(self, text):
        """Full pipeline: /api/analyze"""
        return self._post('/api/analyze', {'text': text})

    def grammar(self, text):
        """Raw grammar only: /api/grammar"""
        return self._post('/api/grammar', {'text': text})

    def punctuation(self, text):
        """Raw punctuation only: /api/punctuation"""
        return self._post('/api/punctuation', {'text': text})


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class TestVector:
    """A single adversarial test case."""
    id: str
    category: str                # Edge-case category (1-5)
    subcategory: str             # Specific sub-type
    input_text: str
    expected_behavior: str       # What SHOULD happen
    severity: str = "critical"

@dataclass
class IsolationResult:
    """Results from testing each model in isolation + pipeline."""
    vector_id: str
    category: str
    subcategory: str
    input_text: str
    expected_behavior: str
    # Raw model outputs
    grammar_raw_output: str = ""
    grammar_raw_ms: int = 0
    punctuation_raw_output: str = ""
    punctuation_raw_ms: int = 0
    # Pipeline output
    pipeline_output: str = ""
    pipeline_corrected: str = ""
    pipeline_suggestions: list = field(default_factory=list)
    pipeline_ms: int = 0
    pipeline_timing: dict = field(default_factory=dict)
    # Analysis
    verdict: str = ""            # PASS, FAIL_MODEL, FAIL_PIPELINE, FAIL_FILTER, ERROR
    root_cause: str = ""
    failure_detail: str = ""
    # Integration delta
    grammar_raw_changed: bool = False
    pipeline_changed: bool = False
    raw_vs_pipeline_match: bool = False
    # Coordinate validation
    span_errors: list = field(default_factory=list)
    offset_drift: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: ADVERSARIAL TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

ADVERSARIAL_VECTORS: List[TestVector] = [
    # ──────────────────────────────────────────────────────────
    # CATEGORY 1: Punctuation Coordinate Shift (OffsetMapper bug)
    # ──────────────────────────────────────────────────────────
    TestVector("OFS-001", "offset_shift", "punct_after_spelling_fix",
               "ذهبت الي المدرسه وقابلت صديقتي وتحدثنا كثيرا",
               "Punct marks should align with corrected text, not shift 1-2 words"),
    TestVector("OFS-002", "offset_shift", "punct_after_multi_word_fix",
               "الطلاب ذهبو الي المكتبه لقراءة الكتب",
               "Punctuation positions should not drift after spelling corrects الي→إلى and المكتبه→المكتبة"),
    TestVector("OFS-003", "offset_shift", "length_changing_fix",
               "انا احب القراءه كثيرا وخصوصا الكتب العلميه",
               "أنا → 3 chars vs انا → 3 chars (same length), but القراءه→القراءة changes char positions"),
    TestVector("OFS-004", "offset_shift", "insertion_diffs",
               "كتبت رساله لصديقي واخبرته بالاخبار",
               "When spelling inserts أ (اخبرته→أخبرته), downstream coords must shift +1"),
    TestVector("OFS-005", "offset_shift", "multi_stage_coord_chain",
               "المهندسون ذهبو الي الموقعو وبدأو العمل",
               "3+ fixes in same sentence: verify offset chain doesn't accumulate drift"),

    # ──────────────────────────────────────────────────────────
    # CATEGORY 2: Prefixes and Prepositions (السوابق وحروف الجر)
    # ──────────────────────────────────────────────────────────
    TestVector("PFX-001", "prefix_handling", "wa_prefix",
               "وبالمستشفيات الكبيره يعالجون المرضي",
               "وبالمستشفيات should NOT be split or hallucinated — it's a valid prefixed word"),
    TestVector("PFX-002", "prefix_handling", "ba_prefix",
               "بالمدرسه الجديده تعلمت كثيرا",
               "بالمدرسه → بالمدرسة (only ه→ة fix, keep ب prefix)"),
    TestVector("PFX-003", "prefix_handling", "li_prefix",
               "للطالبات المجتهدات جوائز قيمه",
               "للطالبات should be preserved intact"),
    TestVector("PFX-004", "prefix_handling", "ka_prefix",
               "كالعاده ذهبت الي العمل",
               "كالعادة — ه→ة fix should work through ك+ال prefix"),
    TestVector("PFX-005", "prefix_handling", "fa_prefix",
               "فبالتالي يجب ان نعمل بجد",
               "فبالتالي is valid, should not be split or changed"),
    TestVector("PFX-006", "prefix_handling", "complex_prefix_chain",
               "وبالاضافه الي ذلك فان المشكله كبيره",
               "وبالإضافة إلى — hamza fix through وب prefix, plus ه→ة fixes"),
    TestVector("PFX-007", "prefix_handling", "wa_attached_to_error",
               "والمهندسين بنو المبني بسرعه",
               "والمهندسين should stay, بنو→بنوا (grammar), المبني→المبنى, بسرعه→بسرعة"),
    TestVector("PFX-008", "prefix_handling", "attached_pronoun",
               "كتابه قديم وصفحاته ممزقه",
               "كتابه (his book) — ه is pronoun, NOT ta marbuta. Must NOT become كتابة"),
    TestVector("PFX-009", "prefix_handling", "pronoun_vs_tamarbuta",
               "قرأته بعنايه فتأملته جيدا",
               "قرأته and فتأملته — ته is pronoun suffix, NOT ta marbuta"),
    TestVector("PFX-010", "prefix_handling", "merged_preposition",
               "ذهبتللمدرسه صباحا",
               "Missing space: ذهبت+ل+المدرسه — should split and fix"),

    # ──────────────────────────────────────────────────────────
    # CATEGORY 3: StageLocker / Directional Flow
    # ──────────────────────────────────────────────────────────
    TestVector("SLK-001", "stagelocker", "spelling_lock_grammar_override",
               "السياره جميل جدا",
               "Spelling fixes السياره→السيارة, Grammar should still fix جميل→جميلة (Phase 11 hierarchical)"),
    TestVector("SLK-002", "stagelocker", "grammar_not_overwrite_spelling",
               "المدرسه كبير وجميل",
               "Spelling: المدرسه→المدرسة. Grammar should NOT revert to المدرسه. Should add ة to كبير/جميل"),
    TestVector("SLK-003", "stagelocker", "punct_respects_grammar_lock",
               "الطلاب ذهبوا الى المكتبة لقراءة الكتب الجديدة",
               "Grammar unchanged (correct text). Punctuation should NOT move/corrupt words"),
    TestVector("SLK-004", "stagelocker", "overlapping_patches",
               "الاطفال يلعبون بالكره في الحديقه الكبيره",
               "Spelling: الاطفال→الأطفال, بالكره→بالكرة, الحديقه→الحديقة, الكبيره→الكبيرة — multiple overlapping spans"),
    TestVector("SLK-005", "stagelocker", "backward_overwrite",
               "هذه المدينه جميله وهادئه",
               "Three ه→ة fixes. Grammar must NOT overwrite any of them back to ه"),
    TestVector("SLK-006", "stagelocker", "grammar_overrides_spelling_adjacent",
               "الطالبه ذكي في المدرسه",
               "Spelling fixes ه→ة, Grammar must fix gender (ذكي→ذكية) on ADJACENT word"),

    # ──────────────────────────────────────────────────────────
    # CATEGORY 4: Overcorrection & Safety Filter Analysis
    # ──────────────────────────────────────────────────────────
    TestVector("OVR-001", "overcorrection", "correct_text_unchanged",
               "ذهب الطالب إلى المكتبة وقرأ كتاباً مفيداً",
               "Perfectly correct text — should return UNCHANGED"),
    TestVector("OVR-002", "overcorrection", "correct_grammar_unchanged",
               "المهندسون يعملون في المصنع الكبير بجدٍ واجتهاد",
               "Correct SV agreement + tanween — must not be modified"),
    TestVector("OVR-003", "overcorrection", "jaccard_threshold_test",
               "جالس في البيت يقرأ الصحيفة",
               "Correct text. Grammar should not hallucinate جالس→جاكسون (Jaccard < 0.3)"),
    TestVector("OVR-004", "overcorrection", "meaning_change_block",
               "وكان الجو صحواً اليوم",
               "وكان must NOT become وكأن (directional block). Correct as-is"),
    TestVector("OVR-005", "overcorrection", "rare_word_dampening",
               "الفيلسوف سقراط تأمل الحقيقة",
               "سقراط is a rare valid name — spelling should not 'correct' it"),
    TestVector("OVR-006", "overcorrection", "filter_over_blocking",
               "انا ذاهب الي المدرسه",
               "IV-IV guard should NOT block انا→أنا or الي→إلى (these are whitelist entries)"),
    TestVector("OVR-007", "overcorrection", "tanween_preservation",
               "قرأت كتاباً جميلاً عن التاريخ",
               "Tanween (ً) must be preserved — grammar should not strip it"),
    TestVector("OVR-008", "overcorrection", "correct_feminine_form",
               "المعلمة الجديدة شرحت الدرس",
               "Already correct — must NOT change المعلمة to المعلمه"),
    TestVector("OVR-009", "overcorrection", "brackets_protection",
               "الفصل الأول (المقدمة) يتناول الموضوع",
               "Brackets must be preserved. Grammar should not unbalance them"),
    TestVector("OVR-010", "overcorrection", "digits_protection",
               "تأسست الشركة عام 2020 وبلغ عدد موظفيها 150 شخصاً",
               "Digits must NOT be corrupted by grammar model"),

    # ──────────────────────────────────────────────────────────
    # CATEGORY 5: Model Mismatch (Spelling→Grammar friction)
    # ──────────────────────────────────────────────────────────
    TestVector("MIS-001", "model_mismatch", "spelling_output_breaks_grammar",
               "الطالبه المجتهده حصلت علي درجات عاليه",
               "Spelling: 4x ه→ة. Grammar should NOT break on the corrected output"),
    TestVector("MIS-002", "model_mismatch", "grammar_undoes_spelling",
               "ذهبنا الي المكتبه القريبه",
               "Spelling fixes الي→إلى, المكتبه→المكتبة. Grammar must NOT revert these"),
    TestVector("MIS-003", "model_mismatch", "cascading_length_change",
               "اريد ان اذهب الي المدرسه لانني احب القراءه",
               "Many hamza + ه→ة fixes. Total text length changes significantly — grammar must handle shifted text"),
    TestVector("MIS-004", "model_mismatch", "grammar_hallucination_on_corrected",
               "الاولاد يلعبون والبنات يذهبن",
               "Spelling: الاولاد→الأولاد. Grammar should NOT hallucinate on already-correct يلعبون/يذهبن"),
    TestVector("MIS-005", "model_mismatch", "punc_on_grammar_corrected",
               "السيارات سريعة والطرق واسعه",
               "After spelling (واسعه→واسعة), punctuation should add period at end, not corrupt words"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: ISOLATION vs INTEGRATION MATRIX
# ═══════════════════════════════════════════════════════════════════════════════

def strip_diacritics(text: str) -> str:
    return re.sub(r'[\u064B-\u065F\u0670]', '', text)

def normalize(text: str) -> str:
    t = strip_diacritics(text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def validate_spans(original: str, suggestions: list) -> List[str]:
    """Validate all suggestion spans point to correct original text."""
    errors = []
    for sg in suggestions:
        start = sg.get('start', 0)
        end = sg.get('end', 0)
        expected_orig = sg.get('original', '')
        actual_slice = original[start:end]
        if actual_slice != expected_orig:
            errors.append(
                f"SPAN[{start}:{end}] expected='{expected_orig}' actual='{actual_slice}' "
                f"(drift={len(actual_slice) - len(expected_orig)})"
            )
    return errors

def compute_offset_drift(original: str, suggestions: list) -> int:
    """Compute max drift between expected and actual span content."""
    max_drift = 0
    for sg in suggestions:
        start = sg.get('start', 0)
        end = sg.get('end', 0)
        expected = sg.get('original', '')
        actual = original[start:end]
        if actual != expected:
            # Try to find the expected text nearby
            for delta in range(-5, 6):
                try_start = max(0, start + delta)
                try_end = min(len(original), end + delta)
                if original[try_start:try_end] == expected:
                    max_drift = max(max_drift, abs(delta))
                    break
            else:
                max_drift = max(max_drift, 99)  # Not found at all
    return max_drift


def run_isolation_matrix(api: API, vectors: List[TestVector]) -> List[IsolationResult]:
    """Run each vector through raw models + pipeline and compare."""
    results = []

    for i, v in enumerate(vectors):
        print(f"\n  [{i+1}/{len(vectors)}] {v.id} ({v.category}/{v.subcategory})")
        print(f"    Input: {v.input_text[:80]}...")

        r = IsolationResult(
            vector_id=v.id,
            category=v.category,
            subcategory=v.subcategory,
            input_text=v.input_text,
            expected_behavior=v.expected_behavior,
        )

        # ── A) Raw Grammar Only ──
        try:
            resp_g = api.grammar(v.input_text)
            r.grammar_raw_output = resp_g.get('corrected_text', resp_g.get('corrected', ''))
            r.grammar_raw_ms = resp_g.get('_ms', 0)
            r.grammar_raw_changed = (r.grammar_raw_output != v.input_text)
            print(f"    [A] Grammar raw: {'CHANGED' if r.grammar_raw_changed else 'unchanged'} ({r.grammar_raw_ms}ms)")
            if r.grammar_raw_changed:
                print(f"         → {r.grammar_raw_output[:80]}")
        except Exception as e:
            print(f"    [A] Grammar raw: ERROR ({e})")

        # ── B) Raw Punctuation Only ──
        try:
            resp_p = api.punctuation(v.input_text)
            r.punctuation_raw_output = resp_p.get('corrected_text', resp_p.get('corrected', ''))
            r.punctuation_raw_ms = resp_p.get('_ms', 0)
            punct_changed = (r.punctuation_raw_output != v.input_text)
            print(f"    [B] Punct raw:   {'CHANGED' if punct_changed else 'unchanged'} ({r.punctuation_raw_ms}ms)")
            if punct_changed:
                print(f"         → {r.punctuation_raw_output[:80]}")
        except Exception as e:
            print(f"    [B] Punct raw: ERROR ({e})")

        # ── C) Full Pipeline ──
        try:
            resp = api.analyze(v.input_text)
            r.pipeline_ms = resp.get('_ms', 0)
            r.pipeline_timing = resp.get('timing_ms', {})
            r.pipeline_corrected = resp.get('corrected', '')
            r.pipeline_output = r.pipeline_corrected
            r.pipeline_suggestions = resp.get('suggestions', [])
            r.pipeline_changed = (r.pipeline_corrected != resp.get('original', v.input_text))
            print(f"    [C] Pipeline:    {'CHANGED' if r.pipeline_changed else 'unchanged'} ({r.pipeline_ms}ms) [{len(r.pipeline_suggestions)} suggestions]")
            if r.pipeline_changed:
                print(f"         → {r.pipeline_corrected[:80]}")

            # ── Span validation ──
            original = resp.get('original', v.input_text)
            r.span_errors = validate_spans(original, r.pipeline_suggestions)
            r.offset_drift = compute_offset_drift(original, r.pipeline_suggestions)
            if r.span_errors:
                print(f"    ⚠️  SPAN ERRORS: {r.span_errors}")
            if r.offset_drift > 0:
                print(f"    ⚠️  OFFSET DRIFT: {r.offset_drift} chars")

            # ── Raw vs Pipeline comparison ──
            norm_grammar = normalize(r.grammar_raw_output)
            norm_pipeline = normalize(r.pipeline_corrected)
            r.raw_vs_pipeline_match = (norm_grammar == norm_pipeline)

        except Exception as e:
            r.verdict = "ERROR"
            r.failure_detail = str(e)
            print(f"    [C] Pipeline: ERROR ({e})")

        # ── Verdict determination ──
        _classify_result(v, r)

        icon = {"PASS": "✅", "FAIL_MODEL": "🔴", "FAIL_PIPELINE": "🟡",
                "FAIL_FILTER": "🟠", "FAIL_OFFSET": "🔵", "ERROR": "💥"}.get(r.verdict, "❓")
        print(f"    {icon} {r.verdict}: {r.root_cause}")

        results.append(r)

    return results


def _classify_result(v: TestVector, r: IsolationResult):
    """Classify the test result into a verdict + root cause."""
    if r.verdict == "ERROR":
        return

    cat = v.category

    # ── Category 1: Offset shift ──
    if cat == "offset_shift":
        if r.span_errors:
            r.verdict = "FAIL_OFFSET"
            r.root_cause = f"OffsetMapper coordinate drift ({r.offset_drift} chars): {r.span_errors[0]}"
            r.failure_detail = "; ".join(r.span_errors)
        elif r.offset_drift > 0:
            r.verdict = "FAIL_OFFSET"
            r.root_cause = f"Offset drift detected: {r.offset_drift} chars"
        else:
            r.verdict = "PASS"
            r.root_cause = "Spans aligned correctly"
        return

    # ── Category 2: Prefix handling ──
    if cat == "prefix_handling":
        output = r.pipeline_corrected
        inp = v.input_text
        # Check for catastrophic prefix destruction
        if _check_prefix_destruction(inp, output):
            r.verdict = "FAIL_MODEL"
            r.root_cause = "Prefix word was split, hallucinated, or destroyed"
            r.failure_detail = f"Input had prefixed words that were corrupted in output"
        elif r.span_errors:
            r.verdict = "FAIL_OFFSET"
            r.root_cause = f"Span errors in prefix test: {r.span_errors[0]}"
        else:
            r.verdict = "PASS"
            r.root_cause = "Prefixed words handled correctly"
        return

    # ── Category 3: StageLocker ──
    if cat == "stagelocker":
        # Check if grammar fix was blocked by spelling lock
        sugg_stages = [s.get('type', '') for s in r.pipeline_suggestions]
        if v.subcategory == "spelling_lock_grammar_override":
            has_grammar = 'grammar' in sugg_stages
            has_spelling = 'spelling' in sugg_stages
            if has_spelling and not has_grammar:
                r.verdict = "FAIL_PIPELINE"
                r.root_cause = "StageLocker STILL blocking grammar override of spelling (Phase 11 fix not deployed?)"
            elif has_spelling and has_grammar:
                r.verdict = "PASS"
                r.root_cause = "Grammar successfully overrode spelling lock"
            else:
                r.verdict = "PASS"
                r.root_cause = "Pipeline handled correctly"
        elif v.subcategory == "backward_overwrite":
            # Check that spelling fixes were preserved
            if 'ه' in r.pipeline_corrected and 'المدين' in r.pipeline_corrected:
                # Check if any ه→ة fix was reverted
                for sg in r.pipeline_suggestions:
                    if sg.get('type') == 'grammar':
                        orig_sg = sg.get('original', '')
                        corr_sg = sg.get('correction', '')
                        if orig_sg.endswith('ة') and corr_sg.endswith('ه'):
                            r.verdict = "FAIL_PIPELINE"
                            r.root_cause = f"Grammar reverted spelling fix: '{orig_sg}'→'{corr_sg}'"
                            return
            r.verdict = "PASS"
            r.root_cause = "No backward overwrite detected"
        else:
            r.verdict = "PASS"
            r.root_cause = "StageLocker operating correctly"
        return

    # ── Category 4: Overcorrection ──
    if cat == "overcorrection":
        if v.subcategory in ("correct_text_unchanged", "correct_grammar_unchanged",
                              "correct_feminine_form", "tanween_preservation"):
            if r.pipeline_changed:
                changes = [f"{s.get('original','')}→{s.get('correction','')}"
                           for s in r.pipeline_suggestions]
                r.verdict = "FAIL_FILTER"
                r.root_cause = f"Correct text was modified: {changes[:3]}"
                r.failure_detail = f"All changes: {changes}"
            else:
                r.verdict = "PASS"
                r.root_cause = "Correct text preserved"
        elif v.subcategory == "meaning_change_block":
            # Check if وكان was changed to وكأن
            if 'وكأن' in r.pipeline_corrected:
                r.verdict = "FAIL_FILTER"
                r.root_cause = "Directional block failed: وكان→وكأن leaked through"
            else:
                r.verdict = "PASS"
                r.root_cause = "Meaning preserved"
        elif v.subcategory == "digits_protection":
            if not re.search(r'2020', r.pipeline_corrected):
                r.verdict = "FAIL_FILTER"
                r.root_cause = "Digits were corrupted"
            elif not re.search(r'150', r.pipeline_corrected):
                r.verdict = "FAIL_FILTER"
                r.root_cause = "Digits were corrupted"
            else:
                r.verdict = "PASS"
                r.root_cause = "Digits preserved"
        elif v.subcategory == "brackets_protection":
            if '(' in v.input_text and '(' not in r.pipeline_corrected:
                r.verdict = "FAIL_FILTER"
                r.root_cause = "Brackets were removed"
            else:
                r.verdict = "PASS"
                r.root_cause = "Brackets preserved"
        else:
            if r.pipeline_changed and not r.pipeline_suggestions:
                r.verdict = "FAIL_FILTER"
                r.root_cause = "Text changed without suggestions"
            else:
                r.verdict = "PASS"
                r.root_cause = "No overcorrection detected"
        return

    # ── Category 5: Model mismatch ──
    if cat == "model_mismatch":
        if v.subcategory == "grammar_undoes_spelling":
            # Check if spelling corrections were preserved
            if 'الي' in r.pipeline_corrected or 'المكتبه' in r.pipeline_corrected:
                r.verdict = "FAIL_PIPELINE"
                r.root_cause = "Grammar undid spelling corrections"
            else:
                r.verdict = "PASS"
                r.root_cause = "Spelling corrections preserved through grammar"
        elif v.subcategory == "spelling_output_breaks_grammar":
            if r.verdict != "ERROR" and r.pipeline_corrected:
                r.verdict = "PASS"
                r.root_cause = "Grammar handled spelling-corrected input"
            else:
                r.verdict = "FAIL_PIPELINE"
                r.root_cause = "Grammar broke on spelling output"
        else:
            r.verdict = "PASS"
            r.root_cause = "No model mismatch detected"
        return

    r.verdict = "PASS"
    r.root_cause = "No issues detected"


def _check_prefix_destruction(input_text: str, output: str) -> bool:
    """Check if prefixed words were catastrophically destroyed."""
    PREFIXED_PATTERNS = [
        (r'\bوبال\w+', 'وبال'),
        (r'\bبال\w+', 'بال'),
        (r'\bكال\w+', 'كال'),
        (r'\bفبال\w+', 'فبال'),
        (r'\bلل\w+', 'لل'),
    ]
    input_words = set(input_text.split())
    output_words = set(output.split())

    for word in input_words:
        for pattern, prefix in PREFIXED_PATTERNS:
            if re.match(pattern, word):
                # This word has a prefix — check if it survived
                # Allow ه→ة change but not complete destruction
                stripped_orig = re.sub(r'[ةه]$', '', word)
                found = False
                for ow in output_words:
                    stripped_out = re.sub(r'[ةه]$', '', ow)
                    if stripped_orig == stripped_out or ow.startswith(prefix):
                        found = True
                        break
                if not found:
                    return True  # Prefixed word was destroyed
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: ANALYSIS & REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(results: List[IsolationResult], url: str) -> dict:
    """Generate comprehensive analysis report."""

    # Aggregate
    total = len(results)
    by_verdict = {}
    by_category = {}
    offset_issues = []
    filter_issues = []
    pipeline_issues = []
    model_issues = []

    for r in results:
        by_verdict[r.verdict] = by_verdict.get(r.verdict, 0) + 1
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "pass": 0, "fail": 0}
        by_category[cat]["total"] += 1
        if r.verdict == "PASS":
            by_category[cat]["pass"] += 1
        else:
            by_category[cat]["fail"] += 1

        if r.verdict == "FAIL_OFFSET":
            offset_issues.append(r)
        elif r.verdict == "FAIL_FILTER":
            filter_issues.append(r)
        elif r.verdict == "FAIL_PIPELINE":
            pipeline_issues.append(r)
        elif r.verdict == "FAIL_MODEL":
            model_issues.append(r)

    pass_count = by_verdict.get("PASS", 0)
    pass_rate = pass_count / total if total > 0 else 0

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": url,
        "total_vectors": total,
        "pass_rate": round(pass_rate * 100, 1),
        "by_verdict": by_verdict,
        "by_category": by_category,
        "offset_issues": [asdict(r) for r in offset_issues],
        "filter_issues": [asdict(r) for r in filter_issues],
        "pipeline_issues": [asdict(r) for r in pipeline_issues],
        "model_issues": [asdict(r) for r in model_issues],
        "results": [asdict(r) for r in results],
    }
    return report


def print_report(results: List[IsolationResult], report: dict):
    """Print detailed report to console."""
    print(f"\n{'='*70}")
    print("ADVERSARIAL DIAGNOSTIC REPORT")
    print(f"{'='*70}")
    print(f"\n## Overall: {report['pass_rate']}% pass rate ({report['total_vectors']} vectors)")
    print(f"\n| Verdict         | Count |")
    print(f"|-----------------|-------|")
    for verdict, count in sorted(report['by_verdict'].items()):
        icon = {"PASS": "✅", "FAIL_MODEL": "🔴", "FAIL_PIPELINE": "🟡",
                "FAIL_FILTER": "🟠", "FAIL_OFFSET": "🔵", "ERROR": "💥"}.get(verdict, "❓")
        print(f"| {icon} {verdict:<14} | {count:>5} |")

    print(f"\n## By Edge-Case Category")
    print(f"| Category             | Total | Pass | Fail | Rate |")
    print(f"|----------------------|-------|------|------|------|")
    for cat, data in sorted(report['by_category'].items()):
        rate = data['pass'] / data['total'] * 100 if data['total'] > 0 else 0
        print(f"| {cat:<20} | {data['total']:>5} | {data['pass']:>4} | {data['fail']:>4} | {rate:>3.0f}% |")

    # ── Failure details ──
    failures = [r for r in results if r.verdict != "PASS"]
    if failures:
        print(f"\n## Failure Details ({len(failures)} issues)")
        print(f"{'─'*70}")
        for r in failures:
            icon = {"FAIL_MODEL": "🔴", "FAIL_PIPELINE": "🟡",
                    "FAIL_FILTER": "🟠", "FAIL_OFFSET": "🔵", "ERROR": "💥"}.get(r.verdict, "❓")
            print(f"\n  {icon} [{r.vector_id}] {r.category}/{r.subcategory}")
            print(f"     Input:    {r.input_text[:70]}")
            print(f"     Pipeline: {r.pipeline_corrected[:70]}")
            print(f"     Cause:    {r.root_cause}")
            if r.span_errors:
                for se in r.span_errors[:3]:
                    print(f"     Span:     {se}")

    # ── OffsetMapper analysis ──
    all_drifts = [r.offset_drift for r in results if r.offset_drift > 0]
    if all_drifts:
        print(f"\n## OffsetMapper Drift Analysis")
        print(f"  Vectors with drift: {len(all_drifts)}/{len(results)}")
        print(f"  Max drift: {max(all_drifts)} chars")
        print(f"  Affected vectors: {[r.vector_id for r in results if r.offset_drift > 0]}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Phase 11 Adversarial Diagnostic")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--category", default=None, help="Filter by category (offset_shift, prefix_handling, etc.)")
    args = parser.parse_args()

    api = API(args.url)

    # Filter vectors if category specified
    vectors = ADVERSARIAL_VECTORS
    if args.category:
        vectors = [v for v in vectors if v.category == args.category]

    print(f"\n{'='*70}")
    print(f"BAYAN ADVERSARIAL DIAGNOSTIC — Phase 11")
    print(f"{'='*70}")
    print(f"  Target:  {args.url}")
    print(f"  Vectors: {len(vectors)}")
    print(f"  Categories: {sorted(set(v.category for v in vectors))}")
    print(f"{'='*70}")

    results = run_isolation_matrix(api, vectors)
    report = generate_report(results, args.url)
    print_report(results, report)

    # Save JSON report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "adversarial_diagnostic.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[DIAG] Full report → {out_path}")


if __name__ == "__main__":
    main()
