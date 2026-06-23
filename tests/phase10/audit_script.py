import json
from pathlib import Path
import random
import re

GOLD_DIR = Path('d:/BAYAN2/tests/phase10/gold_datasets')

datasets = {
    'Spelling': 'spelling.json',
    'Grammar': 'grammar.json',
    'Punctuation': 'punctuation.json',
    'Entities': 'entities.json',
    'Religious': 'religious.json',
    'Structured': 'structured_content.json',
    'Hallucination': 'hallucination.json'
}

data = {}
for name, file in datasets.items():
    with open(GOLD_DIR / file, 'r', encoding='utf-8') as f:
        data[name] = json.load(f)

def words(text):
    return len(re.findall(r'[\w]+', text))

print("=== Section 1 & 2: Counts & Categories ===")
for name, samples in data.items():
    print(f"\n{name} ({len(samples)} samples):")
    categories = {}
    for s in samples:
        c = s.get('category', 'None')
        categories[c] = categories.get(c, 0) + 1
    for c, cnt in categories.items():
        print(f"  {c}: {cnt}")

print("\n=== Section 3: Lengths ===")
for name, samples in data.items():
    lengths = [words(s['input']) for s in samples]
    avg = sum(lengths) / len(lengths) if lengths else 0
    l_sorted = sorted(lengths)
    med = l_sorted[len(lengths)//2] if lengths else 0
    mx = max(lengths) if lengths else 0
    mn = min(lengths) if lengths else 0
    single = sum(1 for l in lengths if l == 1)
    short = sum(1 for l in lengths if 1 < l <= 5)
    medium = sum(1 for l in lengths if 5 < l <= 15)
    long_s = sum(1 for l in lengths if 15 < l <= 30)
    para = sum(1 for l in lengths if l > 30)
    print(f"{name}: Avg={avg:.1f}, Med={med}, Max={mx}, Min={mn} | 1w:{single}, <5:{short}, <15:{medium}, <30:{long_s}, >30:{para}")

print("\n=== Section 4: Synthetic Patterns ===")
for name, samples in data.items():
    inputs = [s['input'] for s in samples]
    unique = set(inputs)
    dupes = len(inputs) - len(unique)
    print(f"{name}: {dupes} exact duplicates. Unique={len(unique)}/{len(inputs)}")

print("\n=== Section 10: Random Samples for Review ===")
samples_to_review = {
    'Spelling': 20, 'Grammar': 20, 'Punctuation': 10,
    'Entities': 10, 'Religious': 10, 'Structured': 10, 'Hallucination': 10
}
random.seed(42)
for name, count in samples_to_review.items():
    print(f"\n--- {name} ({count} samples) ---")
    samps = random.sample(data[name], min(count, len(data[name])))
    for i, s in enumerate(samps):
        print(f"[{i+1}] ID: {s.get('id')} | Cat: {s.get('category')}")
        print(f"    In : {s.get('input')}")
        if 'expected' in s: print(f"    Exp: {s.get('expected')}")
        if 'expected_fix' in s: print(f"    Fix: {s.get('expected_fix')}")
