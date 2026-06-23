"""
BAYAN Round 2 — Live API Tests
Covers: A1 (BUG-032 exact input), A2 (Appendix E FP rate), B1 (31 prefix cases),
        B4 (300/301 boundary), B5 (shadda), B7 (brackets)
"""
import sys, os, json, time, requests
from datetime import datetime, timezone

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 120

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

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

results = {"timestamp": datetime.now(timezone.utc).isoformat()}

# ═══════════════════════════════════════════════════════════════
# A1: BUG-032 — Exact 1104-char/187-word Input Re-test
# ═══════════════════════════════════════════════════════════════
log("=" * 70)
log("A1: BUG-032 — Exact Original Input Re-test")
log("=" * 70)

# Exact original text from phase0_investigation.py L100-112
BUG032_TEXT = (
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

log(f"  Input: {len(BUG032_TEXT)} chars, {len(BUG032_TEXT.split())} words")

# Test 1: Full pipeline
log("  Running /api/analyze...")
a1_pipeline = api_call("/api/analyze", BUG032_TEXT)
log(f"  Pipeline: status={a1_pipeline.get('status', 'N/A')}, "
    f"suggestions={len(a1_pipeline.get('suggestions', []))}, "
    f"elapsed={a1_pipeline.get('_elapsed_ms', 'N/A')}ms")
if 'timing_ms' in a1_pipeline:
    log(f"  Timing: {a1_pipeline['timing_ms']}")
if 'warnings' in a1_pipeline:
    log(f"  Warnings: {a1_pipeline['warnings']}")

# Test 2: Individual endpoints for timing reconciliation
log("  Running /api/spelling (expect timeout or skip)...")
a1_spell = api_call("/api/spelling", BUG032_TEXT, timeout=120)
log(f"  Spelling: elapsed={a1_spell.get('_elapsed_ms', 'N/A')}ms, "
    f"error={a1_spell.get('error', 'none')}")

log("  Running /api/grammar...")
a1_gram = api_call("/api/grammar", BUG032_TEXT, timeout=120)
log(f"  Grammar: elapsed={a1_gram.get('_elapsed_ms', 'N/A')}ms, "
    f"changed={a1_gram.get('corrected_text', BUG032_TEXT) != BUG032_TEXT}")

log("  Running /api/punctuation...")
a1_punc = api_call("/api/punctuation", BUG032_TEXT, timeout=120)
log(f"  Punctuation: elapsed={a1_punc.get('_elapsed_ms', 'N/A')}ms, "
    f"changed={a1_punc.get('corrected_text', BUG032_TEXT) != BUG032_TEXT}")

results['a1_bug032'] = {
    'input_chars': len(BUG032_TEXT),
    'input_words': len(BUG032_TEXT.split()),
    'pipeline': {
        'status': a1_pipeline.get('status'),
        'suggestions': len(a1_pipeline.get('suggestions', [])),
        'elapsed_ms': a1_pipeline.get('_elapsed_ms'),
        'timing_ms': a1_pipeline.get('timing_ms'),
        'warnings': a1_pipeline.get('warnings'),
    },
    'spelling': {'elapsed_ms': a1_spell.get('_elapsed_ms'), 'error': a1_spell.get('error')},
    'grammar': {'elapsed_ms': a1_gram.get('_elapsed_ms')},
    'punctuation': {'elapsed_ms': a1_punc.get('_elapsed_ms')},
}

# ═══════════════════════════════════════════════════════════════
# A2: Appendix E FP Rate — EXACT Original Sentences
# ═══════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("A2: Appendix E — Exact Original Sentences FP Rate")
log("=" * 70)

# EXACT sentences from deep_dive_gaps.py L260-271
APPENDIX_E_ORIGINAL = [
    {"id": "R-01", "sentence": "استوقفني المشهد فتأملته مليا", "domain": "literary"},
    {"id": "R-02", "sentence": "تستأثر القوى العظمى بالنفوذ الدولي", "domain": "political"},
    {"id": "R-03", "sentence": "استقطب المؤتمر ثلة من العلماء الأفذاذ", "domain": "formal"},
    {"id": "R-04", "sentence": "يتسنى للمرء أن يستشف الحقيقة من بين السطور", "domain": "literary_verb"},
    {"id": "R-05", "sentence": "ألقى المحاضر خطبة عصماء استحوذت على إعجاب الحاضرين", "domain": "oratory"},
    {"id": "R-06", "sentence": "تمخض الاجتماع عن قرارات مصيرية", "domain": "formal_verb"},
    {"id": "R-07", "sentence": "أرهقته المسغبة فاستكان للقدر", "domain": "classical"},
    {"id": "R-08", "sentence": "نستشرف آفاق المستقبل بثقة واقتدار", "domain": "formal_speech"},
    {"id": "R-09", "sentence": "اعتراه القلق فتملكه الأرق", "domain": "literary_psych"},
    {"id": "R-10", "sentence": "استأنف العمل بعد فترة من التقاعس", "domain": "formal_verb"},
]

# Constructed sentences from gap_filling_tests.py (for comparison)
CONSTRUCTED_SENTENCES = [
    {"id": "R-01c", "sentence": "المدينة العصماء تحتضن آلاف السكان", "word": "العصماء"},
    {"id": "R-02c", "sentence": "يستشف الباحث نتائج الدراسة بعناية", "word": "يستشف"},
    {"id": "R-03c", "sentence": "أرهقته المسغبة والعطش الشديد", "word": "المسغبة"},
    {"id": "R-04c", "sentence": "التقاعس عن العمل يؤدي إلى الفشل", "word": "التقاعس"},
    {"id": "R-05c", "sentence": "استئثار السلطة يهدد الديمقراطية", "word": "استئثار"},
    {"id": "R-06c", "sentence": "تبجيل العلماء واجب على المجتمع", "word": "تبجيل"},
    {"id": "R-07c", "sentence": "الرجل الدمث يحبه الجميع", "word": "الدمث"},
    {"id": "R-08c", "sentence": "استقصاء الحقائق مهم في الصحافة", "word": "استقصاء"},
    {"id": "R-09c", "sentence": "لا يجوز التواني في طلب العلم", "word": "التواني"},
    {"id": "R-10c", "sentence": "كتاب المستطرف من أمهات الكتب العربية", "word": "المستطرف"},
]

def test_fp_set(name, items):
    fp_count = 0
    item_results = []
    for item in items:
        text = item["sentence"]
        r = api_call("/api/analyze", text)
        corrected = r.get("corrected", text)
        suggestions = r.get("suggestions", [])
        changed = corrected != text
        if changed:
            fp_count += 1
        result = {
            "id": item["id"], "input": text, "corrected": corrected,
            "changed": changed, "suggestion_count": len(suggestions),
        }
        item_results.append(result)
        status = "❌ CHANGED" if changed else "✅ PRESERVED"
        log(f"  {item['id']}: {status}")
        if changed:
            log(f"    Input:     '{text[:60]}'")
            log(f"    Corrected: '{corrected[:60]}'")
            for s in suggestions:
                log(f"      [{s.get('type','')}] '{s.get('original','')}' → '{s.get('correction','')}'")
    log(f"\n  {name} FP rate: {fp_count}/{len(items)} = {fp_count*100//len(items)}%")
    return {"fp_count": fp_count, "total": len(items), "fp_rate": f"{fp_count*100//len(items)}%", "results": item_results}

log("\n  --- Original Appendix E sentences ---")
a2_original = test_fp_set("Original Appendix E", APPENDIX_E_ORIGINAL)

log("\n  --- Constructed sentences (comparison) ---")
a2_constructed = test_fp_set("Constructed", CONSTRUCTED_SENTENCES)

results['a2_fp_rate'] = {
    'original_appendix_e': a2_original,
    'constructed_sentences': a2_constructed,
}

# ═══════════════════════════════════════════════════════════════
# B1: All 31 Prefix/Clitic Cases through Pipeline
# ═══════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("B1: All 31 Prefix/Clitic Cases through Pipeline")
log("=" * 70)

CAT8_ROOTS = ['مدرسة', 'شمس', 'أمة', 'نافذة', 'علم', 'اقتصاد']
CAT8_PREFIXES = [("bare", ""), ("wa", "و"), ("ba", "ب"), ("la", "ل"), ("ka", "ك")]

b1_total = 0
b1_blocked = 0
b1_leaked = 0
b1_unchanged = 0
b1_results = []

for root in CAT8_ROOTS:
    for pfx_name, pfx in CAT8_PREFIXES:
        word = pfx + root
        # Put word in a minimal sentence context
        sentence = f"{word} مهم جدا"
        r = api_call("/api/analyze", sentence)
        corrected = r.get("corrected", sentence)
        suggestions = r.get("suggestions", [])

        # Check if the word was changed
        word_in_corrected = word in corrected
        word_changed = not word_in_corrected

        # Find suggestions targeting this word
        targeting = [s for s in suggestions if s.get("original", "").strip() == word
                     or word in s.get("original", "")]

        b1_total += 1
        if not word_changed and not targeting:
            b1_unchanged += 1
            status = "✅ PRESERVED"
        elif targeting and not word_changed:
            # Suggestion exists but wasn't applied (dampened?)
            conf = targeting[0].get('confidence', '?')
            if conf and float(str(conf)) < 0.9:
                b1_blocked += 1
                status = f"✅ DAMPENED (conf={conf})"
            else:
                b1_leaked += 1
                status = f"⚠ LEAKED (conf={conf})"
        elif word_changed:
            b1_leaked += 1
            status = "❌ CHANGED"
        else:
            b1_unchanged += 1
            status = "✅ OK"

        result = {
            "word": word, "root": root, "prefix": pfx_name,
            "input": sentence, "corrected": corrected,
            "word_preserved": word_in_corrected,
            "targeting_suggestions": len(targeting),
            "status": status,
        }
        b1_results.append(result)
        log(f"  {word:12s} ({pfx_name:4s}+{root}): {status}")
        if word_changed:
            log(f"    Input:     '{sentence}'")
            log(f"    Corrected: '{corrected}'")

# BUG-021: ولذالك (case 31)
sentence_31 = "ولذالك يجب الاهتمام"
r31 = api_call("/api/analyze", sentence_31)
corrected_31 = r31.get("corrected", sentence_31)
word_31 = "ولذالك"
word_31_ok = "ولذلك" in corrected_31
bad_split_31 = "ولذا ذلك" in corrected_31
b1_total += 1

if word_31_ok:
    status_31 = "✅ CORRECTED (ولذالك→ولذلك)"
    b1_blocked += 1
elif bad_split_31:
    status_31 = "❌ BAD SPLIT (ولذا ذلك)"
    b1_leaked += 1
elif word_31 in corrected_31:
    status_31 = "⚠ UNCHANGED (misspelling preserved)"
    b1_unchanged += 1
else:
    status_31 = f"⚠ OTHER: '{corrected_31}'"
    b1_leaked += 1

b1_results.append({"word": word_31, "input": sentence_31, "corrected": corrected_31, "status": status_31})
log(f"  {'ولذالك':12s} (BUG-021): {status_31}")

log(f"\n  Total: {b1_total}, Preserved: {b1_unchanged}, Blocked/Dampened: {b1_blocked}, Leaked: {b1_leaked}")

results['b1_prefix'] = {
    'total': b1_total, 'unchanged': b1_unchanged,
    'blocked': b1_blocked, 'leaked': b1_leaked,
    'results': b1_results,
}

# ═══════════════════════════════════════════════════════════════
# B4: 300/301 Boundary + Repetitive Text
# ═══════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("B4: 300/301 Boundary + Repetitive Text")
log("=" * 70)

# Test 1: Exact boundary (300 chars vs 301 chars)
base = "ذهب الولد الى المدرسه وقابل المعلمه "  # ~37 chars with errors
text_300 = (base * 10)[:300]
text_301 = (base * 10)[:301]
log(f"  300-char text: {len(text_300)} chars")
log(f"  301-char text: {len(text_301)} chars")

r300 = api_call("/api/analyze", text_300)
r301 = api_call("/api/analyze", text_301)

s300 = r300.get("suggestions", [])
s301 = r301.get("suggestions", [])
s300_types = {s.get('type') for s in s300}
s301_types = {s.get('type') for s in s301}

log(f"  300 chars: {len(s300)} suggestions, types={s300_types}")
log(f"  301 chars: {len(s301)} suggestions, types={s301_types}")

# Check if spelling suggestions differ
s300_spell = [s for s in s300 if s.get('type') == 'spelling']
s301_spell = [s for s in s301 if s.get('type') == 'spelling']
log(f"  300 chars spelling: {len(s300_spell)} suggestions")
log(f"  301 chars spelling: {len(s301_spell)} suggestions")

if len(s300_spell) > 0 and len(s301_spell) == 0:
    log(f"  ✅ AraSpell skip confirmed: spelling runs at 300, skipped at 301")
    boundary_explanation = "Character count: <=300 runs AraSpell, >300 skips it"
elif len(s300_spell) == len(s301_spell):
    log(f"  ⚠ Same spelling count at both — boundary may not work as expected")
    boundary_explanation = "Boundary NOT working as expected — same results at 300 and 301"
else:
    log(f"  ⚠ Different spelling counts but not the expected pattern")
    boundary_explanation = f"Partial: 300={len(s300_spell)} spell, 301={len(s301_spell)} spell"

# Test 2: Repetitive text (مرحبا × 100)
repetitive = "مرحبا " * 100
log(f"\n  Repetitive text: '{repetitive[:30]}...' ({len(repetitive)} chars)")
r_rep = api_call("/api/analyze", repetitive)
rep_corrected = r_rep.get("corrected", "")
rep_sugg = r_rep.get("suggestions", [])
rep_status = r_rep.get("status", "")

# Check for garbling
has_garble = any(c in rep_corrected for c in 'صطن') and 'مرحبا' not in rep_corrected[:20]
log(f"  Status: {rep_status}, Suggestions: {len(rep_sugg)}")
log(f"  Corrected starts with: '{rep_corrected[:60]}...'")
if has_garble:
    log(f"  ❌ GARBLED output detected")
else:
    log(f"  ✅ No obvious garbling")

results['b4_boundary'] = {
    'boundary_explanation': boundary_explanation,
    'test_300': {'chars': 300, 'suggestions': len(s300), 'spelling': len(s300_spell)},
    'test_301': {'chars': 301, 'suggestions': len(s301), 'spelling': len(s301_spell)},
    'repetitive': {
        'input_chars': len(repetitive),
        'status': rep_status,
        'suggestions': len(rep_sugg),
        'garbled': has_garble,
        'corrected_preview': rep_corrected[:100],
    },
}

# ═══════════════════════════════════════════════════════════════
# B5: Shadda Duplication Verification
# ═══════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("B5: Shadda Duplication — Sentence Context")
log("=" * 70)

shadda_tests = [
    {"input": "إنّ العلم نور", "check": "إنّ", "desc": "إنّ in sentence"},
    {"input": "علمت أنّ الامتحان صعب", "check": "أنّ", "desc": "أنّ in sentence"},
    {"input": "إنّ", "check": "إنّ", "desc": "إنّ in isolation"},
    {"input": "أنّ", "check": "أنّ", "desc": "أنّ in isolation"},
]

b5_results = []
for t in shadda_tests:
    r = api_call("/api/spelling", t["input"])
    out = r.get("corrected_text", t["input"])
    duplicated = out.count("إن") >= 2 or out.count("أن") >= 2
    changed = out != t["input"]
    status = "❌ DUPLICATED" if duplicated else ("⚠ CHANGED" if changed else "✅ OK")
    b5_results.append({"input": t["input"], "output": out, "status": status})
    log(f"  {t['desc']}: '{t['input']}' → '{out}' {status}")

results['b5_shadda'] = b5_results

# ═══════════════════════════════════════════════════════════════
# B7: Unbalanced Brackets
# ═══════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("B7: Unbalanced Brackets — E6")
log("=" * 70)

bracket_tests = [
    "(([{هذا النص}]))",
    "({هذا النص})",
    "(هذا النص)",
    "[هذا النص]",
]

b7_results = []
for text in bracket_tests:
    r = api_call("/api/analyze", text)
    corrected = r.get("corrected", text)
    suggestions = r.get("suggestions", [])

    # Count bracket balance
    def bracket_balance(s):
        opens = sum(1 for c in s if c in '([{')
        closes = sum(1 for c in s if c in ')]}')
        return opens, closes, opens == closes

    in_o, in_c, in_bal = bracket_balance(text)
    out_o, out_c, out_bal = bracket_balance(corrected)

    result = {
        "input": text, "corrected": corrected,
        "input_balanced": in_bal, "output_balanced": out_bal,
        "suggestions": len(suggestions),
    }
    b7_results.append(result)

    if not out_bal and in_bal:
        status = "❌ BRACKETS UNBALANCED"
    elif out_bal:
        status = "✅ BRACKETS OK"
    elif not in_bal and not out_bal:
        status = "⚠ BOTH UNBALANCED"
    else:
        status = "✅ FIXED"

    log(f"  '{text}' → '{corrected}' {status}")
    log(f"    Input: {in_o} opens, {in_c} closes, balanced={in_bal}")
    log(f"    Output: {out_o} opens, {out_c} closes, balanced={out_bal}")

results['b7_brackets'] = b7_results

# ═══════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════
output_path = os.path.join(os.path.dirname(__file__), 'round2_results.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
log(f"\nAll results saved to {output_path}")
