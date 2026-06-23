# Phase 5 — Authentication Architecture Plan

**Project:** Bayan (بيان)  
**Date:** 2026-06-15  
**Status:** Architecture plan only — no implementation  
**Provider:** Supabase Auth  

---

## Executive Summary

Phase 5 adds **identity only**: who is using the app. It does **not** add document persistence, cloud sync, or backend authorization for AI routes. That belongs to Phase 6.

**Supported methods:**

| Method | Supabase mechanism |
|--------|-------------------|
| Continue as Guest | `signInAnonymously()` |
| Continue with Google | `signInWithOAuth({ provider: 'google' })` |

**Explicitly out of scope:** email/password, password reset, email verification, roles, admin panel.

**Architecture principle:** Auth wraps the existing SPA shell. **Zero changes** to `renderer.js`, `selection.js`, or editor analyze/render/selection flows. Editor continues to use `getEditorText()` / `loadDocumentText()` unchanged.

---

## Current State (Baseline)

| Layer | Today |
|-------|-------|
| Frontend | Single `index.html` + vanilla JS modules, no auth |
| Editor | `editor.js` → `selection.js` + `renderer.js` |
| Backend | Flask `app.py`, open CORS, no JWT validation |
| Persistence | Browser-only (contenteditable + localStorage for theme) |
| Login UI | Non-functional marketing placeholders |

Phase 5 introduces Supabase on the **client** first. Flask AI endpoints remain public until Phase 6 optionally adds JWT checks.

---

# 1. Authentication Flow

## 1.1 Guest User Flow

**Intent:** Immediate access with zero friction; obtain a real Supabase `user.id` for Phase 6 FK relationships.

```
User opens Bayan
    ↓
Auth bootstrap: getSession()
    ↓
No session?
    ↓
Show Auth Gate (modal or dedicated strip — not blocking editor forever)
    ↓
User clicks "المتابعة كضيف"
    ↓
supabase.auth.signInAnonymously()
    ↓
Session created (anonymous user in auth.users)
    ↓
Ensure profile row exists (Phase 5 hook or Phase 6 trigger)
    ↓
Hide auth gate → showPage('editor') [recommended for demo]
    ↓
Editor works exactly as Phase 1/4 (local contenteditable only)
```

**Guest identity:**

- Supabase assigns `auth.users.id` (UUID)
- `is_anonymous = true` in user metadata
- Display label: **"ضيف"** or **"مستخدم ضيف"**

**Local editor content:** Unchanged — still in DOM only. Phase 6 will persist using this `user.id`.

**Optional shortcut (demo mode):** Auto-call `signInAnonymously()` on first visit without showing gate — show gate only when user explicitly wants Google. **Recommendation:** Show gate once; remember choice in `sessionStorage` flag `bayan-auth-dismissed` only for UX, not for security.

---

## 1.2 Google Login Flow

**Intent:** Upgrade guest to identified user, or sign in directly.

### Path A — Guest upgrades to Google

```
Guest session active (anonymous)
    ↓
User clicks "المتابعة باستخدام Google"
    ↓
If anonymous: linkIdentity OR signInWithOAuth with data migration plan
    ↓
OAuth redirect → Google consent
    ↓
Redirect to app callback URL
    ↓
Supabase exchanges code → session with Google identity
    ↓
Same or new user.id (see Guest-to-User upgrade in §6)
    ↓
Update UI: show name, avatar, "مسجل عبر Google"
    ↓
Phase 6: migrate local/guest documents to user.id
```

**Recommended Supabase approach:** Use **`linkIdentity({ provider: 'google' })`** when upgrading from anonymous session — preserves `user.id` and simplifies Phase 6 FK consistency.

### Path B — Direct Google (no prior session)

```
No session → User clicks Google
    ↓
signInWithOAuth({ provider: 'google' })
    ↓
OAuth redirect → return → session established
    ↓
Profile row created
    ↓
Enter app
```

**Redirect URLs required:**

- Local: `http://localhost:5000/` (or dedicated `/auth/callback` hash route)
- Production: `https://<your-domain>/`

Supabase JS v2 handles hash fragment tokens on return automatically when `detectSessionInUrl: true`.

---

## 1.3 Logout Flow

