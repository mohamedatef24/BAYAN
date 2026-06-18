import re
orig_word = 'محمد:'
res = re.search(r'[^ء-يآأإىa-zA-Z]', orig_word)
print("Regex match:", res)
