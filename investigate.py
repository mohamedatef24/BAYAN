import re
html = open('src/index.html', encoding='utf-8').read()
editor = open('src/js/editor.js', encoding='utf-8').read()
ui = open('src/js/ui.js', encoding='utf-8').read()

# 1. Feature sections count
features_start = html.find('page-features')
features_section = html[features_start:features_start+30000]
h3_count = features_section.count('</h3')
print(f'1. Feature h3 count in features page: {h3_count}')

# 2. window.confirm
lines = html.split('\n')
for i, line in enumerate(lines, 1):
    if 'window.confirm' in line:
        is_comment = '//' in line
        print(f'2. window.confirm at line {i} (comment={is_comment}): {line.strip()[:100]}')

# 3. render() in editor.js
lines2 = editor.split('\n')
for i, line in enumerate(lines2, 1):
    stripped = line.strip()
    if 'render' in stripped and '(' in stripped and not stripped.startswith('//'):
        if 'renderWith' in stripped or 'render(' in stripped:
            print(f'3. editor.js L{i}: {stripped[:80]}')

# 4. نصك ممتاز in ui.js - prove it
idx = ui.find('\u0646\u0635\u0643')
if idx >= 0:
    context = ui[max(0,idx-20):idx+60]
    print(f'4. نصك found in ui.js at idx {idx}: {context}')
