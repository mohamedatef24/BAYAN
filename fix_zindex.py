import re

with open('src/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace z-50 with z-[1000] on the nav
html = re.sub(r'class="site-nav fixed top-0 right-0 left-0 z-50"', r'class="site-nav fixed top-0 right-0 left-0 z-[1000]"', html)

with open('src/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("z-index fixed.")
