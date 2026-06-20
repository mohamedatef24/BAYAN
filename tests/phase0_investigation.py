"""
Phase 0 — Investigation Script
Tests:
  0.1 — ان→أن in sentence context vs isolation
  0.3 — BUG-032 (long text) with detailed error capture
  0.4 — BUG-031 sentence (already resolved: الطلاب = plural → اللذين is wrong)
"""
import sys, os, json, time, requests

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 90

def api_call(endpoint, text):
    url = f"{API_BASE}{endpoint}"
    try:
        t0 = time.time()
        resp = requests.post(url, json={"text": text}, timeout=TIMEOUT)
        elapsed = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data['_elapsed_ms'] = elapsed
            return data
        return {"error": f"HTTP {resp.status_code}", "_elapsed_ms": elapsed}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

def test_0_1():
    """0.1 — Does spelling correct ان→أن in sentence context?"""
    print("=" * 70)
    print("PHASE 0.1 — ان→أن contradiction test")
    print("=" * 70)

    tests = [
        ("ان (isolation)", "ان"),
        ("ان الحياة جميلة (sentence)", "ان الحياة جميلة"),
        ("ان الذكاء مهم (sentence)", "ان الذكاء مهم"),
        ("قال ان الحق واضح (mid-sentence)", "قال ان الحق واضح"),
    ]

    results = []
    for label, text in tests:
        # Track A: raw spelling model
        a = api_call("/api/spelling", text)
        a_out = a.get("corrected_text", text)
        a_changed = a_out != text

        # Track B: full pipeline
        b = api_call("/api/analyze", text)
        b_out = b.get("corrected", text)
        b_sugg = b.get("suggestions", [])

        result = {
            "label": label, "input": text,
            "raw_spelling": a_out, "raw_changed": a_changed,
            "pipeline_corrected": b_out,
            "pipeline_suggestions": len(b_sugg),
        }
        results.append(result)

        print(f"\n  {label}:")
        print(f"    Input:      '{text}'")
        print(f"    Raw spell:  '{a_out}' (changed={a_changed})")
        print(f"    Pipeline:   '{b_out}' (suggestions={len(b_sugg)})")

        # Check if ان was corrected to أن or إن
        if 'أن' in a_out or 'إن' in a_out:
            print(f"    ✅ Raw spelling DID correct ان")
        elif a_changed:
            print(f"    ⚠ Raw spelling changed but NOT to أن/إن")
        else:
            print(f"    ❌ Raw spelling did NOT correct ان")

    # Verdict
    print("\n" + "-" * 50)
    isolation = results[0]
    sentences = results[1:]
    iso_fixed = 'أن' in isolation['raw_spelling'] or 'إن' in isolation['raw_spelling']
    sent_fixed = any('أن' in r['raw_spelling'] or 'إن' in r['raw_spelling'] for r in sentences)

    if iso_fixed and sent_fixed:
        verdict = "WORKS in both isolation AND sentence context"
    elif iso_fixed and not sent_fixed:
        verdict = "WORKS in isolation ONLY, FAILS in sentence context"
    elif not iso_fixed:
        verdict = "FAILS in both isolation and sentence context"
    else:
        verdict = "Inconsistent"

    print(f"  FINAL VERDICT: {verdict}")
    return {"verdict": verdict, "results": results}


