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
                    'type': 'generic'
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
                    'type': 'generic'
                })
        elif tag == 'insert':
            pos = orig_words[i1][1] if i1 < len(orig_words) else len(original)
            suggestions.append({
                'start': pos,
                'end': pos,
                'original': '',
                'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                'type': 'generic'
            })
            
    return suggestions

def test():
    original = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوبات..."
    corrected = "قال محمد علي: أننا حققنا نجاحا كبيرا في المشروع رغم الصعوبات...."
    
    diffs = get_word_diffs(original, corrected)
    for d in diffs:
        print(d)

if __name__ == "__main__":
    test()
