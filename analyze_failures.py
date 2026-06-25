"""Analyze remaining 24 failures after Layer 1/2/3 fixes."""
import json, re

with open('tests/phase10/reports/collision_benchmark_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def norm(t):
    t = re.sub(r'[\u064B-\u065F\u0670]', '', t)
    t = t.rstrip('.،؛؟!?!')
    return re.sub(r'\s+', ' ', t).strip()

categories = {}
for r in data['results']:
    if r['pipeline_verdict'] != 'FN':
        continue
    rid = r['id']
    exp = r['expected'].strip()
    act = r['pipeline_output'].strip()
    inp = r['input'].strip()
    
    inp_w = inp.split()
    exp_w = exp.split()
    act_w = act.split()
    
    issues = []
    for i in range(min(len(exp_w), len(act_w))):
        aw = act_w[i].rstrip('.،؛؟!?!')
        ew = exp_w[i].rstrip('.،؛؟!?!')
        iw = inp_w[i] if i < len(inp_w) else '—'
        aw_n = re.sub(r'[\u064B-\u065F]', '', aw)
        ew_n = re.sub(r'[\u064B-\u065F]', '', ew)
        
        if aw_n == ew_n:
            continue  # tanween/diacritic only diff
        if aw != ew:
            if iw == aw:
                cause = "MODEL_MISS"
            elif iw == ew:
                cause = "CORRUPTED"
            else:
                cause = "WRONG_FIX"
            issues.append(f"    [{i}] '{iw}'→'{aw}' (exp:'{ew}') {cause}")
    
    if len(exp_w) != len(act_w):
        issues.append(f"    word count: {len(act_w)} vs {len(exp_w)}")
    
    # Classify
    has_junk = any('وومن' in a or '.و' in a or 'ةل' in a for a in act_w)
    has_trailing_و = any(a.endswith('و') and not e.endswith('و') and not e.endswith('وا') 
                         for a, e in zip(act_w, exp_w) if a != e)
    
    cat = r['category']
    print(f"\n{rid} [{cat}]")
    print(f"  IN:  {inp[:60]}")
    print(f"  EXP: {exp[:60]}")
    print(f"  ACT: {act[:60]}")
    for iss in issues:
        print(iss)
    if has_junk:
        print("  >>> TRAILING JUNK")

# Summary of what each failure needs
print("\n" + "="*60)
print("FIXABILITY ANALYSIS")
print("="*60)
print(f"\nTotal failures: 24")
print(f"Need: 17 more passes to reach 85% (43/50)")
