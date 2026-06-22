"""Fetch HF Space runtime logs and extract key events."""
import requests
import json
import sys
import os

SPACE_ID = "bayan10/bayan-api"

def _get_hf_token():
    """Read HF token from stored credentials (huggingface-cli login)."""
    # 1. Environment variable
    token = os.environ.get("HF_TOKEN", "")
    if token:
        return token
    # 2. huggingface_hub stored token
    token_path = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            return f.read().strip()
    return ""

TOKEN = _get_hf_token()

def fetch_logs(max_lines=500):
    """Fetch runtime logs from HF Space."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"https://huggingface.co/api/spaces/{SPACE_ID}/logs/run"
    
    r = requests.get(url, headers=headers, timeout=30, stream=True)
    if r.status_code != 200:
        print(f"Error: {r.status_code}")
        return []
    
    lines = []
    for chunk in r.iter_content(chunk_size=8192, decode_unicode=True):
        for line in chunk.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    lines.append(data.get('data', ''))
                except:
                    pass
        if len(lines) > max_lines:
            break
    return lines

def analyze_logs(lines):
    """Extract key events from logs."""
    errors = []
    grammar_events = []
    spelling_events = []
    startup = []
    
    for line in lines:
        if 'ERROR' in line or 'NameError' in line or 'Traceback' in line:
            errors.append(line)
        elif '[GRAMMAR' in line or 'Grammar' in line:
            grammar_events.append(line)
        elif '[SPELLING' in line:
            spelling_events.append(line)
        elif 'Startup' in line or 'loaded' in line.lower() or 'ready' in line.lower():
            startup.append(line)
    
    print(f"\n{'='*60}")
    print(f"HF SPACE LOG ANALYSIS ({len(lines)} lines)")
    print(f"{'='*60}")
    
    print(f"\n🚀 STARTUP ({len(startup)} events):")
    for e in startup[-5:]:
        print(f"  {e}")
    
    print(f"\n❌ ERRORS ({len(errors)}):")
    if errors:
        for e in errors[-10:]:
            print(f"  {e}")
    else:
        print("  None! ✅")
    
    print(f"\n📝 GRAMMAR ({len(grammar_events)} events, last 5):")
    for e in grammar_events[-5:]:
        print(f"  {e}")
    
    print(f"\n✏️ SPELLING ({len(spelling_events)} events, last 5):")
    for e in spelling_events[-5:]:
        print(f"  {e}")

if __name__ == "__main__":
    lines = fetch_logs()
    analyze_logs(lines)
