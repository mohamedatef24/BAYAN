import re

def fix_listener(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        js = f.read()
    
    # Replace the wrapping DOMContentLoaded for our appended theme toggle
    pattern = r"// ── Theme Toggle Logic ──\s*document\.addEventListener\('DOMContentLoaded',\s*\(\)\s*=>\s*\{"
    replacement = "// ── Theme Toggle Logic ──\n(function initBayanThemeToggle() {"
    
    # We also need to replace the closing `});` of our block with `})();`
    # We know it's at the very end of the file.
    
    new_js, count = re.subn(pattern, replacement, js)
    if count > 0:
        # replace the last `});` with `})();`
        new_js = new_js.rstrip()
        if new_js.endswith("});"):
            new_js = new_js[:-3] + "})();\n"
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_js)
        print(f"Fixed in {filepath}")
    else:
        print(f"Not found in {filepath}")

fix_listener('extension/popup.js')
fix_listener('extension/sidepanel/sidepanel.js')
