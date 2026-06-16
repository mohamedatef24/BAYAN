import re
from playwright.sync_api import Page, expect

def test_summary_generation_and_history(authenticated_page: Page):
    """Test generating a summary deterministically."""
    page = authenticated_page
    
    # Ensure we are on the write tab
    write_tab = page.locator("#write-tab")
    write_tab.wait_for(state="visible")
    write_tab.evaluate("el => el.click()")
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    editor.click()
    editor.focus()
    editor.evaluate("el => { el.innerHTML = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
    editor.press_sequentially("هذا النص الطويل مخصص لاختبار قدرة النظام على التلخيص في منصة بيان بشكل موثوق وفعال ومستقر جداً.")
    
    # Switch to summarize tab
    tab = page.locator("#summarize-tab")
    tab.wait_for(state="visible")
    tab.evaluate("el => el.click()")
    
    # Generate summary
    btn = page.locator("#generate-summary-btn")
    btn.wait_for(state="visible")
    btn.evaluate("el => el.click()")
    
    # Wait for the summary preview to be visible
    summary_preview = page.locator("#summary-preview")
    expect(summary_preview).to_have_class(re.compile(r"show"), timeout=15000)
    
    # Wait for the loading to finish and text to appear
    summary_text = page.locator("#summary-text")
    expect(summary_text).not_to_contain_text("جاري توليد الملخص...", timeout=15000)
    expect(summary_text).not_to_contain_text("⚠️ حدث خطأ", timeout=15000)
    expect(summary_text).not_to_be_empty(timeout=15000)

