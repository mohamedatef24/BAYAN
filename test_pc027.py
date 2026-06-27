import json
from src.app import analyze_text

res = analyze_text("الكتاب مفيد جدا وانا احبه")
print(json.dumps(res, ensure_ascii=False, indent=2))
