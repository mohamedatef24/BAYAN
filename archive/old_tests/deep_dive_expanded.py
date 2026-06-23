"""
BAYAN Deep-Dive Test Harness — EXPANDED (ALL Categories)
Covers every item from the original prompt that was missing.
"""
import sys, os, re, json, time, argparse, concurrent.futures
from datetime import datetime, timezone
import requests

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 60

def api_call(endpoint, text, retries=2):
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
            return {"error": f"Timeout after {TIMEOUT}s"}
        except Exception as e:
            return {"error": str(e)}

def track_a_spelling(text):
    r = api_call("/api/spelling", text)
    if "error" in r and "corrected_text" not in r:
        return {"input": text, "output": text, "error": r["error"], "changed": False}
    c = r.get("corrected_text", text)
    return {"input": text, "output": c, "changed": c != text, "elapsed_ms": r.get("_elapsed_ms")}

def track_a_grammar(text):
    r = api_call("/api/grammar", text)
    if "error" in r and "corrected_text" not in r:
        return {"input": text, "output": text, "error": r["error"], "changed": False}
    c = r.get("corrected_text", text)
    return {"input": text, "output": c, "changed": c != text, "elapsed_ms": r.get("_elapsed_ms"), "timestamp": r.get("_timestamp")}

def track_a_punctuation(text):
    r = api_call("/api/punctuation", text)
    if "error" in r and "corrected_text" not in r:
        return {"input": text, "output": text, "error": r["error"], "changed": False}
    c = r.get("corrected_text", text)
    PUNC = '.,;:!?،؛؟'
    return {"input": text, "output": c, "changed": c != text,
            "marks_added": sum(1 for ch in c if ch in PUNC) - sum(1 for ch in text if ch in PUNC),
            "elapsed_ms": r.get("_elapsed_ms")}

def track_b_analyze(text):
    r = api_call("/api/analyze", text)
    if "error" in r and "suggestions" not in r:
        return {"input": text, "error": r["error"], "suggestions": [], "corrected": text}
    return {
        "input": text, "original": r.get("original", text),
        "corrected": r.get("corrected", text),
        "suggestions": r.get("suggestions", []),
        "timing_ms": r.get("timing_ms", {}),
        "elapsed_ms": r.get("_elapsed_ms"),
    }

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ═══════════════════════════════════════════════════════════════════
# CATEGORY 1 — Cross-model mismatch
# ═══════════════════════════════════════════════════════════════════
def run_cat1():
    log("=== CATEGORY 1: Cross-model mismatch ===")
    results = []
    inputs = [
        {"id": "C1-01", "input": "كانت الفتيات يلعبون في الحديقه"},
        {"id": "C1-02", "input": "ان الطالبات ذهبو الى الجامعه"},
        {"id": "C1-03", "input": "هذة المدينه جميله جدا ومناخها معتدل"},
        {"id": "C1-04", "input": "الطلاب اجتهدو في دراستهم وحققو نتائج ممتازه"},
        {"id": "C1-05", "input": "ذهب الولد الى المكتبه وقرا كتاب مفيد"},
    ]
    for test in inputs:
        log(f"  {test['id']}: {test['input'][:50]}...")
        # Track A: each model on ORIGINAL independently
        a_spell = track_a_spelling(test['input'])
        a_gram_on_orig = track_a_grammar(test['input'])
        # NEW: grammar on SPELLING-CORRECTED text
        a_gram_on_spell = track_a_grammar(a_spell['output'])
        a_punc = track_a_punctuation(test['input'])
        # Track B
        b = track_b_analyze(test['input'])

        # Diff: grammar on original vs grammar on spell-corrected
        gram_orig_words = a_gram_on_orig['output'].split()
        gram_spell_words = a_gram_on_spell['output'].split()
        gram_diff = []
        for i, (w1, w2) in enumerate(zip(gram_orig_words, gram_spell_words)):
            if w1 != w2:
                gram_diff.append({"word_idx": i, "gram_on_orig": w1, "gram_on_spell": w2})

        result = {
            "id": test['id'], "category": 1, "input": test['input'],
            "a_spelling": a_spell['output'],
            "a_grammar_on_original": a_gram_on_orig['output'],
            "a_grammar_on_spell_corrected": a_gram_on_spell['output'],
            "a_punctuation": a_punc['output'],
            "grammar_diff_orig_vs_spell": gram_diff,
            "b_corrected": b.get('corrected', ''),
            "b_suggestions": b.get('suggestions', []),
        }
        log(f"    A_spell: {a_spell['output'][:60]}")
        log(f"    A_gram(orig): {a_gram_on_orig['output'][:60]}")
        log(f"    A_gram(spell): {a_gram_on_spell['output'][:60]}")
        log(f"    Grammar diff: {gram_diff}")
        log(f"    B_final: {b.get('corrected','')[:60]}")
        results.append(result)
    return results

