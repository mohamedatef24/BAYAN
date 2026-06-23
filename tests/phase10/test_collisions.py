import json
import requests

url = "https://bayan10-bayan-api.hf.space/api/analyze"
with open("d:/BAYAN2/tests/phase10/gold_datasets/pipeline_collision.json", "r", encoding="utf-8") as f:
    samples = json.load(f)

failures = []
passed = 0

for i, s in enumerate(samples[:10]):  # Test first 10 for analysis
    try:
        r = requests.post(url, json={"text": s["input"]}).json()
        out = r.get("corrected", "")
        if out == s["expected"]:
            passed += 1
            print(f"[{s['id']}] PASS")
        else:
            failures.append((s, out))
            print(f"[{s['id']}] FAIL")
            print(f"  Input: {s['input']}")
            print(f"  Expected: {s['expected']}")
            print(f"  Actual:   {out}")
    except Exception as e:
        print(f"[{s['id']}] ERROR: {e}")

print(f"\nResults: {passed} PASS, {len(failures)} FAIL")
