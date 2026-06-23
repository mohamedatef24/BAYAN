"""
BAYAN v2.0 — Benchmark Matrix Runner
======================================
Master script that runs all 3 test levels and produces a side-by-side
comparison matrix showing raw model vs solo API vs integrated pipeline.

Usage:
    # Full matrix (all 3 levels)
    python tests/v2/benchmark_matrix.py --url URL

    # Single level only
    python tests/v2/benchmark_matrix.py --url URL --level 1
    python tests/v2/benchmark_matrix.py --url URL --level 3

    # Single dataset
    python tests/v2/benchmark_matrix.py --url URL --dataset spelling

    # Compare saved results
    python tests/v2/benchmark_matrix.py --compare
"""
import argparse
import json
import sys
import time
from pathlib import Path

REPORT_DIR = Path(__file__).parent / "reports"


def run_level(level: int, url: str, dataset: str = None):
    """Run a specific test level."""
    import subprocess
    scripts = {
        1: "tests/v2/test_level1_raw.py",
        2: "tests/v2/test_level2_solo.py",
        3: "tests/v2/test_level3_integrated.py",
    }
    script = scripts[level]
    cmd = [sys.executable, script, "--url", url]
    if dataset:
        cmd.extend(["--dataset", dataset])

    print(f"\n{'#'*70}")
    print(f"# RUNNING LEVEL {level}: {script}")
    print(f"{'#'*70}\n")

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent.parent))
    return result.returncode == 0


