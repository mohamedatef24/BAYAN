"""
Phase 11 — Task 8: Local Telemetry Capture

Runs all benchmark samples through the pipeline and captures structured
telemetry events from HF logs. Stores telemetry locally as JSONL files.

Usage:
    python tests/phase11/telemetry_capture.py --url https://bayan10-bayan-api.hf.space

Output:
    tests/phase11/artifacts/telemetry.jsonl
    tests/phase11/artifacts/telemetry_summary.json
"""
import argparse
import json
import os
import sys
import time
import re
import requests
import glob

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')
SPACE_ID = 'bayan10/bayan-api'


def load_all_datasets():
    """Load all benchmark samples from gold datasets."""
    datasets_dir = os.path.join(os.path.dirname(__file__), '..', 'phase10', 'gold_datasets')
    samples = []
    for f in sorted(glob.glob(os.path.join(datasets_dir, '*.json'))):
        name = os.path.basename(f).replace('.json', '')
        data = json.load(open(f, encoding='utf-8'))
        items = data if isinstance(data, list) else data.get('samples', [])
        for item in items:
            item['dataset'] = name
        samples.extend(items)
    return samples


def call_analyze(url, text):
    """Call the /api/analyze endpoint."""
    resp = requests.post(
        f"{url}/api/analyze",
        json={"text": text},
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()


def fetch_logs(n_lines=500):
    """Fetch recent HF Spaces logs."""
    url = f"https://api.hf.space/v1/{SPACE_ID}/logs"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        lines = []
        for line in resp.iter_lines(decode_unicode=True):
            if line:
                lines.append(line)
            if len(lines) >= n_lines:
                break
        return lines
    except Exception as e:
        print(f"  [WARN] Failed to fetch logs: {e}")
        return []


def extract_telemetry_events(log_lines):
    """Extract [FILTER-TEL] JSON events from log lines."""
    events = []
    for line in log_lines:
        # Find [FILTER-TEL] markers
        match = re.search(r'\[FILTER-TEL\]\s*(\{.*\})', line)
        if match:
            try:
                event = json.loads(match.group(1))
                events.append(event)
            except json.JSONDecodeError:
                pass
    return events


def run_telemetry_capture(url, max_samples=None):
    """Run all samples and capture telemetry."""
    samples = load_all_datasets()
    if max_samples:
        samples = samples[:max_samples]

    artifacts_dir = os.path.join(os.path.dirname(__file__), 'artifacts')
    os.makedirs(artifacts_dir, exist_ok=True)
    telemetry_path = os.path.join(artifacts_dir, 'telemetry.jsonl')
    summary_path = os.path.join(artifacts_dir, 'telemetry_summary.json')

    all_events = []
    sample_results = []

    print(f"Running telemetry capture on {len(samples)} samples...")
    print(f"URL: {url}")
    print(f"Output: {telemetry_path}")
    print()

    with open(telemetry_path, 'w', encoding='utf-8') as f:
        for i, sample in enumerate(samples):
            sid = sample.get('id', f'UNKNOWN_{i}')
            dataset = sample.get('dataset', 'unknown')
            text = sample.get('input', '')
            expected = sample.get('expected', text)

            print(f"  [{i+1}/{len(samples)}] {sid} ({dataset})...", end=' ', flush=True)

            # Call the API
            try:
                result = call_analyze(url, text)
                pipeline_output = result.get('corrected', text)
                suggestions = result.get('suggestions', [])
                timing = result.get('timing_ms', {})
            except Exception as e:
                print(f"ERROR: {e}")
                sample_results.append({
                    'sample_id': sid,
                    'dataset': dataset,
                    'error': str(e)
                })
                continue

            # Small delay then fetch logs
            time.sleep(0.3)
            log_lines = fetch_logs(200)
            events = extract_telemetry_events(log_lines)

            # Write events for this sample
            sample_record = {
                'sample_id': sid,
                'dataset': dataset,
                'input': text[:200],
                'expected': expected[:200],
                'pipeline_output': pipeline_output[:200],
                'passed': (pipeline_output.strip() == expected.strip()),
                'suggestion_count': len(suggestions),
                'timing': timing,
                'telemetry_events': events
            }
            f.write(json.dumps(sample_record, ensure_ascii=False) + '\n')
            all_events.extend(events)
            sample_results.append(sample_record)

            status = '✅' if sample_record['passed'] else '❌'
            n_events = len(events)
            print(f"{status} ({n_events} events)")

    # Summary
    filter_counts = {}
    accepted_count = 0
    for evt in all_events:
        if evt.get('event') == 'filter_reject':
            f_name = evt.get('filter', 'Unknown')
            filter_counts[f_name] = filter_counts.get(f_name, 0) + 1
        elif evt.get('event') == 'patch_accepted':
            accepted_count += 1

    total_diffs = sum(1 for e in all_events if e.get('event') == 'grammar_diff')
    total_rejections = sum(filter_counts.values())

    summary = {
        'total_samples': len(samples),
        'total_grammar_diffs': total_diffs,
        'total_accepted': accepted_count,
        'total_rejected': total_rejections,
        'rejection_by_filter': dict(sorted(filter_counts.items(), key=lambda x: -x[1])),
        'pass_rate': sum(1 for r in sample_results if r.get('passed', False)) / len(sample_results) * 100 if sample_results else 0,
    }

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"TELEMETRY SUMMARY")
    print(f"{'='*60}")
    print(f"  Samples: {summary['total_samples']}")
    print(f"  Grammar diffs generated: {summary['total_grammar_diffs']}")
    print(f"  Accepted: {summary['total_accepted']}")
    print(f"  Rejected: {summary['total_rejected']}")
    print(f"\n  Rejections by filter:")
    for f_name, count in sorted(filter_counts.items(), key=lambda x: -x[1]):
        print(f"    {f_name}: {count}")
    print(f"\n  Pass rate: {summary['pass_rate']:.1f}%")
    print(f"\n  Saved: {telemetry_path}")
    print(f"  Saved: {summary_path}")

    return summary, sample_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Phase 11 Telemetry Capture')
    parser.add_argument('--url', default='https://bayan10-bayan-api.hf.space')
    parser.add_argument('--max-samples', type=int, default=None)
    args = parser.parse_args()
    run_telemetry_capture(args.url, args.max_samples)
