
import sys
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from model_loader import SpellingModel, GrammarModel, PunctuationModel
except ImportError as e:
    logger.error(f"Failed to import models: {e}")
    sys.exit(1)

def test_models():
    print("--- Testing Model Loading and Inference ---")
    
    # Test Spelling
    print("\n1. Testing Spelling Model...")
    try:
        spelling = SpellingModel()
        text = "الكتبة الصحيحه مهمة"
        corrected = spelling.correct(text)
        print(f"Input: {text}")
        print(f"Output: {corrected}")
        if text == corrected:
            print("WARNING: Spelling model returned original text (no correction).")
    except Exception as e:
        print(f"ERROR: Spelling model failed: {e}")

    # Test Grammar
    print("\n2. Testing Grammar Model...")
    try:
        grammar = GrammarModel()
        text = "الطلاب ذهبوا الى المدرسة" # Should be gold standard? Or maybe "الطلاب ذهب" needs correction
        corrected = grammar.correct(text)
        print(f"Input: {text}")
        print(f"Output: {corrected}")
    except Exception as e:
        print(f"ERROR: Grammar model failed: {e}")

    # Test Punctuation
    print("\n3. Testing Punctuation Model...")
    try:
        punctuation = PunctuationModel()
        text = "قال المعلم الدرس مهم"
        punctuated = punctuation.add_punctuation(text)
        print(f"Input: {text}")
        print(f"Output: {punctuated}")
    except Exception as e:
        print(f"ERROR: Punctuation model failed: {e}")

if __name__ == "__main__":
    test_models()