def load_report(level: int) -> dict:
    """Load saved report for a level."""
    filenames = {
        1: "level1_raw_results.json",
        2: "level2_solo_results.json",
        3: "level3_integrated_results.json",
    }
    path = REPORT_DIR / filenames[level]
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _compute_f1(tp, fp, fn):
    """Compute F1 score from TP/FP/FN."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return round(f1, 4), round(precision, 4), round(recall, 4)


def _extract_model_metrics(report, model_key):
    """Extract TP/TN/FP/FN for a model from a report."""
    a = report.get("analysis", {})
    by_model = a.get("by_model", {})
    data = by_model.get(model_key, {})
    return data.get("TP", 0), data.get("TN", 0), data.get("FP", 0), data.get("FN", 0)


def print_comparison_matrix():
    """Load all 3 reports and print side-by-side comparison."""
    l1 = load_report(1)
    l2 = load_report(2)
    l3 = load_report(3)

    print(f"\n{'='*70}")
    print("BAYAN v2.0 — BENCHMARK COMPARISON MATRIX")
    print(f"{'='*70}")

    for level, report, name in [(1, l1, "L1-Raw"), (2, l2, "L2-Solo"), (3, l3, "L3-Pipeline")]:
        if report:
            ts = report.get("timestamp", "N/A")
            total = report.get("analysis", {}).get("total", "?")
            print(f"  {name}: {ts} ({total} tests)")
        else:
            print(f"  {name}: NOT RUN")

    # ── Level 1 Summary ──
    if l1:
        print(f"\n{'─'*70}")
        print("Level 1: RAW MODEL OUTPUT (through solo API endpoints)")
        print(f"{'─'*70}")
        a = l1.get("analysis", {})
        by_model = a.get("by_model", {})
        print(f"  {'Model':<12} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} {'Pass%':>7} {'ChgRate':>8} {'F1':>6}")
        print(f"  {'-'*12} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*7} {'-'*8} {'-'*6}")
        for model, data in by_model.items():
            tp, tn, fp, fn = data.get("TP",0), data.get("TN",0), data.get("FP",0), data.get("FN",0)
            pr = data.get("pass_rate", 0) * 100
            cr = data.get("change_rate", 0) * 100
            f1, _, _ = _compute_f1(tp, fp, fn)
            print(f"  {model:<12} {tp:>4} {tn:>4} {fp:>4} {fn:>4} {pr:>6.1f}% {cr:>6.1f}%  {f1:.3f}")

    # ── Level 2 Summary ──
    if l2:
        print(f"\n{'─'*70}")
        print("Level 2: SOLO API (single model + filters, no integration)")
        print(f"{'─'*70}")
        a = l2.get("analysis", {})
        by_model = a.get("by_model", {})
        print(f"  {'Model':<12} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} {'Pass%':>7} {'F1':>6}")
        print(f"  {'-'*12} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*7} {'-'*6}")
        for model, data in by_model.items():
            tp, tn, fp, fn = data.get("TP",0), data.get("TN",0), data.get("FP",0), data.get("FN",0)
            pr = data.get("pass_rate", 0) * 100
            f1, _, _ = _compute_f1(tp, fp, fn)
            print(f"  {model:<12} {tp:>4} {tn:>4} {fp:>4} {fn:>4} {pr:>6.1f}% {f1:.3f}")

    # ── Level 3 Summary ──
    if l3:
        print(f"\n{'─'*70}")
        print("Level 3: INTEGRATED PIPELINE (full Spelling→Grammar→Punctuation)")
        print(f"{'─'*70}")
        a = l3.get("analysis", {})
        agg = a.get("aggregate", {})
        total = a.get("total", 0)
        pr = agg.get("pass_rate", 0) * 100
        tp, tn, fp, fn = agg.get("TP",0), agg.get("TN",0), agg.get("FP",0), agg.get("FN",0)
        f1, prec, rec = _compute_f1(tp, fp, fn)
        print(f"  Overall: {pr:.1f}% pass ({total} tests)")
        print(f"  TP={tp} TN={tn} FP={fp} FN={fn}")
        print(f"  F1={f1:.3f}  Precision={prec:.3f}  Recall={rec:.3f}")

        print(f"\n  {'Dataset':<14} {'Pass%':>7} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} {'F1':>6}")
        print(f"  {'-'*14} {'-'*7} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*6}")
        by_ds = a.get("by_dataset", {})
        for ds in sorted(by_ds.keys()):
            d = by_ds[ds]
            dp = d.get("pass_rate", 0) * 100
            dtp, dtn, dfp, dfn = d.get("TP",0), d.get("TN",0), d.get("FP",0), d.get("FN",0)
            df1, _, _ = _compute_f1(dtp, dfp, dfn)
            print(f"  {ds:<14} {dp:>6.1f}% {dtp:>4} {dtn:>4} {dfp:>4} {dfn:>4} {df1:.3f}")

    # ── Cross-Level Comparison ──
    if l1 and l2:
        print(f"\n{'─'*70}")
        print("CROSS-LEVEL: L1 (Raw) vs L2 (Solo) — Filter Impact")
        print(f"{'─'*70}")
        print(f"  {'Model':<12} {'L1-Pass%':>9} {'L2-Pass%':>9} {'Delta':>7} {'L1-F1':>7} {'L2-F1':>7}")
        print(f"  {'-'*12} {'-'*9} {'-'*9} {'-'*7} {'-'*7} {'-'*7}")
        for model in ("spelling", "grammar", "punctuation"):
            l1m = l1.get("analysis",{}).get("by_model",{}).get(model,{})
            l2m = l2.get("analysis",{}).get("by_model",{}).get(model,{})
            l1p = l1m.get("pass_rate",0) * 100
            l2p = l2m.get("pass_rate",0) * 100
            delta = l2p - l1p
            l1f1, _, _ = _compute_f1(l1m.get("TP",0), l1m.get("FP",0), l1m.get("FN",0))
            l2f1, _, _ = _compute_f1(l2m.get("TP",0), l2m.get("FP",0), l2m.get("FN",0))
            print(f"  {model:<12} {l1p:>8.1f}% {l2p:>8.1f}% {delta:>+6.1f}% {l1f1:>6.3f}  {l2f1:>6.3f}")

    if l2 and l3:
        print(f"\n{'─'*70}")
        print("CROSS-LEVEL: L2 (Solo) vs L3 (Pipeline) — Integration Impact")
        print(f"{'─'*70}")

        l2_ds = l2.get("analysis", {}).get("by_dataset", {})
        l3_ds = l3.get("analysis", {}).get("by_dataset", {})
        all_datasets = sorted(set(list(l2_ds.keys()) + list(l3_ds.keys())))

        print(f"  {'Dataset':<14} {'L2-Best':>8} {'L3-Pipe':>8} {'Delta':>7}")
        print(f"  {'-'*14} {'-'*8} {'-'*8} {'-'*7}")

        for ds in all_datasets:
            l2d = l2_ds.get(ds, {})
            l3d = l3_ds.get(ds, {})

            l2_s = l2d.get("spelling", {}).get("pass_rate", 0) * 100
            l2_g = l2d.get("grammar", {}).get("pass_rate", 0) * 100
            l2_p = l2d.get("punctuation", {}).get("pass_rate", 0) * 100
            l3_p = l3d.get("pass_rate", 0) * 100
            best_solo = max(l2_s, l2_g, l2_p)
            delta = l3_p - best_solo
            print(f"  {ds:<14} {best_solo:>7.1f}% {l3_p:>7.1f}% {delta:>+6.1f}%")

    # Save comparison
    comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "l1_timestamp": l1.get("timestamp") if l1 else None,
        "l2_timestamp": l2.get("timestamp") if l2 else None,
        "l3_timestamp": l3.get("timestamp") if l3 else None,
        "l1_summary": l1.get("analysis", {}).get("by_model") if l1 else None,
        "l2_summary": l2.get("analysis", {}).get("by_model") if l2 else None,
        "l3_summary": l3.get("analysis", {}).get("aggregate") if l3 else None,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_DIR / "benchmark_matrix.json", 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    print(f"\n[MATRIX] Comparison → {REPORT_DIR / 'benchmark_matrix.json'}")


def main():
    parser = argparse.ArgumentParser(description="BAYAN v2.0 Benchmark Matrix")
    parser.add_argument("--url", default="https://bayan10-bayan-api.hf.space")
    parser.add_argument("--level", type=int, default=None, help="Run specific level (1/2/3)")
    parser.add_argument("--dataset", default=None, help="Filter to single dataset")
    parser.add_argument("--compare", action="store_true", help="Compare saved results only")
    args = parser.parse_args()

    if args.compare:
        print_comparison_matrix()
        return

    levels = [args.level] if args.level else [1, 2, 3]

    print(f"\n{'#'*70}")
    print(f"# BAYAN v2.0 — BENCHMARK MATRIX")
    print(f"# Levels: {levels}")
    print(f"# Target: {args.url}")
    print(f"{'#'*70}")

    for level in levels:
        success = run_level(level, args.url, args.dataset)
        if not success:
            print(f"\n❌ Level {level} failed!")
            sys.exit(1)
        print(f"\n✅ Level {level} complete!")

    # Print comparison
    print_comparison_matrix()


if __name__ == "__main__":
    main()
