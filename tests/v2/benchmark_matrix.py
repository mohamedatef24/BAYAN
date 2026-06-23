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


def print_comparison_matrix():
    """Load all 3 reports and print side-by-side comparison."""
    l1 = load_report(1)
    l2 = load_report(2)
    l3 = load_report(3)

    print(f"\n{'='*70}")
    print("BAYAN v2.0 — BENCHMARK COMPARISON MATRIX")
    print(f"{'='*70}")

    # Timestamps
    for level, report, name in [(1, l1, "L1-Raw"), (2, l2, "L2-Solo"), (3, l3, "L3-Pipeline")]:
        if report:
            ts = report.get("timestamp", "N/A")
            print(f"  {name}: {ts}")
        else:
            print(f"  {name}: NOT RUN")

    # ── Level 1 Summary ──
    if l1:
        print(f"\n{'─'*70}")
        print("Level 1: RAW MODEL OUTPUT (no filters)")
        print(f"{'─'*70}")
        a = l1.get("analysis", {})
        by_model = a.get("by_model", {})
        for model, data in by_model.items():
            changed = data.get("changed", 0)
            unchanged = data.get("unchanged", 0)
            total = changed + unchanged + data.get("errors", 0)
            rate = changed / total * 100 if total else 0
            print(f"  {model:<12}: {changed}/{total} texts modified ({rate:.1f}%)")

    # ── Level 2 Summary ──
    if l2:
        print(f"\n{'─'*70}")
        print("Level 2: SOLO API (single model + filters, no integration)")
        print(f"{'─'*70}")
        a = l2.get("analysis", {})
        by_model = a.get("by_model", {})
        print(f"  {'Model':<12} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} {'Pass%':>7}")
        print(f"  {'-'*12} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*7}")
        for model, data in by_model.items():
            pr = data.get("pass_rate", 0) * 100
            print(f"  {model:<12} {data.get('TP',0):>4} {data.get('TN',0):>4} "
                  f"{data.get('FP',0):>4} {data.get('FN',0):>4} {pr:>6.1f}%")

    # ── Level 3 Summary ──
    if l3:
        print(f"\n{'─'*70}")
        print("Level 3: INTEGRATED PIPELINE (full Spelling→Grammar→Punctuation)")
        print(f"{'─'*70}")
        a = l3.get("analysis", {})
        agg = a.get("aggregate", {})
        total = a.get("total", 0)
        pr = agg.get("pass_rate", 0) * 100
        print(f"  Overall: {pr:.1f}% pass ({total} tests)")
        print(f"  TP={agg.get('TP',0)} TN={agg.get('TN',0)} "
              f"FP={agg.get('FP',0)} FN={agg.get('FN',0)}")

        print(f"\n  {'Dataset':<14} {'Pass%':>7} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4}")
        print(f"  {'-'*14} {'-'*7} {'-'*4} {'-'*4} {'-'*4} {'-'*4}")
        by_ds = a.get("by_dataset", {})
        for ds in sorted(by_ds.keys()):
            d = by_ds[ds]
            dp = d.get("pass_rate", 0) * 100
            print(f"  {ds:<14} {dp:>6.1f}% {d.get('TP',0):>4} {d.get('TN',0):>4} "
                  f"{d.get('FP',0):>4} {d.get('FN',0):>4}")

    # ── Cross-Level Comparison ──
    if l2 and l3:
        print(f"\n{'─'*70}")
        print("CROSS-LEVEL COMPARISON: Solo vs Integrated")
        print(f"{'─'*70}")

        l2_ds = l2.get("analysis", {}).get("by_dataset", {})
        l3_ds = l3.get("analysis", {}).get("by_dataset", {})

        all_datasets = sorted(set(list(l2_ds.keys()) + list(l3_ds.keys())))

        print(f"  {'Dataset':<14} {'L2-Spell':>10} {'L2-Gram':>10} {'L2-Punct':>10} {'L3-Pipeline':>12} {'Delta':>7}")
        print(f"  {'-'*14} {'-'*10} {'-'*10} {'-'*10} {'-'*12} {'-'*7}")

        for ds in all_datasets:
            l2d = l2_ds.get(ds, {})
            l3d = l3_ds.get(ds, {})

            l2_s = l2d.get("spelling", {}).get("pass_rate", 0) * 100
            l2_g = l2d.get("grammar", {}).get("pass_rate", 0) * 100
            l2_p = l2d.get("punctuation", {}).get("pass_rate", 0) * 100
            l3_p = l3d.get("pass_rate", 0) * 100

            # Best solo model vs pipeline
            best_solo = max(l2_s, l2_g, l2_p)
            delta = l3_p - best_solo

            delta_str = f"{delta:+.1f}%"
            print(f"  {ds:<14} {l2_s:>9.1f}% {l2_g:>9.1f}% {l2_p:>9.1f}% {l3_p:>11.1f}% {delta_str:>7}")

    # Save comparison
    comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "l1_timestamp": l1.get("timestamp") if l1 else None,
        "l2_timestamp": l2.get("timestamp") if l2 else None,
        "l3_timestamp": l3.get("timestamp") if l3 else None,
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
