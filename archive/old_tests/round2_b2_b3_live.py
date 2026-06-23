"""
Round 2 — B2 Live API Test
Tests BUG-006/009/010/013 through the DEPLOYED pipeline to verify
whether the existing mechanism catches common-word substitutions.
"""
import requests, json, time, os

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 60

def api_call(endpoint, text):
    try:
        t0 = time.time()
        resp = requests.post(f"{API_BASE}{endpoint}", json={"text": text}, timeout=TIMEOUT)
        elapsed = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data['_elapsed_ms'] = elapsed
            return data
        return {"error": f"HTTP {resp.status_code}", "_elapsed_ms": elapsed}
    except Exception as e:
        return {"error": str(e)}

print("=" * 70)
print("B2 LIVE TEST: Common-word substitution via /api/analyze")
print("=" * 70)

# Test each BUG in sentence context
tests = [
    {"id": "BUG-006", "sentence": "هذا اهم شيء في الحياة", "word": "اهم",
     "bad_correction": "مهم", "concern": "اهم must NOT become مهم"},
    {"id": "BUG-009", "sentence": "قرأ الطالب الكتاب", "word": "قرأ",
     "bad_correction": "قرا", "concern": "قرأ must NOT become قرا"},
    {"id": "BUG-010", "sentence": "مشى الرجل إلى البيت", "word": "مشى",
     "bad_correction": "مضى", "concern": "مشى must NOT become مضى"},
    {"id": "BUG-013", "sentence": "وقع في خطأ كبير", "word": "خطأ",
     "bad_correction": "خطا", "concern": "خطأ must NOT become خطا"},
]

results = []
for t in tests:
    r = api_call("/api/analyze", t["sentence"])
    corrected = r.get("corrected", t["sentence"])
    suggestions = r.get("suggestions", [])
    
    # Check if the target word was changed
    word_present = t["word"] in corrected
    bad_present = t["bad_correction"] in corrected and t["bad_correction"] not in t["sentence"]
    
    # Find suggestions targeting this word
    targeting = [s for s in suggestions if t["word"] in s.get("original", "")
                 or t["bad_correction"] in s.get("correction", "")]
    
    status = "❌ CORRUPTED" if bad_present else ("✅ PRESERVED" if word_present else "⚠ OTHER")
    
    result = {
        "id": t["id"], "word": t["word"], "input": t["sentence"],
        "corrected": corrected, "status": status,
        "targeting_suggestions": len(targeting),
    }
    results.append(result)
    
    print(f"\n  {t['id']}: {t['concern']}")
    print(f"    Input:     '{t['sentence']}'")
    print(f"    Corrected: '{corrected}'")
    print(f"    Status: {status}")
    if targeting:
        for s in targeting:
            conf = s.get('confidence', '?')
            print(f"    Suggestion: '{s.get('original','')}' → '{s.get('correction','')}' (conf={conf})")

# Also test BUG-014/015 live
print("\n" + "=" * 70)
print("B3 LIVE TEST: Suffix corruption via /api/analyze")
print("=" * 70)

b3_tests = [
    {"id": "BUG-014", "sentence": "قرأته بسرعة", "word": "قرأته",
     "bad": "قرأتة", "concern": "قرأته must NOT become قرأتة"},
    {"id": "BUG-015", "sentence": "استوقفني المشهد فتأملته مليا", "word": "فتأملته",
     "bad": "فتأملتة", "concern": "فتأملته must NOT become فتأملتة"},
]

for t in b3_tests:
    r = api_call("/api/analyze", t["sentence"])
    corrected = r.get("corrected", t["sentence"])
    bad_present = t["bad"] in corrected
    word_present = t["word"] in corrected
    status = "❌ CORRUPTED" if bad_present else ("✅ PRESERVED" if word_present else "⚠ OTHER")
    
    print(f"\n  {t['id']}: {t['concern']}")
    print(f"    Input:     '{t['sentence']}'")
    print(f"    Corrected: '{corrected}'")
    print(f"    Status: {status}")
    print(f"    NOTE: Deployed API does NOT have Round 2 fixes yet. "
          f"This tests the CURRENT deployed state.")

# Save
output_path = os.path.join(os.path.dirname(__file__), 'round2_b2_b3_live.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump({"b2": results, "b3_note": "Deployed API lacks Round 2 fixes"}, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to {output_path}")
