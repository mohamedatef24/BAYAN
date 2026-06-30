import json

with open('tests/phase10/reports/phase10_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

failures = [r for r in data['results'] if r['pipeline_verdict'] in ('FP', 'FN', 'ERROR')]

md_content = "# Analysis of the 33 Benchmark Failures\n\n"
md_content += "This document contains a detailed breakdown of the 33 examples that failed the benchmark, grouped by their dataset.\n\n"

from collections import defaultdict
grouped = defaultdict(list)
for r in failures:
    grouped[r.get('dataset', 'unknown')].append(r)

for dataset, items in grouped.items():
    md_content += f"## Dataset: {dataset.upper()} ({len(items)} failures)\n\n"
    for idx, item in enumerate(items, 1):
        md_content += f"### {idx}. ID: {item.get('id')} ({item.get('pipeline_verdict')})\n"
        md_content += f"- **Input:** `{item.get('input')}`\n"
        md_content += f"- **Expected:** `{item.get('expected')}`\n"
        md_content += f"- **Actual Output:** `{item.get('pipeline_output')}`\n"
        md_content += f"- **Failure Reason:** {item.get('pipeline_detail', 'N/A')}\n"
        md_content += f"- **Root Cause:** {item.get('root_cause_stage', 'unknown')} ({item.get('root_cause_detail', 'N/A')})\n"
        
        md_content += "\n"

with open('C:\\Users\\youss\\.gemini\\antigravity-ide\\brain\\9f7cefbc-f722-4b96-bc24-80ce6ffbd124\\failures_analysis.md', 'w', encoding='utf-8') as out:
    out.write(md_content)

print("Analysis successfully written to artifact.")
