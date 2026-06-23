"""
BAYAN v2.0 — Level 1: Raw Model Tests
======================================
Tests each ML model through its individual API endpoint — measuring the RAW
model output with no pipeline integration (no StageLocker, no OffsetMapper,
no cross-stage interaction).

NOTE: On HF Spaces deployment, the solo endpoints (/api/spelling, /api/grammar,
/api/punctuation) call the models directly with minimal preprocessing. This is
as close to "raw model" as we can get without local model access.

Produces:
  - TP/FP/FN/TN verdicts per model per test case
  - Per-word edit analysis (what words each model changed)
  - Change rate and accuracy per model per dataset

Usage:
    python tests/v2/test_level1_raw.py --url URL [--dataset DATASET]
"""
import argparse
import json
import re
import time
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import requests

# Datasets
DATASETS_DIR = Path(__file__).parent.parent / "phase10" / "gold_datasets"
REPORT_DIR = Path(__file__).parent / "reports"

# Terminal punctuation to strip before comparison
_TERMINAL_PUNCT = '.،؛؟!?!'


@dataclass
class RawModelResult:
    id: str
    dataset: str
    category: str
    input_text: str
    expected: str          # What the benchmark expects
    severity: str
    # Raw model outputs
    spelling_raw: str = ""
    spelling_ms: int = 0
    grammar_raw: str = ""
    grammar_ms: int = 0
    punctuation_raw: str = ""
    punctuation_ms: int = 0
    # Change detection
    spelling_changed: bool = False
    grammar_changed: bool = False
    punctuation_changed: bool = False
    # Verdicts (TP/TN/FP/FN)
    spelling_verdict: str = ""
    grammar_verdict: str = ""
    punctuation_verdict: str = ""
    # Word-level edits
    spelling_edits: str = ""   # "word1→word2, word3→word4"
    grammar_edits: str = ""
    punctuation_edits: str = ""


class APIClient:
    """Minimal client to call individual model endpoints."""
    def __init__(self, base_url):
        self.base = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/json'

    def _post(self, endpoint, text, timeout=120):
        t0 = time.time()
        try:
            r = self.session.post(
                f"{self.base}{endpoint}",
                json={"text": text},
                timeout=timeout
            )
            ms = int((time.time() - t0) * 1000)
            data = r.json()
            return data, ms
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            return {"error": str(e)}, ms

    def spelling_raw(self, text):
        data, ms = self._post("/api/spelling", text)
        corrected = data.get("corrected_text", data.get("corrected", text))
        return corrected, ms

    def grammar_raw(self, text):
        data, ms = self._post("/api/grammar", text)
        corrected = data.get("corrected_text", data.get("corrected", text))
        return corrected, ms

    def punctuation_raw(self, text):
        data, ms = self._post("/api/punctuation", text)
        corrected = data.get("corrected_text", data.get("corrected", text))
        return corrected, ms


def load_datasets(dataset_filter=None):
    datasets = {}
    for f in sorted(DATASETS_DIR.glob("*.json")):
        name = f.stem
        if dataset_filter and name != dataset_filter:
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            datasets[name] = json.load(fh)
    return datasets


def normalize(text):
    t = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


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


def get_word_edits(input_text, output_text):
    """Get word-level edits between input and output."""
    inp_words = normalize(input_text).split()
    out_words = normalize(output_text).split()
    edits = []

    # Simple alignment: match by position
    max_len = max(len(inp_words), len(out_words))
    for i in range(max_len):
        iw = inp_words[i] if i < len(inp_words) else "∅"
        ow = out_words[i] if i < len(out_words) else "∅"
        if iw != ow:
            edits.append(f"{iw}→{ow}")

    return ", ".join(edits[:5])  # Cap at 5 edits for readability


