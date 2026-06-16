"""
Build script for Vercel deployment.
Injects Supabase credentials from environment variables into index.html meta tags.

Usage:
  Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables, then run:
    python build.py
"""

import os
import sys

def main():
    html_path = os.path.join('src', 'index.html')
    
    if not os.path.exists(html_path):
        print(f"❌ {html_path} not found")
        sys.exit(1)
    
    supabase_url = os.environ.get('SUPABASE_URL', '')
    supabase_anon_key = os.environ.get('SUPABASE_ANON_KEY', '')
    
    if not supabase_url or not supabase_anon_key:
        print("⚠️  Warning: SUPABASE_URL or SUPABASE_ANON_KEY not set. Auth will run in offline mode.")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Inject Supabase credentials into meta tags
    html = html.replace(
        '<meta name="supabase-url" content="">',
        f'<meta name="supabase-url" content="{supabase_url}">'
    )
    html = html.replace(
        '<meta name="supabase-anon-key" content="">',
        f'<meta name="supabase-anon-key" content="{supabase_anon_key}">'
    )
    
    # Remove development-only SDK scripts that won't exist in production
    html = html.replace('<script src="/_sdk/element_sdk.js"></script>\n', '')
    html = html.replace('<script src="/_sdk/element_sdk.js"></script>\r\n', '')
    html = html.replace('<script src="/_sdk/data_sdk.js" type="text/javascript"></script>\n', '')
    html = html.replace('<script src="/_sdk/data_sdk.js" type="text/javascript"></script>\r\n', '')
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Supabase credentials injected into {html_path}")
    if supabase_url:
        print(f"   SUPABASE_URL: {supabase_url[:40]}...")
    print(f"   Dev SDK scripts removed")

if __name__ == '__main__':
    main()
