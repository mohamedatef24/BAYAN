import difflib
import re

def get_word_positions(text):
    positions = []
    for m in re.finditer(r'\S+', text):
        positions.append((m.group(), m.start(), m.end()))
    return positions

def get_word_diffs(original, corrected):
    orig_words = get_word_positions(original)
    corr_words = get_word_positions(corrected)
    s = difflib.SequenceMatcher(None, [w[0] for w in orig_words], [w[0] for w in corr_words])
    
    print("Opcodes:")
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        orig_seq = [w[0] for w in orig_words[i1:i2]]
        corr_seq = [w[0] for w in corr_words[j1:j2]]
        print(f"{tag:7} | orig[{i1}:{i2}]={orig_seq} | corr[{j1}:{j2}]={corr_seq}")

    suggestions = []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'replace':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                    'type': 'grammar'
                })
        elif tag == 'delete':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': '',
                    'type': 'grammar'
                })
        elif tag == 'insert':
            pos = orig_words[i1][1] if i1 < len(orig_words) else len(original)
            suggestions.append({
                'start': pos,
                'end': pos,
                'original': '',
                'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                'type': 'grammar'
            })
            
    return suggestions

def test():
    original = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    corrected = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوبات..."
    
    print("Testing original vs corrected:")
    diffs = get_word_diffs(original, corrected)
    print("\nSuggestions generated:")
    for d in diffs:
        print(d)

if __name__ == "__main__":
    test()
