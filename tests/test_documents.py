from playwright.sync_api import Page, expect
from conftest import wait_for_sync_idle

def test_document_lifecycle(authenticated_page: Page):
    """Test creating, switching, and reloading documents deterministically."""
    page = authenticated_page
    
    sidebar = page.locator("#docs-sidebar")
    sidebar.wait_for(state="attached")
    
    # Register dialog handler ONCE
    expected_title_ref = ["Test Document 0"]
    page.on("dialog", lambda dialog: dialog.accept(expected_title_ref[0]))
    
    # 1. Create multiple documents
    for i in range(3):
        # Open sidebar if not open by checking class
        if "is-open" not in sidebar.get_attribute("class"):
            page.evaluate("document.getElementById('docs-sidebar-toggle').click()")
            # Wait for animation
            expect(sidebar).to_have_class("docs-sidebar is-open")
        
        expected_title_ref[0] = f"Test Document {i}"
        
        # Click new document button
        new_btn = page.locator("#docs-new-btn")
        new_btn.wait_for(state="visible", timeout=10000)
        new_btn.evaluate("el => el.click()")
        
        # Wait for the new document to be created and appear in the list
        expect(page.locator(f".doc-list-item__title:has-text('{expected_title_ref[0]}')").first).to_be_visible(timeout=10000)
        
        # Write content
        editor = page.locator("#editor-container")
        editor.wait_for(state="visible")
        editor.click()
        editor.focus()
        editor.evaluate("el => { el.innerHTML = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
        editor.press_sequentially(f"Content for document {i}", delay=10)
        
        # Wait for sync to finish before continuing loop
        wait_for_sync_idle(page)
    
    # 2. Switch between documents
    if "is-open" not in sidebar.get_attribute("class"):
        page.evaluate("document.getElementById('docs-sidebar-toggle').click()")
        expect(sidebar).to_have_class("docs-sidebar is-open")
        
    docs = page.locator(".doc-list-item__title").all()
    assert len(docs) >= 3, "Not all documents were created"
    
    # Click on the first created document (index 0 which is oldest)
    docs[-1].evaluate("el => el.click()")
    
    # Wait for the editor to load the content
    editor = page.locator("#editor-container")
    expect(editor).to_contain_text("Content for document 0", timeout=10000)
    
    # 3. Reload and verify persistence
    page.reload()
    page.wait_for_load_state("networkidle")
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    expect(editor).to_contain_text("Content for document 0", timeout=10000)
