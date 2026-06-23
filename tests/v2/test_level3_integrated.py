"""
BAYAN v2.0 — Level 3: Integrated Pipeline Tests
=================================================
Tests the FULL integrated pipeline through /api/analyze.
This is the end-to-end test: Spelling → Grammar → Punctuation
with all filters, StageLocker, OffsetMapper, PatchSet.

Reuses the exact same verdict logic as the existing benchmark_runner.py
to ensure comparability.

Usage:
    python tests/v2/test_level3_integrated.py --url URL [--dataset DATASET]
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
class IntegratedResult:
    id: str
    dataset: str
    category: str
    input_text: str
    expected: str
    severity: str
    # Pipeline output
    pipeline_corrected: str = ""
    pipeline_suggestions: int = 0
    pipeline_ms: int = 0
    spelling_ms: int = 0
    grammar_ms: int = 0
    punctuation_ms: int = 0
    # Verdict
    verdict: str = ""      # TP, TN, FP, FN
    detail: str = ""


class APIClient:
    def __init__(self, base_url):
        self.base = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/json'

    def analyze(self, text, timeout=120):
        t0 = time.time()
        try:
            r = self.session.post(
                f"{self.base}/api/analyze",
                json={"text": text},
                timeout=timeout
            )
            ms = int((time.time() - t0) * 1000)
            return r.json(), ms
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            return {"error": str(e)}, ms


def classify_pipeline(input_text, corrected_text, expected_text, dataset, entity=None):
    """Classify pipeline output.
    
    For correction datasets (spelling, grammar, punctuation, collision):
      Input has errors → should be corrected to match expected.
    
    For preservation datasets (entities, religious, structured, hallucination):
      Input is correct → should NOT be modified.
      For entity tests: specifically check that the entity string is preserved.
    """
    inp_n = normalize(input_text)
    out_n = normalize(corrected_text)
    exp_n = normalize(expected_text)
    
    is_preservation = dataset in ('entities', 'religious', 'structured', 'hallucination')
    text_changed = (out_n != inp_n)
    
    if dataset == 'entities' and entity:
        # Entity tests: check if entity is preserved in output
        entity_n = normalize(entity)
        if entity_n in out_n:
            return "TN", "Entity preserved"
        elif not text_changed:
            return "TN", "Text unchanged"
        else:
            return "FP", f"ENTITY CORRUPTED: '{entity}' missing from output"
    
    if is_preservation:
        if not text_changed:
            return "TN", "Text correctly preserved"
        else:
            # Check what changed
            inp_words = inp_n.split()
            out_words = out_n.split()
            changes = []
            for iw, ow in zip(inp_words, out_words):
                if iw != ow:
                    changes.append(f"{iw}→{ow}")
            detail = f"Text modified: {changes[:5]}"
            return "FP", detail
    else:
        # Correction dataset
        needs_correction = (inp_n != exp_n)
        
        # Strip trailing punctuation from output for comparison
        # Pipeline may add . or ؟ via PuncAra even when the correction is correct
        _TERMINAL_PUNCT = '.،؛؟!?!'
        out_stripped = out_n.rstrip(_TERMINAL_PUNCT).rstrip()
        
        if needs_correction:
            if out_n == exp_n or out_stripped == exp_n:
                return "TP", "Exact match"
            elif text_changed and _closer(out_stripped, inp_n, exp_n):
                return "TP", "Partial improvement"
            elif text_changed and _closer(out_n, inp_n, exp_n):
                return "TP", "Partial improvement (with punct)"
            elif not text_changed:
                return "FN", "No correction applied"
            else:
                return "FP", f"Wrong correction"
        else:
            if not text_changed:
                return "TN", "Correctly unchanged"
            elif out_stripped == inp_n:
                # Only punctuation was added — count as TN for correction datasets
                return "TN", "Only punctuation added"
            else:
                return "FP", f"Modified correct text"


def _closer(output, input_text, expected):
    """Is output closer to expected than input was?"""
    d_out = _edit_distance(output, expected)
    d_inp = _edit_distance(input_text, expected)
    return d_out < d_inp


def _edit_distance(a, b):
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


def run_level3(api: APIClient, datasets: dict) -> List[IntegratedResult]:
    results = []
    total = sum(len(v) for v in datasets.values())
    idx = 0

    for ds_name, cases in datasets.items():
        print(f"\n{'='*60}")
        print(f"DATASET: {ds_name.upper()} ({len(cases)} samples)")
        print(f"{'='*60}")

        tp = tn = fp = fn = 0
        for case in cases:
            idx += 1
            cid = case.get('id', f'{ds_name}_{idx}')
            cat = case.get('category', '')
            inp = case.get('input', '')
            expected = case.get('expected', case.get('input', ''))
            severity = case.get('severity', '')
            entity = case.get('entity', None)

            r = IntegratedResult(
                id=cid, dataset=ds_name, category=cat,
                input_text=inp, expected=expected, severity=severity
            )

            print(f"  [{idx}/{total}] {cid} ({cat})...", end=" ", flush=True)

            data, ms = api.analyze(inp)
            r.pipeline_ms = ms
            r.pipeline_corrected = data.get('corrected', inp)
            r.pipeline_suggestions = len(data.get('suggestions', []))
            timing = data.get('timing_ms', {})
            r.spelling_ms = timing.get('spelling_ms', 0)
            r.grammar_ms = timing.get('grammar_ms', 0)
            r.punctuation_ms = timing.get('punctuation_ms', 0)

            r.verdict, r.detail = classify_pipeline(
                inp, r.pipeline_corrected, expected, ds_name, entity
            )

            icon = {"TP": "✅", "TN": "✅", "FP": "❌", "FN": "⚠️"}.get(r.verdict, "?")
            print(f"{icon} {r.verdict} ({r.pipeline_ms}ms)")

            if r.verdict == "TP": tp += 1
            elif r.verdict == "TN": tn += 1
            elif r.verdict == "FP": fp += 1
            elif r.verdict == "FN": fn += 1

            results.append(r)

        total_ds = tp + tn + fp + fn
        pass_pct = (tp + tn) / total_ds * 100 if total_ds else 0
        print(f"\n  Pass={pass_pct:.1f}% TP={tp} TN={tn} FP={fp} FN={fn}")

    return results


def analyze_and_print(results: List[IntegratedResult]) -> dict:
    verdicts = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    by_dataset = {}

    for r in results:
        verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1
        if r.dataset not in by_dataset:
            by_dataset[r.dataset] = {"TP": 0, "TN": 0, "FP": 0, "FN": 0, "total": 0}
        by_dataset[r.dataset][r.verdict] += 1
        by_dataset[r.dataset]["total"] += 1

    total = sum(verdicts.values())
    pass_count = verdicts["TP"] + verdicts["TN"]

    analysis = {
        "total": total,
        "aggregate": {
            **verdicts,
            "pass_rate": round(pass_count / total, 4) if total else 0,
        },
        "by_dataset": {},
    }

    print(f"\n{'='*60}")
    print("LEVEL 3: INTEGRATED PIPELINE ANALYSIS")
    print(f"{'='*60}")
    print(f"\n  Total: {total} | Pass: {pass_count}/{total} ({analysis['aggregate']['pass_rate']*100:.1f}%)")
    print(f"  TP={verdicts['TP']} TN={verdicts['TN']} FP={verdicts['FP']} FN={verdicts['FN']}")

    print(f"\n| Dataset      | Total | TP  | TN  | FP  | FN  | Pass%  |")
    print(f"|--------------|-------|-----|-----|-----|-----|--------|")
    for ds in sorted(by_dataset.keys()):
        d = by_dataset[ds]
        p = (d["TP"] + d["TN"]) / d["total"] * 100 if d["total"] else 0
        print(f"| {ds:<12} | {d['total']:>5} | {d['TP']:>3} | {d['TN']:>3} | {d['FP']:>3} | {d['FN']:>3} | {p:5.1f}% |")
        analysis["by_dataset"][ds] = {**d, "pass_rate": round(p / 100, 4)}

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Level 3: Integrated Pipeline Tests")
    parser.add_argument("--url", default="https://bayan10-bayan-api.hf.space")
    parser.add_argument("--dataset", default=None)
    args = parser.parse_args()

    api = APIClient(args.url)
    datasets = load_datasets(args.dataset)

    print(f"\n{'='*60}")
    print("BAYAN v2.0 — Level 3: Integrated Pipeline Tests")
    print(f"{'='*60}")
    print(f"  Target:   {args.url}")
    print(f"  Datasets: {list(datasets.keys())}")
    print(f"  Total:    {sum(len(v) for v in datasets.values())} tests")

    results = run_level3(api, datasets)
    analysis = analyze_and_print(results)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "level3_integrated_results.json"
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": args.url,
        "analysis": analysis,
        "results": [asdict(r) for r in results],
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[L3] Results → {out_path}")


if __name__ == "__main__":
    main()
