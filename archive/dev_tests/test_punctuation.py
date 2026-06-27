import sys
sys.stdout.reconfigure(encoding='utf-8')

from src.app import init_pipeline

p = init_pipeline()

tests = [
    "الخطة السنوية للشركة",         # 3 words -> should block trailing .
    "هذا هو تقرير المبيعات",      # 4 words -> should block trailing .
    "محمد ذهب إلى المدرسة اليوم", # 5 words -> allowed!
]

with open('test_punct_output.md', 'w', encoding='utf-8') as f:
    for t in tests:
        res = p.analyze(t)['corrected']
        f.write(f"IN: {t}\nOUT: {res}\n---\n")
