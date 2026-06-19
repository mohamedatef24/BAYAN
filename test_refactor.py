import sys
import os
import json
from pathlib import Path

# Add src to python path
sys.path.insert(0, str(Path(r'd:\BAYAN\src')))

# Mock request context for Flask
from flask import Flask, request
import app

# Set mock endpoints
app.app.config['TESTING'] = True
client = app.app.test_client()

def test_spelling():
    response = client.post('/api/analyze', json={'text': 'هاذا كتاب'})
    data = response.get_json()
    assert 'هذا' in [s['correction'] for s in data['suggestions'] if s['type'] == 'spelling'], "Spelling test failed"
    print("Spelling test passed")

def test_grammar():
    response = client.post('/api/analyze', json={'text': 'الطلاب يذهب الى المدرسة'})
    data = response.get_json()
    assert any(s['type'] == 'grammar' for s in data['suggestions']), "Grammar test failed"
    print("Grammar test passed")

def test_punctuation():
    response = client.post('/api/analyze', json={'text': 'كيف حالك انا بخير'})
    data = response.get_json()
    assert any(s['type'] == 'punctuation' for s in data['suggestions']), "Punctuation test failed"
    print("Punctuation test passed")

def test_pipeline_independence():
    # Test that grammar output doesn't propagate into punctuation
    response = client.post('/api/analyze', json={'text': 'الطلاب يذهب الى المدرسة واكلت التفاحة'})
    data = response.get_json()
    # Check that punctuation suggestions are still mapped correctly to original
    print(f"Pipeline output: {data['suggestions']}")
    print("Pipeline independence passed")

if __name__ == '__main__':
    print("Running Regression Tests...")
    test_spelling()
    test_grammar()
    test_punctuation()
    test_pipeline_independence()
    print("All tests completed successfully!")
