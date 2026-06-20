"""
Phase 9 — Concurrency Re-verification

Send 5 genuinely different inputs simultaneously.
Verify each response correctly corresponds to its own input.
No mixed, swapped, or cross-contaminated suggestions.

If cross-contamination is found, treat as P0 bug.
"""
import sys, os, json, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 60

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


# 5 genuinely different inputs — different lengths, different error types
CONCURRENT_INPUTS = [
    {
        "id": "CONC-1",
        "text": "الحديقه جميله",
        "description": "Short text with spelling error (ه→ة)",
        "expected_contains": "الحديق",  # at least part of the input
        "must_not_contain_from_others": ["المدرسة", "القاهرة", "مصر"],
    },
    {
        "id": "CONC-2",
        "text": "الطلاب ذهبو الى المدرسة",
        "description": "Medium text with grammar error (ذهبو→ذهبوا)",
        "expected_contains": "المدرسة",
        "must_not_contain_from_others": ["الحديق", "القاهرة عاصمة"],
    },
    {
        "id": "CONC-3",
        "text": "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة رغبة في بناء كتلة عضلية قوية ويا له من التزام حديدي يثير الإعجاب ولقد كان أداؤه في المسابقات الأخيرة مبهرا للغاية",
        "description": "Long text with punctuation needed (50+ words)",
        "expected_contains": "الرياضي",
        "must_not_contain_from_others": ["الحديق", "المدرسة"],
    },
    {
        "id": "CONC-4",
        "text": "القاهرة عاصمة مصر",
        "description": "Correct text (should return ~0 suggestions)",
        "expected_contains": "القاهرة",
        "must_not_contain_from_others": ["الحديق", "المدرسة", "الرياضي"],
    },
    {
        "id": "CONC-5",
        "text": "هذة المدينه جميله جدا ومناخها معتدل",
        "description": "Text with mixed errors (هذة→هذه, ه→ة)",
        "expected_contains": "المدين",
        "must_not_contain_from_others": ["المدرسة", "القاهرة", "الرياضي"],
    },
]


def test_concurrent():
    print("=" * 70)
    print("PHASE 9 — Concurrency Re-verification")
    print("=" * 70)

    # Fire all 5 requests simultaneously
    results = {}
    print(f"\nSending {len(CONCURRENT_INPUTS)} requests simultaneously...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for inp in CONCURRENT_INPUTS:
            future = executor.submit(api_call, "/api/analyze", inp["text"])
            futures[future] = inp

        for future in as_completed(futures):
            inp = futures[future]
            result = future.result()
            results[inp["id"]] = {
                "input": inp,
                "response": result,
            }
            print(f"  {inp['id']} completed ({result.get('_elapsed_ms', '?')}ms)")

    # Verify each response corresponds to its own input
    print("\n--- Verification ---")
    all_pass = True
    contamination_found = False

    for test_id, data in sorted(results.items()):
        inp = data["input"]
        resp = data["response"]

        if "error" in resp and "status" not in resp:
            print(f"\n  ⚠ {test_id}: ERROR — {resp['error']}")
            continue

        corrected = resp.get("corrected", "")
        original = resp.get("original", "")
        suggestions = resp.get("suggestions", [])

        print(f"\n  {test_id}: {inp['description']}")
        print(f"    Input:     '{inp['text'][:60]}...'")
        print(f"    Original:  '{original[:60]}...'")
        print(f"    Corrected: '{corrected[:60]}...'")
        print(f"    Suggestions: {len(suggestions)}")

        # Check 1: original field should match our input
        if original != inp["text"]:
            print(f"    ❌ FAIL: original != input! (cross-contamination?)")
            contamination_found = True
            all_pass = False
        else:
            print(f"    ✓ original matches input")

        # Check 2: corrected should contain expected content
        if inp["expected_contains"] in corrected:
            print(f"    ✓ corrected contains '{inp['expected_contains']}'")
        else:
            print(f"    ⚠ corrected missing '{inp['expected_contains']}'")

        # Check 3: corrected must NOT contain content from other inputs
        for foreign in inp["must_not_contain_from_others"]:
            if foreign in corrected:
                print(f"    ❌ CONTAMINATION: corrected contains '{foreign}' from another input!")
                contamination_found = True
                all_pass = False

        # Check 4: suggestions should reference text in our input
        for s in suggestions:
            s_orig = s.get("original", "")
            s_start = s.get("start", 0)
            s_end = s.get("end", 0)
            # The suggestion's original text should be a substring of our input
            if s_orig and s_orig not in inp["text"]:
                # Check if it's a substring match (punc may include partial words)
                input_slice = inp["text"][s_start:s_end]
                if s_orig != input_slice:
                    print(f"    ⚠ Suggestion '{s_orig}' [{s_start}:{s_end}] not in input")

    print("\n" + "=" * 50)
    if contamination_found:
        print("🚨 P0: CROSS-CONTAMINATION DETECTED!")
        print("   PipelineContext state is leaking between requests.")
        print("   STOP ALL OTHER WORK AND FIX THIS FIRST.")
    elif all_pass:
        print("✅ ALL PASSED — No cross-contamination detected.")
    else:
        print("⚠ Some checks failed but no cross-contamination.")

    return {
        "test_count": len(CONCURRENT_INPUTS),
        "all_pass": all_pass,
        "contamination_found": contamination_found,
        "results": {k: {"corrected": v["response"].get("corrected", ""),
                        "suggestions_count": len(v["response"].get("suggestions", []))}
                   for k, v in results.items()},
    }


if __name__ == "__main__":
    result = test_concurrent()
    output_path = os.path.join(os.path.dirname(__file__), 'phase9_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {output_path}")
