"""
Gap-filling live tests for all missing items from the Fix-Everything prompt.
Covers:
  Phase 1.3 — Category 9 pairs: لكن/لاكن, ذلك/ذالك, الى/إلى live verification
  Phase 2   — R-01→R-10 rare vocabulary FP measurement  
  Phase 3.2 — ولذالك and مستشفياتهم specific cases
  Phase 5.5 — Constructed dual-correction cases
  Phase 6.3 — BUG-017 re-test
  Phase 6.4 — 187-word input regression
  Phase 7.1 — BUG-018 precise tracing
"""
import sys, os, json, time, requests

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 90

def api_call(endpoint, text, timeout=TIMEOUT):
    url = f"{API_BASE}{endpoint}"
    try:
        t0 = time.time()
        resp = requests.post(url, json={"text": text}, timeout=timeout)
        elapsed = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data['_elapsed_ms'] = elapsed
            return data
        return {"error": f"HTTP {resp.status_code}", "_elapsed_ms": elapsed}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


all_results = {}


# ══════════════════════════════════════════════════════════════════════
# Phase 1.3 — Category 9 Pairs Live Verification
# ══════════════════════════════════════════════════════════════════════
def test_category9_live():
    print("=" * 70)
    print("PHASE 1.3 — Category 9 Pairs Live Verification")
    print("=" * 70)

    pairs = [
        # (input_text, word_that_must_NOT_change, description)
        ("لكن الأمر مختلف", "لكن", "لكن must NOT become لاكن"),
        ("ذلك الكتاب جميل", "ذلك", "ذلك must NOT become ذالك"),
        ("إلى المدرسة", "إلى", "إلى must NOT become على"),
        ("على الطاولة", "على", "على must NOT become إلى"),
        ("هذه المدينة جميلة", "هذه", "هذه must NOT become هذة"),
        ("كان الجو حارا", "كان", "كان must NOT become كأن"),
        # Reverse direction: misspellings SHOULD be corrected
        ("لاكن الأمر مختلف", "لاكن→لكن", "لاكن should become لكن"),
        ("ذالك الكتاب جميل", "ذالك→ذلك", "ذالك should become ذلك"),
    ]

    results = []
    for text, check, desc in pairs:
        r = api_call("/api/analyze", text)
        corrected = r.get("corrected", text)
        suggestions = r.get("suggestions", [])

        is_reverse = "→" in check
        if is_reverse:
            # For misspellings, check that correction happened
            orig, expected = check.split("→")
            if expected in corrected and orig not in corrected:
                status = "✅ CORRECTED"
            elif orig in corrected:
                status = "⚠ NOT corrected (pipeline didn't fix misspelling)"
            else:
                status = "⚠ UNCLEAR"
        else:
            # For correct words, check they weren't corrupted
            if check in corrected:
                status = "✅ PRESERVED"
            else:
                status = "❌ CORRUPTED"

        result = {
            "input": text, "corrected": corrected,
            "check": check, "status": status,
            "suggestions": len(suggestions),
        }
        results.append(result)
        print(f"\n  {desc}")
        print(f"    Input:     '{text}'")
        print(f"    Corrected: '{corrected}'")
        print(f"    {status}")

    return results


