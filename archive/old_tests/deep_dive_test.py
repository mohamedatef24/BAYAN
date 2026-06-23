"""
BAYAN Deep-Dive Test Harness — Track A (Raw Models via API) & Track B (Full Pipeline via API)

Uses the deployed HF Space API (bayan10/bayan-api) instead of loading models locally.
This avoids the 1GB model download hang and tests the ACTUAL production behavior.

Track A: /api/spelling, /api/grammar, /api/punctuation (individual model endpoints)
Track B: /api/analyze (full pipeline with StageLocker, OffsetMapper, PatchSet)

Usage:
    python tests/deep_dive_test.py --stage spelling
    python tests/deep_dive_test.py --stage grammar
    python tests/deep_dive_test.py --stage punctuation
    python tests/deep_dive_test.py --stage pipeline
    python tests/deep_dive_test.py --stage all
"""

import sys, os, re, json, time, argparse
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════════════════════

import requests

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 60  # seconds per request

def api_call(endpoint, text, retries=2):
    """Call the deployed API with retry."""
    url = f"{API_BASE}{endpoint}"
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            resp = requests.post(url, json={"text": text}, timeout=TIMEOUT)
            elapsed = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                data['_elapsed_ms'] = elapsed
                data['_timestamp'] = datetime.now(timezone.utc).isoformat()
                return data
            else:
                if attempt < retries:
                    time.sleep(2)
                    continue
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}", "_elapsed_ms": elapsed}
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(2)
                continue
            return {"error": f"Timeout after {TIMEOUT}s", "_elapsed_ms": TIMEOUT * 1000}
        except Exception as e:
            return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════════
# TRACK A — RAW MODEL CALLS (individual endpoints, no pipeline)
# ═══════════════════════════════════════════════════════════════════

def track_a_spelling(text):
    """Call /api/spelling — raw AraSpell output."""
    result = api_call("/api/spelling", text)
    if "error" in result:
        return {"input": text, "output": text, "error": result["error"], "changed": False}
    corrected = result.get("corrected_text", text)
    return {
        "input": text, "output": corrected, "changed": corrected != text,
        "elapsed_ms": result.get("_elapsed_ms"), "timestamp": result.get("_timestamp")
    }

def track_a_grammar(text):
    """Call /api/grammar — raw grammar model output."""
    result = api_call("/api/grammar", text)
    if "error" in result:
        return {"input": text, "output": text, "error": result["error"], "changed": False}
    corrected = result.get("corrected_text", text)
    return {
        "input": text, "output": corrected, "changed": corrected != text,
        "elapsed_ms": result.get("_elapsed_ms"), "timestamp": result.get("_timestamp")
    }

def track_a_punctuation(text):
    """Call /api/punctuation — raw PuncAra output."""
    result = api_call("/api/punctuation", text)
    if "error" in result:
        return {"input": text, "output": text, "error": result["error"], "changed": False}
    corrected = result.get("corrected_text", text)
    marks_before = sum(1 for c in text if c in '.,;:!?،؛؟')
    marks_after = sum(1 for c in corrected if c in '.,;:!?،؛؟')
    return {
        "input": text, "output": corrected, "changed": corrected != text,
        "marks_added": marks_after - marks_before,
        "elapsed_ms": result.get("_elapsed_ms"), "timestamp": result.get("_timestamp")
    }

# ═══════════════════════════════════════════════════════════════════
# TRACK B — FULL PIPELINE (/api/analyze)
# ═══════════════════════════════════════════════════════════════════

def track_b_analyze(text):
    """Call /api/analyze — full pipeline with all stages."""
    result = api_call("/api/analyze", text)
    if "error" in result and "status" not in result:
        return {"input": text, "error": result["error"], "suggestions": []}
    return {
        "input": text,
        "original": result.get("original", text),
        "corrected": result.get("corrected", text),
        "suggestions": result.get("suggestions", []),
        "timing_ms": result.get("timing_ms", {}),
        "elapsed_ms": result.get("_elapsed_ms"),
        "timestamp": result.get("_timestamp"),
    }

# ═══════════════════════════════════════════════════════════════════
# TEST INPUTS — ALL CATEGORIES
# ═══════════════════════════════════════════════════════════════════

