import json
with open('tests/phase10/reports/phase10_results.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
    for r in d['results']:
        if r['pipeline_verdict'] == 'FP' and r['dataset'] == 'hallucination':
            print(f"{r['id']}: {r['pipeline_detail']}")
