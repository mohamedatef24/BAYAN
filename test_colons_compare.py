import re

def old_postprocessing(text: str) -> str:
    # 1. Fix misplaced colons for saying verbs
    text = re.sub(r'\b(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت):?\s+(ال[أ-ي]+|أحمد|محمد|محمود|علي|عمر|خالد|فاطمة|مريم|عائشة|خديجة)\b:?', r'\1 \2:', text)

    # 2. Strict Colon Guard
    _ALLOWED_COLON_CUES = r'(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت|وضح|وضحت|أوضح|أوضحت|رد|ردت|التالي|الآتي|مثال|ملاحظة|تنبيه|تحذير|قائلا|قائلة|اسم|العمر|تاريخ|رقم|عاجل|الآتية|التالية)'
    def _colon_guard(match):
        prev_word = match.group(1)
        if re.fullmatch(_ALLOWED_COLON_CUES, prev_word):
            return match.group(0)
        return prev_word + " "
        
    text = re.sub(r'([\u0600-\u06FF]+)(\s*:)', _colon_guard, text)
    return text

def new_postprocessing(text: str) -> str:
    # 1. Strict Colon Guard
    _ALLOWED_COLON_CUES = r'(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت|وضح|وضحت|أوضح|أوضحت|رد|ردت|التالي|الآتي|مثال|ملاحظة|تنبيه|تحذير|قائلا|قائلة|اسم|العمر|تاريخ|رقم|عاجل|الآتية|التالية)'
    def _colon_guard(match):
        prev_word = match.group(1)
        if re.fullmatch(_ALLOWED_COLON_CUES, prev_word):
            return match.group(0)
        return prev_word + " "
        
    text = re.sub(r'([\u0600-\u06FF]+)(\s*:)', _colon_guard, text)
    
    # 2. Fix misplaced colons for saying verbs
    text = re.sub(r'\b(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت):?\s+(ال[أ-ي]+|أحمد|محمد|محمود|علي|عمر|خالد|فاطمة|مريم|عائشة|خديجة)\b:?', r'\1 \2:', text)
    
    return text

examples = [
    "فسألت المرشد السياحي: متى بنيت هذه المساجد العتيقة",
    "قال: المعلم ادرسوا جيدا",
    "قال المعلم: ادرسوا جيدا",
    "رد قائلا: أوافق",
    "قال أحمد: السلام عليكم",
    "أجاب: محمد نعم",
    "سألت: فاطمة متى نذهب"
]

print("Comparing colon post-processing:")
print("-" * 50)
for ex in examples:
    print(f"Input: {ex}")
    print(f"Old logic: {old_postprocessing(ex)}")
    print(f"New logic: {new_postprocessing(ex)}")
    print("-" * 50)
