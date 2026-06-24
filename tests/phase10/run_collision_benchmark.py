"""
Phase 11 — Collision Benchmark Runner
======================================
Integrates with the benchmark_runner.py API client pattern.
Produces a Markdown/CLI table report with pass/fail rates and root causes.

Usage:
    python tests/phase10/run_collision_benchmark.py [--url URL]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List

# Reuse API client from benchmark_runner
sys.path.insert(0, str(Path(__file__).parent))
from benchmark_runner import API, BenchResult, calc_metrics, strip_punct_only

GOLD_DIR = Path(__file__).parent / "gold_datasets"
REPORT_DIR = Path(__file__).parent / "reports"
DEFAULT_URL = "https://bayan10-bayan-api.hf.space"


def _strip_diacritics(text):
    return re.sub(r'[\u064B-\u065F\u0670]', '', text)


def _normalize(text):
    """Normalize for comparison: strip diacritics + trailing punct + collapse whitespace."""
    text = _strip_diacritics(text)
    text = text.rstrip('.،؛؟!?!')  # Terminal punct is not a correctness criterion
    return re.sub(r'\s+', ' ', text).strip()


def run_collision_benchmark(api: API, samples: list) -> List[BenchResult]:
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['id']} ({s.get('category','')})... ", end="", flush=True)
        r = BenchResult(
            s['id'], 'collision', s.get('category', ''), s['input'],
            expected=s.get('expected', ''), severity=s.get('severity', '')
        )

        resp = api.analyze(s['input'])
        r.pipeline_ms = resp.get('_ms', 0)
        r.pipeline_timing = resp.get('timing_ms', {})

        if 'error' in resp:
            r.pipeline_verdict = "ERROR"
            r.pipeline_detail = resp.get('error', '')
            print(f"💥 ERROR")
            results.append(r)
            continue

        r.pipeline_output = resp.get('corrected', '')
        r.pipeline_suggestions = resp.get('suggestions', [])
        original = resp.get('original', s['input'])

        # Normalize for comparison
        norm_output = _normalize(r.pipeline_output)
        norm_expected = _normalize(s.get('expected', ''))

        if norm_output == norm_expected:
            r.pipeline_verdict = "TP"
            r.pipeline_detail = "All corrections applied correctly"
        else:
            # Classify the failure
            category = s.get('category', '')
            stages = [sg.get('type', '') for sg in r.pipeline_suggestions]

            if category == 'spelling_blocks_grammar':
                if 'spelling' in stages and 'grammar' not in stages:
                    r.root_cause_component = "PIPELINE"
                    r.root_cause_stage = "integration"
                    r.root_cause_detail = "Spelling lock blocked grammar correction (StageLocker)"
                else:
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "grammar"
                    r.root_cause_detail = "Grammar model missed gender agreement correction"
            elif category == 'grammar_drops_spelling':
                r.root_cause_component = "PIPELINE"
                r.root_cause_stage = "integration"
                r.root_cause_detail = "Grammar stage dropped spelling fix"
            elif category == 'spelling_grammar_overlap':
                r.root_cause_component = "PIPELINE"
                r.root_cause_stage = "integration"
                r.root_cause_detail = "Spelling and grammar corrections overlapped"
            elif category == 'multi_stage_collision':
                if not any(t == 'grammar' for t in stages):
                    r.root_cause_component = "MODEL"
                    r.root_cause_stage = "grammar"
                    r.root_cause_detail = "Grammar model missed SV/gender agreement"
                else:
                    r.root_cause_component = "PIPELINE"
                    r.root_cause_stage = "integration"
                    r.root_cause_detail = "Multi-stage interaction failure"
            elif category == 'three_stage_collision':
                r.root_cause_component = "PIPELINE"
                r.root_cause_stage = "integration"
                r.root_cause_detail = "Three-stage collision: spelling+grammar+punctuation"
            elif category == 'punctuation_near_spelling':
                r.root_cause_component = "MODEL"
                r.root_cause_stage = "spelling"
                r.root_cause_detail = "Spelling correction near punctuation boundary"
            elif category == 'adjacent_corrections':
                r.root_cause_component = "PIPELINE"
                r.root_cause_stage = "integration"
                r.root_cause_detail = "Adjacent word corrections interfered"
            else:
                r.root_cause_component = "UNKNOWN"
                r.root_cause_stage = "unknown"
                r.root_cause_detail = f"Unclassified failure in {category}"

            # Check what's wrong specifically
            exp_words = set(norm_expected.split())
            act_words = set(norm_output.split())
            missing = exp_words - act_words
            extra = act_words - exp_words

            r.pipeline_verdict = "FN"
            r.pipeline_detail = (
                f"Missing: {list(missing)[:5]}, Extra: {list(extra)[:5]}"
                if missing or extra
                else f"Output mismatch: '{r.pipeline_output[:60]}' vs '{s['expected'][:60]}'"
            )

        # Span check
        for sg in r.pipeline_suggestions:
            actual_slice = original[sg['start']:sg['end']]
            if actual_slice != sg.get('original', ''):
                r.span_valid = False
                r.span_detail = f"SPAN[{sg['start']}:{sg['end']}] exp='{sg.get('original','')}' got='{actual_slice}'"
                break

        icon = {"TP": "✅", "TN": "✅", "FP": "❌", "FN": "⚠️", "ERROR": "💥"}.get(r.pipeline_verdict, "?")
        print(f"{icon} {r.pipeline_verdict} ({r.pipeline_ms}ms)")
        results.append(r)

    return results


def main():
    parser = argparse.ArgumentParser(description="Phase 11 Collision Benchmark")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    api = API(args.url)
    dataset_path = GOLD_DIR / "pipeline_collision.json"

    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        sys.exit(1)

    with open(dataset_path, 'r', encoding='utf-8') as f:
        samples = json.load(f)

    print(f"\n{'='*60}")
    print(f"COLLISION BENCHMARK ({len(samples)} samples)")
    print(f"Target: {args.url}")
    print(f"{'='*60}")

    results = run_collision_benchmark(api, samples)
    m = calc_metrics(results)

    # ── Per-category breakdown ──
    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"total": 0, "pass": 0, "fail": 0}
        categories[cat]["total"] += 1
        if r.pipeline_verdict in ("TP", "TN"):
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1

    # ── Print report ──
    print(f"\n{'='*60}")
    print("COLLISION BENCHMARK RESULTS")
    print(f"{'='*60}")
    print(f"\n## Summary")
    print(f"| Metric        | Value |")
    print(f"|---------------|-------|")
    print(f"| Total         | {m['total']} |")
    print(f"| Passed (TP)   | {m['TP']} |")
    print(f"| Failed (FN)   | {m['FN']} |")
    print(f"| FP            | {m['FP']} |")
    print(f"| Errors        | {m['ERROR']} |")
    print(f"| Pass Rate     | {m['pass_rate']:.1%} |")

    print(f"\n## By Category")
    print(f"| Category | Total | Pass | Fail | Rate |")
    print(f"|----------|-------|------|------|------|")
    for cat, data in sorted(categories.items()):
        rate = data['pass'] / data['total'] * 100 if data['total'] > 0 else 0
        print(f"| {cat} | {data['total']} | {data['pass']} | {data['fail']} | {rate:.0f}% |")

    # ── Root cause for failures ──
    failures = [r for r in results if r.pipeline_verdict in ("FN", "FP")]
    if failures:
        print(f"\n## Failure Details")
        print(f"| ID | Category | Input | Expected | Actual | Root Cause |")
        print(f"|----|----------|-------|----------|--------|------------|")
        for r in failures:
            print(
                f"| {r.id} | {r.category} | "
                f"{r.input[:30]}... | {r.expected[:30]}... | "
                f"{r.pipeline_output[:30]}... | {r.root_cause_detail[:40]} |"
            )

    # ── Save JSON report ──
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": args.url,
        "metrics": m,
        "by_category": categories,
        "results": [asdict(r) for r in results],
    }
    out_path = REPORT_DIR / "collision_benchmark_results.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[P11] Report → {out_path}")


if __name__ == "__main__":
    main()