# ═══════════════════════════════════════════════════════════════════
# CATEGORY 7 — StageLocker adversarial tests
# ═══════════════════════════════════════════════════════════════════
def run_cat7():
    log("=== CATEGORY 7: StageLocker directionality ===")
    results = []
    # 3+ chained mutations: spelling changes length, grammar changes length, punc adds marks
    inputs = [
        {"id": "C7-01", "input": "ذهب الولد الى المدرسه وقابل المعلمه واخذ الكتاب",
         "desc": "3-stage chain: spelling الى→إلى, grammar المدرسه→المدرسة, punc adds marks"},
        {"id": "C7-02", "input": "كانت البنات يلعبون في الحديقه الجميله وفجأه سقطت احداهن",
         "desc": "Multiple overlapping corrections across all stages"},
        {"id": "C7-03", "input": "ان الذكاء الاصطناعي يلعب دورا هاما في تطوير التكنولوجيا الحديثه ولذالك يجب الاهتمام بة",
         "desc": "Long sentence with corrections from all 3 stages"},
        {"id": "C7-04", "input": "هذة المدينه جميله جدا ومناخها معتدل طوال العام وسكانها طيبون جدا",
         "desc": "Multiple ه→ة fixes: does grammar lock prevent punc from adding marks near those words?"},
        {"id": "C7-05", "input": "الطلاب اللذين اجتهدو في دراستهم حققو نتائج ممتازه في الأمتحانات الصعبه",
         "desc": "Heavy corrections needed across stages"},
    ]
    for test in inputs:
        log(f"  {test['id']}: {test['input'][:50]}...")
        a_spell = track_a_spelling(test['input'])
        a_gram = track_a_grammar(test['input'])
        a_punc = track_a_punctuation(test['input'])
        b = track_b_analyze(test['input'])

        # Check: are any suggestions at positions that overlap with corrections from earlier stages?
        sugg = b.get('suggestions', [])
        overlaps = []
        for i, s1 in enumerate(sugg):
            for j, s2 in enumerate(sugg):
                if i < j and s1.get('start',0) < s2.get('end',0) and s2.get('start',0) < s1.get('end',0):
                    overlaps.append({"s1": s1, "s2": s2})

        result = {
            "id": test['id'], "category": 7, "input": test['input'],
            "desc": test['desc'],
            "a_spelling": a_spell['output'],
            "a_grammar": a_gram['output'],
            "a_punc": a_punc['output'],
            "b_corrected": b.get('corrected', ''),
            "b_suggestions": sugg,
            "b_suggestion_count": len(sugg),
            "overlapping_suggestions": overlaps,
        }
        log(f"    B_final: {b.get('corrected','')[:60]}")
        log(f"    Suggestions: {len(sugg)}, Overlaps: {len(overlaps)}")
        results.append(result)
    return results

