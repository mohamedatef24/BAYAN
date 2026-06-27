import logging
from src.nlp.spelling.araspell_rules import AraSpellPostProcessor

# Mock original and result
original = "المهندسات صممو المشرووع الكبير"
result = "المهندسات مصممو المشروع الكبير"

orig_words = original.split()
res_words_list = result.split()

print(f"Original: {orig_words}")
print(f"Result: {res_words_list}")

if len(orig_words) == len(res_words_list):
    for idx in range(len(orig_words)):
        ow = orig_words[idx]
        rw = res_words_list[idx]
        if not ow.startswith('م') and rw.startswith('م') and rw[1:] == ow and ow.endswith('و'):
            print(f"[SPELLING] Blocked morphological mutation (verb→noun '{ow}'→'{rw}'): '{original}' -> '{result}'")
            result = original
            break

print(f"Final result: {result}")
