import json

with open('tests/phase10/reports/collision_benchmark_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

failures = [r for r in data['results'] if r.get('pipeline_verdict') != 'TP']

print(f"Total failures: {len(failures)}\n")

for i, r in enumerate(failures, 1):
    print(f"{'─'*100}")
    print(f"#{i} {r['id']} | Category: {r['category']}")
    print(f"  INPUT:    '{r['input']}'")
    print(f"  EXPECTED: '{r['expected']}'")
    print(f"  GOT:      '{r['pipeline_output']}'")
    
    # What's wrong?
    exp_words = set(r['expected'].rstrip('.').split())
    got_words = set(r['pipeline_output'].rstrip('.').split())
    missing = exp_words - got_words
    extra = got_words - exp_words
    if missing:
        print(f"  MISSING WORDS: {missing}")
    if extra:
        print(f"  EXTRA WORDS:   {extra}")
    
    # Suggestions
    if r.get('pipeline_suggestions'):
        for s in r['pipeline_suggestions']:
            print(f"  [{s['type']:12}] '{s['original']}' → '{s['correction']}' [{s['start']}:{s['end']}]")
    
    print(f"  ROOT CAUSE: {r.get('root_cause_detail', 'N/A')}")
    print()