# ═══════════════════════════════════════════════════════════════════
# CATEGORY 8 EXPANDED — with ال + prefix combos
# ═══════════════════════════════════════════════════════════════════
def run_cat8_expanded():
    log("=== CATEGORY 8 EXPANDED: ال + prefix combos ===")
    results = []
    combos = [
        # root, al_form, wal_form, bal_form, lal_form
        ("مدرسة", "المدرسة", "والمدرسة", "بالمدرسة", "للمدرسة"),
        ("شمس", "الشمس", "والشمس", "بالشمس", "للشمس"),
        ("أمة", "الأمة", "والأمة", "بالأمة", "للأمة"),
        ("نافذة", "النافذة", "والنافذة", "بالنافذة", "للنافذة"),
        ("علم", "العلم", "والعلم", "بالعلم", "للعلم"),
        ("اقتصاد", "الاقتصاد", "والاقتصاد", "بالاقتصاد", "للاقتصاد"),
    ]
    for root, al, wal, bal, lal in combos:
        for label, word in [("al", al), ("wal", wal), ("bal", bal), ("lal", lal)]:
            a = track_a_spelling(word)
            result = {
                "id": f"C8X-{root}-{label}", "category": 8, "input": word,
                "root": root, "prefix_combo": label,
                "track_a_spelling": a['output'], "changed": a.get('changed', False),
            }
            if a.get('changed'):
                log(f"  ⚠ C8X-{root}-{label}: '{word}' → '{a['output']}'")
            results.append(result)
    return results

# ═══════════════════════════════════════════════════════════════════
# CATEGORY 9 EXPANDED — missing pairs
# ═══════════════════════════════════════════════════════════════════
def run_cat9_expanded():
    log("=== CATEGORY 9 EXPANDED: Missing confusable pairs ===")
    results = []
    tests = [
        # إنّ / أنّ (with shadda)
        {"id": "C9X-01", "input": "إنّ", "context": "isolation", "concern": "stays إنّ"},
        {"id": "C9X-02", "input": "أنّ", "context": "isolation", "concern": "stays أنّ"},
        {"id": "C9X-03", "input": "إنّ العلم نور", "context": "sentence", "concern": "إنّ stays"},
        {"id": "C9X-04", "input": "علمت أنّ الامتحان صعب", "context": "sentence", "concern": "أنّ stays"},
        # على vs علي (name)
        {"id": "C9X-05", "input": "علي", "context": "isolation", "concern": "could be name علي or على"},
        {"id": "C9X-06", "input": "ذهب علي إلى المدرسة", "context": "sentence", "concern": "علي is a name here"},
        {"id": "C9X-07", "input": "جلس علي الكرسي", "context": "sentence", "concern": "AMBIGUOUS: علي=name or على=on"},
    ]
    for test in tests:
        a = track_a_spelling(test['input'])
        result = {
            "id": test['id'], "category": 9, "input": test['input'],
            "context": test['context'], "concern": test['concern'],
            "track_a_spelling": a['output'], "changed": a.get('changed', False),
        }
        if a.get('changed'):
            log(f"  ⚠ {test['id']}: '{test['input']}' → '{a['output']}' ({test['concern']})")
        else:
            log(f"  ✓ {test['id']}: no change")
        results.append(result)
    return results

