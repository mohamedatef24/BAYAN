from src.nlp.grammar.grammar_rules import ArabicGrammarGuard
guard = ArabicGrammarGuard()
text = "الحكومة أعلنت قرارا جديدا والمواطنون سعداء"
res = guard.fix_tanween_fathah(text)
print("Result:", res)
