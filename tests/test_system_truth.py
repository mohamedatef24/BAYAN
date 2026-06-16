import re
from playwright.sync_api import Page, expect
from conftest import wait_for_sync_idle

def test_system_truth_data_consistency(authenticated_page: Page):
    """Create, edit, reload, and verify UI matches DB consistency."""
    page = authenticated_page
    
    sidebar = page.locator("#docs-sidebar")
    sidebar.wait_for(state="attached")
    
    # Open sidebar if needed
    if "is-open" not in sidebar.get_attribute("class"):
        page.evaluate("document.getElementById('docs-sidebar-toggle').click()")
        expect(sidebar).to_have_class("docs-sidebar is-open")
    
    # Create doc
    page.once("dialog", lambda dialog: dialog.accept("Truth Validation Doc"))
    new_btn = page.locator("#docs-new-btn")
    new_btn.wait_for(state="visible", timeout=10000)
    new_btn.evaluate("el => el.click()")
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    editor.click()
    editor.focus()
    editor.evaluate("el => { el.innerHTML = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    editor.press_sequentially("Deterministic truth data consistency test.", delay=10)
    
    wait_for_sync_idle(page)
    
    # Verify title in sidebar
    expect(page.locator(".doc-list-item__title").last).to_contain_text("Truth Validation Doc", timeout=5000)
    
    # Reload and verify
    page.reload()
    page.wait_for_load_state("networkidle")
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    expect(editor).to_contain_text("Deterministic truth data consistency test.", timeout=10000)

def test_system_truth_crash_recovery(authenticated_page: Page):
    """Simulate refresh during active save and ensure recovery."""
    page = authenticated_page
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    editor.click()
    editor.focus()
    editor.evaluate("el => { el.innerHTML = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    
    # Type and immediately crash/reload before debounce triggers
    editor.press_sequentially("Crash recovery testing payload.", delay=10)
    page.reload()
    page.wait_for_load_state("networkidle")
    
    # Verify recovery from localStorage queue
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    expect(editor).to_contain_text("Crash recovery testing payload.", timeout=10000)
    
    # Ensure it ultimately saves to cloud
    wait_for_sync_idle(page)
