"""
Gap-filler tests for items explicitly requested in the prompt but not yet covered:
1. 200+ word cumulative drift test (Cat 10)
2. Lower-priority-wins limitation (Cat 4)
3. Systematic dropped patch logging (Cat 3)
4. Rare/literary vocabulary overcorrection (Cat 2)
"""
import sys, os, json, time, requests
from datetime import datetime, timezone

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
                return data
            else:
                if attempt < retries:
                    time.sleep(2)
                    continue
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}", "_elapsed_ms": elapsed}
        except Exception as e:
            return {"error": str(e)}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

results = {"timestamp": datetime.now(timezone.utc).isoformat()}

# ═══════════════════════════════════════════════════════════════
# GAP 1: 200+ word cumulative drift test (Cat 10)
# ═══════════════════════════════════════════════════════════════
log("=== GAP 1: 200+ word cumulative drift test ===")

# Build a 200+ word paragraph with deliberate errors throughout
long_para = (
    "كانت الفتيات يلعبون في الحديقه الجميله وفجأه سقطت احداهن وبدءت تبكي بشده "
    "ذهب الولد الى المدرسه وقابل المعلمه واخذ الكتاب وبدأ يقرأ بتركيز شديد "
    "ان الذكاء الاصطناعي يلعب دورا هاما في تطوير التكنولوجيا الحديثه ولذالك يجب الاهتمام بة "
    "هذة المدينه جميله جدا ومناخها معتدل طوال العام وسكانها طيبون ومحبون للخير "
    "الطلاب الذين اجتهدو في دراستهم حققو نتائج ممتازه في الامتحانات النهائيه "
    "سافر محمد إلى دبي للعمل في شركة جوجل وقابل أصدقاءه القدامى هناك "
    "يستخدم الذكاء الاصطناعي تقنيات التعلم العميق في معالجة البيانات الضخمة والتحليل "
    "القاهرة عاصمة جمهورية مصر العربية وأكبر مدنها وتقع على ضفاف نهر النيل العظيم "
    "تتراوح درجات الحرارة بين خمس وعشرين وثلاثين درجة مئوية في فصل الصيف الحار "
    "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين إياك نعبد وإياك نستعين "
    "بسم الله الرحمن الرحيم نبدأ هذة المحاضره عن اهمية التعليم في حياة الانسان "
    "يحب الأطفال اللعب في الحديقة وركوب الدراجات والجري بين الأشجار والزهور الجميلة "
    "إن العلم نور والجهل ظلام فاحرصوا على طلب العلم من المهد إلى اللحد "
    "كان الرجل يمشي في الشارع وفجأه رأى صديقه القديم فسلم عليه وتحدثا طويلا "
    "المعلم الذي يحب عمله يجتهد في تعليم طلابه ويحرص على نجاحهم في الحياه "
)

word_count = len(long_para.split())
char_count = len(long_para)
log(f"  Input: {word_count} words, {char_count} chars")

# Track A: each model on the full long text
log("  Running Track A (each model independently on original)...")
a_spell = api_call("/api/spelling", long_para)
a_gram = api_call("/api/grammar", long_para)
a_punc = api_call("/api/punctuation", long_para)

# Track B: full pipeline
log("  Running Track B (full pipeline)...")
b = api_call("/api/analyze", long_para)

sugg = b.get("suggestions", [])
mid_char = char_count // 2

# Verify ALL coordinates
coord_mismatches = []
for s in sugg:
    start, end = s.get('start', 0), s.get('end', 0)
    expected_text = long_para[start:end]
    actual_text = s.get('original', '')
    if expected_text != actual_text:
        coord_mismatches.append({
            "start": start, "end": end,
            "expected": expected_text,
            "actual": actual_text,
            "correction": s.get('correction', ''),
            "type": s.get('type', ''),
        })

back_half = [s for s in sugg if s.get('start', 0) >= mid_char]
front_half = [s for s in sugg if s.get('start', 0) < mid_char]

# Log every suggestion with its verified coordinate
log(f"  Total: {len(sugg)} suggestions, {len(coord_mismatches)} coordinate mismatches")
log(f"  Front half ({mid_char} chars): {len(front_half)} suggestions")
log(f"  Back half: {len(back_half)} suggestions")
for s in sugg:
    st, en = s.get('start',0), s.get('end',0)
    in_back = "BACK" if st >= mid_char else "FRONT"
    verified = "✓" if long_para[st:en] == s.get('original','') else "✗ MISMATCH"
    log(f"    [{in_back}] [{st}:{en}] '{s.get('original','')}' → '{s.get('correction','')}' ({s.get('type','')}) {verified}")

for m in coord_mismatches:
    log(f"    MISMATCH: [{m['start']}:{m['end']}] expected='{m['expected']}' actual='{m['actual']}'")

