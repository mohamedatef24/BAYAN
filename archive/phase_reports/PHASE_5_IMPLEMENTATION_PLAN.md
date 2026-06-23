# Phase 5 — Implementation Plan

**Status:** Implemented  
**Architecture:** Option A — Supabase Anonymous + Google OAuth  

## File-by-file change list

### Created

| File | Purpose |
|------|---------|
| `src/js/auth/config.js` | Meta tag config loading |
| `src/js/auth/client.js` | Supabase client singleton |
| `src/js/auth/session.js` | Session state, isGuest, isGoogleUser |
| `src/js/auth/auth.js` | signInAsGuest, signInWithGoogle, linkGoogle, signOut, initAuth |
| `src/js/auth/auth-ui.js` | Auth gate, account menu, updateAuthUI |
| `src/js/vendor/supabase.min.js` | Offline vendor copy |
| `supabase/migrations/001_profiles.sql` | Profiles + triggers + RLS |
| `.env.example` | Supabase env documentation |

### Modified

| File | Change |
|------|--------|
| `src/index.html` | Meta tags, auth UI, scripts, async initAuth, summary XSS fix |
| `src/css/components.css` | Auth gate, menu, offline banner styles |
| `src/js/renderer.js` | Escape `title` attribute on suggestion spans (XSS) |

### Unchanged

| File |
|------|
| `src/js/selection.js` |
| `src/js/editor.js` (analyze/render/apply/loadDocumentText) |
| `src/js/documents/*` |
| `src/app.py` |

## UI mockup descriptions

**Auth gate (desktop):** Centered modal over blurred backdrop. Title "مرحباً بك في بيان", subtitle, primary "المتابعة كضيف", secondary Google button with icon.

**Auth gate (mobile):** Bottom sheet panel with same buttons full-width.

**Account menu:** Nav bar trigger with avatar + name. Dropdown: provider label, "ربط حساب Google" (guest only), "تسجيل الخروج".

**Offline banner:** Fixed strip below nav when Supabase unreachable.

## Risk assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| OAuth redirect misconfiguration | Medium | Document URLs in `.env.example` |
| XSS + localStorage tokens | High | Fixed summary + title XSS before auth |
| Anonymous auth disabled | Low | Dashboard checklist |
| linkIdentity browser support | Low | Fallback to signInWithOAuth |
| Auth blocks editor | Low | initAuth async; editor always inits |