# ═══════════════════════════════════════════════════════════════════
# CATEGORY 10 EXPANDED — sentence position + 200-word drift test
# ═══════════════════════════════════════════════════════════════════
def run_cat10_expanded():
    log("=== CATEGORY 10 EXPANDED: Position + Cumulative drift ===")
    results = []

    # Same error at sentence start vs middle
    log("  Sentence-initial vs mid-sentence:")
    position_tests = [
        {"id": "C10X-01a", "input": "الحديقه جميلة جدا", "concern": "error_at_start"},
        {"id": "C10X-01b", "input": "الجو حار في الحديقه", "concern": "error_at_end"},
        {"id": "C10X-02a", "input": "الى المدرسة ذهب الولد", "concern": "error_at_start"},
        {"id": "C10X-02b", "input": "ذهب الولد الى المدرسة", "concern": "error_at_end"},
    ]
    for test in position_tests:
        a = track_a_spelling(test['input'])
        b = track_b_analyze(test['input'])
        result = {
            "id": test['id'], "category": 10, "input": test['input'],
            "concern": test['concern'],
            "track_a_spelling": a['output'], "a_changed": a.get('changed', False),
            "track_b_corrected": b.get('corrected', ''),
            "track_b_suggestions": len(b.get('suggestions', [])),
        }
        log(f"    {test['id']}: A='{a['output'][:40]}' B_sugg={len(b.get('suggestions',[]))}")
        results.append(result)

    # 200+ word cumulative drift test
    log("\n  200+ word cumulative drift test:")
    long_text = (
        "كانت الفتيات يلعبون في الحديقه الجميله وفجأه سقطت احداهن وبدءت تبكي بشده "
        "ذهب الولد الى المدرسه وقابل المعلمه واخذ الكتاب "
        "ان الذكاء الاصطناعي يلعب دورا هاما في تطوير التكنولوجيا "
        "هذة المدينه جميله جدا ومناخها معتدل طوال العام "
        "الطلاب الذين اجتهدو في دراستهم حققو نتائج ممتازه "
        "سافر محمد إلى دبي للعمل في شركة جوجل وقابل أصدقاءه القدامى "
        "يستخدم الذكاء الاصطناعي تقنيات التعلم العميق في معالجة البيانات الضخمة "
        "القاهرة عاصمة جمهورية مصر العربية وأكبر مدنها وتقع على ضفاف نهر النيل "
        "تتراوح درجات الحرارة بين خمس وعشرين وثلاثين درجة مئوية في فصل الصيف "
        "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين "
        "بسم الله الرحمن الرحيم نبدأ هذة المحاضره عن اهمية التعليم "
        "يحب الأطفال اللعب في الحديقة وركوب الدراجات والجري بين الأشجار "
    )
    word_count = len(long_text.split())
    log(f"    Input: {word_count} words, {len(long_text)} chars")

    b = track_b_analyze(long_text)
    sugg = b.get('suggestions', [])
    # Check coordinates in the back half
    mid_char = len(long_text) // 2
    back_half_sugg = [s for s in sugg if s.get('start', 0) >= mid_char]
    front_half_sugg = [s for s in sugg if s.get('start', 0) < mid_char]

    # Verify coordinates: does original[start:end] == suggestion['original']?
    coord_mismatches = []
    for s in sugg:
        start, end = s.get('start', 0), s.get('end', 0)
        expected_text = long_text[start:end]
        actual_text = s.get('original', '')
        if expected_text != actual_text:
            coord_mismatches.append({
                "start": start, "end": end,
                "expected_from_coords": expected_text,
                "actual_in_suggestion": actual_text,
                "correction": s.get('correction', ''),
                "type": s.get('type', ''),
            })

    result = {
        "id": "C10X-DRIFT", "category": 10, "input_len": len(long_text),
        "word_count": word_count,
        "total_suggestions": len(sugg),
        "front_half_suggestions": len(front_half_sugg),
        "back_half_suggestions": len(back_half_sugg),
        "coordinate_mismatches": coord_mismatches,
        "suggestions_detail": sugg,
    }
    log(f"    Total suggestions: {len(sugg)} (front: {len(front_half_sugg)}, back: {len(back_half_sugg)})")
    log(f"    Coordinate mismatches: {len(coord_mismatches)}")
    for m in coord_mismatches:
        log(f"      [{m['start']}:{m['end']}] expected='{m['expected_from_coords']}' got='{m['actual_in_suggestion']}'")
    results.append(result)

    return results