results['gap1_drift'] = {
    "word_count": word_count, "char_count": char_count,
    "total_suggestions": len(sugg),
    "front_half": len(front_half), "back_half": len(back_half),
    "coordinate_mismatches": coord_mismatches,
    "a_spelling_changed": a_spell.get("corrected_text","") != long_para,
    "a_grammar_changed": a_gram.get("corrected_text","") != long_para,
    "a_punc_changed": a_punc.get("corrected_text","") != long_para,
    "suggestions": sugg,
}

# ═══════════════════════════════════════════════════════════════
# GAP 2: Lower-priority-wins limitation doc (Cat 4)
# ═══════════════════════════════════════════════════════════════
log("\n=== GAP 2: Lower-priority stage was more important (Cat 4) ===")

# Construct case: spelling corrects اجتهدو→اجتهدوا (correct, priority 1)
# but grammar might also touch it with a different correction (priority 3)
# Grammar WINS because higher priority. But what if grammar is wrong here?
gap2_tests = [
    {
        "id": "G2-01",
        "input": "الطلاب اجتهدو في الامتحان",
        "desc": "اجتهدو — spelling should add ا, grammar may do different fix. Grammar wins (priority 3 > 1)",
    },
    {
        "id": "G2-02",
        "input": "البنات ذهبو الى البيت",
        "desc": "ذهبو — spelling could give ذهبوا, grammar could give ذهبن (fem). Grammar wins.",
    },
    {
        "id": "G2-03",
        "input": "وفجأه سقطت الكتب",
        "desc": "وفجأه — spelling may fix ه→ة; punctuation may want comma after it. Overlap?",
    },
]

for test in gap2_tests:
    log(f"  {test['id']}: {test['input']}")
    a_sp = api_call("/api/spelling", test['input'])
    a_gr = api_call("/api/grammar", test['input'])
    a_pu = api_call("/api/punctuation", test['input'])
    b = api_call("/api/analyze", test['input'])

    a_sp_out = a_sp.get("corrected_text", test['input'])
    a_gr_out = a_gr.get("corrected_text", test['input'])
    a_pu_out = a_pu.get("corrected_text", test['input'])

    log(f"    A_spell: {a_sp_out}")
    log(f"    A_gram:  {a_gr_out}")
    log(f"    A_punc:  {a_pu_out}")
    log(f"    B_final: {b.get('corrected','')}")
    log(f"    B_sugg:  {len(b.get('suggestions',[]))}")

    # Which stage's correction won for each word?
    b_sugg = b.get('suggestions', [])
    for s in b_sugg:
        log(f"      [{s.get('type','')}] [{s.get('start',0)}:{s.get('end',0)}] '{s.get('original','')}' → '{s.get('correction','')}'")

    test['a_spelling'] = a_sp_out
    test['a_grammar'] = a_gr_out
    test['a_punctuation'] = a_pu_out
    test['b_corrected'] = b.get('corrected', '')
    test['b_suggestions'] = b_sugg

results['gap2_priority'] = gap2_tests

# ═══════════════════════════════════════════════════════════════
# GAP 3: Systematic dropped patch logging (Cat 3)
# ═══════════════════════════════════════════════════════════════
log("\n=== GAP 3: Systematic dropped patch comparison (Cat 3) ===")

# For each test: run all 3 models independently, count expected patches,
# compare with actual Track B patches. Any patch Track A produces but
# Track B doesn't = dropped patch.
gap3_tests = [
    "كانت الفتيات يلعبون في الحديقه وفجأه سقطت احداهن وبدءت تبكي بشده",
    "ان الذكاء الاصطناعي يلعب دورا هاما ولذالك يجب الاهتمام بة",
    "هذة المدينه جميله جدا ومناخها معتدل طوال العام",
    "ذهب الولد الى المكتبه وقرا كتاب مفيد",
    "الطلاب الذين اجتهدو في دراستهم حققو نتائج ممتازه في الامتحانات",
]

