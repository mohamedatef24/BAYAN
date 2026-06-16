# Phase 5 — Authentication Decision & Implementation Roadmap

**Project:** Bayan (بيان)  
**Date:** 2026-06-15  
**Purpose:** Compare Option A vs Option B and select the path for graduation + Phase 6  
**Status:** Decision document — no code  

---

## Options Under Review

| | **Option A** | **Option B** |
|---|-------------|-------------|
| **Guest** | Supabase Anonymous Auth (`signInAnonymously()`) | Local Guest Mode (no Supabase until Google login) |
| **Google** | Supabase OAuth (`signInWithOAuth`) | Supabase OAuth (`signInWithOAuth`) |
| **Guest identity** | Real `auth.users.id` (UUID) from first click | No UUID until Google login; guest = client flag only |
| **Phase 6 FK** | `user_id` exists for all sessions | `user_id` only after Google; guest data in localStorage |

---

# 1. Comparison Matrix

Scored for Bayan graduation goals: **Higher is better** (5 = best).

| Criterion | Option A — Supabase Anonymous | Option B — Local Guest | Winner |
|-----------|------------------------------|------------------------|--------|
| **Simplicity (conceptual)** | 3 — One auth system; guest needs Supabase project + anonymous provider enabled | 4 — Guest is trivial (flag + skip auth UI logic); two mental models (local vs Supabase) | **B** (short-term) |
| **Simplicity (long-term)** | 5 — Single session, single user.id, one logout path | 2 — Guest vs authenticated split; migration logic required in Phase 6 | **A** |
| **Demo reliability (guest path)** | 3 — Requires network + Supabase uptime; fails if project misconfigured | 5 — Works offline; identical to today’s editor demo | **B** |
| **Demo reliability (Google path)** | 4 — Same OAuth flow as B | 4 — Same OAuth flow as A | **Tie** |
| **Demo reliability (full demo)** | 4 — Test Supabase once; both paths consistent | 3 — Google demo OK; guest-to-Google upgrade story is weaker | **A** |
| **Implementation time** | 3 — ~4–5 days (anonymous + profiles trigger + OAuth) | 4 — ~3–4 days (skip anonymous setup; simpler guest UI) | **B** (~1 day saved) |
| **Future scalability (Phase 6+)** | 5 — RLS, documents, summaries, settings attach to user.id immediately; `linkIdentity` preserves UUID on Google upgrade | 2 — Must design guest blob migration, dual storage, edge cases on login | **A** |

### Weighted view for graduation

| Goal | Weight | A | B |
|------|--------|---|---|
| Simplicity | 20% | 3.5 | 3.5 |
| Demo reliability | 30% | 3.5 | 4.5 |
| Implementation time | 25% | 3 | 4 |
| Future scalability | 25% | 5 | 2 |
| **Weighted score** | | **3.65** | **3.55** |

**Close call** — Option A wins slightly on weighted score because Phase 6 is already planned and scalability is a stated graduation architecture goal (`ARCHITECTURAL_ANALYSIS.md` recommends hybrid guest + Google with Supabase).

---

# 2. Detailed Comparison

## 2.1 Simplicity

### Option A — Supabase Anonymous

**Pros:**

- One client: `@supabase/supabase-js`
- One session object for guest and Google users
- One logout: `signOut()`
- Guest upgrade: `linkIdentity({ provider: 'google' })` keeps same `user.id`

**Cons:**

- Supabase dashboard setup before any guest login works
- Must enable Anonymous provider (easy to forget)
- Auth bootstrap always async (`getSession()`)

### Option B — Local Guest

**Pros:**

- Guest = `localStorage.setItem('bayan-guest', '1')` or no auth gate at all
- No network for 90% of supervisor demo (typing, analyze, import/export)
- Supabase only loaded when user clicks Google

**Cons:**

- Two states: `{ mode: 'local-guest' }` vs `{ mode: 'supabase', session }`
- Logout means different things per mode
- Phase 6 must answer: *Where do guest documents live before Google?*

**Verdict:** Option B is simpler for **Phase 5 only**. Option A is simpler for **the full product arc (Phases 5–6)**.

---

## 2.2 Demo Reliability

