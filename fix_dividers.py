import re

with open('src/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the divider to use standard Tailwind classes and add shrink-0 so it doesn't disappear
old_div_nav = r'<div class="h-6 w-\[1\.5px\] bg-gray-300 dark:bg-gray-700 rounded-full"></div>'
new_div_nav = r'<div class="h-6 w-0.5 bg-gray-300 dark:bg-gray-600 rounded-full shrink-0"></div>'

old_div_footer = r'<div class="h-7 w-\[1\.5px\] bg-gray-300 dark:bg-gray-700 rounded-full"></div>'
new_div_footer = r'<div class="h-7 w-0.5 bg-gray-300 dark:bg-gray-600 rounded-full shrink-0"></div>'

html = re.sub(old_div_nav, new_div_nav, html)
html = re.sub(old_div_footer, new_div_footer, html)

with open('src/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Dividers fixed.")
