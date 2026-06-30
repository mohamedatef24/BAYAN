import sys
import os
import re

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from nlp.grammar.grammar_rules import ArabicGrammarGuard
from nlp.spelling.araspell_rules import AraSpellPostProcessor
from transformers import AutoTokenizer

def run_tests():
    print("Initializing components...")
    grammar = ArabicGrammarGuard()
    
    print("\n--- 1. GRAMMAR BUGS ---")
    
    # 1.1 Asmaa Khamsa Object Position
    # Before: رأيت أخوك (Forced nominative)
    res = grammar.smart_asmaa_khamsa_fix("رأيت أخاك")
    print(f"1.1 [1]: رأيت أخاك -> {res} (Expected: رأيت أخاك)")
    res2 = grammar.smart_asmaa_khamsa_fix("قابلنا أباك")
    print(f"1.1 [2]: قابلنا أباك -> {res2} (Expected: قابلنا أباك)")
    
    # 1.2 Non-Human Plurals
    res = grammar.fix_subject_verb_agreement("السيارات تسرع")
    print(f"1.2 [1]: السيارات تسرع -> {res} (Expected: السيارات تسرع)")
    res2 = grammar.fix_subject_verb_agreement("المدارس تفتح")
    print(f"1.2 [2]: المدارس تفتح -> {res2} (Expected: المدارس تفتح)")
    
    # 1.3 Masculine Nouns Ending in 'ة'
    res = grammar.fix_gender_agreement("خليفة عادل")
    print(f"1.3 [1]: خليفة عادل -> {res} (Expected: خليفة عادل)")
    res2 = grammar.fix_gender_agreement("دعاة كبار")
    print(f"1.3 [2]: دعاة كبار -> {res2} (Expected: دعاة كبار)")
    
    # 1.4 Preposition Blocklist Missing 'ون' Root Words
    res = grammar.fix_prepositions_advanced("في قانون جديد")
    print(f"1.4 [1]: في قانون -> {res} (Expected: في قانون جديد)")
    res2 = grammar.fix_prepositions_advanced("مع فرعون")
    print(f"1.4 [2]: مع فرعون -> {res2} (Expected: مع فرعون)")
    
    # 1.5 Breaking Hamzat Inna after 'Qawl'
    res = grammar.fix_initial_hamza("قال انه قادم")
    print(f"1.5 [1]: قال انه قادم -> {res} (Expected: قال إنه قادم)")
    res2 = grammar.fix_initial_hamza("تقول انهم هناك")
    print(f"1.5 [2]: تقول انهم هناك -> {res2} (Expected: تقول إنهم هناك)")

    # 1.6 Conditional Sentences Overcorrection (Negative ما / Relative من)
    res = grammar.fix_conditional_sentences("رأيت من يدرس")
    print(f"1.6 [1]: رأيت من يدرس -> {res} (Expected: رأيت من يدرس)")
    res2 = grammar.fix_conditional_sentences("أحب من يعلم")
    print(f"1.6 [2]: أحب من يعلم -> {res2} (Expected: أحب من يعلم)")
    
    # 1.7 Lam Al-Ta'leel Overcorrection
    res = grammar.fix_verbs_nasb_and_jazm("ليدعوا إلى الله")
    print(f"1.7 [1]: ليدعوا إلى الله -> {res} (Expected: ليدعوا إلى الله)")
    res2 = grammar.fix_verbs_nasb_and_jazm("ليذهبوا إلى المدرسة")
    print(f"1.7 [2]: ليذهبوا إلى المدرسة -> {res2} (Expected: ليذهبوا إلى المدرسة)")

    # 1.8 Broken Plural Adjective Corruption
    res = grammar.fix_noun_adjective_agreement_advanced("الرجال الطويلون")
    print(f"1.8 [1]: الرجال الطويلون -> {res} (Expected: الرجال الطويلون)")
    res2 = grammar.fix_noun_adjective_agreement_advanced("العمال الماهرون")
    print(f"1.8 [2]: العمال الماهرون -> {res2} (Expected: العمال الماهرون)")
    
    # 1.9 Defective Verb Truncation in VSO
    res = grammar.fix_number_and_gender_agreement("دعوا الأصدقاء")
    print(f"1.9 [1]: دعوا الأصدقاء -> {res} (Expected: دعوا الأصدقاء/دعا الأصدقاء)")
    res2 = grammar.fix_number_and_gender_agreement("رموا الكرة")
    print(f"1.9 [2]: رموا الكرة -> {res2} (Expected: رموا الكرة/رمى الكرة)")

    # 1.10 ان/ون Root Noun Corruption in Kana/Inna
    res = grammar.fix_kana_and_inna("إن قانون")
    print(f"1.10 [1]: إن قانون -> {res} (Expected: إن قانون)")
    res2 = grammar.fix_kana_and_inna("كان فرعون")
    print(f"1.10 [2]: كان فرعون -> {res2} (Expected: كان فرعون)")

    # 1.11 Contextual Jazm Pronoun Contamination
    res = grammar.fix_conditional_sentences("إن يذهبوا يجدوا سياراتكم")
    print(f"1.11 [1]: إن يذهبوا -> {res} (Expected: إن يذهبوا يجدوا سياراتكم)")
    res2 = grammar.fix_conditional_sentences("من يدرسوا ينجحوا بكم")
    print(f"1.11 [2]: من يدرسوا -> {res2} (Expected: من يدرسوا ينجحوا بكم)")

    # 1.12 Destruction of Mid-Sentence Conditional 'إن'
    res = grammar.fix_initial_hamza("سأذهب ان جاء أحمد")
    print(f"1.12 [1]: ان جاء -> {res} (Expected: ان جاء / إن جاء)")
    res2 = grammar.fix_initial_hamza("تنجح ان تذاكر")
    print(f"1.12 [2]: ان تذاكر -> {res2} (Expected: ان تذاكر / إن تذاكر)")
    
    # 1.13 'كان' Misclassified as 'إن' in Regex Fallback
    res = grammar.regex_rules_fallback("كان أخوك")
    print(f"1.13 [1]: كان أخوك -> {res} (Expected: كان أخوك)")
    res2 = grammar.regex_rules_fallback("كان أبوك")
    print(f"1.13 [2]: كان أبوك -> {res2} (Expected: كان أبوك)")

    # 1.14 Dual Nouns Corrupting Plural Verbs
    res = grammar.fix_subject_verb_agreement("إن الطالبين يدرسان")
    print(f"1.14 [1]: إن الطالبين يدرسان -> {res} (Expected: إن الطالبين يدرسان)")
    res2 = grammar.fix_subject_verb_agreement("لعل الطفلين يلعبان")
    print(f"1.14 [2]: لعل الطفلين يلعبان -> {res2} (Expected: لعل الطفلين يلعبان)")

    # 4.1 Punctuation Masking Dictionary Lookups
    res = grammar.fix_tanween_fathah("طويلا.")
    print(f"4.1 [1]: طويلا. -> {res} (Expected: طويلاً.)")
    res2 = grammar.fix_initial_hamza("ايضا،")
    print(f"4.1 [2]: ايضا، -> {res2} (Expected: أيضاً،)")

    print("\n--- 2. SPELLING BUGS ---")
    post = AraSpellPostProcessor()
    
    # 2.1 HAMZA_WHITELIST Overcorrection
    res = post.fix_common_hamza("اعرف الحقيقة")
    print(f"2.1 [1]: اعرف الحقيقة -> {res} (Expected: اعرف الحقيقة)")
    res2 = post.fix_common_hamza("اعمل بجد")
    print(f"2.1 [2]: اعمل بجد -> {res2} (Expected: اعمل بجد)")

    # 2.3 Destructive Word Merging
    res = post.join_fragments("يوم مشمس")
    print(f"2.3 [1]: يوم مشمس -> {res} (Expected: يوم مشمس)")
    res2 = post.join_fragments("أحمد درس")
    print(f"2.3 [2]: أحمد درس -> {res2} (Expected: أحمد درس)")
    
    # 2.4 'إما' vs 'أما' Overcorrection
    res = post.fix_common_hamza("اما هذا أو ذاك")
    print(f"2.4 [1]: اما هذا -> {res} (Expected: اما هذا)")
    res2 = post.fix_common_hamza("إما أن تذهب")
    print(f"2.4 [2]: إما أن تذهب -> {res2} (Expected: إما أن تذهب)")
    
    # 2.5 Trailing Hamza Destruction
    res = post.fix_hamza_conservative("قرأ الكتاب")
    print(f"2.5 [1]: قرأ -> {res} (Expected: قرأ الكتاب)")
    res2 = post.fix_hamza_conservative("مبدأ جديد")
    print(f"2.5 [2]: مبدأ -> {res2} (Expected: مبدأ جديد)")
    
    # 2.9 Destructive Word Repetition Removal
    res = post.remove_word_repetition_with_wa("صنفا وصنفا")
    print(f"2.9 [1]: صنفا وصنفا -> {res} (Expected: صنفا وصنفا)")
    res2 = post.remove_word_repetition_with_wa("رجل ورجل")
    print(f"2.9 [2]: رجل ورجل -> {res2} (Expected: رجل ورجل)")
    
    # 2.11 Destruction of Badal Structures
    res = post.remove_hallucinations("الأستاذ أستاذ الرياضيات")
    print(f"2.11 [1]: الأستاذ أستاذ -> {res} (Expected: الأستاذ أستاذ الرياضيات)")
    res2 = post.remove_hallucinations("الكتاب كتاب النحو")
    print(f"2.11 [2]: الكتاب كتاب -> {res2} (Expected: الكتاب كتاب النحو)")

    print("\nTests completed.")

if __name__ == '__main__':
    run_tests()
