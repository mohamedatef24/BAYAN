"""
Phase 11 — Tasks 2, 3, 4, 6, 7: Analysis Suite

Consumes telemetry.jsonl from Task 8 and produces all Phase 11 reports:
- Task 2: FN Root Cause Classification (grammar_fn_analysis)
- Task 3: G028 Deep Investigation (G028_root_cause)
- Task 4: Rejection Matrix (rejection_matrix)
- Task 6: StageLocker Audit (stagelocker_audit)
- Task 7: PatchSet Audit (patchset_audit)
- Filter Telemetry Report (filter_telemetry)

Usage:
    python tests/phase11/analysis_suite.py

Requires: tests/phase11/artifacts/telemetry.jsonl (from telemetry_capture.py)
          tests/phase10/reports/phase10_results.json (from benchmark_runner.py)
"""
import json
import os
import sys
import glob

PHASE11_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(PHASE11_DIR, 'artifacts')
REPORTS_DIR = os.path.join(PHASE11_DIR, 'reports')
PHASE10_RESULTS = os.path.join(PHASE11_DIR, '..', 'phase10', 'reports', 'phase10_results.json')

os.makedirs(REPORTS_DIR, exist_ok=True)


def load_telemetry():
    """Load telemetry.jsonl"""
    path = os.path.join(ARTIFACTS_DIR, 'telemetry.jsonl')
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run telemetry_capture.py first.")
        sys.exit(1)
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_phase10_results():
    """Load phase10 benchmark results."""
    path = os.path.abspath(PHASE10_RESULTS)
    if not os.path.exists(path):
        print(f"WARNING: {path} not found. Some analyses will be incomplete.")
        return None
    return json.load(open(path, encoding='utf-8'))


# ══════════════════════════════════════════════════════════════════
# Task 1 — Filter Telemetry Report
# ══════════════════════════════════════════════════════════════════