CAT2_OVERCORRECTION = [
    {"id": "C2-01", "input": "القاهرة عاصمة جمهورية مصر العربية وأكبر مدنها", "domain": "news"},
    {"id": "C2-02", "input": "يعد نهر النيل أطول أنهار العالم", "domain": "news"},
    {"id": "C2-03", "input": "بسم الله الرحمن الرحيم", "domain": "religious"},
    {"id": "C2-04", "input": "إنا لله وإنا إليه راجعون", "domain": "religious"},
    {"id": "C2-05", "input": "يستخدم الذكاء الاصطناعي تقنيات التعلم العميق", "domain": "technical"},
    {"id": "C2-06", "input": "سافر محمد إلى دبي للعمل في شركة جوجل", "domain": "proper_nouns"},
    {"id": "C2-07", "input": "الرئيس عبد الفتاح السيسي رئيس جمهورية مصر العربية", "domain": "proper_nouns"},
    {"id": "C2-08", "input": "استوقفني المشهد فتأملته مليا", "domain": "literary"},
    {"id": "C2-09", "input": "أضحى التعليم الإلكتروني ضرورة ملحة في عصرنا الحالي", "domain": "formal"},
    {"id": "C2-10", "input": "تتراوح درجات الحرارة بين خمس وعشرين وثلاثين درجة مئوية", "domain": "weather"},
]

CAT8_CLITIC_ROOTS = [
    ('مدرسة', 'moon'),       # Moon letter
    ('شمس', 'sun'),          # Sun letter
    ('أمة', 'hamza'),        # Hamza-initial
    ('نافذة', 'long'),       # Long word
    ('علم', 'short'),        # Short 3-letter root
    ('اقتصاد', 'alef'),     # Alef-initial, long
]
CAT8_PREFIXES = [("bare", ""), ("wa", "و"), ("ba", "ب"), ("la", "ل"), ("ka", "ك")]
CAT8_TESTS = []
for root, root_type in CAT8_CLITIC_ROOTS:
    for pfx_name, pfx in CAT8_PREFIXES:
        word = pfx + root
        CAT8_TESTS.append({
            "id": f"C8-{root}-{pfx_name}", "input": word, "root": root,
            "root_type": root_type, "prefix": pfx, "expected": word,
        })

CAT9_CONFUSABLE = [
    # === Isolation tests ===
    {"id": "C9-01a", "input": "ان", "context": "isolation", "concern": "should→أن/إن NOT كان"},
    {"id": "C9-01b", "input": "كان", "context": "isolation", "concern": "stays كان"},
    {"id": "C9-02a", "input": "إلى", "context": "isolation", "concern": "stays إلى"},
    {"id": "C9-02b", "input": "على", "context": "isolation", "concern": "stays على"},
    {"id": "C9-03a", "input": "هذا", "context": "isolation", "concern": "stays هذا"},
    {"id": "C9-03b", "input": "هذه", "context": "isolation", "concern": "stays هذه"},
    {"id": "C9-03c", "input": "هذة", "context": "isolation", "concern": "misspelling→هذه"},
    {"id": "C9-04a", "input": "لكن", "context": "isolation", "concern": "stays لكن"},
    {"id": "C9-04b", "input": "لاكن", "context": "isolation", "concern": "misspelling→لكن"},
    {"id": "C9-05a", "input": "ذلك", "context": "isolation", "concern": "stays ذلك"},
    {"id": "C9-05b", "input": "ذالك", "context": "isolation", "concern": "misspelling→ذلك"},
    {"id": "C9-06a", "input": "الى", "context": "isolation", "concern": "should→إلى"},
    # === Sentence-context tests ===
    {"id": "C9-S01", "input": "ان الحياة جميلة", "context": "sentence", "concern": "ان→أن/إن NOT كان"},
    {"id": "C9-S02", "input": "كان الرجل طيبا", "context": "sentence", "concern": "كان stays"},
    {"id": "C9-S03", "input": "ذهب الى المدرسة", "context": "sentence", "concern": "الى→إلى"},
    {"id": "C9-S04", "input": "جلس على الكرسي", "context": "sentence", "concern": "على stays"},
    {"id": "C9-S05", "input": "هذة المدينة جميلة", "context": "sentence", "concern": "هذة→هذه"},
    {"id": "C9-S06", "input": "هو ذكي لاكن كسول", "context": "sentence", "concern": "لاكن→لكن"},
    {"id": "C9-S07", "input": "ذالك الكتاب مفيد", "context": "sentence", "concern": "ذالك→ذلك"},
    {"id": "C9-S08", "input": "هذا البيت كبير", "context": "sentence", "concern": "هذا stays"},
    {"id": "C9-S09", "input": "هذه السيارة سريعة", "context": "sentence", "concern": "هذه stays"},
    {"id": "C9-S10", "input": "سافر إلى القاهرة", "context": "sentence", "concern": "إلى stays"},
    {"id": "C9-S11", "input": "جلس على المقعد", "context": "sentence", "concern": "على stays"},
    {"id": "C9-S12", "input": "ان الذكاء مهم لكن الاجتهاد اهم", "context": "sentence", "concern": "ان→أن, لكن stays"},
]

