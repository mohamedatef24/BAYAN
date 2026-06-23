import sys
import io
from pathlib import Path

# Force UTF-8 encoding for standard output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to python path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

from src.nlp.grammar.grammar_service import get_grammar_model

def test_grammar():
    print("Initializing Grammar Service (No other heavy models loaded)...")
    grammar_checker = get_grammar_model()
    
    test_cases = [
        "يذهبون المهندسون الى الشركة",
        "يذهبون المهندسون الى الشركة، أليس كذلك؟",
        "مرحبا، يا عالم الطيور!",
        "متى يسعون في تطوير مهاراتكم بجد واخلاص تجدون ثمرة ذلك قريبا",
        "هذان فتاتان جميل."
    ]
    
    for text in test_cases:
        print(f"\n[INPUT]:  {text}")
        corrected = grammar_checker.correct(text)
        print(f"[OUTPUT]: {corrected}")

if __name__ == "__main__":
    test_grammar()
