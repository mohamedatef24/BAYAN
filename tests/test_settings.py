import time
from playwright.sync_api import Page, expect

def test_settings_persistence(authenticated_page: Page):
    """Test theme persistence via Settings API (Phase 6.3) deterministically"""
    page = authenticated_page
    
    # Ensure UI is ready
    menu_trigger = page.locator("#auth-menu-trigger")
    menu_trigger.wait_for(state="visible", timeout=15000)
    
    # Wait for theme btn
    theme_btn = page.locator("#theme-toggle")
    theme_btn.wait_for(state="visible")
    
    # Capture the current theme by reading aria-label (more reliable than text for icon buttons)
    html_el = page.locator("html")
    data_theme_before = html_el.get_attribute("data-theme") or ""
    is_dark_before = "dark" in data_theme_before
    
    # Toggle the theme
    theme_btn.click(force=True)
    
    # Wait for the data-theme attribute to change on the html element
    if is_dark_before:
        # Was dark, now expect light
        page.wait_for_function("document.documentElement.getAttribute('data-theme') !== 'dark'", timeout=5000)
    else:
        # Was light, now expect dark
        page.wait_for_function("document.documentElement.getAttribute('data-theme') === 'dark'", timeout=5000)

    data_theme_after = html_el.get_attribute("data-theme") or ""
    is_dark_after = "dark" in data_theme_after
    
    # Confirm the toggle actually changed the theme
    assert is_dark_before != is_dark_after, "Theme did not toggle after click"
    
    # Wait for network idle to ensure settings are synced to Supabase
    page.wait_for_load_state("networkidle")
    # Buffer to ensure Supabase ACK
    page.wait_for_timeout(500)
    
    # Reload page
    page.reload()
    page.wait_for_load_state("networkidle")
    
    html_el = page.locator("html")
    # Check explicitly that it kept the class after reload
    reloaded_theme = html_el.get_attribute("data-theme") or ""
    reloaded_dark = "dark" in reloaded_theme
    
    assert is_dark_after == reloaded_dark, "Theme setting did not persist after reload"

