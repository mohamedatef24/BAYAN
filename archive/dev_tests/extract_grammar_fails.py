import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

try:
    with open('tests/phase10/reports/phase10_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open('grammar_fails_output.md', 'w', encoding='utf-8') as out_f:
        out_f.write("=== GRAMMAR FALSE NEGATIVES ===\n")
        for r in data.get('results', []):
            if r.get('dataset') == 'grammar' and r.get('pipeline_verdict') == 'FN':
                out_f.write(f"[{r.get('id')}] - {r.get('category')}\n")
                out_f.write(f"  IN:       {r.get('input')}\n")
                out_f.write(f"  EXP:      {r.get('expected')}\n")
                out_f.write(f"  RAW_GRAM: {r.get('grammar_raw_output')}\n")
                out_f.write(f"  FINAL:    {r.get('pipeline_output')}\n")
                out_f.write("-" * 50 + "\n")


except Exception as e:
    print(f"Error: {e}")
