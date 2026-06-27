import difflib
import re

def get_word_positions(text):
    positions = []
    for m in re.finditer(r'\S+', text):
        positions.append((m.group(), m.start(), m.end()))
    return positions

# Simulate what happens in the pipeline:
# Spelling changes القصه→القصة but NOT طويل or ومملل
# So current_text becomes: القصة طويل ومملل  (if spelling fixed القصه)
# But wait - from the logs, grammar input was: القصه طويل ومملل 
# That means spelling didn't fix القصه either. But the benchmark shows 
# a spelling suggestion [0:5] 'القصه'→'القصة'. So spelling DID produce a patch.

# Grammar runs on spelling-corrected text.
# If spelling fixed القصه→القصة, grammar input would be: القصة طويل ومملل
grammar_input = "القصة طويل ومملل"
grammar_output = "القصة طويلة ومملة"

print(f"Grammar Input:  '{grammar_input}' (len={len(grammar_input)})")
print(f"Grammar Output: '{grammar_output}' (len={len(grammar_output)})")

orig_words = get_word_positions(grammar_input)
corr_words = get_word_positions(grammar_output)

print(f"\nInput words:")
for w, s, e in orig_words:
    print(f"  '{w}' [{s}:{e}]")

print(f"\nOutput words:")
for w, s, e in corr_words:
    print(f"  '{w}' [{s}:{e}]")

s = difflib.SequenceMatcher(None, [w[0] for w in orig_words], [w[0] for w in corr_words])
print(f"\nOpcodes:")
for tag, i1, i2, j1, j2 in s.get_opcodes():
    print(f"  {tag}: orig_words[{i1}:{i2}] vs corr_words[{j1}:{j2}]")
    if tag != 'equal':
        start_char = orig_words[i1][1]
        end_char = orig_words[i2-1][2]
        orig_slice = grammar_input[start_char:end_char]
        corr_text = " ".join([w[0] for w in corr_words[j1:j2]])
        print(f"    [{start_char}:{end_char}] '{orig_slice}' → '{corr_text}'")

# Now map back to ORIGINAL text coordinates
# Original text: القصه طويل ومملل (len=16)
# After spelling: القصة طويل ومملل (len=16) — same length!
# Grammar diff on current: [5:16] 'طويل ومملل' → 'طويلة ومملة'
# Mapped to original: same since no length change from spelling
