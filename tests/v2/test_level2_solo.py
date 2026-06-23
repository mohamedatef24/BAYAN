"""
BAYAN v2.0 — Level 2: Solo API Tests
=====================================
Tests each model through its INDIVIDUAL API endpoint (/api/spelling, /api/grammar,
/api/punctuation). This measures what each stage produces in isolation — with
any endpoint-level preprocessing but WITHOUT pipeline integration (StageLocker,
OffsetMapper, cross-stage interaction).

Compares with Level 1 raw results to measure filter impact:
- If L2 passes more tests than L1 → filters are helping
- If L2 passes fewer tests than L1 → filters are over-filtering

Usage:
    python tests/v2/test_level2_solo.py --url URL [--dataset DATASET]
"""
import argparse
import json
import re
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List
import requests

DATASETS_DIR = Path(__file__).parent.parent / "phase10" / "gold_datasets"
REPORT_DIR = Path(__file__).parent / "reports"


def normalize(text):
    t = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


@dataclass
class SoloResult:
    id: str
    dataset: str
    category: str
    input_text: str
    expected: str
    severity: str
    # Solo API outputs (each model called independently on the SAME input)
    spelling_solo: str = ""
    spelling_ms: int = 0
    grammar_solo: str = ""
    grammar_ms: int = 0
    punctuation_solo: str = ""
    punctuation_ms: int = 0
    # Verdict per model
    spelling_verdict: str = ""  # TP, TN, FP, FN
    grammar_verdict: str = ""
    punctuation_verdict: str = ""


class APIClient:
    def __init__(self, base_url):
        self.base = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/json'

    def call(self, endpoint, text, timeout=120):
        t0 = time.time()
        try:
            r = self.session.post(
                f"{self.base}{endpoint}",
                json={"text": text},
                timeout=timeout
            )
            ms = int((time.time() - t0) * 1000)
            data = r.json()
            corrected = data.get("corrected_text", data.get("corrected", text))
            return corrected, ms
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            return f"ERROR: {e}", ms


def classify_result(input_text, output_text, expected_text, dataset):
    """Classify a single model output as TP/TN/FP/FN.
    
    For datasets that test CORRECTION (spelling, grammar, punctuation):
      - TP: model corrected AND the correction is in the expected direction
      - FN: model did NOT correct (output == input) but should have
      - FP: model corrected but incorrectly (changed text that was correct or wrong direction)
      - TN: model correctly left unchanged (output == input AND input was correct)
    
    For datasets that test PRESERVATION (entities, religious, structured, hallucination):
      - TN: model left text unchanged → PASS
      - FP: model modified text → FAIL
    """
    inp_n = normalize(input_text)
    out_n = normalize(output_text)
    exp_n = normalize(expected_text)
    
    is_preservation = dataset in ('entities', 'religious', 'structured', 'hallucination')
    text_changed = (out_n != inp_n)
    
    if is_preservation:
        # For preservation tests, the expected output == input (don't change)
        if not text_changed:
            return "TN"  # Correctly preserved
        else:
            return "FP"  # Incorrectly modified
    else:
        # For correction tests
        needs_correction = (inp_n != exp_n)
        
        # Strip trailing punctuation from output for comparison
        _TERMINAL_PUNCT = '.،؛؟!?!'
        out_stripped = out_n.rstrip(_TERMINAL_PUNCT).rstrip()
        
        if needs_correction:
            if text_changed:
                if out_n == exp_n or out_stripped == exp_n:
                    return "TP"  # Perfect correction
                elif _edit_distance(out_stripped, exp_n) < _edit_distance(inp_n, exp_n):
                    return "TP"  # Partial but improving correction
                elif _edit_distance(out_n, exp_n) < _edit_distance(inp_n, exp_n):
                    return "TP"  # Improving (with punct)
                else:
                    return "FP"  # Changed but not in right direction
            else:
                return "FN"  # Should have corrected but didn't
        else:
            if not text_changed:
                return "TN"  # Correctly left unchanged
            elif out_stripped == inp_n:
                return "TN"  # Only punctuation added
            else:
                return "FP"  # Changed text that was already correct


def _edit_distance(a, b):
    """Simple Levenshtein edit distance."""
    if len(a) < len(b):
        return _edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[len(b)]


def load_datasets(dataset_filter=None):
    datasets = {}
    for f in sorted(DATASETS_DIR.glob("*.json")):
        name = f.stem
        if dataset_filter and name != dataset_filter:
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            datasets[name] = json.load(fh)
    return datasets


