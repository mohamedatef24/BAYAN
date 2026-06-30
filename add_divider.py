import re

with open('src/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace Navbar
navbar_pattern = r'(<button onclick="showPage\(\'home\'\)" class="flex items-center) gap-3(" style="background:none;border:none;cursor:pointer;" aria-label="الرئيسية">)(.*?)(<span id="nav-brand" class="text-xl md:text-2xl font-bold text-gradient">بيان</span></button>)'
navbar_replacement = r'\1 gap-2.5 md:gap-3\2\3<div class="h-6 w-[1.5px] bg-gray-300 dark:bg-gray-700 rounded-full"></div>\4'
html = re.sub(navbar_pattern, navbar_replacement, html, flags=re.DOTALL)

# Replace Footer
footer_pattern = r'(<div class="flex items-center) gap-3( mb-4">)(.*?)(<span id="footer-brand" class="text-2xl font-bold text-gradient">بيان</span>)'
footer_replacement = r'\1 gap-2.5 md:gap-3\2\3<div class="h-7 w-[1.5px] bg-gray-300 dark:bg-gray-700 rounded-full"></div>\4'
html = re.sub(footer_pattern, footer_replacement, html, flags=re.DOTALL)

with open('src/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done replacing.")
