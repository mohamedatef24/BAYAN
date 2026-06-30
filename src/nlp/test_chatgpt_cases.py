import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.nlp.grammar.grammar_rules import ArabicGrammarGuard
from src.nlp.spelling.araspell_rules import AraSpellPostProcessor

def process_text(text, grammar, spell):
    # Pipeline simulation
    text = grammar.smart_asmaa_khamsa_fix(text)
    text = grammar.fix_subject_verb_agreement(text)
    text = grammar.fix_gender_agreement(text)
    text = grammar.fix_prepositions_advanced(text)
    text = grammar.fix_initial_hamza(text)
    text = grammar.fix_conditional_sentences(text)
    text = grammar.fix_verbs_nasb_and_jazm(text)
    text = grammar.fix_noun_adjective_agreement_advanced(text)
    text = grammar.fix_number_and_gender_agreement(text)
    text = grammar.fix_kana_and_inna(text)
    text = grammar.regex_rules_fallback(text)
    text = grammar.fix_tanween_fathah(text)
    
    text = spell.fix_common_hamza(text)
    text = spell.join_fragments(text)
    text = spell.fix_hamza_conservative(text)
    text = spell.remove_word_repetition_with_wa(text)
    text = spell.remove_hallucinations(text)
    return text.strip()

def run_tests():
    grammar = ArabicGrammarGuard()
    spell = AraSpellPostProcessor()
    
    test_cases = [
        # 1. Asmaa Khamsa
        ("رأيت أخاك في السوق.", "رأيت أخاك في السوق."),
        ("جاء أبوك اليوم.", "جاء أبوك اليوم."),
        # 2. Non-human plural
        ("السيارات تسير بسرعة.", "السيارات تسير بسرعة."),
        ("المدارس كبيرة.", "المدارس كبيرة."),
        # 3. Masc ends with Ta Marbuta
        ("أسامة بطل شجاع.", "أسامة بطل شجاع."),
        ("حضر القضاة الكبار.", "حضر القضاة الكبار."),
        # 4. Words ending in ون not plural
        ("قرأت عن قانون جديد.", "قرأت عن قانون جديد."),
        ("زرعت زيتونًا في الأرض.", "زرعت زيتونًا في الأرض."),
        # 5. Inna after Qawl
        ("قال إنه قادم.", "قال إنه قادم."),
        ("يقول إنه يعرف الحقيقة.", "يقول إنه يعرف الحقيقة."),
        # 6. Ma Naafiya vs Conditional
        ("ما يذهب محمد إلى المدرسة.", "ما يذهب محمد إلى المدرسة."),
        ("ما فعلت ذلك.", "ما فعلت ذلك."),
        # 7. Lam Al-Ta'leel
        ("ذهبت لأتعلم.", "ذهبت لأتعلم."),
        ("جاء ليساعد صديقه.", "جاء ليساعد صديقه."),
        # 8. Broken Plural + Adjective
        ("جاء الرجال الطويلون.", "جاء الرجال الطويلون."),
        ("رأيت الرجال الأقوياء.", "رأيت الرجال الأقوياء."),
        # 9. Defective verbs
        ("هم رموا الكرة.", "هم رموا الكرة."),
        ("دعوا الله.", "دعوا الله."),
        # 10. Haa Milkiya vs Ta Marbuta
        ("هذا كتابه.", "هذا كتابه."),
        ("سمعت صوته.", "سمعت صوته."),
        # 11. Merged words
        ("أحمد درس اليوم.", "أحمد درس اليوم."),
        ("يوم مشمس جميل.", "يوم مشمس جميل."),
        # 12. Imma / Amma
        ("إما هذا أو ذاك.", "إما هذا أو ذاك."),
        ("أما بعد، فهذا أمر مهم.", "أما بعد، فهذا أمر مهم."),
        # 13. Trailing Hamza
        ("قرأ الطالب الكتاب.", "قرأ الطالب الكتاب."),
        ("هذا مبدأ مهم.", "هذا مبدأ مهم."),
        # 14. Fake Prepositions
        ("هذا كتاب منطقي.", "هذا كتاب منطقي."),
        ("أكلت فيتامينات كثيرة.", "أكلت فيتامينات كثيرة."),
        # 15. Conditional In
        ("سأذهب إن جاء أحمد.", "سأذهب إن جاء أحمد."),
        ("إن تدرس تنجح.", "إن تدرس تنجح.")
    ]
    
    print("Running ChatGPT Regression Test Suite...\n")
    passed = 0
    for idx, (input_text, expected) in enumerate(test_cases, 1):
        final_text = process_text(input_text, grammar, spell)
        
        if final_text == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            
        print(f"Test {idx}: {status}")
        print(f"Input   : {input_text}")
        print(f"Output  : {final_text}")
        if final_text != expected:
            print(f"Expected: {expected}")
        print("-" * 40)
        
    print(f"\nTotal Passed: {passed}/{len(test_cases)}")

if __name__ == '__main__':
    run_tests()
