import re

def improved_postprocessing(text: str) -> str:
    # We will build a function for the colon guard that checks context
    _SPEECH_VERBS = r'(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت|وضح|وضحت|أوضح|أوضحت|رد|ردت)'
    _OTHER_CUES = r'(التالي|الآتي|مثال|ملاحظة|تنبيه|تحذير|قائلا|قائلة|اسم|العمر|تاريخ|رقم|عاجل|الآتية|التالية)'
    
    def _colon_guard(match):
        # match.group(0) is the colon and any spaces before it.
        # But we need to look at the text BEFORE the colon!
        # So it's better to use re.sub with a regex that captures the preceding words.
        pass
        
    # Better approach: find all colons, and check if a speech verb is within 3 words before it.
    # regex to find words before a colon:
    # ((?:[\u0600-\u06FF]+\s+){0,3})(:)
    # Actually, we can use a simpler replacement:
    
    # First, let's fix misplaced colons (e.g. قال: المعلم -> قال المعلم:)
    # We allow 1 or 2 names/titles after the verb.
    text = re.sub(
        r'\b(' + _SPEECH_VERBS + r'):?\s+(ال[أ-ي]+|أحمد|محمد|محمود|علي|عمر|خالد|فاطمة|مريم|عائشة|خديجة)(?:\s+(ال[أ-ي]+))?\b:?',
        lambda m: f"{m.group(1)} {m.group(2)}{' ' + m.group(3) if m.group(3) else ''}:",
        text
    )
    
    # Then apply a smarter Strict Colon Guard
    # We find every colon.
    def smart_guard(match):
        full_match = match.group(0) # e.g. "سألت المرشد السياحي:"
        # check if it contains a speech verb or other cue
        if re.search(r'\b(' + _SPEECH_VERBS + r'|' + _OTHER_CUES + r')\b', full_match):
            return full_match # Keep it!
        else:
            # It's an invalid colon. Strip the colon.
            return full_match.replace(':', ' ').replace('  ', ' ')
            
    # We match up to 3 words before the colon + the colon
    text = re.sub(r'(?:[\u0600-\u06FF]+\s+){1,3}:', smart_guard, text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text

examples = [
    "فسألت المرشد السياحي: متى بنيت هذه المساجد العتيقة",
    "قال: المعلم ادرسوا جيدا",
    "قال المعلم: ادرسوا جيدا",
    "رد قائلا: أوافق",
    "قال أحمد: السلام عليكم",
    "أجاب: محمد نعم",
    "سألت: فاطمة متى نذهب",
    "السيارة سريعة: جدا", # should remove colon
    "ذهبنا إلى السوق: واشترينا تفاحا" # should remove colon
]

print("Improved colon post-processing:")
print("-" * 50)
for ex in examples:
    print(f"Input: {ex}")
    print(f"Output: {improved_postprocessing(ex)}")
    print("-" * 50)
