import json
import random
from pathlib import Path

GOLD_DIR = Path('d:/BAYAN2/tests/phase10/gold_datasets')
OUTPUT_PATH = Path('d:/BAYAN2/reports/benchmark_samples.md')

datasets = {
    'Spelling': 'spelling.json',
    'Grammar': 'grammar.json',
    'Punctuation': 'punctuation.json',
    'Entities': 'entities.json',
    'Religious': 'religious.json',
    'Structured': 'structured_content.json',
    'Hallucination': 'hallucination.json'
}

with open(OUTPUT_PATH, 'w', encoding='utf-8') as out:
    out.write("# Benchmark Random Samples (30 per Dataset)\n\n")
    out.write("These are randomly selected samples exactly as stored in the JSON benchmark files.\n\n")
    
    random.seed(123) # for reproducibility if run again
    
    for name, file in datasets.items():
        out.write(f"## {name}\n\n")
        try:
            with open(GOLD_DIR / file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Select up to 30 samples
            samples = random.sample(data, min(30, len(data)))
            
            out.write("```json\n")
            out.write(json.dumps(samples, ensure_ascii=False, indent=2))
            out.write("\n```\n\n")
        except Exception as e:
            out.write(f"Error loading {file}: {e}\n\n")

print(f"Generated samples report at {OUTPUT_PATH}")