### Graduation demo scenarios

| Scenario | Option A | Option B |
|----------|----------|----------|
| Laptop offline, show editor + analyze | ⚠️ Guest needs Supabase call once | ✅ Works fully |
| Classroom Wi‑Fi flaky | ⚠️ Anonymous sign-in may hang | ✅ Guest unaffected |
| Show Google login to supervisor | ✅ Same | ✅ Same |
| Show “account” in nav | ✅ Real session | ⚠️ Guest shows fake/local state |
| OAuth redirect misconfigured | ❌ Both fail on Google | ❌ Both fail on Google |
| Supabase project paused (free tier) | ❌ Guest broken | ✅ Guest still works |

### Mitigations for Option A (without changing architecture)

1. **Pre-warm session** before demo: open app once while online; session persists in localStorage
2. **Vendor bundle** `supabase.min.js` locally (no CDN dependency)
3. **Demo checklist**: verify anonymous sign-in 24h before presentation
4. **Fallback copy**: if `signInAnonymously()` fails, show toast + allow read-only editor (optional polish — not dual architecture)

**Verdict:** Option B is more reliable for **offline / guest-only** demos. Option A is more reliable for **auth story + Phase 6 narrative** if network is confirmed.

---

## 2.3 Implementation Time

| Task | Option A | Option B |
|------|----------|----------|
| Supabase project + Google OAuth | 0.5 day | 0.5 day |
| Enable anonymous + profiles trigger | 0.5 day | — |
| Auth JS module | 1 day | 0.75 day |
| Auth UI (gate + menu) | 1 day | 1 day |
| OAuth + session restore testing | 0.5 day | 0.5 day |
| Guest local state + edge cases | — | 0.25 day |
| Phase 6 migration design doc | 0.25 day | 0.5 day (more complex) |
| **Total** | **~4–5 days** | **~3–4 days** |

**Verdict:** Option B saves roughly **1 day** in Phase 5. Option A saves **1–2+ days** in Phase 6 by avoiding guest data migration.

---

## 2.4 Future Scalability

### Phase 6 requirements (from existing plans)

- `documents.user_id` → FK to `auth.users`
- `summaries.user_id`
- `settings.user_id`
- Row-Level Security: `auth.uid() = user_id`

### Option A path

```
Guest signs in anonymously → user_id = abc-123
Phase 6 saves document → INSERT documents (user_id = abc-123)
User links Google → still abc-123
No migration
```

### Option B path

```
Guest uses app → documents in localStorage OR no persistence
User signs in with Google → user_id = xyz-789 (NEW)
Phase 6 must:
  - Read localStorage guest drafts
  - INSERT into documents for xyz-789
  - Handle conflict if guest had multiple tabs
  - Decide retention policy for orphaned local data
```

**Verdict:** Option A is strongly preferred if Phase 6 is in scope for the graduation project or immediately after.

---

# 3. Recommendation

## ✅ **Recommend Option A: Supabase Anonymous Auth + Google Login**

### Why

1. **Phase 6 is already architected** around Supabase `user_id` and RLS. Option B creates deliberate technical debt that must be paid during the busiest phase.

2. **Guest → Google upgrade** is a graduation demo story supervisors understand. `linkIdentity()` preserves identity without a migration speech.

3. **Implementation time gap is small** (~1 day). Phase 6 savings exceed that.

4. **Single session model** reduces bugs (logout, refresh, menu state).

5. **Aligns with** `ARCHITECTURAL_ANALYSIS.md` hybrid recommendation and `PHASE_5_AUTHENTICATION_PLAN.md`.

### When Option B would be better

Choose Option B **only if all** of the following are true:

- Phase 6 database is **cut from graduation scope**
- Demo venue has **unreliable or no internet**
- You have **≤ 2 days** for Phase 5 and will not show Google login live

For Bayan’s stated goals (minimal changes + Phase 6 prep), **Option A is the correct choice**.

### Demo reliability compromise (recommended add-on)

Keep Option A architecture but add **one UX fallback** (not Option B):

