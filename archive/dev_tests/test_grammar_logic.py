import sys
import codecs
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Add src to python path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

from nlp.grammar.grammar_rules import ArabicGrammarGuard

guard = ArabicGrammarGuard()

tests = [
    "المهندسون صممت المشروع",  # PC001 spelling output
    "البنات يذهبون إلى المدرسة", # PC003 spelling output
    "أن ابوك رجل طيب", # PC007 spelling output
    "العمال بنى المبنى الجديد", # PC020 spelling output
    "الامهات طبخ الطعام والاطفال لعب", # PC043 spelling output
    "المديره وافق علي المشروع والموظفات وافق أيضا" # PC046
]

for t in tests:
    print(f"\n[IN]  {t}")
    out = guard.apply_rules(t)
    print(f"[OUT] {out}")

