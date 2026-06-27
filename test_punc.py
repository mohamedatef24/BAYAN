from src.nlp.punctuation.punctuation_service import get_punctuation_model
from src.nlp.punctuation.punctuation_rules import validate_punctuation_diff
import logging
logging.basicConfig(level=logging.INFO)

def test():
    checker = get_punctuation_model()
    texts = [
        "قال المعلم يقدر المجتمع جهود المهندسين برغم الصعوبات التي واجهوها حققوا نجاحا كبيرا في المشروع و ابهروا العالم",
        "هل ذهبت الى المدرسة اليوم يا احمد",
        "الجو جميل جدا في الاسكندرية الان",
        "من اهم اهداف الشركة زيادة المبيعات تحسين الجودة و ارضاء العملاء"
    ]
    for t in texts:
        result = checker.correct(t)
        print(f"Original: {t}")
        print(f"Punc:     {result}\n")

if __name__ == '__main__':
    test()
