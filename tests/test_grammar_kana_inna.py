import pytest
from nlp.grammar.grammar_rules import ArabicGrammarGuard

@pytest.fixture
def grammar_guard():
    return ArabicGrammarGuard()

def test_inna_sisters(grammar_guard):
    # Inna: Subject is Mansoub (Accusative), Predicate is Marfoo' (Nominative)
    
    # 1. Subject is Plural
    text = "إن المعلمون مجتهدون"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "إن المعلمين مجتهدون" == corrected

    text = "لعل العاملون قادمون"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "لعل العاملين قادمون" == corrected

    # 2. Subject is Dual
    text = "كأن الفتاتان قمران"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "كأن الفتاتين قمران" == corrected

    # 3. Predicate is wrong
    text = "إن المهندسين نائمين"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "إن المهندسين نائمون" == corrected

    # 4. Five Nouns
    text = "إن أبو بكر رجل صالح"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "إن أبا بكر رجل صالح" == corrected


def test_kana_sisters(grammar_guard):
    # Kana: Subject is Marfoo' (Nominative), Predicate is Mansoub (Accusative)
    
    # 1. Subject is Plural
    text = "كان المهندسين بارعين"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "كان المهندسون بارعين" == corrected

    # 2. Subject is Dual
    text = "أصبح الرجلين غنيين"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "أصبح الرجلان غنيين" == corrected

    # 3. Predicate is wrong
    text = "بات الحارسان نائمون"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "بات الحارسان نائمين" == corrected

    # 4. Five Nouns
    text = "أصبح أبا محمد مريضا"
    corrected = grammar_guard.fix_kana_and_inna(text)
    assert "أصبح أبو محمد مريضا" == corrected

def test_no_false_positives(grammar_guard):
    # Should not mess with correct sentences
    text = "كان المعلمون بارعين"
    assert grammar_guard.fix_kana_and_inna(text) == text
    
    text = "إن المعلمين قادمون"
    assert grammar_guard.fix_kana_and_inna(text) == text
