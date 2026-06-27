import asyncio
from src.nlp.punctuation.punctuation_service import get_punctuation_model

def test():
    checker = get_punctuation_model()
    text = "قال المعلم العلم نور"
    
    # Process text chunk using the model's raw predict
    raw = checker._predict_chunk(text)
    print(f"RAW PREDICT: {raw}")
    
    # Process through the whole pipeline
    final = checker.correct(text)
    print(f"FINAL: {final}")

test()
