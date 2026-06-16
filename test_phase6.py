from playwright.sync_api import sync_playwright
import time
import sys

def run_tests():
    print("Starting Phase 6 UI Verification Tests...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))

        # Auto-accept any prompts (like document rename/create)
        def handle_dialog(dialog):
            print(f"Dialog opened: {dialog.message}")
            if dialog.type == "prompt":
                dialog.accept("Test Document Auto")
            else:
                dialog.accept()

        page.on("dialog", handle_dialog)
        page.goto("http://localhost:5050")

        # --- GUEST LOGIN ---
        print("Logging in as Guest...")
        page.click("text=المتابعة كضيف")
        page.wait_for_timeout(2000)

        # Check for offline mode banner (should not be visible)
        offline_banner = page.locator("#auth-offline-banner")
        if offline_banner.is_visible():
            print("ERROR: Offline mode active. Cannot test cloud features.")
            sys.exit(1)

        # --- DOCUMENTS PERSISTENCE (Phase 6.1) ---
        print("Testing Documents Sidebar...")
        page.click("#docs-sidebar-toggle")
        page.wait_for_timeout(1000)

        print("Testing Create Document...")
        page.click("#docs-new-btn")
        page.wait_for_timeout(2000)

        title = page.locator("#doc-current-title").inner_text()
        print(f"Document created with title: {title}")
        if not title:
            print("ERROR: Document title is empty")
            sys.exit(1)

        print("Testing Manual Save...")
        page.click("#docs-sidebar-toggle") # Close sidebar
        page.wait_for_timeout(500)
        page.click("#write-tab", force=True)
        page.fill("#editor-container", "هذا نص تجريبي لحفظ المستند عبر Playwright.")
        page.click("#doc-save-btn", force=True)
        page.wait_for_timeout(2000)

        page.click("#docs-sidebar-toggle", force=True)
        page.wait_for_timeout(1000)
        docs = page.locator(".doc-list-item").count()
        print(f"Documents in sidebar: {docs}")
        if docs == 0:
            print("ERROR: Document not found in list")
            sys.exit(1)

        # --- SUMMARIES PERSISTENCE (Phase 6.2) ---
        print("Testing Summaries Cloud...")
        page.click("#summarize-tab")
        page.wait_for_timeout(500)
        
        # Inject fake summary directly into UI to speed up test (avoiding actual LLM call time)
        page.evaluate("document.getElementById('summary-text').innerText = 'هذا ملخص تجريبي.'")
        
        page.click("#save-summary-btn")
        print("Clicked Save Summary.")
        page.wait_for_timeout(2000)

        page.click("#summary-history-toggle")
        page.wait_for_timeout(1000)

        histories = page.locator(".summary-history-item").count()
        print(f"Summary history items: {histories}")
        if histories == 0:
            print("ERROR: Summary not saved in history")
            sys.exit(1)

        # --- SETTINGS SYNC (Phase 6.3) ---
        print("Testing Theme Sync...")
        # Since we use Guest mode, let's verify if theme change dispatches without error
        page.evaluate("setTheme('dark')")
        page.wait_for_timeout(2000) # wait for debounce

        print("All Tests Passed! 🎉")
        browser.close()

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"Test Execution Failed: {e}")
        sys.exit(1)
