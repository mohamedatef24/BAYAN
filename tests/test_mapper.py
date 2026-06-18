import difflib

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

def test():
    original = "قال محمد: علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    spelling = "قال محمد علي أننا حققنا نجاحا كبيرا في المشروع رغم الصعوباالصعوبات...."
    
    mapper = OffsetMapper(original, spelling)
    
    # In spelling text, where is "علي"?
    # "قال محمد علي أننا"
    # "قال " -> 0:4
    # "محمد " -> 4:9
    # "علي" -> 9:12
    
    spelling_start = spelling.find("علي")
    spelling_end = spelling_start + 3
    print(f"Spelling string 'علي' is at [{spelling_start}:{spelling_end}]")
    
    orig_start = mapper.map_offset(spelling_start)
    orig_end = mapper.map_offset(spelling_end)
    print(f"Mapped to original: [{orig_start}:{orig_end}]")
    print(f"Original text at mapped span: '{original[orig_start:orig_end]}'")

if __name__ == "__main__":
    test()
