import asyncio
from src.nlp.punctuation.punctuation_service import get_punctuation_model

def run_tests():
    checker = get_punctuation_model()
    
    cases = {
        "1. نقطتين بعد القول": "قال المعلم العلم نور",
        "2. نقطتين للتفصيل": "فصول السنة أربعة الصيف الخريف الشتاء والربيع",
        "3. نقطتين للأمثلة": "أدوات الاستفهام كثيرة مثل أين متى وكيف",
        "4. نقطتين للتفسير": "الأسد حيوان مفترس",
        "5. فاصلة بين الجمل": "ذهبت الى السوق واشتريت الفواكه ثم عدت الى المنزل",
        "6. فاصلة للتعداد": "اشتريت تفاحا وبرتقالا وموزا",
        "7. فاصلة للنداء": "يا علي أقبل",
        "8. فاصلة للشرط": "إذا ذاكرت بجد و اجتهدت في دروسك سوف تنجح",
        "9. فصلة منقوطة للسبب": "أجتهد في دروسي لأنها الطريق إلى نجاحي",
        "10. فصلة منقوطة للنتيجة": "كان الطالب مجتهدا فنجح بتفوق",
        "11. نقطة للنهاية": "الدين النصيحة"
    }
    
    print("=== Testing Punctuation Rules ===")
    for desc, text in cases.items():
        result = checker.correct(text)
        print(f"\n[{desc}]")
        print(f"Input : {text}")
        print(f"Output: {result}")

if __name__ == '__main__':
    run_tests()
