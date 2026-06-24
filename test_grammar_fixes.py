import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.app import init_pipeline

p = init_pipeline()
tests = [
    'الأولاد لعب في الحديقة',
    'العمال بنى المبنى',
    'الطالبة متفوق في دراسته',
    'رأيت أخوك في المسجد',
    'هاتان الطالبان مجتهدان',
    'لم يفعلون الواجب بعد'
]

with open('test_grammar_output.md', 'w', encoding='utf-8') as f:
    for t in tests:
        res = p.analyze(t)['corrected']
        f.write(f"IN: {t}\nOUT: {res}\n---\n")