def classify_raw(input_text, output_text, expected_text, dataset):
    """Classify raw model output as TP/TN/FP/FN.

    Same logic as L2/L3 but applied to raw model output.
    """
    inp_n = normalize(input_text)
    out_n = normalize(output_text)
    exp_n = normalize(expected_text)

    out_stripped = out_n.rstrip(_TERMINAL_PUNCT).rstrip()
    text_changed = (out_n != inp_n)

    is_preservation = dataset in ('entities', 'religious', 'structured', 'hallucination')

    if is_preservation:
        if not text_changed:
            return "TN"
        elif out_stripped == inp_n:
            return "TN"  # Only punctuation added — not entity corruption
        else:
            return "FP"
    else:
        needs_correction = (inp_n != exp_n)
        if needs_correction:
            if out_n == exp_n or out_stripped == exp_n:
                return "TP"
            elif text_changed and _edit_distance(out_stripped, exp_n) < _edit_distance(inp_n, exp_n):
                return "TP"
            elif text_changed and _edit_distance(out_n, exp_n) < _edit_distance(inp_n, exp_n):
                return "TP"
            elif not text_changed:
                return "FN"
            else:
                return "FP"
        else:
            if not text_changed:
                return "TN"
            elif out_stripped == inp_n:
                return "TN"  # Only punctuation added
            else:
                return "FP"


def run_level1(api: APIClient, datasets: dict) -> List[RawModelResult]:
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

            r = RawModelResult(
                id=cid, dataset=ds_name, category=cat,
                input_text=inp, expected=expected, severity=severity
            )

            print(f"  [{idx}/{total}] {cid} ({cat})...", end=" ", flush=True)

            # ── Spelling ──
            try:
                r.spelling_raw, r.spelling_ms = api.spelling_raw(inp)
                r.spelling_changed = (normalize(r.spelling_raw) != normalize(inp))
                r.spelling_verdict = classify_raw(inp, r.spelling_raw, expected, ds_name)
                if r.spelling_changed:
                    r.spelling_edits = get_word_edits(inp, r.spelling_raw)
            except Exception as e:
                r.spelling_raw = f"ERROR: {e}"
                r.spelling_verdict = "ERR"

            # ── Grammar ──
            try:
                r.grammar_raw, r.grammar_ms = api.grammar_raw(inp)
                r.grammar_changed = (normalize(r.grammar_raw) != normalize(inp))
                r.grammar_verdict = classify_raw(inp, r.grammar_raw, expected, ds_name)
                if r.grammar_changed:
                    r.grammar_edits = get_word_edits(inp, r.grammar_raw)
            except Exception as e:
                r.grammar_raw = f"ERROR: {e}"
                r.grammar_verdict = "ERR"

            # ── Punctuation ──
            try:
                r.punctuation_raw, r.punctuation_ms = api.punctuation_raw(inp)
                r.punctuation_changed = (normalize(r.punctuation_raw) != normalize(inp))
                r.punctuation_verdict = classify_raw(inp, r.punctuation_raw, expected, ds_name)
                if r.punctuation_changed:
                    r.punctuation_edits = get_word_edits(inp, r.punctuation_raw)
            except Exception as e:
                r.punctuation_raw = f"ERROR: {e}"
                r.punctuation_verdict = "ERR"

            total_ms = r.spelling_ms + r.grammar_ms + r.punctuation_ms
            print(f"S={r.spelling_verdict} G={r.grammar_verdict} P={r.punctuation_verdict} ({total_ms}ms)")

            results.append(r)

    return results


def analyze_results(results: List[RawModelResult]) -> dict:
    analysis = {
        "total": len(results),
        "by_model": {},
        "by_dataset": {},
    }

    for model in ("spelling", "grammar", "punctuation"):
        verdicts = {"TP": 0, "TN": 0, "FP": 0, "FN": 0, "ERR": 0}
        changed = 0
        for r in results:
            v = getattr(r, f"{model}_verdict", "")
            if v in verdicts:
                verdicts[v] += 1
            if getattr(r, f"{model}_changed", False):
                changed += 1
        total = sum(v for k, v in verdicts.items() if k != "ERR")
        pass_count = verdicts["TP"] + verdicts["TN"]
        analysis["by_model"][model] = {
            **verdicts,
            "changed": changed,
            "total": len(results),
            "change_rate": round(changed / len(results), 4) if results else 0,
            "pass_rate": round(pass_count / total, 4) if total else 0,
        }

    # Per-dataset breakdown
    for ds in sorted(set(r.dataset for r in results)):
        ds_results = [r for r in results if r.dataset == ds]
        ds_analysis = {"total": len(ds_results)}
        for model in ("spelling", "grammar", "punctuation"):
            verdicts = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
            changed = 0
            for r in ds_results:
                v = getattr(r, f"{model}_verdict", "")
                if v in verdicts:
                    verdicts[v] += 1
                if getattr(r, f"{model}_changed", False):
                    changed += 1
            total = sum(verdicts.values())
            pass_count = verdicts["TP"] + verdicts["TN"]
            ds_analysis[model] = {
                **verdicts,
                "changed": changed,
                "change_rate": round(changed / len(ds_results), 4) if ds_results else 0,
                "pass_rate": round(pass_count / total, 4) if total else 0,
            }
        analysis["by_dataset"][ds] = ds_analysis

    return analysis