CAT10_EDGE_CASES = [
    {"id": "C10-01", "input": "كَتَبَ الطَّالِبُ الدَّرسَ", "concern": "tashkeel_present"},
    {"id": "C10-02", "input": "كتب الطالب الدرس", "concern": "tashkeel_absent"},
    {"id": "C10-03", "input": "قرأ إبراهيم آيات من القرآن", "concern": "alef_forms"},
    {"id": "C10-04", "input": "مشى الفتى إلى المستشفى", "concern": "ya_alef_maksura"},
    {"id": "C10-05", "input": "ذهبت إلى المدرسة", "concern": "ta_marbuta"},
    {"id": "C10-06", "input": "جاء ١٢٣ طالبا", "concern": "arabic_indic_digits"},
    {"id": "C10-07", "input": "جاء 123 طالبا", "concern": "western_digits"},
    {"id": "C10-08", "input": "يعمل في شركة Google في القاهرة", "concern": "latin_in_arabic"},
    {"id": "C10-09", "input": "انا رايح المدرسة النهارده", "concern": "egyptian_dialect"},
    {"id": "C10-10", "input": "الموضوع ده كويس جدااااا", "concern": "repeated_letters"},
    {"id": "C10-11", "input": "مسؤول عن الشؤون الداخلية", "concern": "hamza_on_waw"},
    {"id": "C10-12", "input": "بيئة العمل مليئة بالتحديات", "concern": "hamza_on_ya"},
    {"id": "C10-13", "input": "الكتاب الذى قرأته مفيد", "concern": "ya_in_الذي"},
    {"id": "C10-14", "input": "خطأ الطالب في الامتحان", "concern": "hamza_standalone"},
    {"id": "C10-15", "input": "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين", "concern": "religious_long"},
]

CAT5_PUNC_SANITY = [
    {"id": "C5-01", "input": "ذهب إلى المدرسة", "length": "short_3w"},
    {"id": "C5-02", "input": "هل تعلم أن الأرض تدور حول الشمس كل عام", "length": "medium_9w"},
    {"id": "C5-03", "input": "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة رغبة في بناء كتلة عضلية قوية ويا له من التزام حديدي يثير الإعجاب", "length": "long_20w"},
    {"id": "C5-04", "input": "قال المعلم للطلاب ادرسوا جيدا فالامتحان قريب", "length": "medium_imperative"},
    {"id": "C5-05", "input": "كانت الفتيات يلعبن في الحديقة وفجأة سقطت إحداهن وبدأت تبكي بشدة", "length": "long_narrative"},
]

CAT6_PUNC_POSITION = [
    {"id": "C6-01", "input": "ذهب محمد إلى المدرسة ودرس جيدا ثم عاد إلى البيت"},
    {"id": "C6-02", "input": "إن الذكاء الاصطناعي يلعب دورا هاما لذلك يجب الاهتمام به"},
    {"id": "C6-03", "input": "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة رغبة في بناء كتلة عضلية قوية ويا له من التزام حديدي يثير الإعجاب"},
    {"id": "C6-04", "input": "كانت الفتيات يلعبن في الحديقة وفجأة سقطت إحداهن وبدأت تبكي بشدة"},
    {"id": "C6-05", "input": "هل تعلم أن القاهرة هي عاصمة مصر وتقع على ضفاف نهر النيل"},
    {"id": "C6-06", "input": "قال المعلم للطلاب ادرسوا جيدا فالامتحان قريب"},
    {"id": "C6-07", "input": "يحب الأطفال اللعب في الحديقة وركوب الدراجات والجري بين الأشجار"},
    {"id": "C6-08", "input": "رغم صعوبة الامتحان إلا أن الطلاب حققوا نتائج مبهرة"},
    {"id": "C6-09", "input": "سافر العالم إلى عدة دول لحضور المؤتمرات العلمية ونشر أبحاثه"},
    {"id": "C6-10", "input": "يا بني اجتهد في دراستك فالعلم نور والجهل ظلام"},
]