```
User opens account menu → "تسجيل الخروج"
    ↓
Confirm dialog (optional but recommended if editor has unsaved text)
    ↓
supabase.auth.signOut()
    ↓
Clear client auth state:
  - window.__bayanUser = null
  - Do NOT clear editor text (Phase 5) — warn user instead
    ↓
Show Auth Gate again
    ↓
User chooses Guest or Google again
```

**Phase 5 rule:** Logout clears **session only**, not editor content. Phase 6 adds "save before logout?" when cloud sync exists.

---

## 1.4 Session Restoration Flow

```
Page load (before or parallel to initEditor)
    ↓
Load Supabase client with env config
    ↓
const { data: { session } } = await supabase.auth.getSession()
    ↓
If session:
  - Parse user (anonymous vs Google via app_metadata / identities)
  - updateAuthUI(session.user)
  - Skip auth gate
Else:
  - Show auth gate
    ↓
supabase.auth.onAuthStateChange((event, session) => { ... })
  - SIGNED_IN → update UI
  - SIGNED_OUT → show gate
  - TOKEN_REFRESHED → silent
  - USER_UPDATED → refresh avatar/name
    ↓
Continue initTheme → initUI → initEditor → initDocuments
```

**Order constraint:** Auth bootstrap must not block editor script loading. Editor modules load synchronously; auth can resolve in parallel and only gate **optional** UI (nav account menu), not editor internals.

**Recommended init order in `index.html`:**

```
initAuth()          → async, sets session state
initTheme()         → sync
initUI()            → sync (auth UI updates when session ready)
initEditor()        → sync, unchanged
initDocuments()     → sync, unchanged
```

---

# 2. UI Design

## 2.1 Required UI Screens

| Screen | Purpose | Blocks editor? |
|--------|---------|----------------|
| **Auth Gate** | Guest / Google choice | Soft gate — overlay or inline banner; recommend dismissible after choice |
| **Account Menu** | Logged-in state, logout | No |
| **Auth Loading** | OAuth return / session restore | Brief spinner only |

**No separate login page required** — modal/sheet aligned with Phase 2 patterns keeps changes minimal.

## 2.2 Required Buttons

| Button (Arabic) | Action |
|-----------------|--------|
| **المتابعة كضيف** | `signInAnonymously()` |
| **المتابعة باستخدام Google** | `signInWithOAuth({ provider: 'google' })` |
| **تسجيل الخروج** | `signOut()` (in account menu) |

**Optional (Phase 5):**

| Button | Action |
|--------|--------|
| **تسجيل الدخول** (nav) | Opens auth gate if no session |
| **ربط حساب Google** | Shown to guest users in account menu → `linkIdentity` |

## 2.3 User Menu Design

**Desktop (nav bar, left of theme toggle in RTL layout):**

```
[ Avatar or guest icon ▾ ]
  ├─ Display name / "ضيف"
  ├─ Auth provider badge (Google icon or "ضيف")
  ├─ ─────────────
  └─ تسجيل الخروج
```

**Guest-specific menu item:**

```
  └─ ربط حساب Google   (only when is_anonymous)
```

**Styling:** Reuse Phase 2 `.doc-dropdown` / `.nav-link` patterns from `components.css`. New classes: `.auth-menu`, `.auth-gate`, `.auth-btn-google`, `.auth-btn-guest`.

## 2.4 Mobile Behavior

| Element | Mobile behavior |
|---------|-----------------|
| Auth Gate | Full-width bottom sheet (reuse `#bottom-sheet` pattern) OR centered modal |
| Account menu | Inside `#mobile-drawer` below nav links + duplicate compact trigger in nav bar |
| Google OAuth | Same redirect flow; ensure mobile browser allows popup/redirect |
| Guest button | Full-width, min-height 44px (existing touch target standard) |

**Do not** add auth to editor toolbar — keep import/export/editor actions untouched.

---

# 3. Frontend Architecture

## 3.1 New Files to Create

```
src/js/auth/
  config.js       # Reads SUPABASE_URL + SUPABASE_ANON_KEY (injected or meta tags)
  client.js       # Single Supabase client singleton
  session.js      # getSession, onAuthStateChange, isGuest, isGoogleUser
  auth.js         # signInAsGuest, signInWithGoogle, signOut, linkGoogle
  auth-ui.js      # Auth gate, account menu, updateAuthUI()
```

**Vendor (offline demo reliability):**

