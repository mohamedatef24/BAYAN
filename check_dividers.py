import re
with open('src/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
matches = re.findall(r'<div class="h-[67] w-\[1\.5px\] bg-gray-300 dark:bg-gray-700 rounded-full"></div>', html)
print(f'Found {len(matches)} dividers.')
