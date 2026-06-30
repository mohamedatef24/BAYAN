import re

def insert_divider(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # We look for the logo img and the span title, and insert a divider between them.
    # Pattern to match:
    # <img src="assets/icons/icon48.png" alt="بيان" width="28" height="28" style="border-radius:6px;">
    # <span class="bayan-header-title">بيان</span>
    
    # Let's match the closing bracket of the img tag (or its whitespace), followed by the span tag
    pattern = r'(<img[^>]+>)\s*(<span class="(?:bayan-header-title|sp-header-title)">بيان</span>)'
    
    # The divider to insert:
    divider = '\n      <div style="height:24px; width:2px; background-color:#d1d5db; border-radius:9999px; flex-shrink:0;"></div>\n      '
    
    # Replace
    new_html, count = re.subn(pattern, r'\1' + divider + r'\2', html)
    
    if count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"Updated {file_path}")
    else:
        print(f"No match found in {file_path}")

insert_divider('extension/popup.html')
insert_divider('extension/sidepanel/sidepanel.html')
