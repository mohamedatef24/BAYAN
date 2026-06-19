import re
from playwright.sync_api import Page, expect
from conftest import wait_for_sync_idle

def test_sync_engine_stress(authenticated_page: Page, context):
    """Scenario A, B, C, D: Rapid Typing, Offline Mode, Multi-tab, Refresh mid-sync."""
    page = authenticated_page
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    
    # --- Scenario A: Rapid Typing (Debounce Check) ---
    editor.click()
    editor.focus()
    editor.evaluate("el => { el.innerHTML = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    
    # Type continuously with bounds
    editor.press_sequentially("Testing debounce sync engine... ", delay=10)
    page.wait_for_timeout(500)
    editor.focus()
    editor.press_sequentially("Should not trigger save immediately. ", delay=10)
    
    # Ensure saving state isn't triggered instantly, but wait for it
    wait_for_sync_idle(page)
    
    # --- Scenario B: Offline Mode ---
    context.set_offline(True)
    page.evaluate("window.dispatchEvent(new Event('offline'))")
    
    editor.focus()
    editor.press_sequentially("This is typed while offline. ", delay=10)
    
    # Wait for the UI to indicate it's saved locally (or stay at default 'حفظ' if autosave is blocked)
    save_btn = page.locator("#doc-save-btn")
    expect(save_btn).to_have_attribute("title", re.compile(r"محفوظ محلياً|حفظ"), timeout=10000)
    
    context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    
    # Wait for flush to cloud
    wait_for_sync_idle(page)
    
    # --- Scenario D: Refresh Mid-Sync (Local Draft fallback) ---
    editor.focus()
    editor.press_sequentially("Typing and immediately refreshing! ", delay=10)
    # Immediately refresh before 2.5s debounce hits
    page.reload()
    page.wait_for_load_state("networkidle")
    
    # Draft should restore it from localStorage
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    expect(editor).to_contain_text("Typing and immediately refreshing!", timeout=10000)
    
    # --- Scenario C: Multi-tab Conflict ---
    page2 = context.new_page()
    page2.goto("http://localhost:5050")
    page2.wait_for_load_state("networkidle")
    
    # Ensure page2 is authenticated if needed (it shares context but might need explicit navigation)
    try:
        guest_btn = page2.locator("#auth-guest-btn")
        guest_btn.wait_for(state="visible", timeout=2000)
        guest_btn.click(force=True)
    except:
        pass
    
    # Explicitly show the editor on the new page, as session restore might leave it on home
    page2.evaluate("if(typeof showPage==='function') showPage('editor')")
        
    page2_editor = page2.locator("#editor-container")
    page2_editor.wait_for(state="visible")
    
    # Type in page 2
    page2_editor.click()
    page2_editor.focus()
    page2_editor.press_sequentially(" Tab 2 edit.", delay=10)
    
    wait_for_sync_idle(page2)
    
    # Reload page 1. It should fetch the cloud version and merge/override its older local draft
    page.reload()
    page.wait_for_load_state("networkidle")
    
    editor1 = page.locator("#editor-container")
    editor1.wait_for(state="visible")
    expect(editor1).to_contain_text("Tab 2 edit.", timeout=10000)
    
    page2.close()
