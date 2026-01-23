"""Test script to verify model loading works correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from model_loader import SummarizationModel
import logging

logging.basicConfig(level=logging.INFO)

def test_model_loading():
    """Test if the model loads correctly."""
    model_path = Path("models/arabic_summarization_model/content/drive/MyDrive/arabic_summarization_model")
    
    if not model_path.exists():
        print(f"ERROR: Model path does not exist: {model_path}")
        return False
    
    try:
        print("Loading model...")
        model = SummarizationModel(str(model_path))
        print("✓ Model loaded successfully!")
        
        # Test summarization
        test_text = "التكنولوجيا الحديثة أحدثت ثورة في حياتنا اليومية. حيث سهّلت التواصل والتعلم والعمل. مما أدى إلى تطور المجتمعات وتحسين جودة الحياة."
        print(f"\nTesting summarization with text: {test_text[:50]}...")
        summary = model.summarize(test_text, max_length=50, min_length=10)
        print(f"✓ Summarization successful!")
        print(f"Summary: {summary}")
        
        return True
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model_loading()
    sys.exit(0 if success else 1)

