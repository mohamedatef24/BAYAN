import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

from src.nlp.spelling.araspell_service import get_spelling_model
from src.nlp.grammar.grammar_service import get_grammar_model

print("Loading Spelling...")
spell = get_spelling_model()
print("Loading Grammar...")
grammar = get_grammar_model()

text1 = "لم ينمو الاقتصاد كالمعتاد"
text2 = "ذهبت المهندسون"

print(f"\n--- Text 1: {text1} ---")
print("AraSpell output:", spell.correct(text1))
print("Grammar output:", grammar.correct(text1))

print(f"\n--- Text 2: {text2} ---")
print("AraSpell output:", spell.correct(text2))
print("Grammar output:", grammar.correct(text2))

