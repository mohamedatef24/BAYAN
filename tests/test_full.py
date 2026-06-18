import difflib
import re

def get_word_positions(text):
    positions = []
    for m in re.finditer(r'\S+', text):
        positions.append((m.group(), m.start(), m.end()))
    return positions

class OffsetMapper:
    def __init__(self, original, modified):
        self.original = original
        self.modified = modified
        self.mapping = []
        self._build_mapping()
        
    def _build_mapping(self):
        s = difflib.SequenceMatcher(None, self.original, self.modified)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            self.mapping.append((j1, j2, i1, i2))
            
    def map_offset(self, mod_offset):
        for j1, j2, i1, i2 in self.mapping:
            if j1 <= mod_offset <= j2:
                if j2 == j1:
                    return i1
                ratio = (mod_offset - j1) / (j2 - j1)
                return int(i1 + ratio * (i2 - i1))
        return len(self.original)

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
                    'correction': " ".join([w[0] for w in corr_words[j1:j2]])
                })
        elif tag == 'delete':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': ''
                })
        elif tag == 'insert':
            pos = orig_words[i1][1] if i1 < len(orig_words) else len(original)
            suggestions.append({
                'start': pos,
                'end': pos,
                'original': '',
                'correction': " ".join([w[0] for w in corr_words[j1:j2]])
            })
    return suggestions

def test():
    original = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    spelling_corrected = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    # Wait, in the log, spelling DROPPED [4:9] محمد:. This means original was "قال محمد: علي ..."
    original = "قال محمد: علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    spelling_corrected = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    grammar_corrected = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوبات..."
    punct_corrected = "قال محمد علي: أننا حققنا نجاحا كبيرا في المشروع رغم الصعوبات...."

    suggestions = []
    mappers = []

    # 1. Spelling
    # Assume spelling generated the diff exactly as SequenceMatcher would:
    diffs = get_word_diffs(original, spelling_corrected)
    for d in diffs:
        d['type'] = 'spelling'
        suggestions.append(d)
    mappers.append(OffsetMapper(original, spelling_corrected))

    # 2. Grammar
    def map_range_to_original(start, end):
        curr_start, curr_end = start, end
        for mapper in reversed(mappers):
            curr_start = mapper.map_offset(curr_start)
            curr_end = mapper.map_offset(curr_end)
        return curr_start, curr_end

    diffs = get_word_diffs(spelling_corrected, grammar_corrected)
    for d in diffs:
        o_s, o_e = map_range_to_original(d['start'], d['end'])
        suggestions.append({
            'start': o_s, 'end': o_e, 'type': 'grammar',
            'original': original[o_s:o_e], 'correction': d['correction']
        })
    mappers.append(OffsetMapper(spelling_corrected, grammar_corrected))

    # 3. Punctuation
    diffs = get_word_diffs(grammar_corrected, punct_corrected)
    for d in diffs:
        o_s, o_e = map_range_to_original(d['start'], d['end'])
        suggestions.append({
            'start': o_s, 'end': o_e, 'type': 'punctuation',
            'original': original[o_s:o_e], 'correction': d['correction']
        })

    print("ALL SUGGESTIONS:")
    for s in suggestions:
        print(s)

    PRIORITY = {'grammar': 3, 'punctuation': 2, 'spelling': 1, 'autocomplete': 0}
    suggestions.sort(key=lambda s: PRIORITY.get(s['type'], 0), reverse=True)
    claimed_ranges = []
    resolved = []
    for s in suggestions:
        overlaps = False
        for (c_start, c_end, c_type) in claimed_ranges:
            if s['start'] < c_end and s['end'] > c_start:
                overlaps = True
                print(f"[OVERLAP] Dropped {s['type']} [{s['start']}:{s['end']}] '{s['original']}' — conflicts with {c_type}")
                break
        if not overlaps:
            resolved.append(s)
            claimed_ranges.append((s['start'], s['end'], s['type']))

if __name__ == "__main__":
    test()