def test_0_3():
    """0.3 — BUG-032: Long text (187 words / 1104 chars)"""
    print("\n" + "=" * 70)
    print("PHASE 0.3 — BUG-032 long text test")
    print("=" * 70)

    # 187-word Arabic text (from deep-dive report)
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
    print(f"  Input length: {len(long_text)} chars, {len(long_text.split())} words")

    # Test all three individual endpoints
    print("\n  Testing /api/spelling...")
    a_spell = api_call("/api/spelling", long_text)
    print(f"    Status: {'error' if 'error' in a_spell else 'OK'}")
    if 'error' in a_spell:
        print(f"    Error: {a_spell['error']}")
    else:
        print(f"    Elapsed: {a_spell.get('_elapsed_ms', '?')}ms")
        print(f"    Changed: {a_spell.get('corrected_text', '') != long_text}")

    print("\n  Testing /api/grammar...")
    a_gram = api_call("/api/grammar", long_text)
    print(f"    Status: {'error' if 'error' in a_gram else 'OK'}")
    if 'error' in a_gram:
        print(f"    Error: {a_gram['error']}")
    else:
        print(f"    Elapsed: {a_gram.get('_elapsed_ms', '?')}ms")
        print(f"    Changed: {a_gram.get('corrected_text', '') != long_text}")

    print("\n  Testing /api/punctuation...")
    a_punc = api_call("/api/punctuation", long_text)
    print(f"    Status: {'error' if 'error' in a_punc else 'OK'}")
    if 'error' in a_punc:
        print(f"    Error: {a_punc['error']}")
    else:
        print(f"    Elapsed: {a_punc.get('_elapsed_ms', '?')}ms")
        print(f"    Changed: {a_punc.get('corrected_text', '') != long_text}")

    print("\n  Testing /api/analyze (full pipeline)...")
    b = api_call("/api/analyze", long_text)
    print(f"    Status: {'error' if 'error' in b and 'status' not in b else b.get('status', '?')}")
    if 'error' in b and 'status' not in b:
        print(f"    Error: {b['error']}")
    else:
        print(f"    Elapsed: {b.get('_elapsed_ms', '?')}ms")
        print(f"    Suggestions: {len(b.get('suggestions', []))}")
        print(f"    Timing: {b.get('timing_ms', {})}")
        if b.get('corrected') == long_text:
            print(f"    ⚠ corrected == original (no changes or silent failure?)")

    return {
        "input_chars": len(long_text),
        "input_words": len(long_text.split()),
        "spelling": {"error": a_spell.get("error"), "elapsed": a_spell.get("_elapsed_ms")},
        "grammar": {"error": a_gram.get("error"), "elapsed": a_gram.get("_elapsed_ms")},
        "punctuation": {"error": a_punc.get("error"), "elapsed": a_punc.get("_elapsed_ms")},
        "pipeline": {
            "error": b.get("error"),
            "status": b.get("status"),
            "suggestions": len(b.get("suggestions", [])),
            "timing": b.get("timing_ms", {}),
            "elapsed": b.get("_elapsed_ms"),
        }
    }


def test_0_4():
    """0.4 — BUG-031: اللذين vs الذين"""
    print("\n" + "=" * 70)
    print("PHASE 0.4 — BUG-031 (اللذين vs الذين)")
    print("=" * 70)

    sentence = "الطلاب اللذين اجتهدو في دراستهم حققو نتائج ممتازه في الأمتحانات الصعبه"
    print(f"  Test sentence: '{sentence}'")
    print(f"  Subject: الطلاب (PLURAL, not dual)")
    print(f"  Therefore: اللذين (dual) is WRONG, الذين (plural) is CORRECT")
    print(f"  Verdict: BUG-031 IS a real bug — grammar should correct اللذين→الذين")

    # Test it
    a_gram = api_call("/api/grammar", sentence)
    a_out = a_gram.get("corrected_text", sentence)
    print(f"\n  Grammar model output: '{a_out}'")
    if 'الذين' in a_out and 'اللذين' not in a_out:
        print(f"  ✅ Grammar DID correct اللذين→الذين")
        bug_status = "fixed_by_model"
    elif 'اللذين' in a_out:
        print(f"  ❌ Grammar did NOT correct اللذين (left as dual)")
        bug_status = "still_broken"
    else:
        print(f"  ⚠ Unexpected output")
        bug_status = "unclear"

    return {
        "sentence": sentence,
        "subject": "الطلاب (PLURAL)",
        "correct_form": "الذين (plural)",
        "is_real_bug": True,
        "grammar_output": a_out,
        "bug_status": bug_status,
    }


if __name__ == "__main__":
    print("BAYAN Phase 0 — Investigation\n")

    all_results = {}

    all_results["phase_0_1"] = test_0_1()
    all_results["phase_0_3"] = test_0_3()
    all_results["phase_0_4"] = test_0_4()

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), 'phase0_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {output_path}")
