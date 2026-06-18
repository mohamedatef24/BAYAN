_PUNC_CHARS = set('،؛؟!.,:;?»«()[]{}…–—\u060C\u061B\u061F')

def _is_punctuation_only_change(original, correction):
    orig_letters = ''.join(c for c in original if c not in _PUNC_CHARS and not c.isspace())
    corr_letters = ''.join(c for c in correction if c not in _PUNC_CHARS and not c.isspace())

    if orig_letters != corr_letters:
        return False
    has_punc = any(c in _PUNC_CHARS for c in original) or any(c in _PUNC_CHARS for c in correction)
    return has_punc

print(_is_punctuation_only_change('محمد:', 'محمد'))
print(_is_punctuation_only_change('محمد:', 'محمّد'))