for i, text in enumerate(gap3_tests):
    log(f"  Test {i+1}: {text[:50]}...")
    a_sp = api_call("/api/spelling", text)
    a_gr = api_call("/api/grammar", text)
    a_pu = api_call("/api/punctuation", text)
    b = api_call("/api/analyze", text)

    a_sp_out = a_sp.get("corrected_text", text)
    a_gr_out = a_gr.get("corrected_text", text)
    a_pu_out = a_pu.get("corrected_text", text)

    # Find word-level changes from each model
    def word_diffs(orig, corrected):
        o_words = orig.split()
        c_words = corrected.split()
        diffs = []
        for j, (ow, cw) in enumerate(zip(o_words, c_words)):
            if ow != cw:
                diffs.append({"word_idx": j, "original": ow, "corrected": cw})
        return diffs

    sp_diffs = word_diffs(text, a_sp_out)
    gr_diffs = word_diffs(text, a_gr_out)
    pu_diffs = word_diffs(text, a_pu_out)

    b_sugg = b.get('suggestions', [])
    b_corrections = set()
    for s in b_sugg:
        b_corrections.add(s.get('original', ''))

    # Track A produced these corrections; check which survived to Track B
    dropped_spell = [d for d in sp_diffs if d['original'] not in b_corrections and d['corrected'] != d['original']]
    dropped_gram = [d for d in gr_diffs if d['original'] not in b_corrections and d['corrected'] != d['original']]
    dropped_punc = [d for d in pu_diffs if d['original'] not in b_corrections and d['corrected'] != d['original']]

    log(f"    Track A changes: spell={len(sp_diffs)}, gram={len(gr_diffs)}, punc={len(pu_diffs)}")
    log(f"    Track B suggestions: {len(b_sugg)}")
    log(f"    Dropped: spell={len(dropped_spell)}, gram={len(dropped_gram)}, punc={len(dropped_punc)}")

    for d in dropped_spell:
        log(f"      DROPPED SPELL: '{d['original']}' → '{d['corrected']}' (reason: likely filter blocked)")
    for d in dropped_gram:
        log(f"      DROPPED GRAM: '{d['original']}' → '{d['corrected']}' (reason: likely StageLocker)")
    for d in dropped_punc:
        log(f"      DROPPED PUNC: '{d['original']}' → '{d['corrected']}' (reason: likely lock/cap/safety)")

results[f'gap3_dropped'] = {
    "tests": [
        {
            "input": text,
            "a_spell_diffs": word_diffs(text, api_call("/api/spelling", text).get("corrected_text", text)) if False else sp_diffs,
            "a_gram_diffs": gr_diffs,
            "a_punc_diffs": pu_diffs,
            "b_suggestion_count": len(b_sugg),
            "dropped_spell": dropped_spell,
            "dropped_gram": dropped_gram,
            "dropped_punc": dropped_punc,
        }
        for text, sp_diffs, gr_diffs, pu_diffs, b_sugg in [(text, sp_diffs, gr_diffs, pu_diffs, b_sugg)]
    ]
}

# ═══════════════════════════════════════════════════════════════
# GAP 4: Rare/literary vocabulary (Cat 2)
# ═══════════════════════════════════════════════════════════════
log("\n=== GAP 4: Rare/literary vocabulary overcorrection (Cat 2) ===")

rare_tests = [
    {"id": "R-01", "input": "استوقفني المشهد فتأملته مليا", "domain": "literary"},
    {"id": "R-02", "input": "تستأثر القوى العظمى بالنفوذ الدولي", "domain": "political_literary"},
    {"id": "R-03", "input": "استقطب المؤتمر ثلة من العلماء الأفذاذ", "domain": "formal_rare"},
    {"id": "R-04", "input": "يتسنى للمرء أن يستشف الحقيقة من بين السطور", "domain": "literary_verb"},
    {"id": "R-05", "input": "ألقى المحاضر خطبة عصماء استحوذت على إعجاب الحاضرين", "domain": "oratory"},
    {"id": "R-06", "input": "تمخض الاجتماع عن قرارات مصيرية", "domain": "formal_verb"},
    {"id": "R-07", "input": "أرهقته المسغبة فاستكان للقدر", "domain": "classical"},
    {"id": "R-08", "input": "نستشرف آفاق المستقبل بثقة واقتدار", "domain": "formal_speech"},
    {"id": "R-09", "input": "اعتراه القلق فتملكه الأرق", "domain": "literary_psych"},
    {"id": "R-10", "input": "استأنف العمل بعد فترة من التقاعس", "domain": "formal_verb"},
]

fp_count = 0
for test in rare_tests:
    a = api_call("/api/spelling", test['input'])
    a_out = a.get("corrected_text", test['input'])
    changed = a_out != test['input']
    if changed:
        fp_count += 1
        log(f"  ⚠ {test['id']}: '{test['input'][:40]}...' → '{a_out[:40]}...' [{test['domain']}]")
    else:
        log(f"  ✓ {test['id']}: no change [{test['domain']}]")
    test['output'] = a_out
    test['changed'] = changed

log(f"  Rare/literary FP rate: {fp_count}/{len(rare_tests)} ({fp_count*100//len(rare_tests)}%)")
results['gap4_rare'] = {"tests": rare_tests, "fp_count": fp_count, "total": len(rare_tests)}

# ═══════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════
output_path = os.path.join(os.path.dirname(__file__), 'deep_dive_gaps.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
log(f"\nSaved to {output_path}")