> If `signInAnonymously()` fails after timeout (e.g. 5s), show Arabic message and still allow editor access with a visible “وضع غير متصل — سجّل دخولك لاحقاً” banner. Do **not** persist as guest without UUID — Phase 6 hook waits for successful anonymous sign-in or Google.

This preserves architecture while protecting the live demo.

---

# 4. Final Implementation Roadmap

**Chosen path:** Option A  
**Estimated duration:** 4–5 working days  
**Hard rules:** Do not modify `renderer.js`, `selection.js`, or editor analyze/render/apply logic.

---

## Phase 0 — Prerequisites (before auth code)

**Duration:** 0.5 day | **Blocker for graduation security**

| # | Task | Owner |
|---|------|-------|
| 0.1 | Fix `summaryText.innerHTML` XSS (use `textContent` / `escapeHtml`) | Frontend |
| 0.2 | Fix `error.message` in summary error HTML | Frontend |
| 0.3 | Escape `suggestion.correction` in renderer `title` attribute | Frontend |

Auth stores JWT in localStorage — XSS hardening is a **prerequisite**, not optional.

---

## Phase 5.1 — Supabase Foundation

**Duration:** 0.5 day | **Risk:** Low

| # | Task | Deliverable |
|---|------|-------------|
| 1.1 | Create Supabase project | Project URL + anon key |
| 1.2 | Enable **Anonymous** sign-in | Dashboard setting verified |
| 1.3 | Enable **Google** provider | Client ID/secret in Supabase |
| 1.4 | Configure redirect URLs | `localhost:5000`, production domain |
| 1.5 | Add `.env.example` | Document public vars only |
| 1.6 | Download `supabase.min.js` to `src/js/vendor/` | Offline demo support |

**Exit criteria:** Manual test in Supabase Auth dashboard — anonymous user appears in Users table.

---

## Phase 5.2 — Database: Profiles Only

**Duration:** 0.5 day | **Risk:** Low | **Prepares Phase 6**

| # | Task | Deliverable |
|---|------|-------------|
| 2.1 | Create `profiles` table (`id` FK → `auth.users`) | SQL migration |
| 2.2 | Create `handle_new_user()` trigger | Auto-insert profile on signup |
| 2.3 | Enable RLS on `profiles` | Policy: `auth.uid() = id` |
| 2.4 | Set `auth_provider` column | `'anonymous'` or `'google'` |

**Do not create** `documents`, `summaries`, `settings` tables yet — schema documented in `PHASE_5_AUTHENTICATION_PLAN.md` for Phase 6.

**Exit criteria:** Guest anonymous signup creates row in `profiles`.

---

## Phase 5.3 — Auth Module (no UI)

**Duration:** 1 day | **Risk:** Low

| # | Task | File |
|---|------|------|
| 3.1 | Supabase client singleton | `src/js/auth/client.js` |
| 3.2 | Config from meta tags or config.js | `src/js/auth/config.js` |
| 3.3 | Session helpers: `getSession`, `onAuthStateChange`, `isGuest`, `isGoogleUser` | `src/js/auth/session.js` |
| 3.4 | Actions: `signInAsGuest`, `signInWithGoogle`, `linkGoogle`, `signOut` | `src/js/auth/auth.js` |
| 3.5 | Expose read-only `window.__bayanAuth` facade | `auth.js` |

**Exit criteria:** Console-log session after guest sign-in; no UI required yet.

**Must not touch:** `editor.js`, `renderer.js`, `selection.js`, `documents/*`.

---

## Phase 5.4 — Auth UI

**Duration:** 1 day | **Risk:** Low

| # | Task | Location |
|---|------|----------|
| 4.1 | Auth gate markup (Guest + Google buttons) | `index.html` |
| 4.2 | Account menu in nav (avatar, name, logout) | `index.html` |
| 4.3 | Guest menu item: “ربط حساب Google” | Account menu |
| 4.4 | Mobile: auth in drawer + account trigger | `index.html` + `components.css` |
| 4.5 | Styles matching Phase 2 tokens | `components.css` |
| 4.6 | UI wiring: `updateAuthUI()`, show/hide gate | `src/js/auth/auth-ui.js` |

**Copy (Arabic):**

- المتابعة كضيف
- المتابعة باستخدام Google
- تسجيل الخروج
- ربط حساب Google

