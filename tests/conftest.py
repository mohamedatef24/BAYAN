import pytest
from playwright.sync_api import Page, expect

# Global settings
BASE_URL = "http://localhost:5050"

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        }
    }

@pytest.fixture
def page(context):
    page = context.new_page()
    # Intercept console logs to debug tests
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    
    # Auto-accept all dialogs to prevent tests from hanging
    def handle_dialog(dialog):
        print(f"Dialog: {dialog.message}")
        if dialog.type == "prompt":
            dialog.accept("Test Automated Input")
        else:
            dialog.accept()

    # NOTE: We do NOT handle dialog globally here anymore because we want
    # to handle it explicitly in tests (like test_documents.py) to be deterministic.
    # page.on("dialog", handle_dialog)
    
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    return page

@pytest.fixture
def authenticated_page(page: Page):
    """Fixture that provides a page already logged in as a guest."""
    print("Logging in as Guest...")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    # Wait for the guest button to be visible
    guest_btn = page.locator("#auth-guest-btn")
    guest_btn.wait_for(state="visible")
    guest_btn.click(force=True)
    
    # Wait for the gate to hide (it hides on both success and offline mode)
    page.locator("#auth-gate").wait_for(state="hidden", timeout=5000)
    
    # Check if we fell back to offline mode due to rate limit
    is_offline = page.evaluate("window.__bayanAuth && window.__bayanAuth.isOfflineMode === true")
    if is_offline:
        print("Rate limit hit! Injecting fallback session...")
        # Mock all auth endpoints to prevent Supabase from invalidating our fake session
        page.route("**/auth/v1/**", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"id":"81f2f41b-de4f-4836-b633-8a1fa9dacc5e","aud":"authenticated","role":"authenticated","email":"","phone":"","app_metadata":{},"user_metadata":{},"identities":[],"is_anonymous":true}'
        ))
        
        fallback_session = '{"access_token":"eyJhbGciOiJFUzI1NiIsImtpZCI6ImRmODMwMThhLTViNjMtNDcyOS1iNmFkLTdkMmVjYWQxNmY1OSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3JoYmdxam1ranZ5emd4aGV5ZXl0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4MWYyZjQxYi1kZTRmLTQ4MzYtYjYzMy04YTFmYTlkYWNjNWUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgxNjMwMjA3LCJpYXQiOjE3ODE2MjY2MDcsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnt9LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJhbm9ueW1vdXMiLCJ0aW1lc3RhbXAiOjE3ODE2MjY2MDd9XSwic2Vzc2lvbl9pZCI6IjlmYTVmOTc2LTM0NWItNDE0MS1iNjk5LTczYmZlZTc5Nzg1MCIsImlzX2Fub255bW91cyI6dHJ1ZX0.GrkxmXX3wARv_8A71FOGYXJhQHJ7rn3MFn9Zhv9_qIMgEYg53_wQZ98-7HQxK4tQZZp1jVNY7oQ9U7V_N58eDA","token_type":"bearer","expires_in":3600,"expires_at":1781630207,"refresh_token":"doyufdzwficb","user":{"id":"81f2f41b-de4f-4836-b633-8a1fa9dacc5e","aud":"authenticated","role":"authenticated","email":"","phone":"","last_sign_in_at":"2026-06-16T16:16:47.871879355Z","app_metadata":{},"user_metadata":{},"identities":[],"created_at":"2026-06-16T16:16:47.867138Z","updated_at":"2026-06-16T16:16:47.874546Z","is_anonymous":true}}'
        page.evaluate("([k, v]) => localStorage.setItem(k, v)", ["sb-rhbgqjmkjvyzgxheyeyt-auth-token", fallback_session])
        page.reload()
        page.wait_for_load_state("networkidle")
        page.locator("#auth-gate").wait_for(state="hidden")

    # Also ensure the guest menu is visible just in case
    page.locator("#auth-menu-trigger").wait_for(state="visible")
    
    # Navigate to editor explicitly
    page.evaluate("if(typeof showPage==='function') showPage('editor')")
    
    # Wait for the UI to update to the editor
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    
    # Wait for network idle to ensure sync/auth initialization is complete
    page.wait_for_load_state("networkidle")
    
    return page

def wait_for_sync_idle(page: Page):
    """Helper to wait for sync to finish (debounce + save).
    
    Accepts any of these save button title states:
    - 'حفظ' = default idle (no save triggered yet)
    - 'تم الحفظ' = saved to cloud
    - 'محفوظ محلياً' = saved locally (offline)
    - 'خطأ في الحفظ' = save error
    - 'حفظ (يوجد تغييرات غير محفوظة)' = post-save idle with pending changes
    """
    import re
    save_btn = page.locator("#doc-save-btn")
    # Wait for debounce to complete (2.5s) plus buffer
    page.wait_for_timeout(3000)
    # Accept any non-"saving" state
    expect(save_btn).not_to_have_attribute("title", "جاري الحفظ...", timeout=15000)

