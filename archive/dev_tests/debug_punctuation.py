import sys
import io
from pathlib import Path

# Force UTF-8 encoding for standard output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to python path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

from app import app

client = app.test_client()

def test(text):
    print(f"\n--- Testing: {text} ---")
    resp = client.post('/api/analyze', json={'text': text})
    data = resp.get_json()
    
    if data and 'corrected' in data:
        print(f"Corrected: {data['corrected']}")
        
    if data and 'suggestions' in data:
        for s in data['suggestions']:
            print(f"[{s['type'].upper()}] '{s['original']}' -> '{s['correction']}'")
    elif data and 'error' in data:
        print("Error:", data['error'])
    else:
        print("Raw Data:", data)

if __name__ == "__main__":
    # Test 1: Single Entity (Should not have punctuation added)
    test("شركة أبل")
    
    # Test 2: Short phrase (Should not have punctuation added)
    test("مرحبا بكم في التطبيق")
    
    # Test 3: Grammar error that gets fixed but then corrupted by punctuation
    # "الى" is spelled wrong (needs hamza on alif below if it's إِلى or just remains الى depending on rules, 
    # but let's see what grammar does). Actually "يذهبون المهندسون" is a grammar error in Arabic 
    # (should be يذهب المهندسون).
    test("يذهبون المهندسون الى الشركة")
    
    # Test 4: Verify Grammar Model preserves punctuation
    test("يذهبون المهندسون الى الشركة، أليس كذلك؟")
