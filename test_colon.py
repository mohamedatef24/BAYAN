import re

def add_colons(text):
    pattern = r'\b(قال|يقول|قالت|تقول|سأل|سألت|أجاب|أجابت|صرح|صرحت|أضاف|أضافت)\s+(ال[أ-ي]+|[أ-ي]+\s+ال[أ-ي]+|أحمد|محمد|محمود|علي|عمر)\b(?!\s*:)'
    return re.sub(pattern, r'\1 \2:', text)

cases = [
    "قال المعلم يقدر المجتمع",
    "قالت أمي نظف غرفتك", # Won't match أمي
    "أجاب الطالب لا أعرف",
    "قال نعم", # Won't match نعم
    "صرح وزير الخارجية بأن", # Matches وزير الخارجية
]

for c in cases:
    print(add_colons(c))
