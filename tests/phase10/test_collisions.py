"""
Phase 11 — Pipeline Collision Test Runner
==========================================
Runs ALL collision test cases against the live API and produces
a structured JSON report with per-failure classification.
"""
import json
import sys
import time
import re
import requests
from pathlib import Path

# ── Configuration ──
API_URL = "https://bayan10-bayan-api.hf.space/api/analyze"
DATASET_PATH = Path(__file__).parent / "gold_datasets" / "pipeline_collision.json"
REPORT_PATH = Path(__file__).parent / "reports" / "collision_report.json"

def strip_diacritics(text):
    """Remove Arabic diacritics for comparison."""
    return re.sub(r'[\u064B-\u065F\u0670]', '', text)

def normalize_for_compare(text):
    """Normalize text for fuzzy comparison (strip diacritics + collapse spaces)."""
    t = strip_diacritics(text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def classify_failure(sample, actual, suggestions):
    """Classify root cause for a failure."""
    expected = sample["expected"]
    inp = sample["input"]
    category = sample.get("category", "")

    # Check which words are wrong
    exp_words = set(expected.split())
    act_words = set(actual.split())
    inp_words = set(inp.split())
    missing_fixes = exp_words - act_words  # Expected words not in actual
    unwanted = act_words - exp_words       # Actual words not in expected

    # Check suggestion stages
    stages = [s.get('type', '') for s in suggestions]
    has_spelling = 'spelling' in stages
    has_grammar = 'grammar' in stages
    has_punctuation = 'punctuation' in stages

    # Determine root cause
    if category == "spelling_blocks_grammar":
        # Spelling fixed ه→ة but locked the range, grammar couldn't fix gender
        if any(s.get('type') == 'spelling' for s in suggestions):
            grammar_words_missed = [w for w in missing_fixes if w not in inp_words]
            if grammar_words_missed:
                return "STAGELOCKER", "spelling→grammar lock collision", grammar_words_missed
        return "MODEL", "Grammar model missed correction", list(missing_fixes)

    elif category == "grammar_drops_spelling":
        return "PIPELINE", "Grammar stage dropped spelling fix", list(missing_fixes)

    elif category == "spelling_grammar_overlap":
        return "PIPELINE", "Spelling and grammar overlap conflict", list(missing_fixes)

    elif category == "multi_stage_collision":
        if not has_grammar and missing_fixes:
            return "MODEL", "Grammar model missed correction", list(missing_fixes)
        elif has_spelling and not has_grammar:
            return "STAGELOCKER", "Spelling lock blocked grammar", list(missing_fixes)
        return "PIPELINE", "Multi-stage interaction failure", list(missing_fixes)

    else:
        return "UNKNOWN", f"Unclassified failure in category '{category}'", list(missing_fixes)


def main():
    # Load dataset
    if not DATASET_PATH.exists():
        print(f"❌ Dataset not found: {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        samples = json.load(f)

    print(f"[COLLISION] Running {len(samples)} test cases against {API_URL}")
    print(f"{'='*70}")

    results = []
    passed = 0
    failed = 0
    errors = 0

    for i, s in enumerate(samples):
        sid = s["id"]
        print(f"  [{i+1}/{len(samples)}] {sid} ({s.get('category','')})... ", end="", flush=True)

        try:
            t0 = time.time()
            r = requests.post(API_URL, json={"text": s["input"]}, timeout=120)
            elapsed_ms = int((time.time() - t0) * 1000)
            resp = r.json()
            actual = resp.get("corrected", "")
            suggestions = resp.get("suggestions", [])

            # Normalize for comparison (strip diacritics, collapse spaces)
            norm_actual = normalize_for_compare(actual)
            norm_expected = normalize_for_compare(s["expected"])

            result = {
                "id": sid,
                "category": s.get("category", ""),
                "input": s["input"],
                "expected": s["expected"],
                "actual": actual,
                "suggestions": suggestions,
                "elapsed_ms": elapsed_ms,
            }

            if norm_actual == norm_expected:
                result["verdict"] = "PASS"
                passed += 1
                print(f"✅ PASS ({elapsed_ms}ms)")
            else:
                result["verdict"] = "FAIL"
                component, detail, missing = classify_failure(s, actual, suggestions)
                result["root_cause_component"] = component
                result["root_cause_detail"] = detail
                result["missing_words"] = missing
                failed += 1
                print(f"❌ FAIL ({elapsed_ms}ms)")
                print(f"       Input:    {s['input']}")
                print(f"       Expected: {s['expected']}")
                print(f"       Actual:   {actual}")
                print(f"       Cause:    [{component}] {detail}")

            results.append(result)

        except Exception as e:
            errors += 1
            results.append({
                "id": sid, "category": s.get("category", ""),
                "verdict": "ERROR", "error": str(e),
            })
            print(f"💥 ERROR: {e}")

    # ── Summary ──
    total = len(samples)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n{'='*70}")
    print(f"COLLISION BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"  Total:     {total}")
    print(f"  Passed:    {passed}")
    print(f"  Failed:    {failed}")
    print(f"  Errors:    {errors}")
    print(f"  Pass Rate: {pass_rate:.1f}%")

    # ── Root cause breakdown ──
    failures = [r for r in results if r.get("verdict") == "FAIL"]
    by_component = {}
    by_category = {}
    for r in failures:
        comp = r.get("root_cause_component", "UNKNOWN")
        cat = r.get("category", "unknown")
        by_component[comp] = by_component.get(comp, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1

    if failures:
        print(f"\n  Root Cause by Component:")
        for comp, count in sorted(by_component.items(), key=lambda x: -x[1]):
            print(f"    {comp}: {count}")
        print(f"\n  Failures by Category:")
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count}")

    # ── Save report ──
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": API_URL,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": round(pass_rate, 1),
        "root_cause_by_component": by_component,
        "failures_by_category": by_category,
        "results": results,
    }
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[COLLISION] Report saved → {REPORT_PATH}")


if __name__ == "__main__":
    main()
