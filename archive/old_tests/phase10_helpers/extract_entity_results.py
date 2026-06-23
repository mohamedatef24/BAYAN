import json

d = json.load(open('tests/phase10/reports/phase10_results.json', 'r', encoding='utf-8'))
for r in d['results']:
    if r['id'].startswith('E'):
        v = r.get('pipeline_verdict', '?')
        inp = r.get('input', '')[:60]
        out = r.get('pipeline_output', '')[:60]
        det = r.get('pipeline_detail', '')[:60]
        cat = r.get('category', '')
        print(f"{r['id']} [{v:3}] cat={cat}")
        print(f"  IN:  {inp}")
        print(f"  OUT: {out}")
        if det:
            print(f"  DET: {det}")
        print()