def generate_filter_telemetry(records):
    """Task 1: Measure grammar correction rejection by filter."""
    print("\n[Task 1] Generating filter telemetry...")

    all_events = []
    for rec in records:
        for evt in rec.get('telemetry_events', []):
            evt['sample_id'] = rec['sample_id']
            evt['dataset'] = rec['dataset']
            all_events.append(evt)

    # Count by filter
    filter_counts = {}
    accepted = 0
    total_diffs = 0
    raw_outputs = 0
    rejection_details = []

    for evt in all_events:
        if evt.get('event') == 'grammar_diff':
            total_diffs += 1
        elif evt.get('event') == 'grammar_raw_output':
            raw_outputs += 1
        elif evt.get('event') == 'filter_reject':
            f_name = evt.get('filter', 'Unknown')
            filter_counts[f_name] = filter_counts.get(f_name, 0) + 1
            rejection_details.append(evt)
        elif evt.get('event') == 'patch_accepted':
            accepted += 1

    total_rejected = sum(filter_counts.values())

    # JSON report
    report = {
        'grammar_raw_outputs': raw_outputs,
        'grammar_diffs_generated': total_diffs,
        'accepted': accepted,
        'rejected': total_rejected,
        'rejection_by_filter': dict(sorted(filter_counts.items(), key=lambda x: -x[1])),
        'rejection_details': rejection_details,
    }

    json_path = os.path.join(REPORTS_DIR, 'filter_telemetry.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Markdown report
    md_path = os.path.join(REPORTS_DIR, 'filter_telemetry.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Grammar Filter Telemetry Report\n\n")
        f.write("## Pipeline Funnel\n\n")
        f.write(f"| Stage | Count |\n")
        f.write(f"|---|---|\n")
        f.write(f"| Grammar raw outputs | {raw_outputs} |\n")
        f.write(f"| Diffs extracted | {total_diffs} |\n")
        f.write(f"| **Accepted** | **{accepted}** |\n")
        f.write(f"| **Rejected** | **{total_rejected}** |\n\n")
        f.write("## Rejections by Filter\n\n")
        f.write("| Filter | Rejections | % of Total |\n")
        f.write("|---|---|---|\n")
        for f_name, count in sorted(filter_counts.items(), key=lambda x: -x[1]):
            pct = count / total_rejected * 100 if total_rejected > 0 else 0
            f.write(f"| {f_name} | {count} | {pct:.1f}% |\n")
        f.write(f"\n## Rejection Details\n\n")
        for det in rejection_details:
            f.write(f"- **{det.get('filter')}**: `{det.get('original','')}` → `{det.get('correction','')}` (sample: {det.get('sample_id','')})\n")

    print(f"  Generated: {json_path}")
    print(f"  Generated: {md_path}")
    print(f"  Diffs: {total_diffs}, Accepted: {accepted}, Rejected: {total_rejected}")
    return report


# ══════════════════════════════════════════════════════════════════
# Task 2 — FN Root Cause Classification
# ══════════════════════════════════════════════════════════════════

def generate_fn_classification(records, p10_results):
    """Task 2: Classify every grammar FN into a root cause category."""
    print("\n[Task 2] Generating FN root cause classification...")

    # Get grammar FN samples from phase10 results
    grammar_fns = []
    if p10_results:
        for r in p10_results.get('results', []):
            if r.get('dataset') == 'grammar' and r.get('pipeline_verdict') == 'FN':
                grammar_fns.append(r)

    # Cross-reference with telemetry
    tel_by_id = {r['sample_id']: r for r in records}

    classifications = []
    category_counts = {}

    for fn in grammar_fns:
        sid = fn['id']
        tel = tel_by_id.get(sid, {})
        events = tel.get('telemetry_events', [])

        # Determine classification
        classification = 'UNKNOWN'
        evidence = ''

        # Check if grammar model produced any output change
        raw_outputs = [e for e in events if e.get('event') == 'grammar_raw_output']
        diffs = [e for e in events if e.get('event') == 'grammar_diff']
        rejections = [e for e in events if e.get('event') == 'filter_reject']
        accepted = [e for e in events if e.get('event') == 'patch_accepted']

        if not raw_outputs:
            classification = 'MODEL_FAILURE'
            evidence = 'No grammar raw output event found'
        elif not diffs:
            # Model ran but no diffs extracted
            raw = raw_outputs[0] if raw_outputs else {}
            if raw.get('input', '')[:100] == raw.get('output', '')[:100]:
                classification = 'MODEL_FAILURE'
                evidence = 'Grammar model returned input unchanged'
            else:
                classification = 'DIFF_EXTRACTION_FAILURE'
                evidence = f"Model changed text but get_word_diffs() found 0 diffs"
        elif rejections and not accepted:
            # All diffs were rejected
            filter_names = [r.get('filter', '') for r in rejections]
            if any(f == 'StageLocker' for f in filter_names):
                classification = 'STAGELOCKER_FAILURE'
                evidence = f"Rejected by StageLocker: {[r.get('original','') for r in rejections if r.get('filter')=='StageLocker']}"
            else:
                classification = 'FILTER_FAILURE'
                evidence = f"Rejected by: {', '.join(set(filter_names))}"
        elif accepted:
            # Patches were accepted but output doesn't match expected
            classification = 'PATCH_FAILURE'
            evidence = f"Grammar patch accepted but final output doesn't match expected"
        else:
            classification = 'UNKNOWN'
            evidence = f"Events: {len(events)} total, {len(diffs)} diffs, {len(rejections)} rejections"

        classifications.append({
            'sample_id': sid,
            'input': fn.get('input', '')[:100],
            'expected': fn.get('expected', '')[:100],
            'pipeline_output': fn.get('pipeline_output', '')[:100],
            'classification': classification,
            'evidence': evidence,
            'filter_rejections': [r.get('filter', '') for r in rejections],
            'accepted_patches': len(accepted),
        })
        category_counts[classification] = category_counts.get(classification, 0) + 1

    # JSON report
    json_path = os.path.join(REPORTS_DIR, 'grammar_fn_analysis.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_grammar_fn': len(grammar_fns),
            'category_counts': dict(sorted(category_counts.items(), key=lambda x: -x[1])),
            'classifications': classifications,
        }, f, indent=2, ensure_ascii=False)

    # Markdown report
    md_path = os.path.join(REPORTS_DIR, 'grammar_fn_analysis.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Grammar FN Root Cause Analysis\n\n")
        f.write(f"**Total Grammar FN: {len(grammar_fns)}**\n\n")
        f.write("## By Category\n\n")
        f.write("| Category | Count | % |\n")
        f.write("|---|---|---|\n")
        for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
            pct = cnt / len(grammar_fns) * 100 if grammar_fns else 0
            f.write(f"| {cat} | {cnt} | {pct:.0f}% |\n")
        f.write("\n## Detail\n\n")
        for c in classifications:
            f.write(f"### {c['sample_id']} — {c['classification']}\n")
            f.write(f"- **Input**: `{c['input']}`\n")
            f.write(f"- **Expected**: `{c['expected']}`\n")
            f.write(f"- **Pipeline output**: `{c['pipeline_output']}`\n")
            f.write(f"- **Evidence**: {c['evidence']}\n")
            if c['filter_rejections']:
                f.write(f"- **Filters**: {', '.join(c['filter_rejections'])}\n")
            f.write("\n")

    print(f"  Generated: {json_path}")
    print(f"  Generated: {md_path}")
    print(f"  Total FN: {len(grammar_fns)}, Categories: {category_counts}")
    return classifications


# ══════════════════════════════════════════════════════════════════
# Task 3 — G028 Deep Investigation
# ══════════════════════════════════════════════════════════════════

def generate_g028_trace(records, p10_results):
    """Task 3: Full lifecycle trace of G028."""
    print("\n[Task 3] Generating G028 deep investigation...")

    # Find G028 in telemetry
    g028_tel = None
    for r in records:
        if r.get('sample_id') == 'G028':
            g028_tel = r
            break

    # Find G028 in phase10 results
    g028_p10 = None
    if p10_results:
        for r in p10_results.get('results', []):
            if r.get('id') == 'G028':
                g028_p10 = r
                break

    md_path = os.path.join(REPORTS_DIR, 'G028_root_cause.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# G028 Root Cause Investigation\n\n")

        if not g028_tel:
            f.write("> [!CAUTION]\n> G028 not found in telemetry data.\n\n")
            print("  WARNING: G028 not found in telemetry")
            return

        f.write("## Input\n\n")
        f.write(f"```\n{g028_tel.get('input', 'N/A')}\n```\n\n")

        f.write("## Expected Output\n\n")
        f.write(f"```\n{g028_tel.get('expected', 'N/A')}\n```\n\n")

        f.write("## Pipeline Output\n\n")
        f.write(f"```\n{g028_tel.get('pipeline_output', 'N/A')}\n```\n\n")

        f.write(f"## Pass/Fail: {'✅ PASS' if g028_tel.get('passed') else '❌ FAIL'}\n\n")

        # Telemetry events
        events = g028_tel.get('telemetry_events', [])
        f.write("## Telemetry Events (in order)\n\n")
        f.write("| # | Event | Details |\n")
        f.write("|---|---|---|\n")
        for i, evt in enumerate(events):
            event_type = evt.get('event', '')
            if event_type == 'grammar_raw_output':
                f.write(f"| {i+1} | grammar_raw_output | input=`{evt.get('input','')[:60]}` output=`{evt.get('output','')[:60]}` |\n")
            elif event_type == 'grammar_diff':
                f.write(f"| {i+1} | grammar_diff | `{evt.get('original','')}` → `{evt.get('correction','')}` [{evt.get('start')}-{evt.get('end')}] |\n")
            elif event_type == 'filter_reject':
                f.write(f"| {i+1} | **REJECT** | **{evt.get('filter','')}**: `{evt.get('original','')}` → `{evt.get('correction','')}` |\n")
            elif event_type == 'patch_accepted':
                f.write(f"| {i+1} | patch_accepted | `{evt.get('original','')}` → `{evt.get('correction','')}` [{evt.get('start')}-{evt.get('end')}] |\n")
            else:
                f.write(f"| {i+1} | {event_type} | {json.dumps(evt, ensure_ascii=False)[:80]} |\n")

        # Phase 10 data
        if g028_p10:
            f.write("\n## Phase 10 Benchmark Data\n\n")
            f.write(f"- **Verdict**: {g028_p10.get('pipeline_verdict')}\n")
            f.write(f"- **Root cause stage**: {g028_p10.get('root_cause_stage', 'N/A')}\n")
            f.write(f"- **Root cause detail**: {g028_p10.get('root_cause_detail', 'N/A')}\n")
            f.write(f"- **Suggestions**: {len(g028_p10.get('pipeline_suggestions', []))}\n")
            for s in g028_p10.get('pipeline_suggestions', []):
                f.write(f"  - [{s.get('type')}] `{s.get('original','')}` → `{s.get('correction','')}` (conf={s.get('confidence',0)})\n")

        # Root cause determination
        f.write("\n## Root Cause Determination\n\n")
        raw_outputs = [e for e in events if e.get('event') == 'grammar_raw_output']
        diffs = [e for e in events if e.get('event') == 'grammar_diff']
        rejects = [e for e in events if e.get('event') == 'filter_reject']
        accepts = [e for e in events if e.get('event') == 'patch_accepted']

        if not raw_outputs:
            f.write("**ROOT CAUSE: No grammar output** — Grammar model did not run or returned empty.\n")
        elif raw_outputs:
            raw = raw_outputs[0]
            inp = raw.get('input', '')
            out = raw.get('output', '')
            if inp[:80] == out[:80]:
                f.write("**ROOT CAUSE: MODEL_FAILURE** — Grammar model returned input unchanged. The model did not detect the error.\n")
            elif not diffs:
                f.write("**ROOT CAUSE: DIFF_EXTRACTION_FAILURE** — Model changed text but `get_word_diffs()` failed to extract diffs.\n")
                f.write(f"\n- Model input: `{inp[:100]}`\n")
                f.write(f"- Model output: `{out[:100]}`\n")
            elif rejects and not accepts:
                filters = set(r.get('filter', '') for r in rejects)
                f.write(f"**ROOT CAUSE: FILTER_FAILURE** — Grammar model produced the correct fix but filters rejected it.\n")
                f.write(f"\n- Rejected by: {', '.join(filters)}\n")
                for r in rejects:
                    f.write(f"- `{r.get('original','')}` → `{r.get('correction','')}` (filter: {r.get('filter','')})\n")
            elif accepts:
                f.write("**ROOT CAUSE: PATCH_FAILURE or REBUILD_FAILURE** — Grammar patch was accepted but final output doesn't match expected.\n")
                f.write("\nPossible causes:\n")
                f.write("1. OffsetMapper corrupted patch coordinates during rebuild\n")
                f.write("2. PatchSet conflict resolution dropped the patch\n")
                f.write("3. Rebuild logic (accepted diffs → safe_grammar) lost the change\n")
            else:
                f.write("**ROOT CAUSE: UNKNOWN** — Insufficient telemetry data.\n")

    print(f"  Generated: {md_path}")


# ══════════════════════════════════════════════════════════════════
# Task 4 — Rejection Matrix
# ══════════════════════════════════════════════════════════════════

def generate_rejection_matrix(records, p10_results):
    """Task 4: Measure filter quality — correct vs incorrect rejections."""
    print("\n[Task 4] Generating rejection matrix...")

    # Build lookup: sample_id → passed/failed + expected behavior
    p10_by_id = {}
    if p10_results:
        for r in p10_results.get('results', []):
            p10_by_id[r['id']] = r

    # Collect all rejections
    filter_stats = {}  # filter → {total, correct, incorrect}

    for rec in records:
        sid = rec.get('sample_id', '')
        p10 = p10_by_id.get(sid, {})
        expected_unchanged = (p10.get('expected', '') == p10.get('input', ''))
        is_fp = p10.get('pipeline_verdict') == 'FP'
        is_fn = p10.get('pipeline_verdict') == 'FN'

        for evt in rec.get('telemetry_events', []):
            if evt.get('event') != 'filter_reject':
                continue

            f_name = evt.get('filter', 'Unknown')
            if f_name not in filter_stats:
                filter_stats[f_name] = {'total': 0, 'correct': 0, 'incorrect': 0, 'details': []}

            filter_stats[f_name]['total'] += 1

            # Determine if rejection was correct or incorrect
            # Correct rejection: text was already correct (TN/TP scenario), or
            #                    the proposed correction was wrong
            # Incorrect rejection: text had an error AND the correction was right (FN)
            if expected_unchanged:
                # Text was already correct → rejecting a change is CORRECT
                filter_stats[f_name]['correct'] += 1
            elif is_fn:
                # Text had an error AND pipeline didn't fix it → rejection MIGHT be incorrect
                # Check if this rejection's correction matches expected
                orig = evt.get('original', '')
                corr = evt.get('correction', '')
                expected = p10.get('expected', '')
                if corr in expected and orig not in expected:
                    filter_stats[f_name]['incorrect'] += 1
                    filter_stats[f_name]['details'].append({
                        'sample_id': sid,
                        'original': orig,
                        'correction': corr,
                        'expected': expected[:80],
                    })
                else:
                    filter_stats[f_name]['correct'] += 1
            else:
                # FP or TP — rejection is generally correct
                filter_stats[f_name]['correct'] += 1

    # Markdown report
    md_path = os.path.join(REPORTS_DIR, 'rejection_matrix.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Rejection Matrix\n\n")
        f.write("> For every rejected grammar correction, determine whether rejection was correct or incorrect.\n\n")
        f.write("| Filter | Total Rejections | Correct | Incorrect | Precision |\n")
        f.write("|---|---|---|---|---|\n")
        for f_name, stats in sorted(filter_stats.items(), key=lambda x: -x[1]['total']):
            prec = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
            f.write(f"| {f_name} | {stats['total']} | {stats['correct']} | {stats['incorrect']} | {prec:.0f}% |\n")

        total_all = sum(s['total'] for s in filter_stats.values())
        correct_all = sum(s['correct'] for s in filter_stats.values())
        incorrect_all = sum(s['incorrect'] for s in filter_stats.values())
        prec_all = correct_all / total_all * 100 if total_all > 0 else 0
        f.write(f"| **TOTAL** | **{total_all}** | **{correct_all}** | **{incorrect_all}** | **{prec_all:.0f}%** |\n")

        # Incorrect rejection details
        f.write("\n## Incorrect Rejections (Valid Corrections Blocked)\n\n")
        has_incorrect = False
        for f_name, stats in sorted(filter_stats.items(), key=lambda x: -x[1]['incorrect']):
            for det in stats['details']:
                has_incorrect = True
                f.write(f"- **{f_name}** ({det['sample_id']}): `{det['original']}` → `{det['correction']}` (expected: `{det['expected']}`)\n")
        if not has_incorrect:
            f.write("None detected — all rejections appear correct.\n")

    print(f"  Generated: {md_path}")
    print(f"  Total rejections: {total_all}, Correct: {correct_all}, Incorrect: {incorrect_all}")


# ══════════════════════════════════════════════════════════════════
# Task 6 — StageLocker Audit
# ══════════════════════════════════════════════════════════════════

def generate_stagelocker_audit(records, p10_results):
    """Task 6: Audit StageLocker lock/block behavior."""
    print("\n[Task 6] Generating StageLocker audit...")

    stagelocker_blocks = []
    total_locks = 0  # We can't directly count locks from telemetry, so estimate

    for rec in records:
        for evt in rec.get('telemetry_events', []):
            if evt.get('event') == 'filter_reject' and evt.get('filter') == 'StageLocker':
                stagelocker_blocks.append({
                    'sample_id': rec.get('sample_id', ''),
                    'dataset': rec.get('dataset', ''),
                    'original': evt.get('original', ''),
                    'correction': evt.get('correction', ''),
                })
            if evt.get('event') == 'patch_accepted':
                total_locks += 1  # Each accepted patch creates a lock

    # Count grammar vs punctuation blocks
    grammar_blocks = len(stagelocker_blocks)  # All from grammar stage
    # We'd need punctuation telemetry too for punc blocks

    md_path = os.path.join(REPORTS_DIR, 'stagelocker_audit.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# StageLocker Audit\n\n")
        f.write("## Statistics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|---|---|\n")
        f.write(f"| Total locks created (est.) | {total_locks} |\n")
        f.write(f"| Grammar blocks | {grammar_blocks} |\n")
        f.write(f"\n## Grammar Blocks Detail\n\n")
        if stagelocker_blocks:
            f.write("| Sample | Original | Correction |\n")
            f.write("|---|---|---|\n")
            for b in stagelocker_blocks:
                f.write(f"| {b['sample_id']} | `{b['original']}` | `{b['correction']}` |\n")
        else:
            f.write("No StageLocker blocks detected in grammar stage.\n")

    print(f"  Generated: {md_path}")
    print(f"  Total locks: {total_locks}, Grammar blocks: {grammar_blocks}")


# ══════════════════════════════════════════════════════════════════
# Task 7 — PatchSet Audit
# ══════════════════════════════════════════════════════════════════

def generate_patchset_audit(records, p10_results):
    """Task 7: Audit PatchSet conflict resolution."""
    print("\n[Task 7] Generating PatchSet audit...")

    total_patches = 0
    total_conflicts = 0
    ownership_by_stage = {}

    if p10_results:
        for r in p10_results.get('results', []):
            suggestions = r.get('pipeline_suggestions', [])
            for s in suggestions:
                stage = s.get('type', 'unknown')
                ownership_by_stage[stage] = ownership_by_stage.get(stage, 0) + 1
                total_patches += 1

    # Check for conflicts (overlapping patches from different stages)
    if p10_results:
        for r in p10_results.get('results', []):
            suggestions = r.get('pipeline_suggestions', [])
            for i, s1 in enumerate(suggestions):
                for j, s2 in enumerate(suggestions):
                    if i >= j:
                        continue
                    if s1.get('start', 0) < s2.get('end', 0) and s1.get('end', 0) > s2.get('start', 0):
                        if s1.get('type') != s2.get('type'):
                            total_conflicts += 1

    md_path = os.path.join(REPORTS_DIR, 'patchset_audit.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# PatchSet Audit\n\n")
        f.write("## Statistics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|---|---|\n")
        f.write(f"| Total patches generated | {total_patches} |\n")
        f.write(f"| Total cross-stage conflicts | {total_conflicts} |\n")
        f.write(f"\n## Patch Ownership by Stage\n\n")
        f.write("| Stage | Patches |\n")
        f.write("|---|---|\n")
        for stage, count in sorted(ownership_by_stage.items(), key=lambda x: -x[1]):
            f.write(f"| {stage} | {count} |\n")

    print(f"  Generated: {md_path}")
    print(f"  Total patches: {total_patches}, Conflicts: {total_conflicts}")


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════

def main():
    print("Phase 11 Analysis Suite")
    print("=" * 60)

    records = load_telemetry()
    p10_results = load_phase10_results()

    print(f"Loaded {len(records)} telemetry records")
    if p10_results:
        print(f"Loaded phase10 results: {len(p10_results.get('results', []))} samples")

    # Run all analysis tasks
    tel_report = generate_filter_telemetry(records)
    fn_class = generate_fn_classification(records, p10_results)
    generate_g028_trace(records, p10_results)
    generate_rejection_matrix(records, p10_results)
    generate_stagelocker_audit(records, p10_results)
    generate_patchset_audit(records, p10_results)

    print(f"\n{'='*60}")
    print(f"All reports generated in: {REPORTS_DIR}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