# ═══════════════════════════════════════════════════════════════════
# CATEGORY 11 — Genuine stress tests / edge cases
# ═══════════════════════════════════════════════════════════════════
def run_cat11():
    log("=== CATEGORY 11: Edge case discovery (stress tests) ===")
    results = []
    tests = [
        # Pathological inputs
        {"id": "C11-01", "input": "", "desc": "empty_string"},
        {"id": "C11-02", "input": " ", "desc": "whitespace_only"},
        {"id": "C11-03", "input": "أ", "desc": "single_char"},
        {"id": "C11-04", "input": "مستشفياتهم", "desc": "long_single_word"},
        {"id": "C11-05", "input": "ذهبالولدالىالمدرسةوقابلالمعلمة", "desc": "no_spaces"},
        {"id": "C11-06", "input": "...!؟،،؛؛::...", "desc": "all_punctuation"},
        {"id": "C11-07", "input": "(([{هذا النص}]))", "desc": "unbalanced_brackets"},
        {"id": "C11-08", "input": "\"هذا\" 'نص' «اختبار»", "desc": "mixed_quotes"},
        # Boundary lengths (299, 300, 301 chars)
        {"id": "C11-09", "input": ("يستخدم الذكاء الاصطناعي تقنيات التعلم العميق " * 10)[:299], "desc": "len_299"},
        {"id": "C11-10", "input": ("يستخدم الذكاء الاصطناعي تقنيات التعلم العميق " * 10)[:300], "desc": "len_300"},
        {"id": "C11-11", "input": ("يستخدم الذكاء الاصطناعي تقنيات التعلم العميق " * 10)[:301], "desc": "len_301"},
        # Max disagreement: word that is both plausible spelling error AND grammatically ambiguous
        {"id": "C11-12", "input": "يلعب الطلاب في الحديقه بعد المدرسه وقبل العشاء", "desc": "multi_stage_disagreement"},
        # Correction identical to original (model returns same text)
        {"id": "C11-13", "input": "الحمد لله", "desc": "model_returns_identical"},
        # Very long repetitive text
        {"id": "C11-14", "input": "مرحبا " * 100, "desc": "100x_repeated_word"},
        # Mixed Arabic and English heavily
        {"id": "C11-15", "input": "I went to the مدرسة and met the معلم in the فصل", "desc": "heavy_code_switch"},
        # Dialectal variations
        {"id": "C11-16", "input": "ايش هالحكي يا زلمة", "desc": "levantine_dialect"},
        {"id": "C11-17", "input": "شنو تسوي هسه", "desc": "iraqi_dialect"},
    ]
    for test in tests:
        log(f"  {test['id']}: '{test['input'][:40]}...' [{test['desc']}]")
        # Track B only for stress tests (we want to see if pipeline crashes)
        b = track_b_analyze(test['input'])
        crashed = "error" in b and "suggestions" not in b
        result = {
            "id": test['id'], "category": 11, "input": test['input'][:200],
            "desc": test['desc'], "input_len": len(test['input']),
            "crashed": crashed,
            "b_corrected": b.get('corrected', '')[:200] if not crashed else "CRASH",
            "b_suggestions": len(b.get('suggestions', [])),
            "error": b.get('error', None),
        }
        status = "💥 CRASH" if crashed else f"✓ ({len(b.get('suggestions',[]))} sugg)"
        log(f"    {status}")
        results.append(result)

    # Race condition: 2 parallel requests with same input
    log("\n  Race condition test (2 parallel requests):")
    race_input = "كانت الفتيات يلعبون في الحديقه"
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(track_b_analyze, race_input)
        f2 = ex.submit(track_b_analyze, race_input)
        r1, r2 = f1.result(), f2.result()
    race_match = r1.get('corrected') == r2.get('corrected') and len(r1.get('suggestions',[])) == len(r2.get('suggestions',[]))
    race_result = {
        "id": "C11-RACE", "category": 11, "input": race_input,
        "desc": "parallel_race_condition",
        "r1_corrected": r1.get('corrected', ''),
        "r2_corrected": r2.get('corrected', ''),
        "r1_suggestions": len(r1.get('suggestions', [])),
        "r2_suggestions": len(r2.get('suggestions', [])),
        "identical": race_match,
    }
    log(f"    Race test: identical={race_match}")
    results.append(race_result)

    return results

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['cat1', 'cat7', 'cat8x', 'cat9x', 'cat10x', 'cat11', 'all'], default='all')
    args = parser.parse_args()

    all_results = {"timestamp": datetime.now(timezone.utc).isoformat(), "api_base": API_BASE}

    # Health check
    log(f"Health check: {API_BASE}")
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        log(f"  OK: {resp.status_code}")
        all_results['health'] = resp.json()
    except Exception as e:
        log(f"  FAIL: {e}")
        return

    if args.stage in ('cat1', 'all'):
        all_results['cat1'] = run_cat1()
    if args.stage in ('cat7', 'all'):
        all_results['cat7'] = run_cat7()
    if args.stage in ('cat8x', 'all'):
        all_results['cat8x'] = run_cat8_expanded()
    if args.stage in ('cat9x', 'all'):
        all_results['cat9x'] = run_cat9_expanded()
    if args.stage in ('cat10x', 'all'):
        all_results['cat10x'] = run_cat10_expanded()
    if args.stage in ('cat11', 'all'):
        all_results['cat11'] = run_cat11()

    output_path = os.path.join(os.path.dirname(__file__), 'deep_dive_expanded.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    log(f"\nSaved to {output_path}")

if __name__ == '__main__':
    main()
