import json

d = json.load(open('tests/v2/reports/level3_integrated_results.json', 'r', encoding='utf-8'))
for r in d['results'][:5]:
    print(f"ID: {r['id']}")
    print(f"  IN:  {r['input_text']}")
    print(f"  EXP: {r['expected']}")
    print(f"  OUT: {r['pipeline_corrected']}")
    print(f"  V:   {r['verdict']} | {r['detail']}")
    print()