```
src/js/vendor/supabase.min.js   # @supabase/supabase-js UMD build
```

**Optional Phase 5 SQL (documentation only, applied in Supabase dashboard):**

```
supabase/migrations/001_profiles.sql   # profiles table + trigger — prep for Phase 6
```

## 3.2 Files to Modify

| File | Change | Risk |
|------|--------|------|
| `src/index.html` | Auth gate markup, account menu, script tags, `initAuth()` in DOMContentLoaded | Low |
| `src/css/components.css` | Auth gate, Google button, account dropdown styles | Low |
| `src/js/ui.js` | Optional: call `updateAuthUI()` from shared init — or keep all auth UI in `auth-ui.js` | Low |
| `.env.example` | Document Supabase vars | None |

## 3.3 Files That Must NOT Change (Phase 5)

| File | Reason |
|------|--------|
| `src/js/renderer.js` | Phase 1 stable |
| `src/js/selection.js` | Phase 1 stable |
| `src/js/editor.js` | No auth in analyze/render/apply paths |
| `src/js/documents/*` | Import/export unchanged |
| `src/app.py` | No JWT required in Phase 5 |

## 3.4 Integration with Editor Architecture

Auth lives **above** the editor, not inside it:

```
┌─────────────────────────────────────────┐
│  Nav + Auth (Phase 5)                   │
├─────────────────────────────────────────┤
│  Editor Page                            │
│    getEditorText() / loadDocumentText() │  ← unchanged
│    renderer.js / selection.js           │  ← unchanged
├─────────────────────────────────────────┤
│  Flask /api/* (no auth Phase 5)         │
└─────────────────────────────────────────┘
```

**Phase 6 hook point (prepare now, implement later):**

```javascript
// Future — NOT Phase 5
window.__bayanAuth = {
  userId: session?.user?.id ?? null,
  isGuest: session?.user?.is_anonymous ?? true,
  getAccessToken: () => session?.access_token
};
```

Editor and documents modules **must not import** auth modules. Only nav/shell reads auth state.

---

# 4. Supabase Setup

## 4.1 Required Supabase Project Configuration

| Setting | Value |
|---------|-------|
| Project region | Closest to users (e.g. EU if MENA/Europe audience) |
| Auth providers | **Google enabled**; Email disabled |
| Anonymous sign-ins | **Enabled** (Dashboard → Authentication → Providers → Anonymous) |
| Email auth | **Disabled** |
| Phone auth | **Disabled** |
| Confirm email | N/A (email not used) |

## 4.2 Google OAuth Configuration

**Google Cloud Console:**

1. Create OAuth 2.0 Client ID (Web application)
2. Authorized JavaScript origins:
   - `http://localhost:5000`
   - `https://<production-domain>`
3. Authorized redirect URIs:
   - `https://<project-ref>.supabase.co/auth/v1/callback`

**Supabase Dashboard → Authentication → Providers → Google:**

- Paste Google Client ID and Client Secret
- Enable Google provider

## 4.3 Redirect URL Configuration (Supabase)

**Authentication → URL Configuration:**

| Field | Example |
|-------|---------|
| Site URL | `http://localhost:5000` (dev) |
| Redirect URLs | `http://localhost:5000/**`, `https://your-domain.com/**` |

## 4.4 Required Environment Variables

**Frontend (public — safe to expose anon key):**

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | Public anon key |

**Delivery mechanism (pick one):**

| Approach | Demo-friendly? |
|----------|----------------|
| Inline `<meta name="supabase-url" content="...">` in `index.html` | ✅ Simplest for graduation |
| `src/js/auth/config.js` with placeholders replaced at deploy | ✅ |
| Flask injects vars into template | ⚠️ Requires templating change |

**Never expose:**

| Variable | Location |
|----------|----------|
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only, Phase 6+ |

**Backend Phase 5:** No new env vars required. Phase 6 adds optional `SUPABASE_JWT_SECRET` for Flask JWT verification.

## 4.5 Local Development

```
# .env.example (documentation)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
```

Run Flask as today: `python run_app.py` — Supabase auth runs entirely in browser.

---

# 5. Database Preparation (Phase 6 Readiness)

Phase 5 **defines schema** and optionally applies **profiles-only** migration. Full CRUD for documents/summaries/settings is Phase 6.

