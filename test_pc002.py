from src.app import analyze_text
import json

original = "الولاد يلعبون بالشاروع"
result = analyze_text(original)
print(json.dumps(result, ensure_ascii=False, indent=2))
