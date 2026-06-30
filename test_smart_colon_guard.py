import re

_ALLOWED_COLON_CUES = r'^[وفلس]?(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت|وضح|وضحت|أوضح|أوضحت|رد|ردت|التالي|الآتي|مثال|ملاحظة|تنبيه|تحذير|قائلا|قائلة|اسم|العمر|تاريخ|رقم|عاجل|الآتية|التالية)$'

def smart_arabic_postprocessing(text: str) -> str:
    # 1. Fix misplaced colons (e.g. قال: المعلم -> قال المعلم:)
    # Only applies if a colon is actually present on the verb or the name
    def _fix_misplaced(m):
        verb, col1, name, col2 = m.groups()
        if col1 == ':' or col2 == ':':
            return f"{verb} {name}:"
        return m.group(0)
        
    text = re.sub(
        r'\b([وفلس]?(?:قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت))(:?)\s+(ال[أ-ي]+|أحمد|محمد|محمود|علي|عمر|خالد|فاطمة|مريم|عائشة|خديجة)\b(:?)',
        _fix_misplaced, text
    )

    # 2. Smart Colon Guard (looks up to 6 words back)
    def _colon_guard(match):
        context = match.group(1)
        colon = match.group(2)
        
        words = re.findall(r'[\u0600-\u06FFa-zA-Z]+', context)
        if not words:
            return match.group(0)
            
        prev_word = words[-1]
        last_6_words = words[-6:]
        
        if any(re.match(_ALLOWED_COLON_CUES, w) for w in last_6_words):
            return match.group(0)
            
        if prev_word.startswith(('ال', 'لل', 'بال', 'فال', 'وال', 'كال')):
            return context + " " 
            
        return match.group(0)
        
    text = re.sub(r'([^:]+)(:)', _colon_guard, text)
    text = re.sub(r' +', ' ', text)
    return text

examples = [
    "فسألت المرشد السياحي: متى بنيت هذه المساجد العتيقة",
    "قال رئيس مجلس الوزراء المصري: وافقنا على القرار",
    "فقال: المعلم ادرسوا جيدا",
    "وقال المعلم: ادرسوا جيدا",
    "قال أحمد الطويل: السلام عليكم",
    "رد الأستاذ الجامعي المتخصص في الفيزياء: هذه نظرية صحيحة",
]

print("Smart Colon Guard Results:")
for ex in examples:
    print(f"Input:  {ex}")
    print(f"Output: {smart_arabic_postprocessing(ex)}")
    print("-" * 50)