## 5.1 Table: `profiles`

Links public profile data to `auth.users`.

```sql
-- Conceptual — implement in Phase 5 or early Phase 6
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  auth_provider text not null default 'anonymous',  -- 'anonymous' | 'google'
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

**Trigger on signup:**

```sql
-- After insert on auth.users → insert into profiles
-- Set auth_provider from raw_app_meta_data or identities
```

Phase 5 can deploy this trigger so every guest/Google user has a profile row before Phase 6.

## 5.2 Table: `documents` (Phase 6 — schema only in Phase 5 docs)

```sql
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text default 'مستند بدون عنوان',
  content text not null,
  word_count int,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

**Phase 5 prep:** Ensure `user_id` type matches Supabase auth UUID. No frontend reads/writes yet.

## 5.3 Table: `summaries` (Phase 6)

```sql
create table public.summaries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
  source_text_hash text,          -- optional dedup
  summary_text text not null,
  length_preset text,             -- short | medium | long
  created_at timestamptz default now()
);
```

**Phase 5 prep:** Summarize tab in `index.html` continues calling Flask directly. Phase 6 adds optional save after generate.

## 5.4 Table: `settings` (Phase 6)

```sql
create table public.settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  theme text default 'dark',       -- mirrors bayan-theme localStorage
  language text default 'ar',
  preferences jsonb default '{}',
  updated_at timestamptz default now()
);
```

**Phase 5 prep:** Theme stays in `localStorage` (`bayan-theme`). Phase 6 syncs on login.

## 5.5 Row-Level Security (enable in Phase 5, policies Phase 6)

```sql
alter table public.profiles enable row level security;
-- Phase 6: create policy "users read/update own profile"
-- auth.uid() = id
```

Document/summary/settings RLS policies written in Phase 6 when tables are created.

---

# 6. Security Considerations

## 6.1 Session Handling

| Topic | Approach |
|-------|----------|
| Session storage | Supabase JS default: `localStorage` key `sb-<ref>-auth-token` |
| Token refresh | Automatic via Supabase client |
| Session lifetime | Supabase project JWT expiry settings (default 1 hour access, refresh token longer) |
| Tab sync | `onAuthStateChange` handles multi-tab |

**Risk:** XSS can steal tokens from localStorage — mitigated by Phase 5 hardening (summary XSS fix) before auth ships.

## 6.2 Token Storage

| Token | Frontend | Backend Phase 5 |
|-------|----------|-----------------|
| Access token (JWT) | Supabase client memory + localStorage | Not used |
| Refresh token | localStorage | Not used |
| Anon key | config.js / meta tag | N/A |
| Service role | **Never** | Phase 6 server only |

**Do not** manually copy JWT into cookies in Phase 5.

## 6.3 Logout Behavior

- `signOut()` clears Supabase session and localStorage auth entry
- Editor text remains (warn user)
- Phase 6: optional `signOut({ scope: 'local' })` vs global — use default global sign-out

## 6.4 Guest-to-User Upgrade Path

**Recommended: Supabase Anonymous + Link Identity**

```
Guest (anonymous UUID = abc-123)
    ↓
User clicks "ربط حساب Google"
    ↓
linkIdentity({ provider: 'google' })
    ↓
Same user.id = abc-123 (identity linked)
    ↓
Phase 6 documents.user_id = abc-123 — no migration needed
```

**Fallback if linkIdentity unavailable:**

```
signInWithOAuth (new session, new user.id = xyz-789)
    ↓
Phase 6 migration job: copy local documents from guest id to new id
    ↓
More complex — avoid if possible
```

**Phase 5 deliverable:** Document chosen strategy in code comments and Phase 6 plan.

## 6.5 AI API Security (Phase 5 stance)

Flask `/api/analyze`, `/api/summarize` remain **unauthenticated** in Phase 5.

**Rationale:** Minimize changes; models are local; graduation demo runs on localhost.

**Phase 6 option:** Optional JWT middleware — reject requests without valid Supabase JWT for rate limiting per user.

---

# 7. Migration Plan (Implementation Order)

## Step 1 — Supabase Project Setup (0.5 day)

- [ ] Create Supabase project
- [ ] Enable Anonymous auth
- [ ] Enable Google provider + Google Cloud OAuth
- [ ] Configure redirect URLs
- [ ] Copy URL + anon key to `.env.example`