# ═══════════════════════════════════════════════════════════════════
# RUNNERS
# ═══════════════════════════════════════════════════════════════════

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def run_spelling_tests():
    results = []

    log("=== Category 2: Overcorrection (10 tests) ===")
    for test in CAT2_OVERCORRECTION:
        log(f"  {test['id']}: {test['input'][:50]}...")
        a = track_a_spelling(test['input'])
        b = track_b_analyze(test['input'])
        fp = a.get('changed', False)
        result = {
            "id": test['id'], "category": 2, "input": test['input'],
            "domain": test['domain'],
            "track_a_spelling": a['output'],
            "track_a_changed": a.get('changed', False),
            "track_b_suggestions": len(b.get('suggestions', [])),
            "track_b_corrected": b.get('corrected', ''),
            "is_false_positive": fp,
        }
        status = "⚠ FP" if fp else "✓"
        log(f"    {status} A:'{a['output'][:60]}' B_sugg:{len(b.get('suggestions',[]))}")
        results.append(result)

    log("\n=== Category 8: Clitic/Prefix (30 tests) ===")
    for test in CAT8_TESTS:
        a = track_a_spelling(test['input'])
        changed = a.get('changed', False)
        if changed:
            # Classify: did it preserve root or mangle it?
            output = a['output']
            root_preserved = test['root'] in output or any(
                test['root'][:-1] in output  # partial root match
                for _ in [1]
            )
            classification = "root_fixed" if root_preserved else "prefix_mangled"
        else:
            classification = "correct"
        result = {
            "id": test['id'], "category": 8, "input": test['input'],
            "root": test['root'], "root_type": test['root_type'],
            "prefix": test['prefix'],
            "track_a_spelling": a['output'], "changed": changed,
            "classification": classification,
        }
        if changed:
            log(f"  ⚠ {test['id']}: '{test['input']}' → '{a['output']}' [{classification}]")
        results.append(result)

    log("\n=== Category 9: Confusable Words (24 tests) ===")
    for test in CAT9_CONFUSABLE:
        a = track_a_spelling(test['input'])
        result = {
            "id": test['id'], "category": 9, "input": test['input'],
            "context": test['context'], "concern": test['concern'],
            "track_a_spelling": a['output'], "changed": a.get('changed', False),
        }
        if a.get('changed'):
            log(f"  ⚠ {test['id']}: '{test['input']}' → '{a['output']}' (concern: {test['concern']})")
        else:
            log(f"  ✓ {test['id']}: no change")
        results.append(result)

    log("\n=== Category 10: Arabic Edge Cases (15 tests) ===")
    for test in CAT10_EDGE_CASES:
        a = track_a_spelling(test['input'])
        result = {
            "id": test['id'], "category": 10, "input": test['input'],
            "concern": test['concern'],
            "track_a_spelling": a['output'], "changed": a.get('changed', False),
        }
        if a.get('changed'):
            log(f"  ⚠ {test['id']}: '{test['input']}' → '{a['output']}' [{test['concern']}]")
        else:
            log(f"  ✓ {test['id']}: no change [{test['concern']}]")
        results.append(result)

    return results

