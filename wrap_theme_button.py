import re

def wrap_status_and_button(filepath, status_class):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # We want to replace the inserted button and the status indicator with a wrapper.
    # The pattern: the button we just inserted + the status indicator div
    pattern = r'(<button id="ext-theme-toggle"[^>]*>.*?</button>)\s*(<div class="' + status_class + '" id="status-indicator">.*?</div>)'
    
    wrapper = r'<div style="display: flex; align-items: center; gap: 12px;">\n\1\n\2\n</div>'
    
    new_html, count = re.subn(pattern, wrapper, html, flags=re.DOTALL)
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"Wrapped successfully in {filepath}")
    else:
        print(f"No match found in {filepath}")

wrap_status_and_button('extension/popup.html', 'bayan-header-status')
wrap_status_and_button('extension/sidepanel/sidepanel.html', 'sp-header-status')