# ══════════════════════════════════════════════════════════════════════
# Phase 2 — R-01→R-10 Rare Vocabulary FP Measurement
# ══════════════════════════════════════════════════════════════════════
def test_rare_vocabulary():
    print("\n" + "=" * 70)
    print("PHASE 2 — R-01→R-10 Rare Vocabulary FP Measurement")
    print("=" * 70)

    # R-01 through R-10: valid but uncommon Arabic words
    rare_words = [
        {"id": "R-01", "word": "عصماء", "sentence": "المدينة العصماء تحتضن آلاف السكان",
         "desc": "عصماء = impeccable (feminine)"},
        {"id": "R-02", "word": "يستشف", "sentence": "يستشف الباحث نتائج الدراسة بعناية",
         "desc": "يستشف = to discern/perceive"},
        {"id": "R-03", "word": "المسغبة", "sentence": "أرهقته المسغبة والعطش الشديد",
         "desc": "المسغبة = severe hunger"},
        {"id": "R-04", "word": "التقاعس", "sentence": "التقاعس عن العمل يؤدي إلى الفشل",
         "desc": "التقاعس = negligence/laziness"},
        {"id": "R-05", "word": "استئثار", "sentence": "استئثار السلطة يهدد الديمقراطية",
         "desc": "استئثار = monopolization"},
        {"id": "R-06", "word": "تبجيل", "sentence": "تبجيل العلماء واجب على المجتمع",
         "desc": "تبجيل = veneration"},
        {"id": "R-07", "word": "الدمث", "sentence": "الرجل الدمث يحبه الجميع",
         "desc": "الدمث = gentle/affable person"},
        {"id": "R-08", "word": "استقصاء", "sentence": "استقصاء الحقائق مهم في الصحافة",
         "desc": "استقصاء = investigation/inquiry"},
        {"id": "R-09", "word": "التواني", "sentence": "لا يجوز التواني في طلب العلم",
         "desc": "التواني = procrastination"},
        {"id": "R-10", "word": "مستطرف", "sentence": "كتاب المستطرف من أمهات الكتب العربية",
         "desc": "مستطرف = novel/curious (literary term)"},
    ]

    false_positives = 0
    total = len(rare_words)
    results = []

    for item in rare_words:
        # Track A: Raw spelling
        a = api_call("/api/spelling", item["sentence"])
        a_out = a.get("corrected_text", item["sentence"])
        a_changed_word = item["word"] not in a_out

        # Track B: Pipeline
        b = api_call("/api/analyze", item["sentence"])
        b_out = b.get("corrected", item["sentence"])
        b_suggestions = b.get("suggestions", [])
        b_changed_word = item["word"] not in b_out

        # Check if any suggestion targets the rare word
        word_targeted = False
        targeting_suggestion = None
        for s in b_suggestions:
            if s.get("original", "") == item["word"]:
                word_targeted = True
                targeting_suggestion = s
                break

        is_fp = b_changed_word or word_targeted
        if is_fp:
            false_positives += 1

        result = {
            "id": item["id"],
            "word": item["word"],
            "raw_changed": a_changed_word,
            "pipeline_changed": b_changed_word,
            "pipeline_targeted": word_targeted,
            "is_false_positive": is_fp,
        }
        results.append(result)

        status = "❌ FALSE POSITIVE" if is_fp else "✅ PRESERVED"
        print(f"\n  {item['id']}: {item['desc']}")
        print(f"    Input:      '{item['sentence'][:60]}...'")
        print(f"    Raw spell:  changed={a_changed_word}")
        if a_changed_word:
            print(f"    Raw output: '{a_out[:60]}...'")
        print(f"    Pipeline:   changed={b_changed_word}, targeted={word_targeted}")
        if b_changed_word:
            print(f"    Pipeline:   '{b_out[:60]}...'")
        if targeting_suggestion:
            print(f"    Suggestion: '{targeting_suggestion.get('original','')}' → '{targeting_suggestion.get('correction','')}' (conf={targeting_suggestion.get('confidence', '?')})")
        print(f"    {status}")

    raw_fp_count = sum(1 for r in results if r["raw_changed"])
    pipeline_fp_count = false_positives
    print(f"\n{'=' * 50}")
    print(f"  Raw model FP rate:  {raw_fp_count}/{total} = {raw_fp_count/total*100:.0f}%")
    print(f"  Pipeline FP rate:   {pipeline_fp_count}/{total} = {pipeline_fp_count/total*100:.0f}%")

    return {
        "total": total,
        "raw_fp_count": raw_fp_count,
        "raw_fp_rate": f"{raw_fp_count/total*100:.0f}%",
        "pipeline_fp_count": pipeline_fp_count,
        "pipeline_fp_rate": f"{pipeline_fp_count/total*100:.0f}%",
        "results": results,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 3.2 — Specific Word-split Cases
# ══════════════════════════════════════════════════════════════════════
def test_word_splits():
    print("\n" + "=" * 70)
    print("PHASE 3.2 — Specific Word-split Verification")
    print("=" * 70)

    cases = [
        {
            "input": "ولذالك قررت السفر",
            "target_word": "ولذالك",
            "expected_correct": "ولذلك",
            "bad_split": "ولذا ذلك",
            "desc": "ولذالك should become ولذلك, NOT 'ولذا ذلك'"
        },
        {
            "input": "المستشفياتهم كبيرة",
            "target_word": "المستشفياتهم",
            "expected_correct": "مستشفياتهم",
            "bad_split": "في مستشفيات هم",
            "desc": "مستشفياتهم should NOT be split into 'في مستشفيات هم'"
        },
    ]

    results = []
    for case in cases:
        r = api_call("/api/analyze", case["input"])
        corrected = r.get("corrected", case["input"])
        suggestions = r.get("suggestions", [])

        has_bad_split = case["bad_split"] in corrected
        has_good_correction = case["expected_correct"] in corrected

        result = {
            "input": case["input"],
            "corrected": corrected,
            "bad_split_present": has_bad_split,
            "good_correction_present": has_good_correction,
        }
        results.append(result)

        print(f"\n  {case['desc']}")
        print(f"    Input:     '{case['input']}'")
        print(f"    Corrected: '{corrected}'")
        if has_bad_split:
            print(f"    ❌ BAD SPLIT detected: '{case['bad_split']}'")
        elif has_good_correction:
            print(f"    ✅ Correctly fixed to '{case['expected_correct']}'")
        else:
            print(f"    ⚠ Neither expected correction nor bad split found")

    return results


# ══════════════════════════════════════════════════════════════════════
# Phase 5.5 — Constructed Dual-correction Cases
# ══════════════════════════════════════════════════════════════════════
def test_dual_corrections():
    print("\n" + "=" * 70)
    print("PHASE 5.5 — Constructed Dual-correction Cases")
    print("=" * 70)

    # Cases where spelling AND grammar would both want to change words
    cases = [
        {
            "input": "الطالبه كتبو الوجبات",
            "desc": "Spelling: الطالبه→الطالبة, Grammar: كتبو→كتبوا + possibly الوجبات→الواجبات",
        },
        {
            "input": "هو ذهبو الي البيت",
            "desc": "Spelling: الي→إلى, Grammar: ذهبو→ذهب (singular subject هو)",
        },
        {
            "input": "الطلاب اجتهدو في امتحانتهم",
            "desc": "Spelling: امتحانتهم→امتحاناتهم, Grammar: اجتهدو→اجتهدوا",
        },
    ]

    results = []
    for case in cases:
        r = api_call("/api/analyze", case["input"])
        corrected = r.get("corrected", case["input"])
        suggestions = r.get("suggestions", [])

        # Check for text duplication
        words = corrected.split()
        has_duplicate = any(i > 0 and words[i] == words[i-1] for i in range(len(words)))

        # Check for dropped words (output should have ≈ same word count ±1)
        input_words = case["input"].split()
        word_diff = len(words) - len(input_words)

        result = {
            "input": case["input"],
            "corrected": corrected,
            "suggestions": len(suggestions),
            "has_duplicate": has_duplicate,
            "word_count_diff": word_diff,
        }
        results.append(result)

        print(f"\n  {case['desc']}")
        print(f"    Input:     '{case['input']}'")
        print(f"    Corrected: '{corrected}'")
        print(f"    Suggestions: {len(suggestions)}")
        if has_duplicate:
            print(f"    ❌ DUPLICATE WORDS detected in output!")
        else:
            print(f"    ✅ No duplicate words")
        if abs(word_diff) > 2:
            print(f"    ⚠ Word count diff: {word_diff} (possible drop/duplication)")
        else:
            print(f"    ✅ Word count reasonable (diff={word_diff})")

        for s in suggestions:
            print(f"      [{s.get('start')}:{s.get('end')}] {s.get('type')}: '{s.get('original','')}' → '{s.get('correction','')}'")

    return results


# ══════════════════════════════════════════════════════════════════════
# Phase 6.3 — BUG-017 Re-test (Intermittent Empty Response)
# ══════════════════════════════════════════════════════════════════════
def test_bug017():
    print("\n" + "=" * 70)
    print("PHASE 6.3 — BUG-017 Re-test (Intermittent Empty Response)")
    print("=" * 70)

    # Send the same input 5 times rapidly and check for empty responses
    test_input = "الحديقه جميله والأزهار متفتحه"
    empty_count = 0
    error_count = 0
    results = []

    for i in range(5):
        r = api_call("/api/analyze", test_input, timeout=30)
        corrected = r.get("corrected", "")
        suggestions = r.get("suggestions", [])
        status = r.get("status", "")
        warnings = r.get("warnings", {})

        is_empty = (corrected == test_input and len(suggestions) == 0)
        is_error = "error" in r and "status" not in r

        if is_empty:
            empty_count += 1
        if is_error:
            error_count += 1

        result = {
            "attempt": i + 1,
            "corrected": corrected,
            "suggestions": len(suggestions),
            "status": status,
            "warnings": warnings,
            "is_empty": is_empty,
            "is_error": is_error,
        }
        results.append(result)

        status_str = "❌ EMPTY" if is_empty else ("❌ ERROR" if is_error else "✅ OK")
        print(f"  Attempt {i+1}: {status_str} — suggestions={len(suggestions)}, status='{status}'")
        if warnings:
            print(f"    Warnings: {warnings}")
        if is_error:
            print(f"    Error: {r.get('error', '?')}")

    print(f"\n  Empty responses: {empty_count}/5")
    print(f"  Error responses: {error_count}/5")
    if empty_count > 0:
        print(f"  ⚠ BUG-017 may still be present!")
    else:
        print(f"  ✅ No empty responses detected")

    return {
        "empty_count": empty_count,
        "error_count": error_count,
        "results": results,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 6.4 — 187-word Long Input Regression
# ══════════════════════════════════════════════════════════════════════
def test_long_input_regression():
    print("\n" + "=" * 70)
    print("PHASE 6.4 — 187-word Long Input Regression")
    print("=" * 70)

    long_text = (
        "في ظل التطورات التكنولوجية المتسارعة التي يشهدها العالم اليوم أصبح من الضروري "
        "أن نواكب هذه التغييرات ونتكيف معها بشكل فعال حيث تلعب التكنولوجيا دورا محوريا "
        "في مختلف جوانب حياتنا اليومية بدءا من التعليم والصحة وصولا إلى الاقتصاد والسياسة "
        "ولقد أدى الذكاء الاصطناعي إلى تحولات جذرية في طريقة عمل المؤسسات والشركات حيث "
        "باتت الآلات قادرة على أداء مهام كانت حكرا على البشر مما يطرح تساؤلات عديدة حول "
        "مستقبل سوق العمل والوظائف التقليدية كما أن التحول الرقمي فرض على الحكومات والمجتمعات "
        "إعادة النظر في سياساتها التعليمية والاقتصادية لضمان مواكبة هذا التطور السريع وفي هذا "
        "السياق يبرز دور البحث العلمي والابتكار كعاملين أساسيين في دفع عجلة التنمية المستدامة "
        "وتحقيق الرفاهية للمجتمعات البشرية إذ لا يمكن لأي دولة أن تحقق تقدما حقيقيا دون "
        "الاستثمار في العقول البشرية وتوفير بيئة محفزة للإبداع والابتكار ومن هنا تأتي أهمية "
        "التعاون الدولي في مجال البحث العلمي وتبادل الخبرات والمعارف بين الدول المتقدمة والنامية "
        "على حد سواء لتحقيق التنمية الشاملة والمستدامة التي تعود بالنفع على جميع شعوب العالم"
    )
    print(f"  Input: {len(long_text)} chars, {len(long_text.split())} words")

    r = api_call("/api/analyze", long_text, timeout=120)
    status = r.get("status", "")
    corrected = r.get("corrected", "")
    suggestions = r.get("suggestions", [])
    warnings = r.get("warnings", {})
    timing = r.get("timing_ms", {})

    if "error" in r and "status" not in r:
        print(f"  ❌ ERROR: {r['error']}")
        result_status = "error"
    elif status == "partial":
        print(f"  ⚠ PARTIAL: some stages failed")
        print(f"    Warnings: {warnings}")
        result_status = "partial"
    elif status == "success":
        print(f"  ✅ SUCCESS")
        result_status = "success"
    else:
        print(f"  ⚠ UNKNOWN STATUS: '{status}'")
        result_status = "unknown"

    print(f"  Elapsed: {r.get('_elapsed_ms', '?')}ms")
    print(f"  Timing: {timing}")
    print(f"  Suggestions: {len(suggestions)}")
    print(f"  Corrected == Original: {corrected == long_text}")

    # Key check: response should NOT be silently empty
    is_silently_empty = (status == "success" and corrected == long_text and len(suggestions) == 0)
    if is_silently_empty:
        print(f"  ⚠ Silently empty! This is the BUG-032 behavior we're preventing.")
    else:
        print(f"  ✅ Response is either successful with results or properly flagged as partial/error")

    return {
        "input_chars": len(long_text),
        "input_words": len(long_text.split()),
        "status": result_status,
        "suggestions": len(suggestions),
        "warnings": warnings,
        "timing": timing,
        "elapsed_ms": r.get("_elapsed_ms"),
        "is_silently_empty": is_silently_empty,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 7.1 — BUG-018 Precise Tracing
# ══════════════════════════════════════════════════════════════════════
def test_bug018_tracing():
    print("\n" + "=" * 70)
    print("PHASE 7.1 — BUG-018 Precise Tracing (dropped ؛)")
    print("=" * 70)

    test_input = "قال المعلم للطلاب ادرسوا جيدا فالامتحان قريب"
    print(f"  Input: '{test_input}'")

    # Track A: Raw punctuation only
    a = api_call("/api/punctuation", test_input)
    a_out = a.get("corrected_text", test_input)
    has_semicolon_raw = "؛" in a_out
    print(f"\n  Raw punctuation output: '{a_out}'")
    print(f"  Has ؛: {has_semicolon_raw}")

    # Track B: Full pipeline
    b = api_call("/api/analyze", test_input)
    b_out = b.get("corrected", test_input)
    b_sugg = b.get("suggestions", [])
    has_semicolon_pipeline = "؛" in b_out
    print(f"\n  Pipeline output: '{b_out}'")
    print(f"  Has ؛: {has_semicolon_pipeline}")
    print(f"  Suggestions: {len(b_sugg)}")

    for s in b_sugg:
        print(f"    [{s.get('start')}:{s.get('end')}] {s.get('type')}: '{s.get('original','')}' → '{s.get('correction','')}'")

    # Determine drop cause
    if has_semicolon_raw and not has_semicolon_pipeline:
        # Raw produced it but pipeline dropped it
        punc_suggestions = [s for s in b_sugg if s.get('type') == 'punctuation']
        total_punc = len(punc_suggestions)
        if total_punc >= 3:
            cause = "MAX_PUNC_PATCHES_PER_RESPONSE cap (3 patches, ؛ was 4th+)"
        else:
            # Check if any grammar suggestion overlaps the ؛ position
            cause = "StageLocker or validate_punctuation_diff rejection"
        print(f"\n  DIAGNOSIS: ؛ was produced by raw model but dropped by pipeline")
        print(f"  Likely cause: {cause}")
    elif not has_semicolon_raw:
        cause = "Raw punctuation model did NOT produce ؛ at all"
        print(f"\n  DIAGNOSIS: {cause} — not a pipeline bug")
    else:
        cause = "؛ present in both raw and pipeline — BUG-018 not reproduced"
        print(f"\n  DIAGNOSIS: {cause}")

    return {
        "input": test_input,
        "raw_output": a_out,
        "pipeline_output": b_out,
        "has_semicolon_raw": has_semicolon_raw,
        "has_semicolon_pipeline": has_semicolon_pipeline,
        "diagnosis": cause,
        "pipeline_punc_count": len([s for s in b_sugg if s.get('type') == 'punctuation']),
    }


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("BAYAN — Gap-filling Live Tests\n")

    all_results["phase_1_3"] = test_category9_live()
    all_results["phase_2"] = test_rare_vocabulary()
    all_results["phase_3_2"] = test_word_splits()
    all_results["phase_5_5"] = test_dual_corrections()
    all_results["phase_6_3"] = test_bug017()
    all_results["phase_6_4"] = test_long_input_regression()
    all_results["phase_7_1"] = test_bug018_tracing()

    # Save all results
    output_path = os.path.join(os.path.dirname(__file__), 'gap_filling_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n\nAll results saved to {output_path}")
