import difflib

orig = ['قال', 'محمد', 'علي', 'أننا']
corr = ['قال', 'محمد', 'علي:', 'أننا']

s = difflib.SequenceMatcher(None, orig, corr)
for tag, i1, i2, j1, j2 in s.get_opcodes():
    print(f"{tag:7} | orig[{i1}:{i2}]={orig[i1:i2]} | corr[{j1}:{j2}]={corr[j1:j2]}")
