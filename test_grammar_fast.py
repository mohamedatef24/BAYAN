import sys
import os
sys.path.append(os.path.abspath('src'))
from nlp.spelling.araspell_service import get_spelling_model
from nlp.grammar.grammar_service import get_grammar_model

def test_fast():
    spell_checker = get_spelling_model()
    grammar_checker = get_grammar_model()
    
    cases = {
        # الأسماء الخمسة
        "[الأسماء الخمسة] فاعل مرفوع بالواو": "جاء أباك مسرعاً",
        "[الأسماء الخمسة] مفعول به منصوب بالألف": "رأيت أبوك في المسجد",
        "[الأسماء الخمسة] اسم مجرور بالياء": "مررت بأخوك أمس",
        "[الأسماء الخمسة] مبتدأ مرفوع بالواو": "ذا العلم محترم",
        
        # العدد والمعدود
        "[العدد والمعدود] 3-10 مخالفة (مؤنث)": "اشتريت ثلاثة سيارات",
        "[العدد والمعدود] 3-10 مخالفة (مذكر)": "عندي سبع أقلام",
        "[العدد والمعدود] تمييز مفرد منصوب (11-99)": "في الفصل عشرون طالب",
        "[العدد والمعدود] العددان 1 و 2 يوافقان": "حضر رجلان اثنتان",
        
        # الأفعال الخمسة
        "[الأفعال الخمسة] ثبوت النون (مرفوع)": "الطلاب يذاكروا بجد",
        "[الأفعال الخمسة] حذف النون (منصوب بلن)": "الطلاب لن يذاكرون",
        "[الأفعال الخمسة] حذف النون (مجزوم بلم)": "أنتِ لم تذهبين",
        "[الأفعال الخمسة] ثبوت النون (مرفوع للمخاطبة)": "أنتِ تلعبي جيداً"
    }

    print("=== Testing Grammar Rules (Advanced) ===")
    for desc, text in cases.items():
        print(f"\n{desc}")
        print(f"Input : {text}")
        
        # 1. Spell Check
        spelled_text = spell_checker.correct(text)
        
        # 2. Grammar Check
        final_text = grammar_checker.correct(spelled_text)
        
        print(f"Output: {final_text}")

if __name__ == '__main__':
    test_fast()