def run_level2(api: APIClient, datasets: dict) -> List[SoloResult]:
    results = []
    total = sum(len(v) for v in datasets.values())
    idx = 0

    for ds_name, cases in datasets.items():
        print(f"\n{'='*60}")
        print(f"DATASET: {ds_name.upper()} ({len(cases)} samples)")
        print(f"{'='*60}")

        for case in cases:
            idx += 1
            cid = case.get('id', f'{ds_name}_{idx}')
            cat = case.get('category', '')
            inp = case.get('input', '')
            expected = case.get('expected', case.get('input', ''))
            severity = case.get('severity', '')

            r = SoloResult(
                id=cid, dataset=ds_name, category=cat,
                input_text=inp, expected=expected, severity=severity
            )

            print(f"  [{idx}/{total}] {cid} ({cat})...", end=" ", flush=True)

            # Test each model independently on the SAME original input
            r.spelling_solo, r.spelling_ms = api.call("/api/spelling", inp)
            r.grammar_solo, r.grammar_ms = api.call("/api/grammar", inp)
            r.punctuation_solo, r.punctuation_ms = api.call("/api/punctuation", inp)

            # Classify each model's result
            r.spelling_verdict = classify_result(inp, r.spelling_solo, expected, ds_name)
            r.grammar_verdict = classify_result(inp, r.grammar_solo, expected, ds_name)
            r.punctuation_verdict = classify_result(inp, r.punctuation_solo, expected, ds_name)

            total_ms = r.spelling_ms + r.grammar_ms + r.punctuation_ms
            print(f"S={r.spelling_verdict} G={r.grammar_verdict} P={r.punctuation_verdict} ({total_ms}ms)")

            results.append(r)

    return results


def analyze_and_print(results: List[SoloResult]) -> dict:
    analysis = {"total": len(results), "by_model": {}, "by_dataset": {}}
    
    for model in ("spelling", "grammar", "punctuation"):
        verdicts = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
        for r in results:
            v = getattr(r, f"{model}_verdict", "")
            if v in verdicts:
                verdicts[v] += 1
        total = sum(verdicts.values())
        pass_count = verdicts["TP"] + verdicts["TN"]
        analysis["by_model"][model] = {
            **verdicts,
            "pass_rate": round(pass_count / total, 4) if total else 0,
        }

    # Per-dataset breakdown
    for ds in set(r.dataset for r in results):
        ds_results = [r for r in results if r.dataset == ds]
        ds_analysis = {}
        for model in ("spelling", "grammar", "punctuation"):
            verdicts = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
            for r in ds_results:
                v = getattr(r, f"{model}_verdict", "")
                if v in verdicts:
                    verdicts[v] += 1
            total = sum(verdicts.values())
            pass_count = verdicts["TP"] + verdicts["TN"]
            ds_analysis[model] = {
                **verdicts,
                "pass_rate": round(pass_count / total, 4) if total else 0,
            }
        analysis["by_dataset"][ds] = {"total": len(ds_results), **ds_analysis}

    # Print
    print(f"\n{'='*60}")
    print("LEVEL 2: SOLO API ANALYSIS")
    print(f"{'='*60}")

    print(f"\n## Per-Model Summary ({analysis['total']} tests)")
    print(f"| Model       | TP  | TN  | FP  | FN  | Pass%  |")
    print(f"|-------------|-----|-----|-----|-----|--------|")
    for model, data in analysis["by_model"].items():
        print(f"| {model:<11} | {data['TP']:>3} | {data['TN']:>3} | {data['FP']:>3} | {data['FN']:>3} | {data['pass_rate']*100:5.1f}% |")

    print(f"\n## Per-Dataset × Model Pass Rate")
    print(f"| Dataset      | Spelling | Grammar | Punctuation |")
    print(f"|--------------|----------|---------|-------------|")
    for ds in sorted(analysis["by_dataset"].keys()):
        d = analysis["by_dataset"][ds]
        s = d["spelling"]["pass_rate"] * 100
        g = d["grammar"]["pass_rate"] * 100
        p = d["punctuation"]["pass_rate"] * 100
        print(f"| {ds:<12} | {s:6.1f}%  | {g:5.1f}%  | {p:9.1f}%  |")

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Level 2: Solo API Tests")
    parser.add_argument("--url", default="https://bayan10-bayan-api.hf.space")
    parser.add_argument("--dataset", default=None)
    args = parser.parse_args()

    api = APIClient(args.url)
    datasets = load_datasets(args.dataset)

    print(f"\n{'='*60}")
    print("BAYAN v2.0 — Level 2: Solo API Tests")
    print(f"{'='*60}")
    print(f"  Target:   {args.url}")
    print(f"  Datasets: {list(datasets.keys())}")
    print(f"  Total:    {sum(len(v) for v in datasets.values())} tests")

    results = run_level2(api, datasets)
    analysis = analyze_and_print(results)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "level2_solo_results.json"
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": args.url,
        "analysis": analysis,
        "results": [asdict(r) for r in results],
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[L2] Results → {out_path}")


if __name__ == "__main__":
    main()
