from playwright.sync_api import Page, expect

def test_editor_stress(authenticated_page: Page):
    """Stress test the core editor engine with deterministic text injection."""
    editor = authenticated_page.locator("#editor-container")
    editor.wait_for(state="visible")
    
    editor.click()
    # Reset contents
    editor.focus()
    editor.evaluate("el => { el.innerHTML = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    
    text_to_type = "هذا نص تجريبي لاختبار أداء المحرر واستقراره أثناء الكتابة. "
    
    # 5 iterations of bounded deterministic text insertion
    for _ in range(5):
        editor.press_sequentially(text_to_type)
        # Yield to let sync handlers run
        authenticated_page.wait_for_timeout(100)
        editor.focus() # Ensure focus is not lost by sync rendering

    # Validate final content
    content = editor.inner_text()
    expected_content = (text_to_type * 5).strip()
    
    assert expected_content in content.replace("\n", ""), "Editor text loss detected due to contenteditable flake"
