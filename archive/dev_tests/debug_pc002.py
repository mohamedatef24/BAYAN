import logging
from src.nlp.spelling.araspell_rules import AraSpellPostProcessor

# Mock original and result
original = "الولاد يلعبون بالشاروع"
result = "الأولاد يلعبون ب الشارع"

orig_standalone = set(w for w in original.split() if len(w) == 1)
orig_words = original.split()
res_words_list = result.split()

print(f"Original: {orig_words}")
print(f"Result: {res_words_list}")

for idx, w in enumerate(res_words_list):
    if len(w) == 1 and w not in orig_standalone:
        if w in 'واتيبلفك':
            is_prefix_separation = False
            if w in 'وفبلك' and idx + 1 < len(res_words_list):
                next_word = res_words_list[idx + 1]
                combined = w + next_word
                for ow in orig_words:
                    if ow.startswith(w) and len(ow) > 2:
                        print(f"  Match! ow={ow}, w={w}, combined={combined}")
                        is_prefix_separation = True
                        break
            
            if not is_prefix_separation:
                print(f"[SPELLING] Blocked destructive tokenization '{w}'")
                result = original
                break

print(f"Final result: {result}")