def run_punctuation_tests():
    results = []

    log("=== Category 5: Punctuation Sanity (5 tests) ===")
    for test in CAT5_PUNC_SANITY:
        log(f"  {test['id']}: {test['input'][:50]}...")
        a = track_a_punctuation(test['input'])
        result = {
            "id": test['id'], "category": 5, "input": test['input'],
            "length": test['length'],
            "track_a_punc": a['output'],
            "marks_added": a.get('marks_added', 0),
            "changed": a.get('changed', False),
        }
        log(f"    Marks: +{a.get('marks_added', 0)} | Output: {a['output'][:80]}")
        results.append(result)

    log("\n=== Category 6: Punctuation Position (10 tests) ===")
    for test in CAT6_PUNC_POSITION:
        log(f"  {test['id']}: {test['input'][:50]}...")
        # Track A: raw punctuation on original text
        a_punc = track_a_punctuation(test['input'])
        # Track B: full pipeline
        b = track_b_analyze(test['input'])

        # Measure: where did Track A put punctuation marks?
        a_marks = _find_punct_positions(test['input'], a_punc['output'])
        # Measure: where did Track B put punctuation suggestions?
        b_punc_sugg = [s for s in b.get('suggestions', []) if s.get('type') == 'punctuation']
        b_marks = [(s.get('start', 0), s.get('end', 0), s.get('correction', '')) for s in b_punc_sugg]

        result = {
            "id": test['id'], "category": 6, "input": test['input'],
            "track_a_punc_output": a_punc['output'],
            "track_a_marks": a_marks,
            "track_b_corrected": b.get('corrected', ''),
            "track_b_punc_suggestions": b_punc_sugg,
            "track_b_marks": b_marks,
        }
        log(f"    A marks: {a_marks}")
        log(f"    B marks: {b_marks}")
        results.append(result)

    return results

def _find_punct_positions(original, punctuated):
    """Find where punctuation was added by comparing original vs punctuated."""
    PUNC = set('.,;:!?،؛؟')
    marks = []
    # Word-level alignment
    orig_words = original.split()
    punc_words = punctuated.split()
    oi, pi = 0, 0
    char_pos = 0
    while oi < len(orig_words) and pi < len(punc_words):
        o_base = ''.join(c for c in orig_words[oi] if c not in PUNC)
        p_base = ''.join(c for c in punc_words[pi] if c not in PUNC)
        if o_base == p_base:
            # Same word — check for added punctuation
            o_punc = set(c for c in orig_words[oi] if c in PUNC)
            p_punc = set(c for c in punc_words[pi] if c in PUNC)
            added = p_punc - o_punc
            if added:
                marks.append({
                    "word_index": oi, "word": orig_words[oi],
                    "after_word": orig_words[oi],
                    "marks_added": list(added),
                    "char_pos": char_pos,
                })
            char_pos += len(orig_words[oi]) + 1  # +1 for space
            oi += 1
            pi += 1
        else:
            # Mismatch — model changed the word
            char_pos += len(orig_words[oi]) + 1
            oi += 1
            pi += 1
    return marks

def run_pipeline_comparison():
    """Run tests that need both Track A and Track B for comparison (Cat 1, 3, 4, 7)."""
    results = []

    # Cat 3: Integration-only — test where raw models work but pipeline might not
    log("=== Category 3: Integration-Only (5 tests) ===")
    integration_inputs = [
        {"id": "C3-01", "input": "كانت الفتيات يلعبون في الحديقه وفجأه سقطت احداهن وبدءت تبكي بشده"},
        {"id": "C3-02", "input": "ان الذكاء الاصطناعي يلعب دورا هاما ولذالك يجب الاهتمام بة"},
        {"id": "C3-03", "input": "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة رغبة في بناء كتلة عضلية قوية ويا له من التزام حديدي يثير الإعجاب"},
        {"id": "C3-04", "input": "هذة المدينه جميله جدا ومناخها معتدل طوال العام"},
        {"id": "C3-05", "input": "الطلاب الذين اجتهدو في دراستهم حققو نتائج ممتازه في الامتحانات"},
    ]
    for test in integration_inputs:
        log(f"  {test['id']}: {test['input'][:50]}...")
        a_spell = track_a_spelling(test['input'])
        a_gram = track_a_grammar(test['input'])
        a_punc = track_a_punctuation(test['input'])
        b = track_b_analyze(test['input'])
        result = {
            "id": test['id'], "category": 3, "input": test['input'],
            "track_a": {
                "spelling": a_spell['output'], "spelling_changed": a_spell.get('changed'),
                "grammar": a_gram['output'], "grammar_changed": a_gram.get('changed'),
                "punctuation": a_punc['output'], "punctuation_changed": a_punc.get('changed'),
            },
            "track_b": {
                "corrected": b.get('corrected', ''),
                "suggestions": b.get('suggestions', []),
                "timing_ms": b.get('timing_ms', {}),
            }
        }
        log(f"    A_spell: {a_spell['output'][:60]}")
        log(f"    A_gram:  {a_gram['output'][:60]}")
        log(f"    A_punc:  {a_punc['output'][:60]}")
        log(f"    B_final: {b.get('corrected','')[:60]}")
        log(f"    B_sugg:  {len(b.get('suggestions',[]))}")
        results.append(result)

    # Cat 4: Overlap — run 3x for determinism
    log("\n=== Category 4: Overlap Resolution (3 tests × 3 runs) ===")
    overlap_inputs = [
        {"id": "C4-01", "input": "كانت الفتيات يلعبون في الحديقه"},
        {"id": "C4-02", "input": "ذهب الى المدرسه وقابل المعلمه"},
        {"id": "C4-03", "input": "ان الطالبات ذهبو الى الجامعه"},
    ]
    for test in overlap_inputs:
        runs = []
        for run_idx in range(3):
            b = track_b_analyze(test['input'])
            runs.append({
                "run": run_idx + 1,
                "corrected": b.get('corrected', ''),
                "suggestions": b.get('suggestions', []),
            })
        # Check determinism
        all_same = all(r['corrected'] == runs[0]['corrected'] for r in runs)
        result = {
            "id": test['id'], "category": 4, "input": test['input'],
            "runs": runs, "deterministic": all_same,
        }
        log(f"  {test['id']}: deterministic={all_same}")
        for r in runs:
            log(f"    Run {r['run']}: {r['corrected'][:60]} ({len(r['suggestions'])} sugg)")
        results.append(result)

    return results

