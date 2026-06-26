import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
# Add src to python path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

from app import app
import json

client = app.test_client()

def test(text):
    print(f"\n--- Testing: {text} ---")
    resp = client.post('/api/analyze', json={'text': text})
    data = resp.get_json()
    if 'suggestions' in data:
        for s in data['suggestions']:
            print(f"[{s['type'].upper()}] '{s['original']}' -> '{s['correction']}'")
    else:
        print("Error:", data)

test("ذهبت المهندسون الي العمل")
test("ذهبت المهندسون")
test("الي العمل")