**Exit criteria:** Visual review in dark + light theme.

---

## Phase 5.5 — App Integration

**Duration:** 0.5 day | **Risk:** Medium

| # | Task | Notes |
|---|------|-------|
| 5.1 | Add script tags (auth before editor init) | Order: vendor → auth/* → theme → ui → editor |
| 5.2 | Update `DOMContentLoaded`: `initAuth()` then existing inits | Editor always initializes |
| 5.3 | Default landing: `#/editor` or post-auth redirect to editor | Graduation demo preference |
| 5.4 | OAuth return handling (`detectSessionInUrl: true`) | Test full redirect cycle |
| 5.5 | Network failure fallback toast (optional) | Demo safety net |

**Exit criteria:** Full app loads; editor typing/analyze/import/export unchanged.

---

## Phase 5.6 — End-to-End Testing

**Duration:** 0.5 day | **Risk:** Medium

| # | Test | Expected |
|---|------|----------|
| 6.1 | Guest sign-in | Session + profile row; editor works |
| 6.2 | Page refresh | Session restored; no re-gate |
| 6.3 | Google sign-in (cold) | OAuth → session; profile shows Google |
| 6.4 | Guest → link Google | Same `user.id`; provider updated |
| 6.5 | Logout | Session cleared; gate shown |
| 6.6 | Regression: `node test_renderer.js` | PASS |
| 6.7 | Regression: TXT/DOCX import/export | PASS |
| 6.8 | Mobile drawer auth | Touch targets OK |

---

## Phase 5.7 — Documentation & Demo Pack

**Duration:** 0.5 day | **Risk:** Low

| # | Deliverable |
|---|-------------|
| 7.1 | Update README — Supabase setup steps |
| 7.2 | `PHASE_5_COMPLETION_REPORT.md` |
| 7.3 | Graduation demo script: Guest path → editor → Google upgrade |
| 7.4 | Phase 6 handoff note: `user_id` contract + table schemas |

---

## Timeline Summary

```
Week view (single developer)
──────────────────────────────────────────────────
Day 1   Phase 0 (security) + Phase 5.1 (Supabase) + 5.2 (profiles)
Day 2   Phase 5.3 (auth module)
Day 3   Phase 5.4 (auth UI)
Day 4   Phase 5.5 (integration) + 5.6 (E2E tests)
Day 5   Phase 5.7 (docs) + demo rehearsal buffer
──────────────────────────────────────────────────
```

---

## Files Summary (Option A)

### Create

```
src/js/auth/config.js
src/js/auth/client.js
src/js/auth/session.js
src/js/auth/auth.js
src/js/auth/auth-ui.js
src/js/vendor/supabase.min.js
supabase/migrations/001_profiles.sql   (optional repo location)
.env.example
PHASE_5_COMPLETION_REPORT.md
```

### Modify

```
src/index.html          — auth UI, scripts, init order
src/css/components.css  — auth gate, account menu, Google button
src/js/ui.js            — optional: minimal hook only if needed
```

### Do not modify

```
src/js/renderer.js
src/js/selection.js
src/js/editor.js        (analyze / render / apply / loadDocumentText logic)
src/js/documents/*
src/app.py              (Phase 5)
```

---

## Phase 6 Handoff (what Option A unlocks)

After Phase 5, Phase 6 can immediately:

1. Add `documents`, `summaries`, `settings` tables with `user_id uuid references auth.users`
2. Enable RLS policies using `auth.uid()`
3. Save editor content on interval or explicit save — keyed to existing session
4. Sync theme from `settings` table on login
5. Optionally add Flask JWT middleware for per-user rate limits

No guest migration layer required.

---

## Decision Record

| Field | Value |
|-------|-------|
| **Decision** | Option A — Supabase Anonymous Auth + Google Login |
| **Rejected** | Option B — Local Guest Mode (deferred migration cost outweighs 1-day savings) |
| **Condition** | Ship Phase 0 XSS fixes before auth |
| **Demo fallback** | Network error toast + editor access banner (not full Option B) |
| **Next step** | Execute Phase 5.1 after Phase 0 security fixes |

---

*End of decision document — no code implemented*