# Boundary tests for spelling 300-char cutoff
def run_boundary_tests():
    results = []
    log("\n=== Boundary: Spelling 300-char cutoff ===")
    base = "يستخدم الذكاء الاصطناعي تقنيات التعلم العميق في معالجة البيانات "
    for target_len in [299, 300, 301, 500]:
        text = (base * 10)[:target_len]
        b = track_b_analyze(text)
        has_spelling = any(s.get('type') == 'spelling' for s in b.get('suggestions', []))
        result = {
            "id": f"BOUND-{target_len}", "category": 3, "input_len": target_len,
            "input": text[:80] + "...",
            "has_spelling_suggestions": has_spelling,
            "total_suggestions": len(b.get('suggestions', [])),
            "timing": b.get('timing_ms', {}),
        }
        log(f"  len={target_len}: spelling_active={has_spelling} suggestions={len(b.get('suggestions',[]))}")
        results.append(result)
    return results

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='BAYAN Deep-Dive Test Harness')
    parser.add_argument('--stage', choices=['spelling', 'grammar', 'punctuation', 'pipeline', 'all'],
                       default='spelling')
    args = parser.parse_args()

    all_results = {"timestamp": datetime.now(timezone.utc).isoformat(), "api_base": API_BASE}

    # Health check
    log(f"Checking API health at {API_BASE}...")
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        log(f"  Health: {resp.status_code} — {resp.json()}")
        all_results['health'] = resp.json()
    except Exception as e:
        log(f"  ⚠ API unreachable: {e}")
        all_results['health'] = {"error": str(e)}

    if args.stage in ('spelling', 'all'):
        log("\n══════ SPELLING TESTS (Cat 2, 8, 9, 10) ══════")
        all_results['spelling_tests'] = run_spelling_tests()

    if args.stage in ('punctuation', 'all'):
        log("\n══════ PUNCTUATION TESTS (Cat 5, 6) ══════")
        all_results['punctuation_tests'] = run_punctuation_tests()

    if args.stage in ('pipeline', 'all'):
        log("\n══════ PIPELINE TESTS (Cat 3, 4) ══════")
        all_results['pipeline_tests'] = run_pipeline_comparison()
        all_results['boundary_tests'] = run_boundary_tests()

    # Save
    output_path = os.path.join(os.path.dirname(__file__), 'deep_dive_output.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    log(f"\nResults saved to {output_path}")

    # Summary
    for key in ['spelling_tests', 'punctuation_tests', 'pipeline_tests', 'boundary_tests']:
        if key in all_results:
            tests = all_results[key]
            if isinstance(tests, list):
                changed = sum(1 for t in tests if t.get('changed') or t.get('is_false_positive'))
                log(f"  {key}: {len(tests)} tests, {changed} with changes")

if __name__ == '__main__':
    main()
