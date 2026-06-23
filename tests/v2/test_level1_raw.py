"""
BAYAN v2.0 — Level 1: Raw Model Tests
======================================
Tests each ML model DIRECTLY — no filters, no pipeline, no StageLocker.
Measures the raw model ceiling: what's the best each model can do?

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
    # Analysis
    spelling_changed: bool = False
    grammar_changed: bool = False
    punctuation_changed: bool = False


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
        """Call /api/spelling — raw spelling model through API."""
        data, ms = self._post("/api/spelling", text)
        corrected = data.get("corrected_text", data.get("corrected", text))
        return corrected, ms

    def grammar_raw(self, text):
        """Call /api/grammar — raw grammar model through API."""
        data, ms = self._post("/api/grammar", text)
        corrected = data.get("corrected_text", data.get("corrected", text))
        return corrected, ms

    def punctuation_raw(self, text):
        """Call /api/punctuation — raw punctuation model through API."""
        data, ms = self._post("/api/punctuation", text)
        corrected = data.get("corrected_text", data.get("corrected", text))
        return corrected, ms


def load_datasets(dataset_filter=None):
    """Load all gold datasets."""
    datasets = {}
    for f in sorted(DATASETS_DIR.glob("*.json")):
        name = f.stem
        if dataset_filter and name != dataset_filter:
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            datasets[name] = data
    return datasets


def strip_diacritics(text):
    return re.sub(r'[\u064B-\u065F\u0670]', '', text)


def normalize(text):
    t = strip_diacritics(text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def run_level1(api: APIClient, datasets: dict) -> List[RawModelResult]:
    """Run each test case through all 3 raw models."""
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
            except Exception as e:
                r.spelling_raw = f"ERROR: {e}"

            # ── Grammar ──
            try:
                r.grammar_raw, r.grammar_ms = api.grammar_raw(inp)
                r.grammar_changed = (normalize(r.grammar_raw) != normalize(inp))
            except Exception as e:
                r.grammar_raw = f"ERROR: {e}"

            # ── Punctuation ──
            try:
                r.punctuation_raw, r.punctuation_ms = api.punctuation_raw(inp)
                r.punctuation_changed = (normalize(r.punctuation_raw) != normalize(inp))
            except Exception as e:
                r.punctuation_raw = f"ERROR: {e}"

            total_ms = r.spelling_ms + r.grammar_ms + r.punctuation_ms
            changes = []
            if r.spelling_changed: changes.append("S")
            if r.grammar_changed: changes.append("G")
            if r.punctuation_changed: changes.append("P")
            change_str = "+".join(changes) if changes else "none"
            print(f"[{change_str}] ({total_ms}ms)")

            results.append(r)

    return results


def analyze_results(results: List[RawModelResult]) -> dict:
    """Produce per-model analysis of raw outputs."""
    analysis = {
        "total": len(results),
        "by_model": {
            "spelling": {"changed": 0, "unchanged": 0, "errors": 0},
            "grammar": {"changed": 0, "unchanged": 0, "errors": 0},
            "punctuation": {"changed": 0, "unchanged": 0, "errors": 0},
        },
        "by_dataset": {},
    }

    for r in results:
        ds = r.dataset
        if ds not in analysis["by_dataset"]:
            analysis["by_dataset"][ds] = {
                "total": 0,
                "spelling_changed": 0,
                "grammar_changed": 0,
                "punctuation_changed": 0,
            }
        analysis["by_dataset"][ds]["total"] += 1

        # Spelling
        if "ERROR" in r.spelling_raw:
            analysis["by_model"]["spelling"]["errors"] += 1
        elif r.spelling_changed:
            analysis["by_model"]["spelling"]["changed"] += 1
            analysis["by_dataset"][ds]["spelling_changed"] += 1
        else:
            analysis["by_model"]["spelling"]["unchanged"] += 1

        # Grammar
        if "ERROR" in r.grammar_raw:
            analysis["by_model"]["grammar"]["errors"] += 1
        elif r.grammar_changed:
            analysis["by_model"]["grammar"]["changed"] += 1
            analysis["by_dataset"][ds]["grammar_changed"] += 1
        else:
            analysis["by_model"]["grammar"]["unchanged"] += 1

        # Punctuation
        if "ERROR" in r.punctuation_raw:
            analysis["by_model"]["punctuation"]["errors"] += 1
        elif r.punctuation_changed:
            analysis["by_model"]["punctuation"]["changed"] += 1
            analysis["by_dataset"][ds]["punctuation_changed"] += 1
        else:
            analysis["by_model"]["punctuation"]["unchanged"] += 1

    return analysis


def print_analysis(analysis: dict):
    print(f"\n{'='*60}")
    print("LEVEL 1: RAW MODEL ANALYSIS")
    print(f"{'='*60}")

    print(f"\n## Per-Model Summary ({analysis['total']} tests)")
    print(f"| Model       | Changed | Unchanged | Errors |")
    print(f"|-------------|---------|-----------|--------|")
    for model, data in analysis["by_model"].items():
        print(f"| {model:<11} | {data['changed']:>7} | {data['unchanged']:>9} | {data['errors']:>6} |")

    print(f"\n## Change Rate by Dataset")
    print(f"| Dataset      | Total | S-Changed | G-Changed | P-Changed |")
    print(f"|--------------|-------|-----------|-----------|-----------|")
    for ds, data in sorted(analysis["by_dataset"].items()):
        print(f"| {ds:<12} | {data['total']:>5} | {data['spelling_changed']:>9} | {data['grammar_changed']:>9} | {data['punctuation_changed']:>9} |")


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
    print_analysis(analysis)

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
