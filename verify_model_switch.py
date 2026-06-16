import sys
import os
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from model_loader import GrammarModel, SpellingModel
from app import load_models, grammar_model, spelling_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_models():
    print("Testing load_models()...")
    # Change to src directory as run_app.py does
    os.chdir(Path(__file__).parent / 'src')
    
    success = load_models()
    print(f"load_models() returned: {success}")
    
    print(f"Grammar model loaded: {grammar_model is not None}")
    print(f"Spelling model loaded: {spelling_model is not None}")
    
    if grammar_model is None:
        print("ERROR: Grammar model should be loaded!")
        return False
        
    if spelling_model is not None:
        print("ERROR: Spelling model should NOT be loaded!")
        return False
        
    print("✓ Model load state is correct.")
    
    # Test Grammar Correction (Optional, might be slow)
    # test_text = "ذهب الولد الى المدرسة"
    # print(f"Testing grammar correction with: {test_text}")
    # corrected = grammar_model.correct(test_text)
    # print(f"Corrected: {corrected}")
    
    return True

if __name__ == "__main__":
    if verify_models():
        print("\nVerification SUCCESSFUL!")
        sys.exit(0)
    else:
        print("\nVerification FAILED!")
        sys.exit(1)
