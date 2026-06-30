import os
import sys

# Ensure we can import from src
sys.path.append(os.path.abspath('src'))
from nlp.punctuation.punctuation_service import get_punctuation_model

examples = [
    # 1. 1 word after verb
    "قال المعلم ادرسوا جيدا",
    
    # 2. 2 words after verb
    "فسألت المرشد السياحي متى بنيت هذه المساجد",
    
    # 3. 4 words after verb
    "قال رئيس مجلس الوزراء المصري وافقنا على القرار",
    
    # 4. Indirect speech (should NOT have a colon)
    "قال المعلم إن الامتحان سهل",
    
    # 5. Question to someone (no direct speech)
    "سألت فاطمة عن موعد الرحلة"
]

def run_tests():
    print("Loading PuncAra-v1...")
    punc_model = get_punctuation_model()
    print("Model loaded. Testing adding colons to raw text:\n")
    
    for i, text in enumerate(examples, 1):
        # We only pass raw text without any punctuation
        result = punc_model.correct(text)
        print(f"--- Example {i} ---")
        print(f"Input:  {text}")
        print(f"Output: {result}\n")

if __name__ == "__main__":
    run_tests()
