import json
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
with open('tests/phase10/reports/collision_benchmark_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for r in data['results']:
    if r.get('pipeline_verdict') != 'PASS':
        print(f"{r['id']} | {r['category']} | Expected: {r['expected']} | Actual: {r.get('pipeline_output', '')}")
