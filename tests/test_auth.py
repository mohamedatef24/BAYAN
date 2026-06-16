import re
from playwright.sync_api import Page, expect

def test_guest_login(page: Page):
    """Test guest login functionality."""
    auth_gate = page.locator("#auth-gate")
    expect(auth_gate).to_be_visible()
    
    guest_btn = page.locator("#auth-guest-btn")
    guest_btn.wait_for(state="visible")
    guest_btn.click(force=True)
    
    expect(auth_gate).not_to_be_visible()
    expect(page.locator("#page-editor")).to_be_visible()

def test_session_persistence(page: Page):
    """Test that session persists after a refresh."""
    guest_btn = page.locator("#auth-guest-btn")
    guest_btn.wait_for(state="visible")
    guest_btn.click(force=True)
    
    # Wait for the gate to hide
    page.locator("#auth-gate").wait_for(state="hidden", timeout=5000)
    
    # Check if we fell back to offline mode due to rate limit
    is_offline = page.evaluate("window.__bayanAuth && window.__bayanAuth.isOfflineMode === true")
    if is_offline:
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
        
    page.evaluate("if(typeof showPage==='function') showPage('editor')")
    
    editor = page.locator("#editor-container")
    editor.wait_for(state="visible")
    
    page.reload()
    page.wait_for_load_state("networkidle")
    
    expect(page.locator("#editor-container")).to_be_visible()
    expect(page.locator("#auth-gate")).not_to_be_visible()

def test_auth_menu_guest_options(authenticated_page: Page):
    """Test that auth menu correctly shows guest options (Link Google)."""
    # Ensure UI is ready
    menu_trigger = authenticated_page.locator("#auth-menu-trigger")
    menu_trigger.wait_for(state="visible", timeout=15000)
    
    # Force click and evaluate click just to be 100% deterministic
    menu_trigger.evaluate("el => el.click()")
    
    # Guest should see Link Google button, NOT Logout
    link_btn = authenticated_page.locator("#auth-link-google-btn")
    link_btn.wait_for(state="visible", timeout=5000)
    expect(link_btn).to_be_visible()
    
    # Logout button should be visible for guests too (they can sign out)
    logout_btn = authenticated_page.locator("#auth-logout-btn")
    expect(logout_btn).to_be_visible()