def print_analysis(analysis: dict, results: List[RawModelResult]):
    print(f"\n{'='*60}")
    print("LEVEL 1: RAW MODEL ANALYSIS")
    print(f"{'='*60}")

    # Per-model summary
    print(f"\n## Per-Model Summary ({analysis['total']} tests)")
    print(f"| Model       | Changed | TP  | TN  | FP  | FN  | ChgRate | Pass%  |")
    print(f"|-------------|---------|-----|-----|-----|-----|---------|--------|")
    for model, data in analysis["by_model"].items():
        cr = data['change_rate'] * 100
        pr = data['pass_rate'] * 100
        print(f"| {model:<11} | {data['changed']:>7} | {data['TP']:>3} | {data['TN']:>3} "
              f"| {data['FP']:>3} | {data['FN']:>3} | {cr:5.1f}%  | {pr:5.1f}% |")

    # Per-dataset breakdown
    print(f"\n## Per-Dataset × Model Pass Rate")
    print(f"| Dataset      | Total | S-Pass% | G-Pass% | P-Pass% | S-Chg% | G-Chg% | P-Chg% |")
    print(f"|--------------|-------|---------|---------|---------|--------|--------|--------|")
    for ds in sorted(analysis["by_dataset"].keys()):
        d = analysis["by_dataset"][ds]
        sp = d["spelling"]["pass_rate"] * 100
        gp = d["grammar"]["pass_rate"] * 100
        pp = d["punctuation"]["pass_rate"] * 100
        sc = d["spelling"]["change_rate"] * 100
        gc = d["grammar"]["change_rate"] * 100
        pc = d["punctuation"]["change_rate"] * 100
        print(f"| {ds:<12} | {d['total']:>5} | {sp:5.1f}%  | {gp:5.1f}%  | {pp:5.1f}%  "
              f"| {sc:4.1f}%  | {gc:4.1f}%  | {pc:4.1f}%  |")

    # Word-level edit summary (top FP edits)
    print(f"\n## Top FP Word Edits (model changed text incorrectly)")
    for model in ("spelling", "grammar", "punctuation"):
        fp_edits = []
        for r in results:
            if getattr(r, f"{model}_verdict") == "FP":
                edits = getattr(r, f"{model}_edits", "")
                if edits:
                    fp_edits.append(f"  {r.id}: {edits}")
        if fp_edits:
            print(f"\n  [{model.upper()}] {len(fp_edits)} FP cases:")
            for e in fp_edits[:10]:  # Show first 10
                print(e)


def main():
    parser = argparse.ArgumentParser(description="Level 1: Raw Model Tests")
    parser.add_argument("--url", default="https://bayan10-bayan-api.hf.space")
    parser.add_argument("--dataset", default=None, help="Filter to single dataset")
    args = parser.parse_args()

    api = APIClient(args.url)
    datasets = load_datasets(args.dataset)

    print(f"\n{'='*60}")
    print("BAYAN v2.0 — Level 1: Raw Model Tests")
    print(f"{'='*60}")
    print(f"  Target:   {args.url}")
    print(f"  Datasets: {list(datasets.keys())}")
    print(f"  Total:    {sum(len(v) for v in datasets.values())} tests")
    print(f"{'='*60}")

    results = run_level1(api, datasets)
    analysis = analyze_results(results)
    print_analysis(analysis, results)

    # Save results
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "level1_raw_results.json"
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": args.url,
        "analysis": analysis,
        "results": [asdict(r) for r in results],
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[L1] Results → {out_path}")


if __name__ == "__main__":
    main()