**Risk:** Low  
**Demo impact:** None until frontend wired

---

## Step 2 — Database Prep: Profiles Only (0.5 day)

- [ ] Apply `profiles` table migration
- [ ] Create `handle_new_user()` trigger on `auth.users`
- [ ] Enable RLS on `profiles`; policy: user reads/updates own row
- [ ] Verify guest signup creates profile with `auth_provider = 'anonymous'`

**Risk:** Low  
**Prepares Phase 6:** ✅ user rows exist

---

## Step 3 — Frontend Auth Module (1 day)

- [ ] Add `supabase.min.js` vendor copy + CDN fallback
- [ ] Create `src/js/auth/*` modules
- [ ] Implement `initAuth()`, session restore, `onAuthStateChange`
- [ ] Expose `window.__bayanAuth` read-only facade

**Risk:** Low — isolated new files  
**Must not touch:** renderer.js, selection.js, editor.js

---

## Step 4 — Auth UI (1 day)

- [ ] Add auth gate markup to `index.html`
- [ ] Add account menu to nav (desktop + mobile drawer)
- [ ] Style in `components.css` (match Phase 2 tokens)
- [ ] Wire buttons: Guest, Google, Logout, Link Google (guest only)

**Risk:** Low  
**Demo impact:** Visible login flow

---

## Step 5 — Init Integration (0.5 day)

- [ ] Update `DOMContentLoaded`: `initAuth()` before or parallel to `initEditor()`
- [ ] Ensure auth gate does not prevent `initEditor()` / `initDocuments()`
- [ ] OAuth return: handle URL hash cleanup if needed

**Risk:** Medium — test OAuth redirect carefully  
**Regression test:** `node test_renderer.js`, manual editor typing

---

## Step 6 — Guest & Google E2E Testing (0.5 day)

- [ ] Guest: anonymous session, profile row created
- [ ] Google: OAuth round-trip on localhost
- [ ] Guest → Google linkIdentity preserves user.id
- [ ] Logout → re-auth both paths
- [ ] Session restore after page refresh
- [ ] Mobile drawer account menu

**Risk:** Medium (OAuth redirect URLs)  
**Demo impact:** Critical path validated

---

## Step 7 — Documentation & Phase 6 Handoff (0.5 day)

- [ ] Update README with Supabase setup steps
- [ ] Document `documents`, `summaries`, `settings` schema (not implemented)
- [ ] Document RLS policy templates for Phase 6
- [ ] Add auth section to graduation demo checklist

**Total estimate:** **4–5 days** (single developer)

---

# 8. Risk Summary

| Risk | Level | Mitigation |
|------|-------|------------|
| Breaking editor on auth init | Low | Auth module isolated; editor init unchanged |
| OAuth redirect misconfiguration | Medium | Test localhost + production URLs early |
| Anonymous users disabled in Supabase | Low | Verify dashboard setting before coding |
| XSS + localStorage token theft | Medium | Ship Priority 1 security fixes before Phase 5 |
| linkIdentity browser support | Low | Test on Chrome/Edge; document fallback |
| Scope creep (email auth, roles) | Medium | Strict scope doc; code review checklist |

---

# 9. Phase 5 Success Criteria

| Criterion | Required |
|-----------|----------|
| Guest can enter app and use editor | ✅ |
| Google login works via OAuth | ✅ |
| Logout works | ✅ |
| Session restores on refresh | ✅ |
| Guest can link Google without new user.id | ✅ (linkIdentity) |
| `renderer.js` / `selection.js` unchanged | ✅ |
| `editor.js` analyze/render/apply unchanged | ✅ |
| Import/export unchanged | ✅ |
| Profile row exists for each auth user | ✅ |
| No document DB reads/writes yet | ✅ (Phase 6) |
| No email/password UI or backend | ✅ |

---

# 10. Phase 6 Preview (Out of Scope for Phase 5)

Phase 6 will use Phase 5 `user.id` to:

1. Save/load editor content to `documents` table
2. Persist summaries to `summaries` table
3. Sync theme to `settings` table
4. Optionally protect Flask routes with JWT
5. Migrate guest local content on Google link if needed

Phase 5 must deliver a **stable `user.id`** for every session — that is the only database contract required now.

---

*End of Phase 5 Authentication Architecture Plan*
